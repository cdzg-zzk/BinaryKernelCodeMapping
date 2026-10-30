#!/usr/bin/env python3
"""Preserve every scoped publication/document target before installing new results."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=ROOT/'paper/build/section65-preoptimization-publication-01';out.mkdir()
    files=set()
    for name in ['paper/filesystem-section.tex','paper/filesystem-section-preview.tex','paper/filesystem-section-preview.pdf',
        'paper/build/filesystem-section-preview.pdf','paper/build_filesystem_section.py','paper/paper_content/sections/06-evaluation.tex',
        'paper/notes/section65-alignment.md','test/section65/claim-verdicts.json','test/section65/claim-experiment-map.md',
        'test/section65/final-evidence.json','test/section65/STATUS.md','test/section65/README.md',
        'test/section65/backend-conditions.md','test/section65/related-work-comparison.md','test/section65/reproduce.md','test/section65/squashfs/README.md']:
        p=ROOT/name;assert p.is_file(),p;files.add(p)
    for name in ['paper/figures/section65','paper/data/section65']:
        files.update(p for p in (ROOT/name).rglob('*') if p.is_file())
    for name in ['paper/tables','paper/paper_content/tables']:
        files.update(p for p in (ROOT/name).glob('filesystem-*.tex') if p.is_file())
    records=[]
    for source in sorted(files):
        relative=source.relative_to(ROOT);dest=out/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        assert sha(dest)==sha(source);records.append(dict(source=str(relative),sha256=sha(dest),bytes=dest.stat().st_size))
    source=ROOT/'paper/paper_content/sections/06-evaluation.tex';raw=source.read_bytes();marker=b'\\subsection{Filesystem Reuse in Applications}'
    assert raw.count(marker)==1
    prefix=raw.split(marker,1)[0]
    result=dict(status='complete',files=records,canonical_prefix_sha256=hashlib.sha256(prefix).hexdigest(),
        scope='Exact prior publication/documents, including canonical text before Section 6.5. No historical experiment deleted or relabeled.')
    (out/'identity.json').write_text(json.dumps(result,indent=2)+'\n');print('archived',len(records),'files; prior-section prefix',result['canonical_prefix_sha256'])
if __name__=='__main__':main()
