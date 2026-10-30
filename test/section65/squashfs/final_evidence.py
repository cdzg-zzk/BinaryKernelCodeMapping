#!/usr/bin/env python3
"""Check the experiment, functional, manuscript and artifact completion gates."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]


def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',type=Path,required=True);p.add_argument('--figures',type=Path,required=True)
    p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analysis=a.analysis.resolve();figures=a.figures.resolve();snapshot=a.snapshot.resolve()
    state=load(analysis/'result.json');assert state['status']=='complete'
    assert (state['native_campaigns'],state['application_campaigns'],state['matched_cache_campaigns'])==(16,9,9)
    assert state['native_observations']+state['application_observations']+state['matched_cache_observations']==13968
    for group in ['native','application','cache']:
        assert load(analysis/(group+'-statistics-validation.json'))['status']=='pass'
        assert (analysis/group/'campaign-estimates.csv').exists()
    extra=ROOT/'test/evaluation-local/runs/iso9660/squash-functional-extra-01'
    functional=load(extra/'result.json')
    assert functional['status']=='complete' and functional['restored'] and functional['modules_unloaded']
    assert len(functional['cases'])==25 and all(c['status']=='pass' for c in functional['cases'])
    maintenance=load(analysis/'existing-audit.json')['squashfs_maintenance']
    assert functional['binaries']['vkso_sq_core.ko']==maintenance['owner_hashes']['fixed']
    for name,pair in maintenance['unchanged_user_binaries'].items():assert functional['binaries'][name]==pair['fixed']
    for codec in ['gzip','xz','zstd','lz4','lzo']:
        pages=[]
        for variant in ['copied','shared']:
            observation=load(extra/(variant+'-'+codec+'-pfns.json'))
            assert observation['status']=='pass' and len(observation['pages'])==6
            assert all(r['shared']==(variant=='shared') for r in observation['pages'])
            assert observation['private_table_distinct_from_native']
            assert all(int(v,16)==0 for v in observation['operation_table_targets'])
            pages.append({r['offset']:r['mapped_page_sha256'] for r in observation['pages']})
        assert pages[0]==pages[1]
    provenance=load(figures/'provenance.json')
    assert sha(Path(provenance['generator']))==provenance['generator_sha256']
    for item in provenance['sources']:
        assert sha(Path(item['path']))==item['sha256']==sha(figures/item['copy'])
    for item in load(snapshot/'identity.json')['files']:
        assert sha(snapshot/item['snapshot'])==item['sha256']
    section=(ROOT/'paper/filesystem-section.tex').read_text()
    canonical=(ROOT/'paper/paper_content/sections/06-evaluation.tex').read_text()
    marker=r'\subsection{Filesystem Reuse in Applications}'
    assert section==marker+canonical.split(marker,1)[1].split(r'\subsection{',1)[0]
    assert '% Work in progress:' not in section
    pdf=ROOT/'paper/filesystem-section-preview.pdf';assert pdf.read_bytes().startswith(b'%PDF-')
    qa=ROOT/'paper/data/section65/render-qa.json';review=load(qa)
    assert review['status']=='pass' and review['pdf_sha256']==sha(pdf)
    verdicts=ROOT/'test/section65/claim-verdicts.json';assert load(verdicts)['status']=='complete'
    for claim in load(verdicts)['claims']:
        assert all((ROOT/path).exists() for path in claim['evidence'])
    result=dict(status='complete',campaigns=34,timed_observations=13968,
        native_campaigns=16,default_application_campaigns=9,matched_cache_campaigns=9,
        extra_semantic_mount_cases=25,
        scope='Section 6.5 evidence and standalone compiled subsection; no claim that the entire paper builds.',
        records=[dict(path=str(path.relative_to(ROOT)),sha256=sha(path)) for path in
            [analysis/'result.json',extra/'result.json',snapshot/'identity.json',figures/'provenance.json',
             ROOT/'paper/filesystem-section.tex',pdf,qa,verdicts]],
        analysis=str(analysis.relative_to(ROOT)),snapshot=str(snapshot.relative_to(ROOT)))
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='complete',campaigns=34,timed_observations=13968,extra_semantic_mount_cases=25)))


if __name__=='__main__':main()
