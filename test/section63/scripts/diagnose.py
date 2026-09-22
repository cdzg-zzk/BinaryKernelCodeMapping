#!/usr/bin/env python3
"""Separate causal controls: BCH cached loop and XZ kernel CRC dependency.

Never changes an official owner or joins diagnostic rows to the main campaign.
Run preparation/collection only after the formal campaign has finished.
"""
import argparse
from collections import defaultdict
import csv
import io
import json
import os
from pathlib import Path
import re
import shutil
import statistics as stats
import subprocess
import sys

BCH_BACKENDS=('original-matched','cached-matched','owner-kernel')
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/evaluation'))
from bch_kernel_audit import new_log_window
from section63_audit import function_source


def save(p,data):p.write_text(json.dumps(data,indent=2)+'\n')
def read(p):return json.loads(p.read_text())
def modules():return {r.split()[0]:int(r.split()[2]) for r in Path('/proc/modules').read_text().splitlines()}
def command(args,log):
    with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True)
def copy_source(src,dst):
    dst.mkdir(parents=True)
    for p in src.iterdir():
        if p.name=='Makefile' or p.suffix in ('.c','.h'):
            if not p.name.endswith('.mod.c'):shutil.copy2(p,dst/p.name)
def build(directory,extra=None):
    command(['make','-C','/lib/modules/5.15.0-119-generic/build','M='+str(directory),
        *(['KBUILD_EXTRA_SYMBOLS='+' '.join(map(str,extra))] if extra else []),'-j2','modules'],directory/'build.log')

