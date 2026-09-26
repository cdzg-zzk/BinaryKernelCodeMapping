#!/usr/bin/env python3
"""Instrumented UPDATE/concurrent protocol; fixed shell entrypoints dispatch here."""
import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import csv
import fcntl
import gzip
import json
import mmap
import os
from pathlib import Path
import platform
import re
import select
import shutil
import signal
import statistics
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
DIRECT = HERE.parent / 'direct-api'
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, str(DIRECT))
from bundle import REQUIRED, audit_binary, audit_public_library, kv_file, sha256, verify_sums, write_json
from campaign import plan, atomic, archive
from collect import logged, must, cpu_list
from results import validate_sharing, summarize as summarize_read, summarize_kernel
from package_check import check as check_read_package
from mapping_census import COUNTS as CENSUS_COUNTS, PROTOCOL as CENSUS_PROTOCOL, summarize as census_summarize
import workflow
PROTOCOL = 'clocktime-stateful-v1'
SCENARIOS = ('idle', 'monotonic', 'monotonic_raw', 'monotonic_coarse')
PMU_EVENTS = ('l2_rqsts.rfo_hit', 'l2_rqsts.rfo_miss',
              'ocr.demand_rfo.l3_hit.snoop_hitm')
BARE = HERE.parent / 'baremetal'


def full_plan(blocks):
    """One clean and one instrumented boot per implementation in every block."""
    return [dict(entry, mode=mode) for entry in plan(blocks)
            for mode in ('read', 'update')]


def seal(root):
    with (root/'SHA256SUMS').open('w') as f:
        for p in sorted(root.rglob('*')):
            if p.is_file() and not p.is_symlink() and p != root/'SHA256SUMS':
                f.write(sha256(p)+'  '+str(p.relative_to(root))+'\n')


def check(package):
    must((package/'SHA256SUMS').is_file(),
         'package is absent or incomplete (missing SHA256SUMS): '+str(package)+
         '; finish the build before verify/install')
    outer = verify_sums(package, REQUIRED | {'direct/build.json','direct/SHA256SUMS',
        'direct/native-load','direct/vkso-load','direct/libvkso_time.so',
        'direct/native-bench.sections.txt','direct/vkso-bench.sections.txt',
        'direct/libvkso_time.so.sections.txt'})
    m = kv_file(package/'boot-manifest.txt')
    must(m.get('update_bench') == '1' and m.get('vkso_validation_tests') == '0', 'requires UPDATE instrumentation, no validation probes')
    stage_flag=m.get('update_stage_diag','0')
    must(stage_flag in ('0','1'), 'invalid stage diagnosis package flag')
    split_flag=m.get('update_split_diag','0')
    must(split_flag in ('0','1') and (split_flag=='0' or stage_flag=='1'),
         'invalid split diagnosis package flag')
    prep_flag=m.get('raw_cacheprep_diagnostic','0')
    must(prep_flag in ('0','1') and (prep_flag=='0' or
         (m['build_variant']=='normal' and
          m.get('config_difference')=='diagnostic_raw_cacheprep_only' and
          len(m.get('raw_update_bench_header_sha256',''))==64 and
          len(m.get('raw_update_bench_recorder_sha256',''))==64)),
         'invalid Raw cache-preparation diagnosis package')
    prefetch_flag=m.get('raw_prefetch_diagnostic','0')
    must(prefetch_flag in ('0','1') and
         (prefetch_flag=='0' or prep_flag=='1'),
         'invalid Raw prefetch diagnosis package')
    order_flag=m.get('raw_order_diagnostic','0')
    must(order_flag in ('0','1') and
         (order_flag=='0' or
          (prep_flag=='1' and 'raw-update-disassembly.txt' in outer and
           'timekeeping_update' in
           (package/'raw-update-disassembly.txt').read_text())),
         'invalid Raw order diagnosis package')
    percall_flag=m.get('raw_percall_pmu_diagnostic','0')
    must(percall_flag in ('0','1') and not (percall_flag=='1' and prep_flag=='1') and
         (percall_flag=='0' or
          (m['build_variant']=='normal' and
           m.get('config_difference')=='diagnostic_raw_percall_pmu_only' and
           len(m.get('raw_update_bench_header_sha256',''))==64 and
           len(m.get('raw_update_bench_recorder_sha256',''))==64)),
         'invalid Raw per-call PMU diagnosis package')
    d = package/'direct'
    verify_sums(d, {'build.json','native-load','vkso-load','native-bench',
                    'vkso-bench','libvkso_time.so','native-bench.sections.txt',
                    'vkso-bench.sections.txt','libvkso_time.so.sections.txt'})
    b = json.loads((d/'build.json').read_text())
    must(b['protocol'] == PROTOCOL and b['scope'] == 'update', 'legacy/READ package; build explicit update public bundle')
    must(all(outer.get(k) == v for k,v in b['kernel_checksums'].items()), 'kernel inventory differs from linked public bundle')
    must(b['carrier_sha256'] == outer['libkernel.so'] and b['package_manifest_sha256'] == outer['boot-manifest.txt'], 'carrier identity mismatch')
    for name,digest in b['source_hashes'].items():
        must(sha256(d/'src'/name) == digest, 'public source identity mismatch: '+name)
    must(b['compiler_version'] == m['cc_version'] == '11.4.0', 'compiler mismatch')
    must(b['build_variant'] == m['build_variant'], 'variant mismatch')
    must(os.path.samefile(d/'carrier/libkernel.so',package/'libkernel.so'), 'carrier inode differs')
    for backend in ('raw','vkso'):
        config_text=(package/(backend+'.config')).read_text()
        must('CONFIG_TIMEKEEPING_UPDATE_BENCH=y\n' in config_text,
             'instrumentation absent')
        must(('CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG=y\n' in config_text)==
             (stage_flag=='1'), 'stage diagnosis config/manifest mismatch')
        must(('CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG=y\n' in config_text)==
             (prep_flag=='1' and backend=='raw'),
             'cache-preparation diagnosis config/manifest mismatch')
        must(('CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG=y\n' in config_text)==
             (percall_flag=='1' and backend=='raw'),
             'per-call PMU diagnosis config/manifest mismatch')
    audit_public_library(d/'libvkso_time.so')
    for backend in ('native','vkso'):
        audit_binary(d/(backend+'-bench'),backend)
        binary = d/(backend+'-load')
        nm = subprocess.check_output(['nm','-u',str(binary)],text=True)
        dyn = subprocess.check_output(['readelf','-dW',str(binary)],text=True)
        must(not any(x in nm for x in ('dlsym','dlopen','dlvsym')), 'dynamic provider lookup')
        must('clock_gettime@' in nm or ' clock_gettime\n' in nm, 'no public clock entry')
        must(('[libvkso_time.so]' in dyn) == (backend == 'vkso'), 'wrong linked provider')
    return b


def config():
    c = kv_file(HERE/'update-experiment.conf')
    for key in ('BLOCKS','REPEATS','UPDATE_SECONDS','READER_ITERATIONS',
                'WARMUP','STABILIZE_SECONDS','CPU','READ_ITERATIONS',
                'READ_REPEATS','READ_PROCESSES','READ_WARMUP'):
        c[key] = int(c[key])
    must(1 <= c['BLOCKS'] <= 100 and 1 <= c['REPEATS'] <= 1000, 'invalid blocks/repeats')
    must(1 <= c['UPDATE_SECONDS'] <= 60 and 10000 <= c['READER_ITERATIONS'] <= 1000000, 'invalid window/batch')
    must(0 <= c['WARMUP'] <= 1000000 and c['STABILIZE_SECONDS'] >= 0, 'invalid warmup')
    must(c['CPU'] == 2 and c['HOUSEKEEPING_CPUS'] == '0-1,3', 'installed update boot layout requires CPU=2, housekeeping=0-1,3')
    must(c['BENCH_SCOPE'] == 'all' and c['BLOCKS'] >= 3, 'full campaign requires all phases and at least three boots per case')
    must(1 <= c['READ_PROCESSES'] <= c['READ_REPEATS'] <= 1000 and
         0 < c['READ_ITERATIONS'] <= 1000000 and 0 <= c['READ_WARMUP'] <= 1000000,
         'invalid READ batch/repetition settings')
    read_config=kv_file(BARE/'experiment.conf')
    for key,source in [('CPU','CPU'),('READ_ITERATIONS','ITERATIONS'),
                       ('READ_REPEATS','REPEATS'),('READ_PROCESSES','PERF_PROCESSES'),
                       ('READ_WARMUP','WARMUP')]:
        must(c[key] == int(read_config[source]), 'READ and full campaign configs disagree: '+key)
    return c


def compatible(package):
    b=check(package)
    for name in ('stateful_reader.c','time_bench.c','vkso_public.c','vkso_time_init.c','vkso_time.h','Makefile'):
        must(sha256(DIRECT/name)==b['source_hashes']['direct-api/'+name], 'compiled source changed; use bench rebuild: '+name)
    return b


def tools_snapshot(root):
    directory = root/'tools'/str(time.time_ns())
    needed = {
        HERE: ('stateful.py', 'boot-update-once.sh', 'update-experiment.conf'),
        DIRECT: ('bundle.py', 'campaign.py', 'collect.py', 'results.py',
                 'package_check.py', 'workflow.py', 'sharing.py', 'mapping_census.py'),
        BARE: ('boot-once.sh', 'collect-case.sh', 'experiment.conf', 'experiment.sh'),
    }
    for source, names in needed.items():
        target = directory/source.name
        target.mkdir(parents=True)
        for name in names:
            shutil.copy2(source/name,target/name)
    seal(directory)
    return directory.relative_to(root).as_posix()


def tools_current_match(snapshot):
    entries = verify_sums(snapshot)
    source = HERE.parent
    for name, digest in entries.items():
        must(sha256(source/name) == digest,
             'campaign tool changed; run experiment.sh refresh-tools: '+name)


def package_identity(package):
    return dict(path=str(package), sha256=sha256(package/'SHA256SUMS'),
                direct_sha256=sha256(package/'direct/SHA256SUMS'))


def check_all_packages(packages):
    read = packages['read']; update = packages['update']
    subprocess.run([str(BARE/'verify-packages.sh'),
                    *(str(read[v]) for v in ('normal','no-retpoline'))], check=True)
    subprocess.run([str(HERE/'verify-update-packages.sh'),
                    *(str(update[v]) for v in ('normal','no-retpoline'))], check=True)
    source_ids = set(); source_fingerprints = set(); libraries = set()
    for mode, variants in packages.items():
        for variant, package in variants.items():
            if mode == 'read':
                build = check_read_package(package)
                workflow.compatible(DIRECT, package)
            else:
                build = compatible(package)
            manifest = kv_file(package/'boot-manifest.txt')
            must(manifest.get('raw_cacheprep_diagnostic','0')=='0',
                 'Raw cache-preparation package is diagnostic-only, not a formal campaign package')
            must(manifest.get('raw_percall_pmu_diagnostic','0')=='0',
                 'Raw per-call PMU package is diagnostic-only, not a formal campaign package')
            must(manifest['build_variant'] == variant, 'package variant mismatch')
            source_ids.add((manifest['git_commit'], manifest['candidate_patch_sha256'],
                            manifest['vkso_source_tree_sha256']))
            source_fingerprints.add(build['source_fingerprint'])
            libraries.add(sha256(package/'direct/libvkso_time.so'))
    must(len(source_ids) == 1, 'clean and instrumented kernels must be built from the same VKSO source and patch')
    must(len(source_fingerprints) == 1 and len(libraries) == 1,
         'public API source/library differs among the eight images')


@contextmanager
def tune(record):
    saved = []; irq = False
    record['tuning_before'] = {}; record['tuning_after'] = {}
    try:
        paths = [(Path('/sys/devices/system/cpu/intel_pstate')/k,v) for k,v in
                 [('no_turbo','1'),('max_perf_pct','100'),('min_perf_pct','100')]]
        governors = list(Path('/sys/devices/system/cpu/cpufreq').glob('policy*/scaling_governor'))
        must(bool(governors), 'no cpufreq governors')
        paths += [(p,'performance') for p in governors]
        for p,value in paths:
            old = p.read_text().strip(); record['tuning_before'][str(p)] = old
            if old != value:
                saved.append((p,old)); p.write_text(value+'\n')
            must(p.read_text().strip() == value, 'tuning failed: '+str(p))
        irq = subprocess.run(['systemctl','is-active','--quiet','irqbalance']).returncode == 0
        record['irqbalance_was_active'] = irq
        if irq: subprocess.run(['systemctl','stop','irqbalance'],check=True)
        yield
    finally:
        errors = []
        for p,old in reversed(saved):
            try:
                if p.read_text().strip() != old: p.write_text(old+'\n')
                must(p.read_text().strip() == old, 'restore mismatch: '+str(p))
            except Exception as e: errors.append(str(e))
        if irq:
            if subprocess.run(['systemctl','start','irqbalance']).returncode: errors.append('irqbalance restore failed')
        for name in record['tuning_before']:
            try: record['tuning_after'][name] = Path(name).read_text().strip()
            except OSError as e: errors.append(str(e))
        record['environment_cleanup'] = 'FAIL' if errors else 'PASS'
        if errors: raise RuntimeError('; '.join(errors))


