#!/usr/bin/env python3
"""Separate isofs image-reading code from VFS/device services, retaining kernel callers.

Generated files are build inputs. Upstream sources remain unmodified. Each
function move and semantic boundary edit is recorded for adaptation accounting.
"""
import argparse
import difflib
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FUNCTIONS = {
    'inode.c': ['rootdir_empty', 'isofs_fill_super', 'isofs_get_blocks', 'isofs_get_block',
                'isofs_bmap', 'isofs_bread', 'isofs_read_level3_size', 'isofs_read_inode'],
    'namei.c': ['isofs_cmp', 'isofs_find_entry', 'isofs_lookup'],
    'dir.c': ['isofs_name_translate', 'get_acorn_filename', 'do_isofs_readdir', 'isofs_readdir'],
    'rock.c': ['check_sp', 'setup_rock_ridge', 'init_rock_state', 'rock_continue',
               'rock_check_overflow', 'get_rock_ridge_filename',
               'parse_rock_ridge_inode_internal', 'get_symlink_chunk',
               'parse_rock_ridge_inode', 'rock_ridge_symlink_readpage'],
    'joliet.c': ['uni16_to_x8', 'get_joliet_filename'],
    'util.c': ['iso_date'],
}

# Function pointers are private bindings. They are not a shared kernel service
# endpoint. The kernel initializer uses real services, the user initializer uses
# process-owned objects and POSIX byte I/O.
SUPPORT = [
    ('alloc', 'void *', 'size_t, gfp_t', '__kmalloc'),
    ('free', 'void', 'const void *', 'kfree'),
    ('bread', 'struct buffer_head *', 'struct super_block *, sector_t', 'iso_kernel_bread'),
    ('getblk', 'struct buffer_head *', 'struct super_block *, sector_t', 'iso_kernel_getblk'),
    ('brelse', 'void', 'struct buffer_head *', 'iso_kernel_brelse'),
    ('put_bh', 'void', 'struct buffer_head *', 'iso_kernel_put_bh'),
    ('iget', 'struct inode *', 'struct super_block *, unsigned long, unsigned long, int', '__isofs_iget'),
    ('iput', 'void', 'struct inode *', 'iput'),
    ('nlink', 'void', 'struct inode *, unsigned int', 'set_nlink'),
    ('uid', 'void', 'struct inode *, uid_t', 'iso_kernel_uid'),
    ('gid', 'void', 'struct inode *, gid_t', 'iso_kernel_gid'),
    ('blocksize', 'int', 'struct super_block *, int', 'sb_set_blocksize'),
    ('make_root', 'struct dentry *', 'struct inode *', 'd_make_root'),
    ('splice_alias', 'struct dentry *', 'struct inode *, struct dentry *', 'd_splice_alias'),
    ('load_nls', 'struct nls_table *', 'const char *', 'load_nls'),
    ('load_nls_default', 'struct nls_table *', 'void', 'load_nls_default'),
    ('unload_nls', 'void', 'struct nls_table *', 'unload_nls'),
    ('attach_inode', 'int', 'struct inode *', 'iso_kernel_attach_inode'),
    ('attach_super', 'void', 'struct super_block *, int', 'iso_kernel_attach_super'),
    ('dotdot', 'bool', 'struct file *, struct dir_context *', 'iso_kernel_dotdot'),
    ('print', 'int', 'const char *, ...', '_printk'),
    ('memcpy', 'void *', 'void *, const void *, size_t', 'memcpy'),
    ('memset', 'void *', 'void *, int, size_t', 'memset'),
    ('memcmp', 'int', 'const void *, const void *, size_t', 'memcmp'),
    ('memchr', 'void *', 'const void *, int, size_t', 'memchr'),
    ('strcmp', 'int', 'const char *, const char *', 'strcmp'),
    ('strncmp', 'int', 'const char *, const char *, size_t', 'strncmp'),
    ('sprintf', 'int', 'char *, const char *, ...', 'sprintf'),
    ('time', 'time64_t', 'unsigned int, unsigned int, unsigned int, unsigned int, unsigned int, unsigned int', 'mktime64'),
]


