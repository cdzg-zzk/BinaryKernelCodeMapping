#!/usr/bin/env python3
"""Inspect the two native module controls without re-reading the host vmlinux."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from elftools.elf.elffile import ELFFile

ROOT=Path(__file__).resolve().parents[3]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    prior=ROOT/'test/section65/build/squashfs/build-audit-02/audit.json'
    original=json.loads(prior.read_text())
    rows=[];objects={}
    functions=list(dict.fromkeys(r['function'] for r in original['functions']))
    for label,run in [('normal','squash-maintenance-reference-01'),
                      ('relaxed','squash-maintenance-relaxed-reference-01')]:
        build=ROOT/'test/evaluation-local/runs/iso9660'/run/'build'
        binary=build/'sq_reference.ko'
        objects[label]=dict(path=str(binary),sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
        for name in ['Makefile','.inode.o.cmd','.cache.o.cmd','.block.o.cmd','.dir.o.cmd','.super.o.cmd']:
            (out/(label+'-'+name.lstrip('.'))).write_bytes((build/name).read_bytes())
        with binary.open('rb') as stream:
            symbols=ELFFile(stream).get_section_by_name('.symtab')
            extents={f:(symbols.get_symbol_by_name(f)[0]['st_value'],symbols.get_symbol_by_name(f)[0]['st_size']) for f in functions}
        for function in functions:
            asm=subprocess.check_output(['objdump','-dr','--disassemble='+function,str(binary)],text=True)
            start,size=extents[function]
            asm='\n'.join(line for line in asm.splitlines() if not (
                (m:=re.match(r'\s*([0-9a-f]+):\s+R_X86_64_',line)) and
                not start<=int(m[1],16)<start+size))+'\n'
            assert '<'+function+'>:' in asm
            (out/(label+'-'+function+'.asm')).write_text(asm)
            rows.append(dict(variant=label,function=function,bytes=size,
                stack_chk_fail_references=asm.count('__stack_chk_fail'),
                indirect_thunk_references=asm.count('__x86_indirect_thunk'),
                return_thunk_references=asm.count('__x86_return_thunk'),
                fentry_references=asm.count('__fentry__')))
    result=dict(status='complete',objects=objects,functions=rows,
        original_prepared_audit=str(prior),original_prepared_sha256=hashlib.sha256(prior.read_bytes()).hexdigest(),
        interpretation='Matched source-version and upstream fix. Normal control retains native build settings; relaxed control changes selected options but retains kernel addressing. These are emitted ELF instructions, not a trace of runtime alternative patching or executed mitigation sites. Instruction differences do not support an additive causal decomposition.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