def preflight(package, case, c):
    b = check(package); backend,variant = case.split('-',1)
    m = kv_file(package/'boot-manifest.txt')
    must(not any(os.environ.get(k) for k in ('LD_PRELOAD','LD_LIBRARY_PATH','LD_AUDIT')), 'remove loader overrides')
    must(variant == m['build_variant'], 'wrong package variant')
    must(platform.release() == '5.15.198' and platform.version() == m[backend+'_uts_version'], 'wrong kernel build; boot the instrumented image')
    with gzip.open('/proc/config.gz','rb') as f:
        must(f.read() == (package/(backend+'.config')).read_bytes(), 'running config mismatch')
    args = Path('/proc/cmdline').read_text().split()
    image = 'vkso-update-'+case+'-5.15.198.bzImage'
    boot = next((x.split('=',1)[1] for x in args if x.startswith('BOOT_IMAGE=')), '')
    must(Path(boot).name == image and sha256(Path('/boot')/image) == sha256(package/(backend+'-bzImage')), 'boot image mismatch')
    for required in ('nokaslr','nosmt','clocksource=tsc','tsc=reliable','isolcpus=domain,managed_irq,2',
                     'nohz_full=2','rcu_nocbs=2','irqaffinity=0-1,3','idle=poll','nmi_watchdog=0','nowatchdog','audit=0'):
        must(required in args, 'missing boot control: '+required)
    must(Path('/sys/devices/system/clocksource/clocksource0/current_clocksource').read_text().strip() == 'tsc', 'not TSC')
    must(Path('/sys/devices/system/cpu/smt/active').read_text().strip() == '0', 'SMT active')
    must(c['CPU'] in cpu_list(Path('/sys/devices/system/cpu/isolated').read_text()), 'reader CPU not isolated')
    must({0,c['CPU']} <= os.sched_getaffinity(0), 'required CPUs unavailable')
    modules = Path('/proc/modules').read_text().splitlines()
    must(not any(x.split()[0] in ('page_cache_replace','vkso_m09_clock','vkso_kernel_reader') for x in modules), 'prior test module still loaded; recover first')
    probe = subprocess.check_output(['setarch','x86_64','-R',str(package/'direct/native-bench'),'--probe'],text=True)
    fields = dict(x.split('=',1) for x in probe.splitlines())
    must(fields['native_vdso'] == ('1' if backend == 'raw' else '0') and fields['vkso_mm_auxv'] == ('0' if backend == 'raw' else '1'), 'wrong auxv backend')
    return dict(protocol=PROTOCOL,case=case,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                kernel_uts=platform.version(),cmdline=args,config=c,package=str(package),
                package_sha256=sha256(package/'SHA256SUMS'),bundle_sha256=sha256(package/'direct/SHA256SUMS'),
                build=b,probe=fields,counter_unit='TSC ticks',status='RUNNING')


def writer_rows(path):
    lines = path.read_text().splitlines()
    import re
    header = next((x for x in lines if x.startswith('#') and 'dropped=' in x), '')
    dropped = re.search(r'\bdropped=(\d+)', header)
    must(dropped is not None and int(dropped[1]) == 0, 'writer missing metadata or overflow')
    start = next((i for i,x in enumerate(lines) if x.startswith('sample,')), None)
    must(start is not None, 'missing writer CSV header')
    rows = list(csv.DictReader(lines[start:]))
    must(bool(rows), 'empty writer samples')
    seen=re.search(r'\bseen=(\d+)',header)
    must(seen is not None and int(seen[1])==len(rows), 'writer sample count mismatch')
    for i,r in enumerate(rows):
        must(int(r['sample']) == i and int(r['cycles']) > 0 and int(r['cpu']) >= 0 and int(r['action']) >= 0, 'invalid writer row')
    normal = [int(x['cycles']) for x in rows if int(x['action']) == 0]
    must(bool(normal), 'no periodic updates')
    return dict(median_ticks=statistics.median(normal),mean_ticks=statistics.fmean(normal),count=len(normal),
                other_actions=len(rows)-len(normal),cpu_counts=dict(Counter(x['cpu'] for x in rows)),dropped=0)


DIAG_FIELDS = {'phase_nsec','ktime_carry','realtime_carry',
               'monotonic_carry','leap_pending','clock_mode','shift'}
STAGE_FIELDS = ('prep_ticks','ktime_ticks','first_publish_ticks',
                'second_publish_ticks','base_real_ticks','fast_mono_ticks',
                'fast_raw_ticks','tail_ticks')
SPLIT_PARTS = {'raw':(1,2), 'vkso':(2,3)}
SPLIT_SCENARIOS = ('idle','monotonic')


def diagnostic_rows(path, staged=False, split_part=None):
    lines = path.read_text().splitlines()
    header = next((i for i,line in enumerate(lines) if line.startswith('sample,')), None)
    must(header is not None, 'missing diagnostic sample header')
    rows = list(csv.DictReader(lines[header:]))
    must(bool(rows) and DIAG_FIELDS <= set(rows[0]), 'diagnostic state columns missing')
    if staged:
        import re
        stage_header=next((line for line in lines if line.startswith('# stage_schema=')), '')
        match=re.fullmatch(r'# stage_schema=1 invalid_stages=(\d+)',stage_header)
        must(match is not None and int(match[1])==0,
             'missing stage schema or invalid stage timestamps')
        must(set(STAGE_FIELDS) <= set(rows[0]), 'stage timing columns missing')
    if split_part is not None:
        must(not staged, 'split and full-stage schemas cannot mix')
        expected=f'# split_schema=1 split_part={split_part} invalid_splits=0'
        must(expected in lines and {'prefix_ticks','suffix_ticks'} <= set(rows[0]),
             'split timing schema or timestamps missing')
    for row in rows:
        must(0 <= int(row['phase_nsec']) < 1000000000 and
             all(int(row[field]) in (0,1) for field in
                 ('ktime_carry','realtime_carry','monotonic_carry','leap_pending')) and
             0 <= int(row['shift']) <= 32, 'invalid diagnostic state')
        if staged:
            parts=[int(row[field]) for field in STAGE_FIELDS]
            must(all(value>0 for value in parts) and sum(parts)==int(row['cycles']),
                 'stage intervals do not cover complete update')
        if split_part is not None:
            prefix,suffix=int(row['prefix_ticks']),int(row['suffix_ticks'])
            must(prefix>0 and suffix>0 and prefix+suffix==int(row['cycles']),
                 'split intervals do not cover complete update')
    calibration = path.with_name(path.stem+'-calibration.csv')
    lines = calibration.read_text().splitlines()
    must(lines[:2] == ['# cpu=0 unit=TSC_ticks','sample,ticks'],
         'invalid TSC calibration header')
    pairs = list(csv.DictReader(lines[1:]))
    must(len(pairs) == 4096 and all(int(row['sample']) == i and
         int(row['ticks']) > 0 for i,row in enumerate(pairs)),
         'invalid TSC pair distribution')
    ticks=[int(row['ticks']) for row in pairs]
    metadata=next((line for line in path.read_text().splitlines() if line.startswith('# tsc_pair_min=')), '')
    must(metadata and int(metadata.split('tsc_pair_min=')[1].split()[0])==min(ticks),
         'TSC pair minimum differs from writer metadata')
    return rows,ticks


def reader_rows(path, batch):
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    must(bool(rows), 'empty reader')
    for i,r in enumerate(rows):
        must(int(r['batch']) == i and int(r['calls']) == batch and int(r['tsc_ticks']) > 0 and r['aux_start'] == r['aux_end'], 'invalid reader batch/migration')
    must(len({r['aux_start'] for r in rows}) == 1, 'reader migrated between batches')
    return dict(batches=len(rows),median_ticks_per_call=statistics.median(int(r['tsc_ticks'])/batch for r in rows))


def perf_binary():
    candidates=sorted(Path('/usr/lib').glob('linux-tools-*/perf'),reverse=True)
    candidates += [Path('/usr/bin/perf')]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate,os.X_OK):
            version=subprocess.run([str(candidate),'--version'],text=True,
                                   capture_output=True)
            if version.returncode==0 and version.stdout.startswith('perf version '):
                return candidate,version.stdout.strip()
    raise ValueError('install a working perf binary')


def perf_control(write_fd,read_fd,process,command):
    must(process.poll() is None,'perf recorder exited: '+command)
    os.write(write_fd,(command+'\n').encode())
    ready,_,_=select.select([read_fd],[],[],15)
    must(bool(ready),'perf control timeout: '+command)
    reply=os.read(read_fd,64)
    must(reply in (b'ack\n',b'ack\n\x00'),
         'perf control failure: '+command+' '+repr(reply))


def pt_capture(recorder,dest,perf,seconds,filter_symbol='timekeeping_update'):
    """Trace the writer's function without adding a timestamp to its body."""
    pt=dest.with_name(dest.stem+'-pt')
    log=dest.with_name(dest.stem+'-pt.log')
    must(filter_symbol in ('timekeeping_update','update_vsyscall','timekeeping_advance'),
         'unsupported Intel PT target')
    filter_text='filter '+filter_symbol
    read_ctl,write_ctl=os.pipe()
    read_ack,write_ack=os.pipe()
    process=None
    try:
        command=['taskset','-c','1',str(perf),'record','-q','--kcore',
                 '--max-size','256M','-D','-1',
                 '-e','intel_pt/tsc=1,cyc=1/k','--filter',filter_text,
                 '-C','0','--control',f'fd:{read_ctl},{write_ack}',
                 '-o',str(pt),'--','sleep','30']
        with log.open('xb') as stream:
            process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,
                                     pass_fds=(read_ctl,write_ack))
            os.close(read_ctl);read_ctl=-1
            os.close(write_ack);write_ack=-1
            perf_control(write_ctl,read_ack,process,'ping')
            perf_control(write_ctl,read_ack,process,'enable')
            start_seen=int(kv_file(recorder/'control')['seen'])
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                must(process.poll() is None,'Intel PT recorder exited during capture')
                time.sleep(min(.05,max(0,deadline-time.monotonic())))
            end_seen=int(kv_file(recorder/'control')['seen'])
            perf_control(write_ctl,read_ack,process,'disable')
            perf_control(write_ctl,read_ack,process,'stop')
            exit_code=process.wait(timeout=30)
        data=pt/'data'
        must(data.is_file() and data.stat().st_size>4096,
             'Intel PT output missing or empty (perf exit '+str(exit_code)+'): '+str(pt)+
             '; inspect '+str(log))
        must(end_seen-start_seen>=500,'too few writer samples under Intel PT')
        return dict(data=str(data),data_bytes=data.stat().st_size,
                    perf_exit_code=exit_code,
                    filter=filter_text,event='intel_pt/tsc=1,cyc=1/k',
                    requested_seconds=seconds,
                    traced_sample_start=start_seen,traced_sample_end=end_seen)
    finally:
        if process is not None and process.poll() is None:
            try:
                os.write(write_ctl,b'stop\n')
                process.wait(timeout=10)
            except (OSError,subprocess.TimeoutExpired):
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill();process.wait()
        for fd in (read_ctl,write_ctl,read_ack,write_ack):
            if fd>=0: os.close(fd)


def pt_shape(path,interval,backend):
    """Describe complete UPDATE times around the trace, without attributing a cause."""
    lines=path.read_text().splitlines()
    header=next(i for i,line in enumerate(lines) if line.startswith('sample,'))
    rows=list(csv.DictReader(lines[header:]))
    rows=[r for r in rows if int(r['action'])==0 and int(r['cpu'])==0]
    start=interval['traced_sample_start']; end=interval['traced_sample_end']
    guard=50
    groups={
        'before':[r for r in rows if int(r['sample'])<start-guard],
        'traced':[r for r in rows if start+guard<=int(r['sample'])<end-guard],
        'after':[r for r in rows if int(r['sample'])>=end+guard],
    }
    threshold=120 if backend=='raw' else 110
    def summarize(group):
        ticks=[int(r['cycles']) for r in group]
        if not ticks: return dict(samples=0,distribution_sufficient=False)
        return dict(samples=len(ticks),distribution_sufficient=len(ticks)>=500,
                    median_ticks=statistics.median(ticks),
                    high_fraction_at_historical_valley=
                        sum(t>threshold for t in ticks)/len(ticks),
                    histogram=dict(sorted(Counter(ticks).items())))
    return dict(protocol='clocktime-update-pt-shape-pilot-v1',
                unit='TSC ticks',historical_valley_threshold=threshold,
                boundary_guard_samples=guard,
                note='descriptive within one boot; PT changes the observation environment; '
                     'sample indices are not automatically aligned to PT packets',
                groups={name:summarize(group) for name,group in groups.items()})


