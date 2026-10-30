#!/usr/bin/env python3
"""Prepare a shared SquashFS format core and retain a native filesystem caller.

This is implementation scaffolding, not evidence that the user adapter works.
Input sources remain untouched. Generated patches account for each boundary.
"""
import argparse
import difflib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
SECTION = HERE.parent
ROOT = SECTION.parents[1]
spec = importlib.util.spec_from_file_location('iso_extraction', SECTION / 'adapt.py')
iso = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iso)

FUNCTIONS = {
    'super.c': ['supported_squashfs_filesystem', 'squashfs_fill_super'],
    'inode.c': ['squashfs_new_inode', 'squashfs_read_inode'],
    'namei.c': ['get_dir_index_using_name', 'squashfs_lookup'],
    'dir.c': ['get_dir_index_using_offset', 'squashfs_readdir'],
    'file.c': ['locate_meta_index', 'empty_meta_index', 'release_meta_index',
               'read_indexes', 'calculate_skip', 'fill_meta_index', 'read_blocklist'],
    'cache.c': ['squashfs_copy_data', 'squashfs_read_metadata',
                'squashfs_get_fragment', 'squashfs_get_datablock', 'squashfs_read_table'],
    'fragment.c': ['squashfs_frag_lookup', 'squashfs_read_fragment_index_table'],
    'id.c': ['squashfs_get_id', 'squashfs_read_id_index_table'],
    'export.c': ['squashfs_read_inode_lookup_table'],
    'xattr_id.c': ['squashfs_xattr_lookup', 'squashfs_read_xattr_id_table'],
    'block.c': ['squashfs_read_data'],
    'decompressor.c': ['get_comp_opts', 'squashfs_decompressor_setup'],
    'xz_wrapper.c': ['squashfs_xz_comp_opts'],
    'lz4_wrapper.c': ['lz4_comp_opts'],
    'xattr.c': ['squashfs_listxattr', 'squashfs_xattr_get'],
}
PUBLIC_STATIC = {'squashfs_fill_super', 'squashfs_lookup', 'squashfs_readdir', 'read_blocklist',
                 'squashfs_xz_comp_opts', 'lz4_comp_opts', 'squashfs_xattr_get'}

