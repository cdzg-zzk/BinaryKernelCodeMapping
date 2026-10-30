#!/usr/bin/env python3
"""Preserve complete measurement records and text logs without deployment binaries."""
import argparse,gzip,hashlib,io,json,shutil,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RUNS=Path('/var/tmp/vkso-section65-optimization-20261030-hBcg9Y')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def allowed(p):
    return not p.is_symlink() and p.is_file() and (p.suffix in {'.json','.jsonl','.log','.txt','.md','.csv','.py','.c','.h','.sh','.conf','.gdb','.patch','.diff','.cmd','.inc','.S'} or p.name in {'Makefile','Kbuild','.config'})
def archive(folder,source_files,output):
    output.parent.mkdir(parents=True,exist_ok=True);records=[]
    with output.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
        for f in sorted(set(source_files)):
            data=f.read_bytes();name=str(f.relative_to(folder));info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;tar.addfile(info,io.BytesIO(data))
            records.append(dict(source=str(f),member=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        data=(json.dumps(dict(root=str(folder),files=records),indent=2)+'\n').encode();info=tarfile.TarInfo('MANIFEST.json');info.size=len(data);info.mode=0o644;tar.addfile(info,io.BytesIO(data))
    return dict(path=str(output),sha256=sha(output),files=len(records),uncompressed_bytes=sum(r['bytes'] for r in records),compressed_bytes=output.stat().st_size)
def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    audit=read(a.analysis/'completion-audit.json');assert audit['status']=='complete'
    queue=read(HERE/'recovered-formal-queue.json');manifest=dict(status='complete',scope='Raw measurement and text-log archives plus generated-source snapshots; binaries and images remain at hashed original server paths.',archives=[],analysis_files=[],campaigns=[])
    for job in queue:
        run=Path(job['result']).parent;target=out/'campaigns'/(job['name']+'.tar.gz')
        item=archive(run,[f for f in run.rglob('*') if allowed(f)],target);item['path']=str(target.relative_to(out));manifest['archives'].append(item)
        manifest['campaigns'].append(dict(name=job['name'],kind=job['kind'],archive=item['path'],original=str(run)))
    # Entire interrupted native group and recovery/queue logs remain separate.
    diagnostic_names=['squash-data48-native-final-03','data48-recovery-01','data48-confirmation-queue-01','data48-confirmation-queue-02','data48-postprocess-01','data48-postprocess-02',
        'data48-functional-01','data48-bcj-01','data48-guest-01','data48-simultaneous-01','data48-cache-sanitize-01','data48-lifetime-01','data48-metadata-work-01','data48-minimal-01','data48-resource-queue-01']
    diagnostic_names.extend(Path(j['result']).parent.name for j in read(HERE/'resource-queue.json'))
    for name in dict.fromkeys(diagnostic_names):
        folder=RUNS/name;assert folder.is_dir(),folder
        target=out/'support'/(name+'.tar.gz');item=archive(folder,[f for f in folder.rglob('*') if allowed(f)],target);item['path']=str(target.relative_to(out));manifest['archives'].append(item)
    # Materialized final owner/adapter sources and actual build configuration.
    folder=RUNS/'builds/data-cache-controls-02/data-48';target=out/'source/final-build.tar.gz'
    item=archive(folder,[f for f in folder.rglob('*') if allowed(f)],target);item['path']=str(target.relative_to(out));manifest['archives'].append(item)
    reg=read(HERE/'recovered-registration.json');manifest['frozen_input_identities']=reg['identities']
    frozen_text=[Path(n).resolve() for n in reg['identities'] if allowed(Path(n))]
    for config in [ROOT/'test/section65/build/native/kernel/.config',ROOT/'test/section65/build/native/linux-5.15.198/.config']:
        if config.is_file():frozen_text.append(config.resolve())
    target=out/'source/frozen-text-inputs.tar.gz';item=archive(Path('/'),frozen_text,target)
    item['path']=str(target.relative_to(out));manifest['archives'].append(item)
    for f in sorted(a.analysis.rglob('*')):
        if not allowed(f):continue
        dest=out/'analysis'/f.relative_to(a.analysis);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
        manifest['analysis_files'].append(dict(source=str(f),path=str(dest.relative_to(out)),sha256=sha(dest)))
    for name in ['recovered-formal-queue.json','recovered-registration.json','formal-queue.json','registration.json','SELECTION.md','CACHE_PROTOCOL.md']:
        dest=out/'registration'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/name,dest)
        manifest['analysis_files'].append(dict(source=str(HERE/name),path=str(dest.relative_to(out)),sha256=sha(dest)))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(len(manifest['archives']),'archives;',sum(r['compressed_bytes'] for r in manifest['archives']),'compressed bytes')
if __name__=='__main__':main()