def business_shape(path,interval):
    """Keep phase and carry strata for the PT-covered Raw UPDATE interval."""
    lines=path.read_text().splitlines()
    header=next(i for i,line in enumerate(lines) if line.startswith('sample,'))
    rows=list(csv.DictReader(lines[header:]))
    start=interval['traced_sample_start']+50
    end=interval['traced_sample_end']-50
    rows=[row for row in rows if start<=int(row['sample'])<end and
          int(row['action'])==0 and int(row['cpu'])==0]
    def group(items):
        ticks=[int(row['cycles']) for row in items]
        return dict(samples=len(ticks),median_ticks=statistics.median(ticks) if ticks else None,
                    high_fraction_at_historical_valley=(sum(t>120 for t in ticks)/len(ticks)
                                                         if ticks else None))
    phase=lambda row:int(row['phase_nsec'])//1000000
    bands={'second_start_0_40ms':[row for row in rows if phase(row)<40],
           'interior_40_900ms':[row for row in rows if 40<=phase(row)<900],
           'second_end_900_1000ms':[row for row in rows if phase(row)>=900]}
    must(len(bands['second_start_0_40ms'])>=10 and
         len(bands['interior_40_900ms'])>=500,
         'too few PT-covered UPDATE samples for business phase analysis')
    return dict(protocol='clocktime-update-business-path-pilot-v1',
                scope='PT-covered Raw UPDATE calls, excluding 50 calls at each edge',
                unit='TSC ticks',historical_valley_threshold=120,
                phase={name:group(items) for name,items in bands.items()},
                ktime_carry={str(flag):group([row for row in rows if
                             int(row['ktime_carry'])==flag]) for flag in (0,1)})


def validate_pt_recording(perf,interval):
    """A stopped perf may exit nonzero; accept only a complete, decodable PT trace."""
    recording=Path(interval['data']).parent
    header=subprocess.run([str(perf),'report','--header-only','-i',str(recording)],
                          text=True,capture_output=True,timeout=30)
    must(header.returncode==0 and 'contains AUX area data' in header.stdout and
         'name = intel_pt/tsc=1,cyc=1/k' in header.stdout,
         'Intel PT file has no valid filtered AUX event: '+header.stderr.strip())
    first=re.search(r'time of first sample\s*:\s*([\d.]+)',header.stdout)
    last=re.search(r'time of last sample\s*:\s*([\d.]+)',header.stdout)
    seconds=interval.get('requested_seconds',5)
    must(first is not None and last is not None and
         float(last[1])-float(first[1])>=seconds-.5,
         'Intel PT file does not cover the requested capture window')
    target=interval.get('filter','filter timekeeping_update').removeprefix('filter ')
    must(target in ('timekeeping_update','update_vsyscall','timekeeping_advance'),
         'unexpected Intel PT filter target')
    begin=float(first[1])+.05
    itrace='c' if target=='timekeeping_update' else 'b'
    trace=subprocess.run([str(perf),'script','-i',str(recording),'--itrace='+itrace,
                          '-F','time,ip,sym,dso','--time',
                          f'{begin:.6f},{begin+.1:.6f}'],
                         text=True,capture_output=True,timeout=30)
    events=sum(re.search(r'\b'+re.escape(target)+r'(?:\+0x[\da-f]+)?\b',line) is not None
               for line in trace.stdout.splitlines())
    must(trace.returncode==0 and events>=5,
         'Intel PT trace cannot decode '+target+' events: '+trace.stderr.strip())
    result=dict(validation='PASS',duration_seconds=float(last[1])-float(first[1]),
                decoded_target_events_in_100ms=events,target=target,itrace=itrace,
                perf_exit_code=interval['perf_exit_code'])
    if itrace=='c': result['decoded_target_calls_in_100ms']=events
    return result


def window(recorder, seconds, dest, reader=None, diagnostic=False, staged=False,
           split_part=None, pt_perf=None, pmu_control=None, prep_mode=None,
           percall_pmu=False, order_mode=None, pt_target='timekeeping_update',
           pt_seconds=5):
    """Writer starts after READY + first completed reader batch; stops before reader.
    Reader batch distribution covers the enclosing sustained-load interval, not
    exact writer wall time. No throughput inference from a nominal duration.
    """
    proc = control = output = err = None; running = False
    prep_commands={1:'prepctl',2:'prepraw',3:'preftctl',4:'preftraw',
                   5:'prefct0',6:'prefrawt0'}
    must(prep_mode is None or prep_mode in prep_commands,
         'unknown UPDATE preparation mode')
    must(order_mode in (None,False,True) and
         (order_mode is None or prep_mode is None),
         'invalid UPDATE order mode')
    try:
        if reader:
            path = dest.with_suffix('.control')
            with path.open('xb') as f: f.truncate(4096)
            with path.open('r+b') as f: control = mmap.mmap(f.fileno(),4096)
            output = dest.with_name(dest.stem+'-reader.csv').open('xb')
            err = dest.with_name(dest.stem+'-reader.log').open('xb')
            proc = subprocess.Popen(reader[:1]+[str(path)]+reader[1:],stdout=output,stderr=err)
            deadline = time.monotonic()+30
            while struct.unpack_from('Q',control,16)[0] < 1:
                must(proc.poll() is None, 'reader failed before steady state')
                must(time.monotonic()<deadline, 'reader READY timeout')
                time.sleep(.01)
            must(struct.unpack_from('Q',control,0)[0] == 1, 'reader not ready')
        if pmu_control: pmu_control('enable')
        running = True
        recorder.joinpath('control').write_text(
            'pmurfo\n' if percall_pmu else
            ('orderswap\n' if order_mode else 'ordernormal\n') if order_mode is not None else
            prep_commands[prep_mode]+'\n' if prep_mode is not None else
            f'split{split_part}\n' if split_part is not None else
            'stage\n' if staged else 'diagnose\n' if diagnostic else 'start\n')
        start = time.monotonic_ns(); deadline = time.monotonic()+seconds
        first_batch = struct.unpack_from('Q',control,16)[0] if control else None
        pt_result=pt_capture(recorder,dest,pt_perf,pt_seconds,pt_target) if pt_perf else None
        while time.monotonic()<deadline:
            if proc: must(proc.poll() is None,'reader exited during writer recording')
            time.sleep(min(.05,max(0,deadline-time.monotonic())))
        recorder.joinpath('control').write_text('stop\n'); running = False
        if prep_mode is not None:
            must(kv_file(recorder/'control').get('prep_mode')==str(prep_mode),
                 'cache-preparation mode was not armed')
        if order_mode is not None:
            must(kv_file(recorder/'control').get('order_swapped')==str(int(order_mode)),
                 'publisher order mode was not armed')
        if percall_pmu:
            pmu_state=kv_file(recorder/'control')
            must(pmu_state.get('percall_pmu_active')=='1' and
                 pmu_state.get('percall_pmu_validation')=='PASS',
                 'per-call PMU event was not active throughout the writer window')
        end = time.monotonic_ns()
        if pmu_control: pmu_control('disable')
        last_batch = struct.unpack_from('Q',control,16)[0] if control else None
        if proc:
            must(proc.poll() is None and last_batch > first_batch,'reader did not sustain load')
            struct.pack_into('Q',control,8,1)
            must(proc.wait(timeout=30) == 0,'reader failed')
        dest.write_bytes(recorder.joinpath('samples').read_bytes())
        if diagnostic:
            calibration = dest.with_name(dest.stem+'-calibration.csv')
            calibration.write_bytes(recorder.joinpath('calibration').read_bytes())
            must(calibration.read_text().startswith('# cpu=0 unit=TSC_ticks\n'),
                 'TSC calibration did not run on writer CPU 0')
        interval=dict(writer_start_ns=start,writer_end_ns=end,
                      load_batch_before_start=first_batch,load_batch_after_stop=last_batch,
                      reader_window='enclosing load interval; writer window is nested')
        if percall_pmu:
            interval['percall_pmu_status']={key:pmu_state[key] for key in (
                'percall_pmu_validation','percall_pmu_hit_index',
                'percall_pmu_miss_index','percall_pmu_mask',
                'percall_pmu_hit_running_ns','percall_pmu_miss_running_ns')}
        if pt_result is not None: interval['intel_pt']=pt_result
        write_json(dest.with_suffix('.json'),interval)
    finally:
        # Stop readers before the caller can restore/unload the carrier.
        try:
            if running: recorder.joinpath('control').write_text('stop\n')
        finally:
            if proc and proc.poll() is None:
                if control: struct.pack_into('Q',control,8,1)
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
            if output: output.close()
            if err: err.close()
            if control: control.close()


def kcore_target(symbol,kallsyms=Path('/proc/kallsyms'),kcore=Path('/proc/kcore')):
    """Locate one live tk_fast object in /proc/kcore (ELF64, read-only)."""
    must(symbol in ('linux_banner','tk_fast_mono','tk_fast_raw'), 'invalid cacheline target')
    matches=[]
    for line in kallsyms.read_text().splitlines():
        fields=line.split()
        if len(fields)>=3 and fields[2]==symbol:
            matches.append(int(fields[0],16))
    must(len(matches)==1 and matches[0]!=0,
         'root-visible /proc/kallsyms symbol unavailable: '+symbol)
    address=matches[0]
    if symbol!='linux_banner':
        must(address%64==0, symbol+' is not cacheline aligned')
    with kcore.open('rb',buffering=0) as core:
        header=core.read(64)
        must(len(header)==64 and header[:6]==b'\x7fELF\x02\x01' and
             struct.unpack_from('<H',header,16)[0]==4,
             '/proc/kcore is not ELF64 little-endian core')
        phoff=struct.unpack_from('<Q',header,32)[0]
        phentsize,phnum=struct.unpack_from('<HH',header,54)
        must(phentsize>=56 and 0<phnum<65536, 'invalid /proc/kcore program headers')
        for i in range(phnum):
            entry=os.pread(core.fileno(),56,phoff+i*phentsize)
            must(len(entry)==56,'truncated /proc/kcore program header')
            kind,_,offset,vaddr,_,filesz,_,_=struct.unpack('<IIQQQQQQ',entry)
            if kind==1 and vaddr<=address and address+128<=vaddr+filesz:
                target=offset+address-vaddr
                must(len(os.pread(core.fileno(),128,target))==128,
                     'cannot read live '+symbol+' from /proc/kcore')
                return dict(symbol=symbol,address=hex(address),offset=target)
    raise ValueError('symbol not covered by readable /proc/kcore segment: '+symbol)


def cacheline_reader(symbol):
    """CPU1 repeatedly reads one real kernel object; parent owns the writer."""
    must(os.geteuid()==0,'root required for /proc/kcore reader')
    os.sched_setaffinity(0,{1})
    target=kcore_target(symbol)
    with Path('/proc/kcore').open('rb',buffering=0) as core:
        print('READY '+json.dumps(target,sort_keys=True),flush=True)
        running=True
        def stop(signum,frame):
            nonlocal running
            running=False
        signal.signal(signal.SIGTERM,stop)
        count=0; next_progress=time.monotonic_ns()+1_000_000_000
        while running:
            must(len(os.pread(core.fileno(),128,target['offset']))==128,
                 'short /proc/kcore reader transfer')
            count+=1
            if count%1000==0:
                now=time.monotonic_ns()
                if now>=next_progress:
                    print(f'PROGRESS monotonic_ns={now} reads={count}',flush=True)
                    next_progress=now+1_000_000_000
    print('DONE reads='+str(count),flush=True)


def record_cacheline_reader(dest,target,first,tail,returncode):
    """Keep reader evidence separate from the already written writer interval."""
    log=dest.with_name(dest.stem+'-kcore-reader.log')
    log.write_text(first+tail)
    match=re.search(r'^DONE reads=(\d+)$',tail,re.M)
    must(returncode==0 and match and int(match[1])>=1000,
         'cacheline reader did not sustain enough reads: '+str(log))
    interval=json.loads(dest.with_suffix('.json').read_text())
    progress=[int(value) for value in re.findall(r'^PROGRESS monotonic_ns=(\d+) reads=\d+$',tail,re.M)]
    within=sum(interval['writer_start_ns']<=value<=interval['writer_end_ns']
               for value in progress)
    must(within>=3,'cacheline reader did not report sustained activity inside writer window: '+str(log))
    result=dict(**target,reads=int(match[1]),cpu=1,log=str(log.relative_to(dest.parents[1])))
    result['progress_reports_inside_writer']=within
    write_json(dest.with_name(dest.stem+'-cacheline-reader.json'),result)
    return result


def cacheline_window(recorder,seconds,dest,symbol,pmu_control=None):
    """Bracket an unchanged diagnostic writer window with one CPU1 reader."""
    if symbol is None:
        window(recorder,seconds,dest,diagnostic=True,pmu_control=pmu_control)
        return None
    proc=None
    try:
        proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),
                               '_cacheline_reader','--symbol',symbol],
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,bufsize=1)
        ready,_,_=select.select([proc.stdout],[],[],15)
        must(ready and proc.poll() is None,
             'cacheline reader did not become ready; check /proc/kcore and /proc/kallsyms')
        first=proc.stdout.readline()
        must(first.startswith('READY '),'cacheline reader failed: '+first.strip())
        target=json.loads(first[6:])
        time.sleep(.5)
        must(proc.poll() is None,'cacheline reader exited before writer window')
        window(recorder,seconds,dest,diagnostic=True,pmu_control=pmu_control)
        must(proc.poll() is None,'cacheline reader exited during writer window')
        proc.terminate()
        tail=proc.communicate(timeout=10)[0]
        return record_cacheline_reader(dest,target,first,tail,proc.returncode)
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try: proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.communicate()
        if proc and proc.stdout: proc.stdout.close()


