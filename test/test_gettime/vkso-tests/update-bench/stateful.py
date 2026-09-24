#!/usr/bin/env python3
"""Instrumented UPDATE/concurrent protocol; fixed shell entrypoints dispatch here."""
import argparse
from collections import Counter
from contextlib import contextmanager
import csv
import fcntl
import gzip
import json
import mmap
import os
from pathlib import Path
import platform
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
    outer = verify_sums(package, REQUIRED | {'direct/build.json','direct/SHA256SUMS',
        'direct/native-load','direct/vkso-load','direct/libvkso_time.so',
        'direct/native-bench.sections.txt','direct/vkso-bench.sections.txt',
        'direct/libvkso_time.so.sections.txt'})
    m = kv_file(package/'boot-manifest.txt')
    must(m.get('update_bench') == '1' and m.get('vkso_validation_tests') == '0', 'requires UPDATE instrumentation, no validation probes')
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
        must('CONFIG_TIMEKEEPING_UPDATE_BENCH=y\n' in (package/(backend+'.config')).read_text(), 'instrumentation absent')
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


def diagnostic_rows(path):
    lines = path.read_text().splitlines()
    header = next((i for i,line in enumerate(lines) if line.startswith('sample,')), None)
    must(header is not None, 'missing diagnostic sample header')
    rows = list(csv.DictReader(lines[header:]))
    must(bool(rows) and DIAG_FIELDS <= set(rows[0]), 'diagnostic state columns missing')
    for row in rows:
        must(0 <= int(row['phase_nsec']) < 1000000000 and
             all(int(row[field]) in (0,1) for field in
                 ('ktime_carry','realtime_carry','monotonic_carry','leap_pending')) and
             0 <= int(row['shift']) <= 32, 'invalid diagnostic state')
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


def window(recorder, seconds, dest, reader=None, diagnostic=False):
    """Writer starts after READY + first completed reader batch; stops before reader.
    Reader batch distribution covers the enclosing sustained-load interval, not
    exact writer wall time. No throughput inference from a nominal duration.
    """
    proc = control = output = err = None; running = False
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
        running = True
        recorder.joinpath('control').write_text('diagnose\n' if diagnostic else 'start\n')
        start = time.monotonic_ns(); deadline = time.monotonic()+seconds
        first_batch = struct.unpack_from('Q',control,16)[0] if control else None
        while time.monotonic()<deadline:
            if proc: must(proc.poll() is None,'reader exited during writer recording')
            time.sleep(min(.05,max(0,deadline-time.monotonic())))
        recorder.joinpath('control').write_text('stop\n'); running = False
        end = time.monotonic_ns()
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
        write_json(dest.with_suffix('.json'),dict(writer_start_ns=start,writer_end_ns=end,
                   load_batch_before_start=first_batch,load_batch_after_stop=last_batch,
                   reader_window='enclosing load interval; writer window is nested'))
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


def collect(package,case,c,out,block,revision,diagnostic=False):
    record = preflight(package,case,c)
    out.mkdir(parents=True,exist_ok=False)
    record.update(scope='diagnostic' if diagnostic else 'all',
                  block=block,tool_revision=revision)
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
                for r in range(c['REPEATS']):
                    for operation in SCENARIOS:
                        print(f'round={r+1}/{c["REPEATS"]} scenario={operation}',flush=True)
                        directory=out/operation; directory.mkdir(exist_ok=True)
                        dest=directory/('round-%02d.csv'%r)
                        reader=None
                        if operation!='idle':
                            reader=[str(package/'direct'/('native-load' if backend=='raw' else 'vkso-load')),
                                    str(c['CPU']),operation,str(c['READER_ITERATIONS']),str(c['WARMUP'])]
                        # Disable ASLR in controller, inherited by reader, via outer setarch.
                        window(recorder,c['UPDATE_SECONDS'],dest,reader,diagnostic)
                        writer_rows(dest)
                        if diagnostic: diagnostic_rows(dest)
                        if reader: reader_rows(dest.with_name(dest.stem+'-reader.csv'),c['READER_ITERATIONS'])
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


