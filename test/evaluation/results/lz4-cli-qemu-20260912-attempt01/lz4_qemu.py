#!/usr/bin/env python3
"""Prepare an ordinary-user private KVM guest for full LZ4 CLI validation."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def run(argv, **kwargs):
    return subprocess.run(list(map(str, argv)), check=True, **kwargs)


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1048576):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--kernel', type=Path, required=True)
    parser.add_argument('--initramfs', type=Path, required=True,
                        help='previously validated exact119 Python/busybox initramfs with virtio_blk')
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--kernel-package-evidence', type=Path)
    parser.add_argument('--environment-evidence', type=Path)
    args = parser.parse_args()
    output, kernel, base = [path.resolve() for path in (args.output, args.kernel, args.initramfs)]
    output.mkdir(parents=True, exist_ok=False)
    manifest = []

    def copy_file(source, destination):
        source, destination = Path(source), Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            destination.unlink()
        shutil.copy2(source, destination)
        manifest.append({'source': str(source), 'destination': str(destination.relative_to(output)),
                         'sha256': digest(source), 'bytes': source.stat().st_size})

    if args.kernel_package_evidence is not None:
        for name in ('evidence.json', 'apt-package-metadata.txt', 'installed-package.txt'):
            copy_file(args.kernel_package_evidence / name, output / 'kernel-package-evidence' / name)
    if args.environment_evidence is not None:
        for name in ('command.json', 'components.json', 'console.log', 'result.json',
                     'evidence/validation/observations.json'):
            copy_file(args.environment_evidence / name, output / 'environment-evidence' / name)

    initroot = output / 'initramfs'
    initroot.mkdir()
    archive = gzip.decompress(base.read_bytes())
    listing = run(['cpio', '-it'], input=archive, capture_output=True).stdout.decode().splitlines()
    assert all(not name.startswith('/') and '..' not in Path(name).parts for name in listing)
    run(['cpio', '-id', '--no-absolute-filenames', '--no-preserve-owner'],
        cwd=initroot, input=archive, capture_output=True)

    def runtime(source, destination=None):
        source = Path(source)
        copy_file(source, destination or initroot / str(source).lstrip('/'))
        result = subprocess.run(['ldd', str(source)], capture_output=True, text=True)
        for name in re.findall(r'(/[^\s()]+)', result.stdout):
            copy_file(name, initroot / name.lstrip('/'))

    for name in ('bash', 'gcc', 'as', 'ld', 'make', 'readelf', 'nm', 'install', 'realpath',
                 'stat', 'sha256sum', 'awk', 'sed', 'grep', 'tee', 'cp', 'mv', 'rm', 'mktemp'):
        runtime(shutil.which(name), initroot / 'usr/bin' / name)
    runtime('/bin/bash', initroot / 'bin/bash')
    runtime('/usr/lib/linux-tools/5.15.0-119-generic/bpftool', initroot / 'usr/bin/bpftool')
    compiler = Path('/usr/lib/gcc/x86_64-linux-gnu/11')
    shutil.copytree(compiler, initroot / str(compiler).lstrip('/'), symlinks=True)
    shutil.copytree('/usr/include', initroot / 'usr/include', symlinks=True)
    runtime(compiler / 'cc1')
    runtime(compiler / 'collect2')
    for name in ('crti.o', 'crtn.o', 'libc.so', 'libc_nonshared.a', 'libgcc_s.so.1'):
        source = Path('/usr/lib/x86_64-linux-gnu') / name
        copy_file(source, initroot / str(source).lstrip('/'))
    import capstone
    import elftools
    for module in (capstone, elftools):
        directory = Path(module.__file__).parent
        shutil.copytree(directory, initroot / 'opt/python-packages' / directory.name,
                        ignore=shutil.ignore_patterns('__pycache__'))
    (initroot / 'init').write_text('''#!/bin/busybox sh
/bin/busybox --install -s /bin
export PATH=/usr/bin:/bin
export PYTHONPATH=/opt/python-packages
export LC_ALL=C
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
insmod /guest-drivers/virtio_blk.ko
n=0
while [ ! -b /dev/vda ] && [ "$n" -lt 15 ]; do sleep 1; n=$((n+1)); done
if ! mount -t ext4 /dev/vda /work; then
  echo lz4_guest_status=90
  poweroff -f
fi
mount -t debugfs debugfs /sys/kernel/debug
python3 -u /work/guest.py
status=$?
echo lz4_guest_status=$status
sync
poweroff -f
''')
    (initroot / 'init').chmod(0o755)
    payload = output / 'payload'
    payload.mkdir()
    files = ['vkso', 'kernel_cgd/src/krg', 'kernel_cgd/src/krg.cpp',
             'kernel_cgd/kerne_type/vkso_gen_types.py',
             'kernel_cgd/function_checker/functions_checker.py', 'make_dll/build_PIC_so.py',
             'make_dll/shim.c', 'make_dll/shim.txt', 'page_cache_replace/manager',
             'page_cache_replace/manager.cpp', 'page_cache_replace/page_cache_replace.ko']
    for relative in files:
        copy_file(ROOT / relative, payload / 'repo' / relative)
    runtime(ROOT / 'kernel_cgd/src/krg', payload / 'repo/kernel_cgd/src/krg')
    for name in ('lz4-stock', 'lz4-adapted'):
        runtime(HERE / 'lz4-cli/build' / name, payload / 'cli' / name)
    copy_file(ROOT / 'test/test_lz4/kmod/vkso_lz4.ko', payload / 'owner/vkso_lz4.ko')
    for name in ('footprint.py', 'carrier.py'):
        copy_file(ROOT / 'test/test_gettime/vkso-tests/revision' / name, payload / 'helpers' / name)
    copy_file(ROOT / 'test/test_gettime/vkso-tests/revision/kernel-reader/vkso_kernel_reader.ko',
              payload / 'helpers/vkso_kernel_reader.ko')
    for module in (payload / 'owner/vkso_lz4.ko', payload / 'helpers/vkso_kernel_reader.ko',
                   payload / 'repo/page_cache_replace/page_cache_replace.ko'):
        magic = run(['modinfo', '-F', 'vermagic', module], capture_output=True, text=True).stdout
        assert magic.startswith('5.15.0-119-generic '), (module, magic)
    copy_file(ROOT / 'test/test_lz4/config/symbols.txt', payload / 'symbols.txt')
    corpus = ROOT / 'test/test_lz4/corpus/silesia'
    copy_file(corpus / 'manifest.txt', payload / 'corpus/manifest.txt')
    names = [line for line in (corpus / 'manifest.txt').read_text().splitlines()
             if line and not line.startswith('#')]
    assert len(names) == 12 and len(set(names)) == 12
    for name in names:
        copy_file(corpus / name, payload / 'corpus' / name)
    copy_file('/usr/lib/debug/boot/vmlinux-5.15.0-119-generic', payload / 'vmlinux-5.15.0-119-generic')
    copy_file(HERE / 'lz4_guest.py', payload / 'guest.py')
    paths = b'\0'.join(str(path.relative_to(initroot)).encode() for path in initroot.rglob('*')) + b'\0'
    rebuilt = run(['cpio', '--null', '-o', '--format=newc', '--owner=0:0'], cwd=initroot,
                  input=paths, capture_output=True).stdout
    initrd = output / 'initramfs.cpio.gz'
    initrd.write_bytes(gzip.compress(rebuilt, compresslevel=1))
    disk = output / 'guest.ext4'
    with disk.open('wb') as stream:
        stream.truncate(4 * 1024**3)
    run(['mkfs.ext4', '-q', '-F', '-d', payload, disk])
    metadata = {'scope': 'KVM full LZ4 CLI functional validation only', 'host_euid': os.geteuid(),
                'kernel': str(kernel), 'kernel_sha256': digest(kernel),
                'base_initramfs': str(base), 'base_initramfs_sha256': digest(base),
                'components': manifest, 'host_command': list(map(str, sys.argv))}
    (output / 'components.json').write_text(json.dumps(metadata, indent=2) + '\n')
    argv = ['qemu-system-x86_64', '-no-user-config', '-nodefaults', '-accel', 'kvm',
            '-cpu', 'host', '-m', '4096', '-smp', '2', '-kernel', str(kernel), '-initrd', str(initrd),
            '-drive', f'file={disk},if=virtio,format=raw', '-append',
            'console=ttyS0 init=/init panic=-1 oops=panic nokaslr', '-display', 'none',
            '-serial', 'stdio', '-monitor', 'none', '-nic', 'none', '-no-reboot']
    (output / 'command.json').write_text(json.dumps({'argv': argv, 'timeout': args.timeout}, indent=2) + '\n')
    result = {'started_unix': time.time()}
    console = output / 'console.log'
    try:
        with console.open('w') as stream:
            process = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout)
        result['qemu_returncode'] = process.returncode
    except subprocess.TimeoutExpired:
        result['error'] = 'guest exceeded observation limit; retained console/disk; incomplete result'
    finally:
        evidence = output / 'evidence'
        evidence.mkdir()
        extract = subprocess.run(['debugfs', '-R', f'rdump /validation {evidence}', str(disk)],
                                 capture_output=True, text=True)
        (output / 'extraction.log').write_text(extract.stdout + extract.stderr)
        content = console.read_text()
        result['kernel_failure'] = bool(re.search(r'Kernel panic|BUG:|WARNING:', content))
        result['guest_status_zero'] = 'lz4_guest_status=0' in content
        status = evidence / 'validation/status.json'
        result['guest_record'] = json.loads(status.read_text()) if status.exists() else None
        result['status'] = 'pass' if result.get('qemu_returncode') == 0 and result['guest_status_zero'] and not result['kernel_failure'] and result['guest_record'] and result['guest_record']['status'] == 'pass' else 'fail'
        result['finished_unix'] = time.time()
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'output': str(output), **result}, indent=2))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
