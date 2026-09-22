#!/usr/bin/env python3
"""Package the namespace-only kernel using the original Clocktime builder/tools."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
TESTS=HERE.parent/'vkso-tests'


def run(args, **kwargs):
    return subprocess.run(list(map(str,args)),check=True,**kwargs)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('kernel',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    kernel=a.kernel.resolve();out=a.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    archive=TESTS/'baremetal/artifacts/reader-load-v4-normal'
    run(['sha256sum','--quiet','-c','SHA256SUMS'],cwd=archive)
    builder=out/'build_PIC_so.py'
    builder.write_bytes(run(['git','show','adfe3138e1388c34cb58051d33b2047682ac1a28:make_dll/build_PIC_so.py'],
                           cwd=ROOT,capture_output=True).stdout)
    for name in ['symbols.txt','shared_data.txt','reusable_text.txt']:
        shutil.copy2(TESTS/'baremetal'/name,out/name)
    with (out/'builder.log').open('w') as log:
        run([ROOT/'kernel_cgd/src/krg','build',kernel/'vmlinux','-o',out/'kernel.krg',
             '--kallsyms',kernel/'System.map'],stdout=log,stderr=subprocess.STDOUT)
        run(['gcc','-I'+str(kernel/'include'),'-c','-fPIC','-o',out/'vkso_user_entry.o',
             TESTS/'functional/vkso_user_entry.S'],stdout=log,stderr=subprocess.STDOUT)
        run(['python3',builder,'--symbols','symbols.txt','--krg',out/'kernel.krg',
             '--shim-list',ROOT/'make_dll/shim.txt','--reusable-text-list','reusable_text.txt',
             '--shared-data-list','shared_data.txt','--vmlinux',kernel/'vmlinux',
             '--private-wrapper-object','vkso_user_entry.o','--symbol-addresses','resolved_symbol_addresses.txt',
             '--page-map','page_mappings.txt'],cwd=out,stdout=log,stderr=subprocess.STDOUT)
    for name in ['manager','page_cache_replace.ko','vkso_m09_clock.ko','vkso-abi-matrix','vkso-time-bench']:
        shutil.copy2(archive/name,out/name)
    shutil.copy2(kernel/'arch/x86/boot/bzImage',out/'vkso-bzImage')
    shutil.copy2(kernel/'.config',out/'vkso.config')
    shutil.copy2(kernel/'System.map',out/'System.map')
    module=out/'test-module';module.mkdir()
    shutil.copy2(HERE/'page_refs.c',module/'page_refs.c')
    (module/'Makefile').write_text('obj-m += page_refs.o\n')
    with (module/'build.log').open('w') as log:
        run(['make','-C',kernel,f'M={module}','KBUILD_MODPOST_WARN=1','modules'],stdout=log,stderr=subprocess.STDOUT)
    shutil.copy2(module/'page_refs.ko',out/'page_refs.ko')
    identities={name:hashlib.sha256((out/name).read_bytes()).hexdigest()
                for name in ['libkernel.so','vkso-bzImage','vkso.config','page_refs.ko','build_PIC_so.py']}
    (out/'identity.json').write_text(json.dumps(dict(kernel=str(kernel),
        archive=str(archive),files=identities),indent=2)+'\n')
    print('package=pass')


if __name__=='__main__':main()