def diagnosis_report(paths):
    """Descriptive within-boot mode/state tables; never infer independence per tick."""
    summaries=[]; boots=set()
    for path in paths:
        verify_sums(path, {'run.json','start.json','abi.log','check.log','check-fast.log'})
        run=json.loads((path/'run.json').read_text())
        must(run['status']=='COMPLETE' and run['scope']=='diagnostic' and
             run['environment_cleanup']=='PASS', 'not a complete diagnostic run')
        must(sha256(Path(run['package'])/'SHA256SUMS')==run['package_sha256'],
             'diagnostic package identity changed')
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
                data,calibration=diagnostic_rows(round_path)
                rows.extend(r for r in data if int(r['action'])==0 and int(r['cpu'])==0)
                pairs.extend(calibration)
            must(len(rows)>=1000, 'too few CPU0 periodic samples')
            low=[int(r['cycles']) for r in rows if int(r['cycles'])<=threshold]
            high=[int(r['cycles']) for r in rows if int(r['cycles'])>threshold]
            must(low and high, 'no two descriptive mode groups')
            flags={}
            for field in ('ktime_carry','realtime_carry','monotonic_carry','leap_pending'):
                groups={str(value):[r for r in rows if int(r[field])==value]
                        for value in (0,1)}
                flags[field]={value:dict(count=len(group),
                    high_fraction=(sum(int(r['cycles'])>threshold for r in group)/len(group)
                                   if group else None))
                    for value,group in groups.items()}
            phase=[]
            for bin_no in range(10):
                group=[r for r in rows if int(r['phase_nsec'])//100000000==bin_no]
                phase.append(dict(phase_decile=bin_no,count=len(group),
                    high_fraction=(sum(int(r['cycles'])>threshold for r in group)/len(group)
                                   if group else None)))
            summaries.append(dict(path=str(path),boot_id=run['boot_id'],case=run['case'],
                scenario=scenario,unit='TSC ticks',periodic_cpu0_samples=len(rows),
                historical_valley_threshold=threshold,low_count=len(low),high_count=len(high),
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
                flag_groups=flags,phase_deciles=phase))
    return dict(protocol='clocktime-update-bimodal-diagnosis-v1',
                scope='descriptive; boot is independent unit; mode labels use prior normal peaks',
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
    p.add_argument('action',choices=['begin','boot','collect','status','aggregate','refresh-tools','stop','verify','_collect',
                                     'diagnose','_diagnose','diagnose-report'])
    p.add_argument('value',nargs='?')
    p.add_argument('--package',type=Path); p.add_argument('--case'); p.add_argument('--out',type=Path)
    p.add_argument('--config'); p.add_argument('--block',type=int); p.add_argument('--revision')
    p.add_argument('--runs',nargs='+',type=Path)
    a=p.parse_args()
    def interrupted(signum,frame): raise InterruptedError('signal '+str(signum))
    for sig in (signal.SIGTERM,signal.SIGHUP): signal.signal(sig,interrupted)
    if a.action=='verify': check(a.package.resolve()); print('stateful_package=PASS'); return
    if a.action=='diagnose-report':
        must(a.runs and a.out and not a.out.exists(),
             'provide --runs RUN [RUN ...] --out NEW.json')
        report=diagnosis_report([path.resolve() for path in a.runs])
        write_json(a.out,report)
        print('diagnosis_report='+str(a.out)); print('independent_boots='+str(report['boots']))
        return
    if a.action=='diagnose':
        must(a.package and a.case and a.out and
             a.case in ('raw-normal','vkso-normal') and not a.out.exists(),
             'use diagnose --package PACKAGE --case raw-normal|vkso-normal --out NEW_DIRECTORY')
        package=a.package.resolve(); out=a.out.resolve()
        check(package)
        c=config(); c.update(REPEATS=3,UPDATE_SECONDS=10,STABILIZE_SECONDS=30)
        argv=['setarch','x86_64','-R',sys.executable,str(Path(__file__).resolve()),
              '_diagnose','--package',str(package),'--case',a.case,'--out',str(out),
              '--config',json.dumps(c)]
        if os.geteuid()!=0: argv=['sudo',*argv]
        run_collector(argv,needs_sudo=os.geteuid()!=0)
        must(json.loads((out/'run.json').read_text())['status']=='COMPLETE',
             'diagnostic collection incomplete')
        print('diagnosis_run='+str(out))
        return
    if a.action=='_diagnose':
        must(os.geteuid()==0,'root required')
        with open('/run/vkso-direct-api.lock','a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            collect(a.package.resolve(),a.case,json.loads(a.config),a.out,
                    0,'standalone-diagnostic',diagnostic=True)
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
