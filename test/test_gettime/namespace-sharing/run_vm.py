#!/usr/bin/env python3
"""Run the new full kernel in KVM; no host module/boot changes."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE=Path(__file__).resolve().parent


def run(args,**kwargs):return subprocess.run(list(map(str,args)),check=True,**kwargs)


def main():
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    package=a.package.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    payload=out/'payload';(payload/'package').mkdir(parents=True);(payload/'revision').mkdir()
    for name in ['libkernel.so','page_mappings.txt','manager','page_cache_replace.ko','vkso_m09_clock.ko','page_refs.ko','vkso-abi-matrix','vkso-time-bench']:
        shutil.copy2(package/name,payload/'package'/name)
    shutil.copy2(HERE/'guest.py',payload/'revision/qemu-guest.py')
    shutil.copy2(HERE/'probe.py',payload/'probe.py')
    shutil.copy2(HERE.parent/'optimization-audit/memory_probe.py',payload/'memory_probe.py')
    disk=out/'guest.ext4'
    with disk.open('wb') as f:f.truncate(128*1024*1024)
    run(['mkfs.ext4','-q','-F','-d',payload,disk])
    command=['timeout','300','qemu-system-x86_64','-accel','kvm','-cpu','host','-m','1024','-smp','4',
        '-kernel',package/'vkso-bzImage','-initrd',HERE.parent/'vkso-tests/revision/results/qemu-read-final/initramfs.cpio.gz',
        '-drive',f'file={disk},if=ide,format=raw','-append','console=ttyS0 init=/init panic=-1 oops=panic nokaslr clocksource=tsc tsc=reliable',
        '-nographic','-no-reboot']
    (out/'command.json').write_text(json.dumps(list(map(str,command)),indent=2))
    with (out/'guest.log').open('w') as f:run(command,stdout=f,stderr=subprocess.STDOUT)
    run(['debugfs','-R',f'rdump /results {out}',disk],capture_output=True)
    content=(out/'guest.log').read_text()
    assert 'namespace_guest=pass' in content and 'revision_guest_status=0' in content
    assert not re.search(r'Kernel panic|BUG:|WARNING:',content)
    assert json.loads((out/'results/complete.json').read_text())['status']=='pass'
    print('namespace_vm=pass')


if __name__=='__main__':main()
