#!/usr/bin/env python3
"""Fresh-directory collector; never invokes historical destructive run.sh files."""
import argparse
import csv
import datetime
import getpass
import os
import re
import shutil
import statistics as st
import subprocess as sp
import uuid
from pathlib import Path
from layer3_v2 import ROOT, ROUTINES, BUILDS, sha, dump, write_csv
import json

PASSWORD=None
def command(args, cwd=None):
    return sp.check_output(list(map(str,args)),cwd=cwd,text=True,stderr=sp.STDOUT)

def privileged(args):
    global PASSWORD
    if os.geteuid()==0: return command(args)
    if PASSWORD is None:
        if sp.run(['sudo','-n','true'],stdout=sp.DEVNULL,stderr=sp.DEVNULL).returncode==0:
            PASSWORD=''
        else: PASSWORD=getpass.getpass('sudo password (not saved): ')
    return sp.check_output(['sudo','-S','-p','','--',*map(str,args)],input=PASSWORD+'\n',text=True,stderr=sp.STDOUT)

def identity(out):
    data=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),kernel=os.uname().release,
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        compiler=command(['gcc','--version']),git_commit=command(['git','rev-parse','HEAD']).strip(),
        cmdline=Path('/proc/cmdline').read_text(),cpuinfo=Path('/proc/cpuinfo').read_text(),
        online=Path('/sys/devices/system/cpu/online').read_text(),
        smt=Path('/sys/devices/system/cpu/smt/active').read_text())
    dump(out/'identity.json',data)
    (out/'git-status.txt').write_text(command(['git','status','--short']))
    (out/'worktree.patch').write_text(command(['git','diff','HEAD']))
    return data

def capture_sources(out):
    dst=out/'source';dst.mkdir()
    for name in ROUTINES:
        d=dst/name;d.mkdir()
        for p in (ROOT/'layer3'/name).iterdir():
            if p.name in ('bench_kmod.c','bench_kmod_main.c','Makefile','run.sh') or p.name.startswith('generate_'):
                shutil.copy2(p,d/p.name)
    d=dst/'scripts';d.mkdir()
    for p in (ROOT/'scripts').glob('*layer3*v2*.py'):shutil.copy2(p,d/p.name)
    dump(out/'source-hashes.json',{str(p.relative_to(dst)):sha(p) for p in dst.rglob('*') if p.is_file()})

def module_session(ko,args,out,module='bench_kmod'):
    assert not Path('/sys/module',module).exists(),f'{module} already loaded'
    marker='PGOT_V2_BEGIN_'+uuid.uuid4().hex
    privileged(['sh','-c',f'echo {marker} > /dev/kmsg'])
    record=dict(command=['insmod',str(ko),*args],module_sha256=sha(ko),
                start=datetime.datetime.now(datetime.timezone.utc).isoformat(),marker=marker)
    try:
        record['load_output']=privileged(['insmod',ko,*args])
        record['loaded']=Path('/sys/module',module).exists()
        assert record['loaded']
    finally:
        if Path('/sys/module',module).exists(): record['unload_output']=privileged(['rmmod',module])
        log=privileged(['dmesg','--raw'])
        assert marker in log,'kernel log wrapped before capture'
        log=log.split(marker,1)[1]
        out.write_text(log)
        record['end']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        record['unloaded']=not Path('/sys/module',module).exists()
        dump(out.with_suffix('.json'),record)
    assert record['unloaded']
    return log,record

def calibrate(a):
    a.output.mkdir(parents=True,exist_ok=False);ident=identity(a.output)
    src=ROOT/'layer3/timestamp_calibration';work=a.output/'build';shutil.copytree(src,work,ignore=shutil.ignore_patterns('*.o','*.ko','.*.cmd','Module.symvers','modules.order','*.mod*'))
    records=[];medians=[]
    for build in BUILDS:
        flags=('-mindirect-branch=keep' if build=='no_retpoline' else '-mindirect-branch=thunk-inline -mindirect-branch-register')+' -mfunction-return=keep -fcf-protection=none'
        (a.output/f'build-{build}.log').write_text(command(['make','-B',f'KCFLAGS={flags}'],cwd=work))
        ko=a.output/f'pgot_timestamp_{build}.ko';shutil.copy2(work/'pgot_timestamp.ko',ko)
        (a.output/f'objdump-{build}.txt').write_text(command(['objdump','-dr',ko]))
        for run in range(3):
            log,_=module_session(ko,[f'cpu={a.cpu}'],a.output/f'{build}-{run}.log',module='pgot_timestamp')
            values=re.findall(r'PGOT_TIMESTAMP,(\d+),(\d+)',log)
            assert len(values)==1001 and [int(i) for i,_ in values]==list(range(1001))
            records.extend(dict(build=build,run_id=run,sample=int(i),tsc=int(v)) for i,v in values)
            medians.append(dict(build=build,run_id=run,median_tsc=st.median(int(v) for _,v in values)))
    write_csv(a.output/'raw.csv',records)
    dump(a.output/'calibration.json',dict(identity=ident,cpu=a.cpu,samples_per_load=1001,runs=medians,
        selection_overhead_tsc=max(r['median_tsc'] for r in medians),
        rule='maximum of six module-load medians; exact empty timestamp interval',
        retrospective=True,raw_sha256=sha(a.output/'raw.csv')))
    print('timestamp overhead:',max(r['median_tsc'] for r in medians))

