#!/usr/bin/env python3
"""Detach a serial, dependency-gated diagnostic follow-up, never publication."""
import argparse,copy,hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65';HERE=Path(__file__).resolve().parent
RUNS=(SECTION/'build/squashfs/optimization-runs-01').resolve();OUT=RUNS/'followup-queue-01'

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--detach',action='store_true');a=p.parse_args()
    assert os.geteuid()==0
    if a.detach:
        assert not OUT.exists() and not (RUNS/'followup-queue-01-launch.json').exists()
        with (RUNS/'followup-queue-01.log').open('x') as log:
            child=subprocess.Popen([sys.executable,str(Path(__file__).resolve())],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(RUNS/'followup-queue-01-launch.json',dict(pid=child.pid,created=time.time(),scope='Waits for completed confirmation and numeric analysis; serial diagnostics only, no paper updates.'))
        print('detached follow-up waiter',child.pid);return
    OUT.mkdir();state=dict(status='waiting',pid=os.getpid(),started=time.time(),jobs=[])
    frozen={str(HERE/name):sha(HERE/name) for name in ['FOLLOWUP_PROTOCOL.md','followup_queue.py','component_ledger.py','fuse_memory_diagnostic.py','fuse_memory_probe.inc','bittree_diagnostic.py','bittree_unrolled.inc','validate_dictionary.py','bench.c']}
    save(OUT/'source-registration.json',dict(created=time.time(),identities=frozen,scope='New finite diagnostic protocol, separate from unchanged main confirmation.'))
    def write():save(OUT/'result.json',state)
    write()
    try:
        while True:
            prior=read(RUNS/'formal-recovery-queue-01/result.json');post=read(RUNS/'postprocess-02/result.json')
            assert prior['status'] in ['running','complete'],prior.get('error',prior['status'])
            assert post['status'] in ['waiting','running','complete'],post.get('error',post['status'])
            if prior['status']==post['status']=='complete':break
            if prior['status']=='running':
                assert b'campaign_queue.py' in Path('/proc',str(prior['pid']),'cmdline').read_bytes()
            time.sleep(5)
        for path,digest in frozen.items():assert sha(Path(path))==digest,('follow-up source changed while waiting',path)
        registered=read(HERE/'confirmation-registration.json')
        for path,digest in registered['identities'].items():assert sha(Path(path))==digest,('frozen production input changed',path)
        assert not {'vkso_sq_core','vkso_squashfs','page_cache_replace','vkso_kernel_reader'}.intersection(l.split()[0] for l in Path('/proc/modules').read_text().splitlines())
        state.update(status='running',execution_started=time.time());write()
        def run(name,argv):
            argv=list(map(str,argv));row=dict(name=name,status='running',started=time.time(),argv=argv);state['jobs'].append(row);write()
            with (OUT/(name+'.log')).open('w') as log:
                child=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT);row['pid']=child.pid;write()
                row['returncode']=child.wait()
            assert row['returncode']==0,(name,row['returncode'])
            row.update(status='complete',finished=time.time());write();print('complete',name,flush=True)
        ordinary=['runuser','-u','zzk','--','python3']
        run('component-ledger',[*ordinary,HERE/'component_ledger.py','--output',RUNS/'component-ledger-01'])
        run('fuse-live-memory',[*ordinary,HERE/'fuse_memory_diagnostic.py','--output',RUNS/'fuse-memory-diagnostic-01'])
        run('bittree-candidate',[*ordinary,HERE/'bittree_diagnostic.py','--output',RUNS/'bittree-diagnostic-01'])
        base=next(j for j in read(HERE/'formal-queue.json') if j['name']=='squash-optimized-heldout-xz-01')
        jobs=[];variants=['stock','copied-library','copied-retained','copied','vkso']
        for index in range(1,4):
            job=copy.deepcopy(base);name=f'python-decoder-attribution-{index:02d}';job.update(name=name,kind='python-decoder-attribution',result=str(RUNS/name/'result.json'))
            args=job['argv']
            for flag,value in [('--campaign',name),('--output',str(RUNS/name)),('--analysis-group','python-decoder-attribution'),('--seed',str(68300+index))]:
                args[args.index(flag)+1]=value
            start=args.index('--variant-set')+1;end=start
            while end<len(args) and not args[end].startswith('--'):end+=1
            args[start:end]=variants
            args+=['--extra-readers',str(HERE/'decoder-readers.json'),'--equal-loader-paths']
            assert not Path(job['result']).parent.exists();jobs.append(job)
        queue=OUT/'python-attribution-queue.json';save(queue,jobs)
        save(OUT/'python-attribution-registration.json',dict(created=time.time(),queue_sha256=sha(queue),campaigns=3,blocks=8,variants=variants,observations=120,
            production_registration=str(HERE/'confirmation-registration.json'),production_registration_sha256=sha(HERE/'confirmation-registration.json'),
            hypotheses=['Library/common-retained decoder choice','Common-retained/common unused dependencies','Copied/shared physical backing'],scope='Fixed original Python XZ SIF and full compile; no new input selection, no significance stopping.'))
        run('python-attribution',['python3',SECTION/'squashfs/campaign_queue.py','--queue',queue,'--output',RUNS/'python-attribution-queue-01'])
        # The queue metadata is root-owned but readable; all analysis outputs
        # are ordinary-user files in the task-owned RUNS directory.
        run('python-attribution-analysis',[*ordinary,HERE/'analyze.py','--queue',queue,'--output',RUNS/'python-attribution-analysis-01'])
        data=read(RUNS/'python-attribution-analysis-01/analysis.json');assert data['observations']==120 and len(data['inputs'])==3
        state.update(status='complete',finished=time.time(),scope='Additional attribution/diagnostic evidence only. No candidate promotion, publication or final-delivery claim.')
    except BaseException:
        state.update(status='failed',error=traceback.format_exc(),finished=time.time())
        if state['jobs'] and state['jobs'][-1]['status']=='running':state['jobs'][-1]['status']='failed'
        raise
    finally:write()

if __name__=='__main__':main()
