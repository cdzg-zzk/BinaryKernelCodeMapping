#!/usr/bin/env python3
"""Bounded XZ diagnosis using exact blocks reached in existing SIF images.

New output only. No module loading, root operations or historical modifications.
Captured/instrumented code is never used as a timed decoder.
"""
import argparse, ctypes as C, hashlib, json, lzma, os, random, shlex
import shutil, statistics, subprocess, sys
from pathlib import Path

ROOT=Path('/home/zzk/BinaryKernelCodeMapping')
SECTION=ROOT/'test/section65'
BASE=SECTION/'build/squashfs/refine-xz-01'
LINUX=SECTION/'build/native/linux-5.15.198'
KDIR=SECTION/'build/native/kernel'
SOURCE=Path(__file__).resolve().parent
OBJECTS=['xz_dec_stream','xz_dec_lzma2','xz_dec_bcj','xz_support']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value): p.write_text(json.dumps(value,indent=2)+'\n')
def run(cmd,log,cwd=None):
    log.write(shlex.join(map(str,cmd))+'\n');log.flush()
    subprocess.run(list(map(str,cmd)),cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)

def build(out):
    binaries={}
    with (out/'build.log').open('w') as log:
        # Instrument only the private boundary to extract real decoder inputs.
        capture=out/'capture';capture.mkdir()
        shutil.copy2(BASE/'xz-user-source/posix_io.c',capture/'posix_io.c')
        flags=['-O2','-g','-fPIC','-DVKSO_SQ_SHARED_LZ4','-DVKSO_SQ_SHARED_XZ',
               '-DVKSO_SQ_DIRECT_DECODE','-I'+str(BASE),'-I'+str(capture),'-I'+str(BASE/'xz-user-source'),
               '-I'+str(SECTION/'build/squashfs/deps/usr/include')]
        run(['gcc',*flags,'-c',SOURCE/'capture.c','-o',capture/'posix.o'],log)
        run(['gcc','-shared','-Wl,-Bsymbolic','-o',capture/'bridge.so',BASE/'user_bridge.o',capture/'posix.o',
             '-lz','-Wl,-l:libzstd.so.1','-Wl,-l:liblzo2.so.2'],log)
        for variant in ['prepared','jump-tables','small-memory','dictionary-word','dictionary-word-o3','dictionary-word-branchless']:
            target=out/variant;target.mkdir()
            for p in BASE.iterdir():
                if p.is_file() and p.suffix in ('.c','.h'):shutil.copy2(p,target/p.name)
            if variant=='small-memory':
                p=target/'xz_private.h';text=p.read_text()
                # Only constant-size accesses can become ordinary scalar instructions;
                # all variable-size operations keep the existing domain service.
                for op,slot,args,call in [('memcpy','copy','d,s,n','d,s,n'),('memset','set','d,c,n','d,c,n'),
                                         ('memcmp','compare','a,b,n','a,b,n')]:
                    before=f'#define {op}({args}) (sq_xz_services.{slot})({call})'
                    after=f'#define {op}({args}) (__builtin_constant_p(n) && (n)<=16 ? __builtin_{op}({call}) : (sq_xz_services.{slot})({call}))'
                    assert before in text;text=text.replace(before,after)
                p.write_text(text)
            if variant.startswith('dictionary-word'):
                p=target/'xz_dec_lzma2.c';text=p.read_text()
                before='\tdo {\n\t\tdict->buf[dict->pos++] = dict->buf[back++];\n\t\tif (back == dict->end)\n\t\t\tback = 0;\n\t} while (--left > 0);'
                after=(SOURCE/'dictionary_word.inc').read_text().rstrip()
                assert text.count(before)==1
                p.write_text(text.replace(before,after))
            if variant=='dictionary-word-branchless':
                p=target/'xz_dec_lzma2.c';text=p.read_text()
                start=text.index('static __always_inline int rc_bit(')
                end=text.index('\n}\n',start)+3
                p.write_text(text[:start]+(SOURCE/'range_branchless.inc').read_text()+text[end:])
            for obj in OBJECTS:
                if variant=='prepared':shutil.copy2(BASE/(obj+'.o'),target/(obj+'.o'));continue
                cmd=shlex.split((BASE/('.'+obj+'.o.cmd')).read_text().splitlines()[0].split(' := ',1)[1])
                cmd=cmd[:cmd.index('-c')]
                cmd=[x for x in cmd if not x.startswith('-Wp,-MMD')]
                cmd=[x.replace(str(BASE),str(target)) for x in cmd]
                if variant=='jump-tables':cmd=[x for x in cmd if x!='-fno-jump-tables']+['-fjump-tables']
                if variant=='dictionary-word-o3':cmd=[x for x in cmd if x not in ['-O2','-Os']]+['-O3']
                run(cmd+['-c',target/(obj+'.c'),'-o',target/(obj+'.o')],log,KDIR)
            binary=target/'bench'
            run(['gcc','-O2','-I'+str(target),'-I'+str(SECTION/'build/squashfs/deps/usr/include'),
                 SOURCE/'bench.c',*[target/(o+'.o') for o in OBJECTS],'-lz','-Wl,-l:liblzma.so.5',
                 '-o',binary],log)
            binaries[variant]=str(binary)
        normal=out/'ordinary';normal.mkdir()
        for name in ['xz_dec_stream.c','xz_dec_lzma2.c','xz_dec_bcj.c','xz_crc32.c','xz_private.h','xz_stream.h','xz_lzma2.h']:
            shutil.copy2(LINUX/'lib/xz'/name,normal/name)
        shutil.copy2(LINUX/'include/linux/xz.h',normal/'sq_xz_api.h')
        shutil.copy2(SOURCE/'xz_config.h',normal/'xz_config.h')
        run(['gcc','-O2','-DORDINARY_XZ','-DXZ_INTERNAL_CRC32','-I'+str(normal),
             '-I'+str(SECTION/'build/squashfs/deps/usr/include'),SOURCE/'bench.c',
             *[normal/(o+'.c') for o in OBJECTS[:3]],normal/'xz_crc32.c',
             '-lz','-Wl,-l:liblzma.so.5','-o',normal/'bench'],log)
        binaries['ordinary']=str(normal/'bench')
        run(['gcc','-O2','-DORDINARY_XZ','-DXZ_INTERNAL_CRC32','-I'+str(normal),
             '-I'+str(SECTION/'build/squashfs/deps/usr/include'),SOURCE/'bench.c',
             *[normal/(o+'.c') for o in OBJECTS[:3]],SOURCE/'crc_zlib.c',
             '-lz','-Wl,-l:liblzma.so.5','-o',normal/'bench-matched-crc'],log)
        binaries['ordinary-matched-crc']=str(normal/'bench-matched-crc')
    save(out/'binaries.json',binaries)
    return binaries