def parse_perf_stat(path,events=PMU_EVENTS):
    """Reject missing, unsupported, or multiplexed CPU0 PMU counters."""
    values={}
    for line in path.read_text().splitlines():
        if not line or line.startswith('#'): continue
        fields=[field.strip() for field in line.split(',')]
        if len(fields)<5: continue
        name=fields[2].removesuffix(':k')
        if name not in events: continue
        must(name not in values,'duplicate perf stat event: '+name)
        must(fields[0].isdigit() and fields[3].isdigit(),
             'perf stat event not counted: '+name+'; inspect '+str(path))
        running=float(fields[4])
        must(running>=99.0,'PMU event multiplexed: '+name+'; inspect '+str(path))
        values[name]=dict(count=int(fields[0]),enabled_ns=int(fields[3]),
                          running_percent=running)
    must(set(values)==set(events),
         'PMU event missing or unsupported: '+str(set(events)-set(values))+
         '; inspect '+str(path))
    return values


def record_pmu_window(dest,seconds,timestamps,returncode):
    """Validate the count file even when perf exits nonzero after SIGINT."""
    stat=dest.with_name(dest.stem+'-pmu.csv')
    counters=parse_perf_stat(stat)
    interval=json.loads(dest.with_suffix('.json').read_text())
    must(timestamps['enable_ns']<=interval['writer_start_ns'] and
         interval['writer_end_ns']<=timestamps['disable_ns'],
         'PMU measurement did not cover complete writer window')
    must(all(item['enabled_ns']>=seconds*900_000_000 for item in counters.values()),
         'PMU events did not run for the writer window')
    result=dict(cpu=0,scope='whole CPU; cannot attribute events to individual UPDATE calls',
                events=counters,perf_exit_code=returncode,
                validation='PASS',enable_ns=timestamps['enable_ns'],
                disable_ns=timestamps['disable_ns'],
                writer_start_ns=interval['writer_start_ns'],
                writer_end_ns=interval['writer_end_ns'])
    write_json(dest.with_name(dest.stem+'-pmu.json'),result)
    return result


def pmu_window(recorder,seconds,dest,symbol,perf):
    """CPU0-wide event counts over the same writer window; no per-call attribution."""
    stat=dest.with_name(dest.stem+'-pmu.csv')
    log=dest.with_name(dest.stem+'-pmu.log')
    read_ctl,write_ctl=os.pipe(); read_ack,write_ack=os.pipe()
    process=None; stream=None; enabled=False; timestamps={}
    try:
        command=['taskset','-c','3',str(perf),'stat','-D','-1','-x,',
                 '--no-scale','--all-kernel','-C','0',
                 '-e',','.join(PMU_EVENTS),
                 '--control',f'fd:{read_ctl},{write_ack}',
                 '-o',str(stat),'--','sleep','60']
        stream=log.open('xb')
        process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,
                                 pass_fds=(read_ctl,write_ack),start_new_session=True)
        os.close(read_ctl);read_ctl=-1
        os.close(write_ack);write_ack=-1
        perf_control(write_ctl,read_ack,process,'ping')
        def control(action):
            nonlocal enabled
            perf_control(write_ctl,read_ack,process,action)
            timestamps[action+'_ns']=time.monotonic_ns()
            enabled=(action=='enable')
        cacheline_window(recorder,seconds,dest,symbol,pmu_control=control)
        must(not enabled and {'enable_ns','disable_ns'}<=set(timestamps),
             'PMU counter was not bracketed around writer')
        os.killpg(process.pid,signal.SIGINT)
        return record_pmu_window(dest,seconds,timestamps,process.wait(timeout=10))
    finally:
        if process is not None and process.poll() is None:
            if enabled:
                try: perf_control(write_ctl,read_ack,process,'disable')
                except (OSError,ValueError): pass
            os.killpg(process.pid,signal.SIGINT)
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL); process.wait()
        if stream: stream.close()
        for fd in (read_ctl,write_ctl,read_ack,write_ack):
            if fd>=0: os.close(fd)


def cacheline_shape(out,backend,sequence):
    threshold=120 if backend=='raw' else 110
    groups={}
    for name,_ in sequence:
        dest=out/name/'round-00.csv'
        rows,_=diagnostic_rows(dest)
        ticks=[int(row['cycles']) for row in rows
               if int(row['action'])==0 and int(row['cpu'])==0]
        must(len(ticks)>=1000,'too few periodic UPDATE samples in '+name)
        low=[x for x in ticks if x<=threshold]
        high=[x for x in ticks if x>threshold]
        groups[name]=dict(samples=len(ticks),median_ticks=statistics.median(ticks),
                          low_samples=len(low),high_samples=len(high),
                          low_median_ticks=statistics.median(low) if low else None,
                          high_median_ticks=statistics.median(high) if high else None,
                          high_fraction=len(high)/len(ticks),
                          histogram=dict(sorted(Counter(ticks).items())))
    return dict(protocol='clocktime-update-cacheline-intervention-v1',
                unit='TSC ticks',historical_valley_threshold=threshold,
                sequence=[name for name,_ in sequence],groups=groups,
                note='same-boot sequential causal pilot; reader load may perturb clock/cache; '
                     'do not merge these samples with formal measurements')


def cacheprep_shape(out,sequence):
    report=cacheline_shape(out,'raw',sequence)
    report.update(protocol='clocktime-update-cache-preparation-v1',
                  preparation='two locked OR-zero operations on separate lines before UPDATE TSC start',
                  modes={'baseline-before':0,'control-before':1,'fast-raw':2,
                         'control-after':1,'baseline-after':0},
                  note='single-boot diagnostic sequence; compare control-before and control-after '
                       'with fast-raw only if baseline bimodality persists; do not merge into formal UPDATE')
    for name,mode in report['modes'].items():
        dest=out/name/'round-00.csv'
        must(f'# prep_mode={mode}' in dest.read_text().splitlines()[:5],
             'writer mode mismatch in '+name)
    return report


def prefetch_shape(out,sequence):
    report=cacheline_shape(out,'raw',sequence)
    report.update(protocol='clocktime-update-prefetch-v1',
                  preparation='two non-locking PREFETCHT0 or PREFETCHW hints before UPDATE TSC start',
                  modes={name:0 if mode is None else mode for name,mode in sequence},
                  note='compare both repetitions of each target mode to its control and baseline windows; '
                       'a changed control distribution invalidates target-specific attribution')
    for name,mode in report['modes'].items():
        dest=out/name/'round-00.csv'
        must(f'# prep_mode={mode}' in dest.read_text().splitlines()[:5],
             'prefetch writer mode mismatch in '+name)
    return report