# The domain adapter owns every mutable object reached through these services.
# Native bindings retain native allocation, cache synchronization, BIOs and
# existing decompressor workspaces. No native buffer flattening is introduced.
SERVICES = [
    ('alloc', 'void *', 'size_t, gfp_t', '__kmalloc'),
    ('alloc_array', 'void *', 'size_t, size_t, gfp_t', 'sq_kernel_array'),
    ('free', 'void', 'const void *', 'kfree'),
    ('mutex_init', 'void', 'struct mutex *', 'sq_kernel_mutex_init'),
    ('mutex_lock', 'void', 'struct mutex *', 'mutex_lock'),
    ('mutex_unlock', 'void', 'struct mutex *', 'mutex_unlock'),
    ('cache_init', 'struct squashfs_cache *', 'char *, int, int', 'squashfs_cache_init'),
    ('cache_delete', 'void', 'struct squashfs_cache *', 'squashfs_cache_delete'),
    ('cache_get', 'struct squashfs_cache_entry *', 'struct super_block *, struct squashfs_cache *, u64, int', 'squashfs_cache_get'),
    ('cache_put', 'void', 'struct squashfs_cache_entry *', 'squashfs_cache_put'),
    ('actor_init', 'struct squashfs_page_actor *', 'void **, int, int', 'sq_kernel_actor'),
    ('iget', 'struct inode *', 'struct super_block *, long long, unsigned int', 'squashfs_iget'),
    ('new_inode', 'struct inode *', 'struct super_block *', 'new_inode'),
    ('bad_inode', 'void', 'struct inode *', 'make_bad_inode'),
    ('insert_inode', 'void', 'struct inode *', 'sq_kernel_insert'),
    ('iput', 'void', 'struct inode *', 'iput'),
    ('nlink', 'void', 'struct inode *, unsigned int', 'set_nlink'),
    ('uid', 'void', 'struct inode *, uid_t', 'sq_kernel_uid'),
    ('gid', 'void', 'struct inode *, gid_t', 'sq_kernel_gid'),
    ('special_inode', 'void', 'struct inode *, umode_t, dev_t', 'init_special_inode'),
    ('nohighmem', 'void', 'struct inode *', 'sq_kernel_nohighmem'),
    ('blocksize', 'int', 'struct super_block *, int', 'sb_min_blocksize'),
    ('device_size', 'loff_t', 'struct super_block *', 'sq_kernel_device_size'),
    ('make_root', 'struct dentry *', 'struct inode *', 'd_make_root'),
    ('splice_alias', 'struct dentry *', 'struct inode *, struct dentry *', 'd_splice_alias'),
    ('lookup_decompressor', 'const struct squashfs_decompressor *', 'int', 'squashfs_lookup_decompressor'),
    ('max_decompressors', 'int', 'void', 'squashfs_max_decompressors'),
    ('decompressor_create', 'void *', 'struct squashfs_sb_info *, void *', 'squashfs_decompressor_create'),
    ('decompressor_destroy', 'void', 'struct squashfs_sb_info *', 'squashfs_decompressor_destroy'),
    ('read_raw', 'int', 'struct super_block *, u64, int, struct bio **, int *', 'squashfs_bio_read'),
    ('input_byte', 'int', 'struct bio *, int', 'sq_kernel_input_byte'),
    ('free_raw', 'void', 'struct bio *', 'sq_kernel_free_raw'),
    ('decompress', 'int', 'struct squashfs_sb_info *, struct bio *, int, int, struct squashfs_page_actor *', 'squashfs_decompress'),
    ('copy_raw', 'int', 'struct bio *, struct squashfs_page_actor *, int, int', 'copy_bio_to_actor'),
    ('error', 'void', 'struct fs_context *, const char *, ...', 'sq_kernel_error'),
    ('print', 'int', 'const char *, ...', '_printk'),
    ('dynamic_debug', 'void', 'struct _ddebug *, const char *, ...', '__dynamic_pr_debug'),
    ('fatal', 'void', 'const char *', 'sq_kernel_fatal'),
    ('memcpy', 'void *', 'void *, const void *, size_t', 'memcpy'),
    ('memset', 'void *', 'void *, int, size_t', 'memset'),
    ('memcmp', 'int', 'const void *, const void *, size_t', 'memcmp'),
    ('strcmp', 'int', 'const char *, const char *', 'strcmp'),
    ('strncmp', 'int', 'const char *, const char *, size_t', 'strncmp'),
    ('strncpy', 'char *', 'char *, const char *, size_t', 'strncpy'),
    ('strlen', 'size_t', 'const char *', 'strlen'),
    ('xattr_handler', 'const struct xattr_handler *', 'int', 'squashfs_xattr_handler'),
]
DATA = [
    ('super_ops', 'const struct super_operations *', 'squashfs_super_ops', True),
    ('export_ops', 'const struct export_operations *', 'squashfs_export_ops', True),
    ('xattr_handlers', 'const struct xattr_handler **', 'squashfs_xattr_handlers', False),
    ('ro_fops', 'const struct file_operations *', 'generic_ro_fops', True),
    ('inode_ops', 'const struct inode_operations *', 'squashfs_inode_ops', True),
    ('dir_inode_ops', 'const struct inode_operations *', 'squashfs_dir_inode_ops', True),
    ('dir_ops', 'const struct file_operations *', 'squashfs_dir_ops', True),
    ('symlink_ops', 'const struct inode_operations *', 'squashfs_symlink_inode_ops', True),
    ('symlink_aops', 'const struct address_space_operations *', 'squashfs_symlink_aops', True),
    ('aops', 'const struct address_space_operations *', 'squashfs_aops', True),
]

INCLUDES = '''#include <linux/slab.h>
#include <linux/blkdev.h>
#include <linux/bio.h>
#include <linux/fs_context.h>
#include <linux/pagemap.h>
#include <linux/magic.h>
#include <linux/xattr.h>
#include "squashfs_fs.h"
#include "squashfs_fs_sb.h"
#include "squashfs_fs_i.h"
#include "squashfs.h"
#include "decompressor.h"
#include "page_actor.h"
#include "xattr.h"
'''


