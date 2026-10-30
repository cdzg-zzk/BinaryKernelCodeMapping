#!/usr/bin/env python3
"""Budget closeout: stop this queue dispatcher, let its current child finish."""
import argparse,json,os,signal,time
from pathlib import Path
R=Path('/var/tmp/vkso-section65-optimization-20261030-hBcg9Y')
O=R/'budget-closeout-01'
def read(p):return json.loads(p.read_text())
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def command(pid):return Path('/proc',str(pid),'cmdline').read_bytes().replace(b'\0',b' ').decode()
def children(pid):return Path('/proc',str(pid),'task',str(pid),'children').read_text().split()
def alive(pid):
    p=Path('/proc',str(pid),'stat')
    return p.exists() and p.read_text().split(') ',1)[1][0]!='Z'
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['arm','finish']);a=p.parse_args()
    assert os.geteuid()==0
    if a.action=='arm':
        assert not O.exists();O.mkdir();os.chown(O,1000,1000)
        q=read(R/'formal-recovery-queue-01/result.json');pid=q['pid']
        assert pid==2129032 and q['status']=='running'
        assert 'campaign_queue.py' in command(pid) and str(R/'confirmation-recovery-01/remaining-queue.json') in command(pid)
        # STOP only the dispatcher, not the process group or active campaign.
        os.kill(pid,signal.SIGSTOP)
        q=read(R/'formal-recovery-queue-01/result.json')
        active=[j for j in q['jobs'] if j['status']=='running'];assert len(active)==1
        child=active[0]['pid'];assert str(child) in children(pid)
        save(O/'dispatcher-snapshot.json',q)
        state=dict(status='draining-current-campaign',created=time.time(),dispatcher_pid=pid,active=active[0],cancelled_waiters=[],reason='User requested quota-conserving core closeout. Selection is chronological completion, not measured effect.')
        for name,wp,marker in [('followup-queue-01',2187427,'followup_queue.py'),('postprocess-02',2141744,'postprocess.py')]:
            s=read(R/name/'result.json');assert s['status']=='waiting' and not s['jobs']
            assert marker in command(wp) and not children(wp)
            save(O/(name+'-snapshot.json'),s)
            os.kill(wp,signal.SIGTERM)
            state['cancelled_waiters'].append(dict(name=name,pid=wp,signal='TERM',jobs_started=0))
        save(O/'control.json',state);print(json.dumps(state),flush=True)
    else:
        state=read(O/'control.json');pid=state['dispatcher_pid'];active=state['active']
        job=next(j for j in read(O/'dispatcher-snapshot.json')['queue'] if j['name']==active['name'])
        result=read(Path(job['result']))
        assert result['status']=='complete' and result['modules_unloaded'] and result['restored'],result.get('status')
        assert not alive(active['pid']),'current campaign still active; wait, do not kill'
        assert 'campaign_queue.py' in command(pid)
        assert Path('/proc',str(pid),'stat').read_text().split(') ',1)[1][0]=='T'
        # The completed child has already restored mappings and unloaded modules.
        # TERM is pending before CONT, so no next campaign is dispatched.
        os.kill(pid,signal.SIGTERM);os.kill(pid,signal.SIGCONT)
        time.sleep(.2)
        assert not alive(pid)
        assert all(not alive(w['pid']) for w in state['cancelled_waiters'])
        task_modules={'vkso_sq_core','vkso_squashfs','page_cache_replace','vkso_kernel_reader'}
        assert not task_modules.intersection(l.split()[0] for l in Path('/proc/modules').read_text().splitlines())
        state.update(status='stopped-at-complete-campaign-boundary',finished=time.time(),active_result=job['result'],task_modules_unloaded=True,background_tasks_alive=False,scope='Original queue status files preserved as interrupted/stale; this sidecar is the authoritative budget cancellation record. No samples deleted or modified.')
        save(O/'stopped.json',state);print(json.dumps(state),flush=True)
if __name__=='__main__':main()
