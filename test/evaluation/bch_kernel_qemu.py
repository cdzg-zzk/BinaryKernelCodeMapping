#!/usr/bin/env python3
"""Validate a BCH kernel comparison driver in private KVM, outside formal performance results."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RELEASE = '5.15.0-119-generic'


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1048576):
            value.update(chunk)
    return value.hexdigest()


def compare_algorithm_commands(build, owner_source=None):
    """Require identical compiler invocations except namespace and build paths."""
    records = []
    for directory, module_name, api_prefix in [('kmod', 'vkso_bch', 'vkso_bch_'),
                                              ('matched', 'bch_matched', 'matched_bch_')]:
        directory_path = Path(owner_source) if directory == 'kmod' and owner_source else build / directory
        text = (directory_path / '.bch_impl.o.cmd').read_text().splitlines()[0]
        argv = shlex.split(text.split(' := ', 1)[1])
        normalized = []
        for token in argv:
            token = token.replace(str(directory_path), '<module-build>')
            for api in ('init', 'free', 'encode', 'decode'):
                if token == f'-Dbch_{api}={api_prefix}{api}':
                    token = f'-Dbch_{api}=<namespace>_{api}'
            if token == f'-DKBUILD_MODNAME="{module_name}"':
                token = '-DKBUILD_MODNAME="<module>"'
            if token == '-D__KBUILD_MODNAME=kmod_' + module_name:
                token = '-D__KBUILD_MODNAME=kmod_<module>'
            normalized.append(token)
        records.append({'module': module_name, 'command': text,
                        'normalized_compiler_argv': normalized})
    assert records[0]['normalized_compiler_argv'] == records[1]['normalized_compiler_argv'], \
        'matched-source algorithm compilation differs from actual owner beyond namespace/build paths'
    return {'status': 'pass', 'allowed_differences': ['API/module namespace', 'module build directory'],
            'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--kernel', type=Path, default=Path('/tmp/vkso-guest-kernel-119/extracted/boot') / ('vmlinuz-' + RELEASE))
    parser.add_argument('--initramfs', type=Path, default=HERE / 'results/lz4-cli-qemu-20260912-attempt06/initramfs.cpio.gz')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--measure', action='store_true',
                        help='validate the full 11-round measurement path; guest timings are diagnostic only')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    metadata = {'scope': 'stock, matched-source and actual owner kernel backends; private guest validation; no host module operations',
                'host_euid': os.geteuid(), 'host_argv': sys.argv,
                'measure': args.measure, 'guest_timings_are_formal_performance': False,
                'components': [], 'commands': []}

    def save():
        (output / 'components.json').write_text(json.dumps(metadata, indent=2) + '\n')

    def copy(source, target):
        source, target = Path(source), Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        metadata['components'].append({'source': str(source),
            'target': str(target.relative_to(output)), 'sha256': digest(source),
            'bytes': source.stat().st_size})

    def command(argv, name):
        argv = list(map(str, argv))
        with (output / name).open('w') as stream:
            result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
        metadata['commands'].append({'argv': argv, 'log': name, 'returncode': result.returncode})
        save()
        if result.returncode:
            raise RuntimeError(f'preparation command failed; see {name}')

    try:
        assert os.geteuid() != 0, 'host preparation uses the ordinary repository owner'
        assert os.uname().release == RELEASE
        kernel, initramfs = args.kernel.resolve(), args.initramfs.resolve()
        package = Path('/tmp/vkso-guest-kernel-119/evidence.json')
        assert digest(kernel) == json.loads(package.read_text())['kernel_sha256']
        metadata['kernel'] = {'path': str(kernel), 'sha256': digest(kernel)}
        metadata['initramfs'] = {'path': str(initramfs), 'sha256': digest(initramfs)}
        copy(package, output / 'kernel-package-evidence.json')
        source = ROOT / 'test/test_BCH'
        build = output / 'build-source'
        for directory in ('adapted', 'kmod'):
            for path in (source / directory).rglob('*'):
                if path.is_file() and (path.name == 'Makefile' or path.suffix in ('.c', '.h')):
                    if not path.name.endswith('.mod.c'):
                        copy(path, build / path.relative_to(source))
        for path in (HERE / 'bch-kernel').iterdir():
            if path.is_file() and (path.name == 'Makefile' or path.suffix in ('.c', '.h')):
                copy(path, build / 'driver' / path.name)
        for path in (HERE / 'bch-kernel-matched').iterdir():
            if path.is_file() and (path.name == 'Makefile' or path.suffix in ('.c', '.h')):
                copy(path, build / 'matched' / path.name)
        copy(source / 'vendor/linux-5.15/lib/bch.c', build / 'original/bch.c')
        headers = Path('/lib/modules') / RELEASE / 'build'
        command(['make', '-C', headers, f'M={build / "kmod"}', '-j2', 'modules'], 'owner-build.log')
        owner = build / 'kmod/vkso_bch.ko'
        command(['pahole', '-J', '--btf_base', '/sys/kernel/btf/vmlinux', owner], 'owner-btf.log')
        command(['make', '-C', headers, f'M={build / "matched"}', '-j2', 'modules'], 'matched-build.log')
        (output / 'compiler-comparison.json').write_text(json.dumps(
            compare_algorithm_commands(build), indent=2) + '\n')
        command(['make', '-C', headers, f'M={build / "driver"}',
                 f'KBUILD_EXTRA_SYMBOLS={build / "kmod/Module.symvers"} {build / "matched/Module.symvers"}',
                 '-j2', 'modules'], 'driver-build.log')
        stock = Path('/lib/modules') / RELEASE / 'kernel/lib/bch.ko'
        payload = output / 'payload'
        for name, module in [('bch', stock), ('vkso_bch', owner),
                             ('bch_matched', build / 'matched/bch_matched.ko'),
                             ('bch_kernel_bench', build / 'driver/bch_kernel_bench.ko')]:
            copy(module, payload / 'modules' / (name + '.ko'))
            command(['modinfo', module], f'{name}-modinfo.txt')
            info = (output / f'{name}-modinfo.txt').read_text()
            assert re.search(r'^vermagic:\s+' + re.escape(RELEASE) + r'\s', info, re.M)
        command(['readelf', '-rW', build / 'driver/bch_kernel_bench.ko'], 'driver-relocations.txt')
        command(['nm', '-u', build / 'driver/bch_kernel_bench.ko'], 'driver-imports.txt')
        command(['objdump', '-drwC', '-Mintel', build / 'driver/bch_kernel_bench.ko'], 'driver-disassembly.txt')
        command(['dpkg-query', '-W', 'linux-modules-' + RELEASE, 'linux-headers-' + RELEASE], 'package-versions.txt')
        copy(HERE / 'bch_kernel_guest.py', payload / 'guest.py')
        copy(HERE / 'bch_kernel_audit.py', payload / 'bch_kernel_audit.py')
        (payload / 'configuration.json').write_text(json.dumps({
            'measure': args.measure, 'correctness_vectors': 128,
            'outer_runs': 11, 'sample_ms': 10, 'cpu': 1}, indent=2) + '\n')
        copy(Path(__file__), output / 'bch_kernel_qemu.py')
        disk = output / 'guest.ext4'
        with disk.open('wb') as stream:
            stream.truncate(256 * 1024**2)
        command(['mkfs.ext4', '-q', '-F', '-d', payload, disk], 'disk-build.log')
        argv = ['qemu-system-x86_64', '-no-user-config', '-nodefaults', '-accel', 'kvm',
                '-cpu', 'host', '-m', '2048', '-smp', '2', '-kernel', str(kernel),
                '-initrd', str(initramfs), '-drive', f'file={disk},if=virtio,format=raw',
                '-append', 'console=ttyS0 init=/init panic=-1 oops=panic nokaslr vkso_bch_kernel_guest=1',
                '-display', 'none', '-serial', 'stdio', '-monitor', 'none', '-nic', 'none', '-no-reboot']
        (output / 'command.json').write_text(json.dumps({'argv': argv, 'timeout': args.timeout}, indent=2) + '\n')
        save()
        result = {'status': 'running', 'started_unix': time.time()}
        with (output / 'console.log').open('w') as stream:
            try:
                process = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout)
                result['qemu_returncode'] = process.returncode
            except subprocess.TimeoutExpired:
                result['error'] = 'private guest exceeded observation limit; disk and console retained'
        evidence = output / 'evidence'
        evidence.mkdir()
        extraction = subprocess.run(['debugfs', '-R', f'rdump /validation {evidence}', str(disk)],
                                    capture_output=True, text=True)
        (output / 'extraction.log').write_text(extraction.stdout + extraction.stderr)
        console = (output / 'console.log').read_text()
        result['kernel_failure'] = bool(re.search(r'Kernel panic|BUG:|WARNING:', console))
        status = evidence / 'validation/status.json'
        result['guest_record'] = json.loads(status.read_text()) if status.exists() else None
        result['status'] = 'pass' if (result.get('qemu_returncode') == 0 and
            not result['kernel_failure'] and 'lz4_guest_status=0' in console and
            'bch_kernel_guest_validation=pass' in console and result['guest_record'] and
            result['guest_record']['status'] == 'pass') else 'fail'
        result['finished_unix'] = time.time()
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'output': str(output), **result}, indent=2))
        return 0 if result['status'] == 'pass' else 1
    except BaseException:
        import traceback
        metadata['preparation_error'] = traceback.format_exc()
        save()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
