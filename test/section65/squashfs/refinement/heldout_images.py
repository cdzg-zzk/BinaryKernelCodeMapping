#!/usr/bin/env python3
"""Freeze a distribution Python byte-compilation workflow before its evaluation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[4]
SECTION=ROOT/'test/section65'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    tree=out/'rootfs'
    shutil.copytree(ROOT/'test/evaluation-local/runs/iso9660/squash-apptainer-copied-02/rootfs',tree,symlinks=True)
    interpreter=Path('/usr/bin/python3.10');stdlib=Path('/usr/lib/python3.10')
    shutil.copy2(interpreter,tree/'usr/bin/python3.10')
    shutil.copytree(stdlib,tree/'usr/lib/python3.10',symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    dependencies={}
    for binary in [interpreter,*stdlib.rglob('*.so')]:
        listing=subprocess.check_output(['ldd',binary],text=True)
        for name in re.findall(r'(/[^\s()]+)',listing):
            source=Path(name)
            if not source.is_file():continue
            target=tree/source.relative_to('/')
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():target.unlink()
            shutil.copy2(source,target)
            dependencies[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    sources={str(f.relative_to(tree)):hashlib.sha256(f.read_bytes()).hexdigest()
             for f in sorted((tree/'usr/lib/python3.10').rglob('*.py'))}
    result=dict(status='running',scope='Independent distribution byte-compilation task; not used to optimize the reader.',
        python_version=subprocess.check_output([interpreter,'--version'],text=True).strip(),
        python_sha256=hashlib.sha256(interpreter.read_bytes()).hexdigest(),
        stdlib_sources=sources,source_count=len(sources),dependencies=dependencies,cases=[],
        workload='PYTHONHASHSEED=0 PYTHONPYCACHEPREFIX=/work/pycache /usr/bin/python3.10 -m compileall -q -f --invalidation-mode checked-hash /usr/lib/python3.10',
        output_validation='Fresh writable cache for each timing; compare relative paths and SHA-256 of every generated .pyc against the stock backend oracle. Cache deletion and verification are outside timing.')
    write=lambda:(out/'images.json').write_text(json.dumps(result,indent=2)+'\n');write()
    app=SECTION/'build/squashfs/apptainer/jammy/usr/bin/apptainer'
    env=dict(os.environ,LD_LIBRARY_PATH=str(SECTION/'build/squashfs/apptainer/runtime/usr/lib/x86_64-linux-gnu'))
    for codec in ['gzip','xz']:
        image=out/(codec+'.sif')
        command=[str(app),'build','--mksquashfs-args',f'-comp {codec} -processors 1 -b 131072 -all-time 1700000000 -mkfs-time 1700000000',str(image),str(tree)]
        with (out/(codec+'-build.log')).open('w') as log:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        listing=subprocess.check_output([app,'sif','list',image],env=env,text=True)
        row=[line.split('|') for line in listing.splitlines() if 'FS (Squashfs/' in line];assert len(row)==1
        result['cases'].append(dict(compressor=codec,image=str(image),offset=int(row[0][3].strip().split('-')[0]),
            bytes=image.stat().st_size,sha256=hashlib.sha256(image.read_bytes()).hexdigest(),command=command))
        write();print('built held-out',codec,flush=True)
    result['status']='complete';write()


if __name__=='__main__':main()
