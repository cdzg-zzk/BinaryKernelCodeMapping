#!/usr/bin/env python3
"""Reproduce complete clean READ evidence, using boots as replication units."""
import argparse
from collections import Counter, defaultdict
import csv
import io
import itertools
import json
from pathlib import Path
import statistics as st
import subprocess

import numpy as np
from bundle import verify_sums, sha256
from results import CASE_NAMES, KERNEL_APIS, summarize, validate_kernel_rows

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BARE = HERE.parent / 'baremetal'
CAMPAIGN = BARE / 'results/20260929T040650Z-clocktime-full'
OUT = HERE / 'read-evidence'
VARIANTS = ('normal', 'no-retpoline')
REV = 'cf9dc817f29f9c8d6f88dde0c58c4ccb75347aeb'


def rows(p):
    with p.open() as f:
        return list(csv.DictReader(f))


def csv_text(data):
    s = io.StringIO(newline='')
    w = csv.DictWriter(s, fieldnames=list(data[0]))
    w.writeheader(); w.writerows(data)
    return s.getvalue()


def category(domain, api):
    if domain == 'kernel': return 'kernel_read'
    if api.endswith('fallback'): return 'fallback'
    if api in CASE_NAMES[:7]: return 'clock_gettime_fast'
    if api == 'getcpu_both': return 'getcpu'
    return 'other_time_fast'


def exact_intervals(raw, vkso):
    """Enumerate all empirical bootstrap samples; no inner-batch resampling.

    Main: independent 4-boot draws per backend (256^2 possibilities).
    Sensitivity: resample the four campaign blocks together (256 possibilities).
    Same estimator in both: median(VKSO boot medians)-median(Raw boot medians).
    """
    r, v = np.asarray(raw), np.asarray(vkso)
    if r.shape != (4,) or v.shape != (4,):
        raise ValueError('exactly four complete boots/backend required')
    ix = np.array(list(itertools.product(range(4), repeat=4)))
    rb, vb = np.median(r[ix], axis=1), np.median(v[ix], axis=1)
    delta = (vb[:, None] - rb[None, :]).ravel()
    ratio = (vb[:, None] / rb[None, :]).ravel()
    return dict(delta_ci95_low=float(np.quantile(delta, .025)),
                delta_ci95_high=float(np.quantile(delta, .975)),
                ratio_ci95_low=float(np.quantile(ratio, .025)),
                ratio_ci95_high=float(np.quantile(ratio, .975)),
                block_ci95_low=float(np.quantile(vb-rb, .025)),
                block_ci95_high=float(np.quantile(vb-rb, .975)))


