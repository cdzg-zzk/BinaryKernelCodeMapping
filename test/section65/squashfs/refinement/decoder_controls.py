#!/usr/bin/env python3
"""Build decoder-path versus unused-library controls on one unchanged owner."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
HERE=ROOT/'test/section65/squashfs'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base=a.build.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    variants={'copied-library':['--bind-lz4','--bind-xz'],
              'copied-retained':['--shared-lz4','--shared-xz','--retain-lz4-dependency','--retain-xz-dependency']}
    rows=[];manifest={}
    for name,flags in variants.items():
        build=out/name;shutil.copytree(base,build)
        argv=[sys.executable,str(HERE/'build_user.py'),'--build',str(build),
            '--source-dir',str(base/'xz-user-source'),'--bridge-only','--directory-cache','--direct-decode',*flags]
        with (out/(name+'.log')).open('w') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True)
        for binary in ['vkso_sq_core.ko','vkso_squashfs.ko','vkso-squashfuse','vkso-squash-helper']:
            assert (build/binary).read_bytes()==(base/binary).read_bytes(),binary
        needed=subprocess.check_output(['readelf','-d',build/'libsq-bridge.so'],text=True)
        assert 'liblz4' in needed and 'liblzma' in needed
        rows.append(dict(variant=name,argv=argv,bridge_sha256=hashlib.sha256((build/'libsq-bridge.so').read_bytes()).hexdigest(),dynamic=needed))
        manifest[name]={'build':str(build)}
    (out/'readers.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'result.json').write_text(json.dumps(dict(status='complete',controls=rows,
        interpretation='Library/common-retained compares decoder execution with both external libraries retained. Common-retained/common compares dependency retention with the same decoder path. All variants bind both private service tables and materialize the same owner instructions; no claim of identical linker layout.'),indent=2)+'\n')
    print('built two decoder/dependency controls')


if __name__=='__main__':main()
