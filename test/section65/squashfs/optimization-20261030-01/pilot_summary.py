#!/usr/bin/env python3
"""Descriptive pilot contrasts only; no campaign CI or formal acceptance claim."""
import argparse, hashlib, json, math, statistics
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--queue',type=Path,required=True)
    p.add_argument('--output',type=Path);p.add_argument('--brief',action='store_true');a=p.parse_args();results=[];inputs=[]
    for job in json.loads(a.queue.read_text()):
        path=Path(job['result'])
        if not path.exists() or json.loads(path.read_text())['status']!='complete':continue
        data=path.parent if job['kind'].startswith('native') else path.parent/'benchmark'
        state=json.loads((data/'result.json').read_text());assert state['status']=='complete' and state['pilot']
        samples=data/'samples.jsonl';rows=[json.loads(line) for line in samples.read_text().splitlines()]
        assert len(rows)==state['observations']
        inputs.append(dict(name=job['name'],samples=len(rows),sha256=hashlib.sha256(samples.read_bytes()).hexdigest()))
        keys=sorted({(r.get('compressor',Path(state.get('image','unknown')).stem),r['workload'],r.get('phase','application')) for r in rows})
        for codec,workload,phase in keys:
            cell=[r for r in rows if r.get('compressor',Path(state.get('image','unknown')).stem)==codec and r['workload']==workload and r.get('phase','application')==phase]
            variants={r['variant'] for r in cell}
            pairs=[('stock','vkso'),('stock-single','vkso'),('copied','vkso'),('lkl-cache-512','vkso'),('copied-unbounded','copied'),
                   ('native-word-normal','prepared-optimized'),('native-word-relaxed','prepared-optimized'),
                   ('prepared-xz','prepared-optimized'),('native-small-normal','native-word-normal')]
            for baseline,treatment in pairs:
                if not {baseline,treatment}<=variants:continue
                ratios=[];cpu=[];pairs=[]
                for block in sorted({r['block'] for r in cell}):
                    bs=[r for r in cell if r['variant']==baseline and r['block']==block]
                    ts=[r for r in cell if r['variant']==treatment and r['block']==block]
                    assert len(bs)==len(ts)==1
                    ratios.append(ts[0]['wall_seconds']/bs[0]['wall_seconds'])
                    bcpu=bs[0].get('cpu_seconds',bs[0].get('user_cpu_seconds',0)+bs[0].get('system_cpu_seconds',0))
                    tcpu=ts[0].get('cpu_seconds',ts[0].get('user_cpu_seconds',0)+ts[0].get('system_cpu_seconds',0))
                    if bcpu>0 and tcpu>0:cpu.append(tcpu/bcpu)
                    pairs.append(dict(block=block,baseline_wall=bs[0]['wall_seconds'],treatment_wall=ts[0]['wall_seconds'],baseline_cpu=bcpu,treatment_cpu=tcpu))
                results.append(dict(campaign=job['name'],codec=codec,workload=workload,phase=phase,baseline=baseline,treatment=treatment,
                    blocks=len(ratios),paired_geomean_ratio=math.exp(statistics.mean(math.log(v) for v in ratios)),
                    min_ratio=min(ratios),max_ratio=max(ratios),ratios=ratios,
                    paired_observations=pairs,
                    paired_cpu_geomean=math.exp(statistics.mean(math.log(v) for v in cpu)) if cpu else None))
    record=dict(status='descriptive-pilot',scope='Completed pilots only; one campaign, no formal CI/acceptance, no pooling across versions',inputs=inputs,results=results)
    if a.output:
        assert not a.output.exists();a.output.write_text(json.dumps(record,indent=2)+'\n')
    if a.brief:
        for r in results:
            print(r['campaign'],r['codec'],r['workload'],r['phase'],r['treatment']+'/'+r['baseline'],
                  f"wall={r['paired_geomean_ratio']:.4f}",f"cpu={r['paired_cpu_geomean']:.4f}" if r['paired_cpu_geomean'] else 'cpu=unavailable')
    else:print(json.dumps(record,indent=2))

if __name__=='__main__':main()
