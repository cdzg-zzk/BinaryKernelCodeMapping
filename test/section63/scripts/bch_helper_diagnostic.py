#!/usr/bin/env python3
"""One follow-up control for the residual BCH generated-code difference."""
import argparse
from collections import defaultdict
import csv
import json
import os
from pathlib import Path
import shutil
import statistics as stats
import diagnose as diag

BACKENDS=('cached-direct','cached-helpers','owner-kernel')

def prepare(base):
    assert diag.read(base/'diagnostics/complete.json')['status']=='pass'
    out=base/'diagnostics/bch-helper';out.mkdir()
    source=out/'cached-source';source.mkdir()
    shutil.copy2(base/'diagnostics/bch/cached-source/bch.c',source/'bch.c')
    reference=out/'reference';diag.copy_source(base/'deployment-00-bch/prepared/kernel-cost-build/matched',reference)
    p=reference/'bch_impl.c';p.write_text(p.read_text().replace('../original/','../cached-source/'))
    diag.build(reference)
    helper=out/'helper-source';helper.mkdir()
    adapted=(base/'owners/adapted/bch.c').read_text()
    block=adapted[adapted.index('#ifdef __KERNEL__'):adapted.index('\n#if defined(CONFIG_BCH_CONST_PARAMS)')]
    block=block.replace('vkso_bch_','cached_bch_')
    text=(source/'bch.c').read_text();assert text.count('#include <linux/bch.h>')==1
    (helper/'bch.c').write_text(text.replace('#include <linux/bch.h>','#include <linux/bch.h>\n'+block))
    cached=out/'cached';diag.copy_source(base/'diagnostics/bch/cached',cached)
    p=cached/'bch_impl.c';p.write_text(p.read_text().replace('../cached-source/','../helper-source/'))
    p=cached/'module_meta.c';p.write_text(p.read_text()+'''
#include <linux/slab.h>
#include <linux/string.h>
void *(*cached_bch_kmalloc_slot)(size_t, gfp_t) = __kmalloc;
void (*cached_bch_kfree_slot)(const void *) = kfree;
void *(*cached_bch_memcpy_slot)(void *, const void *, size_t) = memcpy;
void *(*cached_bch_memset_slot)(void *, int, size_t) = memset;
''')
    diag.build(cached)
    driver=out/'driver';diag.copy_source(base/'diagnostics/bch/driver',driver)
    p=driver/'bch_kernel_bench.c';p.write_text(p.read_text().replace('original-matched','cached-direct').replace('cached-matched','cached-helpers'))
    diag.build(driver,[base/'owners/bch/Module.symvers',reference/'Module.symvers',cached/'Module.symvers'])
    for name,p in [('cached-direct',reference/'bch_matched.ko'),('cached-helpers',cached/'bch_cached.ko')]:
        diag.command(['objdump','-drwC','-Mintel',p],out/(name+'.asm'))
    diag.save(out/'intervention.json',dict(backends=list(BACKENDS),reason='loop-only control left a material residual in t=8 precomputed decode',
        first='original Matched plus adopted cached syndrome loop',second='same source plus four kernel-bound helper slots',
        unchanged='same original initialization, lookup-table representation, compiler settings, complete workloads',
        scope='kernel-only source/helper ablation; no production owner changes',loads=3,rounds=11,sample_ms=10))
    print('Prepared the residual BCH helper control.')

def collect(base):
    assert os.geteuid()==0
    out=base/'diagnostics/bch-helper';diag.BCH_BACKENDS=BACKENDS
    for n in range(3):
        assert not {'vkso_bch','bch_matched','bch_cached','bch_kernel_bench','page_cache_replace'} & diag.modules().keys()
        d=out/f'load-{n:02d}';d.mkdir()
        diag.save(d/'identity.json',dict(kernel=os.uname().release,cpu=2,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))
        diag.collect_bch(base,d,out)
        diag.save(d/'complete.json',dict(status='pass',unloaded=True));print(d.name+': complete',flush=True)
    diag.save(out/'complete.json',dict(status='pass',loads=3))
    analyze(base)

def analyze(base):
    out=base/'diagnostics/bch-helper';pairs=[]
    for d in sorted(p for p in out.glob('load-*') if p.is_dir()):
        assert diag.read(d/'complete.json')['status']=='pass'
        groups=defaultdict(dict)
        for r in csv.DictReader((d/'driver-results.txt').open()):
            groups[f"t={r['t']}/errors={r['errors']}/{r['mode']}",int(r['round'])][r['backend']]=int(r['ns'])/int(r['iterations'])
        for (work,repeat),v in groups.items():
            for t,b in ((BACKENDS[1],BACKENDS[0]),(BACKENDS[2],BACKENDS[1]),(BACKENDS[2],BACKENDS[0])):
                pairs.append(dict(load=d.name,workload=work,round=repeat,target=t,baseline=b,cost_ratio=v[t]/v[b]))
    def write(name,rows):
        with (out/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write('paired-rounds.csv',pairs);groups=defaultdict(list)
    for r in pairs:groups[r['load'],r['workload'],r['target'],r['baseline']].append(r['cost_ratio'])
    loads=[dict(zip(('load','workload','target','baseline'),k),median_cost_ratio=stats.median(v)) for k,v in sorted(groups.items())]
    write('load-ratios.csv',loads);groups=defaultdict(list)
    for r in loads:groups[r['workload'],r['target'],r['baseline']].append(r['median_cost_ratio'])
    rows=[]
    for k,v in sorted(groups.items()):
        assert len(v)==3
        rows.append(dict(zip(('workload','target','baseline'),k),median_cost_ratio=stats.median(v),minimum_load_ratio=min(v),maximum_load_ratio=max(v)))
    write('summary.csv',rows)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','collect','analyze'));p.add_argument('directory',type=Path);a=p.parse_args()
    globals()[a.action](a.directory.resolve())
