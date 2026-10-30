#!/usr/bin/env python3
"""Read-only compact status for this optimization's explicit run namespace."""
import json,sys
from pathlib import Path
RUNS=Path('/home/zzk/BinaryKernelCodeMapping/test/section65/build/squashfs/optimization-runs-01').resolve()

for queue in sorted(RUNS.glob('*queue-*/result.json')):
    r=json.loads(queue.read_text())
    if '--formal' in sys.argv and not queue.parent.name.startswith('formal-'):continue
    recovered=queue.parent.name=='formal-queue-01' and (RUNS/'confirmation-recovery-01/recovery.json').exists()
    if '--compact' in sys.argv:
        completed=sum(j['status']=='complete' for j in r['jobs'])
        live=Path('/proc',str(r.get('pid',0)),'cmdline')
        alive=live.exists() and b'campaign_queue.py' in live.read_bytes()
        print(queue.parent.name,'interrupted-stale' if recovered else r['status'],'completed',completed,'pid',r.get('pid'),'alive',alive)
    else:
        print(queue.parent.name,'interrupted (stale state retained; see confirmation-recovery-01)' if recovered else r['status'],[(j['name'],j['status']) for j in r['jobs']])
    for job in r['jobs']:
        if job['status']=='running' and not recovered:
            for p in [RUNS/job['name']/'samples.jsonl',RUNS/job['name']/'benchmark/samples.jsonl']:
                if p.exists():print('current observations',job['name'],len(p.read_text().splitlines()))
    if r.get('error'):print(r['error'])
if '--formal' in sys.argv:
    for folder in ['postprocess-02','followup-queue-01']:
        path=RUNS/folder/'result.json'
        if path.exists():
            state=json.loads(path.read_text());print(folder,state['status'],[(j['name'],j['status']) for j in state['jobs']])
            if state.get('error'):print(state['error'])
    raise SystemExit(0)
for path in sorted(RUNS.glob('resource-scale-*/benchmark/resources.json')):
    r=json.loads(path.read_text())
    print(path.parents[1].name,{v:dict(entries=x['entries'],retained_pss_kib=x['after']['helper']['memory']['Pss'],
        private_kib=x['after']['helper']['memory']['Private_Clean']+x['after']['helper']['memory']['Private_Dirty'],
        highwater_rss_kib=x['after']['helper']['memory'].get('VmHWM')) for v,x in r.items()})
for name in ['shared-decoder-01','native-calls-01','minimal-deployment-01','hardening-01']:
    p=RUNS/name/'result.json'
    if p.exists():
        r=json.loads(p.read_text());print(name,r.get('status'),{k:v for k,v in r.items() if k in ['observations','error','restored','modules_unloaded']})
