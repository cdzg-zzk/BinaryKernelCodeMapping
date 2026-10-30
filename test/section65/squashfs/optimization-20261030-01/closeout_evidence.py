#!/usr/bin/env python3
"""Index existing correctness and final cleanup evidence; no new workload."""
import hashlib,json,time
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping')
B=ROOT/'test/section65/build/squashfs'
R=Path('/var/tmp/vkso-section65-optimization-20261030-hBcg9Y')
O=R/'budget-closeout-01'
def main():
    records=[]
    paths=[B/n/'result.json' for n in ['optimization-xz-valid-01','optimization-cache-valid-01','optimization-cache-fuse-01','optimization-cache-guest-01']]
    paths+=[B/'optimization-cache-sanitize-01/sanitizer.json']
    paths += [R/n/'result.json' for n in ['functional-01','simultaneous-01','shared-decoder-01','minimal-deployment-01','native-controls-guest-01','validation-queue-01','cache-scale-direct-01','hardening-01','native-calls-01','metadata-work-01']]
    for p in paths:
        assert p.exists(),str(p)
        data=json.loads(p.read_text())
        expected='pass' if p.parent.name=='optimization-xz-valid-01' else 'complete'
        assert data['status']==expected,(str(p),data['status'])
        compact={k:v for k,v in data.items() if not isinstance(v,(dict,list))}
        for k,v in data.items():
            if isinstance(v,list):compact[k+'_count']=len(v)
        records.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),summary=compact))
    alive=[]
    for pid in [2129032,2141744,2187427,2244341]:
        p=Path('/proc',str(pid),'stat')
        if p.exists() and p.read_text().split(') ',1)[1][0]!='Z':alive.append(pid)
    assert not alive
    names={'vkso_sq_core','vkso_squashfs','page_cache_replace','vkso_kernel_reader'}
    module_lines=[l for l in Path('/proc/modules').read_text().splitlines() if l.split()[0] in names]
    assert not module_lines
    mount_lines=[l for l in Path('/proc/self/mountinfo').read_text().splitlines() if str(R) in l or '/optimization-runs-01/' in l]
    assert not mount_lines
    result=dict(status='complete',time=time.time(),existing_correctness=records,live_queue_or_current_campaign_pids=alive,loaded_task_modules=module_lines,task_mounts_in_observer_namespace=mount_lines,scope='Existing tests indexed, not rerun; current queue cleanup plus final process/module checks. No unrelated mount or process was modified.')
    with (O/'correctness-and-cleanup.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
