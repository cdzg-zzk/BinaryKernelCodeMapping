#!/usr/bin/env python3
"""Separate full-workload BCH PMU/context diagnostic; production modules unchanged."""
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import diagnose as diag

ROOT=Path(__file__).resolve().parents[3]
def prepare(base):
    out=base/'repeat-bch/pmu';out.mkdir(exist_ok=True)
    driver=out/'driver'
    if driver.exists(): shutil.rmtree(driver)
    diag.copy_source(base/'deployment-00-bch/prepared/kernel-cost-build/driver',driver)
    p=driver/'bch_kernel_bench.c';s=p.read_text().replace('#include <linux/module.h>','#include <linux/module.h>\n#include <linux/perf_event.h>')
    insertion=r'''
#define PMU_EVENTS 5
static struct perf_event *pmu_events[PMU_EVENTS];
static unsigned int context_rotation;
module_param(context_rotation, uint, 0444);
static void pmu_release(void)
{
    unsigned int i;
    for (i = 0; i < PMU_EVENTS; i++)
        if (pmu_events[i]) {
            perf_event_release_kernel(pmu_events[i]);
            pmu_events[i] = NULL;
        }
}
static int pmu_create(void)
{
    unsigned int i;
    const u32 types[PMU_EVENTS] = {PERF_TYPE_HARDWARE, PERF_TYPE_HARDWARE,
        PERF_TYPE_HARDWARE, PERF_TYPE_HW_CACHE, PERF_TYPE_HARDWARE};
    const u64 configs[PMU_EVENTS] = {PERF_COUNT_HW_CPU_CYCLES, PERF_COUNT_HW_INSTRUCTIONS,
        PERF_COUNT_HW_BRANCH_MISSES,
        PERF_COUNT_HW_CACHE_L1D | (PERF_COUNT_HW_CACHE_OP_READ << 8) |
        (PERF_COUNT_HW_CACHE_RESULT_MISS << 16), PERF_COUNT_HW_REF_CPU_CYCLES};
    for (i = 0; i < PMU_EVENTS; i++) {
        struct perf_event_attr attr = { .type = types[i], .size = sizeof(attr),
            .config = configs[i], .exclude_user = 1, .exclude_hv = 1, .pinned = 1 };
        pmu_events[i] = perf_event_create_kernel_counter(&attr, raw_smp_processor_id(), NULL, NULL, NULL);
        if (IS_ERR(pmu_events[i])) {
            int error = PTR_ERR(pmu_events[i]);
            pmu_events[i] = NULL;
            pmu_release();
            return error;
        }
    }
    return 0;
}
'''
    s=s.replace('struct measurement {',insertion+'\nstruct measurement {').replace('u64 iterations, ns, seed;','u64 iterations, ns, seed;\n\tu64 pmu[PMU_EVENTS], enabled[PMU_EVENTS], running[PMU_EVENTS];')
    start=s.index('static int time_batch(');end=s.index('\nstatic int calibrate(',start)
    part=s[start:end].replace('u64 start, end, i;', 'u64 start, end, i;\n\tu64 before[PMU_EVENTS], enabled[PMU_EVENTS], running[PMU_EVENTS];\n\tunsigned int event;')
    part=part.replace('start = ktime_get_ns();','for (event = 0; event < PMU_EVENTS; event++)\n\t\tbefore[event] = perf_event_read_value(pmu_events[event], &enabled[event], &running[event]);\n\tstart = ktime_get_ns();')
    part=part.replace('end = ktime_get_ns();','end = ktime_get_ns();\n\tfor (event = 0; event < PMU_EVENTS; event++) {\n\t\tu64 en, run;\n\t\trecord->pmu[event] = perf_event_read_value(pmu_events[event], &en, &run) - before[event];\n\t\trecord->enabled[event] = en - enabled[event];\n\t\trecord->running[event] = run - running[event];\n\t}')
    s=s[:start]+part+s[end:]
    pmuout=r'''
static int pmu_show(struct seq_file *stream, void *unused)
{
    unsigned int i, e;
    const char *names[PMU_EVENTS] = {"cycles", "instructions", "branch_misses", "l1d_read_misses", "ref_cycles"};
    seq_puts(stream, "round,backend,t,errors,mode,iterations,ns,event,count,enabled,running\n");
    for (i = 0; i < result_count; i++) {
        const struct measurement *r = &results[i];
        for (e = 0; e < PMU_EVENTS; e++)
            seq_printf(stream, "%d,%s,%u,%d,%s,%llu,%llu,%s,%llu,%llu,%llu\n",
                r->round, backends[r->backend].name, r->t, r->errors,
                operation_names[r->operation], r->iterations, r->ns, names[e],
                r->pmu[e], r->enabled[e], r->running[e]);
    }
    return 0;
}
DEFINE_SHOW_ATTRIBUTE(pmu);
'''
    s=s.replace('static int create_outputs(void)',pmuout+'\nstatic int create_outputs(void)')
    s=s.replace('entry = debugfs_create_file("status",', 'entry = debugfs_create_file("pmu", 0400, debug_directory, NULL, &pmu_fops);\n\tif (IS_ERR_OR_NULL(entry)) return -ENOMEM;\n\tentry = debugfs_create_file("status",')
    rotation=r'''
    {
        unsigned int c, k;
        for (c = 0; c < CASES; c++) {
            struct context original[BACKENDS];
            memcpy(original, cases[c].context, sizeof(original));
            for (k = 0; k < BACKENDS; k++) {
                struct context *ctx = &cases[c].context[k];
                *ctx = original[(k + context_rotation) % BACKENDS];
                pr_info(PREFIX "layout t=%u backend=%s rotation=%u control=%px pow=%px log=%px ecc=%px syn=%px elp=%px work=%px difference=%px\n",
                    cases[c].t, backends[k].name, context_rotation, ctx->control,
                    ctx->control->a_pow_tab, ctx->control->a_log_tab, ctx->control->ecc_buf,
                    ctx->control->syn, ctx->control->elp, ctx->work, ctx->difference);
            }
        }
    }
'''
    s=s.replace('stage = "correctness";',rotation+'\n\tstage = "correctness";')
    s=s.replace('stage = "calibration";', 'stage = "pmu-create";\n\t\terror = pmu_create();\n\t\tif (error) goto fail;\n\t\tstage = "calibration";')
    s=s.replace('\tfree_cases();','\tpmu_release();\n\tfree_cases();')
    # Retain the same six allocated contexts across three complete phases.
    s=s.replace('\tpmu_release();\n\tfree_cases();\n\tstage = "outputs";', '\tstage = "outputs";')
    s=s.replace('static void __exit bch_kernel_bench_exit(void)\n{', 'static void __exit bch_kernel_bench_exit(void)\n{\n\tpmu_release();\n\tfree_cases();')
    advance=r'''
static unsigned int advance_count;
static ssize_t advance_write(struct file *file, const char __user *buffer,
                             size_t count, loff_t *position)
{
    unsigned int c, k;
    int error;
    if (count != 5 || advance_count >= 2 || check_cpu()) return -EINVAL;
    for (c = 0; c < CASES; c++) {
        struct context previous[BACKENDS];
        memcpy(previous, cases[c].context, sizeof(previous));
        for (k = 0; k < BACKENDS; k++) cases[c].context[k] = previous[(k+1)%BACKENDS];
    }
    advance_count++;
    context_rotation = (context_rotation+1)%BACKENDS;
    for (c = 0; c < CASES; c++) for (k = 0; k < BACKENDS; k++) {
        struct context *ctx=&cases[c].context[k];
        pr_info(PREFIX "layout t=%u backend=%s rotation=%u control=%px pow=%px log=%px ecc=%px syn=%px elp=%px work=%px difference=%px\n",
            cases[c].t, backends[k].name, context_rotation, ctx->control,
            ctx->control->a_pow_tab, ctx->control->a_log_tab, ctx->control->ecc_buf,
            ctx->control->syn, ctx->control->elp, ctx->work, ctx->difference);
    }
    passed=false; vector_count=0; result_count=0; parity_checks=4;
    memset(decode_checks,0,sizeof(decode_checks));
    memset(vectors,0,vector_capacity*sizeof(*vectors));
    memset(results,0,result_capacity*sizeof(*results));
    stage="correctness"; error=correctness();
    if (!error) { stage="measurement"; error=benchmark(); }
    if (error) { terminal_errno=error; return error; }
    passed=true; stage="complete"; return count;
}
static const struct file_operations advance_fops = { .owner=THIS_MODULE, .write=advance_write };
'''
    s=s.replace('static int create_outputs(void)',advance+'\nstatic int create_outputs(void)')
    s=s.replace('entry = debugfs_create_file("pmu",','entry = debugfs_create_file("advance", 0200, debug_directory, NULL, &advance_fops);\n\tif (IS_ERR_OR_NULL(entry)) return -ENOMEM;\n\tentry = debugfs_create_file("pmu",')
    p.write_text(s)
    diag.build(driver,[base/'owners/bch/Module.symvers',base/'deployment-00-bch/prepared/kernel-cost-build/matched/Module.symvers'])
    diag.save(out/'plan.json',dict(scope='separate instrumented kernel diagnostic, no formal timing replacement',events=['cycles','instructions','branch_misses','l1d_read_misses','ref_cycles'],context_rotations=[0,1,2],loads=3,phases_per_load=3,within_load_same_allocated_contexts=True,rounds=11,full_workload=True,question='Does variation follow a fixed allocated context when reassigned to another algorithm within the same load?'))
    print('Prepared PMU and context-rotation diagnostic.')

