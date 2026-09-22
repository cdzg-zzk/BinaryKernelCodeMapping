#!/usr/bin/env python3
"""User PMU diagnostics through real carriers; separate from formal samples."""
import argparse,csv,json,os,shutil,subprocess,sys
from pathlib import Path
import campaign
ROOT=campaign.ROOT

def prepare(base):
    out=base/'repeat-bch/user-pmu';out.mkdir()
    s=(base/'source-files/bch-bench-source/bch_bench.c').read_text()
    support=r'''
#include <linux/perf_event.h>
#include <sys/syscall.h>
#include <unistd.h>
static int pmu_fd=-1;
static FILE *pmu_output;
struct pmu_reading { uint64_t nr, enabled, running, counts[5]; };
static struct pmu_reading pmu_before, pmu_delta;
static const char *pmu_names[5]={"cycles","instructions","branch_misses","l1d_read_misses","ref_cycles"};
static void pmu_read(struct pmu_reading *value)
{
    if (read(pmu_fd,value,sizeof(*value)) != sizeof(*value) || value->nr != 5) {
        perror("PMU group read"); exit(2);
    }
}
static void pmu_begin(void)
{
    if (pmu_fd < 0) {
        uint64_t configs[5]={PERF_COUNT_HW_CPU_CYCLES,PERF_COUNT_HW_INSTRUCTIONS,PERF_COUNT_HW_BRANCH_MISSES,
            PERF_COUNT_HW_CACHE_L1D | (PERF_COUNT_HW_CACHE_OP_READ<<8) | (PERF_COUNT_HW_CACHE_RESULT_MISS<<16),
            PERF_COUNT_HW_REF_CPU_CYCLES};
        for (int i=0;i<5;i++) {
            struct perf_event_attr attr={.type=i==3?PERF_TYPE_HW_CACHE:PERF_TYPE_HARDWARE,
                .size=sizeof(attr),.config=configs[i],.exclude_kernel=1,.exclude_hv=1,.pinned=i==0,
                .read_format=PERF_FORMAT_GROUP|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING};
            int fd=syscall(__NR_perf_event_open,&attr,0,-1,pmu_fd,0);
            if (fd<0) {perror("perf_event_open");exit(2);}
            if (i==0) pmu_fd=fd;
        }
        pmu_output=fopen(getenv("PMU_OUTPUT"),"w");
        if (!pmu_output) {perror("PMU output");exit(2);}
        fprintf(pmu_output,"round,backend,t,errors,mode,iterations,ns,event,count,enabled,running\n");
    }
    pmu_read(&pmu_before);
}
static void pmu_end(void)
{
    pmu_read(&pmu_delta);
    pmu_delta.enabled-=pmu_before.enabled;pmu_delta.running-=pmu_before.running;
    for (int i=0;i<5;i++) pmu_delta.counts[i]-=pmu_before.counts[i];
}
'''
    s=s.replace('#define BACKEND_COUNT 3',support+'\n#define BACKEND_COUNT 3')
    for start,end in [('static uint64_t measure_context(', 'static uint64_t calibrate_context('),('static uint64_t measure_init(', 'static uint64_t calibrate_init(')]:
        a=s.index(start);b=s.index(end,a);part=s[a:b]
        first=part.index('\n\tif (clock_gettime' if 'context' in start else '\n\tclock_gettime')
        part=part[:first]+'\n\tpmu_begin();'+part[first:]
        part=part.replace('\treturn elapsed_ns(&start, &end);','\tpmu_end();\n\treturn elapsed_ns(&start, &end);')
        s=s[:a]+part+s[b:]
    a=s.index('static void write_row(');b=s.index('static void run_benchmark(',a);part=s[a:b]
    extra=r'''
    for (int i=0;i<5;i++) fprintf(pmu_output,"%d,%s,%d,%d,%s,%" PRIu64 ",%" PRIu64 ",%s,%" PRIu64 ",%" PRIu64 ",%" PRIu64 "\n",
        outer,backend->name,test->t,errors,mode,iterations,duration,pmu_names[i],pmu_delta.counts[i],pmu_delta.enabled,pmu_delta.running);
    fflush(pmu_output);
'''
    part=part.replace('\tfflush(output);','\tfflush(output);'+extra);s=s[:a]+part+s[b:]
    (out/'bench.c').write_text(s)
    subprocess.run(['gcc','-O2','-g',str(out/'bench.c'),'-ldl','-o',str(out/'bench')],check=True)
    campaign.save(out/'plan.json',dict(loads=3,rounds=11,sample_ms=10,correctness_vectors=128,source='same full user benchmark plus PMU group reads outside timing',purpose='explain Native/Adapted/VKSO generated-work differences',formal_population=False))

