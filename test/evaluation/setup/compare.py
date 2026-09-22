#!/usr/bin/env python3
"""Compare complete LZ4 tasks with/without observers and registration cost.

active runs native/carrier processes inside an existing registration. ready
runs native commands and complete exec-ready commands after the main session.
The same full task and library baselines are used in both phases.
"""
from pathlib import Path
import argparse
import itertools
import json
import os
import subprocess
import time
try:
    from .collect import events
except ImportError:
    from collect import events


def now():
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)


def observe(argv, path, env, traced, iterations):
    started=now()
    with path.open('w') as stream:
        result=subprocess.run(list(map(str,argv)),env=env,stdout=stream,stderr=subprocess.STDOUT)
    ended=now();raw=path.read_text()
    if result.returncode: raise RuntimeError(f'command failed ({result.returncode}): {path}')
    valid=[line for line in raw.splitlines() if line.startswith('valid\tlz4\t')]
    assert valid==[f'valid\tlz4\t12\t211938580\t{iterations}'],valid
    samples=events(raw) if traced else []
    if not traced: assert not any(line.startswith('event\t') for line in raw.splitlines())
    row=dict(argv=list(map(str,argv)),start_ns=started,end_ns=ended,total_ns=ended-started,
             returncode=0,log=path.name,inputs=12,input_bytes=211938580,iterations=iterations,
             events=samples,first_valid_ns=None,to_first_valid_ns=None)
    if traced:
        def one(name):
            values=[e['ns'] for e in samples if e['name']==name];assert len(values)==1,(name,values)
            return values[0]
        assert started<=one('process.main')<=one('load.begin')<=one('load.end')<=one('task.begin')<=one('first.valid')<=one('task.end')<=one('unload.end')<=ended
        row.update(first_valid_ns=one('first.valid'),to_first_valid_ns=one('first.valid')-started)
    return row


def run(phase, work, native, manifest, binaries, vkso, output, cpu, rounds=3):
    work,native,manifest,binaries,vkso,output=map(lambda p:Path(p).resolve(),(work,native,manifest,binaries,vkso,output))
    assert phase in ('active','ready') and rounds>0 and cpu in os.sched_getaffinity(0)
    fields=dict(line.split('=',1) for line in (work/'vkso/metadata/outputs.env').read_text().splitlines())
    library=Path(fields['library']).resolve()
    for path in (library,native,manifest,binaries/'setup-lz4',binaries/'setup-lz4-plain',vkso):assert path.is_file(),path
    output.mkdir(parents=True,exist_ok=False)
    prior=os.sched_getaffinity(0);os.sched_setaffinity(0,{cpu})
    env=dict(os.environ)
    for key in ('VKSO_SETUP_TRACE','VKSO_SETUP_CLOCK','LD_PRELOAD'):env.pop(key,None)
    record=dict(status='running',phase=phase,cpu_affinity=[cpu],rounds=rounds,
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                kernel=os.uname().release,rows=[],warmup=[],clock_calibration=[],
                libraries=dict(native=str(native),vkso=str(library)),
                scope='full 12-file compression/decompression/validation; process repetitions within one owner deployment',
                cache_policy='one complete warmup per backend; repeated input use without eviction; registration/restoration retained',
                timing='external CLOCK_MONOTONIC_RAW; trace off totals and trace on first-valid/stages kept separate')
    def save(): (output/'comparison.json').write_text(json.dumps(record,indent=2)+'\n')
    def launch(backend,traced,iterations,label):
        driver=binaries/('setup-lz4' if traced else 'setup-lz4-plain')
        command=[driver,library if backend=='vkso' else native,manifest,'65536',str(iterations)]
        current=dict(env);trace=output/(label+'-stages.tsv')
        if phase=='ready' and backend=='vkso':
            command=[vkso,'exec-ready',work,'--',*command]
            if traced:current.update(VKSO_SETUP_TRACE=str(trace),VKSO_SETUP_CLOCK=str(binaries/'setup-clock'))
        row=observe(command,output/(label+'.log'),current,traced,iterations)
        row.update(backend=backend,traced=traced,shell_events=[],kernel_transactions=[])
        if trace.exists():
            row['shell_events']=events(trace.read_text())
            names=[e['name'] for e in row['shell_events']]
            assert names==['command.begin','session.begin','manager.begin','manager.ready','application.begin','application.end','cleanup.begin','cleanup.end'],names
            assert row['start_ns']<=row['shell_events'][0]['ns']<row['first_valid_ns']<=row['shell_events'][-1]['ns']<=row['end_ns']
        if phase=='ready' and backend=='vkso':
            import re
            logs=[line for line in (work/'vkso/metadata/page_replace.log').read_text().splitlines() if line.startswith('VKSO_TRANSACTION id=')]
            operations=[{k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)} for line in logs]
            # exec-ready appends to the existing manager log: retain this completed session.
            starts=[i for i,r in enumerate(operations) if r['operation']==1];assert starts
            current_ops=operations[starts[-1]:]
            assert [r['operation'] for r in current_ops]==[1,2,3,5,6]
            assert len({r['id'] for r in current_ops})==1 and all(r['status']==0 for r in current_ops)
            assert current_ops[2]['applied']==5 and current_ops[3]['applied']==0
            row['kernel_transactions']=current_ops
        return row
    try:
        for backend in ('native','vkso'):
            record['warmup'].append(launch(backend,False,1,'warmup-'+backend));save()
        # Rotate all eight conditions. Formal independent units remain deployments.
        conditions=list(itertools.product(('native','vkso'),(False,True),(1,3)))
        for repeat in range(rounds):
            ordered=conditions[repeat%8:]+conditions[:repeat%8]
            if repeat%2:ordered=list(reversed(ordered))
            for position,(backend,traced,iterations) in enumerate(ordered):
                row=launch(backend,traced,iterations,f'{repeat:02}-{position:02}-{backend}-{int(traced)}-{iterations}')
                row.update(repeat=repeat,position=position);record['rows'].append(row);save()
        if phase=='ready':
            calibration=output/'clock-calibration.tsv'
            for i in range(30):
                started=now();subprocess.run([str(binaries/'setup-clock'),str(calibration),str(os.getpid()),'calibration'],check=True)
                ended=now();record['clock_calibration'].append(dict(start_ns=started,end_ns=ended,total_ns=ended-started))
            stamps=events(calibration.read_text());assert len(stamps)==30
            for row,stamp in zip(record['clock_calibration'],stamps):assert row['start_ns']<=stamp['ns']<=row['end_ns']
        record['status']='pass'
    except BaseException as error:
        record.update(status='fail',error=repr(error));raise
    finally:
        os.sched_setaffinity(0,prior);save()
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('active','ready'))
    for name in ('work','native','manifest','binaries','vkso','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cpu',type=int,default=2);p.add_argument('--rounds',type=int,default=3)
    a=p.parse_args();r=run(**vars(a));print(json.dumps(dict(status=r['status'],phase=r['phase'],rows=len(r['rows'])),indent=2))
