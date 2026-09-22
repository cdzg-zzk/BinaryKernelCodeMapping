#!/usr/bin/env python3
"""Summarize the predefined repetition and the independent PMU/context crossover."""
import argparse
from collections import defaultdict
import csv,json,re,statistics as st
from pathlib import Path

def rows(p):return list(csv.DictReader(p.open()))
def write(p,data):
    with p.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def repetitions(base):
    data=[r for r in rows(base/'analysis/deployment-ratios.csv') if r['algorithm']=='bch'];group=defaultdict(list)
    for r in data:
        number=int(r['deployment'].split('-')[1]);cohort='original' if number<3 else 'additional'
        group[(r['domain'],r['workload'],r['target'],r['baseline'],cohort)].append(float(r['median_cost_ratio']))
    result=[]
    for k,v in sorted(group.items()):
        assert len(v)==(3 if k[-1]=='original' else 9)
        result.append(dict(zip(('domain','workload','target','baseline','cohort'),k),loads=len(v),median=st.median(v),minimum=min(v),maximum=max(v),q25=st.quantiles(v,n=4,method='inclusive')[0],q75=st.quantiles(v,n=4,method='inclusive')[2]))
    write(base/'repeat-bch/cohort-summary.csv',result)
    addresses=[]
    for e in json.loads((base/'plan.json').read_text())['entries']:
        if e['algorithm']!='bch':continue
        d=Path(e['directory'])
        for r in json.loads((d/'results/kernel/public-api-symbols.json').read_text()):
            addresses.append(dict(deployment=d.name,**{k:r[k] for k in ('name','address')}))
    write(base/'repeat-bch/entry-addresses.csv',addresses)
    print('Original and additional populations summarized separately.')

def pmu(base):
    out=base/'repeat-bch/pmu';observations=[];layout=[]
    backends=['stock-kernel','matched-source-kernel','owner-kernel']
    for d in sorted(p for p in out.glob('load-*') if p.is_dir()):
        for p in sorted(d.glob('phase-*')):
            audit=json.loads((p/'audit.json').read_text());assert audit['status']=='pass'
            rotation=audit['rotation'];groups=defaultdict(dict)
            for r in rows(p/'pmu.csv'):
                key=(r['backend'],int(r['t']),int(r['errors']),r['mode'],int(r['round']))
                groups[key][r['event']]=int(r['count'])/int(r['iterations'])
                groups[key]['ns']=int(r['ns'])/int(r['iterations'])
            for key,values in groups.items():
                assert set(values)=={'cycles','instructions','branch_misses','l1d_read_misses','ref_cycles','ns'}
                observations.append(dict(load=d.name,phase=p.name,rotation=rotation,context_origin=(backends.index(key[0])+rotation)%3,
                    **dict(zip(('backend','t','errors','mode','round'),key)),**values,
                    cycles_per_ref_cycle=values['cycles']/values['ref_cycles']))
            text=(p/'dmesg-window.txt').read_text()
            matches=[dict(re.findall(r'(\w+)=([^\s]+)',line)) for line in text.splitlines() if 'BCH_KERNEL_BENCH layout ' in line]
            current=matches[-6:];assert len(current)==6 and all(int(r['rotation'])==rotation for r in current)
            layout.extend(dict(load=d.name,phase=p.name,**r) for r in current)
    assert len(observations)==9504
    write(out/'observations.csv',observations);write(out/'context-addresses.csv',layout)
    # Every allocated context must visit all three code backends within its load.
    groups=defaultdict(list)
    for r in layout:groups[r['load'],r['t'],r['control']].append(r)
    assert len(groups)==18
    for k,g in groups.items():
        assert len(g)==3 and {r['backend'] for r in g}==set(backends)
        for field in ('pow','log','ecc','syn','elp','work','difference'):assert len({r[field] for r in g})==1
    groups=defaultdict(list)
    for r in observations:groups[tuple(r[k] for k in ('load','phase','rotation','context_origin','backend','t','errors','mode'))].append(r)
    summary=[];metrics=('ns','cycles','instructions','branch_misses','l1d_read_misses','ref_cycles','cycles_per_ref_cycle')
    for k,g in sorted(groups.items()):
        assert len(g)==11
        summary.append(dict(zip(('load','phase','rotation','context_origin','backend','t','errors','mode'),k),**{m:st.median(r[m] for r in g) for m in metrics}))
    write(out/'phase-summary.csv',summary)
    # Match the same context and error vector across phases rather than compare
    # unrelated allocation addresses. Preserve the individual load as the unit.
    groups=defaultdict(dict)
    for r in observations:groups[tuple(r[k] for k in ('load','context_origin','t','errors','mode','round'))][r['backend']]=r
    paired=[]
    for k,g in sorted(groups.items()):
        assert set(g)==set(backends)
        for target,baseline in [(backends[2],backends[1]),(backends[2],backends[0])]:
            paired.append(dict(zip(('load','context_origin','t','errors','mode','round'),k),target=target,baseline=baseline,
                **{m+'_ratio':g[target][m]/g[baseline][m] for m in ('ns','cycles','instructions')}))
    write(out/'same-context-pairs.csv',paired)
    (out/'analysis-audit.json').write_text(json.dumps(dict(status='pass',loads=3,phases_per_load=3,raw_workload_rows=len(observations),event_rows=len(observations)*5,contexts=18,all_contexts_visit_three_backends=True,no_counter_multiplexing=True),indent=2)+'\n')
    print('PMU and same-context crossover summarized.')

def user_pmu(base):
    out=base/'repeat-bch/user-pmu';observations=[]
    for d in sorted(p for p in out.glob('load-*') if p.is_dir()):
        assert json.loads((d/'complete.json').read_text())['status']=='pass'
        assert json.loads((d/'results/audit.json').read_text())['aligned_inputs']
        groups=defaultdict(dict)
        for r in rows(d/'results/pmu.csv'):
            k=(r['backend'],int(r['t']),int(r['errors']),r['mode'],int(r['round']))
            groups[k][r['event']]=int(r['count'])/int(r['iterations'])
            groups[k]['ns']=int(r['ns'])/int(r['iterations'])
        for k,v in groups.items():
            observations.append(dict(load=d.name,**dict(zip(('backend','t','errors','mode','round'),k)),**v))
    assert len(observations)==3168
    write(out/'observations.csv',observations);groups=defaultdict(list)
    for r in observations:groups[tuple(r[k] for k in ('load','backend','t','errors','mode'))].append(r)
    summary=[]
    for k,g in sorted(groups.items()):
        assert len(g)==11
        summary.append(dict(zip(('load','backend','t','errors','mode'),k),**{m:st.median(r[m] for r in g) for m in ('ns','cycles','instructions','branch_misses','l1d_read_misses','ref_cycles')}))
    write(out/'load-summary.csv',summary)
    (out/'analysis-audit.json').write_text(json.dumps(dict(status='pass',loads=3,timing_rows=3168,event_rows=15840,scope='user-only PMU around complete operations through real carriers'),indent=2)+'\n')
    print('User PMU summary complete.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('repetitions','pmu','user_pmu'));p.add_argument('directory',type=Path);a=p.parse_args();globals()[a.action](a.directory.resolve())
