#!/usr/bin/env python3
"""Keep within-round pairing and complete deployments in formal cost summaries."""
from pathlib import Path
from collections import defaultdict
import argparse
import csv
import json
import math
import itertools
import statistics as stats

from algorithm_deployments import read_observations
from formal_kernel_audit import audit as audit_kernel
from setup.compare_audit import audit as audit_setup, audit_export


def read(path):return json.loads(path.read_text())


def csv_rows(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))


def write_csv(path, rows):
    assert rows
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def summarize(campaign, output, partial=False, continuation=None, applications_only=False):
    campaign=Path(campaign).resolve();output=Path(output).resolve()
    plan=read(campaign/'plan.json');output.mkdir(parents=True,exist_ok=True)
    completion_root=campaign
    if continuation is not None:
        continuation=Path(continuation).resolve()
        resumed=read(continuation/'plan.json')
        assert Path(resumed['continuation']['source']).resolve()==campaign
        for key in ('kernel','cpu','deployments_per_algorithm','with_lz4_workflow','with_kernel_cost','with_lz4_setup'):
            assert resumed[key]==plan[key], 'continuation changed experimental configuration'
        kept=set(resumed['continuation']['completed_deployments'])
        replacements={e['deployment']:e for e in resumed['entries']}
        assert not kept & replacements.keys()
        assert kept | replacements.keys()=={e['deployment'] for e in plan['entries']}
        entries=[]
        path_fields={'RUNTIME_DIR','RESULT_DIR','BUILD_DIR','WORK_DIR'}
        for old in plan['entries']:
            if old['deployment'] in kept:
                if not applications_only or old['algorithm'] == 'lz4':
                    assert (Path(old['directory'])/'complete.json').exists()
                entries.append(old)
            else:
                new=replacements[old['deployment']]
                assert new['command']==old['command'] and new['algorithm']==old['algorithm']
                assert {k:v for k,v in new['environment'].items() if k not in path_fields}=={
                    k:v for k,v in old['environment'].items() if k not in path_fields}
                entries.append(new)
        plan={**plan,'entries':entries}
        completion_root=continuation
    if applications_only:
        assert plan['with_lz4_workflow'] and plan['with_lz4_setup']
        plan = {**plan, 'entries': [e for e in plan['entries'] if e['algorithm'] == 'lz4']}
    available=[e for e in plan['entries'] if (Path(e['directory'])/'complete.json').exists()]
    if not partial:
        assert len(available)==len(plan['entries']) and (completion_root/'collection-complete.json').exists(), 'campaign incomplete'
    rows=[];audits=[];identities=[]
    replacement = None
    marker = campaign / 'kernel-replacement.json'
    if marker.exists() and not applications_only:
        replacement = read(marker)
        assert replacement['algorithm'] == 'xz'
        replacement_path = (campaign / replacement['directory']).resolve()
        from xz_kernel_campaign import analyze as analyze_xz
        report = analyze_xz(replacement_path)
        audits.extend(report['deployments'])
        for r in csv_rows(replacement_path / 'observations.csv'):
            r['round'] = int(r['round']); r['value'] = float(r['value'])
            r['deployment'] = 'xz-kernel-' + r['deployment']
            rows.append(r)
        for d in sorted(replacement_path.glob('deployment-[0-9][0-9]')):
            identities.append(read(d / 'identity.json'))
    for entry in available:
        d=Path(entry['directory']);a=entry['algorithm'];name=entry['deployment']
        identities.append(read(d/'identity.json'))
        if not applications_only:
            # Reconstruct the user table from raw counters rather than trusting the normalized CSV.
            user=read_observations(a,d/'results/raw.csv',name)
            retained=csv_rows(d/'observations.csv')
            assert len(user)==len(retained)
            for actual,saved in zip(user,retained):
                assert all(str(value)==saved[key] for key,value in actual.items()), 'normalized user row differs'
            for r in user:
                rows.append(dict(deployment=name,algorithm=a,domain='user',round=r['round'],backend=r['backend'],
                                 workload=r['workload'],value=r['value'],unit=r['unit']))
            replace_kernel = replacement is not None and a == 'xz'
            if not replace_kernel:
                audits.append(audit_kernel(d))
            if a=='bch':
                for r in csv_rows(d/'results/kernel-cost/driver-results.txt'):
                    rows.append(dict(deployment=name,algorithm=a,domain='kernel',round=int(r['round']),backend=r['backend'],
                        workload=f"m={r['m']}/t={r['t']}/bytes={r['len']}/errors={r['errors']}/{r['mode']}",
                        value=int(r['ns'])/int(r['iterations']),unit='ns/op'))
            elif not replace_kernel:
                for r in csv_rows(d/'results/kernel-cost/raw.csv'):
                    rows.append(dict(deployment=name,algorithm=a,domain='kernel',round=int(r['outer_run']),backend=r['backend'],
                        workload=f"{r['case']}/{r['operation']}/block={r['block_bytes']}",
                        value=int(r['elapsed_ns'])/int(r['repeats']),unit='ns/task'))
        if a=='lz4' and plan.get('with_lz4_setup'):
            for phase in ('active','ready'):
                directory=d/f'results/setup-comparison-{phase}'
                audits.append(audit_setup(directory,d/'work/vkso/metadata/page_replace.log'))
                for r in read(directory/'comparison.json')['rows']:
                    rows.append(dict(deployment=name,algorithm=a,domain='setup',round=r['repeat'],backend=r['backend'],
                        workload=f"{phase}/traced={int(r['traced'])}/passes={r['iterations']}",value=r['total_ns'],unit='ns/command'))
            audits.append(audit_export(d/'results/setup-export-stages.tsv'))
        if a=='lz4' and plan.get('with_lz4_workflow'):
            cli=d/'results/cli-workflow'; raw=csv_rows(cli/'raw.csv')
            metadata=read(cli/'metadata.json'); helpers=read(cli/'helper-targets.json')
            assert metadata['boot_id']==identities[-1]['boot_id'] and metadata['cpu']==plan['cpu']
            assert metadata['rounds']==4 and metadata['block_ids']==[4,6]
            backends=('stock-cli','upstream-dso','same-source','kernel-vkso')
            assert set(metadata['backends'])==set(backends)
            assert helpers['status']=='pass' and helpers['library']==metadata['backends']['kernel-vkso'][0]
            assert helpers['same_source']==metadata['backends']['same-source'][0]
            assert Path(helpers['same_source']).name=='libkernel-userspace-libc.so'
            assert {h['name'] for h in helpers['helpers']}=={'memcpy','memmove','memset'}
            for helper in helpers['helpers']:
                assert helper['baseline_imports'] and all(x['target']==helper['provider'] for x in helper['baseline_imports'])
            for block,backend,operation in itertools.product((4,6),backends[1:],('compress','decompress')):
                trace=cli/'logs'/f'trace-{block}-{backend}-{operation}.txt'
                fields=dict(line.split('=',1) for line in trace.read_text().splitlines())
                assert int(fields[operation+'_calls'])>0
                assert fields['compress_dso']==fields['decompress_dso']==metadata['backends'][backend][0]
            assert len(raw)==read(cli/'complete.json')['rows']==768
            groups=defaultdict(list)
            for r in raw:groups[int(r['round']),int(r['block_id']),r['backend'],r['operation']].append(r)
            assert set(groups)==set(itertools.product(range(4),(4,6),backends,('compress','decompress')))
            for (repeat,block,backend,op), group in sorted(groups.items()):
                assert len(group)==12 and len({r['input'] for r in group})==12
                assert sum(int(r['plain_bytes']) for r in group)==211938580
                rows.append(dict(deployment=name,algorithm=a,domain='cli',round=repeat,backend=backend,
                    workload=f'{op}/block={65536 if block==4 else 1048576}',value=sum(int(r['wall_ns']) for r in group),unit='ns/corpus'))
    # Native references remain distinct; no averaging across different baselines.
    groups=defaultdict(dict)
    for row in rows:
        assert math.isfinite(row['value']) and row['value']>0
        key=tuple(row[k] for k in ('deployment','algorithm','domain','workload','round','unit'))
        assert row['backend'] not in groups[key]
        groups[key][row['backend']]=row['value']
    paired=[]
    for key,values in sorted(groups.items()):
        name,a,domain,workload,repeat,unit=key
        target='owner-kernel' if domain=='kernel' else 'vkso' if domain=='setup' else 'kernel-vkso'
        assert target in values
        for baseline,value in sorted(values.items()):
            if baseline==target:continue
            # All ratios use cost direction: >1 means slower, also for throughput inputs.
            ratio=value/values[target] if unit in ('MB/s','MiB/s') else values[target]/value
            paired.append(dict(deployment=name,algorithm=a,domain=domain,workload=workload,round=repeat,
                target=target,baseline=baseline,cost_ratio=ratio,target_value=values[target],baseline_value=value,unit=unit))
    by_deployment=defaultdict(list)
    for r in paired:
        by_deployment[tuple(r[k] for k in ('deployment','algorithm','domain','workload','target','baseline','unit'))].append(r)
    deployment_rows=[]
    for key,group in sorted(by_deployment.items()):
        ratios=[r['cost_ratio'] for r in group]
        deployment_rows.append(dict(zip(('deployment','algorithm','domain','workload','target','baseline','unit'),key),
            rounds=len(group),median_cost_ratio=stats.median(ratios),minimum_round_ratio=min(ratios),maximum_round_ratio=max(ratios),
            median_target_value=stats.median(r['target_value'] for r in group),median_baseline_value=stats.median(r['baseline_value'] for r in group)))
    cross=defaultdict(list)
    for r in deployment_rows:cross[tuple(r[k] for k in ('algorithm','domain','workload','target','baseline','unit'))].append(r)
    summary=[]
    for key,group in sorted(cross.items()):
        values=[r['median_cost_ratio'] for r in group]
        if not partial:assert len(group)==plan['deployments_per_algorithm']
        summary.append(dict(zip(('algorithm','domain','workload','target','baseline','unit'),key),deployments=len(group),
            median_cost_ratio=stats.median(values),minimum_deployment_ratio=min(values),maximum_deployment_ratio=max(values)))
    if rows:
        for filename,data in [('observations.csv',rows),('paired-rounds.csv',paired),('deployment-ratios.csv',deployment_rows),('summary.csv',summary)]:
            write_csv(output/filename,data)
    report=dict(applications_only=applications_only,status='partial' if partial else 'complete',completed_deployments=len(available),planned_deployments=len(plan['entries']),
        source_campaign=str(campaign),continuation=str(continuation) if continuation else None,
        included_directories=[e['directory'] for e in available],
        boot_ids=sorted({r['boot_id'] for r in identities}),audits=audits,
        kernel_replacement=replacement,
        estimator='median paired round cost ratio per deployment, then equal-weight median and range across deployments',
        interpretation='cost ratio >1 means slower; ranges are descriptive, not confidence or equivalence intervals; same-boot deployments are not independent boots')
    (output/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('campaign',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--partial',action='store_true')
    p.add_argument('--continuation',type=Path)
    p.add_argument('--applications-only',action='store_true')
    a=p.parse_args();r=summarize(**vars(a))
    print(json.dumps({k:v for k,v in r.items() if k!='audits'},indent=2))
