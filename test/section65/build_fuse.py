#!/usr/bin/env python3
"""Build the thin FUSE frontend with an extracted, versioned libfuse header package."""
from pathlib import Path
import json
import subprocess

HERE = Path(__file__).resolve().parent
OUT = HERE / 'build/fuse'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    headers=HERE/'build/fuse-deps/usr/include/fuse3'
    if not (headers/'fuse.h').exists():
        raise SystemExit('Extract libfuse3-dev into test/section65/build/fuse-deps first')
    command=['gcc','-std=gnu11','-O0','-g','-Wall','-Wextra','-Werror',
             '-I'+str(headers),str(HERE/'fuse_frontend.c'),'-Wl,-l:libfuse3.so.3',
             '-ldl','-o',str(OUT/'vkso-isofuse')]
    subprocess.run(command,check=True)
    (OUT/'build.json').write_text(json.dumps(dict(command=command,
        libfuse_version='3.10.5-1build1',scope='read-only single-threaded FUSE frontend'),indent=2)+'\n')

if __name__=='__main__': main()
