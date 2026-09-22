#!/usr/bin/env python3
"""Inventory actual compiled binding sites and save inspectable instruction contexts."""
import argparse
import difflib
import re
from pathlib import Path
from collections import defaultdict
from run_layer3_v2 import command
from layer3_v2 import ROUTINES, BUILDS, VARIANTS, write_csv, dump, sha

FUNCTION=re.compile(r'^([0-9a-f]+) <([^>]+)>:$',re.M)
HELPER=re.compile(r'pgot_mem(?:cpy|set|move)_table')

def functions(s):
    matches=list(FUNCTION.finditer(s))
    return [(m[2],s[m.start():matches[i+1].start() if i+1<len(matches) else len(s)]) for i,m in enumerate(matches)]

def main(a):
    out=a.campaign/'static-evidence';out.mkdir(exist_ok=True)
    stats=[];sites=[];source_sites=[];sizes=[];hashes={};examples=[]
    for routine in ROUTINES:
        for build in BUILDS:
            d=a.campaign/routine/build
            nm=(d/'nm.txt').read_text()
            slots=set(re.findall(r'^\w+\s+\w+\s+[DdBbRr]\s+(pgot_\w+)$',nm,re.M))
            assert slots
            objects=sorted(d.glob('closure_*.o')) or [d/'bench_kmod.o']
            totals=defaultdict(lambda:dict(text_bytes=0,instructions=0,data_slot_references=0,helper_slot_references=0,direct_memory_calls=0,indirect_transfers=0,inline_retpoline_loops=0))
            variant_text=defaultdict(list)
            for obj in objects:
                name=f'{routine}-{build}-{obj.stem}.txt'
                dis=command(['objdump','-dr','--no-show-raw-insn',obj]);(out/name).write_text(dis)
                hashes[str(obj.relative_to(a.campaign))]=sha(obj)
                sizes_nm={n:int(size,16) for addr,size,t,n in re.findall(r'^(\w+)\s+(\w+)\s+([tT])\s+(\S+)$',command(['nm','-S',obj]),re.M)}
                vs=('origin','data_pgot') if routine.startswith('01') else ('origin',*VARIANTS)
                object_v=next((v for v in vs if obj.name==f'closure_{v}.o' or obj.name.startswith(f'closure_{v}_')),None)
                for fn,body in functions(dis):
                    v=object_v or next((v for v in vs if fn.endswith('_'+v)),None)
                    if v is None or fn.startswith('body_'):continue
                    t=totals[v];lines=body.splitlines()
                    t['text_bytes']+=sizes_nm.get(fn,0)
                    t['instructions']+=len(re.findall(r'^\s*[0-9a-f]+:\s+(?!R_X86)\w+',body,re.M))
                    t['indirect_transfers']+=len(re.findall(r'\b(?:call|jmp)\s+\*',body))
                    loops=len(re.findall(r'\bpause\b',body))
                    complete=len(re.findall(r'\bpause\s*\n\s*[0-9a-f]+:\s+lfence\s*\n\s*[0-9a-f]+:\s+jmp[^\n]+\n\s*[0-9a-f]+:\s+mov\s+%\w+,\(%rsp\)\s*\n\s*[0-9a-f]+:\s+ret',body))
                    assert loops==complete,(routine,build,v,fn,'incomplete retpoline sequence')
                    t['inline_retpoline_loops']+=loops
                    sizes.append(dict(routine=routine,build=build,variant=v,object=obj.name,function=fn,bytes=sizes_nm.get(fn,0)))
                    variant_text[v].append(body)
                    for i,line in enumerate(lines):
                        match=re.search(r'([0-9a-f]+):\s+(R_X86_64_\w+)\s+([^\s+\-]+)',line)
                        if not match:continue
                        offset,reloc,symbol=match.groups()
                        if symbol in slots:kind='helper_slot' if HELPER.match(symbol) else 'data_slot'
                        elif symbol in ('memcpy','memset','memmove'):kind='direct_memory_call'
                        else:continue
                        t[{'helper_slot':'helper_slot_references','data_slot':'data_slot_references','direct_memory_call':'direct_memory_calls'}[kind]]+=1
                        sites.append(dict(routine=routine,build=build,variant=v,object=obj.name,function=fn,offset=offset,kind=kind,symbol=symbol,disassembly=name,line=dis[:dis.find(body)].count('\n')+i+1))
                        examples.append(f'## {routine}/{build}/{v}: {fn}, {offset}, {symbol}\n\n```asm\n'+ '\n'.join(lines[max(0,i-2):min(len(lines),i+17)])+'\n```\n')
            for v,t in totals.items():
                stats.append(dict(routine=routine,build=build,variant=v,**t))
                assert bool(t['data_slot_references'])==(v in ('data_pgot','all_pgot')),(routine,build,v,t)
                assert bool(t['helper_slot_references'])==(not routine.startswith('01') and v in ('func_pgot','all_pgot')),(routine,build,v,t)
                if routine.startswith('01'):assert t['indirect_transfers']==0 and t['inline_retpoline_loops']==0
                if build=='no_retpoline':assert t['inline_retpoline_loops']==0
                if v in ('func_pgot','all_pgot'):
                    assert t['indirect_transfers']>0 if build=='no_retpoline' else t['inline_retpoline_loops']>0
            if routine.startswith('03'):
                def normalize(v):
                    text='\n'.join(variant_text[v]);text=re.sub(r'_(origin|data_pgot|func_pgot|all_pgot)\b','_VARIANT',text)
                    return re.sub(r'^\s*[0-9a-f]+:', 'ADDR:',text,flags=re.M).splitlines(True)
                for v in VARIANTS:
                    diff=difflib.unified_diff(normalize('origin'),normalize(v),fromfile='Origin',tofile=v)
                    (out/f'zlib-{build}-{v}.diff').write_text(''.join(diff))
            if build=='no_retpoline':
                for source in sorted(d.glob('closure_func_pgot*.c')):
                    lines=source.read_text().splitlines()
                    for i,line in enumerate(lines):
                        if re.search(r'\bPGOT_MEM(?:CPY|SET|MOVE)\s*\(',line) and not line.lstrip().startswith('#'):
                            source_sites.append(dict(routine=routine,source=str(source.relative_to(a.campaign)),line=i+1,
                                statement=line.strip(),context=' / '.join(x.strip() for x in lines[max(0,i-2):i+3])))
    write_csv(out/'object-summary.csv',stats);write_csv(out/'binding-sites.csv',sites)
    write_csv(out/'helper-source-sites.csv',source_sites);write_csv(out/'function-sizes.csv',sizes)
    (out/'binding-contexts.md').write_text('# Binding instruction contexts\n\nStatic sites, not execution counts. Full disassembly is adjacent.\n\n'+'\n'.join(examples))
    dump(out/'manifest.json',dict(status='complete',objects=hashes,static_binding_sites=len(sites),source_helper_sites=len(source_sites)))
    print('static evidence:',len(stats),'variant/build summaries;',len(sites),'binding sites')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);main(p.parse_args())
