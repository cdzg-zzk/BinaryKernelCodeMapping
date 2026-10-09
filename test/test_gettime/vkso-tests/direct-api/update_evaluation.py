#!/usr/bin/env python3
"""Full UPDATE cost: exact band + occupancy + tail decomposition by boot."""
import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import numpy as np
from bundle import verify_sums, sha256
from read_evaluation import ROOT, BARE, CAMPAIGN, REV, csv_text, rows
from update_peaks import load, histogram, peaks, stats, bootstrap

OUT=Path(__file__).resolve().parent/'update-evidence'
VARIANTS=('normal','no-retpoline')
SCENARIOS=('idle','monotonic','monotonic_raw','monotonic_coarse')


def band(a,cut,cap):
    a=np.asarray(a,dtype=float)
    if not np.isfinite(a).all() or not (a>0).all() or not 0<cut<cap:raise ValueError('invalid sample or cut/cap')
    high=a>cut
    if high.all() or not high.any():raise ValueError('unresolved band')
    z=np.minimum(a,cap)
    p=float(high.mean());low=float(z[~high].mean());hi=float(z[high].mean())
    full=float(a.mean());capped=float(z.mean());excess=float(np.maximum(a-cap,0).mean())
    assert abs((1-p)*low+p*hi+excess-full)<1e-9
    return dict(n=len(a),cut=cut,cap=cap,mean=full,low_mean=low,high_mean=float(a[high].mean()),
                high_capped_mean=hi,high_fraction=p,low_median=float(np.median(a[~high])),
                high_median=float(np.median(a[high])),cap_mean=capped,tail_excess=excess,
                tail_fraction=float((a>cap).mean()),tail_cost_share=float(a[a>cap].sum()/a.sum()),
                p50=float(np.quantile(a,.5)),p95=float(np.quantile(a,.95)),p99=float(np.quantile(a,.99)),maximum=float(a.max()))


def components(r,v):
    p=(r['high_fraction']+v['high_fraction'])/2
    low=(1-p)*(v['low_mean']-r['low_mean'])
    high=p*(v['high_capped_mean']-r['high_capped_mean'])
    mix=(v['high_fraction']-r['high_fraction'])*(v['high_capped_mean']+r['high_capped_mean']-v['low_mean']-r['low_mean'])/2
    tail=v['tail_excess']-r['tail_excess'];delta=v['mean']-r['mean']
    assert abs(low+high+mix+tail-delta)<1e-9
    return dict(low_contribution=low,high_capped_contribution=high,occupancy_contribution=mix,
                tail_contribution=tail,delta=delta,residual=low+high+mix+tail-delta)


def mean(xs,key):return float(np.mean([x[key] for x in xs]))


