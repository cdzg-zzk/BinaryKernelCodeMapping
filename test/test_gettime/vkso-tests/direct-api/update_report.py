#!/usr/bin/env python3
"""Evidence-bound UPDATE tables, boot distributions and decomposition figures."""
import argparse
from collections import defaultdict
import math
import numpy as np
import cairosvg
from read_evaluation import rows
from read_report import Canvas
from update_evaluation import OUT, VARIANTS, SCENARIOS

LABEL={'normal':'Retpoline','no-retpoline':'No-retpoline','idle':'Idle','monotonic':'Monotonic','monotonic_raw':'Monotonic raw','monotonic_coarse':'Monotonic coarse'}
COL={'raw':'#666666','vkso':'#0072B2'}

def f(x,k):return float(x[k])
def num(x,s=False):return f'{float(x):+.3f}' if s else f'{float(x):.3f}'
def rect(c,x,y,w,h,col):c.parts.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" fill="{col}"/>')
def line(c,pts,col,width=1,opacity=1):c.parts.append('<polyline fill="none" stroke="'+col+f'" stroke-width="{width}" opacity="{opacity}" points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in pts)+'"/>')

def forest(summary,parts):
    c=Canvas(1040,640);left=285;right=990;top=110;step=56;lo=-16;hi=16
    xx=lambda x:left+(x-lo)/(hi-lo)*(right-left)
    c.text(20,28,'Periodic UPDATE function: VKSO − Raw',19,weight=600)
    c.text(20,53,'Instrumented function-internal interval; all samples retained',13)
    c.text(left,82,'Filled: mean difference + 95% CI; hollow: four block differences',12)
    for t in range(-16,17,4):
        c.line(xx(t),96,xx(t),554,'#888' if t==0 else '#ddd');c.text(xx(t),577,str(t),12,'middle')
    for i,x in enumerate(summary):
        y=top+i*step;col='#0072B2' if x['variant']=='normal' else '#D55E00';sq=x['variant']!='normal'
        c.text(left-15,y+4,LABEL[x['variant']]+' / '+LABEL[x['scenario']],13,'end')
        a,b,d=[f(x,k) for k in ['delta_ci95_low','delta_ci95_high','delta']]
        c.line(xx(a),y,xx(b),y,col,2)
        for z in [a,b]:c.line(xx(z),y-4,xx(z),y+4,col)
        c.marker(xx(d),y,col,sq)
        for p in parts:
            if (p['variant'],p['scenario'])==(x['variant'],x['scenario']):
                assert lo<=f(p,'delta')<=hi;c.marker(xx(f(p,'delta')),y+12,col,sq,2.3,False)
    c.text((left+right)/2,612,'VKSO − Raw (TSC ticks/update)',14,'middle')
    return c.svg()

def loadplot(loads,loadblocks):
    c=Canvas(1040,530);left=305;right=990;lo=-5;hi=25;xx=lambda x:left+(x-lo)/(hi-lo)*(right-left)
    c.text(20,28,'UPDATE function cost under a concurrent reader',19,weight=600)
    c.text(20,53,'Loaded mean − idle mean within each boot; filled = four-boot mean, hollow = boots',12)
    for m,x in [('raw',left),('vkso',left+145)]:c.marker(x,80,COL[m],m=='vkso');c.text(x+12,85,m.upper() if m=='vkso' else 'Raw',13)
    for t in range(lo,hi+1,5):c.line(xx(t),96,xx(t),430,'#888' if t==0 else '#ddd');c.text(xx(t),451,str(t),12,'middle')
    for i,s in enumerate(loads):
        y=110+i*52;c.text(left-15,y+10,LABEL[s['variant']]+' / '+LABEL[s['scenario']],13,'end')
        for j,m in enumerate(['raw','vkso']):
            yy=y+j*20;c.marker(xx(f(s,m+'_load_minus_idle')),yy,COL[m],m=='vkso')
            for b in loadblocks:
                if (b['variant'],b['scenario'])==(s['variant'],s['scenario']):
                    val=f(b,m+'_load_minus_idle');assert lo<=val<=hi
                    c.marker(xx(val),yy+7,COL[m],m=='vkso',2.3,False)
    c.text((left+right)/2,485,'Loaded − idle (TSC ticks/update)',14,'middle')
    c.text(left,511,'One public API reader on CPU 2; fixed-duration writer windows',12)
    return c.svg()

def decomposition(summary):
    c=Canvas(1080,565);left=85;right=1040;top=95;bottom=450;low=-20;high=20
    yy=lambda v:bottom-(v-low)/(high-low)*(bottom-top)
    c.text(20,28,'Exact decomposition of the complete mean difference',19,weight=600)
    keys=['low_contribution','high_capped_contribution','occupancy_contribution','tail_contribution']
    names=['Low-side cost','Capped high-side cost','Occupancy','Tail excess (>300)']
    colors=['#0072B2','#CC79A7','#E69F00','#009E73']
    for i,(name,col) in enumerate(zip(names,colors)):
        x=45+i*260;rect(c,x,49,10,10,col);c.text(x+16,59,name,12)
    c.text(85,81,'Bars sum to black total marker; per-block identity, then equal boot weighting',12)
    for t in range(low,high+1,5):c.line(left,yy(t),right,yy(t),'#777' if t==0 else '#ddd');c.text(left-12,yy(t)+4,str(t),12,'end')
    for i,s in enumerate(summary):
        x=left+60+i*118
        for j,(k,col) in enumerate(zip(keys,colors)):
            v=f(s,k);assert low<=v<=high
            rect(c,x-35+j*18,min(yy(v),yy(0)),14,abs(yy(v)-yy(0)),col)
        c.marker(x,yy(f(s,'delta')),'#111',True,r=4)
        short={'idle':'Idle','monotonic':'Mono','monotonic_raw':'Raw','monotonic_coarse':'Coarse'}
        c.text(x,477,short[s['scenario']],12,'middle')
    c.text(320,509,'Retpoline',15,'middle',600);c.text(790,509,'No-retpoline',15,'middle',600)
    c.text(85,541,'Contribution to VKSO − Raw (TSC ticks/update)',13)
    return c.svg()

def distribution(var,hist,cdfs):
    c=Canvas(1080,1065);c.text(20,27,LABEL[var]+': periodic UPDATE function distributions',19,weight=600)
    c.text(20,53,'Thin curves: individual boots; thick density: equal-boot average. Every sample enters denominators.',12)
    for m,x in [('raw',700),('vkso',860)]:c.line(x,75,x+25,75,COL[m],2);c.text(x+32,80,'Raw' if m=='raw' else 'VKSO',13)
    for i,sc in enumerate(SCENARIOS):
        top=115+i*235;bottom=top+150
        hs=[x for x in hist if x['variant']==var and x['scenario']==sc]
        cs=[x for x in cdfs if x['variant']==var and x['scenario']==sc]
        for panel in [0,1]:
            left=80+panel*535;right=505+panel*535
            if panel==0:
                lo,hi=60,300;maxy=max(f(x,'smooth_probability')*100 for x in hs)*1.08
                xx=lambda z:left+(z-lo)/(hi-lo)*(right-left);yy=lambda z:bottom-z/maxy*(bottom-top)
                for t in [60,100,140,180,220,260,300]:c.text(xx(t),bottom+20,str(t),11,'middle')
                for t in np.linspace(0,maxy,4):c.line(left,yy(t),right,yy(t));c.text(left-8,yy(t)+4,f'{t:.1f}',11,'end')
                for m in ['raw','vkso']:
                    per=[]
                    for b in range(1,5):
                        z=sorted([x for x in hs if x['backend']==m and int(x['block'])==b and int(x['ticks'])>=60],key=lambda x:int(x['ticks']))
                        per.append([f(x,'smooth_probability')*100 for x in z]);line(c,[(xx(int(x['ticks'])),yy(f(x,'smooth_probability')*100)) for x in z],COL[m],.7,.3)
                    line(c,[(xx(t),yy(y)) for t,y in zip(range(60,301),np.mean(per,axis=0))],COL[m],2)
                c.text(left,top-13,LABEL[sc]+': density (% / tick), σ = 3',12,weight=600)
            else:
                lo=60;hi=max(f(x,'ticks') for x in cs);loglo,loghi=math.log10(lo),math.log10(hi)
                xx=lambda z:left+(math.log10(z)-loglo)/(loghi-loglo)*(right-left);yy=lambda z:bottom-z*(bottom-top)
                for t in [100,1000,10000,100000]:
                    if t<=hi:c.text(xx(t),bottom+20,str(t),11,'middle')
                for t in [0,.25,.5,.75,1]:c.line(left,yy(t),right,yy(t));c.text(left-8,yy(t)+4,f'{t:g}',11,'end')
                for m in ['raw','vkso']:
                    for b in range(1,5):
                        z=sorted([x for x in cs if x['backend']==m and int(x['block'])==b],key=lambda x:int(x['ticks']))
                        line(c,[(xx(f(x,'ticks')),yy(f(x,'cdf'))) for x in z],COL[m],1,.6)
                c.text(left,top-13,'Full-range CDF (log x-axis)',12)
            c.line(left,bottom,right,bottom,'#777')
            c.text((left+right)/2,bottom+41,'TSC ticks/update',12,'middle')
    return c.svg()

def produce():
    ss=rows(OUT/'summary.csv');gg=rows(OUT/'groups.csv');bs=rows(OUT/'boots.csv');ps=rows(OUT/'decomposition-blocks.csv')
    loads=rows(OUT/'load-response.csv');lbs=rows(OUT/'load-response-blocks.csv');hist=rows(OUT/'histograms.csv');cdfs=rows(OUT/'cdfs.csv')
    md=['# UPDATE 函数内成本与分布分解','','单位为 TSC ticks/update；计时限于 timekeeping_update 函数内部，不含调用者的正式 timekeeper 复制与序列提交。全部周期 action=0 样本保留。主成本先求启动内完整均值，再等权平均四个启动。区间按四个匹配启动块重采样，逐项报告。','','## 完整均值','','| 配置 | 读取负载 | Raw | VKSO | Δ | Δ% | 95% CI | VKSO 更快块数 |','| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |']
    for s in ss:md.append(f"| {LABEL[s['variant']]} | {s['scenario']} | {num(s['raw_mean'])} | {num(s['vkso_mean'])} | {num(s['delta'],True)} | {num(s['delta_percent'],True)} | [{num(s['delta_ci95_low'],True)}, {num(s['delta_ci95_high'],True)}] | {s['faster_blocks']}/4 |")
    md+=['','## 均值差的四项分解','','尾部界为 300 ticks。前三项作用于 min(x,300)，最后一项为 E[(x−300)+] 的后端差；四项合计精确还原完整均值差。','','| 配置 | 负载 | 低侧成本 | 截顶高侧成本 | 占比 | 超额尾部 | 合计 |','| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for s in ss:md.append('| '+LABEL[s['variant']]+' | '+s['scenario']+' | '+' | '.join(num(s[k],True) for k in ['low_contribution','high_capped_contribution','occupancy_contribution','tail_contribution','delta'])+' |')
    md+=['','## 读取负载相对 idle 的成本变化','','| 配置 | 负载 | Raw 变化 | VKSO 变化 | 两变化之差 | 95% CI | 变化差为负块数 |','| --- | --- | ---: | ---: | ---: | --- | ---: |']
    for s in loads:md.append('| '+LABEL[s['variant']]+' | '+s['scenario']+' | '+' | '.join(num(s[k],True) for k in ['raw_load_minus_idle','vkso_load_minus_idle','difference_in_differences'])+f" | [{num(s['ci95_low'],True)}, {num(s['ci95_high'],True)}] | {s['negative_blocks']}/4 |")
    md+=['','## 条件成本、占比与尾部','','各条件统计先在启动内计算，再等权平均。低/高侧按各自分布谷值划分；p95/p99 是启动内单次 UPDATE 分位数的平均。','','| 配置/后端 | 负载 | 谷值 | 低/高峰 | 低侧均值 | 高侧均值 | 高侧% | >300% | 超额尾部 | p95 | p99 |','| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for g in gg:md.append(f"| {LABEL[g['variant']]}/{g['backend']} | {g['scenario']} | {g['cut']} | {g['low_mode']}/{g['high_mode']} | {num(g['low_mean'])} | {num(g['high_mean'])} | {100*f(g,'high_fraction'):.2f} | {100*f(g,'tail_fraction'):.3f} | {num(g['tail_excess'])} | {num(g['p95'])} | {num(g['p99'])} |")
    appendix=['# 逐启动结果','','函数内计时区间；每行四个数按启动块 1→4 排列，表内不混入诊断复测。','','| 配置/后端 | 负载 | 完整均值 | 高侧占比% | 超额尾部 |','| --- | --- | --- | --- | --- |']
    for g in gg:
        z=sorted([x for x in bs if (x['variant'],x['backend'],x['scenario'])==(g['variant'],g['backend'],g['scenario'])],key=lambda x:int(x['block']))
        appendix.append('| '+LABEL[g['variant']]+'/'+g['backend']+' | '+g['scenario']+' | '+', '.join(num(x['mean']) for x in z)+' | '+', '.join(f"{100*f(x,'high_fraction'):.2f}" for x in z)+' | '+', '.join(num(x['tail_excess']) for x in z)+' |')
    output={'tables.md':'\n'.join(md)+'\n','boot-results.md':'\n'.join(appendix)+'\n',
            'update-mean.svg':forest(ss,ps),'update-load-response.svg':loadplot(loads,lbs),'update-decomposition.svg':decomposition(ss)}
    for v in VARIANTS:output['update-distribution-'+v+'.svg']=distribution(v,hist,cdfs)
    for v in VARIANTS:
        tex=[r'\begin{tabular}{lrrrrl}',r'\toprule',r'Load & Raw & VKSO & $\Delta$ & $\Delta\%$ & 95\% CI \\',r'\midrule']
        for s in [s for s in ss if s['variant']==v]:tex.append(LABEL[s['scenario']]+' & '+' & '.join(num(s[k],k in ['delta','delta_percent']) for k in ['raw_mean','vkso_mean','delta','delta_percent'])+f" & [{num(s['delta_ci95_low'],True)}, {num(s['delta_ci95_high'],True)}] "+r'\\')
        output['table-update-'+v+'.tex']='\n'.join(tex+[r'\bottomrule',r'\end{tabular}'])+'\n'
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
    print('UPDATE tables and five vector figures: PASS')
