#!/usr/bin/env python3
"""Pressure scenario for the existing registered first-touch guest and runner."""
from pathlib import Path
import ctypes,json,os,random,shutil,subprocess,time
from lz4_guest_helpers import execute,observe_registered_pages,write_json
ROOT=Path('/work');OUT=ROOT/'validation';WORK=OUT/'export'

def snapshot():
    value={'monotonic_raw_ns':time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)}
    for name in ('vmstat','meminfo','pressure/memory','pressure/io','swaps'):
        path=Path('/proc')/name
        value[name]=path.read_text() if path.exists() else None
    return value

def numbers(text):
    return {line.split()[0].rstrip(':'):int(line.split()[1]) for line in text.splitlines()}

class Child:
    def __init__(self,command,label,environment=None):
        self.label=label;self.err=(OUT/f'pressure-{label}.stderr').open('w')
        self.p=subprocess.Popen(list(map(str,command)),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                stderr=self.err,text=True,bufsize=1,env=environment)
    def response(self,command=None):
        started=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
        if command is not None:
            self.p.stdin.write(command+'\n');self.p.stdin.flush()
        line=self.p.stdout.readline()
        if not line: raise RuntimeError(f'{self.label} ended: {self.p.poll()}')
        value=json.loads(line)
        with (OUT/'pressure-events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(child=self.label,command=command,start_ns=started,
                end_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW),response=value))+'\n')
        return value
    def close(self):
        if self.p.poll() is None:
            self.p.stdin.write('QUIT\n');self.p.stdin.flush()
        code=self.p.wait(timeout=30);self.err.close()
        assert code==0,(self.label,code)

def validate():
    os.sched_setaffinity(0,{0})
    fields=dict(x.split('=',1) for x in (WORK/'vkso/metadata/outputs.env').read_text().splitlines())
    library=Path(fields['library']);native=ROOT/'native/libclone_xxh32.so'
    execute(['python3',ROOT/'guest.py','--functional'],OUT/'functional-process.log')
    shutil.copy2(OUT/'functional.json',OUT/'functional-before-pressure.json')
    assert str(native) not in Path('/proc/self/maps').read_text()
    (OUT/'controller-maps-before-sampling.txt').write_text(Path('/proc/self/maps').read_text())
    pages=observe_registered_pages(library,Path(fields['page_map']))
    write_json(OUT/'pressure-pfns-before.json',pages)
    assert len(pages['pages'])==1
    source_pfn=pages['pages'][0]['kernel_pfn']
    oracle=ctypes.CDLL(str(ROOT/'oracle/libxxhash.so.0')).XXH32
    oracle.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint32];oracle.restype=ctypes.c_uint32
    expected=oracle(b'hello',5,0x1234)
    env=dict(os.environ,STUB_DSO=str(library),NATIVE_DSO=str(native))
    children=[];rows=[];rng=random.Random(20260912)
    try:
        worker=Child([ROOT/'benchmark/pressure_worker',ROOT/'pressure-working-set.bin'],'worker');children.append(worker)
        ready=worker.response();assert ready['file_bytes']==1024**3
        probes={}
        for name in ('native','stub'):
            child=Child([ROOT/'benchmark/pressure_probe',name,expected],name,env);children.append(child)
            probes[name]=child;assert child.response()['cpu']==1
        initial=snapshot();mem=numbers(initial['meminfo'])
        assert mem['SwapTotal']==0 and len(initial['swaps'].splitlines())==1
        reserve=(min(mem['MemAvailable']*1024-512*1024**2,mem['MemTotal']*1024*4//5)//4096)*4096
        assert reserve>=512*1024**2
        config=dict(protocol='first-touch-pressure-v1',seed=20260912,trials_per_phase=10,
            phases=['baseline','pressure','recovery'],file_bytes=1024**3,passes_per_trial=2,
            anonymous_bytes=reserve,reservation_rule='min(MemAvailable - 512 MiB, 0.8 * MemTotal), page aligned',
            probe_cpu=1,worker_cpu=0,expected=expected,input_hex=b'hello'.hex(),hash_seed=0x1234,
            source_pfn=source_pfn,initial=initial,scope='idle page reclaim after PTE removal; all calls retained; diagnostic guest cycles')
        write_json(OUT/'pressure-config.json',config)
        for phase in config['phases']:
            if phase=='pressure':
                assert worker.response(f'ALLOC {reserve}')['anonymous_bytes']==reserve
            elif phase=='recovery': assert worker.response('FREE')['anonymous_bytes']==0
            phase_start=snapshot()
            for trial in range(10):
                order=['native','stub'];rng.shuffle(order)
                prepared={name:probes[name].response('PREP') for name in order}
                assert all(not (v['pte']>>63) for v in prepared.values())
                before=snapshot()
                scan=worker.response('SCAN') if phase=='pressure' else None
                after=snapshot()
                calls={name:probes[name].response('CALL') for name in order}
                row=dict(phase=phase,trial=trial,order=order,prepared=prepared,before=before,after=after,
                    scan=scan,calls=calls,owner_refcnt=int(Path('/sys/module/zzk_xxh32_lkm/refcnt').read_text()),
                    worker_smaps_rollup=Path(f'/proc/{worker.p.pid}/smaps_rollup').read_text())
                rows.append(row)
                with (OUT/'pressure-trials.jsonl').open('a') as stream: stream.write(json.dumps(row)+'\n')
                for name,value in calls.items():
                    assert value['answer']==expected and value['cpu']==1 and value['pte_after']>>63
                    assert not value['pte_before']>>63
                    if name=='stub': assert value['pte_after']&((1<<55)-1)==source_pfn
                assert row['owner_refcnt']==1
            write_json(OUT/f'pressure-phase-{phase}.json',dict(before=phase_start,after=snapshot()))
        pages=observe_registered_pages(library,Path(fields['page_map']))
        write_json(OUT/'pressure-pfns-after.json',pages)
        assert pages['pages'][0]['kernel_pfn']==source_pfn
    finally:
        # Free the reservation before running validation subprocesses or cleanup.
        errors=[]
        for child in reversed(children):
            try: child.close()
            except BaseException as error: errors.append(repr(error))
        if errors: raise RuntimeError(errors)
    execute(['python3',ROOT/'guest.py','--functional'],OUT/'functional-after-pressure.log')
    shutil.copy2(OUT/'functional.json',OUT/'functional-after-pressure.json')
    from first_touch_pressure_audit import summarize
    report=summarize(OUT)
    write_json(OUT/'pressure-summary.json',report)
    write_json(OUT/'collection-status.json',dict(status='complete' if report['reclaim_exercised'] else 'incomplete',
        scope='pressure scenario; not physical-host performance',pressure=report))
