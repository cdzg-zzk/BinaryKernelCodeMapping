#!/usr/bin/env python3
"""Audit completed application samples and saved functional/backing evidence."""
import argparse
import collections
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import statistics


def read(path):
    return json.loads(path.read_text())


def audit(path):
    outer=read(path/'result.json'); root=path/'benchmark'; result=read(root/'result.json')
    assert outer['status']=='complete' and outer['restored'] and outer['modules_unloaded'],path
    assert result['status']=='complete' and result['completed_blocks']==result['blocks']
    rows=[json.loads(line) for line in (root/'samples.jsonl').read_text().splitlines()]
    expected=set(itertools.product(range(result['blocks']),result['workloads'],
                                   result['variants'],range(result['repeats'])))
    actual=[(r['block'],r['workload'],r['variant'],r['repeat']) for r in rows]
    assert len(actual)==len(set(actual))==len(expected)==result['observations']
    assert set(actual)==expected and [r['sequence'] for r in rows]==list(range(len(rows)))
    rng=random.Random(result['seed']); order=[]
    for block in range(result['blocks']):
        cells=list(itertools.product(result['workloads'],result['variants']));rng.shuffle(cells)
        order.extend((block,w,v,r) for w,v in cells for r in range(result['repeats']))
    assert actual==order,'saved execution order differs from seeded randomization'
    for r in rows:
        assert r['campaign']==result['campaign'] and r['wall_seconds']>0
        assert r['user_cpu_seconds']>=0 and r['system_cpu_seconds']>=0
        assert (root/f"timing-{r['block']}-{r['workload']}-{r['variant']}-{r['repeat']}.log").exists()
    for s in result['summary']:
        ratios=[]
        for block in range(result['blocks']):
            values={v:statistics.median(r['wall_seconds'] for r in rows
                    if r['block']==block and r['workload']==s['workload'] and r['variant']==v)
                    for v in (s['baseline'],s['treatment'])}
            ratios.append(values[s['treatment']]/values[s['baseline']])
        assert math.isclose(math.exp(statistics.mean(map(math.log,ratios))),s['paired_time_ratio'],rel_tol=1e-12)
    env=read(root/'environment.json')
    assert hashlib.sha256((root/'runner.py').read_bytes()).hexdigest()==env['runner_sha256']
    native=[read(path/name) for name in ['native-original.json','native-before.json','native-after.json']]
    assert native[0]==native[1]==native[2] and len(native[0])==outer['native_entries']
    resources=read(root/'resources.json');assert set(resources)==set(result['variants'])
    assert len({v['entries'] for v in resources.values()})==1
    physical={}
    for label in ['copied','vkso']:
        snapshots=[read(root/(label+'-pfns'+suffix+'.json')) for suffix in ['', '-after-state']]
        for s in snapshots:
            assert s['status']=='pass' and len(s['pages'])==6 and len(s['binding_targets'])==46
            assert all(p['shared']==(label=='vkso') and
                       (p['kernel_pfn']==p['user_pfn'])==(label=='vkso') for p in s['pages'])
            assert all(0<int(a,16)<2**47 for a in s['binding_targets'])
            assert s['private_table_pfn'] not in {p['kernel_pfn'] for p in s['pages']}
            if 'kernel_table_pfn' in s:
                assert s['private_table_pfn']!=s['kernel_table_pfn'] and s['private_table_distinct_from_native']
            if 'operation_table_targets' in s:
                assert len(s['operation_table_targets'])==10 and all(int(v,16)==0 for v in s['operation_table_targets'])
        assert snapshots[0]['pages']==snapshots[1]['pages']
        assert read(root/(label+'-private-state.json'))['status']=='pass'
        physical[label]=dict(pages=6,kernel_shared_pages=sum(p['shared'] for p in snapshots[0]['pages']),
            native_user_binding_pfns_distinct=snapshots[0].get('private_table_distinct_from_native'))
    mapped=[read(root/(label+'-pfns.json'))['pages'] for label in ['copied','vkso']]
    byte_identity=None
    if all(all('mapped_page_sha256' in p for p in pages) for pages in mapped):
        hashes=[{p['offset']:p['mapped_page_sha256'] for p in pages} for pages in mapped]
        assert hashes[0]==hashes[1], 'copied/shared mapped execution and readonly bytes differ'
        byte_identity=True
    return dict(path=str(path),status='pass',campaign=result['campaign'],pilot=result['pilot'],
                observations=len(rows),blocks=result['blocks'],variants=result['variants'],
                mapped_page_byte_identity=byte_identity,
                physical=physical,seeded_order_verified=True,native_entries=len(native[0]),
                correctness_record='Runner checks each program exit and output against its oracle before appending a sample. Per-sample manifests are not retained; saved native manifests and application preflight remain available.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    result=dict(status='pass',runs=[audit(r.resolve()) for r in a.runs])
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='pass',campaigns=len(result['runs']))))
