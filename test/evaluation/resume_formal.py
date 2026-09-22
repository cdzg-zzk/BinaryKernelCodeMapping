#!/usr/bin/env python3
"""Continue incomplete full deployments in a fresh archive, preserving prior results."""
import argparse
import json
from pathlib import Path
from algorithm_deployments import execute, make_plan, read_observations


def resume(source, output, run=False):
    source, output = Path(source).resolve(), Path(output).resolve()
    assert not output.exists(), 'continuation requires a fresh output directory'
    old = json.loads((source/'plan.json').read_text())
    algorithms = [e['algorithm'] for e in old['entries'][:len({e['algorithm'] for e in old['entries']})]]
    plan = make_plan(algorithms, old['deployments_per_algorithm'], output, old['cpu'], old['kernel'],
                     old['with_lz4_workflow'], old['with_kernel_cost'], old['with_lz4_setup'])
    completed = []
    for entry in old['entries']:
        directory = Path(entry['directory'])
        if (directory/'complete.json').exists():
            record = json.loads((directory/'complete.json').read_text())
            rows = read_observations(entry['algorithm'],directory/'results/raw.csv',entry['deployment'])
            assert record['owner_unloaded'] and len(rows)==record['observations']
            completed.append(entry['deployment'])
    plan['entries'] = [e for e in plan['entries'] if e['deployment'] not in completed]
    assert plan['entries'], 'no incomplete deployment remains'
    plan['continuation'] = dict(source=str(source),completed_deployments=completed,
        policy='retain completed deployments; repeat interrupted deployment in full in a fresh directory; no partial observations pooled')
    if run: execute(plan, output)
    else: print(json.dumps(plan,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--execute',dest='run',action='store_true')
    resume(**vars(p.parse_args()))
