#!/usr/bin/env python3
"""Prepare and run the unified six-version section 6.3 experiment."""
import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'test/section63'
sys.path.insert(0,str(ROOT/'test/evaluation'))
from kernel_cost_host import prepare as prepare_kernel
from build import build as prepare_user


def save(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
def modules():return {l.split()[0]:int(l.split()[2]) for l in Path('/proc/modules').read_text().splitlines()}
def source(algorithm):return ROOT/'test'/('test_BCH' if algorithm=='bch' else 'test_'+algorithm)


def prepare(output):
    output.mkdir(parents=True,exist_ok=False)
    builds=output/'builds';builds.mkdir()
    snapshot=output/'source-files';snapshot.mkdir()
    shutil.copytree(HERE/'source',snapshot/'original')
    shutil.copytree(HERE/'scripts',snapshot/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
    helpers=snapshot/'evaluation';helpers.mkdir()
    for p in (ROOT/'test/evaluation').glob('*.py'):shutil.copy2(p,helpers/p.name)
    for folder in ('kernel-cost','bch-kernel','bch-kernel-matched'):
        shutil.copytree(ROOT/'test/evaluation'/folder,helpers/folder,
                        ignore=shutil.ignore_patterns('*.o','*.ko','*.cmd','*.mod*','__pycache__'))
    corpus=output/'corpus';corpus.mkdir()
    shutil.copytree(ROOT/'test/test_lz4/corpus/silesia',corpus/'silesia')
    xz=corpus/'xz';xz.mkdir()
    old=HERE/'results/corpus/xz/manifest.csv'
    if not old.exists():
        raise FileNotFoundError('Retained XZ corpus required: '+str(old))
    manifest=[]
    for label,plain,compressed in csv.reader(old.open()):
        shutil.copy2(plain,xz/label);shutil.copy2(compressed,xz/(label+'.xz'))
        manifest.append([label,str(xz/label),str(xz/(label+'.xz'))])
    with (xz/'manifest.csv').open('w') as f:csv.writer(f).writerows(manifest)
    owners=output/'owners';owners.mkdir()
    for algorithm in ('lz4','bch','xz'):
        legacy=source(algorithm)
        own=owners/algorithm;own.mkdir()
        for p in (legacy/'kmod').iterdir():
            if p.name in ('Makefile','Module.symvers') or p.suffix in ('.c','.h','.cmd','.ko'):
                shutil.copy2(p,own/p.name)
        if algorithm=='bch':shutil.copytree(legacy/'adapted',owners/'adapted')
        prepare_user(algorithm,builds/algorithm)
        shutil.copytree(legacy/'src',snapshot/(algorithm+'-bench-source'))
        port=snapshot/(algorithm+'-port');port.mkdir()
        shutil.copy2(legacy/'Makefile',port/'Makefile')
        if algorithm=='lz4':
            for folder in ('lib','programs'):
                shutil.copytree(legacy/'vendor/lz4-1.9.3'/folder,port/'vendor/lz4-1.9.3'/folder,
                    ignore=shutil.ignore_patterns('*.o','*.so','*.a'))
        for folder in ('config','userspace','userspace_kernel'):
            if (legacy/folder).exists():
                shutil.copytree(legacy/folder,port/folder,
                    ignore=shutil.ignore_patterns('*.o','*.so','__pycache__','build'))
        if algorithm=='bch':
            shutil.copytree(legacy/'vendor/parrot-bch/standalone',port/'standalone',
                ignore=shutil.ignore_patterns('*.o','*.so'))
    os.environ['BCH_ALIGNED_INPUTS']='1'
    entries=[]
    for number,order in enumerate((('bch','xz','lz4'),('xz','lz4','bch'),('lz4','bch','xz'))):
        for algorithm in order:
            directory=output/f'deployment-{number:02d}-{algorithm}';directory.mkdir()
            manifest=corpus/('silesia/manifest.txt' if algorithm=='lz4' else 'xz/manifest.csv') if algorithm!='bch' else None
            prepare_kernel(algorithm,source(algorithm)/'kmod',directory/'prepared',2,manifest)
            entries.append(dict(algorithm=algorithm,directory=str(directory),manifest=str(manifest) if manifest else None))
    save(output/'plan.json',dict(status='prepared',kernel='5.15.0-119-generic',cpu=2,deployments_per_algorithm=3,
         user_rounds={'lz4':7,'bch':11,'xz':7},kernel_rounds=11,entries=entries,
         user_versions=['native-dso','adapted-dso','kernel-vkso'],kernel_versions=['stock','matched-original-source','owner']))
    print('Prepared all nine deployments.',flush=True)


def collect(output):
    assert os.geteuid()==0 and os.uname().release=='5.15.0-119-generic'
    plan=json.loads((output/'plan.json').read_text())
    assert not (output/'complete.json').exists()
    env={**os.environ,'LC_ALL':'C','BCH_ALIGNED_INPUTS':'1'}
    for key in ('LD_PRELOAD','MAKEFLAGS','MFLAGS'):env.pop(key,None)
    for entry in plan['entries']:
        algorithm=entry['algorithm'];d=Path(entry['directory']);legacy=source(algorithm)
        if (d/'complete.json').exists():continue
        assert not {'vkso_lz4','vkso_bch','vkso_xz','page_cache_replace','matched_lz4','matched_xz','bch_matched'} & modules().keys()
        save(d/'identity.json',dict(kernel=os.uname().release,cpu=2,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),started_utc=dt.datetime.now(dt.timezone.utc).isoformat()))
        owner=output/'owners'/algorithm/('vkso_'+algorithm+'.ko');loaded=False
        with (d/'runner.log').open('w') as log:
            def command(args):subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
            try:
                command(['insmod',owner]);loaded=True
                command([ROOT/'vkso','init',d/'work','--symbols',legacy/'config/symbols.txt'])
                args=[ROOT/'vkso','exec',d/'work','--symbols',legacy/'config/symbols.txt',
                      '--module',owner,'--owner-ko',owner,'--shim-list',ROOT/'make_dll/shim.txt']
                if algorithm!='bch':args+=['--data-bindings',legacy/'config/data-bindings.json']
                args+=['--','python3',HERE/'scripts/collect_user.py',algorithm,'--directory',d,'--build',output/'builds'/algorithm]
                if entry['manifest']:args+=['--manifest',entry['manifest']]
                command(args)
            finally:
                if loaded and modules().get('vkso_'+algorithm)==0:command(['rmmod','vkso_'+algorithm])
        assert 'vkso_'+algorithm not in modules()
        save(d/'complete.json',dict(status='pass',owner_unloaded=True,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))
        print(d.name+': complete',flush=True)
    save(output/'complete.json',dict(status='pass',deployments=9))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','collect'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();(prepare if a.action=='prepare' else collect)(a.output.resolve())
