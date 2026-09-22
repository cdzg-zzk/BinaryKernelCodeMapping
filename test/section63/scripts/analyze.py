#!/usr/bin/env python3
"""Replay the fresh six-version experiment and preserve pairing and load ranges."""
import argparse
from collections import Counter, defaultdict
import csv
import itertools
import json
import math
from pathlib import Path
import statistics as stats
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/evaluation'))
from formal_kernel_audit import audit as kernel_audit
from section63_audit import entry_pages

USER=('native-dso','adapted-dso','kernel-vkso')
KERNEL=('stock-kernel','matched-kernel','owner-kernel')

def read(path):return json.loads(path.read_text())
def rows(path):return list(csv.DictReader(path.open()))
def write(path,data):
    assert data
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')

def user_rows(a,d):
    data=rows(d/'results/user.csv');seen=[];out=[]
    completion=read(d/'results/user-complete.json')
    assert completion['status']=='pass' and completion['algorithm']==a and completion['cpu']==2
    assert set(completion['backends'])==set(USER)
    for b in USER[:2]:
        assert Path(completion['backends'][b])==d.parent/'builds'/a/('libnative.so' if b=='native-dso' else 'libadapted.so')
    if a=='bch':
        log=(d/'results/user.log').read_text()
        assert all(f'correctness: m=13 t={t} vectors=128 backends=3 ok' in log for t in (4,8))
        assert 'BCH evaluation completed' in log
    if a=='lz4':
        expected=Counter(itertools.product(range(7),USER,(4096,65536,1048576),('compress','decompress')))
    elif a=='xz':expected=Counter(itertools.product(range(7),USER,('bash','python3','libc.so.6')))
    else:
        cases=[(13,t,512,-1,'init') for t in (4,8)]+[(13,t,512,0,'encode') for t in (4,8)]
        cases += [(13,t,512,e,m) for t in (4,8) for e in range(t+1) for m in ('decode-full','decode-precomputed')]
        expected=Counter((r,b,*c) for r,b,c in itertools.product(range(11),USER,cases))
    for r in data:
        b=r['backend']
        if a=='lz4':
            repeat=int(r['run']);block=int(r['block_size']);key=(repeat,b,block,r['operation'])
            assert int(r['input_bytes'])==211938580 and int(r['harness_seconds'])==2
            work=f"{r['operation']}/block={block}"
            value=int(r['input_bytes'])/float(r['official_mb_per_second'])*1000
            unit='ns/corpus'
        elif a=='xz':
            repeat=int(r['outer_run']);key=(repeat,b,r['case']);work=r['case']
            assert int(r['repeats'])==20
            value=int(r['elapsed_ns'])/20;unit='ns/task'
        else:
            repeat=int(r['outer']);m,t,size,e=(int(r[k]) for k in ('m','t','len','errors'))
            key=(repeat,b,m,t,size,e,r['operation'])
            work=f"m={m}/t={t}/bytes={size}/errors={e}/{r['operation']}"
            value=int(r['total_ns'])/int(r['iterations']);unit='ns/op'
        assert math.isfinite(value) and value>0
        seen.append(key)
        out.append(dict(deployment=d.name,algorithm=a,domain='user',round=repeat,backend=b,workload=work,value=value,unit=unit))
    assert Counter(seen)==expected,(a,'user matrix mismatch')
    if a=='lz4':
        sys.path.insert(0,str(ROOT/'test/test_lz4/scripts'))
        from parse_official import parse_log
        replay=[r for p in sorted((d/'results/official-logs').glob('*.log')) for r in parse_log(p)]
        fields=list(data[0])
        assert sorted(tuple(str(r[k]) for k in fields) for r in replay)==sorted(tuple(r[k] for k in fields) for r in data)
    return out

def inputs_bch(d):
    groups=defaultdict(list)
    for domain,path in [('user',d/'results/user.csv.inputs.csv'),('kernel',d/'results/kernel/driver-inputs.csv')]:
        data=rows(path);assert len(data)==462
        for r in data:groups[int(r['round']),int(r['t']),int(r['errors'])].append((domain,r))
    assert len(groups)==154
    for key,data in groups.items():
        assert len(data)==len({(domain,r['backend']) for domain,r in data})==6
        for k in ('positions','work_hex','ecc_difference_hex'):
            assert len({r[k] for _,r in data})==1,(key,k)
    return len(groups)

def source_audit(a,d):
    build=d/'prepared/kernel-cost-build'
    original=ROOT/'test/section63/source/linux-5.15.0-119.129'
    if a=='bch':pairs=[(build/'original/bch.c',original/'lib/bch.c')]
    elif a=='lz4':pairs=[(build/'matched'/n,original/'lib/lz4'/n) for n in ('lz4_compress.c','lz4_decompress.c','lz4defs.h')]
    else:pairs=[(build/'matched'/n,original/'lib/xz'/n) for n in ('xz_dec_stream.c','xz_dec_lzma2.c','xz_dec_bcj.c','xz_private.h','xz_stream.h','xz_lzma2.h')]
    for actual,reference in pairs:assert actual.read_bytes()==reference.read_bytes(),str(actual)
    return len(pairs)

