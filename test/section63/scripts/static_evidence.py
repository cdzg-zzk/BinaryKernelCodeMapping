#!/usr/bin/env python3
"""Retain source interventions and generated instructions for all six versions."""
import argparse
import difflib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]

def capture(base):
    output=base/'source-ledger';output.mkdir(exist_ok=True)
    original=ROOT/'test/section63/source/linux-5.15.0-119.129'
    files={'lz4':['lz4_compress.c','lz4_decompress.c','lz4defs.h'],
           'bch':['bch.c'],
           'xz':['xz_dec_stream.c','xz_dec_lzma2.c','xz_dec_bcj.c','xz_private.h','xz_crc32.c']}
    records=[]
    for a,names in files.items():
        directory=output/a;directory.mkdir(exist_ok=True)
        for name in names:
            source=original/'lib'/a/name if a!='bch' else original/'lib/bch.c'
            adapted=base/'owners'/a/name if a!='bch' else base/'owners/adapted/bch.c'
            patch=''.join(difflib.unified_diff(source.read_text().splitlines(True),adapted.read_text().splitlines(True),
                fromfile=str(source.relative_to(ROOT)),tofile=str(adapted.relative_to(base))))
            (directory/(name+'.patch')).write_text(patch)
            records.append(dict(algorithm=a,file=name,changed=bool(patch),original=str(source),adapted=str(adapted)))
        prepared=base/f'deployment-00-{a}/prepared'
        matched=prepared/'payload/kernel-cost'/('bch_matched.ko' if a=='bch' else 'matched_'+a+'.ko')
        binaries={'native-dso':base/f'builds/{a}/libnative.so','adapted-dso':base/f'builds/{a}/libadapted.so',
                  'owner-kernel':base/f'owners/{a}/vkso_{a}.ko','matched-kernel':matched}
        for name,path in binaries.items():
            with (directory/(name+'.asm')).open('w') as f:
                subprocess.run(['objdump','-drwC','-Mintel',str(path)],stdout=f,check=True)
            (directory/(name+'-symbols.txt')).write_text(subprocess.check_output(['readelf','-sW',str(path)],text=True))
        (directory/'compiler-comparison.json').write_bytes((prepared/'kernel-cost-build/compiler-comparison.json').read_bytes())
        (directory/'user-build.json').write_bytes((base/f'builds/{a}/build.json').read_bytes())
    (output/'source-differences.json').write_text(json.dumps(records,indent=2)+'\n')
    (output/'kernel-config.txt').write_text('\n'.join(l for l in Path('/boot/config-5.15.0-119-generic').read_text().splitlines()
        if any(s in l for s in ('BCH','XZ_DEC','CRC32','RETPOLINE','STACKPROTECTOR','UBSAN')))+'\n')
    (output/'compiler.txt').write_text(subprocess.check_output(['gcc','--version'],text=True))
    print('Captured source patches, compiler controls and generated instructions.')

def stock(base):
    output=base/'source-ledger'
    vmlinux=Path('/usr/lib/debug/boot/vmlinux-5.15.0-119-generic')
    entries=[('xz','xz_dec_run',vmlinux),('xz','crc32_le_base',vmlinux),
             ('lz4','LZ4_decompress_safe',vmlinux),
             ('lz4','LZ4_compress_default',Path('/lib/modules/5.15.0-119-generic/kernel/lib/lz4/lz4_compress.ko')),
             ('bch','bch_decode',Path('/lib/modules/5.15.0-119-generic/kernel/lib/bch.ko'))]
    for algorithm,symbol,path in entries:
        with (output/algorithm/('stock-'+symbol+'.asm')).open('w') as f:
            subprocess.run(['objdump','-drwC','-Mintel','--disassemble='+symbol,str(path)],stdout=f,check=True)
    print('Captured distribution XZ/CRC, LZ4 and BCH instructions.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--stock',action='store_true')
    a=p.parse_args();(stock if a.stock else capture)(a.directory.resolve())
