#!/usr/bin/env python3
"""Replay the repaired malformed-input case and all format regressions in a guest."""
import argparse, errno, hashlib, json
from pathlib import Path
import subprocess,sys,traceback
ROOT=Path(__file__).resolve().parents[4];HERE=ROOT/'test/section65/squashfs';sys.path.insert(0,str(HERE))
from maintenance import fixture,package

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);images=out/'fixture';images.mkdir()
    result=dict(status='running',scope='Guest-only repaired-negative-offset and five-format regression of candidate; no timing.',
        fixture=fixture(images),binaries={n:hashlib.sha256((a.build/n).read_bytes()).hexdigest() for n in ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse']})
    write=lambda:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');write()
    try:
        pkg=out/'package';package(a.build.resolve(),pkg,images);(pkg/'mode').write_text('fixed')
        (pkg/'run.sh').write_text('#!/bin/bash\nset -eu\ncd /work/package\nexport LD_LIBRARY_PATH=/work/package\nexport PATH=/work/package/bin:$PATH\nexec python3 -u maintenance_guest.py\n')
        with (out/'guest-runner.log').open('w') as log:
            subprocess.run([sys.executable,HERE.parent/'native/qemu.py','--package',pkg,'--output',out/'guest','--kernel','/boot/vkso-final-raw-normal-5.15.198.bzImage','--native-ide','--timeout','1200'],stdout=log,stderr=subprocess.STDOUT,check=True)
        evidence=json.loads((out/'guest/evidence/result.json').read_text());assert evidence['status']=='complete'
        for v in ['copied','shared']:
            e=evidence[v+'_negative'];assert e['client_errno']==errno.EIO and e['daemon_returncode']==0 and e['daemon_alive_after_read']
        n=evidence['native_negative'];assert n['errno']==errno.EIO or (n['errno']==0 and n['zero_filled'] and n['bytes']==len(result['fixture']['payload'].encode()))
        assert evidence['restored'] and evidence['modules_unloaded'] and len(evidence['native_regression'])==5
        result.update(status='complete',native_negative=n,copied=evidence['copied_negative'],shared=evidence['shared_negative'],restored=True,modules_unloaded=True)
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:write()
if __name__=='__main__':main()
