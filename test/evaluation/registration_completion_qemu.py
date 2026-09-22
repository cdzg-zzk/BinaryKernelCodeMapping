#!/usr/bin/env python3
"""Run the registration transaction matrix with the full manager/module in KVM."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "make_dll"))
from build_PIC_so import elf_build_id

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--kernel', type=Path, required=True)
    parser.add_argument('--initramfs', type=Path, required=True,
                        help='exact119 initramfs from lz4_qemu; executes /work/guest.py')
    parser.add_argument('--owner', type=Path, required=True)
    parser.add_argument('--identity-variant', type=Path, help='same-source module compiled with different flags')
    parser.add_argument('--vmlinux', type=Path, default=Path('/usr/lib/debug/boot/vmlinux-5.15.0-119-generic'))
    parser.add_argument('--kernel-arg', action='append', default=[], choices=['rodata=off'])
    parser.add_argument('--reader', type=Path, default=ROOT / 'test/test_gettime/vkso-tests/revision/kernel-reader/vkso_kernel_reader.ko')
    parser.add_argument('--reader-source-dir', type=Path)
    parser.add_argument('--legacy-module', type=Path, help='required only by the historical v1 completion driver')
    parser.add_argument('--owner-source-dir', type=Path, help='optional fixture source directory to archive')
    parser.add_argument('--guest-driver', type=Path, default=HERE / 'registration_transaction_guest.py')
    args = parser.parse_args()
    if args.guest_driver.name == 'registration_completion_guest.py' and not args.legacy_module:
        parser.error('the historical v1 driver requires --legacy-module')
    out = args.output.resolve()
    assert Path('/dev/kvm').exists()
    assert not out.exists()
    out.mkdir(parents=True)
    payload = out / 'payload'
    payload.mkdir()
    inputs = {
        'manager': ROOT / 'page_cache_replace/manager',
        'vkso': ROOT / 'vkso',
        'registration_wrapper_guest.py': HERE / 'registration_wrapper_guest.py',
        'registration_file_ops_guest.py': HERE / 'registration_file_ops_guest.py',
        'page_cache_replace.ko': ROOT / 'page_cache_replace/page_cache_replace.ko',
        'vkso_lz4.ko': args.owner.resolve(),
        'vkso_kernel_reader.ko': args.reader.resolve(),
        'guest.py': args.guest_driver.resolve(),
        'registration_completion_guest.py': HERE / 'registration_completion_guest.py',
        'registration_transaction_guest.py': HERE / 'registration_transaction_guest.py',
    }
    if args.guest_driver.name == 'registration_scale_guest.py':
        clock = out / 'setup-clock'
        subprocess.run(['gcc', '-O2', str(HERE / 'setup/clock.c'), '-o', str(clock)], check=True)
        inputs['setup-clock'] = clock
        inputs['setup-clock.c'] = HERE / 'setup/clock.c'
    if args.legacy_module:
        inputs['legacy-page_cache_replace.ko'] = args.legacy_module.resolve()
    for name, path in inputs.items():
        if name.endswith('.ko'):
            magic = subprocess.check_output(['modinfo', '-F', 'vermagic', path], text=True)
            assert magic.startswith('5.15.0-119-generic '), (path, magic)
        shutil.copy2(path, payload / name)
    identity = dict(kernel_build_id=elf_build_id(args.vmlinux), owner_build_id=elf_build_id(args.owner),
                    owner_module=subprocess.check_output(['modinfo', '-F', 'name', args.owner], text=True).strip(),
                    owner_srcversion=subprocess.check_output(['modinfo', '-F', 'srcversion', args.owner], text=True).strip())
    if args.identity_variant:
        shutil.copy2(args.identity_variant, payload / 'identity-variant.ko')
        identity['variant_build_id'] = elf_build_id(args.identity_variant)
        identity['variant_srcversion'] = subprocess.check_output(['modinfo', '-F', 'srcversion', args.identity_variant], text=True).strip()
        assert identity['variant_srcversion'] == identity['owner_srcversion']
        assert identity['variant_build_id'] != identity['owner_build_id']
    (payload / 'image-identities.json').write_text(json.dumps(identity, indent=2)+'\n')
    sources = out / 'source'
    sources.mkdir()
    for name in ('page_cache_replace.c', 'manager.cpp', 'protocol.h', 'owner.h', 'Makefile'):
        shutil.copy2(ROOT / 'page_cache_replace' / name, sources / name)
    if args.owner_source_dir:
        fixture = out / 'fixture-source'
        fixture.mkdir()
        for name in ('Makefile', 'metadata.c', 'pages.S'):
            shutil.copy2(args.owner_source_dir / name, fixture / name)
        shutil.copy2(ROOT / 'page_cache_replace/owner.h', fixture / 'owner.h')
    if args.reader_source_dir:
        target = out / 'reader-source'; target.mkdir()
        for path in args.reader_source_dir.iterdir():
            if path.name == 'Makefile' or (path.suffix in ('.c', '.h') and not path.name.endswith('.mod.c')):
                shutil.copy2(path, target / path.name)
    shutil.copy2(__file__, out / Path(__file__).name)
    disk = out / 'guest.ext4'
    with disk.open('xb') as stream:
        stream.truncate(128 * 1024**2)
    subprocess.run(['mkfs.ext4', '-q', '-F', '-d', payload, disk], check=True)
    command = ['qemu-system-x86_64', '-no-user-config', '-nodefaults', '-accel', 'kvm',
               '-cpu', 'host', '-m', '2048', '-smp', '2', '-kernel', str(args.kernel.resolve()),
               '-initrd', str(args.initramfs.resolve()), '-drive', f'file={disk},if=virtio,format=raw',
               '-append', 'console=ttyS0 init=/init panic=-1 oops=panic nokaslr ' + ' '.join(args.kernel_arg),
               '-display', 'none', '-serial', 'stdio', '-monitor', 'none', '-nic', 'none', '-no-reboot']
    (out / 'command.json').write_text(json.dumps(dict(command=command,
        inputs={k: str(v) for k, v in inputs.items()}, scope='guest registration matrix; no performance trials'), indent=2)+'\n')
    record = dict(started_unix=time.time(), status='incomplete')
    try:
        with (out / 'console.log').open('w') as stream:
            process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        record['qemu_returncode'] = process.returncode
    finally:
        evidence = out / 'evidence'
        evidence.mkdir()
        result = subprocess.run(['debugfs', '-R', f'rdump /validation {evidence}', disk], capture_output=True, text=True)
        (out / 'extraction.log').write_text(result.stdout + result.stderr)
        console = (out / 'console.log').read_text()
        status = evidence / 'validation/status.json'
        record['guest_record'] = json.loads(status.read_text()) if status.exists() else None
        record['kernel_failure'] = bool(re.search(r'Kernel panic|BUG:|WARNING:', console))
        record['status'] = 'pass' if record.get('qemu_returncode') == 0 and 'lz4_guest_status=0' in console and not record['kernel_failure'] and record['guest_record'] and record['guest_record']['status'] == 'pass' else 'fail'
        record['finished_unix'] = time.time()
        (out / 'result.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record, indent=2))
    return 0 if record['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
