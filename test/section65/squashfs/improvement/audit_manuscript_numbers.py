#!/usr/bin/env python3
"""Check selected hand-written manuscript numbers against analyzed observations."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['analysis','xz-attribution','section','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--loader-control',type=Path)
    p.add_argument('--single-cpu',type=Path)
    a=p.parse_args();data=json.loads((a.analysis/'analysis.json').read_text())
    resources=json.loads((a.analysis/'resources.json').read_text())
    xz=json.loads(a.xz_attribution.read_text());prose=a.section.read_text();checks=[]
    def rows(source=data,**keys):return [r for r in source['results'] if all(r.get(k)==v for k,v in keys.items())]
    def change(r):return 100*(r['time_ratio']-1)
    def reductions(selected):return [-change(r) for r in selected]
    def bounds(values):return [min(values),max(values)]
    def check(name,actual,reported,digits,anchor):
        assert anchor in prose,(name,'missing prose anchor',anchor)
        assert len(actual)==len(reported) and all(abs(x-y)<=.5*10**(-digits)+1e-9 for x,y in zip(actual,reported)),(name,actual,reported)
        checks.append(dict(name=name,actual=actual,reported=reported,decimal_places=digits,prose_anchor=anchor))
    fresh=dict(kind='native',phase='fresh-mount')
    check('previous prepared scan overhead',bounds([change(r) for r in rows(**fresh,workload='scan',baseline='original',treatment='prepared-before')]),[3.00,4.14],2,'3.00--4.14')
    check('composed scan improvement',bounds(reductions(rows(**fresh,workload='scan',baseline='prepared-before',treatment='prepared-composed'))),[3.57,4.94],2,'3.57--4.94')
    check('composed/original scan',bounds([change(r) for r in rows(**fresh,workload='scan',baseline='original',treatment='prepared-composed')]),[-1.67,-.65],2,'$-1.67$')
    check('composed/original archive',bounds([change(r) for r in rows(**fresh,workload='archive',baseline='original',treatment='prepared-composed')]),[-1.05,-.26],2,'$-1.05$')
    for variant,expected,anchor in [('original',[60.9,77.9],'60.9--77.9'),('prepared-composed',[60.1,77.5],'60.1--77.5')]:
        selected=[r for r in data['absolute'] if r['kind']=='native' and r['phase']=='fresh-mount' and r['workload']=='scan' and r['variant']==variant]
        check(variant+' absolute scan',bounds([r['mean_campaign_median_seconds']*1000 for r in selected]),expected,1,anchor)
    selected=[r for r in rows(kind='application',baseline='copied',treatment='vkso') if r['workload']!='startup']
    check('primary sharing points',bounds([r['time_ratio'] for r in selected]),[.9964,1.0030],4,'0.9964 to 1.0030')
    check('primary sharing interval union',bounds([x for r in selected for x in r['ratio_ci95']]),[.9420,1.0680],4,'0.9420--1.0680')
    for task,expected,anchor in [('archive',[5.73,23.21,3.36],'5.73'),('scan',[6.35,55.45,4.97],'55.45')]:
        selected=[rows(kind='application',codec=c,workload=task,baseline='stock',treatment='vkso')[0] for c in ['gzip','xz','lz4']]
        check('stock '+task+' reductions',reductions(selected),expected,2,anchor)
    check('matched LKL reduction range',bounds(reductions(rows(kind='application',baseline='lkl-cache-512',treatment='vkso'))),[11.78,37.32],2,'11.78--37.32')
    for task,expected,anchor in [('archive',[31.83,45.17],'31.83--45.17'),('scan',[39.13,68.40],'39.13--68.40')]:
        check('LKL cache '+task,bounds(reductions(rows(kind='application',workload=task,baseline='lkl-512',treatment='lkl-cache-512'))),expected,2,anchor)
    for task,expected,anchor in [('archive',[.90,1.53],'0.90--1.53'),('scan',[1.30,2.19],'1.30--2.19')]:
        check('complete/old '+task,bounds(reductions(rows(kind='application',workload=task,baseline='copied-old',treatment='copied'))),expected,2,anchor)
    for source,b,t,expected,anchor in [(data,'copied-old','copied',[3.49,2.71,4.27],'3.49'),(xz,'copied-library','copied',[4.15,3.42,4.89],'4.15')]:
        r=rows(source,kind='application',codec='xz',workload='stream',baseline=b,treatment=t)[0]
        check('xz '+b+'/'+t+' regression',[change(r),*[100*(v-1) for v in r['ratio_ci95']]],expected,2,anchor)
    r=rows(xz,kind='application',codec='xz',workload='stream',baseline='copied',treatment='vkso')[0]
    check('additional xz backing difference',[-change(r),*[100*(1-v) for v in reversed(r['ratio_ci95'])]],[4.68,1.36,7.89],2,'4.68')
    selected=rows(kind='native-stream',phase='fresh-mount',baseline='original',treatment='prepared-composed')
    check('native stream points',bounds([change(r) for r in selected]),[-.45,.60],2,'$+0.60$')
    check('native stream interval union',bounds([100*(x-1) for r in selected for x in r['ratio_ci95']]),[-1.86,2.95],2,'$+2.95$')
    for variant,expected,anchor in [('vkso',[7.00,7.37],'7.00--7.37'),('stock',[14.42,23.93],'14.42--23.93'),('lkl-cache-512',[82.58,82.77],'82.58--82.77')]:
        values=[r['median']/1024 for r in resources['summaries'] if r['variant']==variant and r['phase']=='after' and r['metric']=='pss_kib']
        check(variant+' PSS range',bounds(values),expected,2,anchor)
    for key,expected,anchor in [('setup_command_sum_seconds',[2.612,2.562,2.695],'2.612'),('teardown_command_sum_seconds',[.161,.145,.162],'0.161'),('export_construction_seconds',[2.432,2.432,2.485],'2.432')]:
        r=resources['deployment_summary'][key];check(key,[r[k] for k in ['median','minimum','maximum']],expected,3,anchor)
    sources=[a.analysis/'analysis.json',a.analysis/'resources.json',a.xz_attribution,a.section]
    business_path=a.analysis/'business-costs.json'
    if business_path.exists():
        business=json.loads(business_path.read_text());sources.append(business_path)
        assert business['platform']['charged_to_business_bytes']==0
        r=business['timing']['core_export_registration']
        check('business core export and registration',[r[k] for k in ['median','minimum','maximum']],
              [2.596,2.545,2.646],3,'2.596')
        b=business['business']
        for key,value,anchor in [('native_preparation_delta_bytes',36864,'36~KiB'),
                                 ('shared_backing_avoided_once_bytes',28672,'28~KiB'),
                                 ('registration_requested_bytes',1136,'1,136')]:
            check(key,[b[key]],[value],0,anchor)
    if a.loader_control:
        controlled=json.loads(a.loader_control.read_text());sources.append(a.loader_control)
        r=rows(controlled,kind='application',codec='xz',workload='stream',baseline='copied',treatment='vkso')[0]
        check('equal-path xz sharing',[r['time_ratio'],*r['ratio_ci95']],[1.0021,.9905,1.0138],4,'1.0021 [0.9905, 1.0138]')
        for codec,reported,anchor in [('xz',[4.00,3.34,4.67],'4.00'),('lz4',[.60,-.38,1.59],'$+1.59$')]:
            r=rows(controlled,kind='application',codec=codec,workload='stream',baseline='copied-library',treatment='copied')[0]
            check('equal-path '+codec+' decoder build',[change(r),*[100*(v-1) for v in r['ratio_ci95']]],reported,2,anchor)
    if a.single_cpu:
        single=json.loads(a.single_cpu.read_text());sources.append(a.single_cpu)
        selected=[r for r in rows(single,kind='application',baseline='copied',treatment='vkso') if r['workload']!='startup']
        check('single-CPU nonempty backing points',bounds([r['time_ratio'] for r in selected]),[.9927,1.0062],4,'0.9927 to 1.0062')
        check('single-CPU nonempty interval union',bounds([x for r in selected for x in r['ratio_ci95']]),[.9684,1.0308],4,'0.9684--1.0308')
        selected=[r for r in rows(single,kind='application',baseline='copied-old',treatment='copied') if r['workload'] in ['scan','archive']]
        check('single-CPU metadata adapter reduction',bounds(reductions(selected)),[.77,2.93],2,'0.77')
        assert sum(r['ratio_ci95'][1]<1 for r in selected)==5
        for codec,reported,anchor in [('xz',[4.92,3.87,5.98],'4.92'),('lz4',[.58,-.38,1.56],'$+1.56$')]:
            r=rows(single,kind='application',codec=codec,workload='stream',baseline='copied-library',treatment='copied')[0]
            check('single-CPU '+codec+' decoder build',[change(r),*[100*(v-1) for v in r['ratio_ci95']]],reported,2,anchor)
    result=dict(status='complete',scope='Selected hand-written timing and resource numbers, with rounding and prose anchors. Other mechanism/functional quantities are covered by their evidence audits.',checks=checks,
                sources=[dict(path=str(s.resolve()),sha256=hashlib.sha256(s.read_bytes()).hexdigest()) for s in sources])
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('checked',len(checks),'manuscript numeric claims')


if __name__=='__main__':main()
