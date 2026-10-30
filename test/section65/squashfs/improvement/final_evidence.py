#!/usr/bin/env python3
"""Verify improved-version delivery against actual runs, source identity and rendered text."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];RAW=ROOT/'test/evaluation-local/runs/iso9660'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['analysis','xz-attribution','loader-control','single-cpu','figures','snapshot','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();analysis=a.analysis.resolve();figures=a.figures.resolve();snapshot=a.snapshot.resolve()
    data=load(analysis/'analysis.json');audit=load(analysis/'analysis-audit.json');resources=load(analysis/'resources.json')
    assert data['status']==audit['status']==resources['status']=='complete'
    assert data['observations']==audit['observations']==7776 and len(data['inputs'])==18
    assert audit['analysis_sha256']==sha(analysis/'analysis.json')
    xz=a.xz_attribution.resolve();xz_data=load(xz/'analysis.json');xz_audit=load(xz/'analysis-audit.json')
    assert xz_data['status']==xz_audit['status']=='complete' and xz_data['observations']==xz_audit['observations']==672 and len(xz_data['inputs'])==3
    assert xz_audit['analysis_sha256']==sha(xz/'analysis.json')
    loader=a.loader_control.resolve();loader_data=load(loader/'analysis.json');loader_audit=load(loader/'analysis-audit.json')
    assert loader_data['status']==loader_audit['status']=='complete'
    assert loader_data['observations']==loader_audit['observations']==1440 and len(loader_data['inputs'])==9
    assert loader_audit['analysis_sha256']==sha(loader/'analysis.json') and loader_audit['padding_comparisons']==192
    assert load(RAW/'squash-path-layout-01/result.json')['status']=='complete'
    single=a.single_cpu.resolve();single_data=load(single/'analysis.json');single_audit=load(single/'analysis-audit.json')
    assert single_data['status']==single_audit['status']=='complete'
    assert single_data['observations']==single_audit['observations']==1440 and len(single_data['inputs'])==9
    assert single_audit['analysis_sha256']==sha(single/'analysis.json') and single_audit['padding_comparisons']==192
    assert all(r['cpus']==[1] for r in single_data['inputs'])
    build=ROOT/'test/section65/build/squashfs/evaluation-improved-01/build'
    identity={n:sha(build/n) for n in ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse']}
    for name in ['squash-codec-functional-01','squash-codec-guest-regression-01','squash-simultaneous-final-01']:
        result=load(RAW/name/'result.json');assert result['status']=='complete' and result['restored'] and result['modules_unloaded']
        assert all(result['binaries'][n]==value for n,value in identity.items())
    functional=load(RAW/'squash-codec-functional-01/result.json');assert len(functional['cases'])==25 and all(c['status']=='pass' for c in functional['cases'])
    for codec in ['gzip','xz','zstd','lz4','lzo']:
        observations=[]
        for variant in ['copied','shared']:
            record=load(RAW/'squash-codec-functional-01'/f'{variant}-{codec}-pfns.json')
            assert record['status']=='pass' and len(record['pages'])==7
            assert all(r['shared']==(variant=='shared') for r in record['pages'])
            assert record['private_table_distinct_from_native'] and all(int(v,16)==0 for v in record['operation_table_targets'])
            assert len(record['private_codec_bindings'])==3
            assert all(0<int(s['target'],16)<2**47 and s['user_pfn']!=s['kernel_pfn'] for s in record['private_codec_bindings'])
            observations.append({r['offset']:r['mapped_page_sha256'] for r in record['pages']})
        assert observations[0]==observations[1]
    guest=load(RAW/'squash-codec-guest-regression-01/result.json');assert guest['native_negative']['errno']==5
    for variant in ['copied','shared']:
        assert guest[variant]['client_errno']==5 and guest[variant]['daemon_alive_after_read']
        regression=load(RAW/'squash-codec-guest-regression-01/guest/evidence'/f'regression-{variant}/result.json')
        assert regression['status']=='pass' and len(regression['cases'])==6
        assert sum(c['random_and_boundary_reads'] for c in regression['cases'])==22032
    simultaneous=load(RAW/'squash-simultaneous-final-01/result.json')
    assert len(simultaneous['phases'])==16 and len(simultaneous['cases'])==2
    assert all(c['three_consumer_overlap_phases'] and c['consumer_cleanup_order']==['C','A','B'] and c['private_objects_disjoint'] for c in simultaneous['cases'])
    for item in data['inputs']+xz_data['inputs']+loader_data['inputs']+single_data['inputs']:
        run=Path(item['run'])
        if 'application-improved' not in run.name:continue
        result=load(run/'benchmark/result.json')
        for variant in result['variants']:
            if variant=='stock':continue
            trace=[json.loads(l) for l in (run/'benchmark'/f'{variant}-helper/trace.jsonl').read_text().splitlines()]
            assert len(trace)>=result['blocks']*4 and all(r['source'].startswith('/proc/self/fd/') and r['offset']==36864 for r in trace)
    provenance=load(figures/'provenance.json')
    assert sha(Path(provenance['plotting_script']))==provenance['script_sha256']
    for source in provenance['sources']:assert sha(Path(source['path']))==source['sha256']
    for record in load(snapshot/'identity.json')['files']:assert sha(snapshot/record['snapshot'])==record['sha256']
    assert all(sha(snapshot/'build'/n)==value for n,value in identity.items())
    section=(ROOT/'paper/filesystem-section.tex').read_text();canonical=(ROOT/'paper/paper_content/sections/06-evaluation.tex').read_text();marker=r'\subsection{Filesystem Reuse in Applications}'
    assert section==marker+canonical.split(marker,1)[1].split(r'\subsection{',1)[0]
    assert 'TBD' not in section and '% Work in progress:' not in section
    pdf=ROOT/'paper/filesystem-section-preview.pdf';assert pdf.read_bytes().startswith(b'%PDF-')
    qa=ROOT/'paper/data/section65/render-qa.json';review=load(qa);assert review['status']=='pass' and review['pdf_sha256']==sha(pdf)
    verdicts=ROOT/'test/section65/claim-verdicts.json';judgments=load(verdicts);assert judgments['status']=='complete' and judgments['version']=='composed-improved'
    for claim in judgments['claims']:assert all((ROOT/path).exists() for path in claim['evidence'])
    for name in ['resources.json','maintenance.json','costs.json']:assert (analysis/name).exists()
    business_path=analysis/'business-costs.json';business=load(business_path)
    assert business['status']=='complete' and business['platform']['module']=='page_cache_replace'
    assert business['platform']['resident_bytes']==resources['kernel_module_residency']['page_cache_replace']==32768
    assert business['platform']['charged_to_business_bytes']==0
    assert business['source']['sha256']==sha(analysis/'resources.json')
    assert business['business']['native_preparation_delta_bytes']==36864
    assert business['business']['registration_requested_bytes']==resources['registration']['direct_requested_bytes']==1136
    assert business['business']['shared_backing_avoided_once_bytes']==resources['unique_shared_bytes']==28672
    for timing in business['timing'].values():
        assert len(timing['samples'])==9
        for sample in timing['samples']:
            stages={r['stage']:r for r in [json.loads(line) for line in (RAW/sample['campaign']/'stages.jsonl').read_text().splitlines()]}
            assert sample['seconds']==sum(stages[name]['wall_seconds'] for name in timing['stages'])
    assert sha(business_path)==sha(ROOT/'paper/data/section65/business-costs.json')
    assert sha(ROOT/'paper/tables/filesystem-business.tex')==sha(ROOT/'paper/paper_content/tables/filesystem-business.tex')
    numbers=analysis/'manuscript-numbers.json';numeric=load(numbers);assert numeric['status']=='complete'
    for source in numeric['sources']:assert sha(Path(source['path']))==source['sha256']
    records=[analysis/'analysis.json',analysis/'analysis-audit.json',xz/'analysis.json',xz/'analysis-audit.json',loader/'analysis.json',loader/'analysis-audit.json',single/'analysis.json',single/'analysis-audit.json',analysis/'resources.json',analysis/'maintenance.json',analysis/'costs.json',numbers,snapshot/'identity.json',figures/'provenance.json',ROOT/'paper/filesystem-section.tex',pdf,qa,verdicts,ROOT/'test/section65/claim-experiment-map.md']
    records.extend([business_path,ROOT/'paper/tables/filesystem-business.tex',ROOT/'paper/paper_content/references.bib'])
    result=dict(status='complete',version='composed-improved',accounting='installed-platform; filesystem-specific costs with separate one-time infrastructure',campaigns=39,timed_observations=11328,main_campaigns=18,main_observations=7776,xz_attribution_campaigns=3,xz_attribution_observations=672,loader_control_campaigns=9,loader_control_observations=1440,single_cpu_campaigns=9,single_cpu_observations=1440,
        preserved_baseline=dict(campaigns=34,timed_observations=13968,record='test/section65/build/squashfs/final-analysis-02'),
        scope='Improvement matrix, final-core correctness/maintenance/deployment evidence and compiled standalone Section 6.5; no whole-paper build or universally positive result claim.',
        analysis=str(analysis.relative_to(ROOT)),snapshot=str(snapshot.relative_to(ROOT)),records=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in records])
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('improved Section 6.5 evidence complete')
if __name__=='__main__':main()
