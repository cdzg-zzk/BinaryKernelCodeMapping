#!/usr/bin/env python3
"""Fresh-build complete BCH with the current owner and registration code and run it in the prepared private exact119 guest."""
from pathlib import Path
import argparse
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
                        help='run the full kernel matrix with the same registered owner')
    args = parser.parse_args()
    output, prepared, kernel = map(lambda value: value.resolve(),
                                    (args.output, args.prepared, args.kernel))
    output.mkdir(parents=True, exist_ok=False)
    metadata = {'scope': 'full BCH correctness-only with current owner/registration; no paper performance samples',
                'host_euid': os.geteuid(), 'host_command': sys.argv,
                'prepared_environment': str(prepared), 'components': [], 'host_commands': []}

    def save_metadata():
        (output / 'components.json').write_text(json.dumps(metadata, indent=2) + '\n')

    def copy_file(source, target):
        source, target = Path(source), Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
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
        initrd = prepared / 'initramfs.cpio.gz'
        metadata['initramfs'] = str(initrd)
        metadata['initramfs_sha256'] = digest(initrd)
        metadata['initramfs_status_marker'] = 'lz4_guest_status (inherited generic /work/guest.py wrapper)'

        source = output / 'build-source'
        source.mkdir()
        source_root = ROOT / 'test/test_BCH'
        for directory in ('adapted', 'kmod', 'src', 'userspace', 'vendor', 'config'):
            for path in (source_root / directory).rglob('*'):
                if path.is_file() and not any(part.startswith('.') for part in path.relative_to(source_root).parts):
                    if path.name == 'Makefile' or path.suffix in {'.c', '.h', '.map', '.txt'}:
                        if path.name.endswith('.mod.c'):
                            continue
                        copy_file(path, source / path.relative_to(source_root))
        copy_file(source_root / 'Makefile', source / 'Makefile')
        logged(['make', '-C', '/lib/modules/5.15.0-119-generic/build',
                f'M={source / "kmod"}', '-j2', 'modules'], 'owner-build.log')
        owner = source / 'kmod/vkso_bch.ko'
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
                    relative = path.relative_to(prepared / 'payload')
                    current = ROOT / path.relative_to(prepared / 'payload/repo') if directory == 'repo' else path
                    copy_file(current, payload / relative)
        # These interfaces may be absent from an older prepared environment.
        for name in ('protocol.h', 'owner.h'):
            copy_file(ROOT / 'page_cache_replace' / name,
                      payload / 'repo/page_cache_replace' / name)
        copy_file(prepared / 'payload/vmlinux-5.15.0-119-generic', payload / 'vmlinux-5.15.0-119-generic')
        copy_file(owner, payload / 'owner/vkso_bch.ko')
        copy_file(source / 'config/symbols.txt', payload / 'symbols.txt')
        for name in ('bch-bench', 'libbch-kernel-native.so', 'libbch-author-standalone.so'):
            copy_file(binaries / name, payload / 'binaries' / name)
        copy_file(HERE / 'bch_guest.py', payload / 'guest.py')
        copy_file(HERE / 'lz4_guest.py', payload / 'lz4_guest_helpers.py')
        copy_file(HERE / 'bch_qemu.py', output / 'bch_qemu.py')
        from setup.prepare import prepare as prepare_setup
        prepare_setup(output, payload, copy_file)
        if args.kernel_cost:
            from kernel_cost_prepare import prepare_bch
            prepare_bch(output, payload, copy_file, source / 'kmod')
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
            result['guest_status_zero'] = 'lz4_guest_status=0' in console
            status = evidence / 'validation/status.json'
            result['guest_record'] = json.loads(status.read_text()) if status.exists() else None
            result['status'] = 'pass' if (result.get('qemu_returncode') == 0
                and result['guest_status_zero'] and not result['kernel_failure']
                and result['guest_record'] and result['guest_record']['status'] == 'pass'
                and 'bch_guest_validation=pass' in console) else 'fail'
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
