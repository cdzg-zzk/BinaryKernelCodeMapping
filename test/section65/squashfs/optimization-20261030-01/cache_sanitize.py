#!/usr/bin/env python3
"""Instrument only the private adapter for lifetime diagnostics; never timing."""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True)
    p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=a.build.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    commands=json.loads((source/'user-build.json').read_text())['commands'];record={'status':'running'}
    try:
        with (out/'build.log').open('w') as log:
            for command in commands:
                # The linked common core is unchanged and uninstrumented.
                # Both private bridge objects and allocator interception are checked.
                if '-c' in command and any(str(n).endswith('/'+name) for n in command for name in ['user_bridge.c','posix_io.c']):
                    cmd=[str(n) for n in command if n not in ['-fno-sanitize=all','-fomit-frame-pointer']]
                    idx=cmd.index('-o');cmd[idx+1]=str(out/Path(cmd[idx+1]).name)
                    cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
                    subprocess.run(cmd,cwd='/home/zzk/BinaryKernelCodeMapping/test/section65/build/native/kernel',stdout=log,stderr=subprocess.STDOUT,check=True)
                if '-shared' in command and any(str(n).endswith('/libsq-copy.so') for n in command):
                    cmd=[str(n) for n in command]
                    for j,n in enumerate(cmd):
                        if Path(n).name in ['libsq-copy.so','user_bridge.o','posix_io.o']:cmd[j]=str(out/Path(n).name)
                    cmd+=['-fsanitize=address,undefined']
                    subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
        for name in ['rootfs','paths.json','valid.squashfs']:(out/name).symlink_to(a.fixture.resolve()/name)
        env=dict(os.environ,LD_PRELOAD=subprocess.check_output(['gcc','-print-file-name=libasan.so'],text=True).strip(),
                 ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        with (out/'validation.log').open('w') as log:
            subprocess.run([sys.executable,Path(__file__).with_name('cache_validate.py'),'--build',out,'--output',out,'--existing-fixture'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        record.update(status='complete',scope='ASAN/UBSAN private adapter plus intercepted allocator; common core remains uninstrumented',
            leak_scope='Python runtime leak scanning disabled; this checks invalid accesses, not a whole-process leak proof')
    except BaseException as e:record.update(status='failed',error=repr(e));raise
    finally:(out/'sanitizer.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))

if __name__=='__main__':main()
