#!/usr/bin/env python3
"""Measure complete registration at 1..32 inert pages in a private exact119 guest."""
import csv,ctypes as C,fcntl,io,json,os,random,re,select,signal,struct,subprocess,time,traceback
from pathlib import Path
import registration_completion_guest as G
from registration_transaction_guest import Client,Request,BEGIN,STAGE,COMMIT,QUERY,RELEASE,FORGET
ROOT,OUT,PAGE=G.ROOT,G.OUT,G.PAGE
COUNTS=(1,2,4,8,16,32)

def now(): return time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
def save(path,value): path.write_text(json.dumps(value,indent=2)+'\n')
def run(command,path):
    with path.open('w') as stream:
        r=subprocess.run(list(map(str,command)),stdout=stream,stderr=subprocess.STDOUT,timeout=20)
    assert r.returncode==0,(command,r.returncode)

def residency(path,count):
    fd=os.open(path,os.O_RDONLY)
    address=G.LIBC.mmap(None,count*PAGE,1,2,fd,PAGE);os.close(fd)
    assert address!=C.c_void_p(-1).value
    vector=(C.c_ubyte*count)()
    G.LIBC.mincore.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_ubyte)]
    try:
        assert G.LIBC.mincore(address,count*PAGE,vector)==0,C.get_errno()
        return [int(v)&1 for v in vector]
    finally: G.LIBC.munmap(address,count*PAGE)

def cache_condition(path,count,condition):
    fd=os.open(path,os.O_RDONLY)
    try:
        os.fsync(fd)
        if condition=='evicted': os.posix_fadvise(fd,PAGE,count*PAGE,os.POSIX_FADV_DONTNEED)
        else: assert os.pread(fd,count*PAGE,PAGE)==b'Z'*count*PAGE
    finally: os.close(fd)
    observed=residency(path,count)
    assert observed==[0 if condition=='evicted' else 1]*count,(condition,observed)
    return observed

def process_snapshot(pid):
    root=Path('/proc')/str(pid)
    data={name:(root/name).read_text() for name in ('status','smaps_rollup','maps')}
    data['fd_targets']={p.name:os.readlink(p) for p in (root/'fd').iterdir()}
    return data

def manager_session(path,plan,count,out,refs):
    fifo=out/'notify';os.mkfifo(fifo,0o600)
    fd=os.open(fifo,os.O_RDWR|os.O_NONBLOCK)
    buffer=b'';messages=[]
    def receive(expected):
        nonlocal buffer
        deadline=time.monotonic()+10
        while True:
            if b'\n' not in buffer:
                left=deadline-time.monotonic();assert left>0,(expected,messages)
                ready,_,_=select.select([fd],[],[],left);assert ready,(expected,messages)
                buffer+=os.read(fd,4096)
                continue
            line,buffer=buffer.split(b'\n',1)
            event,status,pid,tid=line.decode().split()
            item=dict(event=event,status=int(status),pid=int(pid),transaction=int(tid),received_ns=now())
            messages.append(item);assert event==expected and item['status']==0,(expected,item)
            return item
    log=out/'manager.log'
    with log.open('w') as stream:
        started=now()
        manager=subprocess.Popen([str(G.MANAGER),'replace',str(path),str(plan),'--hold','--notify-fifo',str(fifo)],
                                 stdout=stream,stderr=subprocess.STDOUT)
        try:
            start=receive('START');ready=receive('READY')
            assert start['pid']==ready['pid']==manager.pid and start['transaction']==ready['transaction']
            active=[G.observe(path,(i+1)*PAGE) for i in range(count)]
            assert all(not p['original'] for p in active)
            snapshot=process_snapshot(manager.pid)
            active_refs=refs();assert active_refs['vkso_tx_fixture']==1
            pipe_capacity=fcntl.fcntl(fd,fcntl.F_GETPIPE_SZ)
            release_start=now();manager.send_signal(signal.SIGTERM)
            done=receive('DONE');assert done['pid']==manager.pid and done['transaction']==ready['transaction']
            assert manager.wait(timeout=10)==0
            finished=now()
            result=dict(start_ns=started,ready_ns=ready['received_ns'],release_start_ns=release_start,
                done_ns=done['received_ns'],end_ns=finished,events=messages,transaction=ready['transaction'],
                register_to_ready_ns=ready['received_ns']-started,release_to_done_ns=done['received_ns']-release_start,
                active=active,active_refs=active_refs,pipe_capacity_bytes=pipe_capacity,
                scope='direct full manager process and FIFO; no vkso build or application execution')
            save(out/'manager-process.json',snapshot)
        finally:
            if manager.poll() is None:
                manager.send_signal(signal.SIGTERM)
                try: manager.wait(timeout=10)
                except subprocess.TimeoutExpired: manager.kill();manager.wait()
            os.close(fd)
    transactions=[]
    for line in log.read_text().splitlines():
        if line.startswith('VKSO_TRANSACTION '):
            transactions.append({key:int(value) for key,value in re.findall(r'(\w+)=(-?\d+)',line)})
    assert [x['operation'] for x in transactions]==[BEGIN,STAGE,COMMIT,RELEASE,FORGET]
    assert all(x['status']==0 and x['id']==result['transaction'] for x in transactions)
    result['transactions']=transactions
    return result

