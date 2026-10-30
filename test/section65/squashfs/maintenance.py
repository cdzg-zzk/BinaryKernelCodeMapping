#!/usr/bin/env python3
"""Reproduce the upstream negative-offset repair in disposable old/fixed guests."""
import argparse
import difflib
import errno
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
SECTION = HERE.parent
ROOT = SECTION.parents[1]
COMMIT = 'e300eb5002925b29be803d2661af07266cfa267e'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(out):
    source = out/'source'; source.mkdir()
    (source/'payload').write_bytes(b'SquashFS maintenance regression\n' * 3)
    image = out/'valid.squashfs'
    argv = ['mksquashfs', source, image, '-noappend', '-processors', '1',
            '-comp', 'gzip', '-noI', '-noD', '-noF', '-noX', '-no-exports',
            '-always-use-fragments', '-all-time', '1700000000',
            '-mkfs-time', '1700000000', '-no-progress']
    with (out/'fixture.log').open('w') as log:
        subprocess.run(list(map(str, argv)), stdout=log, stderr=subprocess.STDOUT, check=True)
    data = bytearray(image.read_bytes())
    assert struct.unpack_from('<I', data)[0] == 0x73717368
    inode_start = struct.unpack_from('<Q', data, 64)[0]
    size = struct.unpack_from('<H', data, inode_start)[0]
    assert size & 0x8000
    start = inode_start + 2
    # There is exactly one ordinary inode in this single-file fixture.
    assert struct.unpack_from('<H', data, start)[0] == 2
    assert struct.unpack_from('<I', data, start+28)[0] == (source/'payload').stat().st_size
    assert struct.unpack_from('<I', data, start+20)[0] != 0xffffffff
    assert struct.unpack_from('<I', data, start+24)[0] == 0
    struct.pack_into('<i', data, start+24, -(1 << 31))
    (out/'negative.squashfs').write_bytes(data)
    return dict(valid=digest(image), negative=digest(out/'negative.squashfs'),
                field='squashfs_reg_inode.offset', byte_offset=start+24,
                old=0, new=-(1 << 31), payload=(source/'payload').read_text())


