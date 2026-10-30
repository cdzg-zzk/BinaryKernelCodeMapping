#!/usr/bin/env python3
"""Run the unmodified isofs reference in a private guest without host mounts."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--module', type=Path, default=HERE / 'build/raw/isofs_probe.ko')
    p.add_argument('--fstype', default='iso9660')
    p.add_argument('--dependency', type=Path)
    p.add_argument('--export', action='store_true', help='run the VKSO registration and full-task checks')
    p.add_argument('--fuse-debug', action='store_true', help='also check FUSE mounts and GDB on shared instructions')
    p.add_argument('--adapted', type=Path, default=HERE / 'build/adapted')
    p.add_argument('--bridge', type=Path, help='reuse an existing adapter binary with a different owner build')
    p.add_argument('--maintenance', type=Path, help='long-Joliet fixture directory; requires fixed owner and --fuse-debug')
    p.add_argument('--registration-mode', choices=('hold','oneshot'), default='hold')
    args = p.parse_args()
    if args.fuse_debug and not args.export:
        p.error('--fuse-debug requires --export')
    if args.maintenance and not args.fuse_debug:
        p.error('--maintenance requires --fuse-debug')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    payload = out / 'payload'
    payload.mkdir()
    shutil.copy2(HERE / 'reference_guest.py', payload / 'guest.py')
    shutil.copy2(args.module, payload / args.module.name)
    if args.dependency: shutil.copy2(args.dependency,payload/args.dependency.name)
    (payload / 'config.json').write_text(json.dumps(dict(module=args.module.name, fstype=args.fstype,
                                                       dependency=args.dependency.name if args.dependency else None)))
    (payload / 'images').mkdir()
    for source in (HERE / 'build/images').glob('*.iso'):
        shutil.copy2(source, payload / 'images' / source.name)
    if args.export:
        (payload/'registration-mode').write_text(args.registration_mode+'\n')
        shutil.copy2(HERE/'build/raw/isofs_probe.ko',payload/'isofs_probe.ko')
        shutil.copy2(HERE/'export_guest.py',payload/'guest.py')
        for name in ('check_user.py','reference_guest.py'):
            shutil.copy2(HERE/name,payload/name)
        for name in ('vkso_iso_core.ko','vkso_isofs.ko','libiso-bridge.so','libisofs-copy.so','symbols.txt','shim.txt'):
            shutil.copy2(args.adapted/name,payload/name)
        if args.bridge:
            shutil.copy2(args.bridge,payload/'libiso-bridge.so')
        shutil.copy2(ROOT/'kernel_cgd/src/krg',payload/'krg')
        shutil.copy2(ROOT/'make_dll/build_PIC_so.py',payload/'build_PIC_so.py')
        shutil.copy2('/usr/lib/debug/boot/vmlinux-5.15.0-119-generic',payload/'vmlinux')
        for name in ('manager','page_cache_replace.ko'):
            shutil.copy2(ROOT/'page_cache_replace'/name,payload/name)
        shutil.copy2(ROOT/'test/test_gettime/vkso-tests/revision/kernel-reader/vkso_kernel_reader.ko',
                     payload/'vkso_kernel_reader.ko')
        shutil.copytree(ROOT/'test/evaluation-local/runs/iso9660/reference-01/evidence',payload/'reference')
        if args.fuse_debug:
            for name in ('check_fuse.py','fuse_gdb.py','export_guest.py'):
                shutil.copy2(HERE/name,payload/name)
            shutil.copy2(HERE/'build/fuse/vkso-isofuse',payload/'vkso-isofuse')
            shutil.copy2('/usr/lib/x86_64-linux-gnu/libfuse3.so.3',payload/'libfuse3.so.3')
            source=payload/'debug-source';source.mkdir()
            for f in args.adapted.glob('*'):
                if f.suffix in ('.c','.h'):shutil.copy2(f,source/f.name)
            for name in ('fuse_frontend.c','user_bridge.c'):shutil.copy2(HERE/name,source/name)
            symbols=subprocess.check_output(['nm','--defined-only',str(payload/'vkso_iso_core.ko')],text=True)
            offset=next(int(l.split()[0],16) for l in symbols.splitlines() if l.split()[-1]=='isofs_get_blocks')
            (payload/'debug-layout.json').write_text(json.dumps(dict(isofs_get_blocks=offset,
                source_prefixes=[str(args.adapted.resolve()),str(HERE)])))
            if args.maintenance:
                (payload/'maintenance').mkdir()
                for name in ('long-joliet.iso','expected.json','backport.json'):
                    shutil.copy2(args.maintenance/name,payload/'maintenance'/name)
                shutil.copy2(HERE/'maintenance/check_mount.py',payload/'check_maintenance.py')
                shutil.copy2(HERE/'build/adapted/libisofs-copy.so',payload/'maintenance-before.so')
    disk = out / 'guest.ext4'
    with disk.open('wb') as f:
        f.truncate((2048 if args.export else 256) << 20)
    subprocess.run(['mkfs.ext4', '-q', '-F', '-m', '0', '-d', str(payload), str(disk)], check=True)
    kernel = ROOT / 'test/evaluation-local/environment/kernel119/vmlinuz-5.15.0-119-generic'
    initrd = ROOT / 'test/evaluation/results/lz4-cli-qemu-20260912-attempt06/initramfs.cpio.gz'
    command = ['qemu-system-x86_64', '-name', 'iso-reference,debug-threads=on',
               '-no-user-config', '-nodefaults',
               '-accel', 'tcg,thread=multi', '-cpu', 'max', '-m', '2048', '-smp', '2',
               '-kernel', str(kernel), '-initrd', str(initrd),
               '-drive', f'file={disk},if=virtio,format=raw',
               '-append', 'console=ttyS0 init=/init panic=-1 oops=panic nokaslr',
               '-display', 'none', '-serial', 'stdio', '-monitor', 'none', '-nic', 'none', '-no-reboot']
    record = dict(status='running', command=command, started=time.time(),
                  scope='TCG functional oracle only; not native performance evidence')
    (out / 'run.json').write_text(json.dumps(record, indent=2) + '\n')
    with (out / 'console.log').open('w') as f:
        try:
            r = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, timeout=args.timeout)
            record['returncode'] = r.returncode
        except subprocess.TimeoutExpired:
            record['returncode'] = 'timeout'
    with (out / 'extraction.log').open('w') as f:
        subprocess.run(['debugfs', '-R', f'rdump /evidence {out}', str(disk)],
                       stdout=f, stderr=subprocess.STDOUT, check=True)
    result = out / 'evidence/result.json'
    record['guest'] = json.loads(result.read_text()) if result.exists() else None
    text = (out / 'console.log').read_text(errors='replace')
    record['status'] = ('complete' if record['returncode'] == 0 and record['guest'] and
                        record['guest']['status'] == 'complete' and
                        'lz4_guest_status=0' in text and
                        not any(s in text for s in ('Kernel panic', 'BUG:', 'Oops:')) else 'failed')
    record['finished'] = time.time()
    (out / 'run.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'status': record['status'], 'output': str(out)}))
    raise SystemExit(0 if record['status'] == 'complete' else 1)


if __name__ == '__main__':
    main()
