#!/usr/bin/env python3
"""Restore the recorded interrupted owner, then detach the remaining serial queues."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[4]
RAW=ROOT/'test/evaluation-local/runs/iso9660'
HERE=Path(__file__).resolve().parent

def main():
    assert os.geteuid()==0
    out=RAW/'squash-refine-interruption-recovery-01';record=json.loads((out/'interruption.json').read_text())
    assert not (out/'recovery.json').exists()
    carrier=RAW/record['interrupted_campaign']/'carrier'
    manager=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029/manager'
    steps=[[str(manager),'restore',str(carrier/'libvkso_sq_core.so'),str(carrier/'page_mappings.txt')]]
    steps += [['rmmod',name] for name in ['page_cache_replace','vkso_kernel_reader','vkso_squashfs','vkso_sq_core']]
    result=dict(status='running',steps=[],queues=[])
    def save():(out/'recovery.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    for index,argv in enumerate(steps):
        with (out/f'cleanup-{index}.log').open('w') as log:r=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
        result['steps'].append(dict(argv=argv,returncode=r.returncode));save();assert r.returncode==0
    assert not any(line.split()[0] in ['page_cache_replace','vkso_kernel_reader','vkso_squashfs','vkso_sq_core'] for line in Path('/proc/modules').read_text().splitlines())
    runner=ROOT/'test/section65/squashfs/campaign_queue.py'
    previous=None
    for name,queue in [('squash-refine-formal-recovery-01','formal-recovery-queue.json'),
                       ('squash-refine-resource-queue-02','resource-queue.json'),
                       ('squash-refine-postprocess-queue-02','postprocess-queue.json')]:
        argv=['python3',str(runner),'--queue',str(HERE/queue),'--output',str(RAW/name)]
        if previous:argv+=['--after',str(previous)]
        with (out/(name+'.log')).open('w') as log:
            child=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        result['queues'].append(dict(name=name,pid=child.pid,argv=argv));save()
        previous=RAW/name/'result.json'
        for _ in range(100):
            if previous.exists():break
            assert child.poll() is None
            time.sleep(.1)
        assert previous.exists()
    result['status']='complete';save();print('Restored and unloaded interrupted owner; detached three serial dependent queues.')

if __name__=='__main__':main()
