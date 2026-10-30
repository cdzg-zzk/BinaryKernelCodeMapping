#!/usr/bin/env python3
"""Verify archived files and independently recompute results without server assets."""
import argparse,collections,hashlib,json,math,statistics,tarfile
from pathlib import Path

def sha(data):return hashlib.sha256(data).hexdigest()
def close(a,b):assert math.isclose(a,b,rel_tol=2e-9,abs_tol=1e-11),(a,b)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();root=a.bundle.resolve()
    manifest=json.loads((root/'manifest.json').read_text());assert manifest['status']=='complete'
    campaigns={r['archive']:r for r in manifest['campaigns']};cells=collections.defaultdict(list);count=0;files=0;boots=set();partial=0
    for item in manifest['analysis_files']:assert sha((root/item['path']).read_bytes())==item['sha256'],item['path']
    for item in manifest['archives']:
        path=root/item['path'];assert sha(path.read_bytes())==item['sha256'],path
        with tarfile.open(path,'r:gz') as tar:
            inventory=json.load(tar.extractfile('MANIFEST.json'));records={r['member']:r for r in inventory['files']}
            assert len(records)==item['files'];assert {m.name for m in tar.getmembers()}==set(records)|{'MANIFEST.json'}
            for member,record in records.items():
                assert not Path(member).is_absolute() and '..' not in Path(member).parts
                content=tar.extractfile(member).read();assert len(content)==record['bytes'] and sha(content)==record['sha256'],(path,member);files+=1
            if path.name=='squash-data48-native-final-03.tar.gz':
                partial=len(tar.extractfile('samples.jsonl').read().splitlines());assert partial==790
            if item['path'] not in campaigns:continue
            campaign=campaigns[item['path']];kind=campaign['kind'];prefix='' if kind.startswith('native') else 'benchmark/'
            state=json.load(tar.extractfile(prefix+'result.json'));outer=json.load(tar.extractfile('result.json'))
            assert state['status']==outer['status']=='complete' and outer['modules_unloaded']
            env=json.load(tar.extractfile(prefix+'environment.json'));boots.add(env['boot_id'])
            rows=[json.loads(l) for l in tar.extractfile(prefix+'samples.jsonl')];assert len(rows)==state['observations'];count+=len(rows)
            keys=[(r['campaign'],r['block'],r['variant'],r['workload'],r.get('compressor'),r.get('phase')) for r in rows];assert len(set(keys))==len(keys)
            for r in rows:cells[kind,r.get('compressor',Path(state.get('image','unknown')).stem),r['workload'],r.get('phase','full-application')].append(r)
    data=json.loads((root/'analysis/analysis.json').read_text());assert count==data['observations']==8172 and len(campaigns)==30 and len(boots)==1
    for result in data['results']:
        rows=cells[tuple(result[k] for k in ['kind','codec','workload','phase'])];pairs=collections.defaultdict(dict)
        for r in rows:
            if r['variant'] in [result['baseline'],result['treatment']]:pairs[r['campaign'],r['block']][r['variant']]=r['wall_seconds']
        ratios=collections.defaultdict(list);diffs=collections.defaultdict(list)
        for (campaign,block),values in pairs.items():
            b=values[result['baseline']];t=values[result['treatment']];ratios[campaign].append(math.log(t/b));diffs[campaign].append(t-b)
        assert len(ratios)==3 and len(pairs)==result['pairs']
        for campaign,values in ratios.items():
            close(math.exp(statistics.mean(values)),result['campaign_ratios'][campaign])
            assert len(values)==result['blocks_per_campaign'][campaign]
        if 'cpu_ratio' in result:
            cpu_pairs=collections.defaultdict(dict);cpu_groups=collections.defaultdict(list)
            for r in rows:
                if r['variant'] in [result['baseline'],result['treatment']]:
                    cpu_pairs[r['campaign'],r['block']][r['variant']]=r.get('cpu_seconds',r.get('user_cpu_seconds',0)+r.get('system_cpu_seconds',0))
            for (campaign,block),values in cpu_pairs.items():
                b,t=values[result['baseline']],values[result['treatment']]
                if b>0 and t>0:cpu_groups[campaign].append(math.log(t/b))
            means=[statistics.mean(v) for v in cpu_groups.values()];assert len(means)==3
            center=statistics.mean(means);half=4.302652730*statistics.stdev(means)/math.sqrt(3)
            close(math.exp(center),result['cpu_ratio']);close(math.exp(center-half),result['cpu_ratio_ci95'][0]);close(math.exp(center+half),result['cpu_ratio_ci95'][1])

        for values,point,ci,transform in [(ratios,result['time_ratio'],result['ratio_ci95'],math.exp),(diffs,result['paired_difference_seconds'],result['difference_ci95_seconds'],lambda x:x)]:
            means=[statistics.mean(v) for v in values.values()];center=statistics.mean(means);half=4.302652730*statistics.stdev(means)/math.sqrt(3)
            close(point,transform(center));close(ci[0],transform(center-half));close(ci[1],transform(center+half))
    for row in data['absolute']:
        rows=cells[tuple(row[k] for k in ['kind','codec','workload','phase'])];campaigns_in_cell={r['campaign'] for r in rows}
        medians=[statistics.median(r['wall_seconds'] for r in rows if r['campaign']==c and r['variant']==row['variant']) for c in campaigns_in_cell]
        center=statistics.mean(medians);half=4.302652730*statistics.stdev(medians)/math.sqrt(3)
        close(center,row['mean_campaign_median_seconds']);close(center-half,row['ci95_seconds'][0]);close(center+half,row['ci95_seconds'][1])

    result=dict(status='complete',scope='Offline archive integrity and independent timing replay; no kernel, binaries or image assets needed.',archives=len(manifest['archives']),files=files,observations=count,campaigns=30,comparisons=len(data['results']),excluded_interrupted_observations=partial,manifest_sha256=sha((root/'manifest.json').read_bytes()))
    if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