def span(text, name):
    pattern = (r'(?m)^(?:(?:static|inline|const|unsigned|long|int|bool|void|char|sector_t|struct)'
               r'[\w \t*]*\s+)+\**' + re.escape(name) + r'\s*\([^;{}]*\)\s*\{')
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError((name, len(matches)))
    start, brace = matches[0].start(), matches[0].end()-1
    # Tokenize comments and string literals together with braces so braces in
    # diagnostics/comments cannot corrupt source extraction.
    tokens = re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',
                         text[brace:], re.S)
    depth = 0
    for token in tokens:
        if token[0] == '{': depth += 1
        elif token[0] == '}':
            depth -= 1
            if depth == 0:
                return start, brace + token.end()
    raise ValueError('unterminated ' + name)


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('source boundary mismatch: ' + old[:100])
    return text.replace(old, new, 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kdir', type=Path, default=Path('/usr/src/linux-headers-5.15.0-119-generic'))
    p.add_argument('--source', type=Path, default=HERE / 'upstream')
    p.add_argument('--output', type=Path, default=HERE / 'build/adapted')
    p.add_argument('--enable-isofs-features', action='store_true',
                   help='enable Joliet/zisofs in external modules when the host has no built-in isofs')
    p.add_argument('--inline-constant-memops', action='store_true',
                   help='preserve compiler expansion of constant-size memory operations up to 128 bytes')
    p.add_argument('--keep-private-helpers', action='store_true',
                   help='retain original static helpers that have no caller outside the common core')
    args = p.parse_args()
    src = args.source.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source = {p.name:p.read_text() for p in src.glob('*') if p.suffix in ('.c','.h')}
    kernel = dict(source)
    option_match = re.search(r'struct iso9660_options\{.*?\n};', source['inode.c'], re.S)
    options = option_match[0]
    kernel['inode.c'] = kernel['inode.c'].replace(options, '')
    shared, declarations, private_declarations, accounting = [], [], [], []
    private_helpers = []
    # These originally static entries still serve native VFS callbacks or the
    # user bridge after moving; their shared-core definitions remain public.
    public_static = {'isofs_fill_super','isofs_get_block','isofs_bmap',
                     'isofs_read_inode','isofs_readdir','rock_ridge_symlink_readpage'}
    attach_inode = None
    for filename, names in FUNCTIONS.items():
        for name in names:
            start, end = span(kernel[filename], name)
            original = kernel[filename][start:end]
            body = re.sub(r'^static\s+', '', original)
            declaration = body[:body.index('{')].strip() + ';'
            replacement = declaration
            if name == 'isofs_fill_super':
                body = once(body, 'int isofs_fill_super(struct super_block *s, void *data, int silent)',
                            'int iso_read_super(struct super_block *s, const struct iso9660_options *options, int silent, unsigned int vol_desc_start)')
                body = once(body, 'struct iso9660_options opt;', 'struct iso9660_options opt = *options;')
                body = once(body, '\tunsigned int vol_desc_start;\n', '')
                a = body.index('\tif (!parse_options(')
                b = body.index('\n\tfor (iso_blknum', a)
                body = body[:a] + '''\tsbi->s_high_sierra = 0;
\tsbi->s_session = opt.session;
\tsbi->s_sbsector = opt.sbsector;
''' + body[b:]
                body = once(body, '\ts->s_op = &isofs_sops;\n\ts->s_export_op = &isofs_export_ops;\n',
                            '\tiso_support.attach_super(s, 0);\n')
                body = once(body, '\tif (table)\n\t\ts->s_d_op = &isofs_dentry_ops[table - 1];',
                            '\tiso_support.attach_super(s, table);')
                replacement = '''static int isofs_fill_super(struct super_block *s, void *data, int silent)
{
    struct iso9660_options opt;
    unsigned int start;
    if (!parse_options(data, &opt)) { kfree(opt.iocharset); return -EINVAL; }
    if (bdev_logical_block_size(s->s_bdev) > 2048) {
        kfree(opt.iocharset); return -EINVAL;
    }
    opt.blocksize = sb_min_blocksize(s, opt.blocksize);
    start = opt.sbsector != -1 ? opt.sbsector : isofs_get_last_session(s, opt.session);
    return iso_read_super(s, &opt, silent, start);
}'''
            elif name == 'isofs_lookup':
                body = once(body, 'struct page *page;', 'char *page;')
                body = once(body, 'alloc_page(GFP_USER)', 'kmalloc(PAGE_SIZE, GFP_USER)')
                body = body.replace('page_address(page)', 'page')
                body = once(body, '1024 + page)', '(struct iso_directory_record *)(1024 + page))')
                body = once(body, '__free_page(page)', 'kfree(page)')
            elif name == 'isofs_read_inode':
                a = body.index('\t/* Install the inode operations vector */')
                b = body.index('\n\tret = 0;\nout:', a)
                attach_inode = body[a:b]
                # Retain dispatch validation in the domain attachment operation.
                body = body[:a] + '\tret = iso_support.attach_inode(inode);\n\tgoto out;\n' + body[b:]
            elif name == 'rock_ridge_symlink_readpage':
                body = once(body, 'int rock_ridge_symlink_readpage(struct file *file, struct page *page)',
                            'int iso_readlink(struct inode *inode, char *link)')
                body = once(body, '\tstruct inode *inode = page->mapping->host;\n', '')
                body = once(body, '\tchar *link = page_address(page);\n', '')
                body = once(body, '\tSetPageUptodate(page);\n\tunlock_page(page);\n', '')
                body = once(body, '\tSetPageError(page);\n\tunlock_page(page);\n', '')
                replacement = '''static int rock_ridge_symlink_readpage(struct file *file, struct page *page)
{
    int ret = iso_readlink(page->mapping->host, page_address(page));
    if (ret) SetPageError(page); else SetPageUptodate(page);
    unlock_page(page);
    return ret;
}'''
            private = args.keep_private_helpers and original.startswith('static ') and name not in public_static
            if private:
                body = 'static ' + body
                replacement = ''
                private_helpers.append(name)
            declaration = body[:body.index('{')].strip() + ';'
            (private_declarations if private else declarations).append(declaration)
            shared.append(body)
            kernel[filename] = kernel[filename][:start] + replacement + kernel[filename][end:]
            accounting.append(dict(source=filename, function=name,
                                   original_lines=len(original.splitlines()),
                                   shared_lines=len(body.splitlines()),
                                   edited_after_move=re.sub(r'^static\s+', '', body) != re.sub(r'^static\s+', '', original)))
    # The old static forward declaration must agree with the moved definition.
    kernel['inode.c'] = kernel['inode.c'].replace('static int isofs_read_inode(struct inode *, int relocated);',
                                               'int isofs_read_inode(struct inode *, int relocated);')
    types = '#ifndef ISO_SUPPORT_TYPES_H\n#define ISO_SUPPORT_TYPES_H\n#include <linux/nls.h>\n'
    types += 'struct rock_state;\nstruct rock_ridge;\n'
    types += options + '\nstruct iso_support {\n'
    for name, ret, params, _ in SUPPORT:
        types += f'    {ret} (*{name})({params});\n'
    types += '};\nextern struct iso_support iso_support;\n'
    types += 'void iso_bind_support(const struct iso_support *source);\n'
    types += 'struct iso_support *iso_support_address(void);\n'
    types += '\n'.join(declarations) + '\n#endif\n'
    (out / 'support_types.h').write_text(types)
    kernel['isofs.h'] += '\n#include "support_types.h"\n'
    # Kernel callers still attach the full VFS operations and use their existing
    # allocation, inode cache, buffer cache, and namespace implementation.
    assert attach_inode is not None
    attach_inode = attach_inode.replace('ret = -EIO;', '').replace('goto fail;', 'return -EIO;')
    kernel['inode.c'] += '''
int iso_kernel_attach_inode(struct inode *inode)
{
    struct iso_inode_info *ei = ISOFS_I(inode);
''' + attach_inode + '''
    return 0;
}
void iso_kernel_attach_super(struct super_block *s, int table)
{
    s->s_op = &isofs_sops;
    s->s_export_op = &isofs_export_ops;
    if (table) s->s_d_op = &isofs_dentry_ops[table - 1];
}
'''
    kernel['inode.c'] = kernel['inode.c'].replace('"iso9660",', '"vksoiso",')
    owner_init = 'static int __init init_iso9660_fs(void)\n{'
    kernel['inode.c'] = once(kernel['inode.c'], owner_init,
                            owner_init + '\n\tint owner_ret = iso_owner_init();\n\tif (owner_ret) return owner_ret;')
    kernel['isofs.h'] += '\nint iso_owner_init(void);\n'
    prelude = '''// SPDX-License-Identifier: GPL-2.0-only
/* Linux isofs reading functions moved from the identified upstream snapshot.
 * Original authors/notices are preserved in upstream/ and generated kernel files.
 */
#include <linux/slab.h>
#include <linux/pagemap.h>
#include <linux/nls.h>
#include <linux/blkdev.h>
#include "isofs.h"
#include "rock.h"
#include "support_remap.h"
#define MAX_TZ_OFFSET (52*15*60)
#define BEQUIET
#define SIG(A,B) ((A) | ((B) << 8))
#define RR_MAX_CE_ENTRIES 32
#define RR_REGARD_XA 1
#define RR_RELOC_DE 2
'''
    rock_state = re.search(r'struct rock_state \{.*?\n};', source['rock.c'], re.S)[0]
    bind = 'void iso_bind_support(const struct iso_support *source)\n{\n'
    bind += ''.join(f'    iso_support.{name} = source->{name};\n' for name,_,_,_ in SUPPORT) + '}\n'
    bind += 'struct iso_support *iso_support_address(void) { return &iso_support; }\n'
    nls = source['nls_base.c']
    unicode = nls[nls.index('struct utf8_table {'):nls.index('int utf8_to_utf32(')]
    for name in ('utf32_to_utf8','get_utf16','utf16s_to_utf8s'):
        a,b = span(nls,name)
        unicode += nls[a:b]+'\n'
    unicode = unicode.replace('utf32_to_utf8','iso_utf32_to_utf8').replace('utf16s_to_utf8s','iso_utf16s_to_utf8s')
    (out / 'shared_core.c').write_text(prelude + unicode + rock_state + '\n\n' +
        ('\n'.join(private_declarations)+'\n\n' if private_declarations else '') + '\n\n'.join(shared) + '\n' + bind)
    remap = '''#define kmalloc(n,g) iso_support.alloc((n),(g))
#define kzalloc(n,g) iso_support.alloc((n),(g)|__GFP_ZERO)
#define kfree(p) iso_support.free(p)
#undef __get_free_page
#define __get_free_page(g) ((unsigned long)iso_support.alloc(PAGE_SIZE,(g)))
#undef free_page
#define free_page(p) iso_support.free((void *)(p))
#define sb_bread(s,b) iso_support.bread((s),(b))
#define sb_getblk(s,b) iso_support.getblk((s),(b))
#define brelse(b) iso_support.brelse(b)
#define put_bh(b) iso_support.put_bh(b)
#define isofs_iget(s,b,o) iso_support.iget((s),(b),(o),0)
#define isofs_iget_reloc(s,b,o) iso_support.iget((s),(b),(o),1)
#define iput(i) iso_support.iput(i)
#define set_nlink(i,n) iso_support.nlink((i),(n))
#define i_uid_write(i,u) iso_support.uid((i),(u))
#define i_gid_write(i,g) iso_support.gid((i),(g))
#define sb_set_blocksize(s,n) iso_support.blocksize((s),(n))
#define d_make_root(i) iso_support.make_root(i)
#define d_splice_alias(i,d) iso_support.splice_alias((i),(d))
#define dir_emit_dotdot(f,c) iso_support.dotdot((f),(c))
#define load_nls(c) iso_support.load_nls(c)
#define load_nls_default() iso_support.load_nls_default()
#define unload_nls(c) iso_support.unload_nls(c)
#undef printk
#define printk(...) iso_support.print(__VA_ARGS__)
#define memcpy(d,s,n) iso_support.memcpy((d),(s),(n))
#define memset(d,c,n) iso_support.memset((d),(c),(n))
#define memcmp(a,b,n) iso_support.memcmp((a),(b),(n))
#define memchr(a,b,n) iso_support.memchr((a),(b),(n))
#define strcmp(a,b) iso_support.strcmp((a),(b))
#define strncmp(a,b,n) iso_support.strncmp((a),(b),(n))
#define sprintf(...) iso_support.sprintf(__VA_ARGS__)
#define mktime64(...) iso_support.time(__VA_ARGS__)
#define utf16s_to_utf8s(...) iso_utf16s_to_utf8s(__VA_ARGS__)
'''
    if args.inline_constant_memops:
        # These operations have identical byte semantics in both domains. Keep
        # small constant operations visible to GCC rather than hiding stack
        # initialization behind an opaque environment-service callback.
        # Dynamic sizes retain the existing explicit service binding.
        remap = once(remap, '#define memcpy(d,s,n) iso_support.memcpy((d),(s),(n))',
            '#define memcpy(d,s,n) ((__builtin_constant_p(n) && (size_t)(n) <= 128) ? __builtin_memcpy((d),(s),(n)) : iso_support.memcpy((d),(s),(n)))')
        remap = once(remap, '#define memset(d,c,n) iso_support.memset((d),(c),(n))',
            '#define memset(d,c,n) ((__builtin_constant_p(n) && (size_t)(n) <= 128) ? __builtin_memset((d),(c),(n)) : iso_support.memset((d),(c),(n)))')
    (out / 'support_remap.h').write_text(remap)
    support = '''// SPDX-License-Identifier: GPL-2.0-only
#include <linux/slab.h>
#include <linux/blkdev.h>
#include <linux/nls.h>
#include "isofs.h"
static struct buffer_head *iso_kernel_bread(struct super_block *s, sector_t b) { return sb_bread(s,b); }
static struct buffer_head *iso_kernel_getblk(struct super_block *s, sector_t b) { return sb_getblk(s,b); }
static void iso_kernel_brelse(struct buffer_head *b) { brelse(b); }
static void iso_kernel_put_bh(struct buffer_head *b) { put_bh(b); }
static void iso_kernel_uid(struct inode *i, uid_t u) { i_uid_write(i,u); }
static void iso_kernel_gid(struct inode *i, gid_t g) { i_gid_write(i,g); }
static bool iso_kernel_dotdot(struct file *f, struct dir_context *c) { return dir_emit_dotdot(f,c); }
extern int iso_kernel_attach_inode(struct inode *);
extern void iso_kernel_attach_super(struct super_block *, int);
static const struct iso_support kernel_bindings = {
'''
    support += ''.join(f'    .{name} = {target},\n' for name,_,_,target in SUPPORT) + '};\n'
    support += 'int iso_owner_init(void) { iso_bind_support(&kernel_bindings); return 0; }\n'
    (out / 'kernel_support.c').write_text(support)
    exports = ['iso_bind_support','iso_support_address'] + [re.search(r'([a-zA-Z_]\w*)\s*\(', d)[1] for d in declarations]
    metadata = '''// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include "isofs.h"
#include "owner.h"
struct iso_support iso_support;
VKSO_DECLARE_OWNER(iso_owner);
static int __init core_init(void) { return vkso_initialize_owner(&iso_owner); }
static void __exit core_exit(void) { }
module_init(core_init);
module_exit(core_exit);
MODULE_LICENSE("GPL");
MODULE_VERSION("1");
'''
    metadata += ''.join(f'EXPORT_SYMBOL_GPL({name});\n' for name in exports)
    (out / 'core_metadata.c').write_text(metadata)
    (out / 'symbols.txt').write_text('\n'.join(['iso_bind_support','iso_support_address','iso_read_super','isofs_read_inode',
        'isofs_lookup','isofs_readdir','iso_readlink','isofs_get_blocks'])+'\n')
    (out / 'shim.txt').write_text('')
    shutil.copy2(ROOT / 'page_cache_replace/owner.h', out / 'owner.h')
    patches = []
    for filename, text in kernel.items():
        (out / filename).write_text(text)
        patches += list(difflib.unified_diff(source[filename].splitlines(True), text.splitlines(True),
                                           fromfile='upstream/'+filename, tofile='kernel/'+filename))
    (out / 'kernel.patch').write_text(''.join(patches))
    (out / 'adaptation.json').write_text(json.dumps(dict(functions=accounting,
        unicode_helpers=['utf32_to_utf8','get_utf16','utf16s_to_utf8s'],
        unicode_source='fs/nls/nls_base.c', unicode_lines=len(unicode.splitlines()),
        binding_setter_lines=len(bind.splitlines()),
        support_bindings=len(SUPPORT), inline_constant_memops=args.inline_constant_memops,
        private_helpers=private_helpers,
        approach='same Linux types; private dependency bindings; kernel VFS callers retained'), indent=2)+'\n')
    (out / 'Makefile').write_text('''obj-m += vkso_iso_core.o vkso_isofs.o
vkso_iso_core-y := shared_core.o core_metadata.o
vkso_isofs-y := namei.o inode.o dir.o util.o rock.o export.o joliet.o compress.o kernel_support.o
CFLAGS_REMOVE_shared_core.o += -pg -mrecord-mcount -mfentry -fstack-protector-strong -mcmodel=kernel
CFLAGS_shared_core.o += -mcmodel=small -fpie -fno-stack-protector -fno-sanitize=all -fno-jump-tables -mfunction-return=keep -mindirect-branch=keep -mpreferred-stack-boundary=4 -mincoming-stack-boundary=3 -D__NO_FORTIFY
UBSAN_SANITIZE_shared_core.o := n
''')
    if args.enable_isofs_features:
        with (out / 'Makefile').open('a') as stream:
            stream.write('ccflags-y += -DCONFIG_JOLIET=1 -DCONFIG_ZISOFS=1\n')
    command = ['make','-C',str(args.kdir.resolve()),f'M={out}','-j2','modules']
    with (out / 'build.log').open('w') as f:
        result = subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
    print(json.dumps({'returncode':result.returncode,'moved_functions':len(accounting),
                      'support_bindings':len(SUPPORT),'log':str(out/'build.log')}))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