def direct_session(client,path,count,source,descriptor,version,tid,refs):
    r=Request();r.total=count;r.filepath=str(path).encode();st=path.stat();r.device=st.st_dev;r.inode=st.st_ino
    r.owner_count=1;r.owners[0].symbol=descriptor.encode();r.owners[0].srcversion=version.encode()
    operations=[]
    def rpc(op,request=None):
        started=now();response=client.rpc(op,tid,request=request);finished=now()
        operations.append(dict(operation=op,start_ns=started,end_ns=finished,response=response))
        return response
    begin=now();rpc(BEGIN,r)
    r=Request();r.total=r.count=count
    for i in range(count): r.pages[i].offset=(i+1)*PAGE;r.pages[i].source=source+i*PAGE;r.pages[i].kind=1
    rpc(STAGE,r);response=rpc(COMMIT);ready=now();assert response['applied']==count
    active=[G.observe(path,(i+1)*PAGE) for i in range(count)]
    active_refs=refs();assert active_refs['vkso_tx_fixture']==1
    release=now();response=rpc(RELEASE);done=now();assert response['applied']==0
    return dict(transaction=tid,start_ns=begin,ready_ns=ready,release_start_ns=release,done_ns=done,
        register_to_ready_ns=ready-begin,release_to_done_ns=done-release,operations=operations,
        active=active,active_refs=active_refs,scope='controlled direct v4 transport; excludes manager identity, file flag and persistence work')

