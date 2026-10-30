#!/usr/bin/env python3
"""Package Section 6.5 sources and selected evidence without runtime image trees."""
from pathlib import Path
import hashlib
import json
import os
import zipfile

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
NAME='vkso-section65-handoff-20261030-01'
OUT=ROOT/'test/evaluation-local'/f'{NAME}.zip'
TEXT={'.py','.c','.h','.cpp','.hpp','.md','.txt','.json','.jsonl','.csv','.tex','.bib','.sh','.patch','.cmd','.config','.conf','.yaml','.yml','.asm','.dis','.disasm','.gdb','.log'}
SPECIAL={'Makefile','Module.symvers','modules.order','.config','stdout','stderr'}
SKIP={'__pycache__','.git','.codegraph','.aws','.codex','node_modules','venv','rootfs','payload','init-overlay','cache','tmp','native-mount','mount','mnt','fixture','old-package','fixed-package','fixed-build','loader-aliases'}
files={};omitted=[]
def sha(data):return hashlib.sha256(data).hexdigest()
def add(path,category):
    path=Path(path)
    assert path.is_file() and not path.is_symlink(),path
    path.resolve().relative_to(ROOT)
    files[str(path.relative_to(ROOT))]=(path,category)
def walk(base,category,all_files=False,raw=False):
    base=Path(base)
    assert base.is_dir(),base
    for folder,dirs,names in os.walk(base,followlinks=False):
        dirs[:]=[n for n in dirs if n not in SKIP and not (Path(folder)/n).is_symlink()
                 and not n.startswith('root-') and not n.startswith('rootfs-')]
        for n in names:
            f=Path(folder)/n
            if f.is_symlink():continue
            if not all_files and f.suffix not in TEXT and n not in SPECIAL:continue
            if raw and (n in {'native-original.json','native-before.json','native-after.json','workload-oracles.json'} or f.stat().st_size>4*1024*1024):
                omitted.append(dict(path=str(f.relative_to(ROOT)),bytes=f.stat().st_size,sha256=sha(f.read_bytes()),reason='Bulk per-file manifest or oversized diagnostic; aggregate/oracle checks and all timing samples are included.'))
                continue
            if raw and f.stat().st_size==0:continue
            add(f,category)