def span(text, name):
    # SquashFS also returns typedefs such as __le64; the ISO extractor's
    # restricted list of C return-type keywords does not cover those.
    pattern = r'(?m)^(?:[A-Za-z_]\w*[\t *]+)+\**' + re.escape(name) + r'\s*\([^;{}]*\)\s*\{'
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError((name, len(matches)))
    start, brace = matches[0].start(), matches[0].end() - 1
    depth = 0
    for token in re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', text[brace:], re.S):
        if token[0] == '{': depth += 1
        elif token[0] == '}':
            depth -= 1
            if depth == 0: return start, brace + token.end()
    raise ValueError('unterminated ' + name)


def prepare(source, output):
    original = {p.name: p.read_text() for p in source.iterdir() if p.suffix in ('.c', '.h')}
    kernel = dict(original)
    options = re.search(r'enum Opt_errors \{.*?\n};', original['super.c'], re.S)[0]
    options += '\n' + re.search(r'struct squashfs_mount_opts \{.*?\n};', original['super.c'], re.S)[0]
    for part in [re.search(r'enum Opt_errors \{.*?\n};', original['super.c'], re.S)[0],
                 re.search(r'struct squashfs_mount_opts \{.*?\n};', original['super.c'], re.S)[0]]:
        kernel['super.c'] = iso.once(kernel['super.c'], part, '')
    shared, public, private, accounting = [], [], [], []
    for filename, functions in FUNCTIONS.items():
        for name in functions:
            start, end = span(kernel[filename], name)
            old = kernel[filename][start:end]
            local = old.startswith('static ') and name not in PUBLIC_STATIC
            body = old if local else re.sub(r'^static\s+', '', old)
            if name == 'squashfs_fill_super':
                body = iso.once(body, 'i_size_read(sb->s_bdev->bd_inode)', 'sq_support.device_size(sb)')
            if name == 'squashfs_read_data':
                body = iso.once(body, '\t\tconst u8 *data;\n\t\tstruct bvec_iter_all iter_all = {};\n\t\tstruct bio_vec *bvec = bvec_init_iter_all(&iter_all);',
                                '\t\tint low, high;')
                a = body.index('\t\tif (WARN_ON_ONCE(!bio_next_segment(')
                b = body.index('\n\t\tcompressed =', a)
                body = body[:a] + '''\t\tlow = sq_support.input_byte(bio, offset);
\t\thigh = sq_support.input_byte(bio, offset + 1);
\t\tif (low < 0 || high < 0) {
\t\t\tres = -EIO;
\t\t\tgoto out_free_bio;
\t\t}
\t\tlength = low | (high << 8);
\t\tsq_support.free_raw(bio);
''' + body[b:]
                body = iso.once(body, '\tbio_free_pages(bio);\n\tbio_put(bio);', '\tsq_support.free_raw(bio);')
                body = iso.once(body, 'panic("squashfs read failed")', 'sq_support.fatal("squashfs read failed")')
            declaration = body[:body.index('{')].strip() + ';'
            (private if local else public).append((name, declaration))
            kernel[filename] = kernel[filename][:start] + ('' if local else declaration) + kernel[filename][end:]
            shared.append(body)
            accounting.append(dict(source=filename, function=name, private=local,
                original_lines=len(old.splitlines()), common_lines=len(body.splitlines()),
                body_edited=re.sub(r'^static\s+', '', old) != re.sub(r'^static\s+', '', body)))

    output.mkdir(parents=True, exist_ok=True)
    types = '#ifndef SQ_SHARED_TYPES_H\n#define SQ_SHARED_TYPES_H\n'
    types += 'struct fs_context;\nstruct bio;\nstruct squashfs_decompressor;\n'
    types += options + '\nstruct sq_support {\n'
    types += ''.join(f'    {ret} (*{field})({params});\n' for field, ret, params, _ in SERVICES)
    types += ''.join(f'    {kind} {field};\n' for field, kind, _, _ in DATA)
    types += '};\nextern struct sq_support sq_support;\n'
    types += 'void sq_bind_support(const struct sq_support *);\nstruct sq_support *sq_support_address(void);\n'
    types += '\n'.join(d for _, d in public) + '\n#endif\n'
    (output / 'shared_types.h').write_text(types)
    kernel['squashfs.h'] += '\n#include "shared_types.h"\n'
    # Expose only native helpers needed to populate the domain service table.
    kernel['super.c'] = kernel['super.c'].replace('static const struct super_operations squashfs_super_ops',
                                                 'const struct super_operations squashfs_super_ops')
    for name in ('copy_bio_to_actor', 'squashfs_bio_read'):
        kernel['block.c'] = iso.once(kernel['block.c'], 'static int ' + name, 'int ' + name)
    kernel['xattr.c'] = kernel['xattr.c'].replace('static const struct xattr_handler *squashfs_xattr_handler',
                                               'const struct xattr_handler *squashfs_xattr_handler')
    kernel['block.c'] += '''
/* Opaque input access preserves the native BIO pages and decompressor API. */
int sq_kernel_input_byte(struct bio *bio, int offset)
{
    struct bio_vec *bv;
    struct bvec_iter_all iter;
    bio_for_each_segment_all(bv, bio, iter) {
        if (offset < bv->bv_len) return ((const u8 *)bvec_virt(bv))[offset];
        offset -= bv->bv_len;
    }
    return -EIO;
}
void sq_kernel_free_raw(struct bio *bio) { bio_free_pages(bio); bio_put(bio); }
'''
    kernel['super.c'] = iso.once(kernel['super.c'], '.name = "squashfs",', '.name = "vksosquash",')
    kernel['super.c'] = iso.once(kernel['super.c'], 'static int __init init_squashfs_fs(void)\n{',
        'extern void sq_owner_bind(void);\nstatic int __init init_squashfs_fs(void)\n{')
    kernel['super.c'] = iso.once(kernel['super.c'], 'int err = init_inodecache();',
                                'int err = init_inodecache();\n\tsq_owner_bind();')
    kernel['super.c'] = kernel['super.c'].replace('"squashfs_inode_cache"', '"vkso_sq_inode_cache"')
    kernel['super.c'] = kernel['super.c'].replace('MODULE_ALIAS_FS("squashfs")', 'MODULE_ALIAS_FS("vksosquash")')
    # The on-disk file-type table belongs with the moved directory parser.
    table = re.search(r'static const unsigned char squashfs_filetype_table\[\] = \{.*?\n};', original['dir.c'], re.S)[0]
    kernel['dir.c'] = iso.once(kernel['dir.c'], table, '')
    bind = 'void sq_bind_support(const struct sq_support *s)\n{\n'
    bind += ''.join(f'    sq_support.{row[0]} = s->{row[0]};\n' for row in SERVICES + DATA)
    bind += '}\nstruct sq_support *sq_support_address(void) { return &sq_support; }\n'
    notice = '// SPDX-License-Identifier: GPL-2.0-or-later\n/* Linux 5.15.198 SquashFS functions; original notices retained in generated source files. */\n'
    compressor_types = ''.join(re.search(r'struct ' + name + r' \{.*?\n};', original[file], re.S)[0] + '\n'
        for file, name in [('xz_wrapper.c', 'disk_comp_opts'), ('xz_wrapper.c', 'comp_opts'), ('lz4_wrapper.c', 'lz4_comp_opts')])
    compressor_types += '#define LZ4_LEGACY 1\n'
    (output / 'shared_core.c').write_text(notice + INCLUDES + '#include "shared_remap.h"\n' + table + '\n' + compressor_types +
        '\n'.join(d for _, d in private) + '\n\n' + '\n\n'.join(shared) + '\n' + bind)

    replacements = {
        'kmalloc': 'alloc', 'kfree': 'free', 'kcalloc': 'alloc_array',
        'mutex_lock': 'mutex_lock', 'mutex_unlock': 'mutex_unlock',
        'squashfs_cache_init': 'cache_init', 'squashfs_cache_delete': 'cache_delete',
        'squashfs_cache_get': 'cache_get', 'squashfs_cache_put': 'cache_put',
        'squashfs_page_actor_init': 'actor_init', 'squashfs_iget': 'iget',
        'new_inode': 'new_inode', 'make_bad_inode': 'bad_inode', 'insert_inode_hash': 'insert_inode',
        'iput': 'iput', 'set_nlink': 'nlink', 'i_uid_write': 'uid', 'i_gid_write': 'gid',
        'init_special_inode': 'special_inode', 'inode_nohighmem': 'nohighmem',
        'sb_min_blocksize': 'blocksize', 'd_make_root': 'make_root', 'd_splice_alias': 'splice_alias',
        'squashfs_lookup_decompressor': 'lookup_decompressor', 'squashfs_max_decompressors': 'max_decompressors',
        'squashfs_decompressor_create': 'decompressor_create', 'squashfs_decompressor_destroy': 'decompressor_destroy',
        'squashfs_bio_read': 'read_raw', 'squashfs_decompress': 'decompress', 'copy_bio_to_actor': 'copy_raw',
        'errorf': 'error', 'printk': 'print', '__dynamic_pr_debug': 'dynamic_debug',
        'memcmp': 'memcmp', 'strcmp': 'strcmp',
        'strncmp': 'strncmp', 'strncpy': 'strncpy',
        'strlen': 'strlen', 'squashfs_xattr_handler': 'xattr_handler',
    }
    remap = ''.join(f'#undef {old}\n#define {old}(...) sq_support.{field}(__VA_ARGS__)\n'
                    for old, field in replacements.items())
    remap += '#define kzalloc(n,g) sq_support.alloc((n),(g)|__GFP_ZERO)\n'
    remap += '#undef mutex_init\n#define mutex_init(m) sq_support.mutex_init(m)\n'
    for name in ('memcpy', 'memset'):
        remap += f'#undef {name}\n#define {name}(d,s,n) ((__builtin_constant_p(n) && (size_t)(n) <= 128) ? __builtin_{name}((d),(s),(n)) : sq_support.{name}((d),(s),(n)))\n'
    for field, _, name, address in DATA:
        remap += f'#define {name} ' + (f'(*sq_support.{field})' if address else f'(sq_support.{field})') + '\n'
    (output / 'shared_remap.h').write_text(remap)

    support = notice + INCLUDES + '''
static void *sq_kernel_array(size_t n, size_t size, gfp_t g) { return kcalloc(n,size,g); }
static void sq_kernel_mutex_init(struct mutex *m) { mutex_init(m); }
static void sq_kernel_insert(struct inode *i) { insert_inode_hash(i); }
static void sq_kernel_uid(struct inode *i, uid_t u) { i_uid_write(i,u); }
static void sq_kernel_gid(struct inode *i, gid_t g) { i_gid_write(i,g); }
static void sq_kernel_nohighmem(struct inode *i) { inode_nohighmem(i); }
static loff_t sq_kernel_device_size(struct super_block *s) { return i_size_read(s->s_bdev->bd_inode); }
static struct squashfs_page_actor *sq_kernel_actor(void **p, int n, int l) { return squashfs_page_actor_init(p,n,l); }
static void sq_kernel_fatal(const char *s) { panic("%s", s); }
static void sq_kernel_error(struct fs_context *fc, const char *fmt, ...)
{
    va_list ap;
    struct va_format vaf;
    va_start(ap,fmt); vaf.fmt=fmt; vaf.va=&ap;
    errorf(fc,"%pV",&vaf);
    va_end(ap);
}
extern const struct super_operations squashfs_super_ops;
extern const struct xattr_handler *squashfs_xattr_handler(int);
'''
    for field, ret, params, target in SERVICES:
        if target in ['squashfs_bio_read', 'sq_kernel_input_byte', 'sq_kernel_free_raw', 'copy_bio_to_actor']:
            support += f'extern {ret} {target}({params});\n'
    support += 'static const struct sq_support bindings = {\n'
    support += ''.join(f'    .{field} = {target},\n' for field, _, _, target in SERVICES)
    support += ''.join(f'    .{field} = {"&" if address else ""}{target},\n' for field, _, target, address in DATA)
    support += '};\nvoid sq_owner_bind(void) { sq_bind_support(&bindings); }\n'
    (output / 'kernel_support.c').write_text(support)
    metadata = notice + '#include <linux/module.h>\n' + INCLUDES + '#include "owner.h"\n'
    metadata += '''struct sq_support sq_support;
VKSO_DECLARE_OWNER(sq_owner);
static int __init core_init(void) { return vkso_initialize_owner(&sq_owner); }
static void __exit core_exit(void) { }
module_init(core_init);
module_exit(core_exit);
MODULE_LICENSE("GPL");
MODULE_VERSION("1");
'''
    symbols = ['sq_bind_support', 'sq_support_address'] + [name for name, _ in public]
    metadata += ''.join(f'EXPORT_SYMBOL_GPL({name});\n' for name in symbols)
    (output / 'core_metadata.c').write_text(metadata)
    (output / 'symbols.txt').write_text('\n'.join(symbols) + '\n')
    (output / 'shim.txt').write_text('')
    shutil.copy2(ROOT / 'page_cache_replace/owner.h', output / 'owner.h')
    patch = []
    for name, content in kernel.items():
        (output / name).write_text(content)
        patch += list(difflib.unified_diff(original[name].splitlines(True), content.splitlines(True),
                                          fromfile='upstream/' + name, tofile='kernel/' + name))
    (output / 'kernel.patch').write_text(''.join(patch))
    make = (source / 'Makefile').read_text().replace('obj-$(CONFIG_SQUASHFS) += squashfs.o',
        'obj-m += vkso_sq_core.o vkso_squashfs.o\nvkso_sq_core-y := shared_core.o core_metadata.o')
    make = re.sub(r'(?m)^squashfs-', 'vkso_squashfs-', make)
    make += '''
vkso_squashfs-y += kernel_support.o
CFLAGS_REMOVE_shared_core.o += -pg -mrecord-mcount -mfentry -fstack-protector-strong -mcmodel=kernel
CFLAGS_shared_core.o += -mcmodel=small -fpie -fno-stack-protector -fno-sanitize=all -fno-jump-tables -mfunction-return=keep -mindirect-branch=keep -mpreferred-stack-boundary=4 -mincoming-stack-boundary=3 -D__NO_FORTIFY
UBSAN_SANITIZE_shared_core.o := n
'''
    (output / 'Makefile').write_text(make)
    record = dict(status='generated; not yet functionally validated', source=str(source),
        functions=accounting, services=len(SERVICES), operation_tables=len(DATA),
        approach='shared format logic, domain-private VFS objects/cache/I/O/decompressors',
        limits=['user adapter and actual Apptainer execution still required',
                'common object uses the experimental ISO compiler settings; production hardening equivalence not claimed'])
    (output / 'adaptation.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SECTION / 'build/native/linux-5.15.198/fs/squashfs')
    parser.add_argument('--output', type=Path, default=SECTION / 'build/squashfs/adapted')
    parser.add_argument('--kdir', type=Path, default=SECTION / 'build/native/kernel')
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    record = prepare(args.source.resolve(), out)
    print(json.dumps(dict(functions=len(record['functions']), services=record['services'], output=str(out))))
    if args.build:
        log = out / 'build.log'
        index = 2
        while log.exists():
            log = out / f'build-{index:02d}.log'
            index += 1
        with log.open('w') as stream:
            result = subprocess.run(['make', '-C', str(args.kdir.resolve()), f'M={out}', '-j2', 'modules'],
                                    stdout=stream, stderr=subprocess.STDOUT)
        built = dict(returncode=result.returncode, log=str(log))
        if result.returncode == 0:
            undefined = subprocess.check_output(['nm', '-u', str(out / 'shared_core.o')], text=True)
            built['common_undefined_symbols'] = [line.split()[-1] for line in undefined.splitlines()]
            assert built['common_undefined_symbols'] == ['sq_support'], built
        (out / 'build.json').write_text(json.dumps(built, indent=2) + '\n')
        print(json.dumps(built))
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