def build_all(out):
    for routine in ROUTINES:
        d=out/routine;d.mkdir();source=out/'source'/routine
        script=(source/'run.sh').read_text()
        for build in BUILDS:
            work=d/build;shutil.copytree(source,work)
            gen=list(work.glob('generate_*.py'))
            if gen: (work/'generate.log').write_text(command(['python3',gen[0],'--out-dir',work]))
            key='NORET_BASE_FLAGS' if build=='no_retpoline' else 'RET_BASE_FLAGS'
            flags=re.search(key+r'="\$\{'+key+r':-([^}]+)\}"',script).group(1)
            (work/'flags.txt').write_text(flags+'\n')
            (work/'build.log').write_text(command(['make','-j2','V=1',f'KCFLAGS={flags}'],cwd=work))
            ko=work/'bench_kmod.ko'
            (work/'objdump.txt').write_text(command(['objdump','-dr','--no-show-raw-insn',ko]))
            (work/'nm.txt').write_text(command(['nm','-S',ko]))
            dump(work/'object-hashes.json',{p.name:sha(p) for p in work.iterdir() if p.suffix in ('.ko','.o')})
            print('built',routine,build,flush=True)

def collect(a):
    config=json.loads(a.config.read_text())
    assert os.uname().release=='5.15.0-119-generic'
    assert config['outer_runs']==8 and config['paired_repeats']==15
    # New result directory only; interrupted measurements never silently reused.
    a.output.mkdir(parents=True,exist_ok=False)
    ident=identity(a.output);capture_sources(a.output)
    shutil.copy2(a.config,a.output/'fixed-batches.json')
    dump(a.output/'status.json',dict(status='building',identity=ident))
    build_all(a.output)
    if a.build_only:
        dump(a.output/'status.json',dict(status='built, formal timing pending'))
        return
    run_built(a.output,config)

def run_built(out,config):
    built=json.loads((out/'identity.json').read_text())
    assert built['kernel']==os.uname().release, 'kernel changed since build'
    assert built['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'boot changed since build'
    for name in ROUTINES:
        for build in BUILDS:
            work=out/name/build
            hashes=json.loads((work/'object-hashes.json').read_text())
            assert sha(work/'bench_kmod.ko')==hashes['bench_kmod.ko'], 'built module changed'
    privileged(['true'])
    # Uses a host advisory lock; do not run any other benchmark concurrently.
    import fcntl
    with (ROOT/'results/.layer3-v2.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        privileged(['modprobe','bch'])
        privileged(['modprobe','zlib_deflate'])
        privileged(['modprobe','zstd_decompress'])
        assert not (out/'sessions.json').exists(),'already has measurement records'
        sessions=[];raws={n:[] for n in ROUTINES}
        dump(out/'status.json',dict(status='running',config_sha256=sha(out/'fixed-batches.json')))
        for run in range(config['outer_runs']):
            # Reverse build order on alternate loads to balance longer-term drift.
            for build in (BUILDS if run%2==0 else BUILDS[::-1]):
                for name in ROUTINES:
                    d=out/name;ko=d/build/'bench_kmod.ko';n=config['batches'][name]
                    params=[f'cpu={config["cpu"]}',f'iterations={n}',f'repeats={config["paired_repeats"]}',
                            f'run_id={run}',f'build={build}',f'irq_off={config["irq_off"]}']
                    params+=['warmups=5'] if name.startswith('01_') else [f'warmup={n}','variants=all']
                    log,record=module_session(ko,params,d/f'{build}-run-{run}.log')
                    assert re.search(r'PGOT_L3(?:SHA)?_DONE,.*ret=0',log)
                    assert 'PGOT_V2_CORRECTNESS,pass' in log
                    assert not re.search(r'VALIDATE_FAIL|BUG:|Oops:|WARNING:|Call Trace:',log)
                    lines=re.findall(r'PGOT_L3(?:SHA)?_RAW,([^\n]+)',log)
                    fields=['experiment','build','run_id','variant','repeat','iterations','origin_cycles','variant_cycles','delta_variant_origin']
                    rows=list(csv.DictReader(lines,fieldnames=fields))
                    assert len(rows)==15*(1 if name.startswith('01_') else 3)
                    assert all(r['build']==build and int(r['run_id'])==run and int(r['iterations'])==n for r in rows)
                    raws[name]+=rows;write_csv(d/'raw.csv',raws[name])
                    record.update(routine=name,build=build,run_id=run,batch=n,status='pass',
                                  correctness='pre-timing checks passed',pair_order='even ABBA, odd BAAB',raw_pairs=len(rows))
                    sessions.append(record);dump(out/'sessions.json',sessions)
            print(f'completed outer run {run+1}/8 for both builds and all routines',flush=True)
        dump(out/'status.json',dict(status='complete',sessions=len(sessions),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('calibrate');q.add_argument('--output',type=Path,required=True);q.add_argument('--cpu',type=int,default=2);q.set_defaults(fn=calibrate)
    q=s.add_parser('collect');q.add_argument('--config',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--build-only',action='store_true');q.set_defaults(fn=collect)
    q=s.add_parser('run-built');q.add_argument('--output',type=Path,required=True)
    q.set_defaults(fn=lambda a:run_built(a.output,json.loads((a.output/'fixed-batches.json').read_text())))
    a=p.parse_args();a.output=a.output.resolve();a.fn(a)
