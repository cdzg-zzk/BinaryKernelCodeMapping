#!/usr/bin/env python3
"""Collect full-task process setup in an already registered algorithm session."""
from pathlib import Path
import csv,json,os,subprocess,time

def now():
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)

def events(text):
    result=[]
    for line in text.splitlines():
        fields=line.split('\t')
        if fields[0]=='event':
            assert len(fields)==4,fields
            result.append(dict(pid=int(fields[1]),name=fields[2],ns=int(fields[3])))
    assert result and all(a['ns']<=b['ns'] for a,b in zip(result,result[1:]))
    return result

def process(command, output):
    start=now()
    with output.open('w') as log:
        result=subprocess.run(list(map(str,command)),stdout=log,stderr=subprocess.STDOUT)
    end=now()
    text=output.read_text()
    assert result.returncode==0,(command,result.returncode,text[-1000:])
    samples=events(text)
    def one(name):
        found=[e['ns'] for e in samples if e['name']==name]
        assert len(found)==1,(name,found)
        return found[0]
    assert start<=one('process.main')<=one('load.begin')<=one('load.end')<=one('task.begin')<=one('first.valid')<=one('task.end')<=one('unload.end')<=end
    validity=[line.split('\t') for line in text.splitlines() if line.startswith('valid\t')]
    assert len(validity)==1 and len(validity[0])==5
    _,algorithm,inputs,size,iterations=validity[0]
    intervals={name:one(name+'.end')-one(name+'.begin') for name in ('load','task','unload')}
    intervals['dlopen']=one('dlopen.end')-one('dlopen.begin')
    lookups=[e for e in samples if e['name'].startswith('dlsym.')]
    assert len(lookups)%2==0
    assert all(a['name']=='dlsym.begin' and b['name']=='dlsym.end' for a,b in zip(lookups[::2],lookups[1::2]))
    intervals['dlsym_sum']=sum(b['ns']-a['ns'] for a,b in zip(lookups[::2],lookups[1::2]))
    return dict(argv=list(map(str,command)),returncode=result.returncode,start_ns=start,end_ns=end,
        external_total_ns=end-start,external_to_first_valid_ns=one('first.valid')-start,
        load_to_first_valid_ns=one('first.valid')-one('load.begin'),first_valid_ns=one('first.valid'),
        stage_ns=intervals,events=samples,algorithm=algorithm,inputs=int(inputs),bytes=int(size),
        iterations=int(iterations),log=output.name)

def active(algorithm, root, output, work):
    root,output,work=map(Path,(root,output,work));output.mkdir(parents=True,exist_ok=False)
    fields=dict(line.split('=',1) for line in (work/'vkso/metadata/outputs.env').read_text().splitlines())
    library=Path(fields['library']);driver=root/'setup'/('setup-'+algorithm)
    native={'lz4':root/'baselines/libkernel-userspace-libc.so',
            'bch':root/'binaries/libbch-kernel-native.so','xz':root/'binaries/libxz-native.so'}[algorithm]
    def command(backend,iterations):
        selected=library if backend=='kernel-vkso' else native
        if algorithm=='lz4':
            return [driver,selected,root/'corpus/manifest.txt','65536',str(iterations)]
        if algorithm=='bch': return [driver,selected,backend,str(iterations)]
        manifest=list(csv.reader((root/'validation/corpus/manifest.csv').read_text().splitlines()))
        assert len(manifest)==3
        return [driver,selected,'vkso_xz_' if backend=='kernel-vkso' else 'xz_',str(iterations),'--',
                *[value for row in manifest for value in row]]
    # First process measures the newly registered carrier before any PFN observer
    # faults it. Later alternating pairs are warm session/process repetitions.
    rows=[]
    for i,(backend,iterations) in enumerate([('kernel-vkso',1),('native',1),
            ('native',3),('kernel-vkso',3),('kernel-vkso',1),('native',1)]):
        row=process(command(backend,iterations),output/f'{i:02}-{backend}-{iterations}.log')
        assert row['inputs']=={'lz4':12,'bch':2,'xz':3}[algorithm]
        row.update(backend=backend,position=i,condition='first process after registration' if i==0 else 'subsequent process; caches not flushed')
        rows.append(row)
    record=dict(status='pass',algorithm=algorithm,clock='CLOCK_MONOTONIC_RAW',
                scope='functional collection validation; six processes in one registration, not six independent deployments',
                library=str(library),native=str(native),rows=rows)
    (output/'processes.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('algorithm',choices=['lz4','bch','xz']);p.add_argument('output',type=Path)
    p.add_argument('--root',type=Path,default=Path('/work'));p.add_argument('--work',type=Path,default=Path('/work/validation/export'))
    a=p.parse_args();active(a.algorithm,a.root,a.output,a.work)


def ready(algorithm, root, output, work):
    root,output,work=map(Path,(root,output,work))
    trace=output.parent/'setup-ready-stages.tsv'
    command=[root/'repo/vkso','exec-ready',work,'--','python3',root/'setup/collect.py',algorithm,output]
    start=now()
    with (output.parent/'setup-ready-session.log').open('w') as stream:
        result=subprocess.run(list(map(str,command)),stdout=stream,stderr=subprocess.STDOUT,
            env=dict(os.environ,VKSO_SETUP_TRACE=str(trace),VKSO_SETUP_CLOCK=str(root/'setup/setup-clock')))
    end=now()
    assert result.returncode==0,(algorithm,result.returncode)
    data=json.loads((output/'processes.json').read_text())
    stages=events(trace.read_text())
    assert 'krg.begin' not in [x['name'] for x in stages]
    assert stages[-1]['name']=='cleanup.end'
    record=dict(status='pass',argv=list(map(str,command)),start_ns=start,end_ns=end,
                external_total_ns=end-start,external_to_first_valid_ns=data['rows'][0]['first_valid_ns']-start,
                stages=stages,scope='prebuilt carrier registration, six full-task processes and complete release')
    (output/'session.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
