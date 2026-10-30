#!/usr/bin/env python3
"""Build real SIFs with the same small-file tree and larger sequential payloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
SECTION = HERE.parent
ROOT = SECTION.parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'test/evaluation-local/runs/iso9660/squash-apptainer-copied-02/rootfs')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--formats',nargs='+',default=['gzip','xz','lz4'])
    p.add_argument('--mib-per-file',type=int,default=128)
    a = p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    tree=out/'rootfs';shutil.copytree(a.source,tree,symlinks=True)
    data=tree/'opt/stream-data';data.mkdir()
    rng=random.Random(650031)
    pattern=(b'VKSO compressed filesystem sequential payload\n'*25000)[:1<<20]
    pattern=(pattern*((1<<20)//len(pattern)+1))[:1<<20]
    for name in ['compressible.bin','random.bin']:
        with (data/name).open('wb') as f:
            for _ in range(a.mib_per_file):f.write(pattern if name=='compressible.bin' else rng.randbytes(1<<20))
        os.utime(data/name,(1700000000,1700000000))
    app=SECTION/'build/squashfs/apptainer/jammy/usr/bin/apptainer'
    env=dict(os.environ,LD_LIBRARY_PATH=str(SECTION/'build/squashfs/apptainer/runtime/usr/lib/x86_64-linux-gnu'),
             APPTAINER_CACHEDIR=str(out/'cache'),APPTAINER_TMPDIR=str(out/'tmp'),APPTAINER_CONFIGDIR=str(out/'config'))
    for name in ['cache','tmp','config']:(out/name).mkdir()
    result=dict(status='running',source=str(a.source.resolve()),rootfs=str(tree),
                logical_stream_bytes=2*a.mib_per_file*(1<<20),payloads={},cases=[])
    for path in data.iterdir():
        h=hashlib.sha256()
        with path.open('rb') as f:
            while chunk:=f.read(1<<20):h.update(chunk)
        result['payloads'][path.name]=dict(bytes=path.stat().st_size,sha256=h.hexdigest())
    write=lambda:(out/'images.json').write_text(json.dumps(result,indent=2)+'\n')
    write()
    for codec in a.formats:
        image=out/(codec+'.sif')
        command=[str(app),'build','--mksquashfs-args',f'-comp {codec} -processors 1 -b 131072 -all-time 1700000000 -mkfs-time 1700000000',str(image),str(tree)]
        with (out/(codec+'-build.log')).open('w') as log:
            subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        listing=subprocess.check_output([app,'sif','list',image],env=env,text=True)
        rows=[line.split('|') for line in listing.splitlines() if 'FS (Squashfs/' in line]
        assert len(rows)==1
        offset=int(rows[0][3].strip().split('-')[0])
        result['cases'].append(dict(compressor=codec,image=str(image),offset=offset,
            bytes=image.stat().st_size,sha256=hashlib.sha256(image.read_bytes()).hexdigest(),command=command,partitions=listing))
        write();print('built SIF',codec,flush=True)
    result['status']='complete';write()


if __name__=='__main__':main()
