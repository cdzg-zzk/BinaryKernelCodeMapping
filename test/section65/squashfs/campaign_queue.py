#!/usr/bin/env python3
"""Run an explicit, serial campaign queue; preserve logs and stop on failure."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import traceback


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--after',type=Path,help='wait for this live queue to finish successfully')
    a=p.parse_args()
    assert os.geteuid()==0
    jobs=json.loads(a.queue.read_text())
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    state=dict(status='running',pid=os.getpid(),started=time.time(),queue=jobs,jobs=[])
    write=lambda:(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    write()
    try:
        if a.after:
            state['waiting_for']=str(a.after.resolve());write()
            while True:
                prior=json.loads(a.after.read_text())
                if prior['status']=='complete':break
                assert prior['status']=='running',prior
                cmdline=Path('/proc',str(prior['pid']),'cmdline').read_bytes()
                assert b'campaign_queue.py' in cmdline, 'prerequisite queue is no longer live'
                time.sleep(5)
            state.pop('waiting_for');write()
        for job in jobs:
            assert not Path(job['result']).exists(), ('existing run',job['result'])
            row=dict(name=job['name'],started=time.time(),status='running')
            state['jobs'].append(row);write()
            with (out/(job['name']+'.log')).open('w') as log:
                child=subprocess.Popen(job['argv'],stdout=log,stderr=subprocess.STDOUT)
                row['pid']=child.pid;write()
                row['returncode']=child.wait()
            row['finished']=time.time()
            if row['returncode']:
                raise RuntimeError(f"Job {job['name']} exited {row['returncode']}; see {out/(job['name']+'.log')}")
            result=json.loads(Path(job['result']).read_text())
            assert row['returncode']==0 and result['status']=='complete', (row,result)
            row['status']='complete';write();print('complete',job['name'],flush=True)
        state.update(status='complete',finished=time.time())
    except BaseException:
        state.update(status='failed',error=traceback.format_exc(),finished=time.time())
        if state['jobs']:state['jobs'][-1]['status']='failed'
        raise
    finally:write()


if __name__=='__main__':main()
