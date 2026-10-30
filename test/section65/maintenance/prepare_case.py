#!/usr/bin/env python3
"""Backport a real Joliet compatibility fix and create its named regression input.

The original source snapshot and previously collected evidence are not modified.
The image uses the long-Joliet extension discussed in the upstream change.
"""
import argparse
import difflib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
SECTION=HERE.parent
sys.path.insert(0,str(SECTION))
from adapt import once

def prepare_source(out):
    src=out/'fixed-source';src.mkdir(parents=True,exist_ok=True)
    for path in (SECTION/'upstream').iterdir():
        if path.is_file():shutil.copy2(path,src/path.name)
    upstream=(HERE/'upstream-long-joliet.patch').read_text()
    pieces=upstream.split('diff --git ')[1:]
    # Three source-file hunks apply unchanged. The header needs a context-only
    # backport because 5.15 does not contain the later dir-record validator.
    patch=''.join('diff --git '+p for p in pieces if not p.startswith('a/fs/isofs/isofs.h '))
    applied=subprocess.run(['patch','--batch','--fuzz=0','-p3','-d',str(src)],
        input=patch,text=True,capture_output=True)
    (out/'patch.log').write_text(applied.stdout+applied.stderr)
    applied.check_returncode()
    header=src/'isofs.h'
    old='int get_joliet_filename(struct iso_directory_record *, unsigned char *, struct inode *);'
    new='''/* The longest name is 111 UTF-16 units, at most 333 UTF-8 bytes.
 * Backported from Linux commit b8253bcf92d6365b20eea6465f5a93c9fc4aa029.
 */
#define JOLIET_NAME_MAX ((255 - sizeof(struct iso_directory_record)) / 2 * 3)
int get_joliet_filename(struct iso_directory_record *de, unsigned char *outname,
                       int outsize, struct inode *inode);'''
    header.write_text(once(header.read_text(),old,new))
    diff=[];changes=[]
    for name in ('dir.c','isofs.h','joliet.c','namei.c'):
        before=(SECTION/'upstream'/name).read_text().splitlines(True)
        after=(src/name).read_text().splitlines(True)
        delta=list(difflib.unified_diff(before,after,fromfile='a/'+name,tofile='b/'+name))
        diff+=delta
        changes.append(dict(file=name,added=sum(s.startswith('+') and not s.startswith('+++') for s in delta),
                            removed=sum(s.startswith('-') and not s.startswith('---') for s in delta)))
    (out/'backport.patch').write_text(''.join(diff))
    record=dict(upstream_commit='b8253bcf92d6365b20eea6465f5a93c9fc4aa029',
        source_url='https://github.com/torvalds/linux/commit/b8253bcf92d6365b20eea6465f5a93c9fc4aa029',
        upstream_title='isofs: return long Joliet names whole',
        base='Linux 5.15.198',backport_note='Header context adapted; three .c patches applied without fuzz',
        changed_files=changes,user_adapter_source_changed=False,fuse_frontend_source_changed=False)
    (out/'backport.json').write_text(json.dumps(record,indent=2)+'\n')
    return src

def fixture(out):
    tree=out/'fixture-tree';tree.mkdir(exist_ok=True)
    placeholder='a'*100
    payload=b'Long Joliet compatibility regression: same core, both execution domains.\n'
    (tree/placeholder).write_bytes(payload)
    image=out/'long-joliet.iso'
    command=[str(SECTION/'build/tools/usr/bin/genisoimage'),'-quiet','-input-charset','utf-8',
             '-J','-joliet-long','-o',str(image),str(tree)]
    subprocess.run(command,check=True)
    data=bytearray(image.read_bytes());block=2048;svd=None
    for i in range(16,32):
        off=i*block
        if data[off]==2 and data[off+1:off+6]==b'CD001':svd=off;break
    assert svd is not None
    root=int.from_bytes(data[svd+158:svd+162],'little')*block
    size=int.from_bytes(data[svd+166:svd+170],'little')
    off=root;patched=[];name='界'*100;encoded=name.encode('utf-16-be')
    while off<root+size:
        length=data[off]
        if not length:off=(off//block+1)*block;continue
        n=data[off+32];raw=bytes(data[off+33:off+33+n])
        if n>1 and raw.decode('utf-16-be').startswith('a'*90):
            assert len(encoded)<=n and 33+len(encoded)<=length
            data[off+32]=len(encoded)
            data[off+33:off+33+len(encoded)]=encoded
            patched.append(off)
        off+=length
    assert len(patched)==1,patched
    image.write_bytes(data)
    expected=dict(name=name,utf8_bytes=len(name.encode()),utf16_units=100,
        payload=payload.decode(),scope='long-Joliet extension used by existing image tools; beyond standard 64-unit Joliet limit',
        generation='Replace the 100-unit ASCII Joliet identifier in-place with 100 CJK units; sizes/extents/content unchanged',
        directory_record_offset=patched[0])
    (out/'expected.json').write_text(json.dumps(expected,ensure_ascii=False,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=SECTION/'build/maintenance')
    p.add_argument('--kdir',type=Path,default=Path('/usr/src/linux-headers-5.15.0-119-generic'))
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    src=prepare_source(out);fixture(out)
    subprocess.run(['python3',str(SECTION/'adapt.py'),'--source',str(src),
                    '--output',str(out/'fixed-adapted'),'--kdir',str(a.kdir)],check=True)
    subprocess.run(['python3',str(SECTION/'build_user.py'),'--build',str(out/'fixed-adapted'),
                    '--kdir',str(a.kdir)],check=True)
    print(json.dumps(dict(output=str(out),status='built')))

if __name__=='__main__':main()
