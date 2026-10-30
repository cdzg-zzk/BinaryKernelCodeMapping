#!/usr/bin/env python3
"""Package newly optimized ordinary native references for guest-only regression."""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65'
HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);pkg=out/'package'
    shutil.copytree(SECTION/'build/squashfs/optimization-cache-guest-01/package',pkg)
    refs=SECTION/'build/squashfs/optimization-native-controls-01';hashes={}
    for policy in ['normal','relaxed']:
        module=refs/('native-word-'+policy)/'sq_reference.ko'
        shutil.copy2(module,pkg/('native-word-'+policy+'.ko'));hashes[policy]=hashlib.sha256(module.read_bytes()).hexdigest()
    shutil.copy2(HERE/'native_controls_guest.py',pkg/'native_controls_guest.py')
    (pkg/'run.sh').write_text('#!/bin/bash\nset -eu\ncd /work/package\nexport LD_LIBRARY_PATH=/work/package\nexport PATH=/work/package/bin:$PATH\nexec python3 -u native_controls_guest.py\n')
    with (out/'runner.log').open('w') as log:
        subprocess.run([sys.executable,SECTION/'native/qemu.py','--package',pkg,'--output',out/'guest',
            '--kernel','/boot/vkso-final-raw-normal-5.15.198.bzImage','--native-ide','--timeout','600'],stdout=log,stderr=subprocess.STDOUT,check=True)
    record=json.loads((out/'guest/evidence/result.json').read_text());assert record['status']=='complete' and len(record['cases'])==10
    record['module_hashes']=hashes;(out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print('10 native-reference valid mounts passed')

if __name__=='__main__':main()
