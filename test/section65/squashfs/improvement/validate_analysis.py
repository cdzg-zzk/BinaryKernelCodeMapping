#!/usr/bin/env python3
"""Independently reconstruct all paired estimates and finite-matrix counts."""
import argparse,collections,hashlib,json,math,statistics
from pathlib import Path
def load(p):return json.loads(p.read_text())
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--analysis',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--xz-attribution',action='store_true');p.add_argument('--loader-control',action='store_true');p.add_argument('--single-cpu',action='store_true');a=p.parse_args()
    if a.single_cpu:a.loader_control=True
    assert not (a.xz_attribution and a.loader_control)
    data=load(a.analysis);assert data['status']=='complete';cells=collections.defaultdict(list);campaigns=[];boots=set();identities={}
    for source in data['inputs']:
        run=Path(source['run']);outer=load(run/'result.json');assert outer['status']=='complete' and outer['modules_unloaded']
        name=run.name
        kind='application' if 'application-improved' in name else 'native-control' if 'bounded-control' in name else 'native-stream' if 'improved-stream' in name else 'native'
        folder=run/'benchmark' if kind=='application' else run;result=load(folder/'result.json');assert not result['pilot']
        raw=(folder/'samples.jsonl').read_bytes();assert hashlib.sha256(raw).hexdigest()==source['sha256']
        rows=[json.loads(line) for line in raw.splitlines()];assert len(rows)==source['samples']==result['observations']
        expected={'native':960,'native-control':240,'native-stream':192}.get(kind)
        codec=Path(result.get('image','unknown')).stem
        if kind=='application':expected={'gzip':480,'xz':288,'lz4':432}[codec]
        if a.xz_attribution:assert kind=='application' and codec=='xz';expected=224
        if a.loader_control:assert kind=='application' and result['equal_loader_paths'];expected=160
        assert len(rows)==expected,(name,len(rows),expected)
        assert [r['sequence'] for r in rows]==list(range(expected))
        env=load(folder/'environment.json');boots.add(env['boot_id'])
        assert {r['block'] for r in rows}==set(range(result['blocks']))
        assert result['blocks']==(8 if kind in ['native-control','native-stream'] or a.xz_attribution or a.loader_control else 12)
        variants=set(result['variants']);assert variants=={r['variant'] for r in rows}
        if kind in ['native','native-stream']:expected_variants={'original','prepared-before','prepared-small-copy','prepared-composed'}
        elif kind=='native-control':expected_variants={'original','native-normal','native-small-normal','native-small-relaxed','prepared-small-copy'}
        else:
            expected_variants={'stock','copied-old','copied','vkso','lkl-512','lkl-cache-512'}
            if codec in ['gzip','lz4']:expected_variants|={'copied-directory','copied-direct','copied-library'}
            if codec=='gzip':expected_variants.add('stock-wrapped')
            if a.xz_attribution:expected_variants={'stock','copied-old','copied-directory','copied-direct','copied-library','copied','vkso'}
            if a.loader_control:expected_variants={'stock','copied-old','copied-library','copied','vkso'}
        assert variants==expected_variants
        order=collections.Counter()
        for row in rows:
            assert row['campaign']==result['campaign'] and row['wall_seconds']>0
            cell=(kind,row.get('compressor',codec),row['workload'],row.get('phase','full-application'))
            cells[cell].append(row);order[cell,row['block'],row['variant']]+=1
        assert set(order.values())=={1},name
        if kind!='application':
            digests=collections.defaultdict(set)
            for row in rows:digests[row['workload']].add((row['digest'],row['bytes']))
            assert all(len(v)==1 for v in digests.values())
            assert len(result['order'])==len(rows)//2
            for index,entry in enumerate(result['order']):
                assert all(rows[index*2][k]==entry[k] for k in ['block','compressor','workload','variant'])
        else:
            assert outer['restored'] and result['resource_observation_order'].startswith('Before workload')
            physical=load(folder/'vkso-pfns.json');copied=load(folder/'copied-pfns.json')
            assert physical['status']==copied['status']=='pass'
            assert len(physical['pages'])==len(copied['pages'])==7
            assert all(p['shared'] for p in physical['pages']) and not any(p['shared'] for p in copied['pages'])
            assert [p['mapped_page_sha256'] for p in physical['pages']]==[p['mapped_page_sha256'] for p in copied['pages']]
            identity=tuple(p['mapped_page_sha256'] for p in physical['pages']);identities.setdefault(codec,identity)
            # Code pages contain relocated helper addressing; compare identical backing within each campaign.
            if a.loader_control:
                assert result['cpus']==([1] if a.single_cpu else [1,2])
                if a.single_cpu:
                    for value in load(folder/'resources.json').values():
                        for phase in ['before','after']:
                            assert value[phase]['helper']['affinity']==[1]
                            # runuser is the common outer launcher, before taskset.
                            assert all(p['affinity']==[1] for p in value[phase]['processes'] if not p['executable'].endswith('/runuser'))
                assert collections.Counter(result['loader_padding_order'])=={0:4,16:4}
                assert all(r['loader_padding']==result['loader_padding_order'][r['block']] for r in rows)
                aliases=load(folder/'loader-aliases.json');assert len(aliases)==24
                for padding in [0,16]:
                    for part in ['core','bridge','frontend']:
                        selected=[r for r in aliases if r['padding']==padding and r['kind']==part]
                        assert len({len(r['path']) for r in selected})==1
                        pair={r['variant']:r for r in selected if r['variant'] in ['copied','vkso']}
                        assert pair['copied']['sha256']==pair['vkso']['sha256']
                        assert (pair['copied']['inode']==pair['vkso']['inode'])==(part!='core')
                        assert all(Path(r['path']).stat().st_ino==Path(r['source']).stat().st_ino==r['inode'] for r in selected)
                traces={v:[json.loads(l) for l in (folder/f'{v}-helper/trace.jsonl').read_text().splitlines()] for v in variants if v!='stock'}
                for v,trace in traces.items():
                    assert len(trace)==33
                    actual=[r['command'][1] for r in trace[1:]]
                    expected_paths=[]
                    for r in rows:
                        if r['variant']==v:
                            expected_paths.append(next(s['path'] for s in aliases if s['variant']==v and s['kind']=='core' and s['padding']==r['loader_padding']))
                    assert actual==expected_paths
        campaigns.append(dict(campaign=name,kind=kind,codec=codec,observations=len(rows),blocks=result['blocks'],variants=sorted(variants),boot_id=env['boot_id'],loadavg=env['loadavg'],frequency=env.get('frequency',env.get('governors'))))
    expected_campaigns,expected_observations=(9,1440) if a.loader_control else (3,672) if a.xz_attribution else (18,7776)
    assert len(campaigns)==expected_campaigns and len(boots)==1 and sum(c['observations'] for c in campaigns)==expected_observations
    errors=[]
    for reported in data['results']+data.get('loader_padding_results',[]):
        key=tuple(reported[k] for k in ['kind','codec','workload','phase']);b,t=reported['baseline'],reported['treatment'];paired=collections.defaultdict(dict)
        for r in cells[key]:
            if 'loader_padding' in reported and r['loader_padding']!=reported['loader_padding']:continue
            if r['variant'] in [b,t]:paired[r['campaign'],r['block']][r['variant']]=r['wall_seconds']
        assert all(set(p)=={b,t} for p in paired.values())
        ratios=collections.defaultdict(list);differences=collections.defaultdict(list)
        for (campaign,block),values in paired.items():
            ratios[campaign].append(math.log(values[t]/values[b]));differences[campaign].append(values[t]-values[b])
        assert len(ratios)==3 and len(paired)==reported['pairs']
        def estimate(groups):
            values=[statistics.fmean(g) for _,g in sorted(groups.items())];mean=statistics.fmean(values);spread=4.302652730*statistics.stdev(values)/math.sqrt(3)
            return mean,mean-spread,mean+spread
        point,low,high=map(math.exp,estimate(ratios));d,dl,dh=estimate(differences)
        actual=[point,low,high,d,dl,dh];expected=[reported['time_ratio'],*reported['ratio_ci95'],reported['paired_difference_seconds'],*reported['difference_ci95_seconds']]
        assert all(math.isclose(x,y,rel_tol=1e-11,abs_tol=1e-12) for x,y in zip(actual,expected)),(key,b,t,actual,expected)
        errors.extend(abs(x-y) for x,y in zip(actual,expected))
    output=dict(status='complete',campaigns=campaigns,observations=expected_observations,comparisons=len(data['results']),max_numeric_replay_error=max(errors),
        padding_comparisons=len(data.get('loader_padding_results',[])),
        analysis_sha256=hashlib.sha256(a.analysis.read_bytes()).hexdigest(),scope='Independent standard-library reconstruction of primary paired estimates; exact matrix, sequence, block and within-campaign instruction-backing checks.',
        exclusions='No formal samples excluded. Pilots and failed development runs are separate from the prospectively fixed formal matrix.',
        inference_scope='One host and boot, three loading/process campaigns per cell. Pointwise intervals, not a simultaneous family-wise equivalence guarantee.')
    a.output.write_text(json.dumps(output,indent=2)+'\n');print('validated',len(campaigns),'campaigns and',len(data['results']),'comparisons')
if __name__=='__main__':main()
