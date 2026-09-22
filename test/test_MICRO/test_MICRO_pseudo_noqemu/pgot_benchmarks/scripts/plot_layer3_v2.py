#!/usr/bin/env python3
"""Two-panel PGOT ablation plot, from outer-run estimates only."""
import argparse
import csv
import shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from layer3_v2 import ROUTINES, BUILDS, VARIANTS, dump, sha

p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);a=p.parse_args()
rows=list(csv.DictReader((a.analysis/'ablation.csv').open()))
outer=list(csv.DictReader((a.analysis/'outer-runs.csv').open()))
lookup={(r['routine'],r['build'],r['variant']):r for r in rows}
assert len(rows)==20
out=a.analysis/'figures';out.mkdir(exist_ok=True)
(out/'visual-contract.md').write_text('''# Visual contract
Artifact: two-panel ablation bar chart for a double-column systems paper.
Question: how do data and helper adaptation appear in the complete routine?
Panels: no retpoline; inline retpoline. Within-build Origin is the zero baseline.
Source: ../ablation.csv and ../outer-runs.csv, regenerated from raw measurements.
Bars: median of module-load overhead estimates. SHA has Data only; missing bars
are inapplicable, never numerical zeros. Gray fills and hatches encode variants.
Uncertainty: confirmatory 95% percentile bootstrap over 8 module loads; archive
range of its 3 module-load estimates. Dots retain every outer-run estimate,
including the BCH outlier. No truncation, decorative images, or external assets.
Outputs: vector PDF, 300 dpi PNG, exact bar and dot CSVs, Python source.
Manuscript placement: standalone artifact; paper prose is not edited.
''')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':9,'axes.labelsize':9,
                     'legend.fontsize':8,'pdf.fonttype':42,'ps.fonttype':42,'hatch.linewidth':.5})
fig,axes=plt.subplots(1,2,figsize=(7.1,3.3),sharey=True)
colors=['white','.75','.4'];hatches=['///','...',''];labels=['Data-PGOT','Func-PGOT','All-PGOT']
xlabels=['SHA-256\ntransform','BCH\nencode','zlib\ndeflate','Zstd\ndecompress']
for ax,build,title in zip(axes,BUILDS,['(a) No retpoline','(b) Retpoline']):
    for x,name in enumerate(ROUTINES):
        vs=('data_pgot',) if name.startswith('01') else VARIANTS
        for v in vs:
            j=VARIANTS.index(v);px=x if len(vs)==1 else x+(j-1)*.24
            r=lookup[name,build,v];y=float(r['overhead_pct'])
            lo=float(r.get('ci_low_pct',r['run_min_pct']));hi=float(r.get('ci_high_pct',r['run_max_pct']))
            ax.bar(px,y,width=.22,color=colors[j],edgecolor='black',linewidth=.65,hatch=hatches[j],zorder=2)
            ax.errorbar(px,y,yerr=[[y-lo],[hi-y]],fmt='none',ecolor='black',elinewidth=.8,capsize=2,zorder=4)
            points=sorted((o for o in outer if (o['routine'],o['build'],o['variant'])==(name,build,v)),key=lambda o:int(o['run_id']))
            offsets=[(i-(len(points)-1)/2)*.017 for i in range(len(points))]
            ax.scatter([px+t for t in offsets],[float(o['overhead_pct']) for o in points],s=7,
                       facecolors='white',edgecolors='black',linewidths=.45,zorder=3)
    ax.axhline(0,color='black',linewidth=.75,zorder=1)
    ax.set_xticks(range(4),xlabels);ax.set_xlim(-.45,3.45);ax.set_title(title,pad=8)
    ax.spines[['top','right']].set_visible(False)
    ax.tick_params(axis='both',length=3)
    ax.grid(axis='y',linewidth=.3,color='.83',zorder=0)
axes[0].set_ylabel('Overhead relative to Origin (%)')
fig.legend(handles=[Patch(facecolor=c,edgecolor='black',hatch=h,label=l) for c,h,l in zip(colors,hatches,labels)],
           loc='upper center',bbox_to_anchor=(.53,1.005),ncol=3,frameon=False)
ci='ci_low_pct' in rows[0]
fig.text(.53,.02,'Dots: module loads. Error bars: '+('95% bootstrap CI (8 loads).' if ci else 'range (3 loads).'),ha='center',fontsize=7)
fig.subplots_adjust(left=.085,right=.99,bottom=.20,top=.81,wspace=.12)
for ext in ['pdf','png']:fig.savefig(out/f'ablation.{ext}',dpi=300)
shutil.copy2(a.analysis/'ablation.csv',out/'plot-data.csv')
shutil.copy2(a.analysis/'outer-runs.csv',out/'plot-outer-runs.csv')
shutil.copy2(__file__,out/'plot_layer3_v2.py')
dump(out/'manifest.json',dict(source_sha256=sha(a.analysis/'ablation.csv'),outer_sha256=sha(a.analysis/'outer-runs.csv'),
                             bars=20,outer_points=len(outer),size_inches=[7.1,3.3],sha256_func_all='not applicable; omitted'))
print(out/'ablation.pdf')
