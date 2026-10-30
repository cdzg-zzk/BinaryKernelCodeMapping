#!/usr/bin/env python3
"""Create a fresh output namespace while preserving the registered protocol and seeds."""
import argparse
import json
from pathlib import Path
import re

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue',type=Path,required=True)
    p.add_argument('--tag',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9-]+',a.tag)
    assert not a.output.exists()
    jobs=json.loads(a.queue.read_text())
    for job in jobs:
        assert Path(job['result']).name=='result.json', 'Clone experiment queues, not dependent analysis pipelines'
        old=job['name'];new=old+'-'+a.tag;job['name']=new
        args=job['argv']
        for option in ['--output','--campaign']:
            if option in args:
                i=args.index(option)+1
                args[i]=str(Path(args[i]).with_name(new)) if option=='--output' else new
        old_result=Path(job['result']);job['result']=str(old_result.parent.with_name(new)/old_result.name)
        assert not Path(job['result']).exists()
    a.output.write_text(json.dumps(jobs,indent=2)+'\n')
    print('cloned',len(jobs),'jobs with unchanged seeds and inputs')

if __name__=='__main__':main()
