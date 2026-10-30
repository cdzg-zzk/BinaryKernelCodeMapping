#!/usr/bin/env python3
"""Preserve actual original/prepared instructions and build-option evidence."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
from elftools.elf.elffile import ELFFile

SECTION=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    objects={'original':SECTION/'build/native/kernel/vmlinux','prepared':a.build.resolve()/'vkso_sq_core.ko'}
    functions=['squashfs_copy_data','squashfs_fill_super','squashfs_read_inode','squashfs_readdir',
               'squashfs_read_metadata','squashfs_read_data']
    result=dict(objects={},functions=[],configuration={},interpretation=
        'Original/prepared includes PIC, optimization, stack-protection and indirect/return mitigation changes. It is total preparation cost, not isolated PGOT or service-call cost.')
    for name,path in objects.items():
        result['objects'][name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        for function in functions:
            asm=subprocess.check_output(['objdump','-d',*(['-r'] if name=='prepared' else []),
                '--disassemble='+function,str(path)],text=True)
            # GNU objdump -dr --disassemble also emits earlier section
            # relocations. Restrict those records to this symbol's real extent.
            with path.open('rb') as stream:
                symbols=ELFFile(stream).get_section_by_name('.symtab').get_symbol_by_name(function)
                if symbols:
                    start=symbols[0]['st_value'];end=start+symbols[0]['st_size']
                    asm='\n'.join(line for line in asm.splitlines() if not (
                        (match:=re.match(r'\s*([0-9a-f]+):\s+R_X86_64_',line)) and
                        not start<=int(match[1],16)<end))+'\n'
            (out/(name+'-'+function+'.asm')).write_text(asm)
            result['functions'].append(dict(variant=name,function=function,found='<'+function+'>:' in asm,
                stack_chk_fail_references=asm.count('__stack_chk_fail'),
                indirect_thunk_references=asm.count('__x86_indirect_thunk'),
                return_thunk_references=asm.count('__x86_return_thunk'),
                service_relocations=asm.count('sq_support')))
    config=(SECTION/'build/native/kernel/.config').read_text()
    result['configuration']={line.split('=')[0]:line.split('=')[1] for line in config.splitlines()
        if line.startswith(('CONFIG_SQUASHFS','CONFIG_RETPOLINE','CONFIG_RETHUNK','CONFIG_STACKPROTECTOR',
                            'CONFIG_FUNCTION_TRACER','CONFIG_CC_OPTIMIZE','CONFIG_CC_VERSION_TEXT')) and '=' in line}
    (out/'kernel.config').write_text(config)
    for name in ['Makefile','.shared_core.o.cmd','.cache.o.cmd']:
        source=a.build/name
        if source.exists():(out/name.lstrip('.')).write_bytes(source.read_bytes())
    result['all_requested_symbols_found']=all(r['found'] for r in result['functions'])
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
