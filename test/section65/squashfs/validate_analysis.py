#!/usr/bin/env python3
"""Independent numerical checks for campaign intervals and retained estimates."""
import argparse
import collections
import json
import math
from pathlib import Path
import statistics
from analyze_campaigns import T95


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--analysis',required=True,type=Path)
    p.add_argument('--previous',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    quantiles=[]
    for n,q in T95.items():
        df=n-1;count=10000;h=q/count
        factor=math.gamma((df+1)/2)/(math.sqrt(df*math.pi)*math.gamma(df/2))
        def pdf(x):return factor*(1+x*x/df)**(-(df+1)/2)
        area=(pdf(0)+pdf(q)+sum((4 if i%2 else 2)*pdf(i*h) for i in range(1,count)))*h/3
        assert abs(.5+area-.975)<1e-9,(n,area)
        quantiles.append(dict(campaigns=n,cdf=.5+area))
    data=json.loads(a.analysis.read_text())
    if a.previous:assert data['summaries']==json.loads(a.previous.read_text())['summaries']
    raw=collections.defaultdict(list)
    for identity in data['identities']:
        path=Path(identity['path']);state=json.loads((path/'result.json').read_text())
        for line in (path/'samples.jsonl').read_text().splitlines():
            row=json.loads(line)
            key=(identity['campaign'],row.get('compressor',Path(state.get('image','unknown')).stem),
                 row['workload'],row.get('phase','lifecycle'),row['variant'],row['block'])
            raw[key].append(row['wall_seconds'])
    paired=0
    for s in data['summaries']:
        logs=[];deltas=[]
        for c in s['campaigns']:
            ratios=[];differences=[]
            for b in c['blocks']:
                base=(c['campaign'],s['codec'],s['workload'],s['phase'])
                reference=statistics.median(raw[base+(s['baseline'],b['block'])])
                treatment=statistics.median(raw[base+(s['treatment'],b['block'])])
                assert reference==b['baseline_seconds'] and treatment==b['treatment_seconds']
                ratios.append(math.log(treatment/reference));differences.append(treatment-reference)
            logs.append(math.fsum(ratios)/len(ratios));deltas.append(math.fsum(differences)/len(differences))
        n=len(logs);center=math.fsum(logs)/n;delta=math.fsum(deltas)/n
        assert math.isclose(math.exp(center),s['paired_ratio'],rel_tol=1e-12)
        assert math.isclose(delta,s['paired_difference_seconds'],abs_tol=1e-12)
        for values,mean,bounds,transform in [(logs,center,s['ratio_95_ci'],math.log),
                                           (deltas,delta,s['difference_95_ci'],lambda x:x)]:
            sem=math.sqrt(math.fsum((x-mean)**2 for x in values)/(n*(n-1)))
            expected=[mean-T95[n]*sem,mean+T95[n]*sem]
            assert all(abs(transform(v)-e)<1e-10 for v,e in zip(bounds,expected))
        paired+=1
    checked=0;absolute_checked=0
    for s in data['absolute']:
        for c in s['campaigns']:
            prefix=(c['campaign'],s['codec'],s['workload'],s['phase'],s['variant'])
            medians=[statistics.median(values) for key,values in raw.items() if key[:5]==prefix]
            assert medians and statistics.median(medians)==c['wall_seconds']
        values=[c['wall_seconds'] for c in s['campaigns']]
        n=len(values);mean=math.fsum(values)/n
        half=T95[n]*math.sqrt(math.fsum((v-mean)**2 for v in values)/(n*(n-1)))
        assert math.isclose(mean,s['metrics']['wall_seconds']['mean_campaign_median'],rel_tol=1e-12)
        assert all(abs(x-y)<1e-10 for x,y in zip([mean-half,mean+half],s['metrics']['wall_seconds']['ci95']))
        absolute_checked+=1
        if s['campaign_count']!=3:continue
        # Independent closed-form inversion of the df=2 CDF.
        q=math.sqrt(2*.95**2/(1-.95**2));mean=statistics.mean(values)
        half=q*statistics.stdev(values)/math.sqrt(3)
        assert all(abs(x-y)<1e-10 for x,y in zip([mean-half,mean+half],s['metrics']['wall_seconds']['ci95']))
        checked+=1
    result=dict(status='pass',quantile_cdf_checks=quantiles,absolute_three_campaign_cells=checked,
                paired_cells_recomputed_from_raw_samples=paired,
                absolute_cells_recomputed_from_raw_samples=absolute_checked,
                previous_point_and_interval_estimates_unchanged=bool(a.previous))
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='pass',absolute_cells=checked)))


if __name__=='__main__':main()
