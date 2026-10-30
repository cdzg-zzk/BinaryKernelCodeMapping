#!/usr/bin/env python3
"""Give normal/relaxed native controls the identical dictionary optimization.

No shared owner or user service bindings: matching kernel decoder sources are
linked inside each reference module, using its ordinary native kernel services.
The host kernel and boot configuration remain unchanged.
"""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping')
SECTION=ROOT/'test/section65';HERE=Path(__file__).resolve().parent
BASE=ROOT/'test/evaluation-local/runs/iso9660/squash-bounded-controls-build-01'
LINUX=SECTION/'build/native/linux-5.15.198'

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);rows={}
    names=['xz_dec_init','xz_dec_reset','xz_dec_run','xz_dec_end','xz_dec_lzma2_create','xz_dec_lzma2_reset',
           'xz_dec_lzma2_run','xz_dec_lzma2_end','xz_dec_bcj_create','xz_dec_bcj_reset','xz_dec_bcj_run']
    for policy in ['normal','relaxed']:
        target=out/('native-word-'+policy);shutil.copytree(BASE/('native-small-'+policy),target)
        for name in ['xz_private.h','xz_lzma2.h','xz_stream.h']:
            shutil.copy2(LINUX/'lib/xz'/name,target/name)
        (target/'native_xz_names.h').write_text(''.join(f'#define {n} reference_{n}\n' for n in names))
        for stem in ['xz_dec_stream','xz_dec_lzma2','xz_dec_bcj']:
            shutil.copy2(LINUX/'lib/xz'/(stem+'.c'),target/(stem+'.c'))
        path=target/'xz_dec_lzma2.c';text=path.read_text()
        old='\tdo {\n\t\tdict->buf[dict->pos++] = dict->buf[back++];\n\t\tif (back == dict->end)\n\t\t\tback = 0;\n\t} while (--left > 0);'
        assert text.count(old)==1
        path.write_text(text.replace(old,(HERE/'dictionary_word.inc').read_text().rstrip()))
        make=target/'Makefile';text=make.read_text()
        text+='\nsq_reference-y += xz_dec_stream.o xz_dec_lzma2.o xz_dec_bcj.o\n'
        for obj in ['xz_dec_stream.o','xz_dec_lzma2.o','xz_dec_bcj.o','xz_wrapper.o']:
            text+=f'CFLAGS_{obj} += -include {target}/native_xz_names.h\n'
        make.write_text(text)
        with (out/(policy+'-build.log')).open('w') as log:
            subprocess.run(['make','-C',SECTION/'build/native/kernel','M='+str(target),'-j2','modules'],stdout=log,stderr=subprocess.STDOUT,check=True)
        symbols=subprocess.check_output(['nm',target/'sq_reference.ko'],text=True)
        assert ' T reference_xz_dec_run' in symbols
        undefined=subprocess.check_output(['nm','-u',target/'sq_reference.ko'],text=True)
        assert not any('xz_dec_' in line for line in undefined.splitlines())
        rows['native-word-'+policy]=dict(module=str(target/'sq_reference.ko'),filesystem='sqreference')
        (target/'optimization.json').write_text(json.dumps(dict(status='built',policy=policy,
            scope='Ordinary native module with identical word-copy algorithm, kernel allocator/memory/CRC services; no VKSO service binding',
            body_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            module_sha256=hashlib.sha256((target/'sq_reference.ko').read_bytes()).hexdigest(),
            undefined=undefined,decoder_symbols=[l for l in symbols.splitlines() if 'reference_xz_' in l]),indent=2)+'\n')
    (out/'references.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
