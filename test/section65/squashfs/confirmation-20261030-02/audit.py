#!/usr/bin/env python3
"""Independently replay raw pairing, campaign estimates, intervals and identities."""
import argparse
import copy
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

def read(p):return json.loads(p.read_text())
def close(a,b):assert math.isclose(a,b,rel_tol=2e-9,abs_tol=1e-11),(a,b)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue',type=Path,required=True)
    p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--registration',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    analyzed=read(a.analysis);cells=defaultdict(list);count=0;boot=set();checks=[]
    jobs=read(a.queue);assert len(jobs)==30
    registration=read(a.registration)
    assert hashlib.sha256(a.queue.read_bytes()).hexdigest()==registration['queue_sha256']
    expected={r['name']:r for r in registration['expected_campaigns']}
    assert set(expected)=={j['name'] for j in jobs}
    for path,digest in registration['identities'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,('changed frozen identity',path)
    for job in jobs:
        run=Path(job['result']).resolve().parent;outer=read(run/'result.json')
        assert outer['status']=='complete' and outer['modules_unloaded']
        kind=job['kind'];data=run if kind.startswith('native') else run/'benchmark'
        state=read(data/'result.json');assert not state['pilot']
        env=read(data/'environment.json');boot.add(env['boot_id'])
        rows=[json.loads(l) for l in (data/'samples.jsonl').read_text().splitlines()]
        count+=len(rows);assert len(rows)==state['observations']
        planned=expected[job['name']]
        assert len(rows)==planned['observations']
        assert {r['variant'] for r in rows}==set(planned['variants'])
        assert {r['workload'] for r in rows}==set(planned['workloads'])
        provenance=[r for r in analyzed['inputs'] if r['run']==str(run)];assert len(provenance)==1
        assert provenance[0]['sha256']==hashlib.sha256((data/'samples.jsonl').read_bytes()).hexdigest()
        expected_blocks={'native-final':8,'native-stream':8,'application-final':12,'heldout':8,'decoder-diagnostic':4,'sharing-singlecpu':12}[kind]
        assert {r['block'] for r in rows}==set(range(expected_blocks))
        if kind.startswith('native'):
            assert len(state['order'])*2==len(rows)
            for binary_group in env['binaries'].values():
                for binary in binary_group.values():assert hashlib.sha256(Path(binary['path']).read_bytes()).hexdigest()==binary['sha256']
            for workload in state.get('workloads',['archive','scan']):
                assert len({r['digest'] for r in rows if r['workload']==workload})<=1
        else:
            assert outer['restored'] and state['repeats']==1
            for path,digest in env['binaries'].items():
                # Carrier restoration changes placeholder file bytes, while
                # separate mapped-page evidence retains executed-byte identity.
                if '/carrier/' not in path:assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
            shared=read(data/'vkso-pfns.json');copied=read(data/'copied-pfns.json')
            assert len(shared['pages'])==len(copied['pages'])==9
            assert all(x['shared'] for x in shared['pages']) and all(not x['shared'] for x in copied['pages'])
            assert [(x['offset'],x['mapped_page_sha256']) for x in shared['pages']]==[(x['offset'],x['mapped_page_sha256']) for x in copied['pages']]
            assert shared['private_xz_bindings']['user_pfn']!=shared['private_xz_bindings']['kernel_pfn']
        for r in rows:cells[kind,r.get('compressor',Path(state.get('image','unknown')).stem),r['workload'],r.get('phase','full-application')].append(r)
        checks.append(dict(campaign=state['campaign'],samples=len(rows),complete=True))
    assert count==analyzed['observations']==registration['expected_observations']==8172
    assert len(boot)==1, 'cross-boot data requires separate analysis and disclosure'
    for result in analyzed['results']:
        rows=cells[tuple(result[k] for k in ['kind','codec','workload','phase'])]
        pairs=defaultdict(dict)
        for r in rows:
            if r['variant'] in [result['baseline'],result['treatment']]:
                key=(r['campaign'],r['block']);assert r['variant'] not in pairs[key]
                pairs[key][r['variant']]=r['wall_seconds']
        ratios=defaultdict(list);diffs=defaultdict(list)
        for (campaign,block),values in pairs.items():
            b=values[result['baseline']];t=values[result['treatment']]
            ratios[campaign].append(math.log(t/b));diffs[campaign].append(t-b)
        assert len(ratios)==3 and len(pairs)==result['pairs']
        for values,point,ci,exponent in [(ratios,result['time_ratio'],result['ratio_ci95'],True),
            (diffs,result['paired_difference_seconds'],result['difference_ci95_seconds'],False)]:
            means=[statistics.mean(v) for v in values.values()]
            center=statistics.mean(means);half=4.302652730*statistics.stdev(means)/math.sqrt(3)
            transform=math.exp if exponent else lambda x:x
            close(point,transform(center));close(ci[0],transform(center-half));close(ci[1],transform(center+half))
    for row in analyzed['absolute']:
        rows=cells[tuple(row[k] for k in ['kind','codec','workload','phase'])]
        campaigns={r['campaign'] for r in rows}
        medians=[statistics.median(r['wall_seconds'] for r in rows if r['campaign']==c and r['variant']==row['variant']) for c in campaigns]
        close(statistics.mean(medians),row['mean_campaign_median_seconds'])
    for saved in registration['reused_native']:
        run=Path(saved['result']).parent
        assert hashlib.sha256((run/'samples.jsonl').read_bytes()).hexdigest()==saved['samples_sha256']
        assert hashlib.sha256((run/'result.json').read_bytes()).hexdigest()==saved['result_sha256']
        assert next(j for j in jobs if j['name']==saved['name'])['kind'].startswith('native')
    assert len(registration['reused_native'])==4
    assert registration['reused_native_observations']==2688
    for path,digest in registration['validation'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
        assert read(Path(path))['status']=='complete'
    interruptions=[]
    if 'data48_recovery' in registration:
        path=Path(registration['data48_recovery']);recovery=read(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==registration['data48_recovery_sha256']
        old_queue=Path(recovery['original_queue']);old_reg=Path(recovery['original_registration'])
        assert hashlib.sha256(old_queue.read_bytes()).hexdigest()==recovery['original_queue_sha256']
        assert hashlib.sha256(old_reg.read_bytes()).hexdigest()==recovery['original_registration_sha256']
        original=read(old_reg);expected_jobs=copy.deepcopy(read(old_queue))
        old,new=recovery['old_campaign'],recovery['new_campaign']
        target=next(j for j in expected_jobs if j['name']==old)
        replacement=next(j for j in jobs if j['name']==new)
        target['name']=new;target['result']=replacement['result']
        for flag in ['--campaign','--output']:
            target['argv'][target['argv'].index(flag)+1]=replacement['argv'][replacement['argv'].index(flag)+1]
        assert expected_jobs==jobs, 'recovery changed experimental conditions'
        cells_expected=copy.deepcopy(original['expected_campaigns'])
        next(c for c in cells_expected if c['name']==old)['name']=new
        assert cells_expected==registration['expected_campaigns']
        assert original['identities']==registration['identities']
        partial=Path(recovery['partial_samples'])
        assert hashlib.sha256(partial.read_bytes()).hexdigest()==recovery['partial_sha256']
        assert len(partial.read_text().splitlines())==recovery['partial_observations']==790
        assert old not in {j['name'] for j in jobs}
        cleanup=Path(recovery['cleanup']);assert hashlib.sha256(cleanup.read_bytes()).hexdigest()==recovery['cleanup_sha256']
        assert read(cleanup)['task_modules_unloaded']
        interruptions.append(recovery)
    if 'recovery_manifest' in registration:
        recovery=Path(registration['recovery_manifest']);interrupted=read(recovery)
        assert hashlib.sha256(recovery.read_bytes()).hexdigest()==registration['recovery_manifest_sha256']
        original_path=Path(registration['original_registration']);original=read(original_path)
        assert hashlib.sha256(original_path.read_bytes()).hexdigest()==registration['original_registration_sha256']==interrupted['original_registration_sha256']
        original_queue=Path(interrupted['original_queue']);old_jobs=read(original_queue)
        assert hashlib.sha256(original_queue.read_bytes()).hexdigest()==original['queue_sha256']==interrupted['original_queue_sha256']
        assert original['identities']==registration['identities'] and original['selection']==registration['selection']
        assert original['expected_observations']==registration['expected_observations']
        expected_jobs=copy.deepcopy(old_jobs);expected_cells=copy.deepcopy(original['expected_campaigns'])
        old=interrupted['interrupted_campaign'];new=interrupted['replacement_campaign']
        assert old not in {j['name'] for j in jobs} and new in {r['campaign'] for r in checks}
        changed=[j for j in expected_jobs if j['name']==old];assert len(changed)==1
        replacement=next(j for j in jobs if j['name']==new);changed[0]['name']=new
        changed[0]['result']=replacement['result']
        for flag in ['--campaign','--output']:
            changed[0]['argv'][changed[0]['argv'].index(flag)+1]=replacement['argv'][replacement['argv'].index(flag)+1]
        assert jobs==expected_jobs, 'recovery changed settings or other campaign identities'
        for row in expected_cells:
            if row['name']==old:row['name']=new
        assert expected_cells==registration['expected_campaigns']
        partial=Path(interrupted['partial_samples'])
        assert hashlib.sha256(partial.read_bytes()).hexdigest()==interrupted['partial_samples_sha256']
        assert len(partial.read_text().splitlines())==interrupted['partial_observations']==127
        for path,digest in interrupted['untouched_evidence'].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
        assert interrupted['boot_id'] in boot
        cleanup=read(recovery.parent/'recovery.json')
        assert cleanup['status']=='complete' and cleanup['restored'] and cleanup['modules_unloaded']
        assert len(cleanup['steps'])==5 and all(s['returncode']==0 for s in cleanup['steps'])
        interruptions.append(interrupted)
    a.output.write_text(json.dumps(dict(status='complete',campaigns=checks,observations=count,
        analysis_sha256=hashlib.sha256(a.analysis.read_bytes()).hexdigest(),
        registration_sha256=hashlib.sha256(a.registration.read_bytes()).hexdigest(),
        comparisons=len(analyzed['results']),boot_ids=sorted(boot),excluded_observations=0,
        excluded_observations_scope='No observations excluded within completed campaigns; interrupted partial campaigns are separately retained below.',
        reused_native=registration['reused_native'],
        historical_closeout=registration['historical_closeout'],
        interrupted_campaigns=interruptions,
        interrupted_partial_observations=sum(x['partial_observations'] for x in interruptions),
        scope='Independent raw-data replay, not independent hardware replication; one host/boot scope retained.'),indent=2)+'\n')
    print('audited',count,'observations and',len(analyzed['results']),'comparisons')


if __name__=='__main__':main()
