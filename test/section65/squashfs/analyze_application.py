#!/usr/bin/env python3
"""Audit completed Apptainer comparisons and summarize their measured scope."""
import json
import math
from pathlib import Path
import random
import statistics
import sys

HERE=Path(__file__).resolve().parent
SECTION=HERE.parent
ROOT=SECTION.parents[1]
sys.path.insert(0,str(SECTION))
from squashfs.apptainer_bench import summarize


def read(path):return json.loads(path.read_text())

def main():
    campaigns=[]
    for name in ['squash-apptainer-comparison-01','squash-apptainer-comparison-02']:
        root=ROOT/'test/evaluation-local/runs/iso9660'/name
        lifecycle=read(root/'result.json');p=root/'benchmark'
        result=read(p/'result.json')
        assert lifecycle['status']=='complete' and lifecycle['restored'] and lifecycle['modules_unloaded']
        assert result['status']=='complete' and result['observations']==192
        samples=[json.loads(line) for line in (p/'samples.jsonl').read_text().splitlines()]
        assert len(samples)==192
        for block in range(8):
            for workload in ['startup','archive']:
                for variant in result['variants']:
                    cell=[r for r in samples if (r['block'],r['workload'],r['variant'])==(block,workload,variant)]
                    assert len(cell)==2 and {r['repeat'] for r in cell}=={0,1}
        resources=read(p/'resources.json')
        assert set(resources)==set(result['variants'])
        for resource in resources.values():assert resource['entries']==5866
        for label,sharing in [('copied',False),('vkso',True)]:
            pages=read(p/(label+'-pfns.json'))
            assert pages['status']=='pass' and len(pages['pages'])==6
            assert all(row['shared']==sharing for row in pages['pages'])
            assert len(pages['binding_targets'])==46
        recomputed=summarize(samples)
        assert recomputed==result['summary']
        comparisons=[]
        for baseline in ['stock','stock-wrapped','copied','lkl-16','lkl-64']:
            for workload in ['startup','archive']:
                ratios=[]
                for block in range(8):
                    values={v:statistics.median(r['wall_seconds'] for r in samples
                        if r['block']==block and r['workload']==workload and r['variant']==v)
                            for v in [baseline,'vkso']}
                    ratios.append(values['vkso']/values[baseline])
                logs=list(map(math.log,ratios));rng=random.Random(20261029)
                boots=sorted(math.exp(statistics.mean(rng.choices(logs,k=len(logs)))) for _ in range(10000))
                comparisons.append(dict(baseline=baseline,treatment='vkso',workload=workload,
                    paired_block_ratios=ratios,paired_time_ratio=math.exp(statistics.mean(logs)),
                    bootstrap_95_percent=[boots[250],boots[9749]]))
        campaigns.append(dict(name=name,evidence=str(root.relative_to(ROOT)),
            helper='Python translator' if result.get('python_helper_included') else result['helper_implementation'],
            observations=len(samples),comparisons=recomputed,vkso_pairs=comparisons,
            variants={v:dict(startup_median_seconds=statistics.median(r['wall_seconds'] for r in samples if r['workload']=='startup' and r['variant']==v),
                             archive_median_seconds=statistics.median(r['wall_seconds'] for r in samples if r['workload']=='archive' and r['variant']==v),
                             helper_memory_before=resources[v]['before']['helper']['memory'],
                             helper_memory_after=resources[v]['after']['helper']['memory'])
                      for v in result['variants']}))
    record=dict(status='audited',campaigns=campaigns,
        scope='single gzip SIF, one hardware boot, GNU tar over 5866 Linux include entries; full process lifecycle timing',
        launcher_scope='timing includes the common runuser/taskset launcher',
        memory_scope='one before/after helper-process snapshot per backend per campaign; not total-machine or exact peak memory',
        comparison_scope='stock SquashFUSE 0.6.2, prepared Linux 5.15.198 core, focused LKL 6.12 at 16/64 MiB configured memory',
        controls=['same native runtime instruction bytes in copied/VKSO carriers',
                  'stock-wrapped uses the same argument translator',
                  'LKL receives the same SIF descriptor and offset; its filesystem/library source is unchanged'],
        limits=['backend caches and runtime implementations differ; only copied/VKSO isolates page sharing',
                'all module preparation and user adapter code must be counted; no measured developer hours',
                'maintenance candidate inspected but not yet executed'])
    (SECTION/'squashfs-application-analysis.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(status=record['status'],campaigns=len(campaigns),observations=sum(c['observations'] for c in campaigns))))


if __name__=='__main__':main()
