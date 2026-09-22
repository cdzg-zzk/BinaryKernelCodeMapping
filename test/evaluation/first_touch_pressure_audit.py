#!/usr/bin/env python3
"""Reconstruct every pressure trial, without fault-class or latency selection."""
from pathlib import Path
import argparse,collections,ctypes,json,random,statistics

def values(raw):
    return {line.split()[0].rstrip(':'):int(line.split()[1]) for line in raw.splitlines()}

def summarize(directory):
    config=json.loads((directory/'pressure-config.json').read_text())
    rows=[json.loads(line) for line in (directory/'pressure-trials.jsonl').read_text().splitlines()]
    assert config['protocol']=='first-touch-pressure-v1' and config['phases']==['baseline','pressure','recovery']
    assert len(rows)==30 and config['trials_per_phase']==10 and config['passes_per_trial']==2
    assert config['file_bytes']==1024**3 and config['probe_cpu']==1 and config['worker_cpu']==0
    initial=values(config['initial']['meminfo'])
    assert initial['SwapTotal']==0 and len(config['initial']['swaps'].splitlines())==1
    reserve=min(initial['MemAvailable']*1024-512*1024**2,initial['MemTotal']*1024*4//5)//4096*4096
    assert config['anonymous_bytes']==reserve>=512*1024**2
    rng=random.Random(config['seed']);groups={};reclaim=[]
    for index,row in enumerate(rows):
        phase=config['phases'][index//10]
        order=['native','stub'];rng.shuffle(order)
        assert row['phase']==phase and row['trial']==index%10 and row['order']==order
        assert set(row['calls'])==set(row['prepared'])=={'native','stub'} and row['owner_refcnt']==1
        before,after=values(row['before']['vmstat']),values(row['after']['vmstat'])
        if phase=='pressure':
            scan=row['scan'];assert scan['read_bytes']==2*config['file_bytes'] and scan['anonymous_bytes']==reserve
            expected_sum=2*1024*sum((i*17+31)%251 for i in range(0,1024**2,4096))
            assert scan['checksum']==expected_sum
            delta={k:after[k]-before[k] for k in ('pgscan_kswapd','pgscan_direct','pgsteal_kswapd',
                'pgsteal_direct','workingset_refault_file','pgmajfault','oom_kill')}
            assert all(value>=0 for value in delta.values()) and delta['oom_kill']==0
            reclaim.append(delta)
        else: assert row['scan'] is None
        for name,call in row['calls'].items():
            assert row['prepared'][name]['event']=='prepared' and not row['prepared'][name]['pte']>>63
            assert call['event']=='call' and call['answer']==call['expected']==config['expected']
            assert call['cpu']==1 and not call['pte_before']>>63 and call['pte_after']>>63
            assert call['resident_before'] in (0,1) and call['cycles']>0 and call['minflt']>=0 and call['majflt']>=0
            if name=='stub': assert call['pte_after']&((1<<55)-1)==config['source_pfn']
            groups.setdefault(f'{phase}/{name}',[]).append(call)
    summary={}
    for key,calls in groups.items():
        summary[key]=dict(calls=len(calls),resident_before=sum(r['resident_before'] for r in calls),
            fault_classes=dict(collections.Counter(f"{r['minflt']}/{r['majflt']}" for r in calls)),
            diagnostic_cycles=dict(min=min(r['cycles'] for r in calls),median=statistics.median(r['cycles'] for r in calls),
                max=max(r['cycles'] for r in calls)))
    reclaim_trials=sum(r['pgscan_kswapd']+r['pgscan_direct']>0 and r['pgsteal_kswapd']+r['pgsteal_direct']>0 for r in reclaim)
    totals={key:sum(r[key] for r in reclaim) for key in reclaim[0]}
    snapshots={phase:json.loads((directory/f'pressure-phase-{phase}.json').read_text()) for phase in config['phases']}
    start=values(snapshots['baseline']['before']['vmstat']);end=values(snapshots['recovery']['after']['vmstat'])
    assert end['oom_kill']==start['oom_kill']
    return dict(protocol=config['protocol'],raw_calls=len(rows)*2,paired_trials=len(rows),anonymous_bytes=reserve,
        reclaim_exercised=reclaim_trials==10,pressure_trials_with_reclaim=reclaim_trials,
        scan_interval_vmstat_deltas=totals,groups=summary,
        scope='all instrumented calls in one private guest; idle-page reclaim after MADV_DONTNEED; no latency filtering or physical-host estimate')

def audit(out):
    from first_touch_audit import symbol_bytes
    from applicability_runtime_audit import hash_vectors
    root=Path(__file__).resolve().parents[2];v=out/'evidence/validation';payload=out/'payload'
    result=json.loads((out/'result.json').read_text())
    assert result['status']=='pass' and result['qemu_returncode']==0 and not result['kernel_failure']
    replay=summarize(v);assert replay==json.loads((v/'pressure-summary.json').read_text())
    assert replay['reclaim_exercised'] and result['guest_record']['collection']['status']=='complete'
    native=symbol_bytes(payload/'native/libclone_xxh32.so','clone_xxh32')
    owner=symbol_bytes(payload/'owner/zzk_xxh32_lkm.ko','zzk_xxh32')
    assert len(native)==338 and owner[:338]==native and all(b==0xcc for b in owner[338:])
    assert (v/'registered-function.bin').read_bytes()==(v/'native-function.bin').read_bytes()==native
    oracle=ctypes.CDLL('/usr/lib/x86_64-linux-gnu/libxxhash.so.0').XXH32
    oracle.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint32];oracle.restype=ctypes.c_uint32
    config=json.loads((v/'pressure-config.json').read_text())
    assert config['expected']==oracle(bytes.fromhex(config['input_hex']),5,config['hash_seed'])
    for phase in ('before','after'):
        data=json.loads((v/f'functional-{phase}-pressure.json').read_text())
        assert data['status']=='pass' and len(data['rows'])==247 and data['matched_function_bytes']==338
        for index,(row,vector) in enumerate(zip(data['rows'],hash_vectors())):
            kind,length,alignment,seed,raw=vector
            assert [row[k] for k in ('index','kind','length','alignment','seed')]==[index,kind,length,alignment,seed]
            assert row['native']==row['stub']==row['expected']==oracle(raw,length,seed)
        pfns=json.loads((v/f'pressure-pfns-{phase}.json').read_text())
        assert pfns['status']=='pass' and len(pfns['pages'])==1
        page=pfns['pages'][0];assert page['shared'] and page['user_pfn']==page['kernel_pfn']==config['source_pfn']
    assert '/work/native/libclone_xxh32.so' not in (v/'controller-maps-before-sampling.txt').read_text()
    assert result['guest_record']['restoration_verified']
    assert {r.split()[0] for r in result['guest_record']['modules_after'].splitlines()}=={'virtio_blk'}
    for name in ('benchmark_first_touch.c','pressure_probe.c','pressure_worker.c'):
        assert (payload/'benchmark'/name).read_bytes()==(root/'test/test_first_call/matrix_bench'/name).read_bytes()
    for name in ('first_touch_pressure.py','first_touch_pressure_audit.py'):
        assert (payload/name).read_bytes()==(root/'test/evaluation'/name).read_bytes()
    assert (payload/'repo/vkso').read_bytes()==(root/'vkso').read_bytes()
    assert (payload/'repo/page_cache_replace/page_cache_replace.ko').read_bytes()==(root/'page_cache_replace/page_cache_replace.ko').read_bytes()
    events=[json.loads(line) for line in (v/'pressure-events.jsonl').read_text().splitlines()]
    assert len(events)==135  # Three READY, 120 probe commands, 10 scans, ALLOC and FREE.
    assert sum(e['response']['event']=='scanned' for e in events)==10
    report=dict(status='pass',boot_id=result['guest_record']['boot_id'],matched_function_bytes=338,
        oracle_vectors_per_checkpoint=247,pfn_call_matches=30,collection=replay)
    (out/'independent-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args()
    print(json.dumps(audit(a.directory.resolve()),indent=2))