def produce():
    campaign = json.loads((CAMPAIGN/'campaign.json').read_text())
    entries = [x for x in campaign['plan'] if x['mode']=='read']
    assert len(entries)==16
    dirs = [CAMPAIGN/f"block-{e['block']:02d}/read/{e['case']}" for e in entries]
    # Reuse established acquisition validation, including archived checksums,
    # correctness, complete matrices, CPU, compiler and package consistency.
    canonical = summarize(dirs)
    values, boots, processes, identities, configs = defaultdict(list), [], [], [], []
    counters = Counter()
    source_checked = set()
    for e, d in zip(entries, dirs):
        run=json.loads((d/'run.json').read_text())
        method, variant=e['case'].split('-',1)
        assert run['git_commit']==REV and run['block']==e['block']
        assert (run['iterations'],run['warmup'],run['repeats'],run['processes'],run['cpu'])==(500000,10000,31,7,2)
        build=json.loads((d/'bundle-build.json').read_text())
        assert build['scope']=='read' and build['build_variant']==variant
        package=BARE/'artifacts'/Path(campaign['packages']['read'][variant]['path']).name
        if variant not in source_checked:
            verify_sums(package); verify_sums(package/'direct')
            assert sha256(package/'SHA256SUMS')==campaign['packages']['read'][variant]['sha256']
            for name in ['time_bench.c','vkso_public.c','vkso_time_init.c']:
                assert sha256(HERE/name)==build['source_hashes']['direct-api/'+name]
            source_checked.add(variant)
        assert sha256(package/(method+'-bzImage'))==run['kernel_image_sha256']
        assert sha256(package/(method+'.config'))==run['kernel_config_sha256']
        assert sha256(package/'direct'/('native-bench' if method=='raw' else 'vkso-bench'))==run['binary_sha256']
        identity_keys=['boot_id','git_commit','kernel_image_sha256','kernel_config_sha256','binary_sha256','public_library_sha256','source_fingerprint']
        identities.append(dict(block=e['block'],method=method,variant=variant,run=str((d/'run.json').relative_to(ROOT)),
                               **{k:run[k] for k in identity_keys}))
        if e['block']==1:
            cfg=(package/(method+'.config')).read_text()
            for symbol in ['CONFIG_RETPOLINE','CONFIG_RETHUNK','CONFIG_CPU_UNRET_ENTRY','CONFIG_CPU_SRSO','CONFIG_MITIGATION_ITS']:
                val=next((x.split('=',1)[1] for x in cfg.splitlines() if x.startswith(symbol+'=')), 'not set')
                configs.append(dict(variant=variant,method=method,symbol=symbol,value=val))
        users=rows(d/'samples.csv')
        component_rows=[r for p in sorted(d.glob('process-*.csv')) for r in rows(p)]
        assert Counter(tuple(r.items()) for r in users)==Counter(tuple(r.items()) for r in component_rows)
        kernel=rows(d/'kernel-reader.csv'); validate_kernel_rows(kernel,run)
        for domain, data, names in [('user',users,CASE_NAMES),('kernel',kernel,KERNEL_APIS)]:
            for api in names:
                selected=[r for r in data if r['case' if domain=='user' else 'api']==api]
                xs=[int(r['tsc_ticks' if domain=='user' else 'total_tsc_cycles'])/int(r['iterations']) for r in selected]
                assert len(xs)==31
                if domain=='user': assert all(int(r['aux_start'])==int(r['aux_end'])==2 for r in selected)
                key=(variant,domain,api,method)
                values[key].append((e['block'],st.median(xs),st.fmean(xs)))
                counters[domain+'_batches']+=len(xs)
                boots.append(dict(block=e['block'],variant=variant,method=method,domain=domain,api=api,
                                  boot_id=run['boot_id'],batches=len(xs),median=st.median(xs),mean=st.fmean(xs),
                                  batch_min=min(xs),batch_p95=float(np.quantile(xs,.95)),batch_max=max(xs),
                                  source=str((d/('samples.csv' if domain=='user' else 'kernel-reader.csv')).relative_to(ROOT))))
                if domain=='user':
                    for pi in range(7):
                        z=[float(r['ticks_per_call']) for r in selected if int(r['process_index'])==pi]
                        processes.append(dict(block=e['block'],variant=variant,method=method,api=api,process=pi,
                                              batches=len(z),median=st.median(z),mean=st.fmean(z)))
    table, block_rows = [], []
    for variant in VARIANTS:
        for domain,names in [('user',CASE_NAMES),('kernel',KERNEL_APIS)]:
            for api in names:
                r,v=[sorted(values[(variant,domain,api,m)]) for m in ('raw','vkso')]
                assert [x[0] for x in r]==[1,2,3,4]==[x[0] for x in v]
                raw, vkso=[[x[1] for x in z] for z in (r,v)]
                a,b=st.median(raw),st.median(vkso)
                diffs=[y-x for x,y in zip(raw,vkso)]
                leave=[st.median([x for j,x in enumerate(vkso) if j!=i])-st.median([x for j,x in enumerate(raw) if j!=i]) for i in range(4)]
                mean_r,mean_v=st.fmean(x[2] for x in r),st.fmean(x[2] for x in v)
                table.append(dict(variant=variant,domain=domain,category=category(domain,api),api=api,
                                  raw_ticks=a,vkso_ticks=b,delta_ticks=b-a,delta_percent=100*(b/a-1),
                                  **exact_intervals(raw,vkso),raw_boot_min=min(raw),raw_boot_max=max(raw),
                                  vkso_boot_min=min(vkso),vkso_boot_max=max(vkso),
                                  block_delta_min=min(diffs),block_delta_max=max(diffs),
                                  faster_blocks=sum(x<0 for x in diffs),slower_blocks=sum(x>0 for x in diffs),
                                  leave_one_block_min=min(leave),leave_one_block_max=max(leave),
                                  raw_equal_boot_mean=mean_r,vkso_equal_boot_mean=mean_v,mean_delta=mean_v-mean_r,
                                  boots_per_backend=4,batches_per_boot=31))
                block_rows.extend(dict(variant=variant,domain=domain,api=api,block=i+1,raw_ticks=x,vkso_ticks=y,delta_ticks=y-x) for i,(x,y) in enumerate(zip(raw,vkso)))
    # Preserve all existing point estimates; CI becomes exact rather than Monte Carlo.
    prior=BARE/'results/paper-clocktime-results-20261002'
    for domain in ['user','kernel']:
        old={(x['variant'],x['api']):x for x in rows(prior/f'read-{domain}.csv')}
        for t in [x for x in table if x['domain']==domain]:
            for k in ['raw_ticks','vkso_ticks','delta_ticks']:
                assert abs(t[k]-float(old[t['variant'],t['api']][k]))<1e-9
    assert len({x['boot_id'] for x in identities})==16
    for variant in VARIANTS:
        for symbol in {x['symbol'] for x in configs}:
            assert len({x['value'] for x in configs if x['variant']==variant and x['symbol']==symbol})==1
    report=dict(status='PASS',source_revision=REV,campaign=str(CAMPAIGN.relative_to(ROOT)),
                independent_read_boots=16,comparisons=len(table),boot_api_summaries=len(boots),
                **counters,timed_calls=sum(counters.values())*500000,
                estimator='median of four boot medians; 31 batch-average costs per boot',
                ci='pointwise 95% percentile; enumerate 256 x 256 independent four-boot resamples',
                sensitivity='256 joint block resamples; leave-one-block-out; equal-boot arithmetic means',
                uncertainty_scope='pointwise empirical bootstrap with four boots/backend; no simultaneous coverage or equivalence test',
                exclusions='none of the 16 complete clean READ boots or their batches; UPDATE and recheck campaigns outside READ scope',
                existing_point_estimates_reproduced=True,
                environment={k:run[k] for k in ['cpu','iterations','warmup','repeats','processes','compiler_version','base_cflags','cpu_info','tuning','controlled_boot_arguments']})
    output={'summary.csv':csv_text(table),'boot-statistics.csv':csv_text(boots),'block-deltas.csv':csv_text(block_rows),
            'process-statistics.csv':csv_text(processes),'build-identities.csv':csv_text(identities),'configurations.csv':csv_text(configs),
            'validation.json':json.dumps(report,ensure_ascii=False,indent=2)+'\n'}
    return output


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    data=produce()
    for name,s in data.items():
        path=OUT/name
        if args.check:
            if path.read_bytes()!=s.encode(): raise ValueError('stale derived output: '+name)
        else: path.write_bytes(s.encode())
    print('READ evidence: PASS; 16 boots, 38 comparisons, all archived batches retained')

if __name__=='__main__':main()
