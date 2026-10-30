#!/usr/bin/env python3
"""Compose matching Linux XZ bodies into the existing filesystem/LZ4 owner."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
HERE = ROOT / 'test/section65/squashfs'
LINUX = ROOT / 'test/section65/build/native/linux-5.15.198'
PUBLIC = ['xz_dec_init', 'xz_dec_reset', 'xz_dec_run', 'xz_dec_end']
NAMES = PUBLIC + ['xz_dec_lzma2_create', 'xz_dec_lzma2_reset',
                 'xz_dec_lzma2_run', 'xz_dec_lzma2_end', 'xz_dec_bcj_create',
                 'xz_dec_bcj_reset', 'xz_dec_bcj_run', 'xz_crc32']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=ROOT/'test/section65/build/squashfs/evaluation-improved-01/build')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    shutil.copytree(a.base, out)
    result = dict(status='building', base=str(a.base.resolve()),
                  source=str(LINUX), original_decoder_sources=[])
    def save():
        (out/'xz-composition.json').write_text(json.dumps(result, indent=2)+'\n')
    save()
    try:
        names = ''.join(f'#define {n} vkso_{n}\n' for n in NAMES)
        (out/'xz_names.h').write_text(names+'#define XZ_INTERNAL_CRC32 1\n')
        api = (LINUX/'include/linux/xz.h').read_text()
        (out/'sq_xz_api.h').write_text('#include "xz_names.h"\n'+api)
        shutil.copy2(Path(__file__).with_name('xz_services.h'), out/'xz_services.h')
        objects = []
        for name in ['xz_dec_stream', 'xz_dec_lzma2', 'xz_dec_bcj']:
            source = LINUX/'lib/xz'/(name+'.c')
            shutil.copy2(source, out/(name+'.c'))
            objects.append(name+'.o')
            result['original_decoder_sources'].append(dict(
                path=str(source), physical_lines=len(source.read_text().splitlines()),
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(), body_edits=0))
        for name in ['xz_lzma2.h', 'xz_stream.h', 'xz_private.h']:
            shutil.copy2(LINUX/'lib/xz'/name, out/name)
        with (out/'xz_private.h').open('a') as f:
            f.write('''
/* Bind environment services after the original kernel header declarations. */
#include "xz_services.h"
#undef kmalloc
#define kmalloc(n, flags) (sq_xz_services.alloc)(n)
#define vmalloc(n) (sq_xz_services.valloc)(n)
#define kfree(p) (sq_xz_services.free)(p)
#define vfree(p) (sq_xz_services.vfree)(p)
#undef memcpy
#undef memmove
#undef memset
#undef memcmp
#define memcpy(d,s,n) (sq_xz_services.copy)(d,s,n)
#define memmove(d,s,n) (sq_xz_services.move)(d,s,n)
#define memset(d,c,n) (sq_xz_services.set)(d,c,n)
#define memcmp(a,b,n) (sq_xz_services.compare)(a,b,n)
''')
        (out/'xz_support.c').write_text('''
#include "xz_services.h"
struct sq_xz_services sq_xz_services;
void sq_bind_xz(const struct sq_xz_services *services)
{
    sq_xz_services = *services;
}
void *sq_xz_support_address(void) { return &sq_xz_services; }
uint32_t vkso_xz_crc32(const uint8_t *buf, size_t size, uint32_t crc)
{
    return sq_xz_services.crc32(buf, size, crc);
}
''')
        objects.append('xz_support.o')
        path = out/'xz_wrapper.c'
        path.write_text(path.read_text().replace('#include <linux/xz.h>', '#include "sq_xz_api.h"'))
        path = out/'kernel_support.c'
        text = path.read_text()
        binding = '''
#include <linux/vmalloc.h>
#include <linux/crc32.h>
#include "xz_services.h"
static void *sq_xz_alloc(size_t n) { return kmalloc(n, GFP_KERNEL); }
static uint32_t sq_xz_crc(const uint8_t *buf, size_t n, uint32_t crc)
{ return ~crc32_le(~crc, buf, n); }
static const struct sq_xz_services xz_bindings = {
    .alloc=sq_xz_alloc, .valloc=vmalloc, .free=kfree, .vfree=vfree,
    .copy=memcpy, .move=memmove, .set=memset, .compare=memcmp, .crc32=sq_xz_crc,
};
'''
        anchor = 'void sq_owner_bind(void) { sq_bind_support(&bindings); sq_bind_lz4(memcpy,memmove,memset); }'
        assert anchor in text
        path.write_text(text.replace(anchor, binding+anchor.replace('); }', '); sq_bind_xz(&xz_bindings); }')))
        with (out/'core_metadata.c').open('a') as f:
            f.write('\n#include "xz_services.h"\n')
            for n in [*['vkso_'+n for n in PUBLIC], 'sq_bind_xz', 'sq_xz_support_address']:
                f.write(f'EXPORT_SYMBOL_GPL({n});\n')
        with (out/'symbols.txt').open('a') as f:
            f.write('\n'+'\n'.join([*['vkso_'+n for n in PUBLIC], 'sq_bind_xz', 'sq_xz_support_address'])+'\n')
        path = out/'Makefile'
        text = path.read_text()
        text = text.replace('shared_core.o shared_lz4.o core_metadata.o',
                            'shared_core.o shared_lz4.o '+' '.join(objects)+' core_metadata.o')
        flags = [s for s in text.splitlines() if s.startswith(('CFLAGS_REMOVE_shared_core.o', 'CFLAGS_shared_core.o', 'UBSAN_SANITIZE_shared_core.o'))]
        for obj in objects:
            text += '\n'+'\n'.join(s.replace('shared_core.o', obj) for s in flags)+'\n'
            text += f'CFLAGS_{obj} += -include {out}/xz_names.h\n'
        path.write_text(text)
        with (out/'xz-build.log').open('w') as log:
            subprocess.run(['make', '-C', ROOT/'test/section65/build/native/kernel',
                            'M='+str(out), '-j2', 'modules'], stdout=log, stderr=subprocess.STDOUT, check=True)
        undefined = subprocess.check_output(['nm', '-u', out/'vkso_sq_core.ko'], text=True)
        result['undefined_owner_symbols'] = undefined
        # The owner module metadata may refer to kernel runtime, but shared objects
        # must only refer to their explicitly bound tables or the common XZ bodies.
        for obj in objects:
            symbols = [line.split()[-1] for line in subprocess.check_output(['nm','-u',out/obj],text=True).splitlines()]
            assert all(n=='sq_xz_services' or n.startswith('vkso_xz_') for n in symbols), (obj,symbols)
        source = out/'xz-user-source'
        source.mkdir()
        for name in ['user_bridge.c','posix_io.c','fuse_frontend.c','apptainer_helper.c','profile.h']:
            shutil.copy2(HERE/name, source/name)
        with (out/'xz-user-build.log').open('w') as log:
            subprocess.run([sys.executable, HERE/'build_user.py', '--build', out,
                            '--source-dir', source, '--bridge-only', '--directory-cache',
                            '--direct-decode', '--shared-lz4', '--shared-xz'],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        needed = subprocess.check_output(['readelf','-d',out/'libsq-bridge.so'],text=True)
        assert 'liblzma' not in needed and 'liblz4' not in needed
        result.update(status='built', public_exports=PUBLIC, private_services=9,
                      original_decoder_physical_lines=sum(r['physical_lines'] for r in result['original_decoder_sources']),
                      user_dependencies=needed,
                      hashes={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in
                              ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse']})
        print('built',out,result['original_decoder_physical_lines'],'unchanged decoder source lines')
    except BaseException as exc:
        result.update(status='failed', error=repr(exc))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
