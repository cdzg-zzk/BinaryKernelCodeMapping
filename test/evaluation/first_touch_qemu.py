#!/usr/bin/env python3
"""Prepare current XXH32 owner and full first-touch raw protocol; no host module loads."""
from pathlib import Path
import argparse,ctypes.util,json,os,re,shutil,subprocess,time,traceback
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'test/evaluation'

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--prepared',type=Path,default=HERE/'results/lz4-setup-qemu-20260912-attempt01')
    p.add_argument('--scenario',choices=('raw','pressure'),default='raw')
    p.add_argument('--timeout',type=int,default=1800);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);prepared=a.prepared.resolve()
    result=dict(status='running',started_unix=time.time());components=[]
    def cp(source,target):
        source,target=Path(source),Path(target);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        components.append(dict(source=str(source),target=str(target.relative_to(out)),bytes=target.stat().st_size))
    def run(command,name):
        with (out/name).open('w') as log:r=subprocess.run(list(map(str,command)),stdout=log,stderr=subprocess.STDOUT)
        assert r.returncode==0,(command,name,r.returncode)
    try:
        assert os.geteuid()!=0 and os.access('/dev/kvm',os.R_OK|os.W_OK)
        source=out/'owner-source';source.mkdir()
        origin=ROOT/'test/test_first_call/so'
        for name in ('Makefile','zzk_xxh32_module.c','zzk_xxh32_kernel.S','clone_xxh32_user.S','clone_xxh32_min.ld','compare_xxh32_bytes.py','vkso_owner.h','api.h'):
            cp(origin/name,source/name)
        run(['make','-C',source,'all','check-asm'],'owner-build.log')
        bench=out/'benchmark';bench.mkdir()
        for name in ('benchmark_first_touch.c','run_benchmarks.sh','analyze_first_touch.py'):
            cp(ROOT/'test/test_first_call/matrix_bench'/name,bench/name)
        run(['gcc','-O3','-Wall','-Wextra','-Werror','-std=c11',bench/'benchmark_first_touch.c','-ldl','-lm','-o',bench/'benchmark_first_touch'],'collector-build.log')
        if a.scenario=='pressure':
            for name in ('pressure_probe','pressure_worker'):
                cp(ROOT/'test/test_first_call/matrix_bench'/f'{name}.c',bench/f'{name}.c')
                run(['gcc','-O3','-Wall','-Wextra','-Werror','-std=c11',bench/f'{name}.c','-ldl','-lm','-o',bench/name],f'{name}-build.log')
        payload=out/'payload';payload.mkdir()
        for directory in ('repo','helpers'):
            for path in (prepared/'payload'/directory).rglob('*'):
                if path.is_file():
                    current=ROOT/path.relative_to(prepared/'payload/repo') if directory=='repo' else path
                    cp(current,payload/path.relative_to(prepared/'payload'))
        cp(source/'zzk_xxh32_lkm.ko',payload/'owner/zzk_xxh32_lkm.ko');cp(source/'libclone_xxh32.so',payload/'native/libclone_xxh32.so')
        for path in bench.iterdir(): cp(path,payload/'benchmark'/path.name)
        cp(prepared/'payload/vmlinux-5.15.0-119-generic',payload/'vmlinux-5.15.0-119-generic')
        cp(HERE/'first_touch_guest.py',payload/'guest.py');cp(HERE/'lz4_guest.py',payload/'lz4_guest_helpers.py')
        cp(HERE/'applicability_runtime_audit.py',payload/'applicability_runtime_audit.py')
        if a.scenario=='pressure':
            for name in ('first_touch_pressure.py','first_touch_pressure_audit.py'):
                cp(HERE/name,payload/name)
            (payload/'first-touch-scenario').write_text('pressure\n')
        cp('/usr/lib/x86_64-linux-gnu/libxxhash.so.0',payload/'oracle/libxxhash.so.0')
        cp(source/'api.h',payload/'api.h')
        (payload/'symbols.txt').write_text('zzk_xxh32\n')
        (out/'components.json').write_text(json.dumps(components,indent=2)+'\n');cp(__file__,out/'first_touch_qemu.py')
        disk=out/'guest.ext4'
        with disk.open('wb') as stream:stream.truncate((5 if a.scenario=='pressure' else 3)*1024**3)
        run(['mkfs.ext4','-q','-F','-d',payload,disk],'disk-build.log')
        command=['qemu-system-x86_64','-no-user-config','-nodefaults','-accel','kvm','-cpu','host','-m','4096','-smp','2',
            '-kernel','/tmp/vkso-guest-kernel-119/extracted/boot/vmlinuz-5.15.0-119-generic','-initrd',str(prepared/'initramfs.cpio.gz'),
            '-drive',f'file={disk},if=virtio,format=raw','-append','console=ttyS0 init=/init panic=-1 oops=panic nokaslr',
            '-display','none','-serial','stdio','-monitor','none','-nic','none','-no-reboot']
        (out/'command.json').write_text(json.dumps(dict(command=command,timeout=a.timeout),indent=2)+'\n')
        with (out/'console.log').open('w') as stream:
            process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=a.timeout)
        result['qemu_returncode']=process.returncode
    except BaseException: result.update(status='fail',error=traceback.format_exc())
    finally:
        if (out/'guest.ext4').exists():
            evidence=out/'evidence';evidence.mkdir()
            run(['debugfs','-R',f'rdump /validation {evidence}',out/'guest.ext4'],'extraction.log')
            status=evidence/'validation/status.json'
            result['guest_record']=json.loads(status.read_text()) if status.exists() else None
            console=(out/'console.log').read_text() if (out/'console.log').exists() else ''
            result['kernel_failure']=bool(re.search(r'Kernel panic|BUG:|WARNING:',console))
            if result.get('qemu_returncode')==0 and 'lz4_guest_status=0' in console and not result['kernel_failure'] and result['guest_record'] and result['guest_record']['status']=='pass': result['status']='pass'
            else: result['status']='fail'
        result['finished_unix']=time.time();(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['status']=='pass' else 1
if __name__=='__main__': raise SystemExit(main())
