#!/usr/bin/env python3
"""Replay the complete improvement matrix with campaign/block paired intervals."""
import argparse, collections, csv, hashlib, json, math
from pathlib import Path
import statistics
import numpy as np
ROOT=Path(__file__).resolve().parents[4]

def hierarchical_interval(groups,seed=650064):
    """Equal campaign weight; resample campaigns then their paired blocks."""
    rng=np.random.default_rng(seed);names=sorted(groups);n=len(names);assert n>=3
    arrays=[np.array(groups[k],dtype=float) for k in names]
    chosen=rng.integers(0,n,size=(10000,n));boot=np.zeros((10000,n))
    for slot in range(n):
        for i,values in enumerate(arrays):
            mask=chosen[:,slot]==i;count=mask.sum()
            boot[mask,slot]=values[rng.integers(0,len(values),size=(count,len(values)))].mean(axis=1)
    return float(np.mean([a.mean() for a in arrays])),np.quantile(boot.mean(axis=1),[.025,.975]).tolist()

def intervals(groups):
    values=[statistics.mean(groups[k]) for k in sorted(groups)]
    assert len(values)==3,'The preregistered matrix has three independent campaigns per cell.'
    mean=statistics.mean(values);half=4.302652730*statistics.stdev(values)/math.sqrt(3)
    return mean,[mean-half,mean+half]

