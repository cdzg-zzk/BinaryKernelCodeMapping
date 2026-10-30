#!/usr/bin/env python3
"""Prove SquashFS native/user shared pages and explicit restore in a guest."""
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from reference_guest import manifest

PACKAGE=Path(__file__).resolve().parent
OUT=Path('/work/evidence')


def command(argv,label,cwd=None):
    with (OUT/(label+'.log')).open('w') as log:
        subprocess.run(list(map(str,argv)),cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)


def kernel_cases(label):
    mount=OUT/'native-mount';mount.mkdir(exist_ok=True)
    cases=[]
    for image in sorted((PACKAGE/'images').glob('*.squashfs')):
        command(['mount','-t','vksosquash','-o','ro,loop',image,mount],label+'-mount')
        try:
            rows=manifest(mount)
            expected=json.loads((PACKAGE/'reference'/(image.stem+'-squashfs.json')).read_text())
            assert rows==expected,image.name
            cases.append(dict(image=image.name,entries=len(rows)))
        finally:command(['umount',mount],label+'-unmount')
    (OUT/(label+'.json')).write_text(json.dumps(dict(status='pass',cases=cases),indent=2)+'\n')


def main():
    OUT.mkdir(exist_ok=False)
    carrier=OUT/'carrier';carrier.mkdir()
    loaded=[];registered=False;library=None
    result=dict(status='running',scope='TCG shared SquashFS functional proof; no performance claim')
    try:
        for name in ['vkso_sq_core','vkso_squashfs','vkso_kernel_reader','page_cache_replace']:
            command(['insmod',PACKAGE/(name+'.ko')],'load-'+name);loaded.append(name)
        kernel_cases('native-before')
        command([PACKAGE/'krg','build',PACKAGE/'vmlinux','--module',PACKAGE/'vkso_sq_core.ko','-o',carrier/'out.krg'],'krg')
        command([sys.executable,PACKAGE/'build_PIC_so.py','--symbols',PACKAGE/'symbols.txt',
                 '--krg',carrier/'out.krg','--ko',PACKAGE/'vkso_sq_core.ko','--shim-list',PACKAGE/'shim.txt',
                 '--vmlinux',PACKAGE/'vmlinux'],'carrier',cwd=carrier)
        library=next(carrier.glob('lib*.so')).resolve()
        before=library.read_bytes()
        command([PACKAGE/'manager','replace',library,carrier/'page_mappings.txt'],'register',cwd=PACKAGE)
        registered=True
        live=[]
        for proc in Path('/proc').iterdir():
            if proc.name.isdigit():
                try:
                    if (proc/'exe').resolve()==PACKAGE/'manager':live.append(int(proc.name))
                except (OSError,RuntimeError):pass
        assert not live
        (OUT/'lifecycle.json').write_text(json.dumps(dict(registration_process_exited=True,live_manager_pids=live))+'\n')
        copied=OUT/'libsq-materialized.so';copied.write_bytes(library.read_bytes())
        for label,core in [('shared',library),('copied',copied)]:
            argv=[sys.executable,PACKAGE/'check_fuse.py','--build',PACKAGE,'--images',PACKAGE/'images',
                  '--reference',PACKAGE/'reference','--core',core,'--bridge',PACKAGE/'libsq-bridge.so',
                  '--pfn-plan',carrier/'page_mappings.txt','--output',OUT/label]
            if label=='shared':argv+=['--expect-shared']
            command(argv,label+'-fuse')
            assert json.loads((OUT/label/'result.json').read_text())['status']=='pass'
        kernel_cases('native-after')
        command([PACKAGE/'manager','restore',library,carrier/'page_mappings.txt'],'restore',cwd=PACKAGE)
        registered=False
        assert library.read_bytes()==before,'carrier contents were not restored'
        result.update(status='complete',registration_process_exited=True,restored=True)
    except BaseException:
        result.update(status='failed',error=traceback.format_exc());raise
    finally:
        try:
            if registered:command([PACKAGE/'manager','restore',library,carrier/'page_mappings.txt'],'cleanup-restore',cwd=PACKAGE)
            for name in reversed(loaded):command(['rmmod',name],'unload-'+name)
            result['modules_unloaded']=True
        except BaseException:
            result.update(status='failed',cleanup_error=traceback.format_exc());raise
        finally:(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
