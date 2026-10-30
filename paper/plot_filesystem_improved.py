#!/usr/bin/env python3
"""Render the full improved Section 6.5 matrix with traceable paired intervals."""
import argparse,hashlib,json
from pathlib import Path
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
FORMATS=['gzip','xz','zstd','lz4','lzo'];APP=['gzip','xz','lz4'];TASKS=['startup','archive','scan','stream']
TITLES=['Empty command','Include archive','Include scan','256 MiB archive']
COLORS=['#666666','#0072B2','#D55E00','#222222','#009E73'];MARKERS=['o','s','^','D']

def select(rows,**keys):
    found=[r for r in rows if all(r.get(k)==v for k,v in keys.items())];assert len(found)==1,(keys,len(found));return found[0]
def save(fig,out,name):
    for ext in ['pdf','svg','png']:fig.savefig(out/(name+'.'+ext),bbox_inches='tight',dpi=180)
    plt.close(fig)
def error_points(ax,x,rows,label,color,marker,percent=False):
    point=np.array([r['time_ratio'] for r in rows]);ci=np.array([r['ratio_ci95'] for r in rows]);err=np.vstack([point-ci[:,0],ci[:,1]-point])
    if percent:point=(point-1)*100;err*=100
    ax.errorbar(x,point,yerr=err,fmt=marker,color=color,label=label,ms=4,capsize=2,lw=1)
def decoration(ax,labels,reference=0):
    ax.axhline(reference,color='#777777',ls='--',lw=.7);ax.set_xticks(range(len(labels)),labels);ax.grid(axis='y',alpha=.15)
def legend(fig,ax,ncol=3):
    h,l=ax.get_legend_handles_labels();rows=(len(l)+ncol-1)//ncol
    fig.legend(h,l,loc='upper center',ncol=ncol,bbox_to_anchor=(.5,1+.22*rows/fig.get_size_inches()[1]),frameon=False,fontsize=8)
def native(data,out,phase='fresh-mount',kind='native'):
    codecs=FORMATS if kind=='native' else APP
    tasks=['archive','scan'] if kind=='native' else ['archive']
    fig,axes=plt.subplots(1,len(tasks),figsize=(7.2,2.5),squeeze=False)
    variants=['prepared-before','prepared-small-copy','prepared-composed'];labels=['Prepared before','Bounded copy','Composed prepared']
    for index,(ax,task) in enumerate(zip(axes[0],tasks)):
        for j,(v,label,color) in enumerate(zip(variants,labels,COLORS)):
            rows=[select(data['results'],kind=kind,codec=c,workload=task,phase=phase,baseline='original',treatment=v) for c in codecs]
            error_points(ax,np.arange(len(codecs))+(j-1)*.18,rows,label,color,MARKERS[j],True)
        decoration(ax,codecs);ax.set_title(('Include archive' if task=='archive' else 'Include scan') if kind=='native' else 'Native 256 MiB archive')
    axes[0,0].set_ylabel('Prepared / original time change (%)');legend(fig,axes[0,0]);fig.tight_layout(w_pad=1.2)
    name='filesystem-native' if kind=='native' else 'filesystem-stream-native'
    save(fig,out,name+('-warm' if phase=='warm' else ''))
def sharing(data,out):
    fig,axes=plt.subplots(1,4,figsize=(7.2,2.35),sharey=True)
    for ax,task,title in zip(axes,TASKS,TITLES):
        rows=[select(data['results'],kind='application',codec=c,workload=task,baseline='copied',treatment='vkso') for c in APP]
        error_points(ax,np.arange(3),rows,'VKSO','#D55E00','o');decoration(ax,APP,1);ax.set_title(title,fontsize=8)
    axes[0].set_ylabel('VKSO / copied elapsed time');fig.tight_layout(w_pad=.7);save(fig,out,'filesystem-sharing')
