#!/usr/bin/env python3
"""Independently replay raw pairing, campaign estimates, intervals and identities."""
import argparse
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
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    analyzed=read(a.analysis);cells=defaultdict(list);count=0;boot=set();checks=[]
    jobs=read(a.queue);assert len(jobs)==30
    for job in jobs:
        run=Path(job['result']).resolve().parent;outer=read(run/'result.json')
        assert outer['status']=='complete' and outer['modules_unloaded']
        kind=job['kind'];data=run if kind.startswith('native') else run/'benchmark'
        state=read(data/'result.json');assert not state['pilot']
        env=read(data/'environment.json');boot.add(env['boot_id'])
        rows=[json.loads(l) for l in (data/'samples.jsonl').read_text().splitlines()]
        count+=len(rows);assert len(rows)==state['observations']
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
    assert count==analyzed['observations']==6540
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
    interruptions=[]
    recovery=Path(__file__).resolve().parents[4]/'test/evaluation-local/runs/iso9660/squash-refine-interruption-recovery-01/interruption.json'
    if recovery.exists():
        interrupted=read(recovery)
        if interrupted['replacement_campaign'] in {r['campaign'] for r in checks}:
            partial=recovery.parent.parent/interrupted['interrupted_campaign']/'benchmark/samples.jsonl'
            assert hashlib.sha256(partial.read_bytes()).hexdigest()==interrupted['partial_samples_sha256']
            assert len(partial.read_text().splitlines())==interrupted['partial_observations']==28
            interruptions.append(interrupted)
    a.output.write_text(json.dumps(dict(status='complete',campaigns=checks,observations=count,
        analysis_sha256=hashlib.sha256(a.analysis.read_bytes()).hexdigest(),
        comparisons=len(analyzed['results']),boot_ids=sorted(boot),excluded_observations=0,
        excluded_observations_scope='No observations excluded within completed campaigns; interrupted partial campaigns are separately retained below.',
        interrupted_campaigns=interruptions,
        scope='Independent raw-data replay, not independent hardware replication; one host/boot scope retained.'),indent=2)+'\n')
    print('audited',count,'observations and',len(analyzed['results']),'comparisons')


if __name__=='__main__':main()
