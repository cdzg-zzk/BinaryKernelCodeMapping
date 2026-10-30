#!/usr/bin/env python3
"""Build a separate LKL SIF frontend with one-second positive FUSE caches."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import traceback


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-build',type=Path,default=Path('test/section65/build/lkl/build-squash-only/sif-frontend'))
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=a.source_build.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    state=dict(status='running',purpose='Separate read-only-image cache-policy diagnostic; same LKL library and SIF offset adapter.')
    try:
        original=(source/'lklfuse.c').read_text();changed=original
        for field in ['entry_timeout','attr_timeout']:
            before='cfg->'+field+' = 0;';after='cfg->'+field+' = 1;'
            assert changed.count(before)==1;changed=changed.replace(before,after)
        changed=changed.replace('/* disable fuse lookup and attr caches */',
            '/* Match positive FUSE caches for the read-only image diagnostic. */')
        (out/'lklfuse.c').write_text(changed)
        (out/'cache.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),
            fromfile='default/lklfuse.c',tofile='cache-one-second/lklfuse.c')))
        command=json.loads((source/'build.json').read_text())['commands'][0]
        command=[str(out/'lklfuse.c') if token==str(source/'lklfuse.c') else
                 str(out/'lklfuse-cache') if token==str(source/'lklfuse') else token for token in command]
        assert str(out/'lklfuse-cache') in command
        with (out/'build.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        library=next(Path(t) for t in command if t.endswith('/liblkl.a'))
        state.update(status='complete',commands=[command],source=str(source),
            old_frontend_sha256=hashlib.sha256((source/'lklfuse').read_bytes()).hexdigest(),
            frontend_sha256=hashlib.sha256((out/'lklfuse-cache').read_bytes()).hexdigest(),
            lkl_library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
            policy=dict(entry_timeout=1,attr_timeout=1,negative_timeout=0),
            note='Only two assignments change. No filesystem/LKL core, memory size, threading or compiler-option change.')
    except BaseException:state.update(status='failed',error=traceback.format_exc());raise
    finally:(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')


if __name__=='__main__':main()
