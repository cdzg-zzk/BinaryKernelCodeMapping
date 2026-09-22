#!/usr/bin/env python3
"""Join observed carrier structure with source adaptation, preserving each scope."""
from pathlib import Path
import argparse,collections,csv,difflib,json,shutil,subprocess,tarfile
from elftools.elf.elffile import ELFFile
from adaptation_ledger import compare,counter

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'test/evaluation'
CLOCK=ROOT/'test/test_gettime'
FINAL='6656f97';M11='adfe313'

def table(path,fields):
    return list(csv.DictReader((l for l in path.read_text().splitlines() if l and not l.startswith('#')),
                              fieldnames=fields,delimiter='\t'))

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')

def copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)

def code_counts(text,path,ranges):
    lines=text.splitlines();selected=counter.parse_ranges(ranges,len(lines))
    flags=counter.lexical_code_flags(Path(path),lines)
    return dict(physical_lines=len(selected),nonblank_lines=sum(bool(lines[i-1].strip()) for i in selected),
                lexical_sloc=sum(flags[i-1] for i in selected))

def clock_sources(out,tarball):
    scope=CLOCK/'vkso-timekeeper-unification'
    fields=['view','system','layer','status','root','path','ranges','reason']
    manifest=table(scope/'M11_SOURCE_MANIFEST.tsv',fields)
    saved=list(csv.DictReader((scope/'M11_SOURCE_COUNTS.csv').open()))
    assert len(manifest)==len(saved)
    delta_fields=['view','layer','status','root','path','m11_ranges','final_ranges','m11_sloc',
        'final_physical','final_nonblank','final_sloc','delta','reason']
    deltas=table(scope/'FINAL_SOURCE_DELTA.tsv',delta_fields)
    def key(r):return tuple(r[k] for k in ('view','layer','status','root','path'))
    changes={key(r):r for r in deltas};assert len(changes)==len(deltas)
    wanted={r['path'] for r in manifest if r['root']=='RAW_KERNEL' or r['root']=='VKSO_KERNEL'}
    upstream={}
    with tarfile.open(tarball,'r|xz') as archive:
        for member in archive:
            prefix='linux-5.15.198/'
            if member.isfile() and member.name.startswith(prefix) and member.name[len(prefix):] in wanted:
                rel=member.name[len(prefix):];raw=archive.extractfile(member).read()
                upstream[rel]=raw.decode();target=out/'clocktime/upstream'/rel
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    blobs={}
    def git_source(root,path,commit):
        rel=('test/test_gettime/linux-5.15.198-vkso/'+path if root=='VKSO_KERNEL' else path)
        if (commit,rel) not in blobs:
            blobs[commit,rel]=subprocess.check_output(['git','show',f'{commit}:{rel}'],cwd=ROOT,text=True)
            target=out/'clocktime'/commit/root/path;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(blobs[commit,rel])
        return blobs[commit,rel]
    final_rows=[];current_differences=[]
    for r,old in zip(manifest,saved):
        assert all(r[k]==old[k] for k in fields)
        original=upstream[r['path']] if r['root']=='RAW_KERNEL' else git_source(r['root'],r['path'],M11)
        counts=code_counts(original,r['path'],r['ranges'])
        assert counts=={k:int(old[k]) for k in counts},(r,counts,old)
        final_range=r['ranges'];d=changes.get(key(r)) if r['system']=='VKSO' else None
        if d:
            assert d['m11_ranges']==r['ranges'] and int(d['m11_sloc'])==counts['lexical_sloc']
            final_range=d['final_ranges']
        final=original if r['system']=='Raw' else git_source(r['root'],r['path'],FINAL)
        final_count=code_counts(final,r['path'],final_range)
        if d:
            expected=dict(physical_lines=int(d['final_physical']),nonblank_lines=int(d['final_nonblank']),lexical_sloc=int(d['final_sloc']))
            assert final_count==expected and final_count['lexical_sloc']-counts['lexical_sloc']==int(d['delta']),(r,final_count,expected)
        else: assert final_count==counts,(r,final_count,counts)
        final_rows.append(dict(r,ranges=final_range,**final_count))
        if r['system']=='VKSO' and r['view'] in ('runtime','build'):
            current=(CLOCK/'linux-5.15.198-vkso'/r['path'] if r['root']=='VKSO_KERNEL' else ROOT/r['path']).read_text()
            selected=counter.parse_ranges(final_range,len(final.splitlines()))
            if [current.splitlines()[i-1] for i in selected]!=[final.splitlines()[i-1] for i in selected]:
                current_differences.append(dict(path=r['path'],ranges=final_range))
    assert not current_differences,current_differences
    totals=collections.defaultdict(int);layers=collections.defaultdict(int)
    for row in final_rows:
        totals[f"{row['system']}/{row['view']}/{row['status']}"]+=row['lexical_sloc']
        layers[f"{row['system']}/{row['layer']}"]+=row['lexical_sloc']
    assert sum(r['lexical_sloc'] for r in final_rows if r['system']=='VKSO' and r['view'] in ('runtime','build'))==1305
    assert sum(r['lexical_sloc'] for r in final_rows if r['system']=='Raw' and r['view'] in ('runtime','build'))==1505
    # Whole-file churn is an additional, explicitly wider view. It includes
    # validation and unchanged/common regions in product-bearing source files.
    files=sorted({(r['root'],r['path']) for r in final_rows if r['system']=='VKSO' and r['view'] in ('runtime','build')})
    churn=[];patch=[]
    for root,path in files:
        original=upstream.get(path,'') if root=='VKSO_KERNEL' else ''
        final=git_source(root,path,FINAL);rel=f'{root}/{path}'
        for kind,text in [('before',original),('after',final)]:
            target=out/'clocktime/full-file-diff'/kind/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
        churn.append(dict(root=root,path=path,**compare(original,final,path)))
        patch.extend(difflib.unified_diff(original.splitlines(True),final.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
    (out/'clocktime/full-file-diff/source.diff').write_text(''.join(patch))
    for name in ('M11_SOURCE_MANIFEST.tsv','M11_SOURCE_COUNTS.csv','FINAL_SOURCE_DELTA.tsv','FINAL_BINARY_SYMBOLS.tsv'):
        copy(scope/name,out/'clocktime/manifests'/name)
    result=dict(source_baseline='official Linux v5.15.198 tarball',source_url='https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.15.198.tar.xz',
        m11_commit=subprocess.check_output(['git','rev-parse',M11],cwd=ROOT,text=True).strip(),
        final_commit=subprocess.check_output(['git','rev-parse',FINAL],cwd=ROOT,text=True).strip(),
        semantic_rows=final_rows,totals=dict(totals),layers=dict(layers),product_sloc=dict(raw=1505,vkso=1305),
        current_product_ranges_differing=current_differences,full_file_churn=churn,
        churn_scope='whole product-bearing files versus upstream; new project files versus empty; includes validation and build changes; not product-only SLOC or hours')
    save(out/'clocktime/source-ledger.json',result);return result

def carrier(out,name,base,metadata,library,pfns):
    target=out/'carriers'/name;target.mkdir(parents=True)
    for source in (metadata/'resolved_symbol_addresses.txt',metadata/'page_mappings.txt',library,pfns):
        copy(source,target/source.name)
    for filename in ('data_bindings_resolved.json','owner_descriptors.txt','kernel_identity.txt','module_deps.txt'):
        if (metadata/filename).exists():copy(metadata/filename,target/filename)
    plan=[dict(file_offset=int(a,0),kernel_vaddr=int(b,0),kind=c,section=d) for a,b,c,d in csv.reader(
        l for l in (metadata/'page_mappings.txt').read_text().splitlines() if l and not l.startswith('#'))]
    observed=json.loads(pfns.read_text())['pages']
    assert len(plan)==len(observed)
    by_offset={r['file_offset']:r for r in observed};assert len(by_offset)==len(plan)
    for row in plan:
        got=by_offset[row['file_offset']]
        assert got['shared'] and got['user_pfn']==got['kernel_pfn']>0 and row['kind']==got['kind']
    records=[dict(name=a,address=int(b,0),krg_extent=int(c,0),owner=d,role=e) for a,b,c,d,e in
             csv.reader((metadata/'resolved_symbol_addresses.txt').read_text().splitlines())]
    with library.open('rb') as stream:
        elf=ELFFile(stream);symbols=elf.get_section_by_name('.symtab')
        functions={s.name:s.entry for s in symbols.iter_symbols() if s['st_info']['type']=='STT_FUNC' and s['st_shndx']!='SHN_UNDEF'}
        objects={s.name:s.entry for s in symbols.iter_symbols() if s['st_info']['type']=='STT_OBJECT' and s['st_shndx']!='SHN_UNDEF'}
        source_funcs=[r for r in records if r['name'] in functions and r['role'] in ('internal','export') and r['krg_extent']>0
            and any(p['kind']=='text' and p['kernel_vaddr']<=r['address']<p['kernel_vaddr']+4096 for p in plan)]
        aliases=collections.defaultdict(list)
        for r in source_funcs: aliases[r['address']].append(r['name'])
        thunks=[names for names in aliases.values() if any('thunk' in n for n in names)]
        code=[names for names in aliases.values() if not any('thunk' in n for n in names)]
        mapped={p['file_offset'] for p in plan if p['kind']=='text'}
        executable=set()
        for section in elf.iter_sections():
            if section['sh_flags']&4 and section['sh_size']:
                executable.update(range(section['sh_offset']//4096*4096,(section['sh_offset']+section['sh_size']+4095)//4096*4096,4096))
        slots=[];relocations=[]
        for section in elf.iter_sections():
            if section['sh_type']!='SHT_RELA':continue
            symtab=elf.get_section(section['sh_link'])
            for rel in section.iter_relocations():
                sym=symtab.get_symbol(rel['r_info_sym'])
                relocations.append(dict(offset=rel['r_offset'],type=rel['r_info_type'],symbol=sym.name,
                    symbol_type=sym['st_info']['type'],undefined=sym['st_shndx']=='SHN_UNDEF'))
        for symbol,entry in objects.items():
            if symbol.endswith('_slot'):
                rel=[r for r in relocations if r['offset']==entry['st_value']]
                assert entry['st_size']==8 and len(rel)==1 and rel[0]['type']==1
                assert rel[0]['undefined'] and rel[0]['symbol_type']=='STT_FUNC'
                slots.append(dict(name=symbol,address=entry['st_value'],bytes=8,user_target=rel[0]['symbol']))
        if name=='clocktime':
            from capstone import Cs,CS_ARCH_X86,CS_MODE_64
            from capstone.x86 import X86_OP_MEM,X86_REG_RIP
            data=elf.get_section_by_name('.data');assert not relocations and data['sh_size']==40
            binding=functions['__vkso_bind_context'];section=elf.get_section(binding['st_shndx'])
            offset=binding['st_value']-section['sh_addr']
            engine=Cs(CS_ARCH_X86,CS_MODE_64);engine.detail=True
            stores=[]
            for insn in engine.disasm(section.data()[offset:offset+binding['st_size']],binding['st_value']):
                if insn.mnemonic=='mov' and insn.operands[0].type==X86_OP_MEM and insn.operands[0].mem.base==X86_REG_RIP:
                    stores.append(insn.address+insn.size+insn.operands[0].mem.disp)
            assert stores==[data['sh_addr']+8*i for i in range(5)],stores
    result=dict(name=name,evidence=str(base.relative_to(ROOT)),declared_code_functions=len(code),
        code_names=code,resident_thunk_bodies=len(thunks),thunk_aliases=thunks,source_symbols=records,
        pages=dict(collections.Counter(p['kind'] for p in plan)),generated_executable_pages=len(executable-mapped),
        helper_function_slots=slots,relocations=relocations,pfn_matches=len(plan),
        counts_scope='positive-extent resolved STT_FUNC starts on declared source text pages, deduplicated by address; thunk aliases separate; excludes incidental neighbors and private generated code')
    if name=='clocktime':result['explicit_context_slots']=dict(function=2,data=3,bytes=40,
        fields=['MM_data','PVClock page','Hyper-V page','clock_gettime failure','gettimeofday failure'])
    if name=='sort':result['callback_parameters']=['comparator','optional swap (default if NULL)']
    save(target/'structure.json',result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--linux-tarball',type=Path,default=Path('/tmp/vkso-ledger-linux-5.15.198.tar.xz'))
    p.add_argument('--algorithm-archive',action='append',default=[],metavar='NAME=PATH',
                   help='select an observed LZ4/BCH/XZ archive explicitly')
    p.add_argument('--algorithm-source',type=Path,default=HERE/'results/adaptation-ledger-20260912-attempt04')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    copy(Path(__file__),out/'applicability_ledger.py')
    copy(HERE/'adaptation_ledger.py',out/'adaptation_ledger.py')
    copy(CLOCK/'vkso-tests/code-size/count_manifest.py',out/'count_manifest.py')
    archives={name:HERE/f'results/{name}-kernel-cost-qemu-20260912-attempt{attempt}'
              for name,attempt in (('lz4','02'),('bch','01'),('xz','03'))}
    for value in args.algorithm_archive:
        name,path=value.split('=',1);assert name in archives
        archives[name]=Path(path).resolve()
    structures=[]
    for name in ('lz4','bch','xz'):
        base=archives[name];v=base/'evidence/validation'
        assert json.loads((base/'result.json').read_text())['status']=='pass'
        structures.append(carrier(out,name,base,v/'export/vkso/metadata',v/f'export/vkso/lib/libvkso_{name}.so',v/'registered-pfns.json'))
        copy(base/'result.json',out/'carriers'/name/'result.json')
        owner=base/f'payload/owner/vkso_{name}.ko';copy(owner,out/'carriers'/name/owner.name)
        if (base/'kernel-cost-audit.json').exists():
            copy(base/'kernel-cost-audit.json',out/'carriers'/name/'kernel-cost-audit.json')
    for name in ('xxh32','sort'):
        base=HERE/'results/applicability-identity-qemu-20260912-attempt01';v=base/'evidence/validation'/name
        structures.append(carrier(out,name,base,v/'export/vkso/metadata',v/'export/vkso/lib/libkernel.so',v/'registered-pfns.json'))
        copy(base/'independent-audit.json',out/'carriers'/name/'runtime-audit.json')
    base=CLOCK/'vkso-tests/revision/results/normal-campaign/step-001';package=CLOCK/'vkso-tests/baremetal/artifacts/reader-load-v4-normal'
    assert (package/'libkernel.so').read_bytes()==(base/'vkso/package/libkernel.so').read_bytes()
    assert (package/'page_mappings.txt').read_bytes()==(base/'vkso/package/page_mappings.txt').read_bytes()
    structures.append(carrier(out,'clocktime',base,package,base/'vkso/package/libkernel.so',base/'vkso/footprint.json'))
    for name in ('complete.json','running.config'):copy(base/name,out/'carriers/clocktime'/name)
    for name in ('vkso.config','source.patch'):copy(package/name,out/'carriers/clocktime'/name)
    for name in ('vkso_user_entry.S','vkso_user_wrapper.c','vkso_user_wrapper.h'):
        copy(CLOCK/'vkso-tests/functional'/name,out/'carriers/clocktime'/name)
    source=clock_sources(out,args.linux_tarball)
    old=args.algorithm_source.resolve();shutil.copytree(old,out/'algorithm-source')
    copy(ROOT/'page_cache_replace/owner.h',out/'common-support/owner.h')
    annotations=json.loads((HERE/'applicability-ledger-cases.json').read_text())
    copy(HERE/'applicability-ledger-cases.json',out/'case-interpretation.json')
    cohort=HERE/'results/applicability-revised-20260912'
    for filename in ('candidate-manifest.json','results.json','inspection-complete.json','identity.json'):
        copy(cohort/filename,out/'fixed-cohort'/filename)
    states=[r for r in json.loads((cohort/'results.json').read_text()) if r['cohort']=='prospective']
    candidate_ids=[r['id'] for r in json.loads((cohort/'candidate-manifest.json').read_text())['cases'] if r['cohort']=='prospective']
    assert [r['id'] for r in states]==candidate_ids and len(states)==8
    classes={'xxh32':'explicit input; unmodified algorithm', 'sort':'caller-owned callbacks; unmodified algorithm',
        'crc32_le':'current binary/tool limitation: absolute table address',
        'string_escape_mem':'current binary/tool limitation: absolute table addresses',
        'sha256':'current binary/tool limitation: absolute addresses and instrumentation',
        'hex_dump_to_buffer':'current binary/tool limitation: unspecialized formatting/error dependency closure',
        'rhashtable_insert_slow':'kernel container/state/synchronization semantics plus binary findings',
        'get_random_bytes':'kernel-private evolving RNG state plus binary findings'}
    joined=[]
    for state in states:
        passed=state['checks'][0]['status']=='checker_pass'
        assert passed==(state['id'] in ('xxh32','sort'))
        joined.append(dict(id=state['id'],checker=state['checks'][0],classification=classes[state['id']],
            carrier='constructed' if passed else 'not attempted after static rejection',
            runtime=annotations['cases'][state['id']]['runtime'] if passed else 'not attempted',
            algorithm_edits=0 if passed else None))
    for name in ('lz4','bch','xz'):
        base=archives[name]
        build=(base/'kernel-cost-build/owner' if name=='lz4' and (base/'kernel-cost-build/owner').exists()
               else base/('baseline-source' if name=='lz4' else 'build-source')/'kmod')
        for filename in ('module_meta.c',):
            assert (build/filename).read_bytes()==(old/name/'support'/filename).read_bytes(),(name,filename)
    copy(HERE/'results/bch-kernel-qemu-20260912-attempt03/evidence/validation/coverage-audit.json',out/'carriers/bch/earlier-kernel-coverage.json')
    save(out/'ledger.json',dict(scope='fixed cohort plus retrospective deployed cases; no new runtime or performance trials',
        prospective=joined,case_interpretation=annotations['cases'],carriers=structures,clocktime_product_sloc=source['product_sloc'],
        algorithm_sources=json.loads((old/'ledger.json').read_text())))
    print(json.dumps([dict(name=r['name'],code=r['declared_code_functions'],thunks=r['resident_thunk_bodies'],
        pages=r['pages'],generated=r['generated_executable_pages'],helper_slots=len(r['helper_function_slots'])) for r in structures],indent=2))
if __name__=='__main__':main()
