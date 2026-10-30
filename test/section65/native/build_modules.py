#!/usr/bin/env python3
"""Build all comparison paths against one kernel SDK, without loading modules."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

SECTION = Path(__file__).resolve().parents[1]
ROOT = SECTION.parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kdir', type=Path, default=SECTION / 'build/native/kernel')
    p.add_argument('--output', type=Path, default=SECTION / 'build/native/modules')
    p.add_argument('--inline-constant-memops', action='store_true')
    p.add_argument('--keep-private-helpers', action='store_true')
    a = p.parse_args()
    kdir, out = a.kdir.resolve(), a.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    common = '-DCONFIG_JOLIET=1 -DCONFIG_ZISOFS=1'
    # The untouched driver still accesses per-CPU kernel state: it must retain
    # mcmodel=kernel/non-PIE. Only instrumentation/mitigation switches are aligned.
    compat_remove = '-pg -mrecord-mcount -mfentry -fstack-protector-strong'
    compat_flags = ('-fno-stack-protector -fno-sanitize=all '
                    '-fno-jump-tables -mfunction-return=keep -mindirect-branch=keep '
                    '-mpreferred-stack-boundary=4 -mincoming-stack-boundary=3 -D__NO_FORTIFY')
    objects = 'namei inode dir util rock export joliet compress'.split()
    commands = []

    def run(command, log):
        commands.append(list(map(str, command)))
        with (out / log).open('w') as stream:
            subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT, check=True)

    for variant, fstype in [('original', 'iso_original'), ('compat', 'iso_compat')]:
        dest = out / variant
        dest.mkdir(exist_ok=True)
        for f in (SECTION / 'upstream').iterdir():
            if f.suffix in ('.c', '.h'):
                shutil.copy2(f, dest / f.name)
        inode = dest / 'inode.c'
        text = inode.read_text()
        assert text.count('"iso9660",') == 1
        inode.write_text(text.replace('"iso9660",', f'"{fstype}",') + '\nMODULE_VERSION("1");\n')
        make = f'obj-m += {fstype}.o\n{fstype}-y := ' + ' '.join(n + '.o' for n in objects) + '\n'
        make += f'ccflags-y += {common}\n'
        if variant == 'compat':
            for n in objects:
                make += (f'CFLAGS_REMOVE_{n}.o += {compat_remove}\n'
                         f'CFLAGS_{n}.o += {compat_flags}\nUBSAN_SANITIZE_{n}.o := n\n')
        (dest / 'Makefile').write_text(make)
        run(['make', '-C', kdir, f'M={dest}', '-j2', 'modules'], variant + '.log')
    adapted = out / 'adapted'
    run([sys.executable, SECTION / 'adapt.py', '--kdir', kdir, '--output', adapted,
         '--enable-isofs-features'] + (['--inline-constant-memops'] if a.inline_constant_memops else []) +
         (['--keep-private-helpers'] if a.keep_private_helpers else []), 'adapt.log')
    run([sys.executable, SECTION / 'build_user.py', '--kdir', kdir, '--build', adapted], 'user.log')
    for name, source in [('registration', ROOT / 'page_cache_replace'),
                         ('reader', ROOT / 'test/test_gettime/vkso-tests/revision/kernel-reader')]:
        dest = out / name
        dest.mkdir(exist_ok=True)
        for f in source.iterdir():
            if f.suffix in ('.c', '.h') or f.name == 'Makefile':
                shutil.copy2(f, dest / f.name)
        run(['make', '-C', kdir, f'M={dest}', '-j2', 'modules', 'EXTRA_CFLAGS=-fno-inline -g'], name + '.log')
    run(['gcc', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-std=gnu11',
         '-I' + str(SECTION / 'build/fuse-deps/usr/include/fuse3'), SECTION / 'fuse_frontend.c',
         '-Wl,-l:libfuse3.so.3', '-ldl', '-o', out / 'vkso-isofuse'], 'frontend.log')
    record = dict(kdir=str(kdir), kernel_release=(kdir / 'include/config/kernel.release').read_text().strip(),
                  commands=commands, original='unmodified algorithm; filesystem registration name and module version only',
                  compat='original algorithm with reduced instrumentation/mitigations, retaining kernel/non-PIE code model; diagnostic control',
                  prepared='shared core plus original kernel VFS consumer',
                  feature_defines=common, compatibility_remove=compat_remove, compatibility_flags=compat_flags,
                  inline_constant_memops=a.inline_constant_memops,
                  keep_private_helpers=a.keep_private_helpers,
                  caveat='Original vs prepared includes compiler/hardening changes; do not attribute all differences to dependency indirection.')
    (out / 'build.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(dict(status='built', output=str(out))))


if __name__ == '__main__':
    main()