def capture(out):
    core=ROOT/'test/evaluation-local/runs/iso9660/squash-refine-application-final-xz-01/libsq-materialized.so'
    C.CDLL(str(core),mode=C.RTLD_GLOBAL)
    api=C.CDLL(str(out/'capture/bridge.so'),mode=C.RTLD_GLOBAL)
    signatures={
        'sq_open_image':([C.c_char_p,C.c_uint64],C.c_void_p),'sq_close_image':([C.c_void_p],None),
        'sq_root_inode':([C.c_void_p],C.c_void_p),
        'sq_lookup_child':([C.c_void_p,C.c_char_p,C.c_uint],C.c_void_p),
        'sq_read_inode_data':([C.c_void_p,C.c_void_p,C.c_size_t,C.c_uint64],C.c_ssize_t),
        'sq_diag_phase':([C.c_char_p,C.c_char_p],None)}
    for name,(args,ret) in signatures.items():getattr(api,name).argtypes=args;getattr(api,name).restype=ret
    blocks=out/'blocks';blocks.mkdir()
    inputs=[];checks=[]
    for label,dirname,files in [
        ('app','application-images-01',['opt/stream-data/compressible.bin','opt/stream-data/random.bin']),
        ('python','heldout-python-images-01',['usr/lib/python3.10/os.py','usr/lib/python3.10/pathlib.py','usr/lib/python3.10/_pydecimal.py'])]:
        imagebase=SECTION/'build/squashfs'/dirname
        meta=json.loads((imagebase/'images.json').read_text())
        case=next(c for c in meta['cases'] if c['compressor']=='xz')
        image=Path(case['image']);assert sha(image)==case['sha256']
        inputs.append(dict(image=str(image),sha256=case['sha256'],offset=case['offset']))
        api.sq_diag_phase(str(blocks).encode(),(label+'-mount').encode())
        im=api.sq_open_image(str(image).encode(),case['offset']);assert im
        try:
            for fi,name in enumerate(files):
                api.sq_diag_phase(str(blocks).encode(),f'{label}-{fi}-lookup'.encode())
                inode=api.sq_root_inode(im)
                for part in name.split('/'):
                    inode=api.sq_lookup_child(inode,part.encode(),len(part));assert inode,name
                ref=imagebase/'rootfs'/name;size=ref.stat().st_size
                positions=[0,(size//2//131072)*131072,max(0,(size-1)//131072*131072)] if label=='app' else list(range(0,size,131072))
                for k,offset in enumerate(sorted(set(positions))):
                    phase=f'{label}-{fi}-data-{k}'
                    api.sq_diag_phase(str(blocks).encode(),phase.encode())
                    buf=C.create_string_buffer(131072)
                    n=api.sq_read_inode_data(inode,buf,len(buf),offset);assert n>=0
                    with ref.open('rb') as f:f.seek(offset);expected=f.read(len(buf))
                    assert buf.raw[:n]==expected,(name,offset,n)
                    checks.append(dict(file=name,offset=offset,bytes=n,phase=phase,
                                       decoder_blocks=len(list(blocks.glob(phase+'-*.xz')))))
        finally:api.sq_close_image(im)
    records=[]
    for p in sorted(blocks.glob('*.xz')):
        raw=p.with_suffix('.raw');assert lzma.decompress(p.read_bytes())==raw.read_bytes()
        records.append(dict(name=p.stem,xz=str(p),raw=str(raw),input_bytes=p.stat().st_size,
                            output_bytes=raw.stat().st_size,input_sha256=sha(p),output_sha256=sha(raw)))
    save(out/'capture.json',dict(images=inputs,read_checks=checks,blocks=records,core_sha256=sha(core)))
    return records

def measure(out,binaries,records,requested=None):
    # Fixed selection: first captured data block per requested offset, plus first mount block.
    selected=[r for r in records if r['name'].endswith('-000') and ('-data-' in r['name'] or '-mount-' in r['name'])]
    assert selected
    conditions=[('library',binaries['prepared'],'library'),('ordinary-single',binaries['ordinary'],'single'),
                ('ordinary-prealloc',binaries['ordinary'],'prealloc'),('prepared-single',binaries['prepared'],'single'),
                ('prepared-prealloc',binaries['prepared'],'prealloc'),('jump-tables',binaries['jump-tables'],'single'),
                ('small-memory',binaries['small-memory'],'single'),
                ('dictionary-word',binaries['dictionary-word'],'single'),
                ('dictionary-word-prealloc',binaries['dictionary-word'],'prealloc'),
                ('dictionary-word-o3',binaries['dictionary-word-o3'],'single'),
                ('dictionary-word-branchless',binaries['dictionary-word-branchless'],'single'),
                ('ordinary-matched-crc',binaries['ordinary-matched-crc'],'single')]
    if requested:
        assert set(requested)<=set(c[0] for c in conditions)
        conditions=[c for c in conditions if c[0] in requested]
        assert 'prepared-single' in requested
    rng=random.Random(653001);rows=[]
    for block in range(5):
        cells=[(r,c) for r in selected for c in conditions];rng.shuffle(cells)
        for record,(name,binary,mode) in cells:
            cmd=['taskset','-c','1',binary,mode,record['xz'],record['raw'],'150']
            value=json.loads(subprocess.check_output(cmd,text=True))
            value.update(block=block,input=record['name'],variant=name)
            rows.append(value)
            with (out/'samples.jsonl').open('a') as f:f.write(json.dumps(value)+'\n')
        print('diagnostic block',block+1,'of 5 complete',flush=True)
    summary=[]
    for record in selected:
        for name,_,_ in conditions:
            paired=[]
            for block in range(5):
                cell=[r for r in rows if r['input']==record['name'] and r['block']==block]
                numerator=next(r for r in cell if r['variant']==name)
                denominator=next(r for r in cell if r['variant']=='prepared-single')
                paired.append(numerator['cpu_seconds']/denominator['cpu_seconds'])
            summary.append(dict(input=record['name'],variant=name,median_paired_cpu_ratio=statistics.median(paired),ratios=paired))
    save(out/'result.json',dict(status='complete',scope='Fixed-input diagnostic, not application or shared-PFN performance',
         observations=len(rows),selected_blocks=selected,conditions=conditions,summary=summary,
         shared_path='Requires separately registered owner; not represented by these copied/user results'))
    print(json.dumps(summary,indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--stage',choices=['all','capture','measure'],default='all');p.add_argument('--conditions',nargs='+');a=p.parse_args()
    out=a.output.resolve()
    if a.stage=='all':out.mkdir(parents=True,exist_ok=False);binaries=build(out)
    else:binaries=json.loads((out/'binaries.json').read_text())
    records=capture(out) if a.stage!='measure' else json.loads((out/'capture.json').read_text())['blocks']
    measure(out,binaries,records,a.conditions)
if __name__=='__main__':main()