def analyze(base,partial=False):
    plan=read(base/'plan.json');out=base/'analysis';out.mkdir(exist_ok=True)
    entries=[e for e in plan['entries'] if (Path(e['directory'])/'complete.json').exists()]
    if not partial:
        assert len(entries)==len(plan['entries']) and read(base/'complete.json')['status']=='pass'
        expected_counts=plan.get('repetition_count',{'bch':3,'lz4':3,'xz':3})
        assert expected_counts in ({'bch':3,'lz4':3,'xz':3},{'bch':12,'lz4':3,'xz':3})
        assert Counter(e['algorithm'] for e in entries)==expected_counts
        assert len({e['directory'] for e in entries})==len(entries)
    observations=[];audits=[]
    for e in entries:
        a=e['algorithm'];d=Path(e['directory'])
        audit=kernel_audit(d)
        audit.update(exports=entry_pages(d),original_matched_source_files=source_audit(a,d))
        if a=='bch':audit['aligned_bch_input_cells']=inputs_bch(d)
        else:
            for backend in USER[:2]:
                helpers=read(d/'results'/(backend+'-helpers.json'));assert helpers['status']=='pass'
        observations+=user_rows(a,d)
        file=d/('results/kernel/driver-results.txt' if a=='bch' else 'results/kernel/raw.csv')
        for r in rows(file):
            if a=='bch':
                repeat=int(r['round']);work=f"m={r['m']}/t={r['t']}/bytes={r['len']}/errors={r['errors']}/{r['mode']}"
                value=int(r['ns'])/int(r['iterations']);unit='ns/op'
            else:
                repeat=int(r['outer_run']);work=f"{r['case']}/{r['operation']}/block={r['block_bytes']}"
                value=int(r['elapsed_ns'])/int(r['repeats']);unit='ns/task'
            backend='matched-kernel' if r['backend'].startswith('matched-') else r['backend']
            observations.append(dict(deployment=d.name,algorithm=a,domain='kernel',round=repeat,backend=backend,workload=work,value=value,unit=unit))
        audits.append(audit)
    if not observations:return {'status':'no complete deployments'}
    # Full-corpus kernel totals keep the twelve input files, rather than averaging
    # their relative overheads or treating them as independent deployments.
    corpus=defaultdict(list)
    for r in observations:
        if r['algorithm']=='lz4' and r['domain']=='kernel':
            corpus[tuple(r[k] for k in ('deployment','round','backend'))+(r['workload'].split('/',1)[1],)].append(r)
    aggregate=[]
    for (d,repeat,b,work),group in corpus.items():
        assert len(group)==12
        aggregate.append(dict(deployment=d,algorithm='lz4',domain='kernel',round=repeat,backend=b,workload='corpus/'+work,value=sum(r['value'] for r in group),unit='ns/corpus'))
    groups=defaultdict(dict)
    for r in observations+aggregate:
        key=tuple(r[k] for k in ('deployment','algorithm','domain','workload','round','unit'))
        assert r['backend'] not in groups[key]
        groups[key][r['backend']]=r['value']
    paired=[]
    for key,values in sorted(groups.items()):
        d,a,domain,work,repeat,unit=key
        native,middle,target=USER if domain=='user' else KERNEL
        assert set(values)=={native,middle,target}
        for t,b in ((target,native),(target,middle),(middle,native)):
            paired.append(dict(deployment=d,algorithm=a,domain=domain,workload=work,round=repeat,target=t,baseline=b,
                cost_ratio=values[t]/values[b],target_value=values[t],baseline_value=values[b],unit=unit))
    grouped=defaultdict(list)
    keys=('deployment','algorithm','domain','workload','target','baseline','unit')
    for r in paired:grouped[tuple(r[k] for k in keys)].append(r)
    deployments=[]
    for key,group in sorted(grouped.items()):
        ratios=[r['cost_ratio'] for r in group]
        deployments.append(dict(zip(keys,key),rounds=len(group),median_cost_ratio=stats.median(ratios),
            minimum_round_ratio=min(ratios),maximum_round_ratio=max(ratios),
            median_target_value=stats.median(r['target_value'] for r in group),median_baseline_value=stats.median(r['baseline_value'] for r in group)))
    keys=keys[1:];grouped=defaultdict(list)
    for r in deployments:grouped[tuple(r[k] for k in keys)].append(r)
    summary=[]
    for key,group in sorted(grouped.items()):
        ratios=[r['median_cost_ratio'] for r in group]
        if not partial:assert len(ratios)==expected_counts[key[0]]
        summary.append(dict(zip(keys,key),deployments=len(ratios),median_cost_ratio=stats.median(ratios),
            minimum_deployment_ratio=min(ratios),maximum_deployment_ratio=max(ratios)))
    for name,data in [('observations',observations),('corpus-observations',aggregate),('paired-rounds',paired),('deployment-ratios',deployments),('summary',summary)]:
        if data:write(out/(name+'.csv'),data)
    report=dict(status='partial' if partial else 'complete',completed_deployments=len(entries),
        raw_user_rows=sum(r['domain']=='user' for r in observations),raw_kernel_rows=sum(r['domain']=='kernel' for r in observations),
        comparisons=len(summary),audits=audits,boot_ids=sorted({a['boot_id'] for a in audits}),
        estimator='within-round cost ratio; median within each load; equal-weight median across loads; ranges are load medians, not confidence intervals',repetition_count=dict(Counter(e['algorithm'] for e in entries)))
    if not partial:
        assert report['raw_user_rows']==126*expected_counts['lz4']+63*expected_counts['xz']+1056*expected_counts['bch']
        assert report['raw_kernel_rows']==1584*expected_counts['lz4']+99*expected_counts['xz']+1056*expected_counts['bch']
        assert report['comparisons']==384 and len(report['boot_ids'])==1
    save(out/'audit.json',report)
    return {k:v for k,v in report.items() if k!='audits'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--partial',action='store_true');a=p.parse_args()
    print(json.dumps(analyze(a.directory.resolve(),a.partial),indent=2))