def prepare(base):
    assert read(base/'complete.json')['status']=='pass'
    output=base/'diagnostics';output.mkdir(exist_ok=False)
    owners=base/'owners'
    bch=output/'bch';bch.mkdir()
    native=read(base/'builds/bch/commands.json')[0]['argv']
    assert native[0]=='gcc' and 'libnative.so' in native[native.index('-o')+1]
    alias_args=list(native);alias_args[alias_args.index('-o')+1]=str(bch/'native-no-strict-alias.so')
    alias_args.append('-fno-strict-aliasing')
    command(alias_args,bch/'alias-control-build.log')
    command(['objdump','-drwC','-Mintel',bch/'native-no-strict-alias.so'],bch/'native-no-strict-alias.asm')
    save(bch/'alias-control.json',dict(scope='generated-code diagnostic only; no performance rows',
        original_command=native,diagnostic_command=alias_args,change='disable strict-alias analysis'))
    original=base/'deployment-00-bch/prepared/kernel-cost-build/matched'
    reference=bch/'reference';reference.mkdir()
    for name in ('bch_matched.ko','Module.symvers'):shutil.copy2(original/name,reference/name)
    cached=bch/'cached';copy_source(original,cached)
    source=bch/'cached-source';source.mkdir()
    raw=(ROOT/'test/section63/source/linux-5.15.0-119.129/lib/bch.c').read_text()
    old=function_source(ROOT/'test/section63/source/linux-5.15.0-119.129/lib/bch.c','static void compute_syndromes(')
    new=function_source(owners/'adapted/bch.c','static void compute_syndromes(')
    assert raw.count(old)==1 and old!=new
    (source/'bch.c').write_text(raw.replace(old,new))
    for p in cached.iterdir():
        if p.name=='Makefile' or p.suffix=='.c':
            p.write_text(p.read_text().replace('bch_matched','bch_cached').replace('matched_bch_','cached_bch_').replace('../original/bch.c','../cached-source/bch.c'))
    build(cached)
    driver=bch/'driver';copy_source(ROOT/'test/evaluation/bch-kernel',driver)
    p=driver/'bch_kernel_bench.c';text=p.read_text().replace('matched_bch_','cached_bch_')
    text=re.sub(r'\bbch_(init|free|encode|decode)\b',r'matched_bch_\1',text)
    # The stock header now declares the original Matched functions.
    text=text.replace('#include <linux/bch.h>', '#define bch_init matched_bch_init\n#define bch_free matched_bch_free\n#define bch_encode matched_bch_encode\n#define bch_decode matched_bch_decode\n#include <linux/bch.h>')
    text=text.replace('stock-kernel','original-matched').replace('matched-source-kernel','cached-matched')
    p.write_text(text)
    build(driver,[owners/'bch/Module.symvers',reference/'Module.symvers',cached/'Module.symvers'])
    save(bch/'intervention.json',dict(reference='original Matched from formal campaign',
        cached='original Matched with only compute_syndromes replaced by adopted cached loop',
        owner='unchanged formal VKSO owner',old_function=old,new_function=new))
    xz=output/'xz';xz.mkdir()
    crc=xz/'kernel-crc';copy_source(owners/'xz',crc)
    for p in crc.iterdir():
        if p.name=='Makefile' or p.suffix in ('.c','.h'):
            p.write_text(p.read_text().replace('vkso_xz','matched_xz'))
    (crc/'xz_crc32.c').write_text('''#include <linux/crc32.h>
#include "xz_private.h"
XZ_EXTERN void xz_crc32_init(void) {}
XZ_EXTERN uint32_t xz_crc32(const uint8_t *buf, size_t size, uint32_t crc)
{
    return ~crc32_le(~crc, buf, size);
}
''')
    build(crc)
    driver=xz/'driver';driver.mkdir()
    # Existing three-way driver retains exactly the same operation/timing code.
    shutil.copy2(ROOT/'test/evaluation/kernel-cost/observer.c',driver/'observer.c')
    p=driver/'observer.c';p.write_text(p.read_text().replace('matched-direct-kernel','owner-kernel-crc'))
    (driver/'Makefile').write_text('obj-m += xz_kernel_bench.o\nxz_kernel_bench-y := observer.o\n')
    build(driver,[owners/'xz/Module.symvers',crc/'Module.symvers'])
    save(xz/'intervention.json',dict(reference='unchanged formal owner with compact internal CRC32',
        variant='same owner decoder, features, helper slots and compiler options; CRC function delegates to kernel crc32_le',
        scope='kernel-only diagnostic; variant is not exported to userspace'))
    save(output/'plan.json',dict(status='prepared',loads=3,cpu=2,rounds=11,sample_ms=10,
        scope='separate kernel diagnostics, no registration or user timing'))
    print('Prepared BCH loop and XZ CRC diagnostics.')

def collect_bch(base,d,builds):
    import bch_kernel_audit as checker
    loaded=[]
    try:
        for name,path in [('vkso_bch',base/'owners/bch/vkso_bch.ko'),('bch_matched',builds/'reference/bch_matched.ko'),
                          ('bch_cached',builds/'cached/bch_cached.ko')]:
            command(['insmod',path],d/('load-'+name+'.log'));loaded.append(name)
        before=subprocess.check_output(['dmesg'],text=True)
        command(['taskset','-c','2','insmod',builds/'driver/bch_kernel_bench.ko','measure=1','correctness_vectors=128',
                 'outer_runs=11','sample_ms=10','aligned_inputs=1'],d/'load-driver.log');loaded.append('bch_kernel_bench')
        debug=Path('/sys/kernel/debug/bch_kernel_bench')
        for name in ('status','results','vectors'):(d/('driver-'+name+'.txt')).write_bytes((debug/name).read_bytes())
        (d/'driver-inputs.csv').write_bytes((debug/'inputs').read_bytes())
        window=new_log_window(before,subprocess.check_output(['dmesg'],text=True));(d/'dmesg-window.txt').write_text(window)
        assert not re.search(r'BUG:|WARNING:|status=fail',window)
        kallsyms=Path('/proc/kallsyms').read_text();(d/'kallsyms.txt').write_text(kallsyms)
        audit_bch_saved(d)
    finally:
        for name in reversed(loaded):command(['rmmod',name],d/('unload-'+name+'.log'))

