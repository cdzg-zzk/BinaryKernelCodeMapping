#!/usr/bin/env python3
"""Collect the full three-backend user workload inside an active VKSO export."""
import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
NAMES=('native-dso','adapted-dso','kernel-vkso')


def run(algorithm,directory,build,manifest):
    directory,build=Path(directory),Path(build)
    results=directory/'results';results.mkdir(exist_ok=True)
    libdir=directory/'work/vkso/lib'
    libraries=[p for p in libdir.glob('lib*.so') if p.name!='libshim.so']
    assert len(libraries)==1
    paths=[build/'libnative.so',build/'libadapted.so',libraries[0]]
    env={**os.environ,'LD_LIBRARY_PATH':str(libdir)+':'+os.environ.get('LD_LIBRARY_PATH',''),'LC_ALL':'C'}
    def command(args,log):
        with (results/log).open('w') as f:
            subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    if algorithm in ('lz4','xz'):
        for name,path in zip(NAMES[:2],paths):
            command(['python3',ROOT/'test/test_lz4/scripts/audit_helpers.py','--library',paths[2],
                '--same-source',path,'--bindings',directory/'work/vkso/metadata/data_bindings_resolved.json',
                '--output',results/(name+'-helpers.json'),'--allow-no-import',
                *(['--native-api','xz_dec_run','--carrier-api','vkso_xz_dec_run','--helpers','memcpy'] if algorithm=='xz' else [])],name+'-helpers.log')
    if algorithm=='bch':
        command(['taskset','-c','2',build/'bench','--native',paths[0],'--adapted',paths[1],'--kernel',paths[2],
                 '--outer','11','--sample-ms','10','--correctness-vectors','128','--aligned-inputs',
                 '--output',results/'user.csv'],'user.log')
    elif algorithm=='xz':
        inputs=[s for row in csv.reader(Path(manifest).open()) for s in row]
        command(['taskset','-c','2',build/'bench','--native',paths[0],'--adapted',paths[1],'--kernel',paths[2],
                 '--outer-runs','7','--repeats','20','--',*inputs],'user.csv')
    else:
        manifest=Path(manifest)
        files=[manifest.parent/n for n in manifest.read_text().splitlines() if n and not n.startswith('#')]
        assert len(files)==12 and sum(p.stat().st_size for p in files)==211938580
        logs=results/'official-logs';logs.mkdir()
        spec=importlib.util.spec_from_file_location('parse_official',ROOT/'test/test_lz4/scripts/parse_official.py')
        parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
        rows=[]
        for repeat in range(7):
            blocks=(4096,65536,1048576)
            for position in range(3):
                block=blocks[(position+repeat)%3]
                for p in range(3):
                    b=(p+repeat)%3;name=NAMES[b]
                    log=logs/f'round-{repeat}-block-{block}-{name}.log'
                    with log.open('w') as f:
                        f.write(f'run={repeat}\nbackend={name}\nblock_size={block}\nharness_seconds=2\n');f.flush()
                        subprocess.run(['taskset','-c','2',str(build/'official-lz4-bench'),'--library',str(paths[b]),
                            '--api','kernel','--block-size',str(block),'--seconds','2','--',*map(str,files)],
                            cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
                    rows.extend(parser.parse_log(log))
        with (results/'user.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (results/'user-complete.json').write_text(json.dumps({'status':'pass','algorithm':algorithm,
        'cpu':2,'backends':dict(zip(NAMES,map(str,paths))),'source_build':str(build/'build.json')},indent=2)+'\n')
    sys.path.insert(0,str(ROOT/'test/evaluation'))
    from kernel_cost_host import collect
    collect(directory/'prepared',results/'kernel')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('algorithm');p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--manifest',type=Path)
    a=p.parse_args();run(a.algorithm,a.directory,a.build,a.manifest)