def produce():
    manifest,data,rounds,identities,other=load(CAMPAIGN)
    assert len(data)==64 and len(identities)==16
    previous=json.loads((BARE/'results/update-peaks-20260929-full/report.json').read_text())
    pg={(x['variant'],x['scenario'],x['backend']):x for x in previous['groups']}
    mainold={(x['variant'],x['scenario']):x for x in rows(BARE/'results/paper-clocktime-results-20261002/update.csv')}
    configs=[]; windows=[]; evidence=[];checkcount=0
    for variant in VARIANTS:
        package=BARE/'artifacts'/Path(manifest['packages']['update'][variant]['path']).name
        verify_sums(package);verify_sums(package/'direct')
        assert sha256(package/'SHA256SUMS')==manifest['packages']['update'][variant]['sha256']
        for method in ['raw','vkso']:
            cfg=(package/(method+'.config')).read_text()
            for symbol in ['CONFIG_TIMEKEEPING_UPDATE_BENCH','CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG','CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG','CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG','CONFIG_TIMEKEEPING_UPDATE_BUSINESS_DIAG']:
                val=next((x.split('=',1)[1] for x in cfg.splitlines() if x.startswith(symbol+'=')),'not set')
                assert val==('y' if symbol=='CONFIG_TIMEKEEPING_UPDATE_BENCH' else 'not set'),(method,variant,symbol,val)
                configs.append(dict(variant=variant,backend=method,symbol=symbol,value=val))
    for entry in manifest['plan']:
        if entry['mode']!='update':continue
        case,b=entry['case'],entry['block'];d=CAMPAIGN/f'block-{b:02}'/'update'/case
        checkcount+=len(verify_sums(d))
        run=json.loads((d/'run.json').read_text())
        assert run['build']['source_git_commit']==REV and run['build']['scope']=='update'
        assert run['error'] is None and not any(v for k,v in run.items() if k.endswith('_diagnostic'))
        for filename,marker in [('check.log','public_api_check=PASS scope=full'),('check-fast.log','time_syscall_denial_check=PASS'),('abi.log','abi_matrix_status=pass')]:
            assert marker in (d/filename).read_text(),filename
        evidence.append(dict(case=case,block=b,boot_id=run['boot_id'],source_revision=run['build']['source_git_commit'],
                             package=Path(manifest['packages']['update'][case.split('-',1)[1]]['path']).name,
                             source=str((d/'run.json').relative_to(ROOT))))
        for scenario in SCENARIOS:
            for i in range(15):
                meta=json.loads((d/scenario/f'round-{i:02}.json').read_text())
                duration=(meta['writer_end_ns']-meta['writer_start_ns'])/1e9
                assert duration>=15
                if scenario!='idle':assert meta['load_batch_after_stop']>meta['load_batch_before_start']>=1
                windows.append(dict(case=case,block=b,scenario=scenario,round=i,duration_seconds=duration,
                                    load_batch_before_start=meta.get('load_batch_before_start',''),load_batch_after_stop=meta.get('load_batch_after_stop','')))
    groups=[];boots=[];roundrows=[];parts=[];summary=[];sensitivity=[];histrows=[];cdfrows=[]
    cuts={}; bs={}; modes={}
    for variant,scenario,method in itertools.product(VARIANTS,SCENARIOS,['raw','vkso']):
        case=method+'-'+variant;arrays=[data[case,scenario,b] for b in range(1,5)]
        hist=histogram(arrays);mode,smooth=peaks(hist);cut=mode['cut'];cuts[case,scenario]=cut;modes[case,scenario]=mode
        assert all(mode[k]==pg[variant,scenario,method][k] for k in ['cut','low_mode','high_mode'])
        items=[]
        for b,a in enumerate(arrays,1):
            s=band(a,cut,300);bs[case,scenario,b]=s;items.append(s)
            own,_=peaks(histogram([a]))
            boots.append(dict(variant=variant,backend=method,scenario=scenario,block=b,
                              own_low_mode=own['low_mode'],own_high_mode=own['high_mode'],own_cut=own['cut'],**s))
            for i,z in enumerate(rounds[case,scenario,b]):
                roundrows.append(dict(variant=variant,backend=method,scenario=scenario,block=b,round=i,**band(z,cut,300)))
            h=histogram([a]);_,sm=peaks(h)
            histrows.extend(dict(variant=variant,backend=method,scenario=scenario,block=b,ticks=t,probability=float(h[t]),smooth_probability=float(sm[t])) for t in range(301))
            sorted_a=np.sort(a)
            grid=np.unique(np.concatenate([np.arange(60,301),np.geomspace(301,max(302,int(a.max())),120).astype(int)]))
            cdfrows.extend(dict(variant=variant,backend=method,scenario=scenario,block=b,ticks=int(t),cdf=float(np.searchsorted(sorted_a,t,side='right')/len(a))) for t in grid)
        g=dict(variant=variant,backend=method,scenario=scenario,**mode,total_samples=sum(x['n'] for x in items),
               **{k:mean(items,k) for k in items[0] if k not in ['n','cut','cap','maximum']},maximum=max(x['maximum'] for x in items),
               boot_mean_min=min(x['mean'] for x in items),boot_mean_max=max(x['mean'] for x in items),
               high_fraction_min=min(x['high_fraction'] for x in items),high_fraction_max=max(x['high_fraction'] for x in items))
        groups.append(g)
    for variant,scenario in itertools.product(VARIANTS,SCENARIOS):
        blockparts=[]
        for b in range(1,5):
            r,v=[bs[m+'-'+variant,scenario,b] for m in ['raw','vkso']]
            x=dict(variant=variant,scenario=scenario,block=b,raw_mean=r['mean'],vkso_mean=v['mean'],**components(r,v))
            parts.append(x);blockparts.append(x)
        s=dict(variant=variant,scenario=scenario,**{k:mean(blockparts,k) for k in blockparts[0] if k not in ['variant','scenario','block']})
        for key in ['delta','low_contribution','high_capped_contribution','occupancy_contribution','tail_contribution']:
            vs=[x[key] for x in blockparts];ci=bootstrap(vs)
            s.update({key+'_ci95_low':ci[0],key+'_ci95_high':ci[1],key+'_min':min(vs),key+'_max':max(vs)})
        s['delta_percent']=100*s['delta']/s['raw_mean'];s['faster_blocks']=sum(x['delta']<0 for x in blockparts)
        assert abs(s['delta']-float(mainold[variant,scenario]['delta_mean_ticks']))<1e-9
        summary.append(s)
        settings=[('cut_shift',rs,vs,300) for rs,vs in itertools.product([-5,0,5],repeat=2)]+[('tail_cap',0,0,c) for c in [180,200,240]]
        for kind,rs,vs,cap in settings:
            xs=[components(band(data['raw-'+variant,scenario,b],cuts['raw-'+variant,scenario]+rs,cap),
                           band(data['vkso-'+variant,scenario,b],cuts['vkso-'+variant,scenario]+vs,cap)) for b in range(1,5)]
            sensitivity.append(dict(variant=variant,scenario=scenario,kind=kind,raw_shift=rs,vkso_shift=vs,cap=cap,status='defined',**{k:mean(xs,k) for k in xs[0]}))
        for sigma in [1.5,2,4,6]:
            try:
                cs={m:peaks(histogram([data[m+'-'+variant,scenario,b] for b in range(1,5)]),sigma)[0]['cut'] for m in ['raw','vkso']}
                xs=[components(band(data['raw-'+variant,scenario,b],cs['raw'],300),band(data['vkso-'+variant,scenario,b],cs['vkso'],300)) for b in range(1,5)]
                vals={k:mean(xs,k) for k in xs[0]};status='defined'
            except ValueError:vals={k:None for k in blockparts[0] if k.endswith('contribution') or k in ['delta','residual']};status='unresolved-peaks'
            sensitivity.append(dict(variant=variant,scenario=scenario,kind='sigma',raw_shift=sigma,vkso_shift=sigma,cap=300,status=status,**vals))
    loads=[];loadblocks=[]
    for variant,scenario in itertools.product(VARIANTS,SCENARIOS[1:]):
        diffs=[]
        for b in range(1,5):
            r,v=[bs[m+'-'+variant,scenario,b]['mean']-bs[m+'-'+variant,'idle',b]['mean'] for m in ['raw','vkso']]
            diffs.append(v-r);loadblocks.append(dict(variant=variant,scenario=scenario,block=b,raw_load_minus_idle=r,vkso_load_minus_idle=v,difference_in_differences=v-r))
        z=loadblocks[-4:];ci=bootstrap(diffs)
        loads.append(dict(variant=variant,scenario=scenario,raw_load_minus_idle=mean(z,'raw_load_minus_idle'),vkso_load_minus_idle=mean(z,'vkso_load_minus_idle'),difference_in_differences=float(np.mean(diffs)),ci95_low=ci[0],ci95_high=ci[1],negative_blocks=sum(x<0 for x in diffs)))
    validation=dict(status='PASS',revision=REV,update_boots=16,boot_scenario_units=len(boots),rounds=len(roundrows),
                    samples=sum(len(a) for a in data.values()),archived_files_verified=checkcount,non_cpu0_samples=other,
                    estimator='mean of complete within-boot sample means, equal boot weight',
                    bootstrap='256 matched four-block resamples, pointwise percentile intervals; cut-dependent terms conditional on fitted cuts',
                    decomposition='cap=300; low + capped high + capped occupancy + excess tail = complete mean difference, per block',
                    primary_samples='all periodic action=0 observations including four CPU2 samples; no pair-calibration subtraction; no dropped observations',
                    scopes='instrumented timekeeping_update interval; end timestamp precedes record append; no calibration subtraction or clean-image UPDATE inference',
                    means_match_prior=True,max_reconstruction_residual=max(abs(x['residual']) for x in parts),
                    window_duration_range=[min(x['duration_seconds'] for x in windows),max(x['duration_seconds'] for x in windows)])
    assert validation['samples']==3599774
    outputs={'groups.csv':groups,'boots.csv':boots,'rounds.csv':roundrows,'decomposition-blocks.csv':parts,'summary.csv':summary,
             'sensitivity.csv':sensitivity,'load-response.csv':loads,'load-response-blocks.csv':loadblocks,'histograms.csv':histrows,
             'cdfs.csv':cdfrows,'identities.csv':evidence,'configurations.csv':configs,'windows.csv':windows}
    return {**{k:csv_text(v) for k,v in outputs.items()},'validation.json':json.dumps(validation,ensure_ascii=False,indent=2)+'\n'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    for name,s in produce().items():
        if a.check:assert (OUT/name).read_bytes()==s.encode(),name
        else:(OUT/name).write_bytes(s.encode())
    print('UPDATE evidence PASS: 16 boots, 64 boot/scenario units, 960 rounds, 3,599,774 observations')
