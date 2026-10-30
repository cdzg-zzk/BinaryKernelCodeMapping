#!/usr/bin/env python3
"""Build an isolated common-XZ word-copy candidate, preserving the baseline."""
import argparse, difflib, hashlib, json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path('/home/zzk/BinaryKernelCodeMapping')
SECTION = ROOT/'test/section65'
BASE = SECTION/'build/squashfs/refine-xz-01'
HERE = Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--bounded-cache',action='store_true');a=ap.parse_args()
    out=a.output.resolve();shutil.copytree(BASE,out)
    result=dict(status='building',baseline=str(BASE),scope='Common algorithm candidate, not a zero-body-edit port',
                compiler_policy='Baseline flags unchanged; O3/jump-table/small-memory experiments not selected',
                inherited_metadata='Baseline build/candidate/composition/source-cost ledgers are historical; optimization.json supersedes their hashes and zero-body-edit assertion')
    def save(): (out/'optimization.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        p=out/'xz_dec_lzma2.c';before=p.read_text()
        old='\tdo {\n\t\tdict->buf[dict->pos++] = dict->buf[back++];\n\t\tif (back == dict->end)\n\t\t\tback = 0;\n\t} while (--left > 0);'
        new=(HERE/'dictionary_word.inc').read_text().rstrip();assert before.count(old)==1
        after=before.replace(old,new);p.write_text(after)
        (out/'dictionary-word.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='baseline/xz_dec_lzma2.c',tofile='candidate/xz_dec_lzma2.c')))
        p=out/'Makefile';p.write_text(p.read_text().replace(str(BASE),str(out)))
        if a.bounded_cache:
            for name in ['user_bridge.c','fuse_frontend.c']:
                before=(out/'xz-user-source'/name).read_text();after=(HERE/name).read_text()
                (out/(name+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='baseline/'+name,tofile='candidate/'+name)))
                shutil.copy2(HERE/name,out/'xz-user-source'/name)
            result['metadata_cache']={'inode_budget':2048,'name_budget':4096,
                'extra_retention':'live pinned inode handles and open-directory listings',
                'identity':'image-local inode number plus disk location; no evictable name-target pointers'}
        with (out/'optimization-build.log').open('w') as log:
            subprocess.run(['make','-C',SECTION/'build/native/kernel','M='+str(out),'-j2','modules'],stdout=log,stderr=subprocess.STDOUT,check=True)
            subprocess.run([sys.executable,SECTION/'squashfs/build_user.py','--build',out,'--source-dir',out/'xz-user-source',
                '--directory-cache','--direct-decode','--shared-lz4','--shared-xz'],stdout=log,stderr=subprocess.STDOUT,check=True)
        objects=['xz_dec_stream.o','xz_dec_lzma2.o','xz_dec_bcj.o','xz_support.o']
        undefined={n:subprocess.check_output(['nm','-u',out/n],text=True) for n in objects}
        assert all(s.split()[-1]=='sq_xz_services' or s.split()[-1].startswith('vkso_xz_') for v in undefined.values() for s in v.splitlines())
        deps=subprocess.check_output(['readelf','-d',out/'libsq-bridge.so'],text=True)
        assert 'liblzma' not in deps and 'liblz4' not in deps
        result.update(status='built',upstream_body_edits=1,modified_function='dict_repeat',
            replaced_lines=len(old.splitlines()),replacement_lines=len(new.splitlines()),
            undefined=undefined,dependencies=deps,
            size=subprocess.check_output(['size',out/'vkso_sq_core.ko',out/'vkso_squashfs.ko'],text=True),
            hashes={n:sha(out/n) for n in ['xz_dec_lzma2.c','vkso_sq_core.ko','vkso_squashfs.ko','libsq-copy.so','libsq-bridge.so','vkso-squashfuse']})
    except BaseException as e:
        result.update(status='failed',error=repr(e));raise
    finally: save()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
