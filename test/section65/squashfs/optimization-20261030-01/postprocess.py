#!/usr/bin/env python3
"""Wait for successful serial confirmation, then analyze only new outputs."""
import argparse,json,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65';HERE=Path(__file__).resolve().parent
RUNS=(SECTION/'build/squashfs/optimization-runs-01').resolve()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--detach',action='store_true');a=p.parse_args()
    out=RUNS/'postprocess-02'
    if a.detach:
        assert not out.exists() and not (RUNS/'postprocess-02-launch.json').exists()
        with (RUNS/'postprocess-02.log').open('x') as log:
            child=subprocess.Popen([sys.executable,str(Path(__file__).resolve())],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        (RUNS/'postprocess-02-launch.json').write_text(json.dumps(dict(pid=child.pid,started=time.time(),scope='Wait for successful recovered confirmation before non-timing analysis.'),indent=2)+'\n')
        print('detached postprocessing waiter',child.pid);return
    out.mkdir();state=dict(status='waiting',started=time.time(),jobs=[])
    def save():(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    save()
    try:
        while True:
            previous=json.loads((RUNS/'formal-recovery-queue-01/result.json').read_text())
            if previous['status']=='complete':break
            assert previous['status']=='running',previous.get('error',previous['status'])
            assert b'campaign_queue.py' in Path('/proc',str(previous['pid']),'cmdline').read_bytes(), 'formal queue is no longer live'
            time.sleep(5)
        state['status']='running';save()
        analysis=RUNS/'analysis-final-01';build=SECTION/'build/squashfs/optimization-cache-01'
        queue=RUNS/'confirmation-recovery-01/selected-queue.json'
        commands=[
            ('analysis','analyze.py',['--queue',queue,'--output',analysis]),
            ('independent-audit','audit.py',['--queue',queue,'--registration',RUNS/'confirmation-recovery-01/selected-registration.json','--analysis',analysis/'analysis.json','--output',analysis/'audit.json']),
            ('source-costs','cost_ledger.py',['--build',build,'--source-dir',build/'xz-user-source','--output',analysis/'costs.json']),
            ('reuse-audit','reuse_audit.py',['--build',build,'--ledger',analysis/'costs.json','--output',analysis/'reuse-audit']),
            ('resource-ledger','resources.py',['--queue',queue,'--resource-queue',HERE/'resource-queue.json','--minimal',RUNS/'minimal-deployment-01/result.json','--output',analysis/'resource-ledger'])]
        for name,script,args in commands:
            row=dict(name=name,status='running',started=time.time());state['jobs'].append(row);save()
            with (out/(name+'.log')).open('w') as log:
                subprocess.run([sys.executable,str(HERE/script),*map(str,args)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)
            row.update(status='complete',finished=time.time());save();print('complete',name,flush=True)
        state.update(status='complete',finished=time.time(),scope='Numerical analysis/audit/component ledgers only. User requested continued experimental diagnosis, not publication. No section prose, claim verdicts, paper/docs, PDF or final-delivery freeze updated.')
    except BaseException:
        state.update(status='failed',error=traceback.format_exc(),finished=time.time())
        if state['jobs']:state['jobs'][-1]['status']='failed'
        raise
    finally:save()
if __name__=='__main__':main()
