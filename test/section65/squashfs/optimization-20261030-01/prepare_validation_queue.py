#!/usr/bin/env python3
"""Serial resource and final-identity diagnostics after application pilots."""
import json
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65';HERE=Path(__file__).resolve().parent

def main():
    runs=(SECTION/'build/squashfs/optimization-runs-01').resolve()
    build=runs/'builds/optimization-cache-01';jobs=json.loads((HERE/'resource-queue.json').read_text())
    def add(name,script,args,private=True):
        out=runs/name;assert not out.exists()
        argv=(['unshare','--mount','--propagation','private'] if private else [])+['python3',str(script),'--build',str(build),*map(str,args),'--output',str(out)]
        jobs.append(dict(name=name,kind='validation',argv=argv,result=str(out/'result.json')))
    add('shared-decoder-01',HERE/'shared_diagnostic.py',[])
    add('native-calls-01',SECTION/'squashfs/improvement/count_native.py',['--counter',SECTION/'build/squashfs/service-counter-02/service_counter.ko'])
    add('minimal-deployment-01',SECTION/'squashfs/improvement/minimal_deployment.py',['--image',SECTION/'build/squashfs/application-images-01/xz.sif','--user','zzk'])
    add('hardening-01',HERE/'hardening.py',[],False)
    path=HERE/'validation-queue.json';assert not path.exists();path.write_text(json.dumps(jobs,indent=2)+'\n')
    print('prepared',len(jobs),'untimed-resource/diagnostic jobs; no formal campaigns')

if __name__=='__main__':main()
