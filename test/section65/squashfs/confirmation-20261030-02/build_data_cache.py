#!/usr/bin/env python3
"""Finite data-cache capacity controls, identical owner and existing semantics."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from prerequisite import ROOT, RUNS, verify

SECTION=ROOT/'test/section65'
BASE=RUNS/'builds/optimization-cache-01'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    verify();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    reads={};records=[]
    for capacity in [16,48]:
        dest=out/f'data-{capacity}';shutil.copytree(BASE,dest)
        path=dest/'xz-user-source/user_bridge.c';before=path.read_text();text=before
        old='    c->entries=entries; c->block_size=blocksize;'
        assert text.count(old)==1
        text=text.replace(old,f'    if (!strcmp(name,"data")) entries={capacity}; /* Bounded private data working set. */\n'+old)
        # Keep unused slots free of backing buffers: memory follows touched
        # slots up to the explicit cap. Metadata and fragment policy unchanged.
        old='''        e->data[0]=malloc(c->pages*PAGE_SIZE);
        if (!e->data[0]) goto fail;
        for (j=1;j<c->pages;j++) e->data[j]=(char *)e->data[0]+j*PAGE_SIZE;
        e->actor=u_actor(e->data,c->pages,blocksize);
        if (!e->actor) goto fail;'''
        assert text.count(old)==1
        text=text.replace(old,'''        if (strcmp(name,"data")) {
'''+old+'''
        }''')
        old='''        SQ_COUNT(cache_misses,1);
        e->block=block; e->refcount=1;'''
        assert text.count(old)==1
        new='''        SQ_COUNT(cache_misses,1);
        if (!e->data[0]) {
            int j;
            e->data[0]=malloc(c->pages*PAGE_SIZE);
            if (!e->data[0]) { image_of(sb)->busy.error=-ENOMEM;return &image_of(sb)->busy; }
            for(j=1;j<c->pages;j++) e->data[j]=(char *)e->data[0]+j*PAGE_SIZE;
            e->actor=u_actor(e->data,c->pages,c->block_size);
            if (!e->actor) { free(e->data[0]);e->data[0]=NULL;image_of(sb)->busy.error=-ENOMEM;return &image_of(sb)->busy; }
        }
        e->block=block; e->refcount=1;'''
        text=text.replace(old,new);path.write_text(text)
        (dest/'private-data-cache.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='word-cache/user_bridge.c',tofile=f'data-{capacity}/user_bridge.c')))
        args=[sys.executable,str(SECTION/'squashfs/build_user.py'),'--build',str(dest),'--source-dir',str(dest/'xz-user-source'),'--directory-cache','--direct-decode','--shared-lz4','--shared-xz']
        with (out/f'build-{capacity}.log').open('w') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
        for name in ['vkso_sq_core.ko','vkso_squashfs.ko']:
            assert sha(BASE/name)==sha(dest/name)
        reads[f'copied-data{capacity}']={'build':str(dest)}
        records.append(dict(capacity=capacity,data_byte_cap=capacity*131072,metadata_entries=8,fragment_entries=3,
                            same_owner_sha256=sha(dest/'vkso_sq_core.ko'),bridge_sha256=sha(dest/'libsq-bridge.so'),
                            source_sha256=sha(path),argv=args))
    (out/'readers.json').write_text(json.dumps(reads,indent=2)+'\n')
    (out/'result.json').write_text(json.dumps(dict(status='built',variants=records,
        rationale='Original Python request trace: 190 data-cache requests, 97 unique blocks, 168 misses at capacity 1; offline FIFO replay predicts 114 at 16 and 98 at 48. 16 caps data at 2 MiB; 48 matches the multithread-built SquashFUSE data slot count. No fragment-capacity, codec, kernel page-cache or workload changes. Memory cost must be measured alongside runtime.',
        scope='Two explicit candidates, not production promotion. Same resident core, private adapter change only.'),indent=2)+'\n')
    print('Built data-cache controls 16 and 48; identical owner')

if __name__=='__main__':main()