def loader_control(main,data,out,single=None):
    fig,axes=plt.subplots(1,4,figsize=(7.2,2.65),sharey=True)
    sources=[(main['results'],'Original paths, 2 CPUs',None),(data['results'],'Equal paths, 2 CPUs',None)]
    if single:sources.append((single['results'],'Equal paths, 1 CPU',None))
    for ax,task,title in zip(axes,TASKS,TITLES):
        for j,(source,label,padding) in enumerate(sources):
            keys=dict(loader_padding=padding) if padding is not None else {}
            rows=[select(source,kind='application',codec=c,workload=task,baseline='copied',treatment='vkso',**keys) for c in APP]
            error_points(ax,np.arange(3)+(j-(len(sources)-1)/2)*.17,rows,label,COLORS[j],MARKERS[j])
        decoration(ax,APP,1);ax.set_title(title,fontsize=8)
    axes[0].set_ylabel('VKSO / copied elapsed time');legend(fig,axes[0],3)
    fig.tight_layout(w_pad=.7);save(fig,out,'filesystem-loader-control')
    if single:
        fig,axes=plt.subplots(1,4,figsize=(7.2,2.65),sharey=True)
        sources=[(data,0,'2 CPUs, padding 0'),(data,16,'2 CPUs, padding 16'),
                 (single,0,'1 CPU, padding 0'),(single,16,'1 CPU, padding 16')]
        for ax,task,title in zip(axes,TASKS,TITLES):
            for j,(source,padding,label) in enumerate(sources):
                rows=[select(source['loader_padding_results'],kind='application',codec=c,workload=task,baseline='copied',treatment='vkso',loader_padding=padding) for c in APP]
                error_points(ax,np.arange(3)+(j-1.5)*.15,rows,label,COLORS[j],MARKERS[j])
            decoration(ax,APP,1);ax.set_title(title,fontsize=8)
        axes[0].set_ylabel('VKSO / copied elapsed time');legend(fig,axes[0],2)
        fig.tight_layout(w_pad=.7);save(fig,out,'filesystem-loader-padding')
def application(data,out):
    variants=['stock','copied','vkso','lkl-512','lkl-cache-512'];labels=['SquashFUSE','Copied','VKSO','LKL512 default','LKL512 matched cache']
    fig,axes=plt.subplots(2,2,figsize=(7.2,4.7))
    for ax,task,title in zip(axes.flat,TASKS,TITLES):
        for j,(v,label,color) in enumerate(zip(variants,labels,COLORS)):
            rows=[select(data['absolute'],kind='application',codec=c,workload=task,variant=v) for c in APP]
            y=np.array([r['mean_campaign_median_seconds'] for r in rows]);ci=np.array([r['ci95_seconds'] for r in rows]);assert np.all(ci[:,0]>=0)
            ax.bar(np.arange(3)+(j-2)*.15,y,width=.14,color=color,label=label,hatch=['','//','','xx','..'][j],edgecolor='white',linewidth=.3,
                yerr=np.vstack([y-ci[:,0],ci[:,1]-y]),capsize=1.5,error_kw=dict(lw=.7))
        ax.set_xticks(range(3),APP);ax.set_title(title);ax.set_ylabel('Elapsed time (s)');ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.15)
    legend(fig,axes[0,0],3);fig.tight_layout(h_pad=1.4);save(fig,out,'filesystem-application')
def ablations(data,out,codecs=None,name='filesystem-ablations'):
    codecs=codecs or ['gzip','lz4']
    variants=['copied-directory','copied-direct','copied-library','copied'];labels=['Directory cache','Direct output','Both + library LZ4','Both + common LZ4']
    if codecs==['xz']:labels=['Directory cache','Direct output','Both + liblz4 dependency','Both without liblz4 dependency']
    fig,axes=plt.subplots(1,len(codecs),figsize=(7.2,2.65));axes=np.atleast_1d(axes)
    for ax,codec in zip(axes,codecs):
        for j,(v,label,color) in enumerate(zip(variants,labels,['#0072B2','#009E73','#666666','#D55E00'])):
            rows=[select(data['results'],kind='application',codec=codec,workload=t,baseline='copied-old',treatment=v) for t in TASKS]
            error_points(ax,np.arange(4)+(j-1.5)*.15,rows,label,color,MARKERS[j],True)
        decoration(ax,['Startup','Include tar','Scan','Stream']);ax.set_title(codec)
    axes[0].set_ylabel('Time change from old adapter (%)');legend(fig,axes[0],2);fig.tight_layout(w_pad=1.1);save(fig,out,name)