def run(base,d):
    out=base/'repeat-bch/user-pmu';results=d/'results';results.mkdir()
    libdir=d/'work/vkso/lib';carrier=libdir/'libvkso_bch.so'
    env={**os.environ,'LD_LIBRARY_PATH':str(libdir),'PMU_OUTPUT':str(results/'pmu.csv')}
    with (results/'user.log').open('w') as log:
        subprocess.run(['taskset','-c','2',str(out/'bench'),'--native',str(base/'builds/bch/libnative.so'),
            '--adapted',str(base/'builds/bch/libadapted.so'),'--kernel',str(carrier),'--outer','11','--sample-ms','10',
            '--correctness-vectors','128','--aligned-inputs','--output',str(results/'user.csv')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    data=list(csv.DictReader((results/'pmu.csv').open()));assert len(data)==5280
    assert all(int(r['running'])>0 and int(r['running'])>=.99*int(r['enabled']) for r in data)
    text=(results/'user.log').read_text();assert all(f'correctness: m=13 t={t} vectors=128 backends=3 ok' in text for t in (4,8))
    reference=list(csv.DictReader((base/'deployment-00-bch/results/user.csv.inputs.csv').open()))
    actual=list(csv.DictReader((results/'user.csv.inputs.csv').open()));assert actual==reference
    sys.path.insert(0,str(ROOT/'test/evaluation'))
    from section63_audit import entry_pages
    campaign.save(results/'audit.json',dict(status='pass',counter_rows=5280,timing_rows=1056,correctness_vectors=128,aligned_inputs=True,no_multiplexing=True,exports=entry_pages(d)))

def collect(base):
    assert os.geteuid()==0
    out=base/'repeat-bch/user-pmu';owner=base/'owners/bch/vkso_bch.ko';symbols=ROOT/'test/test_BCH/config/symbols.txt'
    for n in range(3):
        d=out/f'load-{n:02d}';d.mkdir();loaded=False
        assert not {'vkso_bch','bch_kernel_bench','bch_matched','page_cache_replace'} & campaign.modules().keys()
        with (d/'runner.log').open('w') as log:
            def command(args):subprocess.run(list(map(str,args)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            try:
                command(['insmod',owner]);loaded=True
                command([ROOT/'vkso','init',d/'work','--symbols',symbols])
                command([ROOT/'vkso','exec',d/'work','--symbols',symbols,'--module',owner,'--owner-ko',owner,'--shim-list',ROOT/'make_dll/shim.txt',
                    '--','python3',Path(__file__).resolve(),'run',base,'--load',d])
            finally:
                if loaded and campaign.modules().get('vkso_bch')==0:command(['rmmod','vkso_bch'])
        assert 'vkso_bch' not in campaign.modules()
        campaign.save(d/'complete.json',dict(status='pass',owner_unloaded=True));print(d.name+': complete',flush=True)
    campaign.save(out/'complete.json',dict(status='pass',loads=3))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','collect','run'));p.add_argument('directory',type=Path);p.add_argument('--load',type=Path);a=p.parse_args()
    if a.action=='run':run(a.directory.resolve(),a.load.resolve())
    else:globals()[a.action](a.directory.resolve())
