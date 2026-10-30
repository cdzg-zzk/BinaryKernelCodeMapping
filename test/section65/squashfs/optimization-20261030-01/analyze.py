#!/usr/bin/env python3
"""Analyze explicitly typed refinement campaigns without pooling old versions."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'improvement'))
from analyze import compare, intervals


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cells=defaultdict(list);inputs=[];identities={};resources=[]
    for job in json.loads(a.queue.read_text()):
        kind=job['kind'];run=Path(job['result']).resolve().parent
        outer=json.loads((run/'result.json').read_text());assert outer['status']=='complete'
        data=run if kind.startswith('native') else run/'benchmark'
        state=json.loads((data/'result.json').read_text());assert state['status']=='complete' and not state['pilot']
        samples=data/'samples.jsonl';rows=[json.loads(l) for l in samples.read_text().splitlines()]
        assert len(rows)==state['observations'] and len({r['campaign'] for r in rows})==1
        assert len({(r['block'],r['variant'],r['workload'],r.get('compressor'),r.get('phase'),r['repeat']) for r in rows})==len(rows)
        env=json.loads((data/'environment.json').read_text())
        codec=Path(state.get('image','unknown')).stem
        key=(kind,codec)
        if kind.startswith('native'):
            identity={v:{n:r['sha256'] for n,r in files.items()} for v,files in env['binaries'].items()}
        else:
            # Registered/materialized carrier paths vary, but their execution
            # identity is checked by each run's mapped-page/PFN evidence.
            identity={k:v for k,v in env['binaries'].items() if k.endswith(('.ko','libsq-bridge.so','vkso-squashfuse','vkso-squash-helper','lklfuse','lklfuse-cache','squashfuse_ll'))}
            for variant,value in json.loads((data/'resources.json').read_text()).items():
                resources.append(dict(kind=kind,codec=codec,campaign=state['campaign'],variant=variant,data=value))
        assert identities.setdefault(key,identity)==identity,('changed binary',key)
        inputs.append(dict(kind=kind,run=str(run),samples=len(rows),sha256=hashlib.sha256(samples.read_bytes()).hexdigest(),campaign=state['campaign']))
        for r in rows:cells[kind,r.get('compressor',codec),r['workload'],r.get('phase','full-application')].append(r)
    results=[];absolute=[]
    for (kind,codec,workload,phase),rows in sorted(cells.items()):
        variants={r['variant'] for r in rows}
        campaigns={r['campaign'] for r in rows};assert len(campaigns)==3
        for variant in sorted(variants):
            medians={c:[statistics.median(r['wall_seconds'] for r in rows if r['campaign']==c and r['variant']==variant)] for c in sorted(campaigns)}
            value,ci=intervals(medians)
            absolute.append(dict(kind=kind,codec=codec,workload=workload,phase=phase,variant=variant,
                mean_campaign_median_seconds=value,ci95_seconds=ci,campaign_medians={k:v[0] for k,v in medians.items()}))
        if kind.startswith('native'):
            pairs=[('original',v) for v in variants if v!='original']
            pairs += [('native-small-normal','prepared-xz'),('native-small-relaxed','prepared-xz'),('prepared-composed','prepared-xz'),
                      ('native-small-normal','prepared-composed'),('native-small-relaxed','prepared-composed'),
                      ('prepared-xz','prepared-optimized'),('native-word-normal','prepared-optimized'),
                      ('native-word-relaxed','prepared-optimized'),('native-small-normal','native-word-normal'),
                      ('native-small-relaxed','native-word-relaxed')]
        else:
            pairs=[('stock',v) for v in variants if v!='stock']
            pairs += [('copied','vkso'),('stock-single','vkso'),('lkl-512','vkso'),('lkl-cache-512','vkso'),
                      ('lkl-512','lkl-cache-512'),('copied-library','copied-retained'),('copied-retained','copied'),('copied-library','copied')]
        for b,t in sorted(set(pairs)):
            if {b,t}<=variants:
                # One observation per block/variant/cell in this matrix.
                assert all(sum(r['campaign']==c and r['block']==block and r['variant']==v for r in rows)==1
                    for c in campaigns for block in {r['block'] for r in rows if r['campaign']==c} for v in [b,t])
                results.append(compare(rows,b,t,dict(kind=kind,codec=codec,workload=workload,phase=phase)))
    result=dict(status='complete',scope='Frozen word-copy XZ and bounded-private-cache implementation; no historical observations pooled. Native optimized normal/relaxed references carry the identical edited XZ algorithm, while predecessor references remain explicitly labeled. Separate matrices, equal campaign weight, three campaign means per cell. Pointwise Student-t 95% CIs on campaign mean log paired ratios. Secondary bootstrap resamples campaigns and paired blocks. Absolute times are means of campaign medians, not operands of paired ratios.',
        inputs=inputs,observations=sum(r['samples'] for r in inputs),results=results,absolute=absolute,resources=resources,
        identities={kind+'/'+codec:value for (kind,codec),value in identities.items()})
    (out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'summary.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['kind','codec','workload','phase','baseline','treatment','ratio','ci_low','ci_high','delta_seconds','delta_ci_low','delta_ci_high'])
        for r in results:w.writerow([r[k] for k in ['kind','codec','workload','phase','baseline','treatment']]+[r['time_ratio'],*r['ratio_ci95'],r['paired_difference_seconds'],*r['difference_ci95_seconds']])
    print('analyzed',len(inputs),'campaigns',result['observations'],'observations')


if __name__=='__main__':main()