def native_controls(data,out):
    fig,axes=plt.subplots(1,2,figsize=(7.2,2.65))
    sets=[ [('native-control','native-normal','native-small-normal','Unadapted native'),('native','prepared-before','prepared-small-copy','Prepared')],
           [('native-control','native-small-normal','prepared-small-copy','Optimized normal native'),('native-control','native-small-relaxed','prepared-small-copy','Optimized relaxed native')]]
    for index,(ax,pairs) in enumerate(zip(axes,sets)):
        for j,(kind,b,t,label) in enumerate(pairs):
            rows=[select(data['results'],kind=kind,codec=c,workload='scan',phase='fresh-mount',baseline=b,treatment=t) for c in APP]
            error_points(ax,np.arange(3)+(j-.5)*.15,rows,label,COLORS[j+1],MARKERS[j],True)
        decoration(ax,APP);ax.legend(fontsize=7,frameon=False);ax.set_ylabel('Paired time change (%)')
        ax.set_title(['Effect of the same bounded copy','Prepared / optimized reference'][index],fontsize=9)
    fig.tight_layout(w_pad=1.5);save(fig,out,'filesystem-native-controls')
def detail(data,out,name='filesystem-detail.tex'):
    names={'original':'O','prepared-before':'P0','prepared-small-copy':'P16','prepared-composed':'PC','stock':'SF','stock-wrapped':'SF+T','copied-old':'A0','copied-directory':'AD','copied-direct':'AX','copied-library':'AL','copied':'C','vkso':'V','lkl-512':'L','lkl-cache-512':'LC','native-normal':'N','native-small-normal':'N16','native-small-relaxed':'NR16'}
    lines=[r'\begin{longtable}{lllrrl}',r'\toprule Codec & Task & Treatment / baseline & Baseline (s) & Treatment (s) & Ratio [95\% CI] \\',r'\midrule\endhead']
    group=None
    for r in data['results']:
        key=(r['kind'],r['phase'])
        if key!=group:
            lines.append(r'\multicolumn{6}{l}{\textbf{'+key[0].replace('-',' ')+': '+key[1].replace('-',' ')+r'}} \\');group=key
        b,t=r['baseline'],r['treatment'];seconds=r['absolute_median_seconds'];lo,hi=r['ratio_ci95']
        lines.append(f"{r['codec']} & {r['workload']} & {names[t]}/{names[b]} & {seconds[b]:.4f} & {seconds[t]:.4f} & {r['time_ratio']:.4f} [{lo:.4f}, {hi:.4f}] "+r'\\')
    lines += [r'\bottomrule\end{longtable}'];(out/name).write_text('\n'.join(lines)+'\n')
    (out/'detail-labels.json').write_text(json.dumps(names,indent=2)+'\n')
