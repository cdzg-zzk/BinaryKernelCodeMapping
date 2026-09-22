#!/usr/bin/env python3
"""Reconstruct all scale, cache, PFN and terminal-record observations."""
from pathlib import Path
import argparse,csv,io,json,re,statistics,subprocess
ROOT=Path(__file__).resolve().parents[2]
def audit(out):
    result=json.loads((out/'result.json').read_text());v=out/'evidence/validation'
    assert result['status']=='pass' and not result['kernel_failure'] and result['qemu_returncode']==0
    data=json.loads((v/'status.json').read_text());assert data['status']=='pass' and data['cpu_affinity']==[1]
    manager_retires='r.operation = VKSO_FORGET;' in (out/'source/manager.cpp').read_text()
    assert len(data['rows'])==len(data['schedule'])==96
    pfns=[int(r['pfn']) for r in csv.DictReader((v/'source-pages.csv').open())]
    assert len(pfns)==32 and len(set(pfns))==32
    seen=set();groups={};records=[];manager_rss=[];manager_rollup=[];manager_pss=[];fd_counts=[];capacities=set()
    for planned,listed in zip(data['schedule'],data['rows']):
        row=json.loads((v/listed['result']).read_text());count=row['count'];route=row['route']
        key=(row['repeat'],count,row['cache'],route);assert key not in seen;seen.add(key)
        assert all(row[k]==planned[k]==listed[k] for k in planned)
        assert row['residency_before']==[int(row['cache']=='prepared')]*count
        assert [p['pfn'] for p in row['active']]==pfns[:count]
        assert all(not p['original'] for p in row['active'])
        assert all(p['original'] and p['pfn']!=pfns[i] for i,p in enumerate(row['restored']))
        assert len(row['restored'])==count and row['refs_after']==data['baseline_refs']
        if route=='manager' and manager_retires:
            assert row['terminal']['status']==-2 and row['terminal']['state']==0 and row['forget'] is None
        else:
            assert row['terminal']['state']==4 and row['terminal']['applied']==0
            assert row['forget']['status']==0
        assert row['after_forget']['status']==-2
        assert row['start_ns']<=row['ready_ns']<row['release_start_ns']<=row['done_ns']
        assert row['register_to_ready_ns']==row['ready_ns']-row['start_ns']
        assert row['release_to_done_ns']==row['done_ns']-row['release_start_ns']
        if route=='manager':
            raw=(v/listed['result']).parent/'manager.log'
            operations=[{k:int(val) for k,val in re.findall(r'(\w+)=(-?\d+)',line)}
                        for line in raw.read_text().splitlines() if line.startswith('VKSO_TRANSACTION ')]
            assert operations==row['transactions']
            assert [x['event'] for x in row['events']]==['START','READY','DONE']
            assert all(e['transaction']==row['transaction'] and e['status']==0 for e in row['events'])
            assert row['ready_ns']==row['events'][1]['received_ns'] and row['done_ns']==row['events'][2]['received_ns']
            snapshot=json.loads((raw.parent/'manager-process.json').read_text())
            manager_rss.append(int(re.search(r'^VmRSS:\s+(\d+)',snapshot['status'],re.M)[1]))
            manager_rollup.append(int(re.search(r'^Rss:\s+(\d+)',snapshot['smaps_rollup'],re.M)[1]))
            manager_pss.append(int(re.search(r'^Pss:\s+(\d+)',snapshot['smaps_rollup'],re.M)[1]))
            fd_counts.append(len(snapshot['fd_targets']));capacities.add(row['pipe_capacity_bytes'])
        else:
            operations=[x['response'] for x in row['operations']]
            assert all(x['start_ns']<=x['end_ns'] for x in row['operations'])
        assert [x['operation'] for x in operations]==([1,2,3,5,6] if route=='manager' and manager_retires else [1,2,3,5])
        assert all(x['status']==0 for x in operations)
        assert operations[2]['applied']==count and operations[3]['applied']==0
        assert operations[2]['prepare_ns']==operations[3]['prepare_ns']
        assert operations[2]['apply_ns']==operations[3]['apply_ns']
        entry=dict(repeat=row['repeat'],pages=count,cache=row['cache'],route=route,
            register_ns=row['register_to_ready_ns'],release_ns=row['release_to_done_ns'],
            kernel_prepare_ns=operations[2]['prepare_ns'],kernel_apply_ns=operations[2]['apply_ns'],
            kernel_release_ns=operations[3]['release_ns'])
        records.append(entry);groups.setdefault((count,row['cache'],route),[]).append(entry)
    assert len(seen)==96 and len(groups)==24 and all(len(x)==4 for x in groups.values())
    calibration=data['clock_helper_calibration'];assert len(calibration)==30
    stamps=[int(line.split('\t')[3]) for line in (v/'clock-events.tsv').read_text().splitlines()]
    assert len(stamps)==30
    for event,stamp in zip(calibration,stamps):
        assert event['start_ns']<=stamp<=event['end_ns']
        assert event['elapsed_ns']==event['end_ns']-event['start_ns']
    assert {x.split()[0] for x in data['modules_after'].splitlines()}=={'virtio_blk'}
    module=out/'payload/page_cache_replace.ko';layouts={}
    for name in ('transaction','binding'):
        raw=subprocess.check_output(['pahole','-C',name,str(module)],text=True)
        (out/f'{name}-layout.txt').write_text(raw)
        layouts[name]=int(re.search(r'/\* size: (\d+),',raw)[1])
    protocol=int(re.search(r'#define VKSO_PROTOCOL_VERSION (\d+)', (out/'source/protocol.h').read_text())[1])
    assert protocol in (3,4)
    assert layouts=={'transaction':688,'binding':56 if protocol==3 else 64}
    # The retained ELF layout and actual allocating source determine requested
    # bytes only. They do not determine kmalloc usable size or physical slab pages.
    source=(out/'source/page_cache_replace.c').read_text()
    assert 'kzalloc(sizeof(*t), GFP_KERNEL)' in source and 'kvcalloc(r->total, sizeof(*t->pages), GFP_KERNEL)' in source
    assert 'kvfree(t->pages);\n    t->pages = NULL;' in source
    assert module.read_bytes()==(ROOT/'page_cache_replace/page_cache_replace.ko').read_bytes()
    assert (out/'payload/manager').read_bytes()==(ROOT/'page_cache_replace/manager').read_bytes()
    with (out/'scale-raw.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    summary=[dict(pages=n,cache=c,route=r,registrations=len(items),**{k:statistics.median(x[k] for x in items)
                for k in ('register_ns','release_ns','kernel_prepare_ns','kernel_apply_ns','kernel_release_ns')})
             for (n,c,r),items in sorted(groups.items())]
    report=dict(status='pass',boot_id=data['boot_id'],sessions=96,manager_sessions=48,direct_sessions=48,
        shared_pfn_checks=sum(r['pages'] for r in records),restored_pfn_checks=sum(r['pages'] for r in records),
        cpu_affinity=[1],clock_helper_median_ns=statistics.median(r['elapsed_ns'] for r in calibration),
        manager_status_vmrss_kib_range=[min(manager_rss),max(manager_rss)],
        manager_smaps_rss_kib_range=[min(manager_rollup),max(manager_rollup)],
        manager_smaps_pss_kib_range=[min(manager_pss),max(manager_pss)],manager_fd_count_range=[min(fd_counts),max(fd_counts)],
        pipe_capacity_bytes=sorted(capacities),allocation_request_bytes=layouts,
        requested_live_bytes={str(n):layouts['transaction']+layouts['binding']*n for n in (1,2,4,8,16,32)},terminal_requested_bytes=688,
        manager_terminal_record_after_done=not manager_retires,
        manager_terminal_requested_bytes_after_done=0 if manager_retires else 688,
        resource_scope='transaction allocation requests; FIFO capacity and manager process metrics separate; not physical net memory',
        summary=summary,measurement_scope='four registrations per size/cache/route in one KVM boot; kernel stages nested; no application execution or physical-host scaling claim')
    (out/'independent-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args()
    r=audit(a.directory.resolve());print(json.dumps({k:v for k,v in r.items() if k!='summary'},indent=2))
