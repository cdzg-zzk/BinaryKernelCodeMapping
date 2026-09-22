"""Build the original Ubuntu XZ with the owner's code-generation options."""
import json
import shlex
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = 'matched-build-kernel'
OBJECTS = ('xz_dec_stream', 'xz_dec_lzma2', 'xz_dec_bcj')


def prepare_source(owner, matched):
    source = HERE.parents[1] / 'test/section63/source/linux-5.15.0-119.129'
    identity = json.loads((source / 'source.json').read_text())
    names = ('xz_dec_stream.c', 'xz_dec_lzma2.c', 'xz_dec_bcj.c',
             'xz_private.h', 'xz_stream.h', 'xz_lzma2.h', 'xz.h')
    identity = {**identity, 'files': list(names)}
    for name in names:
        original = source / ('include/linux' if name == 'xz.h' else 'lib/xz') / name
        shutil.copy2(original, matched / name)
    # This wrapper has no algorithm or helper-slot implementation.
    (matched / 'module_meta.c').write_text('''#include <linux/module.h>
#include "xz.h"
EXPORT_SYMBOL_GPL(xz_dec_init);
EXPORT_SYMBOL_GPL(xz_dec_run);
EXPORT_SYMBOL_GPL(xz_dec_reset);
EXPORT_SYMBOL_GPL(xz_dec_end);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Original Ubuntu XZ with VKSO owner code-generation options");
''')
    makefile = (owner / 'Makefile').read_text().replace('vkso_xz', 'matched_xz')
    makefile = '\n'.join(line for line in makefile.splitlines()
                         if '-Dxz_crc32' not in line)
    # Remove the trailing continuation on the final surviving rename.
    makefile = makefile.replace('-Dxz_dec_bcj_run=matched_xz_dec_bcj_run \\',
                                '-Dxz_dec_bcj_run=matched_xz_dec_bcj_run')
    makefile = makefile.replace(' xz_crc32.o', '')
    makefile = makefile.replace('-DXZ_DEC_SINGLE -DXZ_INTERNAL_CRC32=1 ', '')
    makefile = '\n'.join(line for line in makefile.splitlines() if not line.startswith('#'))
    (matched / 'Makefile').write_text(makefile + '\n')
    (matched.parent / 'matched-source.json').write_text(json.dumps({
        'definition': 'original XZ, owner code-generation flags, stock features and kernel CRC32',
        'backend': BACKEND, 'source': identity,
        'algorithm_edits': [], 'packaging': ['symbol renaming', 'module exports'],
    }, indent=2) + '\n')


def compare_commands(owner, matched):
    objects = []
    for name in OBJECTS:
        records = []
        for directory, namespace in ((owner, 'vkso_xz'), (matched, 'matched_xz')):
            command = (directory / ('.' + name + '.o.cmd')).read_text().splitlines()[0]
            args = shlex.split(command.split(' := ', 1)[1])
            normalized = [a.replace(str(directory), '<build>').replace(namespace, '<namespace>')
                          for a in args if not a.startswith('-Dxz_crc32')
                          and a not in ('-DXZ_DEC_SINGLE', '-DXZ_INTERNAL_CRC32=1')]
            records.append({'command': command, 'normalized': normalized})
        assert records[0]['normalized'] == records[1]['normalized'], name
        objects.append({'object': name, 'records': records, 'status': 'pass'})
    return {'status': 'pass', 'definition': BACKEND, 'objects': objects,
            'allowed_differences': ['module namespace and build directory',
                'XZ_DEC_SINGLE and XZ_INTERNAL_CRC32 only in owner',
                'internal CRC32 symbol renames only in owner'],
            'intervention': 'original source and dependencies versus complete export adaptation'}
