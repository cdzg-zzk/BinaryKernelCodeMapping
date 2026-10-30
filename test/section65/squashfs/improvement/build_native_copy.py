#!/usr/bin/env python3
"""Single-factor candidate: inline variable-size copying inside the shared core."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
from prepare import span


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--force-inline',action='store_true',help='force x86 string operations inline, preserving the closed dependency set')
    p.add_argument('--small-copy',action='store_true',help='inline only bounded copies up to 16 bytes; keep service fallback')
    a=p.parse_args();out=a.output.resolve()
    original=ROOT/'test/evaluation-local/runs/iso9660/squash-maintenance-02/fixed-build'
    shutil.copytree(original,out)
    source=out/'shared_core.c';text=source.read_text();start,end=span(text,'squashfs_copy_data')
    body=text[start:end];assert body.count('memcpy(')==2
    assert not (a.force_inline and a.small_copy)
    helper=''
    if a.small_copy:
        helper='''/* Bounded small copies: constant loads/stores, no overread, same in both domains. */
static __always_inline void sq_metadata_copy(void *dst, const void *src, size_t n)
{
    char *d = dst;
    const char *s = src;
    if (n > 16) {
        memcpy(dst, src, n);
    } else if (n >= 8) {
        __builtin_memcpy(d, s, 8);
        __builtin_memcpy(d + n - 8, s + n - 8, 8);
    } else if (n >= 4) {
        __builtin_memcpy(d, s, 4);
        __builtin_memcpy(d + n - 4, s + n - 4, 4);
    } else if (n >= 2) {
        __builtin_memcpy(d, s, 2);
        __builtin_memcpy(d + n - 2, s + n - 2, 2);
    } else if (n) {
        *d = *s;
    }
}

'''
    changed=body.replace('memcpy(','sq_metadata_copy(' if a.small_copy else '__builtin_memcpy(')
    source.write_text(text[:start]+helper+changed+text[end:])
    if a.force_inline:
        with (out/'Makefile').open('a') as stream:stream.write('\nCFLAGS_shared_core.o += -minline-all-stringops\n')
    with (out/'candidate-build.log').open('w') as log:
        subprocess.run(['make','-C',str(ROOT/'test/section65/build/native/kernel'),'M='+str(out),'-j2','modules'],stdout=log,stderr=subprocess.STDOUT,check=True)
    undefined=subprocess.check_output(['nm','-u',str(out/'shared_core.o')],text=True)
    assert [line.split()[-1] for line in undefined.splitlines()]==['sq_support'],undefined
    asm=subprocess.check_output(['objdump','-dr','--disassemble=squashfs_copy_data',str(out/'shared_core.o')],text=True)
    (out/'copy-data.asm').write_text(asm)
    baseline=ROOT/'test/section65/build/squashfs/evaluation-fixed-01/build'
    for name in ['libsq-bridge.so','vkso-squashfuse','vkso-squash-helper']:
        shutil.copy2(baseline/name,out/name)
    result=dict(status='built',scope='Common owner changes for both domains; original service-table ABI and user binaries retained.',
        change=('Both runtime-size memcpy sites use an inline bounded <=16-byte copy and the existing service for larger copies.' if a.small_copy else 'Both runtime-size memcpy sites in squashfs_copy_data change from service binding to compiler builtin. Existing constant-size builtin optimization is unchanged.'),
        before=body,after=helper+changed,force_inline=a.force_inline,small_copy=a.small_copy,undefined=['sq_support'],
        hashes={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse']})
    (out/'candidate.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='built',path=str(out))))


if __name__=='__main__':main()
