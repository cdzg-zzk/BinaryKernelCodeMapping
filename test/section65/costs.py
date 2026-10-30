#!/usr/bin/env python3
"""Count source adaptation and loaded ELF segments without treating disk debug data as RAM."""
import argparse
import difflib
import json
from pathlib import Path
import subprocess
from elftools.elf.elffile import ELFFile

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; BUILD=HERE/'build/adapted'
def lines(path): return len(path.read_text().splitlines())
def elf(path):
    with path.open('rb') as stream:
        e=ELFFile(stream)
        sections=[dict(name=s.name,bytes=s['sh_size'],writable=bool(s['sh_flags']&1),
                       executable=bool(s['sh_flags']&4)) for s in e.iter_sections() if s['sh_flags']&2]
        segments=[dict(flags=p['p_flags'],memory_bytes=p['p_memsz'],file_bytes=p['p_filesz'],vaddr=p['p_vaddr'])
                  for p in e.iter_segments() if p['p_type']=='PT_LOAD']
    return dict(path=str(path.relative_to(ROOT)),file_bytes=path.stat().st_size,
                allocated_section_bytes=sum(s['bytes'] for s in sections),sections=sections,load_segments=segments)
def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    result=dict(accounting='source lines include blanks/comments; ELF allocated bytes are not measured RSS',
                adaptation=json.loads((BUILD/'adaptation.json').read_text()))
    # Function-body comparison excludes only the mechanical removal of static.
    import adapt,re
    changes=[]
    for row in result['adaptation']['functions']:
        original=(HERE/'upstream'/row['source']).read_text(); begin,end=adapt.span(original,row['function'])
        before=re.sub(r'^static\s+','',original[begin:end]).splitlines()
        renamed={'isofs_fill_super':'iso_read_super','rock_ridge_symlink_readpage':'iso_readlink'}.get(row['function'],row['function'])
        shared=(BUILD/'shared_core.c').read_text(); begin,end=adapt.span(shared,renamed)
        after=shared[begin:end].splitlines(); added=removed=0
        for op,i,j,k,l in difflib.SequenceMatcher(a=before,b=after,autojunk=False).get_opcodes():
            if op in ('replace','delete'): removed+=j-i
            if op in ('replace','insert'): added+=l-k
        changes.append(dict(function=row['function'],added=added,removed=removed))
    result['body_changes']=changes
    result['source_lines']={str(p.relative_to(HERE)):lines(p) for p in [
        HERE/'adapt.py',HERE/'build_user.py',HERE/'user_bridge.c',BUILD/'kernel_support.c',
        BUILD/'core_metadata.c',BUILD/'support_types.h',BUILD/'support_remap.h',BUILD/'user_bindings.c']}
    result['binaries']=[elf(path) for path in [BUILD/'vkso_iso_core.ko',BUILD/'vkso_isofs.ko',
        HERE/'build/raw/isofs_probe.ko',BUILD/'libiso-bridge.so',BUILD/'libisofs-copy.so',
        ROOT/'page_cache_replace/page_cache_replace.ko',ROOT/'page_cache_replace/manager']]
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(source_lines=result['source_lines'],body_added=sum(x['added'] for x in changes),
                          body_removed=sum(x['removed'] for x in changes))))
if __name__=='__main__': main()
