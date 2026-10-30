#!/usr/bin/env python3
"""Vary metadata population while retaining the same include-file distribution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[4]
SECTION=ROOT/'test/section65'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    base=ROOT/'test/evaluation-local/runs/iso9660/squash-apptainer-copied-02/rootfs'
    app=SECTION/'build/squashfs/apptainer/jammy/usr/bin/apptainer'
    env=dict(os.environ,LD_LIBRARY_PATH=str(SECTION/'build/squashfs/apptainer/runtime/usr/lib/x86_64-linux-gnu'))
    result=dict(status='running',scope='Metadata/cache growth, not a timing matrix. Independent copies of the same source tree retain identical per-file size/content distributions; SquashFS may deduplicate data blocks, but each replica has distinct directory entries and inodes.',cases=[])
    write=lambda:(out/'images.json').write_text(json.dumps(result,indent=2)+'\n');write()
    for scale in [1,4,16]:
        tree=out/f'root-{scale}';shutil.copytree(base,tree,symlinks=True)
        headers=tree/'opt/linux-headers';shutil.rmtree(headers);headers.mkdir()
        for index in range(scale):shutil.copytree(base/'opt/linux-headers',headers/f'tree-{index}',symlinks=True)
        count=sum(1 for _ in headers.rglob('*'))
        image=out/f'scale-{scale}.sif'
        argv=[str(app),'build','--mksquashfs-args','-comp xz -processors 1 -b 131072 -all-time 1700000000 -mkfs-time 1700000000',str(image),str(tree)]
        with (out/f'build-{scale}.log').open('w') as log:subprocess.run(argv,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        result['cases'].append(dict(scale=scale,entries=count,image=str(image),bytes=image.stat().st_size,
            sha256=hashlib.sha256(image.read_bytes()).hexdigest(),command=argv));write()
        print('built scale',scale,'entries',count,flush=True)
    result['status']='complete';write()


if __name__=='__main__':main()
