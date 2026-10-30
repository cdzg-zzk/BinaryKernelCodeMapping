#!/usr/bin/env python3
"""Check final XZ-composed delivery against runs, identities and publication."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
RAW=ROOT/'test/evaluation-local/runs/iso9660'
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['analysis','figures','snapshot','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();analysis=a.analysis.resolve();figures=a.figures.resolve();snapshot=a.snapshot.resolve()
    data=read(analysis/'analysis.json');audit=read(analysis/'audit.json')
    resources=read(analysis/'resource-ledger/resources.json')
    assert data['status']==audit['status']==resources['status']=='complete'
    assert data['observations']==audit['observations']==6540 and len(data['inputs'])==30
    assert audit['analysis_sha256']==sha(analysis/'analysis.json') and audit['excluded_observations']==0
    build=ROOT/'test/section65/build/squashfs/refine-xz-01'
    identity={n:sha(build/n) for n in ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse']}
    checked=[]
    for name in ['squash-refine-xz-functional-01','squash-refine-xz-guest-01',
                 'squash-refine-xz-execution-01','squash-refine-xz-bcj-02']:
        path=RAW/name/'result.json';result=read(path);checked.append(path)
        assert result['status']=='complete' and result['restored'] and result['modules_unloaded']
        assert all(result['binaries'][n]==value for n,value in identity.items())
    functional=read(checked[0]);assert len(functional['cases'])==25 and all(c['status']=='pass' for c in functional['cases'])
    for codec in ['gzip','xz','zstd','lz4','lzo']:
        hashes=[]
        for variant in ['copied','shared']:
            record=read(RAW/'squash-refine-xz-functional-01'/f'{variant}-{codec}-pfns.json')
            assert record['status']=='pass' and len(record['pages'])==9
            assert all(r['shared']==(variant=='shared') for r in record['pages'])
            assert record['private_table_distinct_from_native'] and all(int(v,16)==0 for v in record['operation_table_targets'])
            assert len(record['private_codec_bindings'])==3
            assert all(0<int(s['target'],16)<2**47 and s['user_pfn']!=s['kernel_pfn'] for s in record['private_codec_bindings'])
            xz=record['private_xz_bindings'];assert xz['services']==9 and xz['user_pfn']!=xz['kernel_pfn']
            assert len(xz['targets'])==9 and all(0<int(v,16)<2**47 for v in xz['targets'])
            hashes.append({r['offset']:r['mapped_page_sha256'] for r in record['pages']})
        assert hashes[0]==hashes[1]
    guest=read(checked[1]);assert guest['native_negative']['errno']==5
    for variant in ['copied','shared']:
        assert guest[variant]['client_errno']==5 and guest[variant]['daemon_alive_after_read']
        regression=read(RAW/'squash-refine-xz-guest-01/guest/evidence'/f'regression-{variant}/result.json')
        assert regression['status']=='pass' and len(regression['cases'])==6
        assert sum(c['random_and_boundary_reads'] for c in regression['cases'])==22032
    simultaneous=read(checked[2]);assert len(simultaneous['phases'])==16 and len(simultaneous['cases'])==2
    assert simultaneous['native_after'] and simultaneous['real_fd_and_partition_offsets']
    assert all(c['three_consumer_overlap_phases'] and c['consumer_cleanup_order']==['C','A','B'] and c['private_objects_disjoint'] for c in simultaneous['cases'])
    debug=RAW/'squash-refine-xz-execution-01'
    before=read(debug/'shared-B-pfns-before.json');after=read(debug/'shared-B-pfns-after-xz-breakpoint.json')
    assert all(r['shared'] for r in after['pages']) and len(after['pages'])==9
    assert [(r['user_pfn'],r['kernel_pfn']) for r in before['pages']]==[(r['user_pfn'],r['kernel_pfn']) for r in after['pages']]
    assert 'vkso_xz_dec_run' in (debug/'xz-breakpoint.log').read_text()
    assert [4,33] in read(checked[3])['xz_filter_chains']
    for name in ['squash-refine-xz-native-calls-01','squash-refine-hardening-02',
                 'squash-refine-metadata-work-01','squash-refine-minimal-deployment-01']:
        path=RAW/name/'result.json';assert read(path)['status']=='complete';checked.append(path)
    for item in data['inputs']:
        run=Path(item['run']);state=read(run/'result.json')
        assert state['status']=='complete' and state['modules_unloaded']
        if not (run/'benchmark').is_dir():continue
        bench=read(run/'benchmark/result.json')
        for variant in ['copied','vkso']:
            trace=[json.loads(l) for l in (run/'benchmark'/f'{variant}-helper/trace.jsonl').read_text().splitlines()]
            assert len(trace)>=bench['blocks'] and all(r['source'].startswith('/proc/self/fd/') and r['offset']>0 for r in trace)
    assert resources['platform']['resident_bytes']==32768 and resources['platform']['charged_to_business_bytes']==0
    for key,value in [('native_preparation_delta_bytes',49152),('shared_backing_avoided_once_bytes',36864),
                      ('registration_requested_bytes',1264),('owner_resident_bytes',69632)]:
        assert resources['business'][key]==value
    assert len(resources['scale'])==15 and resources['minimal_deployment']['copied_modules_absent']
    costs=read(analysis/'costs.json')
    assert len(costs['moved_functions'])==34 and sum(r['original_lines'] for r in costs['moved_functions'])==2103
    assert sum(r['body_changed'] for r in costs['moved_functions'])==3
    assert costs['native_changed_file_count']==16 and costs['lkl_application_added_lines']==30
    assert costs['xz_composition']['unchanged_algorithm_physical_lines']==2604
    for row in costs['xz_composition']['original_sources']:
        assert sha(build/Path(row['path']).name)==row['sha256']
    assert sha(build/'shared_core.c')==sha(ROOT/'test/section65/build/squashfs/evaluation-improved-01/build/shared_core.c')
    assert sum(r['physical_lines'] for r in costs['source_lines'] if r['category']=='generated_native_support')==390
    assert {Path(r['path']).name:r['physical_lines'] for r in costs['source_lines'] if r['category']=='first_user_integration'}=={'user_bridge.c':408,'posix_io.c':154,'fuse_frontend.c':300}
    provenance=read(figures/'provenance.json');assert provenance['status']=='complete'
    assert sha(Path(provenance['plotting_script']))==provenance['script_sha256']
    for source in provenance['sources']:assert sha(Path(source['path']))==source['sha256']
    for record in read(snapshot/'identity.json')['files']:
        assert sha(snapshot/record['snapshot'])==record['sha256']
        assert sha(Path(record['source']))==record['sha256'],record['source']
    assert all(sha(snapshot/'build'/n)==value for n,value in identity.items())
    section=(ROOT/'paper/filesystem-section.tex').read_text();canonical=(ROOT/'paper/paper_content/sections/06-evaluation.tex').read_text()
    marker=r'\subsection{Filesystem Reuse in Applications}'
    assert section==marker+canonical.split(marker,1)[1].split(r'\subsection{',1)[0]
    assert 'TBD' not in section and '@@' not in section
    numbers=read(analysis/'section65.numbers.json');assert numbers['status']=='complete'
    for paragraph in numbers['paragraphs'].values():assert paragraph in section
    pdf=ROOT/'paper/filesystem-section-preview.pdf';assert pdf.read_bytes().startswith(b'%PDF-')
    qa=ROOT/'paper/data/section65/render-qa.json';review=read(qa)
    assert review['status']=='pass' and review['pdf_sha256']==sha(pdf)
    verdicts=ROOT/'test/section65/claim-verdicts.json';judgments=read(verdicts)
    assert judgments['status']=='complete' and judgments['version']=='xz-composed-refined'
    assert len(judgments['claims'])==13
    for claim in judgments['claims']:assert all((ROOT/path).exists() for path in claim['evidence'])
    records=checked+[analysis/'analysis.json',analysis/'audit.json',analysis/'resource-ledger/resources.json',
        analysis/'costs.json',analysis/'section65.numbers.json',snapshot/'identity.json',figures/'provenance.json',
        ROOT/'paper/filesystem-section.tex',pdf,qa,verdicts,ROOT/'test/section65/claim-experiment-map.md',
        ROOT/'paper/paper_content/references.bib']
    result=dict(status='complete',version='xz-composed-refined',campaigns=30,timed_observations=6540,
        accounting='Installed generic platform; filesystem preparation, per-core metadata and private runtime costs retained.',
        preserved_predecessor='paper/build/section65-composed-publication-01/identity.json',
        scope='Final-owner confirmation and compiled standalone Section 6.5, one host/boot. Does not claim whole-paper build, hardening equivalence, human-time savings or whole-machine net savings.',
        analysis=str(analysis.relative_to(ROOT)),snapshot=str(snapshot.relative_to(ROOT)),
        records=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in records])
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('final XZ-composed Section 6.5 evidence complete')


if __name__=='__main__':main()
