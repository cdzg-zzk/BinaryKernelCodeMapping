#!/usr/bin/env python3
"""Count actual mounted user work with unchanged baseline core; no formal timing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
from check_fuse import mounted


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--baseline',type=Path,default=ROOT/'test/section65/build/squashfs/evaluation-fixed-01/build')
    p.add_argument('--core',type=Path,default=ROOT/'test/evaluation-local/runs/iso9660/squash-application-gzip-formal-01/libsq-materialized.so')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--codecs',nargs='+',default=['gzip','xz','lz4'])
    p.add_argument('--workloads',nargs='+',default=['scan','archive','stream'])
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    target=out/'mount';target.mkdir();rows=[]
    state=dict(status='running',scope='Instrumented FUSE workload attribution, not application lifecycle or formal performance.',cases=rows)
    def save():(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    shutil.copy2(__file__,out/'runner.py');save()
    try:
        with tempfile.TemporaryDirectory(prefix='sq-profile-',dir='/dev/shm') as scratch:
            payload=Path(scratch)/'output'
            for codec in a.codecs:
                image=ROOT/f'test/section65/build/squashfs/application-images-01/{codec}.sif'
                with image.open('rb') as stream:
                    while stream.read(1<<20):pass
                for task in a.workloads:
                    expected=None
                    for label,build in [('baseline',a.baseline.resolve()),('profile',a.build.resolve())]:
                        log=out/f'{codec}-{task}-{label}.log'
                        argv=[str(build/'vkso-squashfuse'),str(a.core.resolve()),str(build/'libsq-bridge.so'),str(image),'36864',str(target)]
                        with mounted(argv,target,log):
                            subtree='opt/stream-data' if task=='stream' else 'opt/linux-headers'
                            command=['find','.','-printf','%P\t%y\t%s\n'] if task=='scan' else ['tar','-cf','-','.']
                            with payload.open('wb') as output:
                                result=subprocess.run(['taskset','-c','1',*command],cwd=target/subtree,stdout=output,stderr=subprocess.PIPE,timeout=120)
                            assert result.returncode==0,result.stderr
                        digest=hashlib.sha256(payload.read_bytes()).hexdigest()
                        if expected is None:expected=digest
                        assert digest==expected,(codec,task,label)
                        record=dict(codec=codec,task=task,variant=label,output_bytes=payload.stat().st_size,output_sha256=digest,
                            core_sha256=hashlib.sha256(a.core.read_bytes()).hexdigest(),
                            bridge_sha256=hashlib.sha256((build/'libsq-bridge.so').read_bytes()).hexdigest(),
                            frontend_sha256=hashlib.sha256((build/'vkso-squashfuse').read_bytes()).hexdigest())
                        if label=='profile':
                            lines=log.read_text().splitlines()
                            for prefix,key in [('SQ_PROFILE ','bridge'),('SQ_FRONTEND ','frontend')]:
                                values=[json.loads(l[len(prefix):]) for l in lines if l.startswith(prefix)]
                                assert len(values)==1,(log,prefix,values)
                                record[key]=values[0]
                            record['readdir_requests']=[json.loads(l[len('SQ_READDIR '):]) for l in lines if l.startswith('SQ_READDIR ')]
                            assert record['bridge']['cache_gets']==record['bridge']['cache_hits']+record['bridge']['cache_misses']
                        rows.append(record);save();payload.unlink()
                        print(codec,task,label,'correct',flush=True)
        state.update(status='complete',finished=time.time())
    except BaseException:
        state.update(status='failed',error=traceback.format_exc());raise
    finally:save()


if __name__=='__main__':main()
