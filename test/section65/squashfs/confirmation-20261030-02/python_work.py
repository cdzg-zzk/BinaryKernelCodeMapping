#!/usr/bin/env python3
"""Count decoder work in the unchanged, complete Python/SIF task; never time it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import traceback
from prerequisite import ROOT, RUNS, verify

SECTION=ROOT/'test/section65'
BUILD=RUNS/'builds/optimization-cache-01'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--trace-cache',action='store_true');p.add_argument('--data-controls',action='store_true');a=p.parse_args()
    assert os.geteuid()!=0
    verify()
    assert json.loads((RUNS/'python-attribution-queue-02/result.json').read_text())['status']=='complete'
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    app=SECTION/'build/squashfs/apptainer/jammy/usr/bin/apptainer'
    stock=app.parent.parent/'libexec/apptainer/bin/squashfuse_ll'
    image=SECTION/'build/squashfs/heldout-python-images-01/xz.sif'
    core=RUNS/'squash-optimized-application-final-gzip-01/libsq-materialized.so'
    source=SECTION/'squashfs/refinement/decoder_counts.c'
    interposer=out/'decoder-counts.so'
    cmd=['gcc','-O2','-shared','-fPIC','-I'+str(BUILD),
         '-I'+str(SECTION/'build/squashfs/deps/usr/include'),str(source),'-ldl','-o',str(interposer)]
    with (out/'build.log').open('w') as log: subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    env=dict(os.environ,LD_LIBRARY_PATH=str(SECTION/'build/squashfs/apptainer/runtime/usr/lib/x86_64-linux-gnu'))
    for key,name in [('APPTAINER_CACHEDIR','cache'),('APPTAINER_CONFIGDIR','config'),('APPTAINER_TMPDIR','tmp')]:
        (out/name).mkdir();env[key]=str(out/name)
    # A single policy difference identified in the stock open callback:
    # immutable file data remains cached across opens. Keep decoder/core fixed.
    frontend_source=BUILD/'xz-user-source/fuse_frontend.c'
    modified=frontend_source.read_text()
    marker='    config->use_ino=1;'
    assert modified.count(marker)==1
    modified=modified.replace(marker,marker+'\n    config->kernel_cache=1; /* Immutable image, matching stock keep_cache. */')
    candidate_source=out/'cache-data-frontend.c';candidate_source.write_text(modified)
    candidate=out/'cache-data-frontend'
    cmd2=['gcc','-O2','-g','-DVKSO_SQ_DIRECTORY_CACHE','-I'+str(SECTION/'build/fuse-deps/usr/include/fuse3'),str(candidate_source),'-Wl,-l:libfuse3.so.3','-ldl','-o',str(candidate)]
    with (out/'frontend-build.log').open('w') as log:subprocess.run(cmd2,stdout=log,stderr=subprocess.STDOUT,check=True)
    variants=['stock','stock-single','copied-library','copied','copied-cachedata']
    trace_build=None
    if a.trace_cache:
        trace_build=out/'trace-build';shutil.copytree(BUILD,trace_build)
        path=trace_build/'xz-user-source/user_bridge.c';code=path.read_text()
        marker='    SQ_COUNT(cache_gets,1);';assert code.count(marker)==1
        trace='''    {
        extern char *getenv(const char *);
        extern int open(const char *,int,...);
        static int fd=-2;
        if (fd==-2) { const char *path=getenv("VKSO_CACHE_TRACE"); fd=path ? open(path,O_WRONLY|O_CREAT|O_APPEND,0600) : -1; }
        if (fd>=0) { char line[160]; int n=snprintf(line,sizeof(line),"%s %llu %d %d\\n",c->name,block,length,c->entries); if(n>0 && n<sizeof(line))write(fd,line,n); }
    }
'''
        path.write_text(code.replace(marker,marker+'\n'+trace))
        args=[sys.executable,str(SECTION/'squashfs/build_user.py'),'--build',str(trace_build),'--source-dir',str(trace_build/'xz-user-source'),'--bridge-only','--directory-cache','--direct-decode','--shared-lz4','--shared-xz']
        with (out/'trace-build.log').open('w') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
        variants=['copied-trace']
    if a.data_controls:
        assert not a.trace_cache
        variants=['copied-data16','copied-data48']
    state=dict(status='running',scope='Instrumented complete Apptainer Python compilation, original SIF and 647-output oracle. Includes program loading and helper mount-time decoding. No timing estimate. Buffer and streaming APIs are alternatives, not summed.',
               cases=[],inputs={str(x):sha(x) for x in [app,stock,image,core,BUILD/'libsq-bridge.so',source,interposer,frontend_source,candidate_source,candidate]},build_command=cmd,frontend_build_command=cmd2)
    def save(): (out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    save();oracle=None
    if a.data_controls:
        previous=RUNS/'python-work-02/oracle.json'
        oracle=json.loads(previous.read_text());state['inputs'][str(previous)]=sha(previous)
        (out/'oracle.json').write_text(json.dumps(oracle,sort_keys=True)+'\n')
    try:
        for repeat in range(1 if a.trace_cache else 3):
            for label in variants:
                case=out/f'{label}-{repeat}';case.mkdir()
                counts=case/'counts.json'
                frontend=stock if label.startswith('stock') else candidate if label=='copied-cachedata' else BUILD/'vkso-squashfuse'
                wrapped=case/'frontend'
                wrapped.write_text('#!/bin/sh\nexec '+shlex.join(['/usr/bin/env','LD_PRELOAD='+str(interposer),'VKSO_DECODER_COUNTS='+str(counts),'VKSO_CACHE_TRACE='+str(case/'cache-requests.txt'),str(frontend),*(['-s'] if label=='stock-single' else [])])+' "$@"\n')
                wrapped.chmod(0o755)
                command=[str(wrapped)]
                if label.startswith('copied'):
                    bridge=(RUNS/'builds/optimization-decoder-controls-01/copied-library/libsq-bridge.so' if label=='copied-library' else BUILD/'libsq-bridge.so')
                    if label=='copied-trace':bridge=trace_build/'libsq-bridge.so'
                    if label in ['copied-data16','copied-data48']:
                        bridge=RUNS/'builds/data-cache-controls-02'/('data-'+label.removeprefix('copied-data'))/'libsq-bridge.so'
                    command=[str(BUILD/'vkso-squash-helper'),'--frontend',str(wrapped),'--kind','reader','--core',str(core),'--bridge',str(bridge),'--trace',str(case/'trace.jsonl'),'--']
                    state['inputs'][str(bridge)]=sha(bridge)
                helper=case/'squashfuse_ll';helper.write_text('#!/bin/sh\nexec '+shlex.join(command)+' "$@"\n');helper.chmod(0o755)
                conf=case/'apptainer.conf';conf.write_text((app.parent.parent/'etc/apptainer/apptainer.conf').read_text()+'\nbinary path = '+str(case)+':$PATH:/usr/bin:/bin\n')
                with tempfile.TemporaryDirectory(prefix='vkso-python-count-',dir='/dev/shm') as tmp:
                    work=Path(tmp)
                    argv=['taskset','-c','1,2',str(app),'--config',str(conf),'exec','--contain','--cleanenv','--no-home','--no-mount','cwd','--pwd','/work','--bind',str(work)+':/work',str(image),'/bin/sh','-c',
                          'PYTHONHASHSEED=0 PYTHONPYCACHEPREFIX=/work/pycache /usr/bin/python3.10 -m compileall -q -f --invalidation-mode checked-hash /usr/lib/python3.10']
                    with (case/'application.log').open('w') as log: subprocess.run(argv,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
                    files={str(f.relative_to(work/'pycache')):sha(f) for f in sorted((work/'pycache').rglob('*.pyc'))}
                    assert len(files)==647,len(files)
                    if oracle is None:
                        oracle=files;(out/'oracle.json').write_text(json.dumps(files,sort_keys=True)+'\n')
                    assert files==oracle
                value=json.loads(counts.read_text());assert sum(v['calls'] for v in value.values())>0
                state['cases'].append(dict(variant=label,repeat=repeat,counts=value,outputs=len(files),argv=argv))
                save();print(label,repeat,value,flush=True)
        state['status']='complete'
    except BaseException:
        state.update(status='failed',error=traceback.format_exc());raise
    finally: save()

if __name__=='__main__':main()
