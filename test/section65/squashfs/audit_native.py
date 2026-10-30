#!/usr/bin/env python3
"""Validate actual sampling keys, pairing, image labels and output consistency."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import random
from native_cost import summarize


def audit(path):
    result = json.loads((path/'result.json').read_text())
    env=json.loads((path/'environment.json').read_text())
    if 'runner_sha256' in env:
        assert hashlib.sha256((path/'runner.py').read_bytes()).hexdigest()==env['runner_sha256']
        runner_identity='Per-run source copy matches contemporaneous environment hash.'
    else:
        assert path.name in ['squash-native-five-pilot-01','squash-native-five-formal-01']
        runner_identity='No per-run runner hash was recorded. evaluation-fixed-01 retains the contemporaneous runner; later versions add optional workloads and provenance fields while preserving these default commands. This is source-history evidence, not a retroactive per-run hash.'
    rows = [json.loads(line) for line in (path/'samples.jsonl').read_text().splitlines()]
    assert result['status'] == 'complete' and result['modules_unloaded']
    cases = {c['compressor'] for c in result['cases']}
    workloads=result.get('workloads',['archive','scan'])
    expected = result['blocks']*len(cases)*2*len(workloads)*(result['warm_repeats']+1)
    assert len(rows) == expected == result['observations']
    assert [r['sequence'] for r in rows] == list(range(expected))
    groups = collections.defaultdict(list)
    for row in rows:
        assert row['campaign'] == result['campaign']
        assert row['compressor'] in cases and 0 <= row['block'] < result['blocks']
        assert row['workload'] in workloads
        assert row['wall_seconds']>0 and row.get('cpu_seconds',0)>=0
        assert 0 <= row['repeat'] <= result['warm_repeats']
        assert row['phase'] == ('fresh-mount' if row['repeat']==0 else 'warm')
        groups[row['compressor'],row['block'],row['workload'],row['repeat']].append(row)
    assert len(groups) == expected//2
    assert all(len(v)==2 and {r['variant'] for r in v}=={'original','prepared'} for v in groups.values())
    rng=random.Random(result['seed']);order=[]
    for block in range(result['blocks']):
        ordered=[c['compressor'] for c in result['cases']];rng.shuffle(ordered)
        for codec in ordered:
            tasks=list(workloads);rng.shuffle(tasks)
            for task in tasks:
                variants=['original','prepared'];rng.shuffle(variants)
                order.extend((block,codec,task,variant,repeat) for variant in variants
                             for repeat in range(result['warm_repeats']+1))
    assert [(r['block'],r['compressor'],r['workload'],r['variant'],r['repeat']) for r in rows]==order
    for workload in workloads:
        assert len({r['digest'] for r in rows if r['workload']==workload}) == 1
    summary = [dict(compressor=c['compressor'], **s) for c in result['cases']
               for s in summarize([r for r in rows if r['compressor']==c['compressor']])]
    assert summary == result['summary']
    return dict(path=str(path),status='pass',observations=expected,complete_pairs=len(groups),
                pilot=result['pilot'],campaign=result['campaign'],seed=result['seed'],seeded_order_verified=True,
                runner_identity=runner_identity,summary=summary)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--output',required=True,type=Path)
    args = p.parse_args()
    output = dict(status='pass',runs=[audit(path.resolve()) for path in args.runs])
    args.output.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(status='pass',campaigns=len(output['runs']))))
