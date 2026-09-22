#!/usr/bin/env python3
"""Build ordinary user ports and adapted DSOs under common user flags."""
from pathlib import Path
import argparse
import json
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'test/section63'
SOURCE=HERE/'source/linux-5.15.0-119.129'
USER_FLAGS=['-O2','-g','-fPIC','-std=gnu11']


def build(algorithm, output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    legacy=ROOT/'test'/('test_BCH' if algorithm=='bch' else 'test_'+algorithm)
    commands=[]
    def command(args,name):
        args=list(map(str,args))
        with (output/(name+'.log')).open('w') as log:
            p=subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        commands.append(dict(name=name,argv=args,returncode=p.returncode))
        (output/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        if p.returncode:raise RuntimeError(output/(name+'.log'))
    if algorithm=='bch':
        # Only portability headers differ from a kernel build. Original C is unedited.
        headers=output/'include/linux';headers.mkdir(parents=True)
        shutil.copy2(SOURCE/'include/linux/bch.h',headers/'bch.h')
        common=['-include',legacy/'userspace/kernel_compat.h','-I'+str(output/'include'),
                '-I'+str(legacy/'vendor/parrot-bch/standalone')]
        for name,source in [('native',SOURCE/'lib/bch.c'),('adapted',legacy/'adapted/bch.c')]:
            command(['gcc',*USER_FLAGS,*common,'-shared',source,'-Wl,-Bsymbolic-functions',
                     '-Wl,--version-script='+str(legacy/'userspace/kernel-native.map'),
                     '-o',output/f'lib{name}.so'],name)
        command(['gcc','-O2','-g',legacy/'src/bch_bench.c','-ldl','-o',output/'bench'],'bench')
    elif algorithm=='xz':
        for name,source in [('native',SOURCE/'lib/xz'),('adapted',legacy/'kmod')]:
            config=output/(name+'-config');config.mkdir()
            text=(legacy/'userspace/xz_config.h').read_text()
            if name=='native':
                # The upstream userspace CRC32 fallback is retained. Preserve all
                # stock decoder modes and BCJ filters, instead of owner's subset.
                text=text.replace('#define XZ_DEC_SINGLE\n','')
                text=text.replace('#define XZ_DEC_X86\n','#define XZ_DEC_X86\n#define XZ_DEC_POWERPC\n#define XZ_DEC_IA64\n#define XZ_DEC_ARM\n#define XZ_DEC_ARMTHUMB\n#define XZ_DEC_SPARC\n')
            (config/'xz_config.h').write_text(text)
            shutil.copy2(SOURCE/'include/linux/xz.h',config/'xz.h')
            command(['gcc',*USER_FLAGS,'-shared','-I'+str(config),'-I'+str(source),
                *[source/n for n in ('xz_dec_stream.c','xz_dec_lzma2.c','xz_dec_bcj.c','xz_crc32.c')],
                '-Wl,--version-script='+str(legacy/'userspace/exports.map'),'-o',output/f'lib{name}.so'],name)
        command(['gcc','-O2','-g','-I'+str(legacy/'kmod'),legacy/'src/xz-bench.c','-ldl','-o',output/'bench'],'bench')
    else:
        compat=output/'compat';compat.mkdir()
        shutil.copy2(legacy/'userspace_kernel/kernel_compat.h',compat/'kernel_compat.h')
        for name in ('asm/unaligned.h','linux/lz4.h','linux/kernel.h','linux/types.h','linux/module.h','linux/init.h','linux/string.h'):
            p=compat/name;p.parent.mkdir(exist_ok=True);p.write_text('#include "kernel_compat.h"\n')
        renames=re.findall(r'-DLZ4_\w+=vkso_LZ4_\w+', (legacy/'kmod/Makefile').read_text())
        for name,source,extra in [('native',SOURCE/'lib/lz4',['-I'+str(compat)]),
                                  ('adapted',legacy/'kmod',['-DVKSO_LZ4_USERSPACE'])]:
            command(['gcc',*USER_FLAGS,*renames,*extra,'-shared',
                source/'lz4_compress.c',source/'lz4_decompress.c','-Wl,-Bsymbolic-functions',
                '-Wl,--version-script='+str(legacy/'userspace_kernel/exports.map'),'-o',output/f'lib{name}.so'],name)
        command(['make','-C',legacy,'BUILD_DIR='+str(output),output/'official-lz4-bench'],'bench')
    record={'algorithm':algorithm,'user_flags':USER_FLAGS,'source_version':'Ubuntu 5.15.0-119.129',
        'backends':{'native-dso':str(output/'libnative.so'),'adapted-dso':str(output/'libadapted.so')},
        'native_algorithm_edits':[],
        'native_portability':{'bch':'Linux API compatibility headers with libc allocation/memory helpers',
            'xz':'documented userspace configuration and internal CRC32 fallback; original C and all stock modes/filters',
            'lz4':'Linux type/API header compatibility; original C and lz4defs.h'}[algorithm]}
    (output/'build.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('algorithm',choices=('lz4','bch','xz'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.algorithm,a.output),indent=2))
