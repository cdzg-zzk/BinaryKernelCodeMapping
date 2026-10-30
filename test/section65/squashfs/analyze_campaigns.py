#!/usr/bin/env python3
"""Campaign/block estimates with independent-campaign uncertainty and raw CSV."""
import argparse
import collections
import csv
import json
import math
from pathlib import Path
import statistics

# Two-sided 95% Student t quantiles. Intervals use independent campaign means,
# not individual repeated traversals. Three campaigns are the planned minimum.
T95={2:12.706204736,3:4.302652730,4:3.182446305,5:2.776445105,
     6:2.570581836,7:2.446911851,8:2.364624252,9:2.306004135,10:2.262157163}


def interval(values,log=False):
    vals=list(map(math.log,values)) if log else values
    n=len(vals);mean=statistics.mean(vals)
    if n<2:return None
    assert n in T95, 'add the appropriate campaign t quantile'
    half=T95[n]*statistics.stdev(vals)/math.sqrt(n)
    return [math.exp(mean-half),math.exp(mean+half)] if log else [mean-half,mean+half]


def analyze(runs):
    cells=collections.defaultdict(list);raw=[];identities=[];signatures={}
    for path in runs:
        result=json.loads((path/'result.json').read_text())
        assert result['status']=='complete' and not result.get('pilot',False),path
        rows=[json.loads(line) for line in (path/'samples.jsonl').read_text().splitlines()]
        assert len(rows)==result['observations']
        env=json.loads((path/'environment.json').read_text())
        campaign=result['campaign'];is_native='cases' in result
        assert not any(i['campaign']==campaign for i in identities),campaign
        identities.append(dict(campaign=campaign,path=str(path),environment=env))
        if is_native:
            group='native:'+result.get('baseline_label',result.get('original_filesystem','squashfs'))+':'+result.get('subtree','opt/linux-headers')
        else:group=result.get('analysis_group','application')
        for row in rows:
            codec=row.get('compressor',Path(result.get('image','unknown')).stem)
            if is_native:
                signature=dict(modules=env['modules'],image=next(c['sha256'] for c in result['cases'] if c['compressor']==codec),
                               original_module=result.get('original_module',{}).get('sha256'),cpu=result['cpu'])
            else:
                signature=dict(binaries={str(p):h for p,h in env['binaries'].items()},
                    image=result['image_sha256'],cpus=result['cpus'],translator=result['helper_implementation'])
            assert signatures.setdefault((group,codec),signature)==signature,('mixed implementations or conditions',group,codec,campaign)
            r=dict(row,source=str(path),group=group,codec=codec)
            raw.append(r)
            cells[group,codec,row['workload'],row.get('phase','lifecycle'),campaign].append(r)
    pooled=collections.defaultdict(list);absolute=collections.defaultdict(list)
    for (group,codec,workload,phase,campaign),rows in cells.items():
        variants=sorted({r['variant'] for r in rows})
        for variant in variants:
            metrics={}
            for metric in ['wall_seconds','user_cpu_seconds','system_cpu_seconds','cpu_seconds']:
                selected=[r for r in rows if r['variant']==variant]
                if not all(metric in r for r in selected):continue
                block_values=[statistics.median(r[metric] for r in selected if r['block']==block)
                              for block in sorted({r['block'] for r in selected})]
                metrics[metric]=statistics.median(block_values)
            absolute[group,codec,workload,phase,variant].append(dict(campaign=campaign,**metrics))
        pairs=([('original','prepared')] if group.startswith('native:') else
              [('stock',v) for v in variants if v!='stock']+
              [('copied','vkso')]+[(v,'vkso') for v in variants if v.startswith('lkl-')])
        if 'lkl-cache-512' in variants:pairs.append(('lkl-512','lkl-cache-512'))
        for baseline,treatment in pairs:
            blocks=[]
            for block in sorted({r['block'] for r in rows}):
                b=[r['wall_seconds'] for r in rows if r['block']==block and r['variant']==baseline]
                t=[r['wall_seconds'] for r in rows if r['block']==block and r['variant']==treatment]
                assert b and len(b)==len(t),(campaign,block,baseline,treatment)
                bm,tm=statistics.median(b),statistics.median(t)
                blocks.append(dict(block=block,baseline_seconds=bm,treatment_seconds=tm,
                                   ratio=tm/bm,difference_seconds=tm-bm,repeats=len(b)))
            pooled[group,codec,workload,phase,baseline,treatment].append(dict(campaign=campaign,blocks=blocks,
                ratio=math.exp(statistics.mean(math.log(b['ratio']) for b in blocks)),
                difference_seconds=statistics.mean(b['difference_seconds'] for b in blocks),
                baseline_seconds=statistics.median(b['baseline_seconds'] for b in blocks),
                treatment_seconds=statistics.median(b['treatment_seconds'] for b in blocks)))
    summaries=[]
    for key,campaigns in pooled.items():
        group,codec,workload,phase,baseline,treatment=key
        ratios=[c['ratio'] for c in campaigns];differences=[c['difference_seconds'] for c in campaigns]
        summaries.append(dict(group=group,codec=codec,workload=workload,phase=phase,
            baseline=baseline,treatment=treatment,campaign_count=len(campaigns),campaigns=campaigns,
            paired_ratio=math.exp(statistics.mean(map(math.log,ratios))),ratio_95_ci=interval(ratios,True),
            paired_difference_seconds=statistics.mean(differences),difference_95_ci=interval(differences),
            baseline_seconds=statistics.median(c['baseline_seconds'] for c in campaigns),
            treatment_seconds=statistics.median(c['treatment_seconds'] for c in campaigns)))
    absolute_summaries=[]
    for (group,codec,workload,phase,variant),campaigns in absolute.items():
        metrics={}
        for metric in ['wall_seconds','user_cpu_seconds','system_cpu_seconds','cpu_seconds']:
            if not all(metric in c for c in campaigns):continue
            values=[c[metric] for c in campaigns]
            metrics[metric]=dict(mean_campaign_median=statistics.mean(values),ci95=interval(values))
        absolute_summaries.append(dict(group=group,codec=codec,workload=workload,phase=phase,
            variant=variant,campaign_count=len(campaigns),campaigns=campaigns,metrics=metrics))
    return dict(status='complete',method='Block medians; equal-weight campaign mean log ratios; 95% t intervals across independent campaigns. Absolute summaries use the mean of campaign medians. Descriptive on this host/boot; no repeated-access pseudoreplication.',
                identities=identities,summaries=summaries,absolute=absolute_summaries),raw


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result,raw=analyze([r.resolve() for r in a.runs])
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    with (a.output/'observations.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=sorted(set().union(*(r.keys() for r in raw))))
        writer.writeheader();writer.writerows(raw)
    with (a.output/'summary.csv').open('w',newline='') as stream:
        keys=['group','codec','workload','phase','baseline','treatment','campaign_count',
              'baseline_seconds','treatment_seconds','paired_ratio','ratio_95_ci','paired_difference_seconds','difference_95_ci']
        writer=csv.DictWriter(stream,fieldnames=keys,extrasaction='ignore');writer.writeheader();writer.writerows(result['summaries'])
    with (a.output/'campaign-estimates.csv').open('w',newline='') as stream:
        rows=[]
        for cell in result['summaries']:
            for campaign in cell['campaigns']:
                rows.append(dict(**{k:cell[k] for k in ['group','codec','workload','phase','baseline','treatment']},
                    **{k:v for k,v in campaign.items() if k!='blocks'},blocks=len(campaign['blocks'])))
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(campaigns=len(result['identities']),observations=len(raw),cells=len(result['summaries']))))


if __name__=='__main__':main()
