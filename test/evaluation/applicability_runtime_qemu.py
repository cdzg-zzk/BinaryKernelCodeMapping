#!/usr/bin/env python3
"""Build typed applicability drivers and run a fresh private exact119 guest.

Host work uses the ordinary researcher account and isolated output files only.
The guest exports the actual built-in roots selected by its own script; this
launcher does not build or load BCH. Guest failures retain console, disk and
extracted case records. Raw functional-result auditing remains a separate step.
"""
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
import traceback


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KERNEL_RELEASE = '5.15.0-119-generic'
KERNEL = Path('/tmp/vkso-guest-kernel-119/extracted/boot') / ('vmlinuz-' + KERNEL_RELEASE)
PACKAGE_EVIDENCE = Path('/tmp/vkso-guest-kernel-119/evidence.json')
PREPARED = HERE / 'results/lz4-cli-qemu-20260912-attempt06'
KBUILD = Path('/lib/modules') / KERNEL_RELEASE / 'build'
VMLINUX_BUILD_ID = '822098bf89027e54e3aa301e90cc5b8e5c80f479'
DRIVER_FILES = ('Makefile', 'protocol.h', 'engine.h',
                'applicability_user.c', 'applicability_runtime.c')


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1048576):
            value.update(chunk)
    return value.hexdigest()


