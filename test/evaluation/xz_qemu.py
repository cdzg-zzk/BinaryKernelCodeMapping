#!/usr/bin/env python3
"""Fresh-build complete XZ with the current owner and registration code and run it in the prepared private exact119 guest."""
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
PREPARED = HERE / 'results/lz4-transaction-qemu-20260912-attempt02'
KERNEL = Path('/tmp/vkso-guest-kernel-119/extracted/boot/vmlinuz-5.15.0-119-generic')


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1048576):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepared', type=Path, default=PREPARED)
    parser.add_argument('--kernel', type=Path, default=KERNEL)
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--kernel-cost', action='store_true',
                        help='validate three kernel backends in the same registration')
    args = parser.parse_args()
    output, prepared, kernel = map(lambda value: value.resolve(),
                                    (args.output, args.prepared, args.kernel))
    output.mkdir(parents=True, exist_ok=False)
    metadata = {'scope': 'full XZ workload with current owner/registration; guest timings are diagnostic only',
                'host_euid': os.geteuid(), 'host_command': sys.argv,
                'prepared_environment': str(prepared), 'components': [], 'host_commands': []}

    def save_metadata():
        (output / 'components.json').write_text(json.dumps(metadata, indent=2) + '\n')

    def copy_file(source, target):
        source, target = Path(source), Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink():
            target.unlink()
        shutil.copy2(source, target)
        metadata['components'].append({'source': str(source),
            'target': str(target.relative_to(output)), 'sha256': digest(source),
            'bytes': source.stat().st_size})

    def logged(argv, name):
        argv = list(map(str, argv))
        with (output / name).open('w') as stream:
            result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
        metadata['host_commands'].append({'argv': argv, 'log': name, 'returncode': result.returncode})
        save_metadata()
        if result.returncode:
            raise RuntimeError(f'host build/copy command failed; see {name}')

    try:
        assert os.geteuid() != 0, 'host preparation uses the ordinary researcher account'
        metadata['host_kernel_for_btf'] = os.uname().release
        assert os.uname().release == '5.15.0-119-generic'
        package = json.loads(Path('/tmp/vkso-guest-kernel-119/evidence.json').read_text())
        assert digest(kernel) == package['kernel_sha256']
        copy_file('/tmp/vkso-guest-kernel-119/evidence.json', output / 'kernel-package-evidence.json')
        metadata['kernel'] = str(kernel)
        metadata['kernel_sha256'] = package['kernel_sha256']
        base = prepared / 'initramfs.cpio.gz'
        metadata['base_initramfs'] = str(base)
        metadata['base_initramfs_sha256'] = digest(base)
        initroot = output / 'initramfs'
        initroot.mkdir()
        archive = gzip.decompress(base.read_bytes())
        listing = subprocess.run(['cpio', '-it'], input=archive, check=True,
                                 capture_output=True).stdout.decode().splitlines()
        assert all(not name.startswith('/') and '..' not in Path(name).parts for name in listing)
        subprocess.run(['cpio', '-id', '--no-absolute-filenames', '--no-preserve-owner'],
                       cwd=initroot, input=archive, capture_output=True, check=True)
        for name in ('xz', 'taskset'):
            source = Path(shutil.which(name))
            target = initroot / 'usr/bin' / name
            if target.is_symlink():
                target.unlink()
            copy_file(source, target)
            dependencies = subprocess.run(['ldd', source], text=True,
                                          capture_output=True, check=True).stdout
            for dependency in re.findall(r'(/[^\s()]+)', dependencies):
                copy_file(dependency, initroot / dependency.lstrip('/'))
        init = initroot / 'init'
        init.write_text(init.read_text().replace('lz4_guest_status', 'xz_guest_status'))
        paths = b'\0'.join(str(path.relative_to(initroot)).encode()
                          for path in initroot.rglob('*')) + b'\0'
        rebuilt = subprocess.run(['cpio', '--null', '-o', '--format=newc', '--owner=0:0'],
            cwd=initroot, input=paths, capture_output=True, check=True).stdout
        initrd = output / 'initramfs.cpio.gz'
        initrd.write_bytes(gzip.compress(rebuilt, compresslevel=1))
        metadata['initramfs'] = str(initrd)
        metadata['initramfs_sha256'] = digest(initrd)
        for name in ('apt-package-metadata.txt', 'installed-package.txt'):
            copy_file(Path('/tmp/vkso-guest-kernel-119') / name, output / 'kernel-package-evidence' / name)
        for path in (prepared / 'environment-evidence').rglob('*'):
            if path.is_file():
                copy_file(path, output / 'environment-evidence' / path.relative_to(prepared / 'environment-evidence'))

        source = output / 'build-source'
        source.mkdir()
        source_root = ROOT / 'test/test_xz'
        for directory in ('kmod', 'src', 'userspace', 'config', 'scripts'):
            for path in (source_root / directory).rglob('*'):
                if path.is_file() and not any(part.startswith('.') for part in path.relative_to(source_root).parts):
                    if path.name == 'Makefile' or path.suffix in {'.c', '.h', '.map', '.txt', '.py', '.sh'}:
                        if path.name.endswith('.mod.c'):
                            continue
                        copy_file(path, source / path.relative_to(source_root))
        copy_file(source_root / 'Makefile', source / 'Makefile')
        for name in ('run.sh', 'run_under_replacement.sh'):
            copy_file(source_root / name, source / name)
        logged(['make', '-C', '/lib/modules/5.15.0-119-generic/build',
                f'M={source / "kmod"}', '-j2', 'modules'], 'owner-build.log')
        owner = source / 'kmod/vkso_xz.ko'
        logged(['pahole', '-J', '--skip_encoding_btf_enum64', '--btf_base', '/sys/kernel/btf/vmlinux', owner], 'owner-btf.log')
        logged(['modinfo', '-F', 'vermagic', owner], 'owner-vermagic.log')
        assert (output / 'owner-vermagic.log').read_text().startswith('5.15.0-119-generic ')
        binaries = output / 'binaries'
        logged(['make', '-C', source, f'BUILD_DIR={binaries}', '-j2', 'all'], 'userspace-build.log')

        payload = output / 'payload'
        payload.mkdir()
        for directory in ('repo', 'helpers'):
            for path in (prepared / 'payload' / directory).rglob('*'):
                if path.is_file():
                    if directory == 'repo':
                        current = ROOT / path.relative_to(prepared / 'payload/repo')
                        path = current
                    target = (payload / 'repo' / path.relative_to(ROOT)) if directory == 'repo' else (payload / path.relative_to(prepared / 'payload'))
                    copy_file(path, target)
        # These interfaces may be absent from an older prepared environment.
        for name in ('protocol.h', 'owner.h'):
            copy_file(ROOT / 'page_cache_replace' / name,
                      payload / 'repo/page_cache_replace' / name)
        copy_file(prepared / 'payload/vmlinux-5.15.0-119-generic', payload / 'vmlinux-5.15.0-119-generic')
        copy_file(owner, payload / 'owner/vkso_xz.ko')
        copy_file(source / 'config/symbols.txt', payload / 'symbols.txt')
        for name in ('xz-bench', 'libxz-native.so'):
            copy_file(binaries / name, payload / 'binaries' / name)
        for name in ('prepare_corpus.sh', 'audit_kernel_dso.py'):
            copy_file(source / 'scripts' / name, payload / 'scripts' / name)
        for path in (source / 'src').rglob('*'):
            if path.is_file():
                copy_file(path, payload / 'benchmark-source/src' / path.name)
        for original in ('/bin/bash', '/usr/bin/python3', '/usr/lib/x86_64-linux-gnu/libc.so.6'):
            copy_file(original, payload / 'inputs' / Path(original).name)
        copy_file(HERE / 'xz_guest.py', payload / 'guest.py')
        copy_file(HERE / 'lz4_guest.py', payload / 'lz4_guest_helpers.py')
        copy_file(HERE / 'xz_qemu.py', output / 'xz_qemu.py')
        from setup.prepare import prepare as prepare_setup
        prepare_setup(output, payload, copy_file)
        if args.kernel_cost:
            from kernel_cost_prepare import prepare as prepare_kernel_cost
            prepare_kernel_cost('xz', output, payload, copy_file, source / 'kmod')
        disk = output / 'guest.ext4'
        with disk.open('wb') as stream:
            stream.truncate(3 * 1024**3)
        logged(['mkfs.ext4', '-q', '-F', '-d', payload, disk], 'disk-build.log')
        save_metadata()
        argv = ['qemu-system-x86_64', '-no-user-config', '-nodefaults', '-accel', 'kvm',
                '-cpu', 'host', '-m', '4096', '-smp', '2', '-kernel', str(kernel),
                '-initrd', str(initrd), '-drive', f'file={disk},if=virtio,format=raw',
                '-append', 'console=ttyS0 init=/init panic=-1 oops=panic nokaslr',
                '-display', 'none', '-serial', 'stdio', '-monitor', 'none',
                '-nic', 'none', '-no-reboot']
        (output / 'command.json').write_text(json.dumps({'argv': argv, 'timeout': args.timeout}, indent=2) + '\n')
        result = {'status': 'running', 'started_unix': time.time()}
        try:
            with (output / 'console.log').open('w') as stream:
                process = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT,
                                         timeout=args.timeout)
            result['qemu_returncode'] = process.returncode
        except subprocess.TimeoutExpired:
            result['error'] = 'guest observation limit exceeded; console/disk retained'
        finally:
            evidence = output / 'evidence'
            evidence.mkdir()
            extraction = subprocess.run(['debugfs', '-R', f'rdump /validation {evidence}', str(disk)],
                                        capture_output=True, text=True)
            (output / 'extraction.log').write_text(extraction.stdout + extraction.stderr)
            console = (output / 'console.log').read_text()
            result['kernel_failure'] = bool(re.search(r'Kernel panic|BUG:|WARNING:', console))
            result['guest_status_zero'] = 'xz_guest_status=0' in console
            status = evidence / 'validation/status.json'
            result['guest_record'] = json.loads(status.read_text()) if status.exists() else None
            result['status'] = 'pass' if (result.get('qemu_returncode') == 0
                and result['guest_status_zero'] and not result['kernel_failure']
                and result['guest_record'] and result['guest_record']['status'] == 'pass'
                and 'xz_guest_validation=pass' in console) else 'fail'
            result['finished_unix'] = time.time()
            (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'output': str(output), **result}, indent=2))
        return 0 if result['status'] == 'pass' else 1
    except BaseException:
        import traceback
        metadata['preparation_error'] = traceback.format_exc()
        save_metadata()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