def compare(rows,baseline,treatment,cell):
    groups=collections.defaultdict(dict)
    for r in rows:
        if r['variant'] in [baseline,treatment]:groups[r['campaign'],r['block'],r.get('repeat',0)][r['variant']]=r
    assert groups and all(set(g)=={baseline,treatment} for g in groups.values()),(cell,baseline,treatment)
    logs=collections.defaultdict(list);delta=collections.defaultdict(list);cpu=collections.defaultdict(list)
    for (campaign,block,repeat),g in sorted(groups.items()):
        b,t=g[baseline],g[treatment];logs[campaign].append(math.log(t['wall_seconds']/b['wall_seconds']))
        delta[campaign].append(t['wall_seconds']-b['wall_seconds'])
        def c(r):return r.get('cpu_seconds',r.get('user_cpu_seconds',0)+r.get('system_cpu_seconds',0))
        if c(b)>0 and c(t)>0:cpu[campaign].append(math.log(c(t)/c(b)))
    point,ci=intervals(logs);d,dc=intervals(delta)
    _,bootstrap=hierarchical_interval(logs)
    result=dict(**cell,baseline=baseline,treatment=treatment,campaigns=len(logs),pairs=len(groups),
        time_ratio=math.exp(point),ratio_ci95=list(map(math.exp,ci)),paired_difference_seconds=d,difference_ci95_seconds=dc,
        hierarchical_bootstrap_ratio_ci95=list(map(math.exp,bootstrap)),
        absolute_median_seconds={v:statistics.median(r['wall_seconds'] for r in rows if r['variant']==v) for v in [baseline,treatment]},
        campaign_ratios={k:math.exp(statistics.mean(v)) for k,v in logs.items()},blocks_per_campaign={k:len(v) for k,v in logs.items()})
    if len(cpu)==len(logs):
        p,c=intervals(cpu);result.update(cpu_ratio=math.exp(p),cpu_ratio_ci95=list(map(math.exp,c)))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--queue',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--loader-control',action='store_true');a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    jobs=json.loads(a.queue.read_text());groups=collections.defaultdict(list);inputs=[];identities={};resources=[]
    for job in jobs:
        run=Path(job['result']).resolve().parent;state=json.loads((run/'result.json').read_text());assert state['status']=='complete',job['name']
        if 'native-call-counts' in job['name']:continue
        kind='application' if 'application-improved' in job['name'] else 'native-control' if 'bounded-control' in job['name'] else 'native-stream' if 'improved-stream' in job['name'] else 'native';data=run/'benchmark' if kind=='application' else run
        summary=json.loads((data/'result.json').read_text());assert not summary['pilot']
        rows=[json.loads(l) for l in (data/'samples.jsonl').read_text().splitlines()]
        assert len({(r['campaign'],r['block'],r['variant'],r['workload'],r.get('phase'),r.get('compressor'),r['repeat']) for r in rows})==len(rows)
        inputs.append(dict(run=str(run),samples=len(rows),sha256=hashlib.sha256((data/'samples.jsonl').read_bytes()).hexdigest()))
        if kind=='application':inputs[-1]['cpus']=summary['cpus']
        env=json.loads((data/'environment.json').read_text())
        if kind.startswith('native'):
            ident={v:{n:r['sha256'] for n,r in files.items()} for v,files in env['binaries'].items()}
            key=kind
        else:
            ident={k:v for k,v in env['binaries'].items() if k.endswith(('vkso_sq_core.ko','vkso_squashfs.ko','vkso-squashfuse','libsq-bridge.so','lklfuse','lklfuse-cache'))}
            # Subsets vary by codec; compare the same configured codec across campaigns.
            key=Path(summary['image']).stem
            for variant,r in json.loads((data/'resources.json').read_text()).items():
                resources.append(dict(campaign=summary['campaign'],codec=key,variant=variant,data=r))
        assert identities.setdefault(key,ident)==ident,('binary identity mismatch',key)
        for r in rows:
            codec=r.get('compressor',Path(summary.get('image','unknown')).stem)
            groups[kind,codec,r['workload'],r.get('phase','full-application')].append(r)
    results=[];absolute=[];padding_results=[]
    for (kind,codec,work,phase),rows in sorted(groups.items()):
        variants={r['variant'] for r in rows}
        for variant in sorted(variants):
            medians={campaign:[statistics.median(r['wall_seconds'] for r in rows if r['variant']==variant and r['campaign']==campaign)] for campaign in sorted({r['campaign'] for r in rows})}
            value,ci=intervals(medians)
            absolute.append(dict(kind=kind,codec=codec,workload=work,phase=phase,variant=variant,mean_campaign_median_seconds=value,ci95_seconds=ci,campaign_medians={k:v[0] for k,v in medians.items()}))
        if kind.startswith('native'):
            pairs=[('original',v) for v in variants if v!='original']
            candidates=[('prepared-before','prepared-small-copy'),('prepared-before','prepared-composed'),('prepared-small-copy','prepared-composed'),
                        ('native-normal','native-small-normal'),('native-small-normal','prepared-small-copy'),('native-small-relaxed','prepared-small-copy')]
            pairs += [(b,t) for b,t in candidates if {b,t}<=variants]
        else:
            pairs=[('stock',v) for v in variants if v!='stock']+[('copied','vkso'),('lkl-512','vkso'),('lkl-cache-512','vkso'),('lkl-512','lkl-cache-512')]
            pairs += [('copied-old',v) for v in variants if v.startswith('copied') and v!='copied-old']
            if 'copied-library' in variants:pairs.append(('copied-library','copied'))
        for b,t in sorted(set(pairs)):
            if {b,t}<=variants:
                results.append(compare(rows,b,t,dict(kind=kind,codec=codec,workload=work,phase=phase)))
                if a.loader_control:
                    assert kind=='application' and {r['loader_padding'] for r in rows}=={0,16}
                    for padding in [0,16]:
                        padding_results.append(compare([r for r in rows if r['loader_padding']==padding],b,t,
                            dict(kind=kind,codec=codec,workload=work,phase=phase,loader_padding=padding)))
    result=dict(status='complete',scope='Frozen complete matrix; equal campaign weights, paired blocks. Primary pointwise 95% Student-t intervals use three independent campaign means (log ratios for relative time). 10,000 campaign/block hierarchical bootstrap draws are a secondary sensitivity check; no multiplicity-adjusted discovery claims.',
        inputs=inputs,observations=sum(r['samples'] for r in inputs),identities=identities,results=results,absolute=absolute,resources=resources)
    if a.loader_control:result['loader_padding_results']=padding_results
    (out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'summary.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['kind','codec','workload','phase','baseline','treatment','campaigns','pairs','baseline_seconds','treatment_seconds','paired_ratio','ci95_low','ci95_high','paired_delta_seconds','delta_ci95_low','delta_ci95_high'])
        for r in results:w.writerow([r[k] for k in ['kind','codec','workload','phase','baseline','treatment','campaigns','pairs']]+[r['absolute_median_seconds'][r[v]] for v in ['baseline','treatment']]+[r['time_ratio'],*r['ratio_ci95'],r['paired_difference_seconds'],*r['difference_ci95_seconds']])
    print(json.dumps(dict(status='complete',observations=result['observations'],comparisons=len(results))))
if __name__=='__main__':main()
