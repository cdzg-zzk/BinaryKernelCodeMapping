#!/usr/bin/env python3
"""Paired hardware measurements of original/prepared SquashFS images.

The first traversal follows a new mount; later traversals use populated VFS
caches. The underlying image remains in the host page cache. Output goes to
tmpfs, and its bytes are checked outside the timed interval.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import statistics
import subprocess
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent
SECTION = HERE.parent


def summarize(rows):
    result = []
    for workload in sorted({r['workload'] for r in rows}):
        for phase in ['fresh-mount', 'warm']:
            groups = {}
            for r in rows:
                if r['workload'] == workload and r['phase'] == phase:
                    groups.setdefault((r['block'], r['variant']), []).append(r['wall_seconds'])
            ratios = [statistics.median(groups[b, 'prepared'])/statistics.median(groups[b, 'original'])
                      for b in sorted({key[0] for key in groups})]
            logs = list(map(math.log, ratios)); rng = random.Random(20261029)
            bootstrap = sorted(math.exp(statistics.mean(rng.choices(logs, k=len(logs)))) for _ in range(10000))
            result.append(dict(workload=workload, phase=phase, blocks=len(ratios),
                paired_time_ratio=math.exp(statistics.mean(logs)),
                bootstrap_95_percent=[bootstrap[250], bootstrap[9749]],
                medians_seconds={v:statistics.median(r['wall_seconds'] for r in rows
                    if r['workload']==workload and r['phase']==phase and r['variant']==v)
                    for v in ['original', 'prepared']}))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    inputs = p.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--image', type=Path)
    inputs.add_argument('--image-set', type=Path, help='native_images.py image manifest')
    p.add_argument('--offset', type=int, default=0)
    p.add_argument('--build', type=Path, default=SECTION/'build/squashfs/reader-adapted')
    p.add_argument('--blocks', type=int, default=8)
    p.add_argument('--warm-repeats', type=int, default=2)
    p.add_argument('--cpu', type=int, default=1)
    p.add_argument('--seed', type=int, default=20261029)
    p.add_argument('--campaign', default='unspecified')
    p.add_argument('--pilot', action='store_true')
    p.add_argument('--subtree', default='opt/linux-headers')
    p.add_argument('--workloads', nargs='+', choices=['archive','scan'], default=['archive','scan'])
    p.add_argument('--original-module', type=Path)
    p.add_argument('--original-fs', default='squashfs')
    p.add_argument('--baseline-label', help='explicit identity for a diagnostic reference')
    args = p.parse_args()
    assert os.geteuid() == 0 and args.cpu in os.sched_getaffinity(0)
    assert args.blocks >= 4 and args.warm_repeats >= 1
    assert not Path(args.subtree).is_absolute() and '..' not in Path(args.subtree).parts
    cases = ([dict(image=str(args.image.resolve()), offset=args.offset, compressor='single')]
             if args.image else json.loads(args.image_set.read_text())['cases'])
    assert cases and len({c['compressor'] for c in cases}) == len(cases)
    for case in cases:
        path = Path(case['image'])
        assert path.is_absolute() and path.is_file(), path
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert case.get('sha256', actual) == actual, ('image identity changed', path)
        case['sha256'] = actual
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    (out/'runner.py').write_bytes(Path(__file__).read_bytes())
    mount = out/'mount'; mount.mkdir()
    rows, loaded, expected = [], [], {}
    result = dict(status='running', scope='native hardware performance; fresh-mount and warm VFS caches, host image cached',
                  kernel=os.uname().release, cpu=args.cpu, cases=cases,
                  blocks=args.blocks, warm_repeats=args.warm_repeats,
                  campaign=args.campaign, seed=args.seed, pilot=args.pilot,
                  started=time.time(),
                  subtree=args.subtree, workloads=args.workloads,
                  original_filesystem=args.original_fs,
                  baseline_label=args.baseline_label or args.original_fs,
                  order='randomized compressors, workloads and variant order within each block')
    if args.image:
        result.update(image=str(args.image.resolve()), offset=args.offset)

    def write():
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')

    def command(argv):
        r = subprocess.run(list(map(str, argv)), capture_output=True, text=True, timeout=60)
        with (out/'commands.jsonl').open('a') as log:
            log.write(json.dumps(dict(argv=list(map(str,argv)), returncode=r.returncode,
                                      stdout=r.stdout, stderr=r.stderr))+'\n')
        r.check_returncode()

    write()
    try:
        environment = {'uname': list(os.uname()), 'affinity': sorted(os.sched_getaffinity(0)),
                       'argv':sys.argv, 'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                       'cpuinfo': Path('/proc/cpuinfo').read_text(),
                       'meminfo': Path('/proc/meminfo').read_text(),
                       'loadavg': Path('/proc/loadavg').read_text(),
                       'frequency': {str(p): p.read_text().strip() for p in
                           Path('/sys/devices/system/cpu').glob('cpu*/cpufreq/scaling_governor')},
                       'modules': {name: hashlib.sha256((args.build.resolve()/name).read_bytes()).hexdigest()
                           for name in ['vkso_sq_core.ko', 'vkso_squashfs.ko']}}
        (out/'environment.json').write_text(json.dumps(environment, indent=2)+'\n')
        module_paths=[args.build.resolve()/(name+'.ko') for name in ['vkso_sq_core','vkso_squashfs']]
        if args.original_module:
            module_paths.insert(0,args.original_module.resolve())
            result['original_module']=dict(path=str(args.original_module.resolve()),
                sha256=hashlib.sha256(args.original_module.read_bytes()).hexdigest())
        for path in module_paths:
            name=path.stem
            assert not (Path('/sys/module')/name).exists(), ('already loaded', name)
            command(['insmod', path]); loaded.append(name)
        resident=[line.split() for line in Path('/proc/modules').read_text().splitlines()
                  if line.split()[0] in loaded]
        (out/'resident-modules.json').write_text(json.dumps(dict(
            modules=[dict(name=r[0],reported_bytes=int(r[1]),references=int(r[2])) for r in resident],
            scope='Loaded module residency; dynamic cache and object allocations excluded.'),indent=2)+'\n')
        # Populate the compressed image's host page cache equally for both paths.
        for case in cases:
            with Path(case['image']).open('rb') as stream:
                while stream.read(1 << 20): pass
        rng = random.Random(args.seed)
        with tempfile.TemporaryDirectory(prefix='vkso-squash-cost-', dir='/dev/shm') as scratch:
            payload = Path(scratch)/'payload'
            for block in range(args.blocks):
                ordered = list(cases); rng.shuffle(ordered)
                for case in ordered:
                    collect_case(case, block, payload, mount, args, rng, rows, expected, out, command)
                result['completed_blocks'] = block+1; write()
                print(f"native SquashFS block {block+1}/{args.blocks}", flush=True)
        summary = [dict(compressor=c['compressor'], **s) for c in cases
                   for s in summarize([r for r in rows if r['compressor'] == c['compressor']])]
        assert len(rows) == args.blocks*len(cases)*len(args.workloads)*2*(args.warm_repeats+1)
        result.update(status='complete', observations=len(rows), summary=summary, finished=time.time())
    except BaseException:
        result.update(status='failed', error=traceback.format_exc()); raise
    finally:
        try:
            if os.path.ismount(mount):command(['umount', mount])
            for name in reversed(loaded):command(['rmmod', name])
            result['modules_unloaded'] = True
        except BaseException:
            result.update(status='failed', cleanup_error=traceback.format_exc()); raise
        finally:write()


def collect_case(case, block, payload, mount, args, rng, rows, expected, out, command):
                workloads = list(args.workloads); rng.shuffle(workloads)
                for workload in workloads:
                    variants = ['original', 'prepared']; rng.shuffle(variants)
                    for variant in variants:
                        filesystem = args.original_fs if variant=='original' else 'vksosquash'
                        command(['mount', '-t', filesystem, '-o', f"ro,loop,offset={case['offset']}", case['image'], mount])
                        try:
                            for repeat in range(args.warm_repeats+1):
                                argv = (['tar', '-cf', '-', '-C', str(mount/args.subtree), '.']
                                        if workload=='archive' else
                                        ['find', '.', '-printf', '%P\t%y\t%s\n'])
                                before = resource.getrusage(resource.RUSAGE_CHILDREN)
                                with payload.open('wb') as output:
                                    start = time.perf_counter()
                                    process = subprocess.run(['taskset', '-c', str(args.cpu), *argv], stdout=output,
                                        stderr=subprocess.PIPE, cwd=mount/args.subtree, timeout=60)
                                    elapsed = time.perf_counter()-start
                                after = resource.getrusage(resource.RUSAGE_CHILDREN)
                                assert process.returncode == 0, process.stderr
                                data = payload.read_bytes()
                                digest = hashlib.sha256(data).hexdigest()
                                assert digest == expected.setdefault(workload, digest), (workload, variant)
                                row = dict(campaign=args.campaign, sequence=len(rows), block=block,
                                    compressor=case['compressor'], workload=workload, variant=variant,
                                    phase='fresh-mount' if repeat==0 else 'warm', repeat=repeat,
                                    wall_seconds=elapsed,
                                    cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                                    bytes=len(data), digest=digest)
                                rows.append(row)
                                with (out/'samples.jsonl').open('a') as log:log.write(json.dumps(row)+'\n')
                        finally:command(['umount', mount])


if __name__ == '__main__':main()