def main():
    OUT.mkdir();os.sched_setaffinity(0,{1})
    record=dict(status='running',scope='1..32-page synthetic scale and accounting observations; private KVM timings',
        kernel=os.uname().release,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        cpu_affinity=sorted(os.sched_getaffinity(0)),clock='CLOCK_MONOTONIC_RAW',rows=[])
    loaded=[];client=None
    def refs(): return {n:int(Path('/sys/module',n,'refcnt').read_text()) for n in ('vkso_tx_fixture','page_cache_replace')}
    try:
        assert os.uname().release=='5.15.0-119-generic' and os.geteuid()==0
        for name,file in [('vkso_tx_fixture','vkso_lz4.ko'),('vkso_kernel_reader','vkso_kernel_reader.ko'),('page_cache_replace','page_cache_replace.ko')]:
            run(['insmod',ROOT/file],OUT/('load-'+name+'.log'));loaded.append(name)
        owner=Path('/sys/module/vkso_tx_fixture');source=int((owner/'sections/.text').read_text(),16)
        version=(owner/'srcversion').read_text().strip();descriptor='vkso_fixture_owner'
        identity=json.loads((ROOT/'image-identities.json').read_text())
        assert identity['owner_module']=='vkso_tx_fixture' and identity['owner_srcversion']==version
        probe=Path('/sys/kernel/debug/vkso_kernel_reader')
        (probe/'page_addresses').write_text(' '.join(hex(source+i*PAGE) for i in range(32)))
        raw=(probe/'pages').read_text();(OUT/'source-pages.csv').write_text(raw)
        pfns={int(x['kernel_vaddr'],0):int(x['pfn']) for x in csv.DictReader(io.StringIO(raw))}
        assert len(pfns)==32 and len(set(pfns.values()))==32
        client=Client();baseline=refs();assert baseline=={'vkso_tx_fixture':0,'page_cache_replace':1}
        record['baseline_refs']=baseline
        # Same guest/CPU calibration; retained as raw launch samples, never subtracted.
        calibration=[]
        for i in range(30):
            before=now();subprocess.run([str(ROOT/'setup-clock'),str(OUT/'clock-events.tsv'),str(os.getpid()),f'calibration-{i}'],check=True)
            after=now();calibration.append(dict(start_ns=before,end_ns=after,elapsed_ns=after-before))
        record['clock_helper_calibration']=calibration
        cases=[(n,condition,route) for n in COUNTS for condition in ('prepared','evicted') for route in ('manager','direct')]
        rng=random.Random(20260912);schedule=[]
        for repeat in range(4):
            order=list(cases);rng.shuffle(order)
            schedule.extend(dict(repeat=repeat,count=n,cache=condition,route=route) for n,condition,route in order)
        record['schedule']=schedule;save(OUT/'status.json',record)
        for index,case in enumerate(schedule):
            out=OUT/f'case-{index:03}';out.mkdir();count=case['count']
            path=out/'carrier.bin';path.write_bytes(b'H'*PAGE+b'Z'*PAGE*count)
            plan=out/'page_mappings.txt';plan.write_text('# file_offset,kernel_vaddr,kind,section\n'+''.join(
                f'{hex((i+1)*PAGE)},{hex(source+i*PAGE)},text,.fixture\n' for i in range(count)))
            (out/'owner_descriptors.txt').write_text(f"{descriptor} {version} vkso_tx_fixture {identity['owner_build_id']}\n")
            (out/'kernel_identity.txt').write_text(f"kernel {identity['kernel_build_id']}\n")
            before=cache_condition(path,count,case['cache'])
            if case['route']=='manager': result=manager_session(path,plan,count,out,refs)
            else: result=direct_session(client,path,count,source,descriptor,version,100000+index,refs)
            assert [x['pfn'] for x in result['active']]==[pfns[source+i*PAGE] for i in range(count)]
            restored=[G.observe(path,(i+1)*PAGE) for i in range(count)]
            assert all(x['original'] and x['pfn']!=pfns[source+i*PAGE] for i,x in enumerate(restored))
            assert refs()==baseline and not (ROOT/'runtime/manager.state').exists()
            # The full manager retires its terminal record before DONE; a
            # direct protocol caller still explicitly owns this final step.
            if case['route']=='manager':
                terminal=client.rpc(QUERY,result['transaction'],expected=-2)
                forgotten=None
            else:
                terminal=client.rpc(QUERY,result['transaction']);assert terminal['state']==4 and terminal['applied']==0
                forgotten=client.rpc(FORGET,result['transaction']);assert forgotten['status']==0
            missing=client.rpc(QUERY,result['transaction'],expected=-2)
            result.update(case,index=index,residency_before=before,restored=restored,terminal=terminal,
                          forget=forgotten,after_forget=missing,refs_after=refs())
            save(out/'result.json',result);record['rows'].append(dict(index=index,**case,result=f'case-{index:03}/result.json'))
            save(OUT/'status.json',record)
        assert len(record['rows'])==96
        record['status']='pass'
    except BaseException:
        record.update(status='fail',error=traceback.format_exc())
    finally:
        if client: client.fd.close()
        # Only unload when no source binding or recovery state remains.
        for name in reversed(loaded):
            try: run(['rmmod',name],OUT/('unload-'+name+'.log'))
            except BaseException: record.setdefault('cleanup_errors',[]).append(traceback.format_exc());record['status']='fail'
        record['modules_after']=Path('/proc/modules').read_text()
        (OUT/'dmesg.txt').write_text(subprocess.check_output(['dmesg'],text=True))
        save(OUT/'status.json',record);os.sync()
    return 0 if record['status']=='pass' else 1
if __name__=='__main__': raise SystemExit(main())