def no_other_qemu():
    # Linux comm is limited to 15 bytes; this is qemu-system-x86_64's comm.
    result = subprocess.run(['pgrep', '-x', 'qemu-system-x86'], capture_output=True, text=True)
    if result.returncode != 1:
        raise RuntimeError('serialize private guests: ' + (
            'QEMU PID(s) ' + result.stdout.strip() if result.returncode == 0 else result.stderr.strip()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepared', type=Path, default=PREPARED)
    parser.add_argument('--kernel', type=Path, default=KERNEL)
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    output, prepared, kernel = (path.resolve() for path in (args.output, args.prepared, args.kernel))
    if os.geteuid() == 0:
        raise RuntimeError('host preparation must use the ordinary researcher account')
    no_other_qemu()
    output.mkdir(parents=True, exist_ok=False)
    metadata = {
        'scope': 'actual built-in xxh32/sort export and typed functional checks; no performance samples',
        'host_euid': os.geteuid(), 'host_kernel': os.uname().release,
        'host_command': sys.argv, 'prepared_environment': str(prepared),
        'components': [], 'host_commands': [],
        'guest_isolation': 'KVM, no network, private disk, no host filesystem sharing',
    }
    result = {'status': 'running', 'stage': 'host-preparation', 'started_unix': time.time(),
              'scope': 'launcher and guest execution status; independent raw-result audit is separate'}

    def save():
        (output / 'components.json').write_text(json.dumps(metadata, indent=2) + '\n')
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

    def copy_file(source, target):
        source, target = Path(source), Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        # Identify the bytes actually copied, including executable permission bits.
        metadata['components'].append({
            'source': str(source.resolve()), 'target': str(target.relative_to(output)),
            'sha256': digest(target), 'bytes': target.stat().st_size,
            'mode': oct(target.stat().st_mode & 0o777),
        })

    def logged(argv, name, cwd=None, check=True):
        argv = list(map(str, argv))
        with (output / name).open('w') as stream:
            command_result = subprocess.run(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        metadata['host_commands'].append({
            'argv': argv, 'cwd': str(cwd) if cwd else None,
            'log': name, 'returncode': command_result.returncode,
        })
        save()
        if check and command_result.returncode:
            raise RuntimeError(f'host command exited {command_result.returncode}; see {name}')
        return command_result.returncode

    save()
    try:
        if os.uname().release != KERNEL_RELEASE:
            raise RuntimeError('this prepared experiment requires the exact119 host/header environment')
        if not os.access('/dev/kvm', os.R_OK | os.W_OK):
            raise RuntimeError('ordinary-user access to /dev/kvm is unavailable')
        if not KBUILD.is_dir():
            raise RuntimeError(f'exact119 Kbuild directory is unavailable: {KBUILD}')
        copy_file(__file__, output / 'applicability_runtime_qemu.py')
        copy_file(PACKAGE_EVIDENCE, output / 'kernel-package-evidence.json')
        package = json.loads((output / 'kernel-package-evidence.json').read_text())
        if package['version'] != '5.15.0-119.129' or digest(kernel) != package['kernel_sha256']:
            raise RuntimeError('guest kernel differs from the recorded exact119 public package')
        metadata.update(kernel=str(kernel), kernel_sha256=package['kernel_sha256'],
                        kernel_package_version=package['version'])
        initrd = prepared / 'initramfs.cpio.gz'
        metadata.update(initramfs=str(initrd), initramfs_sha256=digest(initrd),
                        initramfs_status_marker='lz4_guest_status (inherited /work/guest.py init wrapper)')
        logged(['git', '-C', ROOT, 'rev-parse', 'HEAD'], 'repo-commit.log')
        logged(['gcc', '--version'], 'compiler.log')

        source_root = HERE / 'applicability-runtime'
        for name in DRIVER_FILES:
            if not (source_root / name).is_file():
                raise RuntimeError(f'driver source is not ready: {source_root / name}')
        source = output / 'build-source'
        source.mkdir()
        for path in sorted(source_root.rglob('*')):
            relative = path.relative_to(source_root)
            if path.is_file() and not any(part.startswith('.') for part in relative.parts):
                if (path.name == 'Makefile' or path.suffix in {'.c', '.h', '.S', '.mk', '.md'}) and not path.name.endswith('.mod.c'):
                    copy_file(path, source / relative)
        # protocol.h and engine.h keep their original paths relative to both C files.
        result['stage'] = 'driver-build'
        logged(['make', '-C', source, f'KDIR={KBUILD}', 'V=1', 'all'], 'driver-build.log')
        driver_module = source / 'applicability_runtime.ko'
        logged(['modinfo', '-F', 'vermagic', driver_module], 'driver-vermagic.log')
        logged(['modinfo', '-F', 'license', driver_module], 'driver-license.log')
        if not (output / 'driver-vermagic.log').read_text().startswith(KERNEL_RELEASE + ' '):
            raise RuntimeError('test module vermagic does not match exact119')
        if (output / 'driver-license.log').read_text().strip() != 'GPL':
            raise RuntimeError('test module must declare its GPL license')
        binaries = output / 'binaries'
        for name in ('applicability-user', 'applicability_runtime.ko'):
            copy_file(source / name, binaries / name)

        result['stage'] = 'payload-preparation'
        payload = output / 'payload'
        payload.mkdir()
        for directory in ('repo', 'helpers'):
            directory_source = prepared / 'payload' / directory
            if not directory_source.is_dir():
                raise RuntimeError(f'prepared guest directory missing: {directory_source}')
            for path in sorted(directory_source.rglob('*')):
                if path.is_file():
                    relative = path.relative_to(prepared / 'payload')
                    source_path = ROOT / path.relative_to(directory_source) if directory == 'repo' else path
                    copy_file(source_path, payload / relative)
        # Prepared directories supply the runtime environment, while the
        # current source and compiled product supply the implementation.
        for name in ('protocol.h', 'owner.h', 'page_cache_replace.c', 'manager.cpp', 'Makefile'):
            copy_file(ROOT / 'page_cache_replace' / name,
                      payload / 'repo/page_cache_replace' / name)
        metadata['product_source'] = 'current worktree files and binaries; prepared helpers/runtime only'
        vmlinux = payload / ('vmlinux-' + KERNEL_RELEASE)
        copy_file(prepared / 'payload' / vmlinux.name, vmlinux)
        logged(['readelf', '-n', vmlinux], 'vmlinux-notes.txt')
        build_ids = re.findall(r'Build ID:\s*(\S+)', (output / 'vmlinux-notes.txt').read_text())
        if build_ids != [VMLINUX_BUILD_ID]:
            raise RuntimeError(f'prepared vmlinux does not match the exact119 debug image: {build_ids}')
        metadata['vmlinux_build_id'] = VMLINUX_BUILD_ID
        for name in ('applicability-user', 'applicability_runtime.ko'):
            copy_file(binaries / name, payload / 'runtime' / name)
        for name in ('protocol.h', 'types_check.c'):
            copy_file(source / name, payload / 'runtime' / name)
        copy_file(HERE / 'applicability_runtime_guest.py', payload / 'guest.py')
        copy_file(HERE / 'lz4_guest.py', payload / 'lz4_guest_helpers.py')

        result['stage'] = 'disk-preparation'
        disk = output / 'guest.ext4'
        with disk.open('wb') as stream:
            stream.truncate(3 * 1024**3)
        logged(['mkfs.ext4', '-q', '-F', '-d', payload, disk], 'disk-build.log')
        # Preparation can take time; recheck serialization before launching our guest.
        no_other_qemu()
        argv = ['qemu-system-x86_64', '-no-user-config', '-nodefaults', '-accel', 'kvm',
                '-cpu', 'host', '-m', '4096', '-smp', '2', '-kernel', str(kernel),
                '-initrd', str(initrd), '-drive', f'file={disk},if=virtio,format=raw',
                '-append', 'console=ttyS0 init=/init panic=-1 oops=panic nokaslr',
                '-display', 'none', '-serial', 'stdio', '-monitor', 'none',
                '-nic', 'none', '-no-reboot']
        (output / 'command.json').write_text(json.dumps({'argv': argv, 'timeout': args.timeout}, indent=2) + '\n')
        result.update(stage='guest-running', guest_started_unix=time.time())
        save()
        try:
            with (output / 'console.log').open('w') as stream:
                guest = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout)
            result['qemu_returncode'] = guest.returncode
        except subprocess.TimeoutExpired:
            result.update(timed_out=True, error='guest observation limit exceeded; console and private disk retained')
        finally:
            result['stage'] = 'evidence-extraction'
            evidence = output / 'evidence'
            evidence.mkdir()
            # A fixed debugfs command plus cwd also supports output paths containing spaces.
            result['extraction_returncode'] = logged(
                ['debugfs', '-R', 'rdump /validation .', disk], 'extraction.log', cwd=evidence, check=False)
            console = (output / 'console.log').read_text(errors='replace')
            result['kernel_failure'] = bool(re.search(r'Kernel panic|BUG:|WARNING:', console))
            result['initramfs_statuses'] = re.findall(r'^lz4_guest_status=(\d+)\s*$', console, re.M)
            result['guest_markers'] = re.findall(r'^applicability_runtime_guest=(pass|fail)\s*$', console, re.M)
            status_path = evidence / 'validation/status.json'
            result['guest_record'] = json.loads(status_path.read_text()) if status_path.exists() else None
            passed = (result.get('qemu_returncode') == 0 and result['extraction_returncode'] == 0
                      and result['initramfs_statuses'] == ['0'] and result['guest_markers'] == ['pass']
                      and not result['kernel_failure'] and result['guest_record'] is not None
                      and result['guest_record']['status'] == 'pass')
            result.update(status='pass' if passed else 'fail', stage='finished', finished_unix=time.time())
            save()
    except BaseException:
        result.update(status='fail', error_traceback=traceback.format_exc(), finished_unix=time.time())
        metadata['failure_stage'] = result['stage']
        save()
    print(json.dumps({'output': str(output), **result}, indent=2))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
