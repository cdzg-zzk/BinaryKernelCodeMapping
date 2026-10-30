#!/usr/bin/env python3
"""Create fresh serial replay manifests without overwriting any retained run."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    assert re.fullmatch(r'[a-z0-9][a-z0-9-]*',a.tag)
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    files=['final-precheck-queue.json','formal-queue.json','post-formal-queue.json','memory-diagnostic-queue.json','bounded-control-queue.json','native-stream-queue.json','analysis-queue.json','analysis-execution-queue.json','xz-attribution-analysis-queue.json','xz-attribution-queue.json','loader-analysis-queue.json','loader-queue.json','loader-analysis-execution-queue.json','singlecpu-analysis-queue.json','singlecpu-queue.json','singlecpu-analysis-execution-queue.json']
    originals={n:json.loads((HERE/n).read_text()) for n in files};replacements={}
    for jobs in originals.values():
        for job in jobs:
            old=job['name'];replacements.setdefault(old,old+'-'+a.tag)
    analysis_before='test/section65/build/squashfs/improvement-analysis-01';analysis_after='test/section65/build/squashfs/improvement-analysis-'+a.tag
    assert not (ROOT/analysis_after).exists()
    xz_before='test/section65/build/squashfs/improvement-xz-attribution-analysis-01';xz_after='test/section65/build/squashfs/improvement-xz-attribution-analysis-'+a.tag
    assert not (ROOT/xz_after).exists()
    loader_before='test/section65/build/squashfs/improvement-loader-analysis-01';loader_after='test/section65/build/squashfs/improvement-loader-analysis-'+a.tag
    assert not (ROOT/loader_after).exists()
    single_before='test/section65/build/squashfs/improvement-singlecpu-analysis-01';single_after='test/section65/build/squashfs/improvement-singlecpu-analysis-'+a.tag
    assert not (ROOT/single_after).exists()
    def rewrite(value):
        if isinstance(value,list):return [rewrite(v) for v in value]
        if isinstance(value,dict):return {k:rewrite(v) for k,v in value.items()}
        if not isinstance(value,str):return value
        value=value.replace(analysis_before,analysis_after).replace(xz_before,xz_after).replace(loader_before,loader_after).replace(single_before,single_after)
        for name in files:
            value=value.replace('test/section65/squashfs/improvement/'+name,str(out/name))
        # Longest first prevents a short analysis job name rewriting the output directory.
        for old,new in sorted(replacements.items(),key=lambda pair:-len(pair[0])):
            if value==old:value=new;break
            prefix='test/evaluation-local/runs/iso9660/'+old
            if value.startswith(prefix+'/'):value=prefix.rsplit('/',1)[0]+'/'+new+value[len(prefix):];break
            if value==prefix:value=prefix.rsplit('/',1)[0]+'/'+new;break
        return value
    rewritten={n:rewrite(v) for n,v in originals.items()}
    combined=[]
    for name,jobs in rewritten.items():
        (out/name).write_text(json.dumps(jobs,indent=2)+'\n')
        if name not in ['analysis-queue.json','xz-attribution-analysis-queue.json','loader-analysis-queue.json','singlecpu-analysis-queue.json']:combined+=jobs
    results=[j['result'] for j in combined];assert len(set(results))==len(results)
    assert all(not (ROOT/Path(p)).exists() for p in results)
    (out/'serial-queue.json').write_text(json.dumps(combined,indent=2)+'\n')
    (out/'replay.json').write_text(json.dumps(dict(status='prepared-not-executed',tag=a.tag,queue=str(out/'serial-queue.json'),
        prerequistes='Existing frozen implementation, stock/LKL/Apptainer assets, native fixtures and original maintenance-reference builds; matching owned Linux 5.15.198 host. No host boot/config change.',
        command=['sudo','python3',str(HERE.parent/'campaign_queue.py'),'--queue',str(out/'serial-queue.json'),'--output',str(ROOT/'test/evaluation-local/runs/iso9660'/('improvement-replay-'+a.tag))]),indent=2)+'\n')
    print(out/'replay.json')
if __name__=='__main__':main()