def package(build, out, images):
    support = ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029'
    out.mkdir()
    for name in ['vkso_sq_core.ko', 'vkso_squashfs.ko', 'symbols.txt', 'shim.txt',
                 'libsq-bridge.so', 'vkso-squashfuse']:
        shutil.copy2(build/name, out/name)
    for name in ['krg', 'manager', 'vmlinux']:
        shutil.copy2(support/name, out/name)
    for name in ['vkso_kernel_reader.ko', 'page_cache_replace.ko']:
        shutil.copy2(support/'modules'/name, out/name)
    shutil.copy2(ROOT/'make_dll/build_PIC_so.py', out/'build_PIC_so.py')
    for name in ['maintenance_guest.py', 'check_fuse.py']:
        shutil.copy2(HERE/name, out/name)
    shutil.copy2(SECTION/'reference_guest.py', out/'reference_guest.py')
    for name in ['libsq-bridge.so', 'vkso-squashfuse']:
        deps = subprocess.check_output(['ldd', str(out/name)], text=True)
        for library in re.findall(r'=> (/\S+)', deps):
            shutil.copy2(library, out/Path(library).name)
    shutil.copytree(support/'bin', out/'bin')
    for path in support.glob('lib*.so.*'):
        if not (out/path.name).exists(): shutil.copy2(path, out/path.name)
    shutil.copytree(images, out/'case')
    shutil.copytree(SECTION/'build/squashfs/fixtures', out/'images',
                    ignore=shutil.ignore_patterns('source'))
    reference = ROOT/'test/evaluation-local/runs/iso9660/squash-native-guest-03/evidence'
    (out/'reference').mkdir()
    for path in reference.glob('*-squashfs.json'):
        shutil.copy2(path, out/'reference'/path.name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--build', type=Path, default=SECTION/'build/squashfs/reader-adapted')
    p.add_argument('--kernel', type=Path, default=Path('/boot/vkso-final-raw-normal-5.15.198.bzImage'))
    args = p.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    images = out/'fixture'; images.mkdir()
    result = dict(status='running', commit=COMMIT,
                  source='https://github.com/torvalds/linux/commit/'+COMMIT,
                  scope='functional maintenance reproduction; no performance or live-update claim',
                  fixture=fixture(images))
    write = lambda: (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    write()
    old = args.build.resolve(); fixed = out/'fixed-build'
    shutil.copytree(old, fixed)
    before = (fixed/'shared_core.c').read_text()
    # Apply precisely the upstream hunk to the moved, otherwise unchanged body.
    a = before.index('int squashfs_copy_data(')
    b = before.index('\n}\n', a)+3
    body = before[a:b]
    assert body.count('if (length == 0)') == 1
    after = before[:a]+body.replace('if (length == 0)', 'if (length == 0 || offset < 0)')+before[b:]
    (fixed/'shared_core.c').write_text(after)
    (out/'upstream-backport.patch').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile='old/shared_core.c', tofile='fixed/shared_core.c')))
    with (out/'build.log').open('w') as log:
        subprocess.run(['make', '-C', str(SECTION/'build/native/kernel'), f'M={fixed}', '-j2', 'modules'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    result['unchanged_user_binaries'] = {name: dict(old=digest(old/name), fixed=digest(fixed/name))
        for name in ['libsq-bridge.so', 'vkso-squashfuse']}
    assert all(row['old'] == row['fixed'] for row in result['unchanged_user_binaries'].values())
    result['owners'] = {name: digest(path/'vkso_sq_core.ko') for name, path in [('old', old), ('fixed', fixed)]}
    assert result['owners']['old'] != result['owners']['fixed']
    write()
    for label, build in [('old', old), ('fixed', fixed)]:
        pkg = out/(label+'-package'); package(build, pkg, images)
        (pkg/'mode').write_text(label)
        (pkg/'run.sh').write_text('#!/bin/bash\nset -eu\ncd /work/package\n'
            'export LD_LIBRARY_PATH=/work/package\nexport PATH=/work/package/bin:$PATH\n'
            'exec python3 -u maintenance_guest.py\n')
        with (out/(label+'-runner.log')).open('w') as log:
            proc = subprocess.run([sys.executable, str(SECTION/'native/qemu.py'), '--package', str(pkg),
                '--output', str(out/(label+'-guest')), '--kernel', str(args.kernel),
                '--native-ide', '--timeout', '1200'], stdout=log, stderr=subprocess.STDOUT)
        guest = out/(label+'-guest')
        evidence = json.loads((guest/'evidence/result.json').read_text())
        console = (guest/'console.log').read_text(errors='replace')
        if label == 'old':
            assert evidence['stage'] == 'native-negative-read', evidence
            assert evidence['native_valid']['status'] == 'pass', evidence
            for backend in ['copied', 'shared']:
                assert evidence[backend+'_valid']['client_errno'] == 0, evidence
                fault = evidence[backend+'_negative']
                assert fault['client_errno'] in (errno.EIO, errno.ENOTCONN), evidence
                assert fault['daemon_returncode'] == -11 and not fault['daemon_alive_after_read'], evidence
            assert re.search(r'RIP: 0010:squashfs_copy_data\+', console) and 'Kernel panic' in console
            result['old'] = dict(expected_native_panic=True, shared_daemon_sigsegv=True,
                                 runner_returncode=proc.returncode, evidence=str(guest/'evidence'))
        else:
            assert proc.returncode == 0 and evidence['status'] == 'complete', evidence
            # Preserve the actual native outcome: the original read path may zero-fill
            # a zero-byte copy, whereas the user adapter rejects a short copy.
            native = evidence['native_negative']
            assert native['errno'] == errno.EIO or (native['errno'] == 0 and
                native['bytes'] == len(result['fixture']['payload'].encode()) and native['zero_filled']), native
            for backend in ['copied', 'shared']:
                fault = evidence[backend+'_negative']
                assert fault['client_errno'] == errno.EIO, fault
                assert fault['daemon_returncode'] == 0 and fault['daemon_alive_after_read'], fault
            result['fixed'] = dict(native_outcome=native, user_short_copy_rejected=True,
                                  restored=evidence['restored'], modules_unloaded=evidence['modules_unloaded'],
                                  evidence=str(guest/'evidence'))
        write()
        print('maintenance '+label+' verified', flush=True)
    result['status'] = 'complete'; write()


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        # Preserve a terminal failure instead of leaving a misleading running record.
        if '--output' in sys.argv:
            record = Path(sys.argv[sys.argv.index('--output')+1])/'result.json'
            if record.exists():
                data = json.loads(record.read_text())
                data.update(status='failed', error=traceback.format_exc())
                record.write_text(json.dumps(data, indent=2)+'\n')
        raise