def order_shape(out,sequence):
    report=cacheline_shape(out,'raw',sequence)
    report.update(protocol='clocktime-update-order-pt-v1',
                  modes={name:'raw-first' if swapped else 'mono-first'
                         for name,swapped in sequence},
                  note='one Raw boot, balanced normal/swap/swap/normal windows; '
                       'PT and diagnostic image may perturb the natural distribution; '
                       'do not merge with formal UPDATE')
    for name,swapped in sequence:
        dest=out/name/'round-00.csv'
        lines=dest.read_text().splitlines()
        must(f'# order_swapped={int(swapped)}' in lines[:6],
             'publisher order mode mismatch in '+name)
        rows,_=diagnostic_rows(dest)
        cpu0=[row for row in rows if int(row['cpu'])==0]
        must(cpu0 and all('start_tsc' in row and int(row['start_tsc'])>0
                          for row in cpu0),
             'absolute TSC start missing in '+name)
        must(all(int(b['start_tsc'])>int(a['start_tsc'])
                 for a,b in zip(cpu0,cpu0[1:])),
             'nonmonotonic CPU0 TSC starts in '+name)
        values=[int(row['cycles'])>120 for row in cpu0
                if int(row['action'])==0]
        n=len(values)
        report['groups'][name]['quarter_high_fraction']=[
            sum(values[i*n//4:(i+1)*n//4])/len(values[i*n//4:(i+1)*n//4])
            for i in range(4)]
        trace=json.loads((out/name/'pt-shape.json').read_text())
        validation=json.loads((out/name/'pt-validation.json').read_text())
        must(validation['validation']=='PASS' and
             trace['groups']['traced']['distribution_sufficient'],
             'Intel PT coverage insufficient in '+name)
        report['groups'][name]['pt_shape']=trace['groups']
        report['groups'][name]['pt_validation']=validation
        traced_hist=trace['groups']['traced']['histogram']
        report['groups'][name]['pt_traced_low_samples']=sum(
            count for ticks,count in traced_hist.items() if int(ticks)<=120)
        report['groups'][name]['pt_traced_high_samples']=sum(
            count for ticks,count in traced_hist.items() if int(ticks)>120)
    normal=[report['groups'][name] for name,swapped in sequence if not swapped]
    report['normal_both_sides_present']=all(
        item['low_samples']>=200 and item['high_samples']>=200 and
        item['pt_traced_low_samples']>=50 and
        item['pt_traced_high_samples']>=50 for item in normal)
    report['interpretation']='READY_FOR_PT_ORDER_ANALYSIS' if report['normal_both_sides_present'] else \
        'INCONCLUSIVE_NORMAL_TWO_SIDES_NOT_RETAINED'
    return report


def percall_pmu_shape(out,sequence):
    groups={}
    for name,armed in sequence:
        dest=out/name/'round-00.csv'
        lines=dest.read_text().splitlines()
        marker=f'# percall_pmu_active={int(armed)}'
        must(any(line == marker or line.startswith(marker+' ') for line in lines[:5]),
             'per-call PMU mode mismatch in '+name)
        rows,_=diagnostic_rows(dest)
        rows=[row for row in rows if int(row['action'])==0 and int(row['cpu'])==0]
        must(len(rows)>=1000,'too few periodic CPU0 UPDATE samples in '+name)
        ticks=[int(row['cycles']) for row in rows]
        high=[x for x in ticks if x>120]
        result=dict(samples=len(rows),median_ticks=statistics.median(ticks),
                    high_fraction=len(high)/len(ticks),
                    histogram=dict(sorted(Counter(ticks).items())))
        if armed:
            must(all({'rfo_hit','rfo_miss','pmu_valid'}<=row.keys() and
                     row['pmu_valid']=='1' for row in rows),
                 'missing/invalid per-call PMU count in '+name)
            events=defaultdict(list)
            for row in rows:
                hit,miss=int(row['rfo_hit']),int(row['rfo_miss'])
                must(0<=hit<=1024 and 0<=miss<=1024,'invalid RFO count')
                events[(hit,miss)].append(int(row['cycles']))
            result['event_groups']={f'hit={hit},miss={miss}':dict(
                samples=len(values),median_ticks=statistics.median(values),
                high_fraction=sum(x>120 for x in values)/len(values))
                for (hit,miss),values in sorted(events.items())}
            result['rfo_hit_total']=sum(int(row['rfo_hit']) for row in rows)
            result['rfo_miss_total']=sum(int(row['rfo_miss']) for row in rows)
        else:
            must(all('rfo_hit' not in row for row in rows),
                 'baseline unexpectedly contains PMU counters')
        groups[name]=result
    return dict(protocol='clocktime-update-percall-rfo-v1',unit='TSC ticks',
                event_unit='per-UPDATE hardware event increments',
                historical_valley_threshold=120,
                sequence=[name for name,_ in sequence],groups=groups,
                note='RFO counters cover complete UPDATE, not a specific cache line; '
                     'check that uninstrumented baselines and PMU windows retain comparable modes '
                     'before interpreting event association')


def collect(package,case,c,out,block,revision,diagnostic=False,staged=False,
            split=False,pt=False,cacheline=False,pmu=False,cacheprep=False,
            percall_pmu=False,prefetch=False,order=False,business=False,
            business_target='update_vsyscall'):
    record = preflight(package,case,c)
    must(sum((staged,split,pt,cacheline,cacheprep,percall_pmu,prefetch,order,business))<=1 and
         (diagnostic or not any((staged,split,pt,cacheline,pmu,cacheprep,percall_pmu,prefetch,order,business))) and
         (not pmu or cacheline),
         'stage/split/PT/cacheline/cacheprep/percall-PMU/prefetch/order collection requires one diagnostic mode')
    if cacheprep:
        must(case=='raw-normal' and
             kv_file(package/'boot-manifest.txt').get('raw_cacheprep_diagnostic')=='1',
             'cache-preparation diagnosis requires the Raw normal diagnostic package')
    if prefetch:
        must(case=='raw-normal' and
             kv_file(package/'boot-manifest.txt').get('raw_prefetch_diagnostic')=='1',
             'prefetch diagnosis requires the new Raw normal diagnostic package')
        must('3dnowprefetch' in Path('/proc/cpuinfo').read_text().split(),
             'target CPU does not advertise PREFETCHW support')
    if order:
        must(case=='raw-normal' and
             kv_file(package/'boot-manifest.txt').get('raw_order_diagnostic')=='1',
             'order diagnosis requires the new Raw normal diagnostic package')
    if business:
        must(business_target in ('update_vsyscall','timekeeping_advance'),
             'unsupported business trace target')
        must(case=='raw-normal' and
             kv_file(package/'boot-manifest.txt').get('raw_order_diagnostic')=='1',
             'business-path diagnosis requires the Raw order diagnostic package')
    if percall_pmu:
        must(case=='raw-normal' and
             kv_file(package/'boot-manifest.txt').get('raw_percall_pmu_diagnostic')=='1',
             'per-call PMU diagnosis requires the Raw normal diagnostic package')
        record.update(percall_pmu_events={
            'l2_rqsts.rfo_hit':'event=0x24,umask=0xc2',
            'l2_rqsts.rfo_miss':'event=0x24,umask=0x22'},
            percall_pmu_scope='CPU0 kernel events over one complete UPDATE call')
    if staged or split:
        must(kv_file(package/'boot-manifest.txt').get('update_stage_diag')=='1',
             'package was not built for stage/split diagnosis')
    if split:
        must(kv_file(package/'boot-manifest.txt').get('update_split_diag')=='1',
             'package predates the split recorder; rebuild both UPDATE images')
    if pt or order or business:
        must(Path('/sys/bus/event_source/devices/intel_pt/nr_addr_filters').read_text().strip() != '0',
             'Intel PT address filtering unavailable')
        must(1 in os.sched_getaffinity(0),'Intel PT controller CPU 1 unavailable')
    if pt or pmu or order or business:
        perf,version=perf_binary()
        record.update(perf_binary=str(perf),perf_version=version,
                      pt_diagnostic=pt or order or business,pmu_diagnostic=pmu,
                      pmu_events=PMU_EVENTS if pmu else [])
    else: perf=None
    if cacheline:
        must(1 in os.sched_getaffinity(0),'cacheline reader CPU 1 unavailable')
        if pmu: must(3 in os.sched_getaffinity(0),'PMU controller CPU 3 unavailable')
        for symbol in ('linux_banner','tk_fast_mono','tk_fast_raw'): kcore_target(symbol)
    out.mkdir(parents=True,exist_ok=False)
    record.update(scope='diagnostic' if diagnostic else 'all',
                  stage_diagnostic=staged,split_diagnostic=split,
                  cacheline_diagnostic=cacheline,cacheprep_diagnostic=cacheprep,
                  percall_pmu_diagnostic=percall_pmu,prefetch_diagnostic=prefetch,
                  order_diagnostic=order,business_diagnostic=business,
                  split_parts=SPLIT_PARTS[case.split('-')[0]] if split else [],
                  block=block,tool_revision=revision)
    if business:
        record.update(business_pt_filter=business_target,
                      business_pt_seconds=10,
                      diagnostic_tool_sha256=sha256(Path(__file__)))
    for origin,name in ((package/'SHA256SUMS','package-SHA256SUMS'),(package/'direct/SHA256SUMS','direct-SHA256SUMS')):
        (out/name).write_bytes(origin.read_bytes())
    write_json(out/'start.json',record)
    env = dict(os.environ); backend=case.split('-')[0]; clock=manager=attempt=reader_module=False
    error=None; cleanup=[]
    def run(argv,name,environment=env): logged(list(map(str,argv)),out/(name+'.log'),environment)
    common=[package/'libkernel.so',package/'page_mappings.txt']
    recorder=Path('/sys/kernel/debug/timekeeping_update_bench')
    try:
        must(recorder.joinpath('control').is_file(), 'mount debugfs; recorder missing')
        must(kv_file(recorder/'control').get('enabled') == '0', 'recorder already running; refusing interference')
        if diagnostic:
            must(kv_file(recorder/'control').get('diagnostic_schema') == '1' and
                 recorder.joinpath('calibration').is_file(),
                 'boot a diagnostic UPDATE kernel; recorder schema missing')
        if staged:
            must(kv_file(recorder/'control').get('stage_schema') == '1',
                 'boot a stage-diagnostic UPDATE kernel')
        if split:
            must(kv_file(recorder/'control').get('split_schema') == '1',
                 'boot a split-diagnostic UPDATE kernel')
        if cacheprep or prefetch or order:
            must(kv_file(recorder/'control').get('prep_schema') == '1',
                 'boot the Raw cache-preparation diagnostic kernel')
        if order:
            must(kv_file(recorder/'control').get('order_schema') == '1',
                 'boot the Raw order-diagnostic kernel')
        if percall_pmu:
            must(kv_file(recorder/'control').get('percall_pmu_schema') == '1',
                 'boot the Raw per-call PMU diagnostic kernel')
        os.sched_setaffinity(0,{0})
        with tune(record):
            try:
                clock_module=package/('raw-m09-clock.ko' if backend=='raw' else 'vkso_m09_clock.ko')
                run(['insmod',clock_module],'clock-load'); clock=True
                for _ in range(50):
                    if Path('/dev/vkso-m09-clock').is_char_device(): break
                    time.sleep(.1)
                must(Path('/dev/vkso-m09-clock').is_char_device(), 'dynamic clock device missing')
                if backend=='vkso':
                    run(['insmod',package/'page_cache_replace.ko'],'manager-load'); manager=True
                    run([package/'manager','validate',*common],'validate')
                    attempt=True
                    run([package/'manager','replace',*common],'replace')
                run(['setarch','x86_64','-R',package/(backend+'-abi-matrix')],'abi',dict(env,LD_LIBRARY_PATH=str(package),VKSO_TEST_DYNAMIC_CLOCK='/dev/vkso-m09-clock'))
                must('abi_matrix_status=pass' in (out/'abi.log').read_text(),'ABI failure')
                binary=package/'direct'/('native-bench' if backend=='raw' else 'vkso-bench')
                for mode in ('--check','--check-fast'):
                    run(['setarch','x86_64','-R',binary,mode,'--cpu',c['CPU']],mode[2:])
                    marker='public_api_check=PASS scope=full' if mode=='--check' else 'time_syscall_denial_check=PASS'
                    must(marker in (out/(mode[2:]+'.log')).read_text(), 'public API validation missing')
                if backend=='vkso':
                    run(['insmod',package/'vkso-kernel-reader.ko'],'reader-module-load'); reader_module=True
                    run([sys.executable,DIRECT/'sharing.py',*common,'vkso'],'sharing')
                    validate_sharing(json.loads((out/'sharing.log').read_text()))
                    run(['rmmod','vkso_kernel_reader'],'reader-module-unload'); reader_module=False
                time.sleep(c['STABILIZE_SECONDS'])
                sequence=(('baseline-before',None),('static-read','linux_banner'),
                          ('mono-share','tk_fast_mono'),
                          ('raw-share','tk_fast_raw'),('baseline-after',None))
                if cacheprep:
                    sequence=(('baseline-before',None),('control-before',1),
                              ('fast-raw',2),('control-after',1),
                              ('baseline-after',None))
                if prefetch:
                    sequence=(('baseline-before',None),
                              ('read-control-before',5),('read-raw-before',6),
                              ('write-control-before',3),('write-raw-before',4),
                              ('baseline-middle',None),
                              ('write-raw-after',4),('write-control-after',3),
                              ('read-raw-after',6),('read-control-after',5),
                              ('baseline-after',None))
                if order:
                    sequence=(('normal-before',False),('swapped-before',True),
                              ('swapped-after',True),('normal-after',False))
                if percall_pmu:
                    sequence=(('baseline-before',False),('percall-before',True),
                              ('baseline-middle',False),('percall-after',True),
                              ('baseline-after',False))
                if backend=='vkso':
                    sequence=(sequence[0],sequence[1],sequence[3],sequence[2],sequence[4])
                for r in range(c['REPEATS']):
                    for operation in ([name for name,_ in sequence] if cacheline or cacheprep or percall_pmu or prefetch or order else
                                      ('idle',) if pt or business else SPLIT_SCENARIOS if split else SCENARIOS):
                        for part in SPLIT_PARTS[backend] if split else (None,):
                            print(f'round={r+1}/{c["REPEATS"]} scenario={operation} split={part}',flush=True)
                            directory=(out/f'split-{part}'/operation if split else out/operation)
                            directory.mkdir(parents=True,exist_ok=True)
                            dest=directory/('round-%02d.csv'%r)
                            reader=None
                            if not cacheline and not cacheprep and not percall_pmu and not prefetch and not order and operation!='idle':
                                reader=[str(package/'direct'/('native-load' if backend=='raw' else 'vkso-load')),
                                        str(c['CPU']),operation,str(c['READER_ITERATIONS']),str(c['WARMUP'])]
                            # Disable ASLR in controller, inherited by reader, via outer setarch.
                            if pmu:
                                symbol=dict(sequence)[operation]
                                pmu_window(recorder,c['UPDATE_SECONDS'],dest,symbol,perf)
                            elif cacheline:
                                symbol=dict(sequence)[operation]
                                cacheline_window(recorder,c['UPDATE_SECONDS'],dest,symbol)
                            elif cacheprep or prefetch:
                                mode=dict(sequence)[operation]
                                window(recorder,c['UPDATE_SECONDS'],dest,diagnostic=True,
                                       prep_mode=mode)
                            elif order:
                                mode=dict(sequence)[operation]
                                window(recorder,c['UPDATE_SECONDS'],dest,diagnostic=True,
                                       order_mode=mode,pt_perf=perf)
                            elif percall_pmu:
                                mode=dict(sequence)[operation]
                                window(recorder,c['UPDATE_SECONDS'],dest,diagnostic=True,
                                       percall_pmu=mode)
                            elif business:
                                window(recorder,c['UPDATE_SECONDS'],dest,diagnostic=True,
                                       pt_perf=perf,pt_target=business_target,
                                       pt_seconds=10)
                            else:
                                window(recorder,c['UPDATE_SECONDS'],dest,reader,diagnostic,
                                       staged,part,pt_perf=perf)
                            writer_rows(dest)
                            if diagnostic: diagnostic_rows(dest,staged,part)
                            if pt or order or business:
                                interval=json.loads(dest.with_suffix('.json').read_text())['intel_pt']
                                pt_dir=out/operation if order else out
                                write_json(pt_dir/'pt-shape.json',pt_shape(dest,interval,backend))
                                write_json(pt_dir/'pt-validation.json',
                                           validate_pt_recording(perf,interval))
                                if business:
                                    write_json(pt_dir/'business-shape.json',
                                               business_shape(dest,interval))
                            if reader: reader_rows(dest.with_name(dest.stem+'-reader.csv'),c['READER_ITERATIONS'])
                if cacheline: write_json(out/'cacheline-shape.json',cacheline_shape(out,backend,sequence))
                if cacheprep: write_json(out/'cacheprep-shape.json',cacheprep_shape(out,sequence))
                if prefetch: write_json(out/'prefetch-shape.json',prefetch_shape(out,sequence))
                if order: write_json(out/'order-shape.json',order_shape(out,sequence))
                if percall_pmu: write_json(out/'percall-pmu-shape.json',percall_pmu_shape(out,sequence))
                if pmu:
                    write_json(out/'pmu-window-report.json',dict(
                        protocol='clocktime-update-window-pmu-v1',cpu=0,
                        scope='CPU0-wide counters over each writer window; '
                              'not per-call event attribution',
                        sequence=[name for name,_ in sequence],
                        windows={name:json.loads((out/name/'round-00-pmu.json').read_text())
                                 for name,_ in sequence}))
            finally:
                if attempt:
                    try: run([package/'manager','restore',*common],'restore')
                    except BaseException as e: cleanup.append('RESTORE FAILED: retain backing module; '+repr(e))
                if manager and not cleanup:
                    try: run(['rmmod','page_cache_replace'],'manager-unload')
                    except BaseException as e: cleanup.append(repr(e))
                if reader_module:
                    try: run(['rmmod','vkso_kernel_reader'],'reader-module-cleanup')
                    except BaseException as e: cleanup.append(repr(e))
                if clock:
                    try: run(['rmmod','vkso_m09_clock'],'clock-unload')
                    except BaseException as e: cleanup.append(repr(e))
    except BaseException as e: error=repr(e)
    record.update(status='FAIL' if error or cleanup else 'COMPLETE',error=error,cleanup_errors=cleanup)
    write_json(out/'run.json',record); seal(out)
    if os.environ.get('SUDO_UID'):
        uid,gid=int(os.environ['SUDO_UID']),int(os.environ['SUDO_GID'])
        for p in [out,*out.rglob('*')]: os.chown(p,uid,gid)
    must(record['status']=='COMPLETE','collection failed: '+str(error or cleanup))


def split_diagnosis_report(paths):
    """Retain each boot and boundary separately; inspect modes before attribution."""
    summaries=[]; boots=set(); package_ids=set()
    labels={'raw':{1:'before_update_vsyscall',2:'after_update_vsyscall'},
            'vkso':{2:'before_base_real',3:'after_base_real'}}
    for path in paths:
        verify_sums(path, {'run.json','start.json','abi.log','check.log','check-fast.log'})
        run=json.loads((path/'run.json').read_text())
        must(run['status']=='COMPLETE' and run['scope']=='diagnostic' and
             run.get('split_diagnostic') is True and not run.get('stage_diagnostic') and
             run['environment_cleanup']=='PASS', 'not a complete split run')
        must(sha256(Path(run['package'])/'SHA256SUMS')==run['package_sha256'],
             'split package identity changed')
        package_ids.add(run['package_sha256'])
        must(run['boot_id'] not in boots, 'duplicate split diagnostic boot')
        boots.add(run['boot_id'])
        must(run['case'] in ('raw-normal','vkso-normal'), 'split protocol requires normal case')
        backend=run['case'].split('-')[0]
        must(tuple(run['split_parts'])==SPLIT_PARTS[backend], 'wrong split boundaries')
        for scenario in SPLIT_SCENARIOS:
            for part in SPLIT_PARTS[backend]:
                rows=[]; pairs=[]
                for i in range(run['config']['REPEATS']):
                    round_path=path/f'split-{part}'/scenario/('round-%02d.csv'%i)
                    writer_rows(round_path)
                    data,calibration=diagnostic_rows(round_path,split_part=part)
                    rows.extend(r for r in data if int(r['action'])==0 and int(r['cpu'])==0)
                    pairs.extend(calibration)
                must(len(rows)>=1000, 'too few CPU0 periodic split samples')
                total=[int(r['cycles']) for r in rows]
                prefix=[int(r['prefix_ticks']) for r in rows]
                suffix=[int(r['suffix_ticks']) for r in rows]
                summaries.append(dict(path=str(path),case=run['case'],boot_id=run['boot_id'],
                    scenario=scenario,split_part=part,boundary=labels[backend][part],
                    unit='TSC ticks',periodic_cpu0_samples=len(rows),
                    total_median=statistics.median(total),
                    prefix_median=statistics.median(prefix),
                    suffix_median=statistics.median(suffix),
                    total_histogram=dict(sorted(Counter(total).items())),
                    prefix_histogram=dict(sorted(Counter(prefix).items())),
                    suffix_histogram=dict(sorted(Counter(suffix).items())),
                    clock_modes=dict(Counter(r['clock_mode'] for r in rows)),
                    shifts=dict(Counter(r['shift'] for r in rows)),
                    tsc_pair_median=statistics.median(pairs),
                    tsc_pair_p99=sorted(pairs)[int(.99*(len(pairs)-1))]))
    must(len(package_ids)==1, 'split runs mix package identities')
    return dict(protocol='clocktime-update-split-diagnosis-v1',
                scope='one extra ordered TSC per update; boot is independent unit; '
                      'boundary windows are sequential, not per-sample pairs; '
                      'confirm original modes before attributing intervals',
                boots=len(boots),boot_boundaries=summaries)


def no_marker_state_report(paths):
    """Explain whole-update modes using only state recorded after timed end."""
    bands=((0,40),(40,900),(900,960),(960,1000))
    summaries=[]; boots=set()
    for path in paths:
        verify_sums(path, {'run.json','start.json','abi.log','check.log','check-fast.log'})
        run=json.loads((path/'run.json').read_text())
        must(run['status']=='COMPLETE' and run['scope']=='diagnostic' and
             run['environment_cleanup']=='PASS' and
             not run.get('stage_diagnostic') and not run.get('split_diagnostic'),
             'not a complete no-marker diagnostic run')
        must(sha256(Path(run['package'])/'SHA256SUMS')==run['package_sha256'],
             'diagnostic package identity changed')
        must(run['case'] in ('raw-normal','vkso-normal'),
             'no-marker diagnosis requires a normal case')
        must(run['boot_id'] not in boots, 'duplicate diagnostic boot')
        boots.add(run['boot_id'])
        backend=run['case'].split('-',1)[0]
        threshold=120 if backend=='raw' else 110
        for scenario in SPLIT_SCENARIOS:
            rows=[]; transitions=Counter()
            for i in range(run['config']['REPEATS']):
                round_path=path/scenario/('round-%02d.csv'%i)
                writer_rows(round_path)
                data,_=diagnostic_rows(round_path)
                must(not {'prefix_ticks','suffix_ticks',*STAGE_FIELDS} & set(data[0]),
                     'no-marker report received timestamped samples')
                periodic=[r for r in data if int(r['action'])==0 and
                          int(r['cpu'])==0]
                rows.extend(periodic)
                previous=None
                for row in periodic:
                    phase=int(row['phase_nsec'])
                    if previous is not None and int(row['sample'])==int(previous['sample'])+1 and \
                       40000000<=phase<900000000 and \
                       40000000<=int(previous['phase_nsec'])<900000000:
                        before='high' if int(previous['cycles'])>threshold else 'low'
                        after='high' if int(row['cycles'])>threshold else 'low'
                        transitions[before,after]+=1
                    previous=row
            must(len(rows)>=1000, 'too few CPU0 periodic no-marker samples')
            high=[r for r in rows if int(r['cycles'])>threshold]
            low=[r for r in rows if int(r['cycles'])<=threshold]
            must(high and low, 'historical valley does not separate two groups')
            phase_bands=[]
            for begin,end in bands:
                group=[r for r in rows if begin*1000000<=int(r['phase_nsec'])<end*1000000]
                count_high=sum(int(r['cycles'])>threshold for r in group)
                phase_bands.append(dict(begin_ms=begin,end_ms=end,count=len(group),
                    high_count=count_high,
                    high_fraction=count_high/len(group) if group else None,
                    fraction_of_all_high=count_high/len(high)))
            carry={}
            for field in ('ktime_carry','realtime_carry','monotonic_carry','leap_pending'):
                marked=[r for r in rows if int(r[field])==1]
                marked_high=sum(int(r['cycles'])>threshold for r in marked)
                unmarked=len(rows)-len(marked)
                carry[field]=dict(count=len(marked),high_count=marked_high,
                    high_fraction=marked_high/len(marked) if marked else None,
                    high_fraction_without=(len(high)-marked_high)/unmarked
                                          if unmarked else None,
                    fraction_of_all_high=marked_high/len(high))
            high_after_high=transitions['high','high']+transitions['high','low']
            high_after_low=transitions['low','high']+transitions['low','low']
            middle_transitions=dict(pairs=sum(transitions.values()),
                high_after_high=(transitions['high','high']/high_after_high
                                 if high_after_high else None),
                high_after_low=(transitions['low','high']/high_after_low
                                if high_after_low else None))
            summaries.append(dict(path=str(path),case=run['case'],boot_id=run['boot_id'],
                package_sha256=run['package_sha256'],scenario=scenario,
                unit='TSC ticks',phase_clock='realtime',
                periodic_cpu0_samples=len(rows),
                historical_valley_threshold=threshold,
                low_count=len(low),high_count=len(high),
                low_median=statistics.median(int(r['cycles']) for r in low),
                high_median=statistics.median(int(r['cycles']) for r in high),
                high_fraction=len(high)/len(rows),
                total_histogram=dict(sorted(Counter(int(r['cycles']) for r in rows).items())),
                phase_bands=phase_bands,carry=carry,
                middle_second_transitions=middle_transitions))
    return dict(protocol='clocktime-update-no-marker-state-v1',boots=len(boots),
                scope='descriptive per boot; complete UPDATE TSC ticks; state captured '
                      'after timed end; historical valleys only; adjacent samples '
                      'do not establish an internal cause',boot_scenarios=summaries)


def diagnosis_report(paths):
    """Descriptive within-boot tables; never infer independence per tick."""
    split_modes={json.loads((path/'run.json').read_text()).get('split_diagnostic',False)
                 for path in paths}
    must(len(split_modes)==1, 'cannot mix split and previous diagnostic runs')
    if split_modes=={True}:
        return split_diagnosis_report(paths)
    summaries=[]; boots=set(); package_ids=set(); staged_modes=set()
    for path in paths:
        verify_sums(path, {'run.json','start.json','abi.log','check.log','check-fast.log'})
        run=json.loads((path/'run.json').read_text())
        must(run['status']=='COMPLETE' and run['scope']=='diagnostic' and
             run['environment_cleanup']=='PASS', 'not a complete diagnostic run')
        must(sha256(Path(run['package'])/'SHA256SUMS')==run['package_sha256'],
             'diagnostic package identity changed')
        package_ids.add(run['package_sha256'])
        staged=run.get('stage_diagnostic',False)
        staged_modes.add(staged)
        must(run['boot_id'] not in boots, 'duplicate diagnostic boot')
        boots.add(run['boot_id'])
        backend=run['case'].split('-',1)[0]
        must(run['case'] in ('raw-normal','vkso-normal'),
             'initial diagnostic thresholds apply to normal only')
        threshold=120 if backend=='raw' else 110
        for scenario in SCENARIOS:
            rows=[]; pairs=[]
            for i in range(run['config']['REPEATS']):
                round_path=path/scenario/('round-%02d.csv'%i)
                writer_rows(round_path)
                data,calibration=diagnostic_rows(round_path,staged)
                rows.extend(r for r in data if int(r['action'])==0 and int(r['cpu'])==0)
                pairs.extend(calibration)
            must(len(rows)>=1000, 'too few CPU0 periodic samples')
            if staged:
                ordered=sorted(int(r['cycles']) for r in rows)
                lower=ordered[(len(ordered)-1)//4]
                upper=ordered[3*(len(ordered)-1)//4]
                must(lower<upper, 'stage-instrumented totals have no quartile separation')
                is_high=lambda r: int(r['cycles'])>=upper
                low_rows=[r for r in rows if int(r['cycles'])<=lower]
                high_rows=[r for r in rows if is_high(r)]
            else:
                is_high=lambda r: int(r['cycles'])>threshold
                low_rows=[r for r in rows if not is_high(r)]
                high_rows=[r for r in rows if is_high(r)]
            low=[int(r['cycles']) for r in low_rows]
            high=[int(r['cycles']) for r in high_rows]
            must(low and high, 'empty diagnostic comparison group')
            flags={}
            for field in ('ktime_carry','realtime_carry','monotonic_carry','leap_pending'):
                groups={str(value):[r for r in rows if int(r[field])==value]
                        for value in (0,1)}
                flags[field]={value:dict(count=len(group),
                    high_fraction=(sum(is_high(r) for r in group)/len(group)
                                   if group else None))
                    for value,group in groups.items()}
            phase=[]
            for bin_no in range(10):
                group=[r for r in rows if int(r['phase_nsec'])//100000000==bin_no]
                phase.append(dict(phase_decile=bin_no,count=len(group),
                    high_fraction=(sum(is_high(r) for r in group)/len(group)
                                   if group else None)))
            summary=dict(path=str(path),boot_id=run['boot_id'],case=run['case'],
                scenario=scenario,unit='TSC ticks',periodic_cpu0_samples=len(rows),
                partition=('outer-quartiles-of-instrumented-total' if staged else
                           'historical-valley'),
                historical_valley_threshold=None if staged else threshold,
                low_count=len(low),high_count=len(high),
                high_fraction=len(high)/len(rows),low_median=statistics.median(low),
                high_median=statistics.median(high),
                writer_histogram=dict(sorted(Counter(int(r['cycles']) for r in rows).items())),
                clock_modes=dict(Counter(r['clock_mode'] for r in rows)),
                shifts=dict(Counter(r['shift'] for r in rows)),
                tsc_pair=dict(count=len(pairs),median=statistics.median(pairs),
                              p90=sorted(pairs)[int(.9*(len(pairs)-1))],
                              p99=sorted(pairs)[int(.99*(len(pairs)-1))],
                              minimum=min(pairs),maximum=max(pairs),
                              histogram=dict(sorted(Counter(pairs).items()))),
                flag_groups=flags,phase_deciles=phase)
            if staged:
                labels={'first_publish_ticks':('update_vsyscall' if backend=='raw'
                                               else 'update_pvclock_gtod'),
                        'second_publish_ticks':('update_pvclock_gtod' if backend=='raw'
                                                else 'tk_publish_read_state')}
                segments={}
                for field in STAGE_FIELDS:
                    low_stage=statistics.median(int(r[field]) for r in low_rows)
                    high_stage=statistics.median(int(r[field]) for r in high_rows)
                    segments[labels.get(field,field.removesuffix('_ticks'))]=dict(
                        column=field,median_ticks=statistics.median(int(r[field]) for r in rows),
                        low_total_quartile_median_ticks=low_stage,
                        high_total_quartile_median_ticks=high_stage,
                        high_minus_low_ticks=high_stage-low_stage)
                summary.update(total_quartile_cutoffs_ticks=dict(lower=lower,upper=upper),
                               total_high_minus_low_median_ticks=statistics.median(high)-statistics.median(low),
                               stage_segments=segments)
            summaries.append(summary)
    must(len(package_ids)==1 and len(staged_modes)==1,
         'diagnostic runs mix package identities or stage schemas')
    staged=staged_modes.pop()
    return dict(protocol=('clocktime-update-stage-diagnosis-v1' if staged else
                          'clocktime-update-bimodal-diagnosis-v1'),
                scope=('descriptive; boot is independent unit; outer quartiles of '
                       'stage-instrumented total; intervals include ordered TSC overhead'
                       if staged else
                       'descriptive; boot is independent unit; mode labels use prior normal peaks'),
                boots=len(boots),boot_scenarios=summaries)


def aggregate_update(root, manifest):
    records=[]; boots=set(); summaries=[]
    for entry in manifest['plan']:
        if entry['mode'] != 'update':
            continue
        directory=root/('block-%02d'%entry['block'])/'update'/entry['case']
        verify_sums(directory, {'run.json','start.json','abi.log','check.log','check-fast.log'})
        r=json.loads((directory/'run.json').read_text()); c=manifest['config']
        must(r['status']=='COMPLETE' and not r['cleanup_errors'] and r['environment_cleanup']=='PASS', 'failed cleanup/result')
        must(r['protocol']==PROTOCOL and r['case']==entry['case'] and r['block']==entry['block'] and r['config']==c and r['scope']=='all', 'mixed result identity')
        must(r['boot_id'] not in boots,'duplicate boot'); boots.add(r['boot_id'])
        variant=entry['case'].split('-',1)[1]
        must(r['package_sha256']==manifest['packages']['update'][variant]['sha256'] and
             r['bundle_sha256']==manifest['packages']['update'][variant]['direct_sha256'],'mixed package identity')
        tools=root/r['tool_revision']; verify_sums(tools)
        must('abi_matrix_status=pass' in (directory/'abi.log').read_text(),'ABI evidence missing')
        for name,marker in [('check.log','public_api_check=PASS scope=full'),('check-fast.log','time_syscall_denial_check=PASS')]:
            must(marker in (directory/name).read_text(), 'missing public validation: '+name)
        if entry['case'].startswith('vkso-'):
            validate_sharing(json.loads((directory/'sharing.log').read_text()))
        for op in SCENARIOS:
            medians=[]; reader_medians=[]
            must(len(list((directory/op).glob('round-*.json')))==c['REPEATS'],'wrong round count')
            for i in range(c['REPEATS']):
                f=directory/op/('round-%02d.csv'%i)
                w=writer_rows(f); medians.append(w['median_ticks'])
                interval=json.loads(f.with_suffix('.json').read_text())
                must(interval['writer_end_ns']-interval['writer_start_ns'] >= c['UPDATE_SECONDS']*1e9,'short writer interval')
                row=dict(block=entry['block'],case=entry['case'],scenario=op,round=i,writer=w)
                if op!='idle':
                    must(interval['load_batch_after_stop']>interval['load_batch_before_start']>=1,'invalid steady handshake')
                    v=reader_rows(f.with_name(f.stem+'-reader.csv'),c['READER_ITERATIONS'])
                    must(v['batches']>=interval['load_batch_after_stop'],'reader ended before writer')
                    reader_medians.append(v['median_ticks_per_call']); row['reader']=v
                records.append(row)
            summaries.append(dict(block=entry['block'],case=entry['case'],scenario=op,
                writer_boot_median_ticks=statistics.median(medians),
                reader_boot_median_ticks_per_call=statistics.median(reader_medians) if reader_medians else None))
    comparisons=[]
    for variant in ('normal','no-retpoline'):
        for op in SCENARIOS:
            for metric in ('writer_boot_median_ticks','reader_boot_median_ticks_per_call'):
                raw=[s[metric] for s in summaries if s['case']=='raw-'+variant and s['scenario']==op and s[metric] is not None]
                vkso=[s[metric] for s in summaries if s['case']=='vkso-'+variant and s['scenario']==op and s[metric] is not None]
                if not raw: continue
                a,b=statistics.median(raw),statistics.median(vkso)
                comparisons.append(dict(variant=variant,scenario=op,metric=metric,boots_per_case=len(raw),raw=a,vkso=b,delta_ticks=b-a,delta_percent=100*(b/a-1)))
    result=dict(protocol=PROTOCOL,independent_unit='boot',unit='TSC ticks, not core cycles',
                writer_scope='periodic action=0; lock already held; raw counter delta without subtraction',
                reader_scope='enclosing load interval; medians of complete public-call batches',
                comparisons=comparisons,boot_summaries=summaries,round_summaries=records)
    return result


def section_sizes(path):
    sections={}
    for line in path.read_text().splitlines():
        fields=line.split()
        if len(fields) < 3 or not fields[1].isdecimal() or fields[0]=='Total':
            continue
        must(fields[0] not in sections, 'duplicate ELF section: '+fields[0])
        sections[fields[0]]=int(fields[1])
    must(any(name.startswith('.text') and size>0 for name,size in sections.items()),
         'missing .text in code footprint: '+str(path))
    return sections


def text_bytes(sections):
    return sum(size for name,size in sections.items() if name.startswith('.text'))


def static_footprint(manifest):
    rows=[]
    for variant, identity in manifest['packages']['read'].items():
        package=Path(identity['path'])
        inventory=set((package/'SHA256SUMS').read_text().splitlines())
        for name in ('raw-vmlinux-sections.txt','vkso-vmlinux-sections.txt',
                     'raw-vdso-sections.txt','vkso-carrier-sections.txt',
                     'direct/libvkso_time.so.sections.txt','raw-bzImage','vkso-bzImage'):
            must(sha256(package/name)+'  '+name in inventory,
                 'code footprint is absent from sealed package: '+name)
        raw=section_sizes(package/'raw-vmlinux-sections.txt')
        vkso=section_sizes(package/'vkso-vmlinux-sections.txt')
        vdso=section_sizes(package/'raw-vdso-sections.txt')
        carrier=section_sizes(package/'vkso-carrier-sections.txt')
        public=section_sizes(package/'direct/libvkso_time.so.sections.txt')
        rows.append(dict(variant=variant,
            raw_kernel_text_bytes=text_bytes(raw),vkso_kernel_text_bytes=text_bytes(vkso),
            kernel_text_delta_bytes=text_bytes(vkso)-text_bytes(raw),
            raw_native_vdso_text_bytes=text_bytes(vdso),
            vkso_carrier_text_bytes=text_bytes(carrier),
            vkso_public_library_text_bytes=text_bytes(public),
            raw_bzimage_bytes=(package/'raw-bzImage').stat().st_size,
            vkso_bzimage_bytes=(package/'vkso-bzImage').stat().st_size))
    return dict(scope='ELF .text section and compressed image file sizes; carrier pages alias kernel text, so do not sum them as extra physical memory',rows=rows)


def mapping_footprint(directories):
    boots=[]
    for directory in directories:
        verify_sums(directory, {'resource.json','run.json'})
        run=json.loads((directory/'run.json').read_text())
        census=json.loads((directory/'resource.json').read_text())
        backend=run['case'].split('-',1)[0]
        must(census['protocol']==CENSUS_PROTOCOL and census['backend']==backend and
             census['counts']==list(CENSUS_COUNTS) and
             len(census['groups'])==len(CENSUS_COUNTS) and
             census['kernel_release']=='5.15.198' and
             census['page_bytes']==4096,
             'wrong mapping census metadata')
        for count,group in zip(CENSUS_COUNTS,census['groups']):
            must(group==census_summarize(group['records'],backend,count),
                 'mapping census totals differ from raw process PFNs')
            boots.append(dict(block=run['block'],case=run['case'],boot_id=run['boot_id'],
                              processes=count,union_unique_pfns=group['union_unique_pfns'],
                              category_unique_pfns=group['unique_pfns'],
                              unresolved_present_pages=group['unresolved_present_pages']))
    comparisons=[]
    for variant in ('normal','no-retpoline'):
        for count in CENSUS_COUNTS:
            raw=[r['union_unique_pfns'] for r in boots if r['case']=='raw-'+variant and r['processes']==count]
            vkso=[r['union_unique_pfns'] for r in boots if r['case']=='vkso-'+variant and r['processes']==count]
            must(len(raw)==len(vkso)>=3, 'missing independent mapping census boots')
            a,b=statistics.median(raw),statistics.median(vkso)
            comparisons.append(dict(variant=variant,processes=count,boots_per_case=len(raw),
                                    raw_selected_pfns=a,vkso_selected_pfns=b,
                                    delta_selected_pfns=b-a,delta_selected_bytes=(b-a)*4096))
    return dict(scope='resident unique PFNs in named user time mappings only; not whole-system net RAM',
                independent_unit='boot',boot_summaries=boots,comparisons=comparisons)


def aggregate(root, manifest):
    must(manifest['plan'] == full_plan(manifest['config']['BLOCKS']),
         'incomplete or reordered eight-image campaign plan')
    for mode, variants in manifest['packages'].items():
        for variant, identity in variants.items():
            must(package_identity(Path(identity['path'])) == identity,
                 'package changed since campaign begin: '+mode+'/'+variant)
    boots=set(); read=[]
    for entry in manifest['plan']:
        mode, case = entry['mode'], entry['case']
        must(mode in ('read','update'), 'invalid campaign mode')
        directory=root/('block-%02d'%entry['block'])/mode/case
        verify_sums(directory, {'run.json'})
        run=json.loads((directory/'run.json').read_text())
        must(run['status']=='COMPLETE' and run['case']==case and run['block']==entry['block'],
             'incomplete or mixed acquisition')
        must(run['tool_revision'].startswith('tools/'), 'missing frozen collection tool revision')
        verify_sums(root/run['tool_revision'])
        must(run['boot_id'] not in boots, 'same boot reused across READ/UPDATE')
        boots.add(run['boot_id'])
        variant=case.split('-',1)[1]
        package=manifest['packages'][mode][variant]
        if mode=='read':
            must(run['package_checksums_sha256']==package['sha256'] and
                 run['bundle_build_sha256']==sha256(Path(package['path'])/'direct/build.json'),
                 'READ package/bundle changed')
            read.append(directory)
        else:
            must(run['package_sha256']==package['sha256'] and
                 run['bundle_sha256']==package['direct_sha256'],
                 'UPDATE package/bundle changed')
    must(len(read)==manifest['config']['BLOCKS']*4, 'missing clean READ boots')
    return dict(protocol='clocktime-full-v1', independent_unit='boot',
                read_user=summarize_read(read), read_kernel=summarize_kernel(read),
                stateful=aggregate_update(root,manifest),
                mapping_footprint=mapping_footprint(read),
                static_footprint=static_footprint(manifest))


def run_collector(argv, env=None, needs_sudo=False):
    # Do not move a partial directory while a root collector is still restoring
    # mappings or writing logs. A sudo password prompt needs the calling
    # terminal: setsid() would detach it before sudo can authenticate.
    process=subprocess.Popen(argv,env=env,start_new_session=not needs_sudo)
    try:
        code=process.wait()
        if code: raise subprocess.CalledProcessError(code,argv)
    except BaseException:
        handlers={sig:signal.signal(sig,signal.SIG_IGN) for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP)}
        try:
            if process.poll() is None:
                try:
                    if needs_sudo:
                        # sudo forwards the signal to its command and waits for
                        # the collector's cleanup in the foreground process group.
                        process.terminate()
                    else:
                        os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError: pass
                process.wait()
        finally:
            for sig,handler in handlers.items(): signal.signal(sig,handler)
        raise


def campaign(action, value):
    results=Path(os.environ.get('RESULTS_DIR',BARE/'results')).resolve()
    results.mkdir(parents=True,exist_ok=True)
    statefile=Path(os.environ.get('STATE_FILE',BARE/'.clocktime-full-state.json')).resolve()
    with (BARE/'.clocktime-full.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=json.loads(statefile.read_text()) if statefile.exists() else None
        if action=='begin':
            must(not state or state['status']!='active','campaign already active')
            c=config()
            packages={
                'read':{v:Path(os.environ.get(key,BARE/'artifacts'/('direct-'+v))).resolve()
                        for v,key in [('normal','NORMAL_PACKAGE'),('no-retpoline','NO_RETPOLINE_PACKAGE')]},
                'update':{v:Path(os.environ.get(key,BARE/'artifacts'/('update-'+v))).resolve()
                          for v,key in [('normal','UPDATE_NORMAL_PACKAGE'),('no-retpoline','UPDATE_NO_RETPOLINE_PACKAGE')]}}
            check_all_packages(packages)
            name=value or time.strftime('%Y%m%dT%H%M%SZ-clocktime-full',time.gmtime())
            must(bool(name) and all(x.isalnum() or x in '-_' for x in name),'invalid run name')
            root=results/name; root.mkdir(exist_ok=False)
            manifest=dict(protocol='clocktime-full-v1',config=c,plan=full_plan(c['BLOCKS']),
                          packages={mode:{v:package_identity(p) for v,p in variants.items()}
                                    for mode,variants in packages.items()})
            write_json(root/'campaign.json',manifest)
            state=dict(root=str(root),status='active',next_index=0,
                       manifest_sha256=sha256(root/'campaign.json'),tools=tools_snapshot(root))
            atomic(statefile,state)
        if not state:
            if action=='status': print('status=not-started'); return
            raise ValueError('run ./experiment.sh begin first')
        root=Path(state['root'])
        must(sha256(root/'campaign.json')==state['manifest_sha256'],'campaign manifest changed')
        manifest=json.loads((root/'campaign.json').read_text())
        must(manifest['protocol']=='clocktime-full-v1','wrong campaign protocol')
        if action=='stop':
            must(state['status']=='active','campaign is not active')
            write_json(root/'STOPPED.json',dict(status='INCOMPLETE',completed_boots=state['next_index'],
                       reason=value or 'operator stopped'))
            state['status']='stopped'; atomic(statefile,state)
        if action=='refresh-tools':
            must(state['status'] in ('active','complete'),'campaign cannot refresh')
            must(config()==manifest['config'],'measurement config changed; begin a new campaign')
            packages={mode:{v:Path(x['path']) for v,x in variants.items()}
                      for mode,variants in manifest['packages'].items()}
            check_all_packages(packages)
            for mode,variants in packages.items():
                for variant,p in variants.items():
                    must(package_identity(p)==manifest['packages'][mode][variant],
                         'frozen package changed: '+str(p))
            state['tools']=tools_snapshot(root); atomic(statefile,state)
            print('tool_revision='+state['tools'])
        if action=='aggregate':
            must(state['status']=='complete','campaign incomplete')
            report=aggregate(root,manifest)
            summary=root.with_name(root.name+'-summary.json')
            if summary.exists():
                must(json.loads(summary.read_text())==report,'existing summary differs from raw data')
            else: write_json(summary,report)
            if not root.with_name(root.name+'.tar.gz').exists(): archive(root)
            print('summary='+str(summary)); print('archive='+str(root.with_name(root.name+'.tar.gz')))
            return
        if action in ('boot','collect'):
            must(state['status']=='active','campaign is not active')
            snapshot=root/state['tools']; tools_current_match(snapshot)
            entry=manifest['plan'][state['next_index']]
            mode,case=entry['mode'],entry['case']; backend,variant=case.split('-',1)
            must(value is None or value==case or value==mode+':'+case,
                 'expected '+mode+':'+case)
            identity=manifest['packages'][mode][variant]; package=Path(identity['path'])
            if mode=='read': check_read_package(package)
            else: check(package)
            must(package_identity(package)==identity,'frozen package changed')
            if action=='boot':
                prefix='vkso-final-' if mode=='read' else 'vkso-update-'
                image=Path('/boot')/(prefix+case+'-5.15.198.bzImage')
                must(sha256(image)==sha256(package/(backend+'-bzImage')),'installed image mismatch')
                script=snapshot/('baremetal/boot-once.sh' if mode=='read' else 'update-bench/boot-update-once.sh')
                subprocess.run([str(script),case],check=True)
            else:
                boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                for previous in root.glob('block-*/*/*/run.json'):
                    must(json.loads(previous.read_text())['boot_id']!=boot,
                         'this boot was already collected; reboot before the next case')
                final=root/('block-%02d'%entry['block'])/mode/case
                must(not final.exists(),'result exists; refusing overwrite')
                partial=root/('.partial-'+mode+'-'+case+'-'+str(time.time_ns()))
                if mode=='read':
                    c=manifest['config']
                    read_config={key:c[source] for key,source in
                                 [('CPU','CPU'),('ITERATIONS','READ_ITERATIONS'),
                                  ('WARMUP','READ_WARMUP'),('REPEATS','READ_REPEATS'),
                                  ('PERF_PROCESSES','READ_PROCESSES')]}
                    env=dict(os.environ,DIRECT_PACKAGE=str(package),DIRECT_OUT=str(partial),
                             DIRECT_CONFIG=json.dumps(read_config),DIRECT_BLOCK=str(entry['block']),
                             DIRECT_TOOL_REVISION=state['tools'])
                    argv=[str(snapshot/'baremetal/collect-case.sh'),case,root.name]
                else:
                    env=dict(os.environ)
                    argv=['setarch','x86_64','-R',sys.executable,str(snapshot/'update-bench/stateful.py'),
                          '_collect','--package',str(package),'--case',case,'--out',str(partial),
                          '--config',json.dumps(manifest['config']),'--block',str(entry['block']),
                          '--revision',state['tools']]
                    if os.geteuid()!=0: argv=['sudo',*argv]
                try:
                    run_collector(argv,env,needs_sudo=os.geteuid()!=0)
                    must(json.loads((partial/'run.json').read_text())['status']=='COMPLETE',
                         'collector incomplete')
                    final.parent.mkdir(parents=True,exist_ok=True); partial.rename(final)
                except BaseException:
                    if partial.exists():
                        incomplete=root/'incomplete'; incomplete.mkdir(exist_ok=True)
                        partial.rename(incomplete/partial.name)
                    raise
                state['next_index']+=1
                if state['next_index']==len(manifest['plan']): state['status']='complete'
                atomic(statefile,state)
        print('result_root='+str(root)); print('status='+state['status'])
        print('completed_boots='+str(state['next_index']))
        if state['status']=='active':
            entry=manifest['plan'][state['next_index']]
            print('next_block=%d next_mode=%s next_case=%s'%
                  (entry['block'],entry['mode'],entry['case']))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['begin','boot','collect','status','aggregate','distribution-report','refresh-tools','stop','verify','_collect',
                                     'diagnose','_diagnose','diagnose-report',
                                     'diagnose-state-report','diagnose-pt',
                                     'diagnose-cacheline','diagnose-pmu','diagnose-cacheprep',
                                     'diagnose-percall-pmu','diagnose-prefetch','diagnose-order',
                                     'diagnose-business',
                                     '_cacheline_reader'])
    p.add_argument('value',nargs='?')
    p.add_argument('--package',type=Path); p.add_argument('--case'); p.add_argument('--out',type=Path)
    p.add_argument('--config'); p.add_argument('--block',type=int); p.add_argument('--revision')
    p.add_argument('--runs',nargs='+',type=Path)
    p.add_argument('--stage',action='store_true',help='use the separate stage-timing diagnostic kernel')
    p.add_argument('--split',action='store_true',help='sample one selected stage boundary per UPDATE')
    p.add_argument('--pt',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--cacheline',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--pmu',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--cacheprep',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--percall-pmu',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--prefetch',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--order',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--business',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--business-target', choices=('update_vsyscall','timekeeping_advance'),
                   default='update_vsyscall',
                   help='diagnose-business PT target; timekeeping_advance includes tick/NTP work before UPDATE')
    p.add_argument('--symbol',choices=('linux_banner','tk_fast_mono','tk_fast_raw'),help=argparse.SUPPRESS)
    a=p.parse_args()
    must(a.business_target=='update_vsyscall' or
         a.action=='diagnose-business' or (a.action=='_diagnose' and a.business),
         '--business-target is only valid for diagnose-business')
    def interrupted(signum,frame): raise InterruptedError('signal '+str(signum))
    for sig in (signal.SIGTERM,signal.SIGHUP): signal.signal(sig,interrupted)
    if a.action=='_cacheline_reader':
        cacheline_reader(a.symbol); return
    if a.action=='verify': check(a.package.resolve()); print('stateful_package=PASS'); return
    if a.action=='distribution-report':
        must(a.runs and a.out, 'provide --runs CAMPAIGN [CAMPAIGN ...] --out NEW_DIRECTORY')
        from distributions import generate
        generate(a.runs,a.out,aggregate)
        return
    if a.action=='diagnose-report':
        must(a.runs and a.out and not a.out.exists(),
             'provide --runs RUN [RUN ...] --out NEW.json')
        report=diagnosis_report([path.resolve() for path in a.runs])
        write_json(a.out,report)
        print('diagnosis_report='+str(a.out)); print('independent_boots='+str(report['boots']))
        return
    if a.action=='diagnose-state-report':
        must(a.runs and a.out and not a.out.exists(),
             'provide --runs RUN [RUN ...] --out NEW.json')
        report=no_marker_state_report([path.resolve() for path in a.runs])
        write_json(a.out,report)
        print('state_report='+str(a.out)); print('independent_boots='+str(report['boots']))
        return
    if a.action in ('diagnose','diagnose-pt','diagnose-cacheline','diagnose-pmu',
                    'diagnose-cacheprep','diagnose-percall-pmu','diagnose-prefetch',
                    'diagnose-order','diagnose-business'):
        must(a.package and a.case and a.out and
             a.case in ('raw-normal','vkso-normal'),
             'use diagnose[-pt|-cacheline|-pmu|-cacheprep|-percall-pmu|-prefetch|-order|-business] --package PACKAGE --case raw-normal|vkso-normal --out NEW_DIRECTORY')
        must(not a.out.exists(),'output already exists; choose a new --out directory: '+str(a.out))
        package=a.package.resolve(); out=a.out.resolve()
        must(not a.pt and not (a.stage and a.split) and
             (a.action not in ('diagnose-pt','diagnose-cacheline','diagnose-pmu','diagnose-cacheprep','diagnose-percall-pmu','diagnose-prefetch','diagnose-order','diagnose-business') or not (a.stage or a.split)),
             'choose one diagnosis mode')
        check(package)
        if a.action=='diagnose-cacheprep':
            must(a.case=='raw-normal' and
                 kv_file(package/'boot-manifest.txt').get('raw_cacheprep_diagnostic')=='1',
                 'use the Raw normal cache-preparation diagnostic package')
        if a.action=='diagnose-percall-pmu':
            must(a.case=='raw-normal' and
                 kv_file(package/'boot-manifest.txt').get('raw_percall_pmu_diagnostic')=='1',
                 'use the Raw normal per-call PMU diagnostic package')
        if a.action=='diagnose-prefetch':
            must(a.case=='raw-normal' and
                 kv_file(package/'boot-manifest.txt').get('raw_prefetch_diagnostic')=='1',
                 'use the new Raw normal prefetch diagnostic package')
        if a.action in ('diagnose-order','diagnose-business'):
            must(a.case=='raw-normal' and
                 kv_file(package/'boot-manifest.txt').get('raw_order_diagnostic')=='1',
                 'use the Raw normal order diagnostic package')
        if a.stage or a.split:
            must(kv_file(package/'boot-manifest.txt').get('update_stage_diag')=='1',
                 'stage/split diagnosis needs a package built with UPDATE_STAGE_DIAG=1')
        if a.split:
            must(kv_file(package/'boot-manifest.txt').get('update_split_diag')=='1',
                 'package predates the split recorder; rebuild both UPDATE images')
        c=config(); c.update(REPEATS=1 if a.action in ('diagnose-pt','diagnose-cacheline','diagnose-pmu','diagnose-cacheprep','diagnose-percall-pmu','diagnose-prefetch','diagnose-order','diagnose-business') else 3,
                             UPDATE_SECONDS=20 if a.action=='diagnose-business' else 8 if a.action in ('diagnose-cacheline','diagnose-pmu','diagnose-cacheprep','diagnose-percall-pmu','diagnose-prefetch') else 10,
                             STABILIZE_SECONDS=30)
        argv=['setarch','x86_64','-R',sys.executable,str(Path(__file__).resolve()),
              '_diagnose','--package',str(package),'--case',a.case,'--out',str(out),
              '--config',json.dumps(c)]
        if a.stage: argv.append('--stage')
        if a.split: argv.append('--split')
        if a.action=='diagnose-pt': argv.append('--pt')
        if a.action=='diagnose-cacheline': argv.append('--cacheline')
        if a.action=='diagnose-pmu': argv.extend(('--cacheline','--pmu'))
        if a.action=='diagnose-cacheprep': argv.append('--cacheprep')
        if a.action=='diagnose-percall-pmu': argv.append('--percall-pmu')
        if a.action=='diagnose-prefetch': argv.append('--prefetch')
        if a.action=='diagnose-order': argv.append('--order')
        if a.action=='diagnose-business':
            argv.extend(('--business','--business-target',a.business_target))
        if os.geteuid()!=0: argv=['sudo',*argv]
        run_collector(argv,needs_sudo=os.geteuid()!=0)
        must(json.loads((out/'run.json').read_text())['status']=='COMPLETE',
             'diagnostic collection incomplete')
        print(('pt_diagnosis_run=' if a.action=='diagnose-pt' else
               'pmu_diagnosis_run=' if a.action=='diagnose-pmu' else
               'cacheprep_diagnosis_run=' if a.action=='diagnose-cacheprep' else
               'percall_pmu_diagnosis_run=' if a.action=='diagnose-percall-pmu' else
               'prefetch_diagnosis_run=' if a.action=='diagnose-prefetch' else
               'order_diagnosis_run=' if a.action=='diagnose-order' else
               'business_diagnosis_run=' if a.action=='diagnose-business' else
               'cacheline_diagnosis_run=' if a.action=='diagnose-cacheline' else
               'diagnosis_run=')+str(out))
        return
    if a.action=='_diagnose':
        must(os.geteuid()==0,'root required')
        with open('/run/vkso-direct-api.lock','a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            collect(a.package.resolve(),a.case,json.loads(a.config),a.out,
                    0,'standalone-diagnostic',diagnostic=True,staged=a.stage,
                    split=a.split,pt=a.pt,cacheline=a.cacheline,pmu=a.pmu,
                    cacheprep=a.cacheprep,percall_pmu=a.percall_pmu,
                    prefetch=a.prefetch,order=a.order,business=a.business,
                    business_target=a.business_target)
        return
    if a.action=='_collect':
        must(os.geteuid()==0,'root required')
        with open('/run/vkso-direct-api.lock','a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            collect(a.package.resolve(),a.case,json.loads(a.config),a.out,a.block,a.revision)
    else: campaign(a.action,a.value)

if __name__=='__main__':
    try: main()
    except (OSError,ValueError,RuntimeError,KeyError,subprocess.SubprocessError) as e:
        sys.exit('stateful refused/failed: '+str(e))
