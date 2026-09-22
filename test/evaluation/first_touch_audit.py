#!/usr/bin/env python3
"""Replay raw first-touch filtering, full XXH32 oracles and executed code identity."""
from pathlib import Path
import argparse,csv,ctypes,importlib.util,json,sys
from elftools.elf.elffile import ELFFile
from applicability_runtime_audit import hash_vectors
ROOT=Path(__file__).resolve().parents[2]

def symbol_bytes(path,name):
    with path.open('rb') as stream:
        elf=ELFFile(stream);symbols=elf.get_section_by_name('.symtab') or elf.get_section_by_name('.dynsym')
        symbol=symbols.get_symbol_by_name(name)[0];section=elf.get_section(symbol['st_shndx'])
        offset=symbol['st_value']-section['sh_addr'];return section.data()[offset:offset+symbol['st_size']]

def audit(out):
    result=json.loads((out/'result.json').read_text());v=out/'evidence/validation'
    assert result['status']=='pass' and result['qemu_returncode']==0 and not result['kernel_failure']
    payload=out/'payload'
    current=ROOT/'test/test_first_call/matrix_bench/analyze_first_touch.py'
    spec=importlib.util.spec_from_file_location('first_touch_analysis',current);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    replay=m.audit(v/'first-touch.logs');saved=json.loads((v/'first-touch-analysis.json').read_text());assert replay==saved
    assert replay['complete'] and result['guest_record']['collection']['status']=='complete'
    env=replay['environment'];assert env['protocol']=='first-touch-raw-v2' and env['cpu']=='1'
    assert [env[k] for k in ('runs_per_attempt','target_successes','max_attempts','threshold_pct')]==['100','5','20','90.0']
    assert env['conditions']=='hot pte-cold post-drop' and env['input_bytes']=='5' and env['seed']=='0x1234'
    assert set(replay['groups'])=={f'{a}/{b}' for a in ('native','stub') for b in ('hot','pte-cold','post-drop')}
    native=symbol_bytes(payload/'native/libclone_xxh32.so','clone_xxh32')
    owner=symbol_bytes(payload/'owner/zzk_xxh32_lkm.ko','zzk_xxh32')
    assert len(native)==338 and owner[:338]==native and all(b==0xcc for b in owner[338:])
    assert (v/'registered-function.bin').read_bytes()==(v/'native-function.bin').read_bytes()==native
    assert '/work/native/libclone_xxh32.so' not in (v/'controller-maps-before-sampling.txt').read_text()
    oracle=ctypes.CDLL('/usr/lib/x86_64-linux-gnu/libxxhash.so.0').XXH32
    oracle.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint32];oracle.restype=ctypes.c_uint32
    functional=json.loads((v/'functional.json').read_text());assert functional['status']=='pass' and len(functional['rows'])==247
    for i,(row,vector) in enumerate(zip(functional['rows'],hash_vectors())):
        kind,length,alignment,seed,data=vector
        assert [row[k] for k in ('index','kind','length','alignment','seed')]==[i,kind,length,alignment,seed]
        assert row['native']==row['stub']==row['expected']==oracle(data,length,seed)
    pfns=json.loads((v/'registered-pfns.json').read_text());assert pfns['status']=='pass' and len(pfns['pages'])==1
    assert pfns['pages'][0]['shared'] and pfns['pages'][0]['user_pfn']==pfns['pages'][0]['kernel_pfn']
    assert result['guest_record']['restoration_verified']
    assert {r.split()[0] for r in result['guest_record']['modules_after'].splitlines()}=={'virtio_blk'}
    log=(v/'export-and-first-touch.log').read_text();assert 'using caller-supplied API declarations' in log and '(exit code: 0)' in log
    manager=(v/'export/vkso/metadata/page_replace.log').read_text()
    assert 'operation=3 ' in manager and 'operation=5 ' in manager and 'Holding active replacement session.' in manager
    for name in ('benchmark_first_touch.c','run_benchmarks.sh','analyze_first_touch.py'):
        assert (payload/'benchmark'/name).read_bytes()==(ROOT/'test/test_first_call/matrix_bench'/name).read_bytes(),name
    assert (payload/'repo/vkso').read_bytes()==(ROOT/'vkso').read_bytes()
    assert (payload/'repo/page_cache_replace/page_cache_replace.ko').read_bytes()==(ROOT/'page_cache_replace/page_cache_replace.ko').read_bytes()
    groups={name:dict(attempts=g['attempts'],decisions=g['decisions'],fault_classes=g['fault_classes'],
        calls={key:value['calls'] for key,value in g['views'].items()},preparation_failures=g['preparation_failures']) for name,g in replay['groups'].items()}
    report=dict(status='pass',boot_id=result['guest_record']['boot_id'],matched_function_bytes=338,oracle_vectors=247,
        attempted_batches=sum(g['attempts'] for g in replay['groups'].values()),
        prepared_calls=sum(g['views']['all_prepared_calls']['calls'] for g in replay['groups'].values()),
        iqr_retained_calls=sum(g['views']['iqr_retained_calls']['calls'] for g in replay['groups'].values()),
        accepted_batch_calls=sum(g['views']['accepted_batch_calls']['calls'] for g in replay['groups'].values()),
        groups=groups,scope='full protocol and functional/PFN validation in one KVM deployment; not new physical-host latency estimates')
    (out/'independent-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args()
    r=audit(a.directory.resolve());print(json.dumps({k:v for k,v in r.items() if k!='groups'},indent=2))
