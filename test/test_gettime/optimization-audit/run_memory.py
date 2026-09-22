#!/usr/bin/env python3
"""Run the census in an isolated VM with the unchanged archived VKSO image."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
TESTS = HERE.parent / 'vkso-tests'


def run(argv, **kwargs):
    return subprocess.run(list(map(str, argv)), check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--candidates', type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    package = TESTS / 'baremetal/artifacts/reader-load-v4-normal'
    run(['sha256sum', '--quiet', '-c', 'SHA256SUMS'], cwd=package)
    payload = out / 'payload'
    (payload / 'revision').mkdir(parents=True)
    (payload / 'package').mkdir()
    for name in ['libkernel.so', 'page_mappings.txt', 'page_cache_replace.ko', 'manager']:
        shutil.copy2(package / name, payload / 'package' / name)
    shutil.copy2(HERE / 'memory_probe.py', payload)
    (payload / 'revision/qemu-guest.py').write_text('''import os, subprocess
from pathlib import Path
def run(*args): subprocess.run(args, check=True)
p = Path('/work/package')
run('insmod', str(p / 'page_cache_replace.ko'))
with (p / 'libkernel.so').open('rb') as stream: os.fsync(stream.fileno())
run(str(p / 'manager'), 'validate', str(p / 'libkernel.so'), str(p / 'page_mappings.txt'))
run(str(p / 'manager'), 'replace', str(p / 'libkernel.so'), str(p / 'page_mappings.txt'))
try: run('python3', '/work/memory_probe.py')
finally: run(str(p / 'manager'), 'restore', str(p / 'libkernel.so'), str(p / 'page_mappings.txt'))
run('rmmod', 'page_cache_replace')
''')
    if args.candidates:
        for name in ['baseline', 'entry-null', 'coarse-late-offset']:
            dest = payload / name
            dest.mkdir()
            shutil.copy2(args.candidates / f'{name}.so', dest / 'libkernel.so')
            for filename in ['vkso-abi-matrix', 'manager']:
                shutil.copy2(package / filename, dest / filename)
            plan = (package / 'page_mappings.txt').read_text()
            if name != 'entry-null':
                plan = '\n'.join(line for line in plan.splitlines()
                                 if line.startswith('#') or ',shared_data,' in line) + '\n'
            (dest / 'page_mappings.txt').write_text(plan)
        shutil.copy2(package / 'vkso_m09_clock.ko', payload)
        shutil.copy2(HERE / 'candidate_guest.py', payload / 'revision/qemu-guest.py')
    disk = out / 'guest.ext4'
    with disk.open('wb') as stream:
        stream.truncate(128 * 1024 * 1024)
    run(['mkfs.ext4', '-q', '-F', '-d', payload, disk])
    command = ['timeout', '180', 'qemu-system-x86_64', '-accel', 'kvm', '-cpu', 'host',
               '-m', '1024', '-smp', '4', '-kernel', package / 'vkso-bzImage',
               '-initrd', TESTS / 'revision/results/qemu-read-final/initramfs.cpio.gz',
               '-drive', f'file={disk},if=ide,format=raw', '-append',
               'console=ttyS0 init=/init panic=-1 oops=panic nokaslr clocksource=tsc tsc=reliable',
               '-nographic', '-no-reboot']
    (out / 'command.json').write_text(json.dumps(list(map(str, command)), indent=2))
    with (out / 'guest.log').open('w') as log:
        run(command, stdout=log, stderr=subprocess.STDOUT)
    log = (out / 'guest.log').read_text()
    assert ('candidate_validation=pass' if args.candidates else 'memory_probe=pass') in log and 'revision_guest_status=0' in log
    assert not re.search(r'Kernel panic|BUG:|WARNING:', log)
    run(['debugfs', '-R', f'rdump /results {out}', disk], capture_output=True)
    assert (out / ('results/candidates.json' if args.candidates else 'results/memory.json')).is_file()
    print('candidate_vm=pass' if args.candidates else 'memory_vm=pass')


if __name__ == '__main__':
    main()
