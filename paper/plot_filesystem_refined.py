#!/usr/bin/env python3
"""Render final-owner comparisons and full tables from refinement data."""
import argparse, hashlib, json, shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from plot_filesystem_improved import select,save,error_points,decoration,legend

CODECS=['gzip','xz','zstd','lz4','lzo']
APPS=['gzip','xz','lz4'];TASKS=['startup','scan','archive','stream']
COLORS=['#0072B2','#D55E00','#009E73','#777777','#CC79A7','#222222']
LABELS={'original':'O','native-small-normal':'N','native-small-relaxed':'NR',
 'prepared-composed':'PL','prepared-xz':'PX','stock':'SF','stock-single':'SF1',
 'stock-wrapped':'SF+T','copied':'C','vkso':'V','lkl-512':'L','lkl-cache-512':'LC',
 'copied-library':'CL','copied-retained':'CR'}
TITLES={'startup':'Startup','scan':'Include scan','archive':'Include archive','stream':'256 MiB archive'}
ROW=r' \\'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',type=Path,required=True);p.add_argument('--resources',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    data=json.loads(a.analysis.read_text());resources=json.loads(a.resources.read_text())
    assert data['status']==resources['status']=='complete'
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    for phase in ['fresh-mount','warm']:
        fig,axes=plt.subplots(1,2,figsize=(7.1,2.35))
        for ax,task in zip(axes,['scan','archive']):
            for index,(baseline,label) in enumerate([('original','Original native'),('native-small-normal','Optimized native'),('native-small-relaxed','Optimized relaxed native')]):
                rows=[select(data['results'],kind='native-final',codec=c,workload=task,phase=phase,baseline=baseline,treatment='prepared-xz') for c in CODECS]
                error_points(ax,np.arange(5)+(index-1)*.18,rows,label,COLORS[index],['o','s','^'][index],True)
            decoration(ax,CODECS);ax.set_title('Include '+task)
        axes[0].set_ylabel('Final prepared time change (%)');legend(fig,axes[0],3)
        fig.tight_layout(w_pad=1.4);save(fig,out,'filesystem-native'+('-warm' if phase=='warm' else ''))
    fig,axes=plt.subplots(2,2,figsize=(3.45,3.2),sharey=True);axes=axes.ravel()
    for ax,task in zip(axes,TASKS):
        rows=[select(data['results'],kind='application-final',codec=c,workload=task,baseline='copied',treatment='vkso') for c in APPS]
        error_points(ax,np.arange(3),rows,'2 CPUs',COLORS[0],'o',True)
        if task in ['scan','stream']:
            matched=[select(data['results'],kind='decoder-diagnostic',codec=c,workload=task,baseline='copied',treatment='vkso') for c in ['xz','lz4']]
            error_points(ax,np.array([1.16,2.16]),matched,'Equal paths',COLORS[2],'^',True)
        if task=='stream':
            r=select(data['results'],kind='sharing-singlecpu',codec='gzip',workload='stream',baseline='copied',treatment='vkso')
            error_points(ax,np.array([.16]),[r],'1 CPU',COLORS[1],'s',True)
        decoration(ax,APPS);ax.set_title(TITLES[task],fontsize=8)
    fig.supylabel('VKSO / copied time change (%)',fontsize=8);legend(fig,axes[-1],3)
    fig.tight_layout(w_pad=.8);save(fig,out,'filesystem-sharing')
    fig,axes=plt.subplots(1,4,figsize=(7.1,2.45),sharey=True)
    for ax,task in zip(axes,TASKS):
        for index,(baseline,label) in enumerate([('stock','SquashFUSE default'),('stock-single','SquashFUSE single thread'),('lkl-cache-512','LKL matched cache')]):
            rows=[select(data['results'],kind='application-final',codec=c,workload=task,baseline=baseline,treatment='vkso') for c in APPS]
            error_points(ax,np.arange(3)+(index-1)*.18,rows,label,COLORS[index],['o','s','^'][index],True)
        decoration(ax,APPS);ax.set_title(TITLES[task],fontsize=8)
    axes[0].set_ylabel('VKSO / baseline time change (%)');legend(fig,axes[0],3)
    fig.tight_layout(w_pad=.8);save(fig,out,'filesystem-application')
    fig,axes=plt.subplots(2,1,figsize=(3.45,3.1),sharey=True)
    variants=['stock','stock-single','copied','vkso','lkl-512','lkl-cache-512']
    for ax,codec in zip(axes,['gzip','xz']):
        rows=[select(data['absolute'],kind='heldout',codec=codec,workload='compile',variant=v) for v in variants]
        points=np.array([r['mean_campaign_median_seconds'] for r in rows]);ci=np.array([r['ci95_seconds'] for r in rows])
        ax.bar(np.arange(6),points,color=COLORS,width=.65)
        ax.errorbar(np.arange(6),points,yerr=np.vstack([points-ci[:,0],ci[:,1]-points]),fmt='none',ecolor='#333333',capsize=2,lw=.8)
        ax.set_xticks(np.arange(6),[LABELS[v] for v in variants]);ax.set_title(codec+' SIF');ax.grid(axis='y',alpha=.15)
    fig.supylabel('Python compilation elapsed time (s)',fontsize=8)
    fig.tight_layout();save(fig,out,'filesystem-heldout')
    fig,ax=plt.subplots(figsize=(6.6,2.6))
    for index,variant in enumerate(['stock','stock-single','copied','vkso','lkl-cache-512']):
        rows=sorted([r for r in resources['scale'] if r['variant']==variant],key=lambda r:r['entries'])
        ax.plot([r['entries'] for r in rows],[r['pss_kib']/1024 for r in rows],marker=['o','s','^','D','v'][index],color=COLORS[index],label=LABELS[variant],ms=4)
    ax.set_xscale('log',base=4);ax.set_xticks([5866,23464,93856],['5,866','23,464','93,856'])
    ax.set_xlabel('Visited include-tree entries');ax.set_ylabel('Retained helper PSS (MiB)');ax.grid(axis='y',alpha=.15)
    ax.legend(ncol=5,frameon=False);fig.tight_layout();save(fig,out,'filesystem-memory-scale')
    absolute={(r['kind'],r['codec'],r['workload'],r['phase'],r['variant']):r for r in data['absolute']}
    lines=[r'\begin{longtable}{lllrrrr}',r'\toprule','Codec/task/phase & Base & Test & Base s & Test s & Ratio & 95\\% CI'+ROW,r'\midrule\endhead']
    last=None
    for r in data['results']:
        if r['kind']!=last:
            lines.append(r'\multicolumn{7}{l}{\textbf{'+r['kind'].replace('-',' ')+r'}}'+ROW);last=r['kind']
        key=tuple(r[k] for k in ['kind','codec','workload','phase'])
        b=absolute[key+(r['baseline'],)]['mean_campaign_median_seconds'];t=absolute[key+(r['treatment'],)]['mean_campaign_median_seconds']
        label='/'.join([r['codec'],r['workload'],{'full-application':'app','fresh-mount':'fresh','warm':'warm'}[r['phase']]])
        lines.append(f"{label} & {LABELS[r['baseline']]} & {LABELS[r['treatment']]} & {b:.4f} & {t:.4f} & {r['time_ratio']:.4f} & [{r['ratio_ci95'][0]:.4f}, {r['ratio_ci95'][1]:.4f}]"+ROW)
    lines += [r'\bottomrule',r'\end{longtable}'];(out/'filesystem-detail.tex').write_text('\n'.join(lines)+'\n')
    lines=[r'\begin{table}[t]\centering\small',r'\caption{Helper PSS after include archive, before PFN observation. Ranges span three codecs and three campaigns; they are not peaks.}',r'\label{tab:filesystem-resources}',r'\begin{tabular}{lr}\toprule Backend & PSS range (MiB)'+ROW+r'\midrule']
    for variant in variants:
        v=[r['pss_kib']/1024 for r in resources['records'] if r['variant']==variant and r['phase']=='after']
        lines.append(f"{LABELS[variant]} & {min(v):.2f}--{max(v):.2f}"+ROW)
    lines += [r'\bottomrule\end{tabular}\end{table}'];(out/'filesystem-resources.tex').write_text('\n'.join(lines)+'\n')
    b=resources['business'];lines=[r'\begin{table}[t]\centering\small',r'\caption{Filesystem component costs with the generic platform installed. Residency, avoided backing and requested metadata are separate quantities.}',r'\label{tab:filesystem-business}',r'\begin{tabular}{lr}\toprule Component & Size'+ROW+r'\midrule']
    for title,key in [('Matched native module','native_reference_resident_bytes'),('Prepared owner + consumer','prepared_native_resident_bytes'),('Native preparation increment','native_preparation_delta_bytes'),('Avoided core backing','shared_backing_avoided_once_bytes')]:lines.append(f'{title} & {b[key]//1024} KiB'+ROW)
    lines.append(f"Requested registration metadata & {b['registration_requested_bytes']:,} B"+ROW)
    lines += [r'\bottomrule\end{tabular}\end{table}'];(out/'filesystem-business.tex').write_text('\n'.join(lines)+'\n')
    sources=[]
    for path,name in [(a.analysis,'source-refinement-analysis.json'),(a.resources,'source-refinement-resources.json')]:
        shutil.copy2(path,out/name);sources.append(dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),snapshot=name))
    root=Path(__file__).resolve().parent.parent
    baseline=root/'test/section65/build/squashfs/refinement-baseline-audit-02'
    shutil.copy2(baseline/'heap-pilot.tex',out/'filesystem-refinement-heap.tex')
    metadata_path=root/'test/evaluation-local/runs/iso9660/squash-refine-metadata-work-01/result.json'
    metadata=json.loads(metadata_path.read_text());assert metadata['status']=='complete'
    lines=[r'\begin{table}[h]\centering\small',r'\caption{Separate mount-and-scan diagnostic. Decoder API work includes mount startup; all three replays agree. Instrumented time is not used.}',r'\begin{tabular}{lrrr}\toprule Backend & Decoder calls & Input bytes & Decoded bytes'+ROW+r'\midrule']
    for variant,api in [('stock','buffer_library'),('stock-single','buffer_library'),('copied','common'),('copied-library','stream_library')]:
        observed=[r['counts'][api] for r in metadata['cases'] if r['variant']==variant];assert len(observed)==3 and all(x==observed[0] for x in observed)
        r=observed[0];lines.append(f"{LABELS[variant]} & {r['calls']} & {r['input']:,} & {r['output']:,}"+ROW)
    lines+=[r'\bottomrule\end{tabular}\end{table}'];(out/'filesystem-refinement-work.tex').write_text('\n'.join(lines)+'\n')
    hardening_path=root/'test/evaluation-local/runs/iso9660/squash-refine-hardening-02/result.json'
    hardening=json.loads(hardening_path.read_text());assert hardening['status']=='complete'
    lines=[r'\begin{table}[h]\centering\small',r'\caption{Actual object-code audit. The PIC probe is a build-only feasibility check with an explicit GS canary convention; it is not a runnable hardened VKSO configuration.}',r'\begin{tabular}{lrrr}\toprule Object configuration & GS canary & Indirect thunks & Return thunks'+ROW+r'\midrule']
    for name,label in [('optimized-native-normal','Optimized normal native'),('optimized-native-relaxed','Optimized relaxed native'),('prepared-filesystem','Final prepared filesystem'),('pic-hardened-build-only','PIC hardened build-only probe')]:
        functions=hardening['objects'][name]['functions']
        values=['yes' if any(r[k] for r in functions) else 'no' for k in ['gs_canary_instructions','indirect_thunk_relocations','return_thunk_relocations']]
        lines.append(label+' & '+' & '.join(values)+ROW)
    lines += [r'\bottomrule\end{tabular}\end{table}'];(out/'filesystem-refinement-hardening.tex').write_text('\n'.join(lines)+'\n')
    for path,name in [(baseline/'result.json','source-refinement-baselines.json'),(metadata_path,'source-refinement-work.json'),(hardening_path,'source-refinement-hardening.json')]:
        shutil.copy2(path,out/name);sources.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),snapshot=name))
    (out/'provenance.json').write_text(json.dumps(dict(status='complete',sources=sources,plotting_script=str(Path(__file__).resolve()),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),observations=data['observations']),indent=2)+'\n')
    print('rendered final-owner figures and complete tables')


if __name__=='__main__':main()
