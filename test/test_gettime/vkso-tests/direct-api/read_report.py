#!/usr/bin/env python3
"""Create deterministic READ tables and vector interval plots from summary.csv."""
import argparse
from html import escape
import json
import math
from pathlib import Path
import cairosvg
from read_evaluation import OUT, CASE_NAMES, KERNEL_APIS, VARIANTS, rows

LABELS={
 'clock_gettime_realtime':'CLOCK_REALTIME','clock_gettime_monotonic':'CLOCK_MONOTONIC',
 'clock_gettime_monotonic_raw':'CLOCK_MONOTONIC_RAW','clock_gettime_boottime':'CLOCK_BOOTTIME',
 'clock_gettime_tai':'CLOCK_TAI','clock_gettime_realtime_coarse':'CLOCK_REALTIME_COARSE',
 'clock_gettime_monotonic_coarse':'CLOCK_MONOTONIC_COARSE',
 'clock_getres_realtime':'clock_getres(REALTIME)','clock_getres_realtime_coarse':'clock_getres(REALTIME_COARSE)',
 'gettimeofday_tv':'gettimeofday(tv, NULL)','time_null':'time(NULL)','time_pointer':'time(&seconds)',
 'getcpu_both':'getcpu(cpu, node)',
 'clock_gettime_process_cpu_fallback':'clock_gettime(PROCESS_CPUTIME)',
 'clock_getres_process_cpu_fallback':'clock_getres(PROCESS_CPUTIME)',
 'clock_gettime_realtime_alarm_fallback':'clock_gettime(REALTIME_ALARM)',
 'monotonic':'ktime_get_ts64','monotonic_raw':'ktime_get_raw_ts64','monotonic_coarse':'ktime_get_coarse_ts64'}
DISPLAY={'normal':'Retpoline','no-retpoline':'No-retpoline'}


def number(v,signed=False): return f'{float(v):+.3f}' if signed else f'{float(v):.3f}'


# Minimal standard-library SVG canvas, using the CCFA recipe canvas grammar.
# Data positions use linear numerical scales; no rasterized plots or hand-placed values.
class Canvas:
    def __init__(self,w,h):
        self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                    '<style>text{font-family:DejaVu Sans,sans-serif;fill:#222}</style>',f'<rect width="{w}" height="{h}" fill="white"/>']
    def text(self,x,y,s,size=13,anchor='start',weight=400):
        self.parts.append(f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}">{escape(str(s))}</text>')
    def line(self,x1,y1,x2,y2,color='#ddd',width=1):
        self.parts.append(f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" stroke="{color}" stroke-width="{width}"/>')
    def marker(self,x,y,color,square=False,r=4,filled=True):
        fill=color if filled else 'white'
        if square:self.parts.append(f'<rect x="{x-r:.3f}" y="{y-r:.3f}" width="{2*r}" height="{2*r}" fill="{fill}" stroke="{color}"/>')
        else:self.parts.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r}" fill="{fill}" stroke="{color}"/>')
    def svg(self):return '\n'.join(self.parts+['</svg>\n'])


def plot(table,blocks,names,title):
    # Wide layout retains real API names; common axes compare configurations.
    w=1080; top=100; step=58; bottom=top+len(names)*step; h=bottom+88
    c=Canvas(w,h); left=335; right=1028
    chosen=[x for x in table if (x['domain'],x['api']) in names]
    extremes=[float(x[k]) for x in chosen for k in ['delta_ci95_low','delta_ci95_high','block_delta_min','block_delta_max']]+[0.]
    lo,hi=min(extremes),max(extremes)
    grid=1 if hi-lo<10 else (2 if hi-lo<20 else 10)
    lo=math.floor((lo-.12*grid)/grid)*grid;hi=math.ceil((hi+.12*grid)/grid)*grid
    def scale(v):
        assert lo<=v<=hi,(v,lo,hi)
        return left+(v-lo)/(hi-lo)*(right-left)
    c.text(20,27,title,18,weight=600)
    for j,var in enumerate(VARIANTS):
        col=['#0072B2','#D55E00'][j]; x=left+j*220
        c.marker(x,54,col,j==1);c.text(x+12,59,DISPLAY[var],13)
    c.text(left,80,'Filled: median difference + 95% CI; hollow: four block differences',12)
    for t in range(int(lo),int(hi)+1,grid):
        c.line(scale(t),top-8,scale(t),bottom-12,'#888' if t==0 else '#ddd',1.5 if t==0 else 1)
        c.text(scale(t),bottom+10,f'{t:+d}' if t else '0',12,'middle')
    lookup={(x['variant'],x['domain'],x['api']):x for x in chosen}
    for i,(domain,api) in enumerate(names):
        y=top+i*step
        c.text(left-15,y+14,LABELS[api],12,'end')
        if api=='monotonic': c.line(20,y-15,right,y-15,'#aaa')
        for j,var in enumerate(VARIANTS):
            row=lookup[var,domain,api];yy=y+j*24;col=['#0072B2','#D55E00'][j]
            a,b,d=[float(row[k]) for k in ['delta_ci95_low','delta_ci95_high','delta_ticks']]
            c.line(scale(a),yy,scale(b),yy,col,2)
            for z in (a,b):c.line(scale(z),yy-3,scale(z),yy+3,col,1.2)
            c.marker(scale(d),yy,col,j==1)
            pts=[float(x['delta_ticks']) for x in blocks if x['variant']==var and x['domain']==domain and x['api']==api]
            assert len(pts)==4
            for z in pts:c.marker(scale(z),yy+8,col,j==1,r=2.2,filled=False)
    c.text((left+right)/2,bottom+36,'VKSO − Raw (TSC ticks/call)',14,'middle')
    c.text(left,bottom+61,'← Lower cost with VKSO',12)
    c.text(right,bottom+61,'Higher cost with VKSO →',12,'end')
    return c.svg()


