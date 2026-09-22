#!/usr/bin/env python3
"""Render the audited section 6.3 user result; ranges are load medians."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(base):
    out=base/'paper-material'
    data=list(csv.DictReader((out/'user-plot.csv').open()))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42,'ps.fonttype':42,
                         'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(7.1,2.7),gridspec_kw={'width_ratios':[1.1,1.35,0.8]})
    for ax,a,title in zip(axes,('lz4','bch','xz'),('LZ4','BCH (512 B)','XZ complete streams')):
        labels=list(dict.fromkeys(r['label'] for r in data if r['algorithm']==a))
        for b,offset,color,marker,label in [('native-dso',-.13,'#205781','o','VKSO / Native'),('adapted-dso',.13,'#BA6429','s','VKSO / Adapted')]:
            rows=[r for r in data if r['algorithm']==a and r['baseline']==b]
            x=[labels.index(r['label'])+offset for r in rows];y=[float(r['overhead_pct']) for r in rows]
            error=[[v-float(r['minimum_load_pct']) for r,v in zip(rows,y)],
                   [float(r['maximum_load_pct'])-v for r,v in zip(rows,y)]]
            ax.errorbar(x,y,yerr=error,color=color,marker=marker,linestyle='none',markersize=4,capsize=2,label=label)
        ax.axhline(0,color='#777777',linewidth=.8,zorder=0);ax.grid(axis='y',alpha=.2)
        if a=='lz4':names=[s.replace('decompress, ','D ').replace('compress, ','C ').replace(' KiB','K') for s in labels]
        elif a=='bch':names=[s.replace('t=','t').replace(', ','\n').replace('decode-full (2 errors)','Full').replace('decode-precomputed (2 errors)','Pre').replace('encode','Enc.') for s in labels]
        else:names=['bash','libc','Python']
        ax.set_xticks(range(len(labels)),names,rotation=45 if a=='lz4' else 0,ha='right' if a=='lz4' else 'center',fontsize=7)
        ax.set_title(title);ax.set_ylabel('Execution overhead (%)' if a=='lz4' else '')
        ax.margins(x=.08)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',ncol=2,frameon=False,bbox_to_anchor=(.5,1.03))
    fig.tight_layout(rect=(0,0,1,.94))
    for suffix in ('pdf','svg','png'):fig.savefig(out/('exported_algorithms.'+suffix),bbox_inches='tight',dpi=180)
    plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();plot(a.directory.resolve())
