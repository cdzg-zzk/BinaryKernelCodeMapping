#!/usr/bin/env python3
"""Register the prepared owner and verify a real, unprivileged Apptainer task.

Run as root in a private mount namespace. The application itself runs as --user.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
SECTION = HERE.parent
ROOT = SECTION.parents[1]
sys.path.insert(0, str(SECTION))
from reference_guest import manifest
from squashfs.check_fuse import observe


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--user', required=True)
    p.add_argument('--benchmark', action='store_true')
    p.add_argument('--lkl', type=Path)
    p.add_argument('--lkl-cache', type=Path)
    p.add_argument('--variant-set', nargs='+')
    p.add_argument('--extra-readers',type=Path)
    p.add_argument('--analysis-group', default='application')
    p.add_argument('--translator', choices=['c','python'], default='c')
    p.add_argument('--seed', type=int, default=20261029)
    p.add_argument('--campaign', default='unspecified')
    p.add_argument('--pilot', action='store_true')
    p.add_argument('--private-state', action='store_true')
    p.add_argument('--resources-only',action='store_true')
    p.add_argument('--equal-loader-paths', action='store_true', help='separate pathname-controlled diagnostic')
    p.add_argument('--cpus',default='1,2',choices=['1,2','1'],help='application affinity; CPU 1 is a separately labeled placement diagnostic')
    p.add_argument('--verify-without-observer', action='store_true')
    p.add_argument('--blocks', type=int, default=8)
    p.add_argument('--repeats', type=int, default=2)
    p.add_argument('--lkl-memory', nargs='+', type=int, default=[16,64])
    p.add_argument('--workloads', nargs='+', choices=['startup','archive','scan','stream','compile'],
                   default=['startup','archive'])
    p.add_argument('--build', type=Path, default=SECTION/'build/squashfs/reader-adapted')
    p.add_argument('--support', type=Path,
                   default=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029')
    args = p.parse_args()
    assert os.geteuid() == 0
    account = pwd.getpwnam(args.user)
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    os.chown(out, account.pw_uid, account.pw_gid)
    (out/'runner.py').write_bytes(Path(__file__).read_bytes())
    build, support, image = args.build.resolve(), args.support.resolve(), args.image.resolve()
    carrier = out/'carrier'; carrier.mkdir()
    (carrier/'symbols.txt').write_bytes((build/'symbols.txt').read_bytes())
    result = dict(status='running', scope='hardware application correctness and PFN identity; no performance claim')
    result['runner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['stage_resource_observer']=args.verify_without_observer
    if args.benchmark:
        result['scope']='application pilot' if args.pilot else 'hardware application campaign'
        result.update(campaign=args.campaign,pilot=args.pilot)
    loaded, registered, library, child = [], False, None, None
    mount = out/'native-mount'; mount.mkdir()

    def write():
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')

    def command(argv, label, cwd=None, timeout=180):
        executed=list(map(str,argv))
        if args.verify_without_observer:
            executed=['/usr/bin/time','-v','-o',str(out/(label+'-resource.txt')),*executed]
        started=time.perf_counter()
        with (out/(label+'.log')).open('w') as log:
            completed=subprocess.run(executed, cwd=cwd, stdout=log,
                           stderr=subprocess.STDOUT, timeout=timeout)
        with (out/'stages.jsonl').open('a') as log:
            log.write(json.dumps(dict(stage=label,argv=list(map(str,argv)),
                executed=executed,wall_seconds=time.perf_counter()-started,returncode=completed.returncode))+'\n')
        completed.check_returncode()

    try:
        app = SECTION/'build/squashfs/apptainer/jammy/usr/bin/apptainer'
        partitions = subprocess.check_output([app, 'sif', 'list', image], text=True)
        rows = [line.split('|') for line in partitions.splitlines() if 'FS (Squashfs/' in line]
        assert len(rows) == 1
        offset = int(rows[0][3].strip().split('-')[0])
        result.update(partition_offset=offset, user=args.user)
        module_paths = [build/'vkso_sq_core.ko', build/'vkso_squashfs.ko',
                        support/'modules/vkso_kernel_reader.ko', support/'modules/page_cache_replace.ko']
        for path in module_paths:
            assert not (Path('/sys/module')/path.stem).exists(), ('already loaded', path.stem)
            command(['insmod', path], 'load-'+path.stem); loaded.append(path.stem)
        module_rows = [line.split() for line in Path('/proc/modules').read_text().splitlines()
                       if line.split()[0] in loaded]
        (out/'resident-modules.json').write_text(json.dumps(dict(
            modules=[dict(name=r[0],reported_bytes=int(r[1]),references=int(r[2])) for r in module_rows],
            note='Resident module sizes exclude dynamic allocations; original built-in filesystem remains resident in this experimental kernel.'),indent=2)+'\n')
        native = None

        def native_check(filesystem, label):
            command(['mount', '-t', filesystem, '-o', f'ro,loop,offset={offset}', image, mount], label+'-mount')
            try:
                rows = manifest(mount)
                (out/(label+'.json')).write_text(json.dumps(rows, indent=2)+'\n')
                if native is not None:
                    assert native == rows, label
                return rows
            finally:
                command(['umount', mount], label+'-unmount')

        native = native_check('squashfs', 'native-original')
        native_check('vksosquash', 'native-before')
        result.update(stage='export', native_entries=len(native)); write()
        command([support/'krg', 'build', support/'vmlinux', '--module', build/'vkso_sq_core.ko',
                 '-o', carrier/'out.krg'], 'krg')
        command([sys.executable, ROOT/'make_dll/build_PIC_so.py', '--symbols', carrier/'symbols.txt',
                 '--krg', carrier/'out.krg', '--ko', build/'vkso_sq_core.ko',
                 '--shim-list', build/'shim.txt', '--vmlinux', support/'vmlinux'], 'export', cwd=carrier)
        library = next(carrier.glob('lib*.so')).resolve()
        before = library.read_bytes()
        if args.equal_loader_paths:
            # Registration makes the carrier immutable, so hardlinks must
            # exist before replacement. They retain the very same inode.
            for padding in [0,16]:
                alias=out/('loader'+('x'*padding))/'vkso____________________'/'core.so'
                alias.parent.mkdir(parents=True)
                os.link(library,alias)
        command([support/'manager', 'replace', library, carrier/'page_mappings.txt'], 'register', cwd=support)
        registered = True
        result.update(stage='apptainer'); write()
        app_output = out/'application'
        argv = ['runuser', '-u', args.user, '--', sys.executable, HERE/'apptainer_preflight.py',
                '--output', app_output, '--image', image, '--core', library,
                '--bridge', build/'libsq-bridge.so', '--build', build, '--hold-reader',
                '--translator',args.translator]
        with (out/'application.log').open('w') as log:
            child = subprocess.Popen(list(map(str, argv)), stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic()+120
            while not (app_output/'reader/ready').exists():
                assert child.poll() is None, ('application exited', child.returncode)
                assert time.monotonic() < deadline, 'application mount did not become ready'
                time.sleep(.1)
            trace = [json.loads(line) for line in (app_output/'helper.jsonl').read_text().splitlines()]
            assert len(trace) == 1
            observe(trace[0]['pid'], library, carrier/'page_mappings.txt', app_output/'reader.log',
                    out/'application-pfns.json', True)
            (app_output/'reader/release').touch()
            assert child.wait(timeout=120) == 0
        application = json.loads((app_output/'result.json').read_text())
        assert application['status'] == 'pass'
        if args.benchmark:
            copied=out/'libsq-materialized.so';copied.write_bytes(library.read_bytes())
            argv=[sys.executable,HERE/'apptainer_bench.py','--output',out/'benchmark','--image',image,
                  '--user',args.user,'--core',library,'--copy-core',copied,
                  '--page-map',carrier/'page_mappings.txt','--build',build,'--translator',args.translator]
            argv+=['--cpus',args.cpus]
            argv+=['--seed',args.seed,'--campaign',args.campaign,'--blocks',args.blocks,
                   '--repeats',args.repeats,'--lkl-memory',*args.lkl_memory,'--workloads',*args.workloads]
            if args.lkl:argv+=['--lkl',args.lkl.resolve()]
            if args.lkl_cache:argv+=['--lkl-cache',args.lkl_cache.resolve()]
            if args.variant_set:argv+=['--variant-set',*args.variant_set]
            if args.extra_readers:argv+=['--extra-readers',args.extra_readers]
            if args.analysis_group!='application':argv+=['--analysis-group',args.analysis_group]
            if args.pilot:argv+=['--pilot']
            if args.private_state:argv+=['--private-state']
            if args.resources_only:argv+=['--resources-only']
            if args.equal_loader_paths:argv+=['--equal-loader-paths']
            result.update(stage='benchmark');write()
            command(argv,'benchmark',timeout=1800)
            assert json.loads((out/'benchmark/result.json').read_text())['status']=='complete'
            result['benchmark_evidence']=str(out/'benchmark')
        if args.verify_without_observer:
            command(['rmmod','vkso_kernel_reader'],'remove-observer')
            loaded.remove('vkso_kernel_reader')
            output=out/'application-without-observer'
            command(['runuser','-u',args.user,'--',sys.executable,HERE/'apptainer_preflight.py',
                '--output',output,'--image',image,'--core',library,'--bridge',build/'libsq-bridge.so',
                '--build',build,'--translator',args.translator],'application-without-observer',timeout=300)
            observed=json.loads((output/'result.json').read_text())
            assert observed['status']=='pass' and not Path('/sys/module/vkso_kernel_reader').exists()
            result['observer_free_application']=dict(status='pass',entries=observed['entries'],
                scope='Actual new Apptainer invocation after observer-module unload; registration remains active.')
            (out/'modules-without-observer.txt').write_text(Path('/proc/modules').read_text())
        native_check('vksosquash', 'native-after')
        command([support/'manager', 'restore', library, carrier/'page_mappings.txt'], 'restore', cwd=support)
        registered = False
        assert library.read_bytes() == before
        result.update(status='complete', stage='complete', restored=True,
                      application_entries=application['entries'], application_evidence=str(app_output))
    except BaseException:
        result.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        try:
            if child and child.poll() is None:
                release = out/'application/reader/release'
                if release.parent.exists():
                    release.touch()
                child.wait(timeout=120)
            if registered:
                command([support/'manager', 'restore', library, carrier/'page_mappings.txt'], 'cleanup-restore', cwd=support)
                assert library.read_bytes()==before
                result['cleanup_restored']=True
            for name in reversed(loaded):
                command(['rmmod', name], 'unload-'+name)
            result['modules_unloaded'] = True
        except BaseException:
            result.update(status='failed', cleanup_error=traceback.format_exc())
            raise
        finally:
            write()


if __name__ == '__main__':
    main()
