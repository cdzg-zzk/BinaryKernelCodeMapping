#!/usr/bin/env python3
"""Retain all completed pilot cells; never turn pilot ratios into formal CIs."""
import argparse,json,math,statistics,hashlib
from collections import defaultdict
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--queue',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    jobs=json.loads(a.queue.read_text());result=dict(status='complete',scope='Descriptive full pilot groups; no formal confidence interval or significance claim.',inputs=[],comparisons=[])
    for job in jobs:
        run=Path(job['result']).parent;outer=json.loads((run/'result.json').read_text());assert outer['status']=='complete'
        bench=run/'benchmark';state=json.loads((bench/'result.json').read_text());assert state['pilot']
        path=bench/'samples.jsonl';rows=[json.loads(l) for l in path.read_text().splitlines()]
        assert len(rows)==state['observations']
        result['inputs'].append(dict(campaign=job['name'],samples=len(rows),source=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        for work in sorted({r['workload'] for r in rows}):
            cells=defaultdict(dict)
            for r in rows:
                if r['workload']==work:
                    assert r['variant'] not in cells[r['block']];cells[r['block']][r['variant']]=r
            assert len(cells)==state['blocks']
            pairs=[('copied-small',v) for v in ['copied','vkso','copied-data48']]
            pairs += [(b,'vkso') for b in ['stock','stock-single','copied','lkl-cache-512']]
            for b,t in pairs:
                if not all(b in c and t in c for c in cells.values()):continue
                logs=[math.log(c[t]['wall_seconds']/c[b]['wall_seconds']) for c in cells.values()]
                result['comparisons'].append(dict(campaign=job['name'],workload=work,baseline=b,treatment=t,blocks=len(logs),
                    time_ratio=math.exp(statistics.mean(logs)),block_ratios=[math.exp(x) for x in logs],
                    baseline_seconds=statistics.median(c[b]['wall_seconds'] for c in cells.values()),
                    treatment_seconds=statistics.median(c[t]['wall_seconds'] for c in cells.values()),
                    cpu_ratio=math.exp(statistics.mean(math.log((c[t]['user_cpu_seconds']+c[t]['system_cpu_seconds'])/(c[b]['user_cpu_seconds']+c[b]['system_cpu_seconds'])) for c in cells.values()))))
    result['observations']=sum(x['samples'] for x in result['inputs'])
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('summarized',len(jobs),'complete pilots',result['observations'],'observations')

if __name__=='__main__':main()
