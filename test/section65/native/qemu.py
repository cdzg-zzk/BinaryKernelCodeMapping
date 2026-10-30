#!/usr/bin/env python3
"""Exercise the exact runner in a disposable VM; never use these timings as evidence."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import time

SECTION = Path(__file__).resolve().parents[1]
ROOT = SECTION.parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--kernel', type=Path, default=ROOT / 'test/evaluation-local/environment/kernel119/vmlinuz-5.15.0-119-generic')
    p.add_argument('--timeout', type=int, default=1800)
    p.add_argument('--native-ide', action='store_true', help='use built-in PIIX ATA instead of the Ubuntu virtio module')
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    payload = out / 'payload'
    payload.mkdir()
    shutil.copytree(a.package, payload / 'package',
                    ignore=shutil.ignore_patterns('runtime', '__pycache__'))
    (payload / 'guest.py').write_text('''import subprocess
raise SystemExit(subprocess.call(['bash','/work/package/run.sh','--functional',
    '--blocks','1','--repeats','1','--client-cpu','0','--server-cpu','1','--output','/work/evidence']))
''')
    disk = out / 'guest.ext4'
    with disk.open('wb') as stream:
        stream.truncate(2048 << 20)
    subprocess.run(['mkfs.ext4', '-q', '-F', '-m', '0', '-d', str(payload), str(disk)], check=True)
    initrd = ROOT / 'test/evaluation/results/lz4-cli-qemu-20260912-attempt06/initramfs.cpio.gz'
    if a.native_ide:
        overlay = out / 'init-overlay'
        overlay.mkdir()
        init = (initrd.parent / 'initramfs/init').read_text()
        init = init.replace('insmod /guest-drivers/virtio_blk.ko\n', '').replace('/dev/vda', '/dev/sda')
        (overlay / 'init').write_text(init)
        (overlay / 'init').chmod(0o755)
        cpio = subprocess.run(['cpio', '--null', '-o', '--format=newc'], input=b'init\0',
                              cwd=overlay, capture_output=True, check=True).stdout
        combined = out / 'native-initramfs.cpio.gz'
        combined.write_bytes(initrd.read_bytes() + gzip.compress(cpio, compresslevel=1, mtime=0))
        initrd = combined
    command = ['qemu-system-x86_64', '-name', 'iso-functional,debug-threads=on',
               '-no-user-config', '-nodefaults', '-accel', 'tcg,thread=multi',
               '-cpu', 'max', '-m', '2048', '-smp', '2', '-kernel', str(a.kernel.resolve()),
               '-initrd', str(initrd), '-drive', f'file={disk},if={"ide" if a.native_ide else "virtio"},format=raw',
               '-append', 'console=ttyS0 init=/init panic=1 oops=panic nokaslr',
               '-display', 'none', '-serial', 'stdio', '-monitor', 'none', '-nic', 'none', '-no-reboot']
    record = dict(status='running', scope='functional validation only; TCG timings invalid for performance claims',
                  command=command, started=time.time())
    write = lambda: (out / 'run.json').write_text(json.dumps(record, indent=2) + '\n')
    write()
    with (out / 'console.log').open('w') as stream:
        try:
            record['returncode'] = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=a.timeout).returncode
        except subprocess.TimeoutExpired:
            record['returncode'] = 'timeout'
    with (out / 'extraction.log').open('w') as stream:
        subprocess.run(['debugfs', '-R', f'rdump /evidence {out}', str(disk)], stdout=stream, stderr=subprocess.STDOUT, check=True)
    result = out / 'evidence/result.json'
    record['guest'] = json.loads(result.read_text()) if result.exists() else None
    console = (out / 'console.log').read_text(errors='replace')
    record['status'] = 'complete' if (record['returncode'] == 0 and record['guest'] and
        record['guest']['status'] == 'complete' and 'lz4_guest_status=0' in console and
        not any(s in console for s in ('BUG:', 'Oops:', 'Kernel panic'))) else 'failed'
    record['finished'] = time.time()
    write()
    print(json.dumps(record))
    raise SystemExit(record['status'] != 'complete')


if __name__ == '__main__':
    main()