def main():
    assert not OUT.exists(),OUT
    for name in ['AGENTS.md','README.md']:add(ROOT/name,'project-context')
    section=ROOT/'test/section65'
    for f in section.iterdir():
        if f.is_file() and f.suffix in TEXT:add(f,'section-entry-and-history')
    for d in ['squashfs','native','lkl','upstream']:
        walk(section/d,'source-and-protocol')
    walk(ROOT/'make_dll','general-exporter-source')
    walk(ROOT/'page_cache_replace','registration-source')
    for d in ['refined-analysis-01','refinement-reuse-audit-03','refinement-baseline-audit-02',
              'improvement-analysis-01','improvement-xz-attribution-analysis-01',
              'improvement-loader-analysis-01','improvement-singlecpu-analysis-01']:
        walk(section/'build/squashfs'/d,'analysis-and-costs')
    walk(section/'build/squashfs/evaluation-refined-02','final-source-freeze',all_files=True)
    for d in ['refine-xz-01','evaluation-improved-01/build','refine-decoder-controls-01']:
        walk(section/'build/squashfs'/d,'evaluated-source-build')
        base=section/'build/squashfs'/d
        for f in base.rglob('*'):
            if f.is_file() and not f.is_symlink() and (f.suffix in {'.ko','.so','.o'} or f.name in {'vkso-squashfuse','vkso-squash-helper'}):add(f,'evaluated-binary')
    for n in ['filesystem-section.tex','filesystem-section-preview.tex','filesystem-section-preview.pdf',
              'plot_filesystem.py','plot_filesystem_improved.py','plot_filesystem_refined.py',
              'build_filesystem_section.py','evaluation-requirements.txt','Makefile',
              'paper_content/sections/06-evaluation.tex','paper_content/references.bib','paper_content/Paper Draft.md',
              'notes/section65-alignment.md']:
        add(ROOT/'paper'/n,'paper')
    walk(ROOT/'paper/design','paper-design')
    walk(ROOT/'paper/build/section65-refined-figures-01','figures',all_files=True)
    walk(ROOT/'paper/build/section65-composed-publication-01','predecessor-publication',all_files=True)
    add(ROOT/'paper/data/section65/render-qa.json','publication-verification')
    for f in (ROOT/'paper/tables').glob('filesystem*.tex'):add(f,'paper-tables')
    raw=ROOT/'test/evaluation-local/runs/iso9660'
    queue=json.loads((section/'squashfs/refinement/formal-queue.json').read_text())
    current={Path(j['result']).parent.name for j in queue}
    current.update(Path(j['result']).parent.name for j in json.loads((section/'squashfs/refinement/resource-queue.json').read_text()))
    current.update(n for n in [
        'squash-refine-xz-functional-01','squash-refine-xz-guest-01','squash-refine-xz-execution-01',
        'squash-refine-xz-native-calls-01','squash-refine-xz-bcj-01','squash-refine-xz-bcj-02',
        'squash-refine-hardening-01','squash-refine-hardening-02','squash-refine-metadata-work-01',
        'squash-refine-minimal-deployment-01','squash-refine-heldout-gzip-03',
        'squash-refine-interruption-recovery-01','squash-refine-formal-queue-01','squash-refine-formal-recovery-01',
        'squash-refine-resource-queue-01','squash-refine-resource-queue-02',
        'squash-refine-postprocess-queue-01','squash-refine-postprocess-queue-02','squash-maintenance-02'])
    for q in ['pilot-queue.json','decoder-pilot-queue.json']:
        current.update(Path(j['result']).parent.name for j in json.loads((section/'squashfs/refinement'/q).read_text()))
    for name in sorted(current):walk(raw/name,'raw-evidence',raw=True)
    walk(raw/'maintenance-oneshot-01/evidence/debug','iso9660-debug-evidence',raw=True)
    for name in ['README.md','result.json']:
        f=raw/'maintenance-oneshot-01'/name
        if f.exists():add(f,'iso9660-debug-evidence')
    linux=section/'build/native/linux-5.15.198'
    walk(linux/'lib/xz','original-linux-xz')
    for p in ['include/linux/xz.h','fs/squashfs/xz_wrapper.c']:add(linux/p,'original-linux-xz')
    add(section/'build/native/kernel/.config','kernel-config')
    add(section/'build/lkl/linux-6.12/fs/squashfs/xz_wrapper.c','lkl-reference')
    add(section/'build/lkl/linux-6.12/tools/lkl/lklfuse.c','lkl-reference')
    external=[]
    for d in ['native-images-01','application-images-01','heldout-python-images-01','refine-scale-images-01','simultaneous-xz-images-01']:
        base=section/'build/squashfs'/d
        for f in base.iterdir():
            if f.is_file() and f.suffix in {'.json','.log','.txt'}:add(f,'input-manifests')
            elif f.is_file() and f.suffix in {'.sif','.squashfs'}:
                external.append(dict(path=str(f.relative_to(ROOT)),bytes=f.stat().st_size,available_in_original_workspace=True,identity='Use the included images.json in the same directory.'))
    for d,why in [
        ('test/section65/build/native/linux-5.15.198','Complete Linux source tree; only XZ sources and selected reference wrapper included.'),
        ('test/section65/build/native/kernel','Configured kernel build/SDK; .config included.'),
        ('test/section65/build/lkl','Full LKL kernel/library/toolchain; generators, selected reference and evidence included.'),
        ('test/section65/build/squashfs/apptainer','Apptainer, bundled stock backend and runtime libraries.'),
        ('test/section65/build/squashfs/deps','Compression/FUSE build dependencies.'),
        ('test/evaluation-local/packages/iso9660-native-optimized-20261029','Matching support package, vmlinux, manager, krg and modules.'),
        ('paper/build/section65-plot-env-02','Plotting virtual environment; requirements/script included.'),
        ('paper/build/tools','Tectonic executable and build tools.')]:
        external.append(dict(path=d,available_in_original_workspace=(ROOT/d).exists(),reason=why))
    for name in ['package.json','build.json','reproduction.json','README.md']:
        f=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029'/name
        if f.exists():add(f,'runtime-package-manifest')
    expected=0
    for j in queue:
        parent=Path(j['result']).parent
        sample=parent/('samples.jsonl' if j['kind'].startswith('native') else 'benchmark/samples.jsonl')
        assert str(sample) in files,sample
        expected+=len((ROOT/sample).read_text().splitlines())
    assert expected==6540 and len(queue)==30
    (HERE/'EXTERNAL_ASSETS.json').write_text(json.dumps(dict(scope='Not a standalone bootable/runnable environment. Images, VM disks/initramfs, complete kernel/LKL SDKs and runtime installations omitted.',assets=external,omitted_bulk_evidence=omitted),indent=2)+'\n')
    entries=[]
    with zipfile.ZipFile(OUT,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for rel,(path,category) in sorted(files.items()):
            data=path.read_bytes();dest='repo/'+rel
            z.writestr(NAME+'/'+dest,data)
            entries.append(dict(path=dest,bytes=len(data),sha256=sha(data),category=category))
        for n in ['START_HERE.md','HANDOFF_PROMPT.md','HANDOFF_PROMPT.txt','CORE_FILES.md','EXTERNAL_ASSETS.json','verified-baseline.json','build_bundle.py']:
            data=(HERE/n).read_bytes();z.writestr(NAME+'/'+n,data)
            entries.append(dict(path=n,bytes=len(data),sha256=sha(data),category='handoff'))
        manifest=dict(status='complete',baseline='xz-composed-refined',scope='Core sources, all 30 final timing campaigns, selected functional/diagnostic/failure logs, analyses and publications; not all historical raw runs or full runtime assets.',
            formal_campaigns=30,formal_observations=expected,partial_interrupted_observations_retained=28,files=entries,
            omissions='Large runtime images/SDKs, extracted payload trees, bulk per-file native/oracle manifests, and empty successful logs. See EXTERNAL_ASSETS.json; unsuccessful nonempty logs are retained.')
        data=(json.dumps(manifest,indent=2)+'\n').encode();z.writestr(NAME+'/BUNDLE_MANIFEST.json',data)
        (HERE/'BUNDLE_MANIFEST.json').write_bytes(data)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
        for r in entries:assert sha(z.read(NAME+'/'+r['path']))==r['sha256']
    digest=sha(OUT.read_bytes());OUT.with_suffix('.zip.sha256').write_text(digest+'  '+OUT.name+'\n')
    report=dict(status='complete',archive=str(OUT.relative_to(ROOT)),archive_sha256=digest,
        archive_bytes=OUT.stat().st_size,files=len(entries)+1,uncompressed_payload_bytes=sum(r['bytes'] for r in entries),
        formal_campaigns=30,formal_observations=expected,manifest_hashes_verified=True,zip_crc_verified=True)
    (HERE/'PACKAGE_RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