def produce():
    table=rows(OUT/'summary.csv'); blocks=rows(OUT/'block-deltas.csv')
    groups=[('main','clock_gettime and ordinary kernel READ', [('user',x) for x in CASE_NAMES[:7]]+[('kernel',x) for x in KERNEL_APIS]),
            ('other','Other public fast paths',[('user',x) for x in CASE_NAMES[7:13]]),
            ('fallback','Public syscall fallback paths',[('user',x) for x in CASE_NAMES[13:]])]
    output={}
    lines=['# READ 结果表','',
           '单位：TSC ticks/call。Raw/VKSO 为四次启动中位数的中位数；Δ = VKSO − Raw。区间为独立启动精确枚举 bootstrap 的逐项 95% 百分位区间。每个启动包含 31 个批次，每批 500,000 次调用。','']
    for title,domain,cat in [('用户 clock_gettime 快路径','user','clock_gettime_fast'),('其他公开时间快路径','user','other_time_fast'),('getcpu','user','getcpu'),('用户 fallback','user','fallback'),('普通内核 READ','kernel','kernel_read')]:
        lines += ['## '+title,'','| 配置 | 接口 | Raw | VKSO | Δ | Δ 95% CI | Δ% |','| --- | --- | ---: | ---: | ---: | --- | ---: |']
        sel=[x for x in table if x['domain']==domain and x['category']==cat]
        for x in sel:
            lines.append(f"| {DISPLAY[x['variant']]} | `{x['api']}` | {number(x['raw_ticks'])} | {number(x['vkso_ticks'])} | {number(x['delta_ticks'],True)} | [{number(x['delta_ci95_low'],True)}, {number(x['delta_ci95_high'],True)}] | {number(x['delta_percent'],True)} |")
        lines+=['']
    output['tables.md']='\n'.join(lines)+'\n'
    appendix=['# 启动级结果与统计敏感性','',
              '每行是一项接口和配置。r/v 是四个启动块内各后端的启动中位数；块间差区间和删一块范围使用同一中位数差统计量。均值差使用完整批次数据，先求各启动均值再等权平均。全部批次保留。','']
    for var in VARIANTS:
        appendix+=['## '+DISPLAY[var],'','| 接口 | Raw 启动中位数（块1→4） | VKSO 启动中位数（块1→4） | 配对块 CI | 删一块范围 | 完整均值差 |','| --- | --- | --- | --- | --- | ---: |']
        for x in [x for x in table if x['variant']==var]:
            bs=sorted([b for b in blocks if (b['variant'],b['domain'],b['api'])==(var,x['domain'],x['api'])],key=lambda b:int(b['block']))
            rs=', '.join(number(b['raw_ticks']) for b in bs);vs=', '.join(number(b['vkso_ticks']) for b in bs)
            appendix.append(f"| {x['domain']}: `{x['api']}` | {rs} | {vs} | [{number(x['block_ci95_low'],True)}, {number(x['block_ci95_high'],True)}] | [{number(x['leave_one_block_min'],True)}, {number(x['leave_one_block_max'],True)}] | {number(x['mean_delta'],True)} |")
        appendix+=['']
    output['boot-results.md']='\n'.join(appendix)+'\n'
    # Narrow, self-contained booktabs fragments: one table per variant / scope.
    for var in VARIANTS:
        for scope,_,names in groups:
            ls=[r'\begin{tabular}{lrrrrl}',r'\toprule',r'Interface & Raw & VKSO & $\Delta$ & $\Delta\%$ & 95\% CI \\',r'\midrule']
            for x in [x for x in table if x['variant']==var and (x['domain'],x['api']) in names]:
                label=LABELS[x['api']].replace('_',r'\_').replace('&',r'\&')
                ls.append(label+' & '+' & '.join(number(x[k],k in ['delta_ticks','delta_percent']) for k in ['raw_ticks','vkso_ticks','delta_ticks','delta_percent'])+f" & [{number(x['delta_ci95_low'],True)}, {number(x['delta_ci95_high'],True)}] "+r'\\')
            ls+=[r'\bottomrule',r'\end{tabular}']
            output[f'table-{scope}-{var}.tex']='\n'.join(ls)+'\n'
    for name,title,names in groups:output['read-'+name+'.svg']=plot(table,blocks,names,title)
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    for name,s in produce().items():
        path=OUT/name
        if a.check:assert path.read_bytes()==s.encode(),name
        else:
            path.write_bytes(s.encode())
            if name.endswith('.svg'):
                cairosvg.svg2png(bytestring=s.encode(),write_to=str(path.with_suffix('.png')))
                cairosvg.svg2pdf(bytestring=s.encode(),write_to=str(path.with_suffix('.pdf')))
    print('READ presentation: PASS; 38 rows, 6 LaTeX fragments, 3 vector figures')
