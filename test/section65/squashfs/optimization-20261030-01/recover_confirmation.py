#!/usr/bin/env python3
"""One-shot, explicitly scoped recovery of the interrupted optimized XZ campaign."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path('/home/zzk/BinaryKernelCodeMapping')
HERE=ROOT/'test/section65/squashfs/optimization-20261030-01'
RUNS=Path('/var/tmp/vkso-section65-optimization-20261030-hBcg9Y')
OLD='squash-optimized-application-final-xz-01'
NEW=OLD+'-recovery01'
OUT=RUNS/'confirmation-recovery-01'
BOOT='4d29e579-2621-4df3-97a2-8d359ed1f5ea'
MODULES=['page_cache_replace','vkso_kernel_reader','vkso_squashfs','vkso_sq_core']

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')

def main():
    assert os.geteuid()==0
    assert not OUT.exists() and not (RUNS/NEW).exists()
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert not Path('/proc/2077515').exists(), 'old queue PID exists; inspect before recovery'
    queue=HERE/'formal-queue.json';registration=HERE/'confirmation-registration.json'
    jobs=read(queue);original=read(registration)
    assert len(jobs)==30 and sha(queue)==original['queue_sha256']
    for path,digest in original['identities'].items():
        assert sha(Path(path))==digest,('changed frozen identity',path)
    assert jobs[3]['name']==OLD
    for job in jobs[:3]:
        state=read(Path(job['result']))
        assert state['status']=='complete' and state['modules_unloaded']
    for job in jobs[4:]:assert not Path(job['result']).parent.exists(),job['name']
    partial=RUNS/OLD/'benchmark/samples.jsonl'
    assert len(partial.read_text().splitlines())==127
    assert read(RUNS/OLD/'result.json')['status']=='running'
    assert read(RUNS/OLD/'benchmark/environment.json')['boot_id']==BOOT
    processes=subprocess.check_output(['ps','-eo','pid,args'],text=True)
    for line in processes.splitlines():
        assert not (str(RUNS) in line and any(x in line for x in ['campaign_queue.py','apptainer_shared.py','native_compare.py','apptainer_bench.py'])),line
    mounts=subprocess.check_output(['findmnt','-rn','-o','TARGET,SOURCE,FSTYPE'],text=True)
    assert str(RUNS) not in mounts and 'vksosquash' not in mounts
    before=Path('/proc/modules').read_text()
    assert set(MODULES).issubset({l.split()[0] for l in before.splitlines()})
    stages=[json.loads(l) for l in (RUNS/OLD/'stages.jsonl').read_text().splitlines()]
    registered=[s for s in stages if s['stage']=='register'];assert len(registered)==1
    carrier=RUNS/OLD/'carrier'
    manager=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029/manager'
    replace=[str(manager),'replace',str(carrier/'libvkso_sq_core.so'),str(carrier/'page_mappings.txt')]
    assert registered[0]['argv']==replace and registered[0]['returncode']==0
    assert not any(s['stage'].startswith('restore') for s in stages)
    selected=copy.deepcopy(jobs);replacement=selected[3]
    replacement['name']=NEW
    replacement['argv'][replacement['argv'].index('--campaign')+1]=NEW
    replacement['argv'][replacement['argv'].index('--output')+1]=str(RUNS/NEW)
    replacement['result']=str(RUNS/NEW/'result.json')
    # Only identity/output names change. Workloads, random seed and full block
    # count are copied mechanically; no partial observations are reused.
    normalized=copy.deepcopy(replacement)
    normalized['name']=OLD;normalized['result']=jobs[3]['result']
    for flag in ['--campaign','--output']:
        normalized['argv'][normalized['argv'].index(flag)+1]=jobs[3]['argv'][jobs[3]['argv'].index(flag)+1]
    assert normalized==jobs[3]
    OUT.mkdir()
    interruption=dict(status='interrupted',interrupted_campaign=OLD,replacement_campaign=NEW,
        partial_samples=str(partial),partial_samples_sha256=sha(partial),partial_observations=127,
        boot_id=BOOT,recorded=time.time(),original_queue=str(queue),original_queue_sha256=sha(queue),
        original_registration=str(registration),original_registration_sha256=sha(registration),
        observed_cause='Tool exec-server transport disconnected; old SSH/queue and experiment processes absent. Same host boot. Exact termination cause unproven.',
        policy='Keep all three completed campaigns. Replace the entire interrupted campaign with identical settings in a new directory; exclude all 127 partial observations, never filter completed campaigns.',
        untouched_evidence={str(p):sha(p) for p in [partial,RUNS/OLD/'result.json',RUNS/OLD/'benchmark/result.json',RUNS/OLD/'stages.jsonl',RUNS/'formal-queue-01/result.json']})
    write(OUT/'interruption.json',interruption)
    (OUT/'processes-before.txt').write_text(processes)
    (OUT/'mounts-before.txt').write_text(mounts)
    (OUT/'modules-before.txt').write_text(before)
    write(OUT/'selected-queue.json',selected);write(OUT/'remaining-queue.json',selected[3:])
    updated=copy.deepcopy(original)
    updated['expected_campaigns'][3]['name']=NEW
    updated.update(queue_sha256=sha(OUT/'selected-queue.json'),recovery_time=time.time(),
        original_registration=str(registration),original_registration_sha256=sha(registration),
        recovery_manifest=str(OUT/'interruption.json'),recovery_manifest_sha256=sha(OUT/'interruption.json'))
    write(OUT/'selected-registration.json',updated)
    state=dict(status='recovering',steps=[],started=time.time())
    def save():write(OUT/'recovery.json',state)
    save()
    restore=replace.copy();restore[1]='restore'
    for index,argv in enumerate([restore]+[['rmmod',m] for m in MODULES]):
        with (OUT/f'cleanup-{index}.log').open('w') as log:
            result=subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        state['steps'].append(dict(argv=argv,returncode=result.returncode));save()
        assert result.returncode==0,('cleanup failed; inspect, do not blindly retry',argv)
    after=Path('/proc/modules').read_text();(OUT/'modules-after.txt').write_text(after)
    assert not set(MODULES).intersection(l.split()[0] for l in after.splitlines())
    state['restored']=True;state['modules_unloaded']=True;save()
    runner=ROOT/'test/section65/squashfs/campaign_queue.py'
    argv=['python3',str(runner),'--queue',str(OUT/'remaining-queue.json'),'--output',str(RUNS/'formal-recovery-queue-01')]
    with (OUT/'queue.log').open('w') as log:
        child=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    state.update(queue_pid=child.pid,queue_argv=argv,launch='new Linux session, stdin /dev/null, persistent file stdout/stderr');save()
    for _ in range(50):
        assert child.poll() is None,'queue exited; inspect saved logs before retry'
        if (RUNS/'formal-recovery-queue-01/result.json').exists():break
        time.sleep(.1)
    assert (RUNS/'formal-recovery-queue-01/result.json').exists()
    state.update(status='complete',finished=time.time(),scope='Registration restored, modules unloaded, remaining serial queue launched; experiment completion is NOT yet claimed.');save()
    print(json.dumps(dict(cleanup='complete',queue_pid=child.pid,retained_completed=3,remaining_campaigns=27,partial_retained_excluded=127)))

if __name__=='__main__':main()
