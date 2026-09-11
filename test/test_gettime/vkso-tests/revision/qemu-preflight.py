#!/usr/bin/env python3
"""Exercise revision tools on packaged kernels; QEMU data are never formal results."""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def copy_runtime(root, binary):
    binary = Path(binary)
    target = root / str(binary).lstrip('/')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, target)
    result = run(['ldd', binary], capture_output=True, text=True).stdout
    for library in re.findall(r'(/[^\s()]+)', result):
        source = Path(library)
        target = root / library.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('build', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--backend', choices=['raw', 'vkso', 'both'], default='both')
    parser.add_argument('--accel', choices=['kvm', 'tcg'], default='kvm')
    args = parser.parse_args()
    package, build, output = [p.resolve() for p in (args.package, args.build, args.output)]
    run(['sha256sum', '--quiet', '-c', 'SHA256SUMS'], cwd=package)
    output.mkdir(parents=True, exist_ok=False)
    root = output / 'initramfs'
    for folder in ['bin', 'dev', 'proc', 'sys', 'tmp', 'work', 'usr/bin', 'usr/lib']:
        (root / folder).mkdir(parents=True, exist_ok=True)
    shutil.copy2('/usr/bin/busybox', root / 'bin/busybox')
    copy_runtime(root, '/usr/bin/python3.10')
    copy_runtime(root, '/usr/bin/setarch')
    (root / 'usr/bin/python3').symlink_to('python3.10')
    shutil.copytree('/usr/lib/python3.10', root / 'usr/lib/python3.10',
                    ignore=shutil.ignore_patterns('__pycache__', 'test', 'tests'))
    # Extension dependencies used by ctypes, JSON and the collector imports.
    for extension in Path('/usr/lib/python3.10/lib-dynload').glob('*.so'):
        copy_runtime(root, extension)
    init = root / 'init'
    init.write_text('''#!/bin/busybox sh
/bin/busybox --install -s /bin
export PATH=/usr/bin:/bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t ext4 /dev/sda /work
mount -t debugfs debugfs /sys/kernel/debug
python3 -u /work/revision/qemu-guest.py
status=$?
echo revision_guest_status=$status
sync
poweroff -f
''')
    init.chmod(0o755)
    paths = b'\0'.join(str(p.relative_to(root)).encode() for p in root.rglob('*')) + b'\0'
    archive = run(['cpio', '--null', '-o', '--format=newc'], cwd=root,
                  input=paths, capture_output=True).stdout
    import gzip
    (output / 'initramfs.cpio.gz').write_bytes(gzip.compress(archive, compresslevel=1))
    for backend in (['raw', 'vkso'] if args.backend == 'both' else [args.backend]):
        payload = output / f'payload-{backend}'
        payload.mkdir()
        for name in ['raw-abi-matrix', 'vkso-abi-matrix', 'vkso-time-bench', 'libkernel.so',
                     'vkso_m09_clock.ko', 'page_cache_replace.ko', 'manager', 'page_mappings.txt']:
            shutil.copy2(package / name, payload / name)
        shutil.copy2(build / 'vkso-multireader', payload)
        shutil.copy2(build / 'kernel-reader/vkso_kernel_reader.ko', payload)
        shutil.copytree(HERE, payload / 'revision',
                        ignore=shutil.ignore_patterns('build', 'results', '__pycache__', '.git'))
        (payload / 'update-bench').mkdir()
        shutil.copy2(HERE.parent / 'update-bench/compare-update.py', payload / 'update-bench')
        (payload / 'backend').write_text(backend + '\n')
        disk = output / f'{backend}.ext4'
        with disk.open('wb') as stream:
            stream.truncate(256 * 1024 * 1024)
        run(['mkfs.ext4', '-q', '-F', '-d', payload, disk])
        log = output / f'{backend}.log'
        with log.open('w') as stream:
            run(['timeout', '600', 'qemu-system-x86_64', '-accel', args.accel,
                 '-cpu', 'host' if args.accel == 'kvm' else 'max', '-m', '1024', '-smp', '4',
                 '-kernel', package / f'{backend}-bzImage', '-initrd', output / 'initramfs.cpio.gz',
                 '-drive', f'file={disk},if=ide,format=raw',
                 '-append', 'console=ttyS0 init=/init panic=-1 oops=panic nokaslr clocksource=tsc tsc=reliable',
                 '-nographic', '-no-reboot'], stdout=stream, stderr=subprocess.STDOUT)
        content = log.read_text()
        if ('revision_guest_status=0' not in content or 'revision_preflight=pass' not in content
                or re.search(r'Kernel panic|BUG:|WARNING:', content)):
            raise RuntimeError(f'{backend} functional preflight failed: {log}')
        # Extract persistent guest evidence without mounting the image on the host.
        evidence = output / backend
        evidence.mkdir()
        run(['debugfs', '-R', f'rdump /validation {evidence}', disk], capture_output=True)
        for method in (['raw'] if backend == 'raw' else ['vkso', 'compact-split']):
            if not (evidence / 'validation' / method / 'measurements.csv').is_file():
                raise RuntimeError(f'guest evidence extraction failed: {evidence}')
        print(f'{backend} revision functional preflight passed: {log}', flush=True)
    (output / 'complete.json').write_text(json.dumps(dict(scope='QEMU functional validation only',
                                                       package=str(package), backend=args.backend), indent=2))


if __name__ == '__main__':
    main()
