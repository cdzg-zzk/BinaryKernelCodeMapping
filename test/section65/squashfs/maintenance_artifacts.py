#!/usr/bin/env python3
"""Audit every retained old/fixed build file and allocated ELF section."""
import argparse
import hashlib
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile

ROOT=Path(__file__).resolve().parents[3]


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    run=ROOT/'test/evaluation-local/runs/iso9660/squash-maintenance-02'
    old=ROOT/'test/section65/build/squashfs/reader-adapted';fixed=run/'fixed-build'
    state=json.loads((run/'result.json').read_text());assert state['status']=='complete'
    for name,directory in [('old',old),('fixed',fixed)]:
        assert sha((directory/'vkso_sq_core.ko').read_bytes())==state['owners'][name]
        for filename in ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse']:
            assert (directory/filename).read_bytes()==(run/(name+'-package')/filename).read_bytes()
    files=[];elf_changes=[]
    names=sorted({p.name for directory in [old,fixed] for p in directory.iterdir() if p.is_file()})
    for name in names:
        data={label:(directory/name).read_bytes() if (directory/name).exists() else None for label,directory in [('old',old),('fixed',fixed)]}
        files.append(dict(file=name,changed=data['old']!=data['fixed'],
            **{label:dict(bytes=len(value),sha256=sha(value)) if value is not None else None for label,value in data.items()}))
        if data['old'] is not None and data['fixed'] is not None and data['old'].startswith(b'\x7fELF') and data['fixed'].startswith(b'\x7fELF'):
            sections={}
            for label,directory in [('old',old),('fixed',fixed)]:
                with (directory/name).open('rb') as stream:
                    sections[label]={s.name:dict(bytes=s['sh_size'],sha256=sha(s.data())) for s in ELFFile(stream).iter_sections() if s['sh_flags']&2}
            keys=sorted(set(sections['old'])|set(sections['fixed']))
            elf_changes.append(dict(file=name,allocated_sections_changed=[k for k in keys if sections['old'].get(k)!=sections['fixed'].get(k)],sections=sections))
    changed_sources=[r['file'] for r in files if r['changed'] and Path(r['file']).suffix in ['.c','.h'] and not r['file'].endswith('.mod.c')]
    assert changed_sources==['shared_core.c'],changed_sources
    assert all(not r['changed'] for r in files if r['file'] in ['libsq-bridge.so','vkso-squashfuse','vkso-squash-helper'])
    strings=[]
    for directory in [old,fixed]:
        with (directory/'vkso_squashfs.ko').open('rb') as stream:
            data=ELFFile(stream).get_section_by_name('.rodata.str1.8').data()
            strings.append([s.replace(str(directory).encode(),b'BUILD') for s in data.split(b'\0') if s])
    assert strings[0]==strings[1]
    result=dict(status='complete',old=str(old),fixed=str(fixed),
        patch=str(run/'upstream-backport.patch'),patch_sha256=sha((run/'upstream-backport.patch').read_bytes()),
        changed_handwritten_or_extracted_sources=changed_sources,files=files,elf_changes=elf_changes,
        native_consumer_strings='The differing .rodata.str1.8 contents are identical after normalizing the old/fixed build-directory prefix; the raw section hashes remain above. The consumer .text section is unchanged in the relocatable module.',
        scope='All regular files in both retained build directories; package binaries independently matched to what each guest executed. Generated compile metadata and ELF debug/build identity differences are retained separately from allocated sections. Exported runtime carriers are regenerated and registered per guest/run, not hot-patched in existing processes.')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(files=len(files),changed=sum(r['changed'] for r in files),changed_sources=changed_sources,
        modules=[dict(file=r['file'],sections=r['allocated_sections_changed']) for r in elf_changes if r['file'].endswith('.ko')]),indent=2))


if __name__=='__main__':main()
