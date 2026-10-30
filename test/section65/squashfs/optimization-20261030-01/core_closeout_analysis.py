#!/usr/bin/env python3
"""Descriptive, independently checked core closeout; never claims 30/30."""
import copy,hashlib,json,math,statistics,time
from collections import defaultdict
from pathlib import Path
from component_ledger import smaps,disk_file
R=Path('/var/tmp/vkso-section65-optimization-20261030-hBcg9Y')
H=Path(__file__).resolve().parent
O=R/'budget-closeout-01'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
    assert read(O/'stopped.json')['background_tasks_alive'] is False
    queue=R/'confirmation-recovery-01/selected-queue.json'
    regpath=R/'confirmation-recovery-01/selected-registration.json'
    reg=read(regpath);jobs=read(queue)
    assert len(jobs)==30 and sha(queue)==reg['queue_sha256']
    for path,digest in reg['identities'].items():assert sha(Path(path))==digest,('identity changed',path)
    recovery=read(Path(reg['recovery_manifest']))
    assert sha(Path(reg['recovery_manifest']))==reg['recovery_manifest_sha256']
    original=read(Path(reg['original_registration']))
    assert sha(Path(reg['original_registration']))==reg['original_registration_sha256']==recovery['original_registration_sha256']
    oldjobs=read(Path(recovery['original_queue']))
    assert sha(Path(recovery['original_queue']))==original['queue_sha256']==recovery['original_queue_sha256']
    assert reg['identities']==original['identities'] and reg['selection']==original['selection']
    old=recovery['interrupted_campaign'];new=recovery['replacement_campaign']
    expected_jobs=copy.deepcopy(oldjobs);replacement=next(j for j in jobs if j['name']==new)
    changed=next(j for j in expected_jobs if j['name']==old)
    changed['name']=new;changed['result']=replacement['result']
    for flag in ['--campaign','--output']:changed['argv'][changed['argv'].index(flag)+1]=replacement['argv'][replacement['argv'].index(flag)+1]
    assert expected_jobs==jobs
    partial=Path(recovery['partial_samples']);assert sha(partial)==recovery['partial_samples_sha256']
    assert len(partial.read_text().splitlines())==recovery['partial_observations']==127
    for path,digest in recovery['untouched_evidence'].items():assert sha(Path(path))==digest
    cleanup=read(Path(reg['recovery_manifest']).parent/'recovery.json')
    assert cleanup['status']=='complete' and cleanup['restored'] and cleanup['modules_unloaded']
    assert len(cleanup['steps'])==5 and all(s['returncode']==0 for s in cleanup['steps'])
    chosen=[]
    for job in jobs:
        path=Path(job['result'])
        if path.exists() and read(path)['status']=='complete':chosen.append(job)
    assert chosen==jobs[:len(chosen)],'selection must be entire chronological completed prefix'
    assert len(chosen)==14
    save(O/'selected-core-queue.json',chosen)
    planned={x['name']:x for x in reg['expected_campaigns']}
    cells=defaultdict(list);inputs=[];boot=set();modules=[];native_modules=[]
    for j in chosen:
        run=Path(j['result']).parent;outer=read(run/'result.json')
        assert outer['status']=='complete' and outer['modules_unloaded']
        kind=j['kind'];data=run if kind.startswith('native') else run/'benchmark'
        state=read(data/'result.json');env=read(data/'environment.json')
        assert state['status']=='complete' and not state['pilot']
        boot.add(env['boot_id']);samples=data/'samples.jsonl'
        rows=[json.loads(l) for l in samples.read_text().splitlines()]
        spec=planned[j['name']]
        assert len(rows)==state['observations']==spec['observations']
        assert {r['variant'] for r in rows}==set(spec['variants'])
        assert {r['workload'] for r in rows}==set(spec['workloads'])
        assert {r['campaign'] for r in rows}=={j['name']}
        blocks={'native-final':8,'native-stream':8,'application-final':12,'heldout':8,'decoder-diagnostic':4,'sharing-singlecpu':12}[kind]
        assert {r['block'] for r in rows}==set(range(blocks))
        assert len({(r['block'],r['variant'],r['workload'],r.get('compressor'),r.get('phase'),r['repeat']) for r in rows})==len(rows)
        if kind.startswith('native'):
            assert len(state['order'])*2==len(rows)
            for group in env['binaries'].values():
                for binary in group.values():assert sha(Path(binary['path']))==binary['sha256']
            for workload in state.get('workloads',['archive','scan']):assert len({r['digest'] for r in rows if r['workload']==workload})<=1
            native_modules.append(dict(campaign=j['name'],residency=outer['module_residency']))
        else:
            assert outer['restored'] and state['repeats']==1
            for path,digest in env['binaries'].items():
                if '/carrier/' not in path:assert sha(Path(path))==digest,path
            shared=read(data/'vkso-pfns.json');copied=read(data/'copied-pfns.json')
            assert len(shared['pages'])==len(copied['pages'])==9
            assert all(x['shared'] for x in shared['pages']) and all(not x['shared'] for x in copied['pages'])
            assert [(x['offset'],x['mapped_page_sha256']) for x in shared['pages']]==[(x['offset'],x['mapped_page_sha256']) for x in copied['pages']]
            assert shared['private_xz_bindings']['user_pfn']!=shared['private_xz_bindings']['kernel_pfn']
            modules.append(dict(campaign=j['name'],residency=read(run/'resident-modules.json')))
        for r in rows:
            assert r['wall_seconds']>0
            cells[kind,r.get('compressor',Path(state.get('image','unknown')).stem),r['workload'],r.get('phase','full-application')].append(r)
        inputs.append(dict(name=j['name'],kind=kind,samples=len(rows),samples_path=str(samples),sha256=sha(samples),blocks=blocks))
    assert len(boot)==1 and recovery['boot_id'] in boot
    assert sum(i['samples'] for i in inputs)==4580
    results=[]
    for key,rows in sorted(cells.items()):
        kind,codec,workload,phase=key;variants={r['variant'] for r in rows}
        if kind.startswith('native'):
            pairs=[('original',v) for v in variants if v!='original']+[('prepared-xz','prepared-optimized'),('native-word-normal','prepared-optimized'),('native-word-relaxed','prepared-optimized'),('native-small-normal','native-word-normal'),('native-small-relaxed','native-word-relaxed')]
        else:pairs=[('stock',v) for v in variants if v!='stock']+[('copied','vkso'),('stock-single','vkso'),('lkl-cache-512','vkso'),('copied-library','copied-retained'),('copied-retained','copied'),('copied-library','copied')]
        for baseline,treatment in sorted(set(pairs)):
            if not {baseline,treatment}<=variants:continue
            groups=defaultdict(dict)
            for r in rows:
                if r['variant'] in [baseline,treatment]:
                    cell=groups[r['campaign'],r['block']];assert r['variant'] not in cell
                    cell[r['variant']]=r['wall_seconds']
            bycampaign=defaultdict(list)
            for (campaign,block),v in groups.items():
                assert set(v)=={baseline,treatment};bycampaign[campaign].append((v[treatment],v[baseline]))
            campaign_values={c:dict(pairs=len(v),time_ratio=math.exp(statistics.mean(math.log(t/b) for t,b in v)),paired_difference_seconds=statistics.mean(t-b for t,b in v),baseline_median_seconds=statistics.median(b for t,b in v),treatment_median_seconds=statistics.median(t for t,b in v)) for c,v in bycampaign.items()}
            ratio=math.exp(statistics.mean(math.log(v['time_ratio']) for v in campaign_values.values()))
            difference=statistics.mean(v['paired_difference_seconds'] for v in campaign_values.values())
            # Independent second traversal: match raw variant lists by block.
            replay=[];deltas=[]
            for c in sorted(bycampaign):
                b={r['block']:r['wall_seconds'] for r in rows if r['campaign']==c and r['variant']==baseline}
                t={r['block']:r['wall_seconds'] for r in rows if r['campaign']==c and r['variant']==treatment}
                assert set(b)==set(t)
                replay.append(sum(math.log(t[k])-math.log(b[k]) for k in b)/len(b))
                deltas.append(sum(t[k]-b[k] for k in b)/len(b))
            assert math.isclose(ratio,math.exp(sum(replay)/len(replay)),rel_tol=1e-10)
            assert math.isclose(difference,sum(deltas)/len(deltas),rel_tol=1e-10,abs_tol=1e-12)
            results.append(dict(kind=kind,codec=codec,workload=workload,phase=phase,baseline=baseline,treatment=treatment,pairs=len(groups),campaigns=len(bycampaign),time_ratio=ratio,paired_difference_seconds=difference,campaign_values=campaign_values,ci95=None))
    counts={}
    for i in inputs:
        v=counts.setdefault(i['kind'],dict(campaigns=0,observations=0));v['campaigns']+=1;v['observations']+=i['samples']
    analysis=dict(status='complete',created=time.time(),scope='Quota-limited chronological 14/30 campaign closeout. 4580 complete observations, no within-campaign exclusions. One or two campaigns per cell: descriptive paired geometric time ratios only, no confirmatory CI or three-campaign claim. No historical samples pooled.',coverage=counts,inputs=inputs,observations=4580,comparisons=len(results),results=results,boot_ids=sorted(boot),planned_campaigns=30,planned_observations=7692,unstarted_campaigns=[j['name'] for j in jobs[14:]],retained_excluded_incomplete_observations=127,interruption_manifest=str(reg['recovery_manifest']),registration_sha256=sha(regpath))
    save(O/'analysis.json',analysis)
    save(O/'audit.json',dict(status='complete',observations=4580,campaigns=14,raw_cell_counts_valid=True,complete_blocks=True,frozen_identities_verified=len(reg['identities']),pfn_and_mapped_bytes=True,cleanup=True,independent_numeric_replay=True,comparisons=len(results),analysis_sha256=sha(O/'analysis.json'),scope='Independent numeric reconstruction in the closeout script; not independent hardware replication. No inference-grade CI with the truncated campaign count.'))
    scales=[];mappings=[]
    for scale in [1,4,16]:
        run=R/f'resource-scale-{scale:02d}-01';assert read(run/'result.json')['status']=='complete'
        data=run/'benchmark';resources=read(data/'resources.json')
        for variant,v in resources.items():
            m=v['after']['helper']['memory'];assert v['entries']==scale*5866+1
            scales.append(dict(scale=scale,variant=variant,entries=v['entries'],pss_kib=m['Pss'],rss_kib=m['Rss'],private_kib=m['Private_Clean']+m['Private_Dirty'],source=str(data/'resources.json'),source_sha256=sha(data/'resources.json')))
        mapped=smaps(data/'vkso-helper-smaps-after.txt');mapped['scale']=scale;mappings.append(mapped)
    run=R/'squash-optimized-application-final-gzip-01';build=R/'builds/optimization-cache-01'
    paths={'owner':build/'vkso_sq_core.ko','consumer':build/'vkso_squashfs.ko','bridge':build/'libsq-bridge.so','frontend':build/'vkso-squashfuse','translator':build/'vkso-squash-helper','carrier':run/'carrier/libvkso_sq_core.so','copied':run/'libsq-materialized.so'}
    files={key:disk_file(path,key) for key,path in paths.items()}
    def total(keys):
        unique={(files[k]['device'],files[k]['inode']):files[k] for k in keys}
        return dict(roles=keys,logical_bytes=sum(v['logical_bytes'] for v in unique.values()),allocated_bytes=sum(v['allocated_bytes'] for v in unique.values()))
    common=['bridge','frontend','translator']
    scenarios={name:total(keys+common) for name,keys in [('prepared-native-shared',['owner','consumer','carrier']),('prepared-native-copied',['owner','consumer','copied']),('user-only-shared',['owner','carrier']),('user-only-copied',['copied'])]}
    ledger=dict(status='complete',scale_snapshots=scales,vkso_mappings=mappings,disk_files=files,disk_scenarios=scenarios,module_residency=modules,native_module_residency=native_modules,shared_code_ro_pages=9,shared_code_ro_bytes=36864,registration_requested_bytes=1264,boundaries=['Scale measurements are existing untimed helper snapshots, not replicated peaks or whole-machine memory.','Mapping buckets do not identify anonymous-allocation ownership; live allocation diagnosis was cancelled.','Owner/consumer/platform residency, process PSS and shared backing must not be naively added.','Disk scenarios use evaluated unstripped files and inode-deduplicated st_blocks; common installed platform/dependencies/images excluded equally, not proved removable or reduced.','Sparse carrier saves 36KiB versus materialized copied core for an already-prepared native deployment; user-only owner cost can outweigh that saving.','Original host native code remains; no measured host-kernel replacement or whole-machine net saving.'])
    save(O/'resource-ledger.json',ledger)
    print(json.dumps(dict(status='complete',campaigns=14,observations=4580,comparisons=len(results),coverage=counts,disk_scenarios=scenarios),indent=2))
if __name__=='__main__':main()
