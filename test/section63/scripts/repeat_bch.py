#!/usr/bin/env python3
"""Nine additional complete BCH deployments, reusing the exact formal binaries."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import campaign

HERE=Path(__file__).resolve().parents[1]
def prepare(base):
    out=base/'repeat-bch';out.mkdir(exist_ok=False)
    for name in ('builds','owners'):(out/name).symlink_to(Path('..')/name,target_is_directory=True)
    entries=[]
    for n in range(3,12):
        d=out/f'deployment-{n:02d}-bch';d.mkdir()
        shutil.copytree(base/'deployment-00-bch/prepared',d/'prepared')
        entries.append(dict(algorithm='bch',directory=str(d),manifest=None))
    campaign.save(out/'plan.json',dict(status='prepared',kernel='5.15.0-119-generic',cpu=2,
        entries=entries,additional_loads=9,original_loads=3,user_rounds={'bch':11},kernel_rounds=11,
        reason='repeat all BCH workloads after observed instability in the original-source Matched control',
        collection='same owner, reference, driver, user DSOs, input generation and measurement binaries as original campaign; no rebuild',
        inclusion='all nine completed deployments, no rejection based on measured speed',
        started_utc=dt.datetime.now(dt.timezone.utc).isoformat()))
    source=out/'collection-tools';source.mkdir()
    for name in ('repeat_bch.py','campaign.py','collect_user.py'):shutil.copy2(HERE/'scripts'/name,source/name)
    print('Prepared nine BCH deployments with retained binaries.',flush=True)

def merge(base):
    extra=campaign.json.loads((base/'repeat-bch/plan.json').read_text())
    assert campaign.json.loads((base/'repeat-bch/complete.json').read_text())['status']=='pass'
    assert len(extra['entries'])==9
    assert all(campaign.json.loads((Path(e['directory'])/'complete.json').read_text())['status']=='pass' for e in extra['entries'])
    path=base/'plan.json';plan=campaign.json.loads(path.read_text())
    if len(plan['entries'])==18:
        assert plan['entries'][-9:]==extra['entries']
        return
    assert len(plan['entries'])==9
    archive=base/'repeat-bch/original-three-load';archive.mkdir(exist_ok=True)
    for name in ('plan.json','complete.json','report.md'):
        if (base/name).exists() and not (archive/name).exists():shutil.copy2(base/name,archive/name)
    for name in ('analysis','paper-material'):
        if (base/name).exists() and not (archive/name).exists():shutil.copytree(base/name,archive/name)
    plan.update(entries=plan['entries']+extra['entries'],repetition_count={'bch':12,'lz4':3,'xz':3},followup='repeat-bch/plan.json')
    campaign.save(path,plan)
    campaign.save(base/'complete.json',dict(status='pass',deployments=18,repetition_count=plan['repetition_count']))
    print('Merged the nine additional BCH deployments without discarding original samples.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','collect','merge'));p.add_argument('directory',type=Path);a=p.parse_args();base=a.directory.resolve()
    if a.action=='prepare':prepare(base)
    elif a.action=='collect':campaign.collect(base/'repeat-bch')
    else:merge(base)
