#!/usr/bin/env python3
"""Run the registration fixture using existing packaged modules in a private VM."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REVISION = ROOT / 'test/test_gettime/vkso-tests/revision'
PACKAGE = REVISION.parent / 'baremetal/artifacts/reader-load-v4-normal'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--case', choices=('normal', 'partial-failure'), default='normal')
    args = p.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run(['sha256sum', '--quiet', '-c', 'SHA256SUMS'], cwd=PACKAGE, check=True)
    payload = output / 'payload'
    (payload / 'revision').mkdir(parents=True)
    for name in ['manager', 'page_cache_replace.ko', 'vkso_m09_clock.ko']:
        shutil.copy2(PACKAGE / name, payload / name)
    shutil.copy2(REVISION / 'build/kernel-reader/vkso_kernel_reader.ko', payload)
    guest = Path(__file__).with_name('registration_guest.py')
    if args.case == 'partial-failure':
        shutil.copy2(guest, payload / 'revision/registration_guest.py')
        guest = Path(__file__).with_name('registration_partial_guest.py')
    shutil.copy2(guest, payload / 'revision/qemu-guest.py')
    disk = output / 'guest.ext4'
    with disk.open('xb') as f:
        f.truncate(128 * 1024 * 1024)
    subprocess.run(['mkfs.ext4', '-q', '-F', '-d', str(payload), str(disk)], check=True)
    command = ['qemu-system-x86_64', '-accel', 'kvm', '-cpu', 'host', '-m', '1024', '-smp', '2',
               '-kernel', str(PACKAGE / 'vkso-bzImage'), '-initrd',
               str(REVISION / 'results/qemu-read-final/initramfs.cpio.gz'),
               '-drive', f'file={disk},if=ide,format=raw', '-nic', 'none',
               '-append', 'console=ttyS0 init=/init panic=-1 oops=panic nokaslr clocksource=tsc tsc=reliable',
               '-nographic', '-no-reboot']
    (output / 'run.json').write_text(json.dumps({'command': command, 'package': str(PACKAGE), 'case': args.case,
        'scope': 'disposable guest mechanism validation; no host module load or performance measurement'}, indent=2) + '\n')
    evidence = output / 'evidence'
    try:
        with (output / 'console.log').open('w') as f:
            process = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, timeout=180)
    finally:
        evidence.mkdir()
        with (output / 'extraction.log').open('w') as f:
            subprocess.run(['debugfs', '-R', f'rdump /validation {evidence}', str(disk)],
                           stdout=f, stderr=subprocess.STDOUT, check=True)
    content = (output / 'console.log').read_text()
    marker = 'registration_fixture=pass' if args.case == 'normal' else 'registration_observation=complete'
    if process.returncode or marker not in content or 'revision_guest_status=0' not in content:
        raise RuntimeError('guest fixture did not complete; console and extracted evidence retained')
    if re.search(r'Kernel panic|BUG:|WARNING:', content):
        raise RuntimeError('guest kernel diagnostic requires inspection; evidence retained')
    print((evidence / 'validation/observations.json').read_text())


if __name__ == '__main__':
    main()
