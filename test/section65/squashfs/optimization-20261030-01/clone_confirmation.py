#!/usr/bin/env python3
"""Clone the fixed confirmation with new run names and matching registration."""
import argparse,hashlib,json,re,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert re.fullmatch(r'[A-Za-z0-9-]+',a.tag)
    queue=HERE/'formal-queue.json';registered=HERE/'confirmation-registration.json'
    jobs=json.loads(queue.read_text());record=json.loads(registered.read_text())
    assert sha(queue)==record['queue_sha256'] and len(jobs)==30
    for name,digest in record['identities'].items():assert sha(Path(name))==digest,('changed frozen input',name)
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    names={}
    for job in jobs:
        old=job['name'];name=old+'-'+a.tag;names[old]=name;job['name']=name
        args=job['argv'];newrun=out/name
        args[args.index('--campaign')+1]=name;args[args.index('--output')+1]=str(newrun)
        job['result']=str(newrun/'result.json')
    for planned in record['expected_campaigns']:planned['name']=names[planned['name']]
    q=out/'queue.json';q.write_text(json.dumps(jobs,indent=2)+'\n')
    record.update(queue_sha256=sha(q),rerun_of=str(registered),rerun_registration_time=time.time(),
        rerun_scope='Same frozen binaries/runners/inputs/block counts/seeds; only campaign names and output paths change. Separate analysis, never pooled automatically.')
    (out/'registration.json').write_text(json.dumps(record,indent=2)+'\n')
    print('prepared only; launch serial campaign_queue.py with',q,'and a new queue-log output')
if __name__=='__main__':main()