def audit_bch_saved(d):
    import bch_kernel_audit as checker
    window=(d/'dmesg-window.txt').read_text()
    kallsyms=(d/'kallsyms.txt').read_text()
    for prefix,provider in [('matched_bch_','bch_matched'),('cached_bch_','bch_cached'),('vkso_bch_','vkso_bch')]:
        for method in ('init','free','encode','decode'):
            symbol=prefix+method
            address=re.findall(r'\b'+symbol+r'=([0-9a-f]+)',window);assert len(address)==1
            matches=[r.split() for r in kallsyms.splitlines() if len(r.split())==4 and r.split()[2]==symbol]
            assert len(matches)==1 and matches[0][0]==address[0]
            assert matches[0][1].lower()=='t' and matches[0][3]=='['+provider+']'
    checker.BACKENDS=BCH_BACKENDS
    audit=checker.audit(d,measure=True,expected_cpu=2,outer_runs=11,sample_ms=10,aligned_inputs=True)
    audit['scope']='physical-host source/helper intervention; full raw correctness and timing replay'
    save(d/'audit.json',audit)

def collect_xz(base,d,builds):
    loaded=[];backends=('stock-kernel','owner-kernel-crc','owner-kernel')
    debug=Path('/sys/kernel/debug/vkso_kernel_cost')
    prior=os.sched_getaffinity(0)
    try:
        os.sched_setaffinity(0,{2})
        for name,path in [('vkso_xz',base/'owners/xz/vkso_xz.ko'),('matched_xz',builds/'kernel-crc/matched_xz.ko'),
                          ('xz_kernel_bench',builds/'driver/xz_kernel_bench.ko')]:
            command(['insmod',path],d/('load-'+name+'.log'));loaded.append(name)
        status=(debug/'status').read_text();(d/'api-status.txt').write_text(status)
        symbols=Path('/proc/kallsyms').read_text();(d/'kallsyms.txt').write_text(symbols)
        for line in status.splitlines()[2:]:
            backend,*fields=line.split();index=backends.index(backend)
            for field in fields:
                method,address=field.split('=')
                if index==0 and method=='crc_init':assert int(address,16)==0;continue
                suffix={'init':'dec_init','run':'dec_run','reset':'dec_reset','end':'dec_end','crc_init':'crc32_init'}[method]
                name=('','matched_','vkso_')[index]+'xz_'+suffix
                provider=('',r'\s+\[matched_xz\]',r'\s+\[vkso_xz\]')[index]
                assert re.search(r'^'+address+r'\s+\w\s+'+name+provider+r'$',symbols,re.M),(name,address)
        def control(s):
            (debug/'control').write_text(s+'\n');assert (debug/'status').read_text().startswith('errno=0\n')
        measured=[];checks=[]
        for index,(label,plain,compressed) in enumerate(csv.reader((base/'corpus/xz/manifest.csv').open())):
            expected=Path(plain).read_bytes();control(f'LOAD {label} {plain} {compressed} 0')
            for repeat in range(11):
                for position in range(3):
                    b=(position+repeat+index)%3;control(f'RUN {b} {repeat} 10')
                    records=list(csv.DictReader(io.StringIO((debug/'results').read_text())));assert len(records)==1
                    r=records[0];assert r['backend']==backends[b] and r['status']=='pass'
                    assert int(r['cpu'])==2 and int(r['elapsed_ns'])>=10000000 and int(r['repeats'])>0
                    assert int(r['bytes'])==len(expected) and int(r['compressed_bytes'])==Path(compressed).stat().st_size
                    assert (debug/'output').read_bytes()==expected
                    measured.append(r);checks.append(dict(case=label,round=repeat,backend=backends[b],full_output_match=True))
        with (d/'raw.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(measured[0]));w.writeheader();w.writerows(measured)
        assert len(measured)==99
        save(d/'audit.json',dict(status='pass',raw_rows=len(measured),trials=checks,cpu=2,api_identity=True))
    finally:
        os.sched_setaffinity(0,prior)
        for name in reversed(loaded):command(['rmmod',name],d/('unload-'+name+'.log'))

def collect(base):
    assert os.geteuid()==0 and os.uname().release=='5.15.0-119-generic'
    output=base/'diagnostics';assert read(output/'plan.json')['status']=='prepared'
    for load in range(3):
        for a in (('bch','xz') if load%2==0 else ('xz','bch')):
            assert not {'vkso_bch','vkso_xz','bch_matched','bch_cached','matched_xz','page_cache_replace'} & modules().keys()
            d=output/a/f'load-{load:02d}'
            if d.exists():
                assert a=='bch' and (d/'driver-results.txt').exists()
                audit_bch_saved(d)
                assert all((d/('unload-'+n+'.log')).exists() for n in ('bch_kernel_bench','bch_cached','bch_matched','vkso_bch'))
                save(d/'complete.json',dict(status='pass',unloaded=True,replayed_after_parser_fix=True))
                print(f'{a} diagnostic load {load}: retained and verified',flush=True)
                continue
            d.mkdir()
            save(d/'identity.json',dict(kernel=os.uname().release,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),cpu=2))
            (collect_bch if a=='bch' else collect_xz)(base,d,output/a)
            save(d/'complete.json',dict(status='pass',unloaded=True));print(f'{a} diagnostic load {load}: complete',flush=True)
    save(output/'complete.json',dict(status='pass',loads_per_algorithm=3))
    analyze(base)

