#!/usr/bin/env python3
"""Replay the cross-case source ledger, bindings and declared-page arithmetic."""
from pathlib import Path
import argparse,collections,csv,json,shutil,subprocess,tempfile
from elftools.elf.elffile import ELFFile
from adaptation_ledger import compare,counter
from applicability_ledger import code_counts

def read(path):return json.loads(path.read_text())

def replay_patch(before,after,patch):
    with tempfile.TemporaryDirectory(prefix='vkso-source-ledger-') as temp:
        directory=Path(temp)/'source';shutil.copytree(before,directory)
        run=subprocess.run(['patch','--batch','--forward','-p1','-i',str(patch.resolve())],cwd=directory,capture_output=True,text=True)
        assert run.returncode==0,run.stdout+run.stderr
        expected={p.relative_to(after) for p in after.rglob('*') if p.is_file()}
        assert expected=={p.relative_to(directory) for p in directory.rglob('*') if p.is_file()}
        for rel in expected:assert (after/rel).read_bytes()==(directory/rel).read_bytes(),rel
        return len(expected)

def audit(out):
    ledger=read(out/'ledger.json');clock=read(out/'clocktime/source-ledger.json')
    totals=collections.defaultdict(int)
    for row in clock['semantic_rows']:
        if row['system']=='Raw':path=out/'clocktime/upstream'/row['path']
        else:path=out/'clocktime/6656f97'/row['root']/row['path']
        counts=code_counts(path.read_text(),row['path'],row['ranges'])
        assert counts=={k:row[k] for k in counts},row
        totals[f"{row['system']}/{row['view']}/{row['status']}"]+=counts['lexical_sloc']
    assert dict(totals)==clock['totals']
    product={system.lower():sum(v for k,v in totals.items() if k.startswith((system+'/runtime/',system+'/build/'))) for system in ('Raw','VKSO')}
    assert product==clock['product_sloc']==ledger['clocktime_product_sloc']==dict(raw=1505,vkso=1305)
    directory=out/'clocktime/full-file-diff'
    for row in clock['full_file_churn']:
        rel=Path(row['root'])/row['path']
        got=compare((directory/'before'/rel).read_text(),(directory/'after'/rel).read_text(),row['path'])
        assert got=={k:row[k] for k in got}
    patch_files={'clocktime':replay_patch(directory/'before',directory/'after',directory/'source.diff')}
    alg=read(out/'algorithm-source/ledger.json')
    assert alg==ledger['algorithm_sources']
    for row in alg['algorithms']:
        path=out/'algorithm-source'/row['algorithm']
        counts=collections.defaultdict(int)
        for file in row['files']:
            got=compare((path/'original'/file['name']).read_text(),(path/'adapted'/file['name']).read_text(),file['name'])
            assert got=={k:file[k] for k in got}
            for key,value in got.items():counts[key]+=value
        assert dict(counts)==row['totals']
        for file in row['support_files']:
            source=path/'support'/Path(file['path']).name;lines=source.read_text().splitlines()
            assert len(lines)==file['physical_lines']
            if file['lexical_sloc'] is not None:assert sum(counter.lexical_code_flags(source,lines))==file['lexical_sloc']
        patch_files[row['algorithm']]=replay_patch(path/'original',path/'adapted',path/'source.diff')
    pfns=0;bindings={}
    for carrier in ledger['carriers']:
        name=carrier['name'];path=out/'carriers'/name
        assert carrier==read(path/'structure.json')
        observation=read(path/('footprint.json' if name=='clocktime' else 'registered-pfns.json'))['pages']
        plan=list(csv.reader(l for l in (path/'page_mappings.txt').read_text().splitlines() if l and not l.startswith('#')))
        assert len(plan)==len(observation)==carrier['pfn_matches']
        by_offset={r['file_offset']:r for r in observation};assert len(by_offset)==len(plan)
        for offset,address,kind,section in plan:
            observed=by_offset[int(offset,0)]
            assert observed['kind']==kind and observed['shared'] and observed['user_pfn']==observed['kernel_pfn']>0
            if 'pagemap_entry' in observed:
                entry=int(observed['pagemap_entry'],0)
                assert entry>>63 and entry&((1<<55)-1)==observed['user_pfn']
        pfns+=len(plan)
        dso=next(path.glob('lib*.so'))
        with dso.open('rb') as stream:
            elf=ELFFile(stream);symbols=elf.get_section_by_name('.symtab')
            names={s.name:s for s in symbols.iter_symbols()}
            executable=set()
            for section in elf.iter_sections():
                if section['sh_flags']&4 and section['sh_size']:
                    executable.update(range(section['sh_offset']//4096*4096,
                        (section['sh_offset']+section['sh_size']+4095)//4096*4096,4096))
            source_pages={int(offset,0) for offset,_,kind,_ in plan if kind=='text'}
            assert len(executable-source_pages)==carrier['generated_executable_pages']
            assert dict(collections.Counter(kind for _,_,kind,_ in plan))==carrier['pages']
            expected_groups=[];grouped=collections.defaultdict(list)
            selected=[r for r in carrier['source_symbols'] if r['role'] in ('internal','export') and r['krg_extent']>0
                and r['name'] in names and names[r['name']]['st_info']['type']=='STT_FUNC'
                and any(kind=='text' and int(address,0)<=r['address']<int(address,0)+4096 for _,address,kind,_ in plan)]
            for row in selected:grouped[row['address']].append(row['name'])
            code=[g for g in grouped.values() if not any('thunk' in n for n in g)]
            thunks=[g for g in grouped.values() if any('thunk' in n for n in g)]
            assert code==carrier['code_names'] and thunks==carrier['thunk_aliases']
            assert len(code)==carrier['declared_code_functions'] and len(thunks)==carrier['resident_thunk_bodies']
            relocs={}
            for section in elf.iter_sections():
                if section['sh_type']=='SHT_RELA':
                    symtab=elf.get_section(section['sh_link'])
                    for rel in section.iter_relocations():
                        relocs[rel['r_offset']]=(rel['r_info_type'],symtab.get_symbol(rel['r_info_sym']).name)
            for slot in carrier['helper_function_slots']:
                symbol=names[slot['name']]
                assert symbol['st_info']['type']=='STT_OBJECT' and symbol['st_size']==8
                assert symbol['st_value']==slot['address'] and relocs[slot['address']]==(1,slot['user_target'])
        if name in ('bch','lz4','xz'):
            with (path/f'vkso_{name}.ko').open('rb') as stream:
                elf=ELFFile(stream);symtab=elf.get_section_by_name('.symtab')
                syms={s.name:s for s in symtab.iter_symbols()};bound=[]
                for slot in carrier['helper_function_slots']:
                    symbol=syms[slot['name']];found=[]
                    for section in elf.iter_sections():
                        if section['sh_type']=='SHT_RELA' and section['sh_info']==symbol['st_shndx']:
                            table=elf.get_section(section['sh_link'])
                            for rel in section.iter_relocations():
                                if rel['r_offset']==symbol['st_value']:
                                    assert rel['r_info_type']==1 and rel['r_addend']==0
                                    found.append(table.get_symbol(rel['r_info_sym']).name)
                    assert len(found)==1
                    bound.append(dict(slot=slot['name'],kernel_target=found[0],user_target=slot['user_target']))
                bindings[name]=bound
    assert pfns==20
    prospective=ledger['prospective'];assert len(prospective)==8
    original=[r for r in read(out/'fixed-cohort/results.json') if r['cohort']=='prospective']
    assert [r['id'] for r in prospective]==[r['id'] for r in original]
    assert all(a['checker']==b['checks'][0] for a,b in zip(prospective,original))
    assert sum(r['checker']['status']=='checker_pass' for r in prospective)==2
    assert all(r['runtime']=='not attempted' for r in prospective if r['checker']['status']=='checker_fail')
    report=dict(status='pass',carriers=6,prospective=8,static_passes=2,static_rejections=6,
        matched_declared_pages=pfns,source_patch_replay_files=patch_files,clocktime_product_sloc=product,
        kernel_user_slot_bindings=bindings,scope='source, structure and existing-evidence replay; no new kernel execution or performance')
    (out/'independent-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
    print(json.dumps(audit(args.directory.resolve()),indent=2))
