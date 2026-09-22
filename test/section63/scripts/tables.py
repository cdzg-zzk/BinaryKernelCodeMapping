#!/usr/bin/env python3
"""Build publication tables and compact plotting data from the audited campaign."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import statistics as stats


def read(path):return list(csv.DictReader(path.open()))
def write(path,rows):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def format_ratio(r):
    return f"{float(r['median_cost_ratio']):.3f} [{float(r['minimum_deployment_ratio']):.3f}, {float(r['maximum_deployment_ratio']):.3f}]"
def build(base):
    audit=json.loads((base/'analysis/audit.json').read_text());assert audit['status']=='complete'
    out=base/'paper-material';out.mkdir(exist_ok=True)
    data=read(base/'analysis/summary.csv')
    lookup={(r['algorithm'],r['domain'],r['workload'],r['target'],r['baseline']):r for r in data}
    groups=defaultdict(list)
    for name in ('observations.csv','corpus-observations.csv'):
        for r in read(base/'analysis'/name):
            groups[tuple(r[k] for k in ('deployment','algorithm','domain','workload','backend'))].append(float(r['value']))
    medians=defaultdict(list)
    for key,values in groups.items():medians[key[1:]].append(stats.median(values))
    absolute={key:stats.median(v) for key,v in medians.items()}
    main=[]
    for a in ('lz4','bch','xz'):
        if a=='lz4':
            selected=[(f'{op}/block={b}',f'{op}, {b//1024} KiB') for op in ('compress','decompress') for b in (4096,65536,1048576)]
        elif a=='bch':
            selected=[(f'm=13/t={t}/bytes=512/errors={0 if op=="encode" else 2}/{op}',f't={t}, '+op+(' (2 errors)' if op!='encode' else '')) for t in (4,8) for op in ('encode','decode-full','decode-precomputed')]
        else:selected=[(label,label) for label in ('bash','libc.so.6','python3')]
        for work,label in selected:
            for baseline in ('native-dso','adapted-dso'):
                r=lookup[a,'user',work,'kernel-vkso',baseline]
                main.append(dict(algorithm=a,label=label,workload=work,baseline=baseline,
                    overhead_pct=100*(float(r['median_cost_ratio'])-1),
                    minimum_load_pct=100*(float(r['minimum_deployment_ratio'])-1),
                    maximum_load_pct=100*(float(r['maximum_deployment_ratio'])-1)))
    write(out/'user-plot.csv',main)
    kernel=[]
    for a in ('lz4','bch','xz'):
        if a=='lz4':selected=[(f'corpus/{op}/block={b}',f'{op}, {b//1024} KiB') for op in ('compress','decompress') for b in (65536,1048576)]
        elif a=='bch':selected=[(f'm=13/t={t}/bytes=512/errors={0 if op=="encode" else 2}/{op}',f't={t}, '+op) for t in (4,8) for op in ('encode','decode-full','decode-precomputed')]
        else:selected=[(label+'/decompress/block=0',label) for label in ('bash','libc.so.6','python3')]
        for work,label in selected:
            r=lookup[a,'kernel',work,'owner-kernel','stock-kernel'];m=lookup[a,'kernel',work,'owner-kernel','matched-kernel']
            kernel.append(dict(algorithm=a,label=label,workload=work,owner_stock=format_ratio(r),owner_matched=format_ratio(m),
                owner_cost=absolute[a,'kernel',work,'owner-kernel'],unit=r['unit']))
    write(out/'kernel-table.csv',kernel)
    counts=audit.get('repetition_count',{'bch':3,'lz4':3,'xz':3})
    description=f"BCH uses {counts['bch']} deployments; LZ4/XZ use {counts['lz4']} each."
    lines=['# Complete six-version results','',
        description+' Ratios are medians of deployment medians; brackets give their minimum–maximum range. Each deployment median retains within-round pairing. The ranges are not confidence intervals.','']
    for a in ('lz4','bch','xz'):
        for domain in ('user','kernel'):
            native,middle,target=('native-dso','adapted-dso','kernel-vkso') if domain=='user' else ('stock-kernel','matched-kernel','owner-kernel')
            candidates=sorted({r['workload'] for r in data if r['algorithm']==a and r['domain']==domain
                               and (a!='lz4' or domain!='kernel' or r['workload'].startswith('corpus/'))})
            lines += [f'## {a.upper()} — {domain}','',f'| Workload | {native} | {middle} | {target} | {target}/{native} | {target}/{middle} | {middle}/{native} |',
                      '| --- | ---: | ---: | ---: | --- | --- | --- |']
            for work in candidates:
                scale=1 if a=='bch' else 1e6;unit='ns/op' if a=='bch' else 'ms/corpus' if a=='lz4' else 'ms/file'
                costs=[f'{absolute[a,domain,work,b]/scale:.2f} {unit}' for b in (native,middle,target)]
                ratios=[format_ratio(lookup[a,domain,work,t,b]) for t,b in ((target,native),(target,middle),(middle,native))]
                lines.append('| '+' | '.join([work,*costs,*ratios])+' |')
            lines.append('')
    (out/'tables.md').write_text('\n'.join(lines)+'\n')
    tex=[r'\begin{table*}[t]',r'\centering',r'\small',
         r'\caption{Kernel execution costs. Ratios compare the exported owner with Stock and original-source Matched. Brackets span load medians. '+description+' BCH decode rows use two errors.}',
         r'\label{tab:export-kernel}',r'\begin{tabular}{llcc}',r'\toprule',r'Algorithm & Operation/input & /Stock & /Matched \\',r'\midrule']
    for r in kernel:
        label=r['label'].replace('decode-precomputed','precomputed').replace('decode-full','full decode').replace('decompress','decomp.').replace('compress','comp.')
        tex.append(f"{r['algorithm'].upper()} & {label} & {r['owner_stock']} & {r['owner_matched']} \\\\")
    tex += [r'\bottomrule',r'\end{tabular}',r'\end{table*}']
    (out/'kernel-table.tex').write_text('\n'.join(tex)+'\n')
    print('Generated full tables and selected figure/table inputs.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();build(a.directory.resolve())
