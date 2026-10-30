#!/usr/bin/env python3
"""Compose an existing adapted LZ4 safe block decoder with the filesystem owner."""
import argparse, hashlib, json
from pathlib import Path
import shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[4];HERE=ROOT/'test/section65/squashfs'
sys.path.insert(0,str(HERE));from prepare import span

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--base',type=Path,default=ROOT/'test/section65/build/squashfs/improve-native-small-copy-01');a=p.parse_args()
    out=a.output.resolve();shutil.copytree(a.base,out)
    original=ROOT/'test/test_lz4/kmod';text=(original/'lz4_decompress.c').read_text()
    _,end=span(text,'LZ4_decompress_safe');text=text[:end]+'\n'
    text=text.replace('int LZ4_decompress_safe(', 'int vkso_LZ4_decompress_safe(')
    text+='''
/* Private per-domain helper slots; no extra owner or registration instance. */
void *(*vkso_lz4_memcpy_slot)(void *, const void *, size_t);
void *(*vkso_lz4_memmove_slot)(void *, const void *, size_t);
void *(*vkso_lz4_memset_slot)(void *, int, size_t);
void sq_bind_lz4(void *(*copy)(void *, const void *, size_t),
                 void *(*move)(void *, const void *, size_t),
                 void *(*set)(void *, int, size_t))
{
    vkso_lz4_memcpy_slot=copy;
    vkso_lz4_memmove_slot=move;
    vkso_lz4_memset_slot=set;
}
'''
    (out/'shared_lz4.c').write_text(text);shutil.copy2(original/'lz4defs.h',out/'lz4defs.h')
    declarations='''
extern int vkso_LZ4_decompress_safe(const char *,char *,int,int);
extern void sq_bind_lz4(void *(*)(void *,const void *,size_t),
                        void *(*)(void *,const void *,size_t),
                        void *(*)(void *,int,size_t));
'''
    with (out/'core_metadata.c').open('a') as f:f.write(declarations+'EXPORT_SYMBOL_GPL(vkso_LZ4_decompress_safe);\nEXPORT_SYMBOL_GPL(sq_bind_lz4);\n')
    pth=out/'kernel_support.c';s=pth.read_text();s=s.replace('void sq_owner_bind(void) { sq_bind_support(&bindings); }',declarations+'void sq_owner_bind(void) { sq_bind_support(&bindings); sq_bind_lz4(memcpy,memmove,memset); }');pth.write_text(s)
    pth=out/'lz4_wrapper.c';s=pth.read_text();s=s.replace('#include <linux/lz4.h>','#include <linux/lz4.h>\n'+declarations).replace('res = LZ4_decompress_safe(', 'res = vkso_LZ4_decompress_safe(');pth.write_text(s)
    make=(out/'Makefile').read_text();make=make.replace('vkso_sq_core-y := shared_core.o core_metadata.o','vkso_sq_core-y := shared_core.o shared_lz4.o core_metadata.o')
    make+='\n'+'\n'.join(line.replace('shared_core.o','shared_lz4.o') for line in make.splitlines() if line.startswith(('CFLAGS_REMOVE_shared_core.o','CFLAGS_shared_core.o','UBSAN_SANITIZE_shared_core.o')))+'\n';(out/'Makefile').write_text(make)
    with (out/'symbols.txt').open('a') as f:f.write('\nvkso_LZ4_decompress_safe\nsq_bind_lz4\n')
    with (out/'codec-build.log').open('w') as log:subprocess.run(['make','-C',str(ROOT/'test/section65/build/native/kernel'),'M='+str(out),'-j2','modules'],stdout=log,stderr=subprocess.STDOUT,check=True)
    undefined=subprocess.check_output(['nm','-u',out/'shared_lz4.o'],text=True);assert not undefined.strip(),undefined
    source=out/'codec-user-source';source.mkdir()
    for name in ['user_bridge.c','posix_io.c','fuse_frontend.c','apptainer_helper.c','profile.h']:shutil.copy2(HERE/name,source/name)
    with (out/'codec-user-build.log').open('w') as log:subprocess.run([sys.executable,HERE/'build_user.py','--build',out,'--source-dir',source,'--bridge-only','--directory-cache','--direct-decode','--shared-lz4'],stdout=log,stderr=subprocess.STDOUT,check=True)
    needed=subprocess.check_output(['readelf','-d',out/'libsq-bridge.so'],text=True);assert 'liblz4' not in needed
    (out/'codec-candidate.json').write_text(json.dumps(dict(status='built',scope='Existing shared owner also implements safe LZ4 block decompression for native and user consumers.',
        base=str(a.base.resolve()),source=str(original),adaptation='Reuse existing generic decoder and safe entry; omit unused API entry points; bind three existing memory-service slots separately per domain.',
        undefined_codec_symbols=[],user_dynamic_dependencies=needed,
        hashes={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['vkso_sq_core.ko','vkso_squashfs.ko','shared_lz4.c','lz4defs.h','libsq-bridge.so','vkso-squashfuse']}),indent=2)+'\n')
    print('built',out)
if __name__=='__main__':main()