def analyze(base):
    output=base/'diagnostics';paired=[]
    for a in ('bch','xz'):
        for d in sorted((output/a).glob('load-*')):
            assert read(d/'complete.json')['status']=='pass'
            records=list(csv.DictReader((d/('driver-results.txt' if a=='bch' else 'raw.csv')).open()))
            groups=defaultdict(dict)
            for r in records:
                work=f"t={r['t']}/errors={r['errors']}/{r['mode']}" if a=='bch' else r['case']
                repeat=int(r['round' if a=='bch' else 'outer_run'])
                groups[work,repeat][r['backend']]=int(r['ns' if a=='bch' else 'elapsed_ns'])/int(r['iterations' if a=='bch' else 'repeats'])
            comparisons=(('cached-matched','original-matched'),('owner-kernel','cached-matched'),('owner-kernel','original-matched')) if a=='bch' else (('owner-kernel','owner-kernel-crc'),('owner-kernel-crc','stock-kernel'),('owner-kernel','stock-kernel'))
            for (work,repeat),values in groups.items():
                for t,b in comparisons:paired.append(dict(algorithm=a,load=d.name,workload=work,round=repeat,target=t,baseline=b,cost_ratio=values[t]/values[b]))
    def write(name,rows):
        with (output/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write('paired-rounds.csv',paired)
    groups=defaultdict(list)
    for r in paired:groups[tuple(r[k] for k in ('algorithm','load','workload','target','baseline'))].append(r['cost_ratio'])
    loads=[dict(zip(('algorithm','load','workload','target','baseline'),key),median_cost_ratio=stats.median(v)) for key,v in sorted(groups.items())]
    write('load-ratios.csv',loads);groups=defaultdict(list)
    for r in loads:groups[tuple(r[k] for k in ('algorithm','workload','target','baseline'))].append(r['median_cost_ratio'])
    summary=[]
    for key,v in sorted(groups.items()):
        assert len(v)==3
        summary.append(dict(zip(('algorithm','workload','target','baseline'),key),median_cost_ratio=stats.median(v),minimum_load_ratio=min(v),maximum_load_ratio=max(v)))
    write('summary.csv',summary)
    print('Diagnostic analysis complete.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','collect','analyze'));p.add_argument('directory',type=Path);a=p.parse_args()
    globals()[a.action](a.directory.resolve())
