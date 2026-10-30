#!/usr/bin/env python3
"""Compare complete Apptainer executions and separately observe helper memory."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import pwd
import random
import resource
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent
SECTION = HERE.parent
sys.path.insert(0, str(SECTION))
from squashfs.apptainer_preflight import archive_manifest
from squashfs.check_fuse import observe
from lkl.probe import memory


def descendants(parent):
    parents = {}
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try: parents[int(p.name)] = int((p/'stat').read_text().rsplit(')', 1)[1].split()[1])
            except (OSError, IndexError): pass
    selected = {parent}
    while True:
        expanded = selected | {pid for pid, ppid in parents.items() if ppid in selected}
        if expanded == selected: return selected
        selected = expanded


def snapshot(parent, frontend):
    processes = []
    for pid in sorted(descendants(parent)):
        try:
            executable = (Path('/proc')/str(pid)/'exe').resolve(strict=True)
            processes.append(dict(pid=pid, executable=str(executable), memory=memory(pid),affinity=sorted(os.sched_getaffinity(pid))))
        except (OSError, ProcessLookupError): pass
    helpers = [row for row in processes if row['executable'] == str(frontend)]
    assert len(helpers) == 1, (frontend, processes)
    return dict(helper=helpers[0], processes=processes,
                descendant_pss_kib=sum(r['memory']['Pss'] for r in processes))


def summarize(rows):
    result = []
    variants = sorted({r['variant'] for r in rows})
    for workload in sorted({r['workload'] for r in rows}):
        selected = [r for r in rows if r['workload']==workload]
        pairs=[('stock', v) for v in variants if v!='stock']+[('copied','vkso')]
        if 'lkl-cache-512' in variants:pairs.append(('lkl-512','lkl-cache-512'))
        if 'copied-old' in variants:
            pairs += [('copied-old',v) for v in variants if v.startswith('copied') and v!='copied-old']
        if 'copied-library' in variants:pairs.append(('copied-library','copied'))
        for baseline, treatment in pairs:
            ratios = []
            for b in sorted({r['block'] for r in selected}):
                values = {v:statistics.median(r['wall_seconds'] for r in selected if r['block']==b and r['variant']==v)
                          for v in [baseline,treatment]}
                ratios.append(values[treatment]/values[baseline])
            logs = list(map(math.log, ratios)); rng = random.Random(20261029)
            boot = sorted(math.exp(statistics.mean(rng.choices(logs,k=len(logs)))) for _ in range(10000))
            result.append(dict(workload=workload, baseline=baseline, treatment=treatment,
                blocks=len(ratios), paired_time_ratio=math.exp(statistics.mean(logs)),
                bootstrap_95_percent=[boot[250],boot[9749]],
                median_seconds={v:statistics.median(r['wall_seconds'] for r in selected if r['variant']==v)
                                for v in [baseline,treatment]}))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--core', type=Path, required=True)
    p.add_argument('--copy-core', type=Path, required=True)
    p.add_argument('--page-map', type=Path, required=True)
    p.add_argument('--user', required=True)
    p.add_argument('--build', type=Path, default=SECTION/'build/squashfs/reader-adapted')
    p.add_argument('--lkl', type=Path)
    p.add_argument('--lkl-cache', type=Path, help='separate matched-FUSE-cache LKL diagnostic frontend')
    p.add_argument('--variant-set', nargs='+', help='explicit subset for a separately labeled diagnostic')
    p.add_argument('--analysis-group', default='application')
    p.add_argument('--extra-readers',type=Path,help='explicit additional reader builds for single-factor improvement controls')
    p.add_argument('--blocks', type=int, default=8)
    p.add_argument('--repeats', type=int, default=2)
    p.add_argument('--translator', choices=['c','python'], default='c')
    p.add_argument('--seed', type=int, default=20261029)
    p.add_argument('--campaign', default='unspecified')
    p.add_argument('--pilot', action='store_true')
    p.add_argument('--private-state', action='store_true')
    p.add_argument('--resources-only',action='store_true',help='untimed application/resource observation only')
    p.add_argument('--equal-loader-paths', action='store_true')
    p.add_argument('--cpus',default='1,2',choices=['1,2','1'])
    p.add_argument('--lkl-memory', nargs='+', type=int, default=[16,64])
    p.add_argument('--workloads', nargs='+', choices=['startup','archive','scan','stream','compile'],
                   default=['startup','archive'])
    args = p.parse_args()
    assert os.geteuid()==0
    account = pwd.getpwnam(args.user)
    out = args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    (out/'runner.py').write_bytes(Path(__file__).read_bytes())
    build = args.build.resolve()
    app = SECTION/'build/squashfs/apptainer/jammy/usr/bin/apptainer'
    stock = app.parent.parent/'libexec/apptainer/bin/squashfuse_ll'
    env = dict(os.environ, APPTAINER_CACHEDIR=str(out/'cache'), APPTAINER_CONFIGDIR=str(out/'config'),
               APPTAINER_TMPDIR=str(out/'tmp'),
               LD_LIBRARY_PATH=str(SECTION/'build/squashfs/apptainer/runtime/usr/lib/x86_64-linux-gnu'))
    for name in ['cache','config','tmp']:
        (out/name).mkdir(); os.chown(out/name, account.pw_uid, account.pw_gid)
    variants = dict(stock=dict(frontend=stock,conf=[]),
                    **{'stock-wrapped':dict(frontend=stock,kind='stock')},
                    copied=dict(frontend=build/'vkso-squashfuse',kind='reader',core=args.copy_core.resolve()),
                    vkso=dict(frontend=build/'vkso-squashfuse',kind='reader',core=args.core.resolve()))
    if args.variant_set and 'stock-single' in args.variant_set:
        variants['stock-single']=dict(frontend=stock,kind='stock',single_thread=True)
    if args.lkl:
        for mb in args.lkl_memory:variants[f'lkl-{mb}']=dict(frontend=args.lkl.resolve(),kind='lkl',mb=mb)
    if args.lkl_cache:
        variants['lkl-cache-512']=dict(frontend=args.lkl_cache.resolve(),kind='lkl',mb=512)
    if args.extra_readers:
        for label,entry in json.loads(args.extra_readers.read_text()).items():
            assert label not in variants and label.startswith('copied-'),label
            reader_build=Path(entry['build']).resolve()
            variants[label]=dict(frontend=reader_build/'vkso-squashfuse',kind='reader',
                bridge=reader_build/'libsq-bridge.so',core=Path(entry.get('core',args.copy_core)).resolve(),shared=False)
    if args.variant_set:
        assert set(args.variant_set)<=set(variants) and 'stock' in args.variant_set
        variants={k:v for k,v in variants.items() if k in args.variant_set}
    original_variants={k:dict(v) for k,v in variants.items()}
    alias_records=[];alias_sets={}
    if args.equal_loader_paths:
        assert args.blocks%2==0, 'Balanced two-padding diagnostic requires even blocks'
        for padding in [0,16]:
            alias_sets[padding]={}
            for label,variant in variants.items():
                if variant.get('kind')!='reader':continue
                assert len(label)<=24
                directory=out.parent/('loader'+('x'*padding))/label.ljust(24,'_')
                directory.mkdir(parents=True,exist_ok=True)
                aliases={}
                for key,name in [('frontend','frontend'),('bridge','bridge.so'),('core','core.so')]:
                    src=variant.get(key,build/'libsq-bridge.so');dst=directory/name
                    if label=='vkso' and key=='core':assert dst.exists(), 'Shared aliases must predate registration'
                    else:os.link(src,dst)
                    assert (src.stat().st_dev,src.stat().st_ino)==(dst.stat().st_dev,dst.stat().st_ino)
                    aliases[key]=dst
                    alias_records.append(dict(variant=label,padding=padding,kind=key,source=str(src),path=str(dst),
                        inode=dst.stat().st_ino,sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
                alias_sets[padding][label]=aliases
        for padding in alias_sets:
            for key in ['frontend','bridge','core']:
                assert len({len(str(v[key])) for v in alias_sets[padding].values()})==1
        for label,aliases in alias_sets[0].items():variants[label].update(aliases)
        (out/'loader-aliases.json').write_text(json.dumps(alias_records,indent=2)+'\n')
    def write_helper(label,variant):
        directory=out/(label+'-helper');trace=directory/'trace.jsonl'
        translator=([str(build/'vkso-squash-helper')] if args.translator=='c' else
                    [sys.executable,str(HERE/'apptainer_helper.py')])
        command=translator+['--frontend',str(variant['frontend']),'--kind',variant['kind'],
            '--core',str(variant.get('core','-')),'--bridge',str(variant.get('bridge',build/'libsq-bridge.so')),
            '--memory',str(variant.get('mb',16)),'--trace',str(trace),'--']
        if variant.get('single_thread'):
            command=[str(variant['frontend']),'-s']
        helper=directory/'squashfuse_ll'
        helper.write_text('#!/bin/sh\nexec '+shlex.join(command)+' "$@"\n');helper.chmod(0o755)
    for label, variant in variants.items():
        if label=='stock':continue
        directory = out/(label+'-helper');directory.mkdir()
        trace = directory/'trace.jsonl';trace.touch();os.chown(trace,account.pw_uid,account.pw_gid)
        write_helper(label,variant)
        config = directory/'apptainer.conf'
        config.write_text((app.parent.parent/'etc/apptainer/apptainer.conf').read_text()+
                          '\nbinary path = '+str(directory)+':$PATH:/usr/bin:/bin\n')
        variant['conf']=['--config',str(config)]
    rows, resources, expected = [], {}, None
    result = dict(status='running', scope='end-to-end Apptainer hardware timing including helper startup and cleanup',
                  variants=list(variants), blocks=args.blocks, repeats=args.repeats, cpus=list(map(int,args.cpus.split(','))),
                  image=str(args.image.resolve()), compressed_image_cache='warm', mount='fresh for each sample',
                  helper_implementation=args.translator+' translator followed by execv',
                  launcher='common runuser and taskset included',stock_wrapped_control='stock-wrapped' in variants)
    result.update(seed=args.seed,campaign=args.campaign,workloads=args.workloads,
                  pilot=args.pilot,analysis_group=args.analysis_group,
                  image_sha256=hashlib.sha256(args.image.read_bytes()).hexdigest())
    result['stock_single_scope']='Same squashfuse_ll binary with -s, reached through a shell exec wrapper configured as the helper; startup includes that wrapper. Default stock retained.' if 'stock-single' in variants else None
    result['equal_loader_paths']=args.equal_loader_paths
    result['resource_observation_order']='Before workload and after workload snapshots precede PFN/debugger reads, which may fault additional pages.'
    if args.extra_readers:
        result['extra_readers']=json.loads(args.extra_readers.read_text())
        (out/'extra-readers.json').write_bytes(args.extra_readers.read_bytes())
    (out/'environment.json').write_text(json.dumps(dict(
        argv=sys.argv,runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        uname=list(os.uname()),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        cpuinfo=Path('/proc/cpuinfo').read_text(),meminfo=Path('/proc/meminfo').read_text(),
        loadavg=Path('/proc/loadavg').read_text(),
        frequency={str(p):p.read_text().strip() for p in Path('/sys/devices/system/cpu').glob('cpu*/cpufreq/scaling_governor')},
        binaries={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
          {app,stock,build/'vkso_sq_core.ko',build/'vkso_squashfs.ko',
           build/'vkso-squashfuse',build/'libsq-bridge.so',build/'vkso-squash-helper',
           *([args.lkl.resolve()] if args.lkl else []),
           *[v['frontend'] for v in original_variants.values()],
           *[v['bridge'] for v in original_variants.values() if 'bridge' in v],
           *[v['core'] for v in original_variants.values() if 'core' in v],
           *([args.lkl_cache.resolve()] if args.lkl_cache else [])}}),indent=2)+'\n')
    def write(): (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def argv(variant,work,application):
        return ['runuser','-u',args.user,'--','taskset','-c',args.cpus,str(app),*variant['conf'],'exec',
                '--contain','--cleanenv','--no-home','--no-mount','cwd','--pwd','/work',
                '--bind',str(work)+':/work',str(args.image.resolve()),*application]
    def wait_file(path,child):
        deadline=time.monotonic()+120
        while not path.exists():
            assert child.poll() is None, ('application exited',child.returncode)
            assert time.monotonic()<deadline, ('application timeout',path)
            time.sleep(.01)
    write()
    try:
        with args.image.open('rb') as stream:
            while stream.read(1<<20):pass
        with tempfile.TemporaryDirectory(prefix='vkso-squash-app-',dir='/dev/shm') as temporary:
            work=Path(temporary);work.chmod(0o755);os.chown(work,account.pw_uid,account.pw_gid)
            application=['/usr/bin/tar','-cf','/work/headers.tar','-C','/opt/linux-headers','.']
            for label,variant in variants.items():
                for name in ['ready','release','done','finish','headers.tar']:(work/name).unlink(missing_ok=True)
                script=('touch /work/ready; while [ ! -e /work/release ]; do sleep 0.05; done; '+
                        shlex.join(application)+' || exit $?; touch /work/done; '+
                        'while [ ! -e /work/finish ]; do sleep 0.05; done')
                with (out/(label+'-resource.log')).open('w') as log:
                    child=subprocess.Popen(argv(variant,work,['/bin/sh','-c',script]),env=env,stdout=log,stderr=subprocess.STDOUT)
                    try:
                        wait_file(work/'ready',child)
                        before=snapshot(child.pid,variant['frontend'])
                        (out/(label+'-helper-smaps-before.txt')).write_text(
                            Path('/proc',str(before['helper']['pid']),'smaps').read_text())
                        (work/'release').touch();wait_file(work/'done',child)
                        after=snapshot(child.pid,variant['frontend'])
                        (out/(label+'-helper-smaps-after.txt')).write_text(
                            Path('/proc',str(after['helper']['pid']),'smaps').read_text())
                        if variant.get('kind')=='reader':
                            observe(after['helper']['pid'],variant['core'],args.page_map,
                                    out/(label+'-resource.log'),out/(label+'-pfns.json'),variant.get('shared',label=='vkso'))
                        (out/(label+'-helper-maps.txt')).write_text(
                            Path('/proc',str(after['helper']['pid']),'maps').read_text())
                        if args.private_state and label in ['copied','vkso']:
                            state_path=out/(label+'-private-state.json')
                            state_env=dict(os.environ,VKSO_SNAPSHOT_OUTPUT=str(state_path))
                            with (out/(label+'-private-state.log')).open('w') as state_log:
                                subprocess.run(['gdb','-nx','-batch','-q','-p',str(after['helper']['pid']),
                                    '-ex','add-symbol-file '+str(SECTION/'build/squashfs/debug-types-01/types.o')+' 0',
                                    '-ex','python exec(open('+repr(str(HERE/'private_state_gdb.py'))+').read())'],
                                    env=state_env,stdout=state_log,stderr=subprocess.STDOUT,check=True,timeout=60)
                            assert json.loads(state_path.read_text())['status']=='pass'
                            observe(after['helper']['pid'],variant['core'],args.page_map,
                                    out/(label+'-resource.log'),out/(label+'-pfns-after-state.json'),label=='vkso')
                        (work/'finish').touch();assert child.wait(timeout=30)==0
                    finally:
                        if child.poll() is None:
                            (work/'release').touch();(work/'finish').touch()
                            try:child.wait(timeout=30)
                            except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=15)
                observed=archive_manifest(work/'headers.tar')
                if expected is None:expected=observed
                assert observed==expected,label
                resources[label]=dict(before=before,after=after,entries=len(observed))
                (out/'resources.json').write_text(json.dumps(resources,indent=2)+'\n')
                print('application functionality and memory:',label,flush=True)
            if args.resources_only:
                result.update(status='complete',observations=0,summary=[],resources_only=True)
                return
            applications = dict(startup=['/bin/true'], archive=application,
                scan=['/bin/sh','-c','find /opt/linux-headers -type f > /work/scan.txt'],
                stream=['/usr/bin/tar','-cf','/work/headers.tar','-C','/opt/stream-data','.'],
                compile=['/bin/sh','-c','PYTHONHASHSEED=0 PYTHONPYCACHEPREFIX=/work/pycache /usr/bin/python3.10 -m compileall -q -f --invalidation-mode checked-hash /usr/lib/python3.10'])
            oracles = {'archive': expected}
            def output_manifest(workload):
                if workload in ('archive','stream'): return archive_manifest(work/'headers.tar')
                if workload=='scan': return sorted((work/'scan.txt').read_text().splitlines())
                if workload=='compile':
                    files=sorted((work/'pycache').rglob('*.pyc'))
                    assert len(files)>100, 'Compilation must produce a substantial standard-library output'
                    return {str(f.relative_to(work/'pycache')):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
            for workload in args.workloads:
                if workload in ('startup','archive'): continue
                completed=subprocess.run(argv(variants['stock'],work,applications[workload]),env=env,
                                         capture_output=True,timeout=120,check=True)
                oracles[workload]=output_manifest(workload)
            (out/'workload-oracles.json').write_text(json.dumps(oracles,sort_keys=True)+'\n')
            rng=random.Random(args.seed)
            paddings=[0,16]*(args.blocks//2) if args.equal_loader_paths else [None]*args.blocks
            if args.equal_loader_paths:rng.shuffle(paddings)
            result['loader_padding_order']=paddings
            for block in range(args.blocks):
                if args.equal_loader_paths:
                    for label,aliases in alias_sets[paddings[block]].items():
                        variants[label].update(aliases);write_helper(label,variants[label])
                cells=[(w,v) for w in args.workloads for v in variants];rng.shuffle(cells)
                for workload,label in cells:
                    variant=variants[label]
                    for repeat in range(args.repeats):
                        (work/'headers.tar').unlink(missing_ok=True)
                        (work/'scan.txt').unlink(missing_ok=True)
                        if workload=='compile':shutil.rmtree(work/'pycache',ignore_errors=True)
                        command=argv(variant,work,applications[workload])
                        # Pipe EOF gives prompt completion notification. A
                        # timed wait() with only file outputs polls in Python
                        # and can add up to 50 ms to these short executions.
                        cpu_before=resource.getrusage(resource.RUSAGE_CHILDREN)
                        started=time.perf_counter()
                        completed=subprocess.run(command,env=env,stdout=subprocess.PIPE,
                                                 stderr=subprocess.STDOUT,timeout=120)
                        elapsed=time.perf_counter()-started
                        cpu_after=resource.getrusage(resource.RUSAGE_CHILDREN)
                        (out/f'timing-{block}-{workload}-{label}-{repeat}.log').write_bytes(completed.stdout)
                        assert completed.returncode==0,(workload,label,completed.returncode)
                        if workload!='startup':assert output_manifest(workload)==oracles[workload],(label,workload)
                        row=dict(campaign=args.campaign,sequence=len(rows),block=block,workload=workload,
                                 variant=label,repeat=repeat,wall_seconds=elapsed,
                                 user_cpu_seconds=cpu_after.ru_utime-cpu_before.ru_utime,
                                 system_cpu_seconds=cpu_after.ru_stime-cpu_before.ru_stime)
                        if args.equal_loader_paths:row['loader_padding']=paddings[block]
                        rows.append(row)
                        with (out/'samples.jsonl').open('a') as log:log.write(json.dumps(row)+'\n')
                result['completed_blocks']=block+1;write()
                print(f'Apptainer block {block+1}/{args.blocks}',flush=True)
        result.update(status='complete',observations=len(rows),summary=summarize(rows))
    except BaseException:
        result.update(status='failed',error=traceback.format_exc());raise
    finally:write()


if __name__=='__main__':main()
