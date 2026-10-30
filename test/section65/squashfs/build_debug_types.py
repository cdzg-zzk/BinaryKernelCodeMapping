#!/usr/bin/env python3
"""Add a DWARF companion without replacing the evaluated bridge binary."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
from elftools.elf.elffile import ELFFile

HERE=Path(__file__).resolve().parent
SECTION=HERE.parent


def allocated(path):
    with path.open('rb') as f:
        elf=ELFFile(f)
        return {s.name:hashlib.sha256(s.data()).hexdigest() for s in elf.iter_sections()
                if s['sh_flags']&2 and s['sh_type']!='SHT_NOBITS'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build=a.build.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    flags=shlex.split((build/'.shared_core.o.cmd').read_text().splitlines()[0].split(' := ',1)[1])
    flags=flags[:flags.index('-c')]
    flags=[f for f in flags if not f.startswith(('-Wp,-MMD','-DKBUILD_','-D__KBUILD_','-mpreferred-stack-boundary'))]
    flags+=['-fPIC','-mpreferred-stack-boundary=4','-I'+str(build),'-Wno-declaration-after-statement','-g']
    command=flags+['-c',str(HERE/'user_bridge.c'),'-o',str(out/'types.o')]
    with (out/'build.log').open('w') as log:
        subprocess.run(command,cwd=SECTION/'build/native/kernel',stdout=log,stderr=subprocess.STDOUT,check=True)
    before=allocated(build/'user_bridge.o');after=allocated(out/'types.o')
    result=dict(command=command,original=before,debug_companion=after,all_allocated_sections_equal=before==after,
                original_object=str(build/'user_bridge.o'),scope='DWARF only; target libraries unchanged')
    (out/'identity.json').write_text(json.dumps(result,indent=2)+'\n')
    assert before==after,result
    print('debug companion matches all allocated sections')


if __name__=='__main__':main()