def collect(base):
    assert os.geteuid()==0
    out=base/'repeat-bch/pmu';payload=base/'deployment-00-bch/prepared/payload/kernel-cost'
    for n,rotation in enumerate((0,1,2)):
        d=out/f'load-{n:02d}';d.mkdir();loaded=[]
        assert not {'vkso_bch','bch_matched','bch_kernel_bench','page_cache_replace'} & diag.modules().keys()
        try:
            for name,path in [('bch',payload/'bch.ko'),('vkso_bch',base/'owners/bch/vkso_bch.ko'),('bch_matched',payload/'bch_matched.ko')]:
                if name=='bch' and name in diag.modules():continue
                diag.command(['insmod',path],d/('load-'+name+'.log'));loaded.append(name)
            before=subprocess.check_output(['dmesg'],text=True)
            diag.command(['taskset','-c','2','insmod',out/'driver/bch_kernel_bench.ko','measure=1','correctness_vectors=128','outer_runs=11','sample_ms=10','aligned_inputs=1',f'context_rotation={rotation}'],d/'load-driver.log');loaded.append('bch_kernel_bench')
            debug=Path('/sys/kernel/debug/bch_kernel_bench')
            for phase in range(3):
                sub=d/f'phase-{phase:02d}';sub.mkdir()
                if phase:
                    prior=os.sched_getaffinity(0)
                    try:
                        os.sched_setaffinity(0,{2});(debug/'advance').write_text('next\n')
                    finally:os.sched_setaffinity(0,prior)
                for name in ('status','results','vectors'):(sub/('driver-'+name+'.txt')).write_bytes((debug/name).read_bytes())
                (sub/'driver-inputs.csv').write_bytes((debug/'inputs').read_bytes());(sub/'pmu.csv').write_bytes((debug/'pmu').read_bytes())
                window=diag.new_log_window(before,subprocess.check_output(['dmesg'],text=True));(sub/'dmesg-window.txt').write_text(window)
                (sub/'kallsyms.txt').write_text(Path('/proc/kallsyms').read_text())
                import bch_kernel_audit as checker
                audit=checker.audit(sub,measure=True,expected_cpu=2,outer_runs=11,sample_ms=10,aligned_inputs=True)
                counters=list(csv.DictReader((sub/'pmu.csv').open()))
                assert len(counters)==5280
                assert all(int(r['running'])>0 and int(r['running'])>=.99*int(r['enabled']) for r in counters)
                audit.update(rotation=(rotation+phase)%3,phase=phase,pmu_rows=len(counters),no_multiplexing=True)
                diag.save(sub/'audit.json',audit)
                print(f'{d.name} phase {phase}: complete',flush=True)
        finally:
            for name in reversed(loaded):diag.command(['rmmod',name],d/('unload-'+name+'.log'))
        diag.save(d/'complete.json',dict(status='pass',initial_rotation=rotation,phases=3,unloaded=True))
    diag.save(out/'complete.json',dict(status='pass',loads=3,phases_per_load=3))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','collect'));p.add_argument('directory',type=Path);a=p.parse_args();globals()[a.action](a.directory.resolve())