def resources(data,out):
    labels={'stock':'SquashFUSE','copied':'Copied','vkso':'VKSO','lkl-512':'LKL512 default','lkl-cache-512':'LKL512 matched'}
    lines=[r'\begin{table*}[t]',r'\centering\small',r'\caption{Idle helper memory after the include archive, before PFN or debugger observation. Values are medians [minimum, maximum] across three campaigns, in MiB. These process snapshots exclude kernel module residency and are not peak or whole-machine memory.}',r'\label{tab:filesystem-resources}',r'\begin{tabular}{llrrr}',r'\toprule Codec & Backend & RSS & PSS & USS \\',r'\midrule']
    for codec in APP:
        for variant,label in labels.items():
            values=[]
            for metric in ['rss_kib','pss_kib','uss_kib']:
                r=select(data['summaries'],codec=codec,variant=variant,phase='after',metric=metric)
                values.append(f"{r['median']/1024:.2f} [{r['minimum']/1024:.2f}, {r['maximum']/1024:.2f}]")
            lines.append(f'{codec} & {label} & '+' & '.join(values)+r' \\')
    lines.extend([r'\bottomrule\end{tabular}',r'\end{table*}']);(out/'filesystem-resources.tex').write_text('\n'.join(lines)+'\n')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--analysis',type=Path,required=True);p.add_argument('--resources',type=Path);p.add_argument('--xz-attribution',type=Path);p.add_argument('--loader-control',type=Path);p.add_argument('--single-cpu',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--native-only',action='store_true');a=p.parse_args()
    assert a.native_only or a.resources,'Full publication figures include the resource ledger.'
    data=json.loads(a.analysis.read_text());assert data['status']=='complete';out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':8,'ytick.labelsize':8,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none'})
    native(data,out);native(data,out,'warm')
    if not a.native_only:
        sharing(data,out);application(data,out);ablations(data,out);native_controls(data,out);native(data,out,kind='native-stream');native(data,out,'warm',kind='native-stream');detail(data,out)
        resource_data=json.loads(a.resources.read_text());assert resource_data['status']=='complete';resources(resource_data,out)
        shutil.copy2(a.resources,out/'source-improvement-resources.json')
        if a.xz_attribution:
            xz=json.loads(a.xz_attribution.read_text());assert xz['status']=='complete' and xz['observations']==672
            ablations(xz,out,['xz'],'filesystem-xz-attribution');detail(xz,out,'filesystem-xz-detail.tex')
            shutil.copy2(a.xz_attribution,out/'source-xz-attribution-analysis.json')
        if a.loader_control:
            controlled=json.loads(a.loader_control.read_text());assert controlled['status']=='complete' and controlled['observations']==1440
            single=json.loads(a.single_cpu.read_text()) if a.single_cpu else None
            if single:
                assert single['status']=='complete' and single['observations']==1440
                detail(single,out,'filesystem-singlecpu-detail.tex')
                for padding in [0,16]:
                    detail(dict(results=[r for r in single['loader_padding_results'] if r['loader_padding']==padding]),out,f'filesystem-singlecpu-padding-{padding}.tex')
                shutil.copy2(a.single_cpu,out/'source-singlecpu-analysis.json')
            loader_control(data,controlled,out,single);detail(controlled,out,'filesystem-loader-detail.tex')
            for padding in [0,16]:
                detail(dict(results=[r for r in controlled['loader_padding_results'] if r['loader_padding']==padding]),out,f'filesystem-loader-padding-{padding}.tex')
            shutil.copy2(a.loader_control,out/'source-loader-control-analysis.json')
    shutil.copy2(a.analysis,out/'source-improvement-analysis.json')
    shutil.copy2(__file__,out/'plotting-script.py')
    sources=[dict(path=str(a.analysis.resolve()),sha256=hashlib.sha256(a.analysis.read_bytes()).hexdigest())]
    if a.resources:sources.append(dict(path=str(a.resources.resolve()),sha256=hashlib.sha256(a.resources.read_bytes()).hexdigest()))
    if a.xz_attribution:sources.append(dict(path=str(a.xz_attribution.resolve()),sha256=hashlib.sha256(a.xz_attribution.read_bytes()).hexdigest()))
    if a.loader_control:sources.append(dict(path=str(a.loader_control.resolve()),sha256=hashlib.sha256(a.loader_control.read_bytes()).hexdigest()))
    if a.single_cpu:sources.append(dict(path=str(a.single_cpu.resolve()),sha256=hashlib.sha256(a.single_cpu.read_bytes()).hexdigest()))
    (out/'provenance.json').write_text(json.dumps(dict(sources=sources,
        plotting_script=str(Path(__file__).resolve()),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),primary_intervals='pointwise 95% Student-t over three campaign means',native_only=a.native_only),indent=2)+'\n')
    print(out)
if __name__=='__main__':main()
