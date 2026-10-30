#!/usr/bin/env python3
"""Render Section 6.5 from complete campaign estimates, retaining every cell."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

CODECS=['gzip','xz','zstd','lz4','lzo']
APP_CODECS=['gzip','xz','lz4']
TASKS=['startup','archive','scan','stream']
TITLES=['Empty command','Include archive','Include scan','256 MiB archive']
VARIANTS=['stock','stock-wrapped','copied','vkso','lkl-64','lkl-512']
LABELS=['SquashFUSE','SquashFUSE + translator','Copied','VKSO','LKL 64 MiB','LKL 512 MiB']
COLORS=['#777777','#BBBBBB','#0072B2','#D55E00','#56B4E9','#009E73']


def select(rows,**conditions):
    found=[r for r in rows if all(r[k]==v for k,v in conditions.items())]
    assert len(found)==1,(conditions,len(found))
    return found[0]


def save(fig,out,name):
    for ext in ['pdf','svg','png']:fig.savefig(out/(name+'.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)


def errors(rows,percent=False):
    centers=np.array([r['paired_ratio'] for r in rows])
    bounds=np.array([r['ratio_95_ci'] for r in rows])
    err=np.vstack((centers-bounds[:,0],bounds[:,1]-centers))
    return ((centers-1)*100,err*100) if percent else (centers,err)


def native_plot(data,out,phase):
    fig,axes=plt.subplots(1,2,figsize=(7.2,2.45))
    groups=['squashfs','normal-module','relaxed-module']
    names=['Original built-in (7 campaigns)','Patched module (3)','Relaxed module (3)']
    for j,(ax,task) in enumerate(zip(axes,['archive','scan'])):
        for i,(group,label,color,marker) in enumerate(zip(groups,names,['#222222','#0072B2','#D55E00'],['o','s','^'])):
            rows=[select(data['summaries'],group='native:'+group+':opt/linux-headers',codec=c,workload=task,phase=phase) for c in CODECS]
            centers,err=errors(rows,True)
            ax.errorbar(np.arange(5)+(i-1)*.18,centers,yerr=err,fmt=marker,ms=4,
                        color=color,capsize=2,lw=1,label=label)
        ax.axhline(0,color='#666666',ls='--',lw=.7)
        ax.set_xticks(range(5),CODECS);ax.set_title(['(a) Include archive','(b) Include scan'][j])
        ax.grid(axis='y',alpha=.16)
    axes[0].set_ylabel('Prepared / reference time change (%)')
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',ncol=3,bbox_to_anchor=(.5,1.11),fontsize=8)
    fig.tight_layout(w_pad=1.3)
    save(fig,out,'filesystem-native' if phase=='fresh-mount' else 'filesystem-native-warm')


def sharing_plot(data,out):
    fig,axes=plt.subplots(1,4,figsize=(7.2,2.25),sharey=True)
    for i,(ax,task,title) in enumerate(zip(axes,TASKS,TITLES)):
        rows=[select(data['summaries'],group='application',codec=c,workload=task,
                     phase='lifecycle',baseline='copied',treatment='vkso') for c in APP_CODECS]
        centers=np.array([r['paired_ratio'] for r in rows]);ci=np.array([r['ratio_95_ci'] for r in rows])
        ax.errorbar(range(3),centers,yerr=[centers-ci[:,0],ci[:,1]-centers],fmt='o',
                    color=COLORS[3],capsize=3,ms=4)
        ax.axhline(1,color='#666666',ls='--',lw=.7);ax.set_xticks(range(3),APP_CODECS)
        ax.set_title(f'({chr(97+i)}) {title}',fontsize=8);ax.grid(axis='y',alpha=.16)
    axes[0].set_ylabel('VKSO / copied elapsed time')
    fig.tight_layout(w_pad=.7);save(fig,out,'filesystem-sharing')


def application_plot(data,out):
    fig,axes=plt.subplots(2,2,figsize=(7.2,4.7))
    for i,(ax,task,title) in enumerate(zip(axes.flat,TASKS,TITLES)):
        for j,(variant,label,color) in enumerate(zip(VARIANTS,LABELS,COLORS)):
            rows=[select(data['absolute'],group='application',codec=c,workload=task,phase='lifecycle',variant=variant) for c in APP_CODECS]
            values=np.array([r['metrics']['wall_seconds']['mean_campaign_median'] for r in rows])
            ci=np.array([r['metrics']['wall_seconds']['ci95'] for r in rows])
            assert np.min(ci)>=0,'A negative absolute interval requires an explicit plot-axis decision.'
            ax.bar(np.arange(3)+(j-2.5)*.125,values,width=.12,color=color,edgecolor='#222222',lw=.35,
                   hatch=['','///','','','xx',''][j],label=label)
            ax.errorbar(np.arange(3)+(j-2.5)*.125,values,yerr=[values-ci[:,0],ci[:,1]-values],
                        fmt='none',color='#222222',capsize=1.5,lw=.7)
        ax.set_xticks(range(3),APP_CODECS);ax.set_title(f'({chr(97+i)}) {title}')
        ax.set_ylabel('Elapsed time (s)');ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.16)
        ax.set_axisbelow(True)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',ncol=3,bbox_to_anchor=(.5,1.035),fontsize=8)
    fig.tight_layout(rect=(0,0,1,.94));save(fig,out,'filesystem-application')


def stream_plot(data,out):
    fig,axes=plt.subplots(1,2,figsize=(7.2,2.2),sharey=True)
    for ax,phase,title in zip(axes,['fresh-mount','warm'],['(a) Fresh mount','(b) Warm filesystem cache']):
        rows=[select(data['summaries'],group='native:squashfs:opt/stream-data',codec=c,workload='archive',phase=phase) for c in APP_CODECS]
        centers,err=errors(rows,True)
        ax.errorbar(range(3),centers,yerr=err,fmt='o',color=COLORS[3],capsize=3)
        ax.axhline(0,color='#666666',ls='--',lw=.7);ax.set_xticks(range(3),APP_CODECS)
        ax.set_title(title);ax.grid(axis='y',alpha=.16)
    axes[0].set_ylabel('Prepared / original time change (%)')
    fig.tight_layout();save(fig,out,'filesystem-stream-native')


def cache_plots(data,out):
    for baseline,treatment,name,ylabel in [
        ('lkl-512','lkl-cache-512','filesystem-lkl-cache-effect','LKL cache 1 s / default time'),
        ('lkl-cache-512','vkso','filesystem-lkl-matched','VKSO / LKL cache 1 s time')]:
        fig,axes=plt.subplots(1,4,figsize=(7.2,2.25),sharey=True)
        for i,(ax,task,title) in enumerate(zip(axes,TASKS,TITLES)):
            rows=[select(data['summaries'],codec=c,workload=task,baseline=baseline,treatment=treatment) for c in APP_CODECS]
            centers=np.array([r['paired_ratio'] for r in rows]);ci=np.array([r['ratio_95_ci'] for r in rows])
            ax.errorbar(range(3),centers,yerr=[centers-ci[:,0],ci[:,1]-centers],fmt='o',
                color=COLORS[3] if treatment=='vkso' else COLORS[5],capsize=3,ms=4)
            ax.axhline(1,color='#666666',ls='--',lw=.7);ax.set_xticks(range(3),APP_CODECS)
            ax.set_title(f'({chr(97+i)}) {title}',fontsize=8);ax.grid(axis='y',alpha=.16)
        axes[0].set_ylabel(ylabel);fig.tight_layout(w_pad=.7);save(fig,out,name)


def resource_table(resources,out,cache=None):
    lines=[r'\begin{table*}[t]\centering\small',
        r'\caption{Helper PSS after the include archive (MiB): median [minimum, maximum] over three campaigns per codec. These idle process snapshots exclude kernel deployment and host caches. LKL labels give configured heap MiB.'+(' The final row is the separate matched-cache diagnostic.' if cache else '')+'}',
        r'\label{tab:filesystem-resources}',r'\begin{tabular}{@{}lrrr@{}}\toprule',
        r'Backend & gzip & xz & lz4 \\\midrule']
    variants=list(zip(VARIANTS,['SquashFUSE','SquashFUSE + translator','Copied','VKSO','LKL 64','LKL 512']))
    if cache:variants.append(('lkl-cache-512','LKL 512, cache 1 s'))
    for variant,label in variants:
        source=cache if variant=='lkl-cache-512' else resources
        values=[]
        for codec in APP_CODECS:
            row=select(source['summaries'],codec=codec,variant=variant,phase='after',metric='pss_kib')
            assert row['n']==3
            values.append(f"{row['median']/1024:.1f} [{row['minimum']/1024:.1f}, {row['maximum']/1024:.1f}]")
        lines.append(label+' & '+' & '.join(values)+r' \\')
    lines += [r'\bottomrule\end{tabular}\end{table*}']
    (out/'filesystem-resources.tex').write_text('\n'.join(lines)+'\n')
    with (out/'source-resource-snapshots.csv').open('w',newline='') as stream:
        records=[dict(profile='default',**r) for r in resources['records']]
        if cache:records += [dict(profile='matched-cache',**r) for r in cache['records']]
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)


def tables(native,app,out,cache=None):
    lines=[r'\begin{longtable}{@{}llllrrr@{}}',
        r'\caption{Complete filesystem paired effects (test/reference). Absolute columns are medians of campaign medians in milliseconds; intervals use independent campaign log-ratio estimates. Fresh means a new mount with warmed backing-image pages.}\label{tab:filesystem-detail}\\',
        r'\toprule Comparison & Codec & Task & Phase & Ref. ms & Test ms & Ratio [95\% CI] \\\midrule\endfirsthead',
        r'\toprule Comparison & Codec & Task & Phase & Ref. ms & Test ms & Ratio [95\% CI] \\\midrule\endhead',
        r'\bottomrule\endfoot']
    selected=list(native['summaries'])+list(app['summaries'])+(list(cache['summaries']) if cache else [])
    group_order=['native:squashfs:opt/linux-headers','native:normal-module:opt/linux-headers',
        'native:relaxed-module:opt/linux-headers','native:squashfs:opt/stream-data','application','application-cache']
    selected.sort(key=lambda r:(group_order.index(r['group']),CODECS.index(r['codec']),
        TASKS.index(r['workload']),r['phase'],r['baseline'],r['treatment']))
    for r in selected:
        if r['group'].startswith('native:'):
            base=r['group'].split(':')[1];comparison='Prep. / '+{'squashfs':'Orig.','normal-module':'Module','relaxed-module':'Relaxed'}[base]
            task='stream' if r['group'].endswith('stream-data') else r['workload']
        else:
            labels=dict(zip(VARIANTS,['SF','SF+T','copy','VKSO','LKL64','LKL512']))
            labels['lkl-cache-512']='LKL512c'
            comparison=labels[r['treatment']]+' / '+labels[r['baseline']];task=r['workload']
            if r['group']=='application-cache':comparison='Diag. '+comparison
        phase={'fresh-mount':'fresh','warm':'warm','lifecycle':'full'}[r['phase']]
        lo,hi=r['ratio_95_ci']
        lines.append(f"{comparison} & {r['codec']} & {task} & {phase} & {1000*r['baseline_seconds']:.2f} & {1000*r['treatment_seconds']:.2f} & {r['paired_ratio']:.3f} [{lo:.3f}, {hi:.3f}]"+r' \\')
    lines += [r'\end{longtable}']
    (out/'filesystem-detail.tex').write_text('\n'.join(lines)+'\n')
    if cache:
        table=[r'\begin{table*}[t]\centering\small',
            r'\caption{Matched positive FUSE caches on read-only SIFs. All LKL configurations use a 512 MiB heap; cache 1 s changes only positive-entry and attribute timeouts. Absolute times are mean campaign medians in seconds. Ratios use paired campaign estimates with 95\% intervals (three campaigns per codec).}',
            r'\label{tab:filesystem-cache}',r'\begin{tabular}{@{}llrrrrr@{}}\toprule',
            r'Codec & Task & LKL default & LKL cache 1 s & VKSO & Cache/default [CI] & VKSO/cache [CI] \\\midrule']
        for codec in APP_CODECS:
            for task,title in zip(TASKS,['Empty','Include tar','Scan','256 MiB tar']):
                absolute=[select(cache['absolute'],codec=codec,workload=task,variant=v)['metrics']['wall_seconds']['mean_campaign_median'] for v in ['lkl-512','lkl-cache-512','vkso']]
                ratios=[select(cache['summaries'],codec=codec,workload=task,baseline=b,treatment=t) for b,t in [('lkl-512','lkl-cache-512'),('lkl-cache-512','vkso')]]
                cells=[f"{r['paired_ratio']:.3f} [{r['ratio_95_ci'][0]:.3f}, {r['ratio_95_ci'][1]:.3f}]" for r in ratios]
                table.append(f'{codec} & {title} & '+' & '.join(f'{v:.3f}' for v in absolute)+' & '+' & '.join(cells)+r' \\')
        table += [r'\bottomrule\end{tabular}\end{table*}']
        (out/'filesystem-cache.tex').write_text('\n'.join(table)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--analysis',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--allow-default-only',action='store_true',help='intermediate artifacts before cache-policy diagnostics finish')
    a=p.parse_args()
    state=json.loads((a.analysis/'result.json').read_text());assert state['status']=='complete'
    native=json.loads((a.analysis/'native/analysis.json').read_text())
    app=json.loads((a.analysis/'application/analysis.json').read_text())
    assert len(native['identities'])==16 and len(app['identities'])==9
    assert all(r['campaign_count']==3 for r in app['summaries'])
    cache=None
    if state.get('matched_cache_campaigns')==9:
        cache=json.loads((a.analysis/'cache/analysis.json').read_text())
        assert len(cache['identities'])==9 and all(r['campaign_count']==3 for r in cache['summaries'])
    else:assert a.allow_default_only,'The matched-cache diagnostic gate remains open.'
    a.output.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'legend.fontsize':8,
        'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
    native_plot(native,a.output,'fresh-mount');native_plot(native,a.output,'warm')
    sharing_plot(app,a.output);application_plot(app,a.output);stream_plot(native,a.output)
    if cache:cache_plots(cache,a.output)
    tables(native,app,a.output,cache)
    resource_table(json.loads((a.analysis/'resources.json').read_text()),a.output,
        json.loads((a.analysis/'resources-cache.json').read_text()) if cache else None)
    sources=[]
    inputs=['native/analysis.json','native/summary.csv','native/observations.csv',
            'application/analysis.json','application/summary.csv','application/observations.csv','resources.json',
            'native/campaign-estimates.csv','application/campaign-estimates.csv',
            'costs.json','maintenance-artifacts.json','matrix.csv','existing-audit.json','result.json',
            'native-statistics-validation.json','application-statistics-validation.json']
    if cache:inputs+=['cache/analysis.json','cache/summary.csv','cache/observations.csv','cache/campaign-estimates.csv','resources-cache.json','cache-statistics-validation.json']
    for relative in inputs:
        source=a.analysis/relative;destination=a.output/('source-'+relative.replace('/','-'))
        if not source.exists() and a.allow_default_only and relative.endswith('/campaign-estimates.csv'):
            continue  # Earlier complete default analysis predates this additional CSV view.
        shutil.copy2(source,destination)
        sources.append(dict(path=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),copy=destination.name))
    (a.output/'provenance.json').write_text(json.dumps(dict(sources=sources,matplotlib=matplotlib.__version__,
        numpy=np.__version__,python=sys.version,generator=str(Path(__file__).resolve()),
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        note='All formal cells retained; pointwise campaign t intervals; render QA still required.'),indent=2)+'\n')


if __name__=='__main__':main()
