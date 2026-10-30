#!/usr/bin/env python3
"""Physical-backing decoder diagnostic, after all application timings are idle."""
import argparse, hashlib, json, os, random, shutil, statistics, subprocess, sys, traceback
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65';HERE=Path(__file__).resolve().parent
SUPPORT=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029'
sys.path.insert(0,str(SECTION/'squashfs'))
from check_fuse import observe

def main():
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert os.geteuid()==0
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);build=a.build.resolve()
    loaded=[];registered=False;library=None;rows=[];result=dict(status='running',scope='Fixed original SIF blocks, copied/shared dynamic harness; diagnostic, not complete-application timing')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def command(args,label,cwd=None):
        with (out/(label+'.log')).open('w') as log:subprocess.run(list(map(str,args)),cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    save()
    try:
        command(['gcc','-O2','-I'+str(build),HERE/'decoder_shared.c','-ldl','-lz','-o',out/'bench'],'build')
        for name in ['vkso_sq_core','vkso_squashfs','vkso_kernel_reader','page_cache_replace']:
            assert not (Path('/sys/module')/name).exists()
            command(['insmod',(build if name in ['vkso_sq_core','vkso_squashfs'] else SUPPORT/'modules')/(name+'.ko')],'load-'+name);loaded.append(name)
        carrier=out/'carrier';carrier.mkdir()
        for name in ['symbols.txt','shim.txt']:shutil.copy2(build/name,carrier/name)
        command([SUPPORT/'krg','build',SUPPORT/'vmlinux','--module',build/'vkso_sq_core.ko','-o',carrier/'out.krg'],'krg')
        command([sys.executable,ROOT/'make_dll/build_PIC_so.py','--symbols',carrier/'symbols.txt','--krg',carrier/'out.krg',
            '--ko',build/'vkso_sq_core.ko','--shim-list',carrier/'shim.txt','--vmlinux',SUPPORT/'vmlinux'],'export',carrier)
        library=next(carrier.glob('lib*.so')).resolve();before=library.read_bytes();plan=carrier/'page_mappings.txt'
        command([SUPPORT/'manager','replace',library,plan],'register',SUPPORT);registered=True
        copied=out/'libsq-materialized.so';copied.write_bytes(library.read_bytes())
        for v,core in [('copied',copied),('shared',library)]:
            command([sys.executable,HERE/'fuse_lifetime.py','--build',build,'--fixture',SECTION/'build/squashfs/optimization-cache-valid-01',
                '--output',out/('lifetime-'+v),'--core',core,'--plan',plan,*(['--expect-shared'] if v=='shared' else [])],v+'-lifetime')
        original=json.loads((SECTION/'build/squashfs/optimization-xz-diagnostic-04/result.json').read_text())
        selected=original['selected_blocks']
        for r in selected:
            for key in ['input','output']:
                file=r['xz' if key=='input' else 'raw'];assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==r[key+'_sha256']
        rng=random.Random(653002);observed=set()
        for block in range(5):
            cells=[(r,v,mode) for r in selected for v in ['copied','shared'] for mode in ['single','prealloc']];rng.shuffle(cells)
            for r,v,mode in cells:
                core=library if v=='shared' else copied;label=f'{block}-{r["name"]}-{v}-{mode}'
                with (out/(label+'.log')).open('w') as log:
                    child=subprocess.Popen(['taskset','-c','1',str(out/'bench'),str(core),str(build/'libsq-bridge.so'),mode,r['xz'],r['raw'],'150'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
                    try:
                        ready=json.loads(child.stdout.readline());assert ready['status']=='ready' and ready['pid']==child.pid
                        if (v,mode) not in observed:
                            observe(child.pid,core,plan,out/(label+'.log'),out/(v+'-'+mode+'-pfns.json'),v=='shared');observed.add((v,mode))
                        output,_=child.communicate('\n',timeout=30);assert child.returncode==0
                        sample=json.loads(output);assert sample['valid'];sample.update(block=block,input=r['name'],variant=v,mode=mode);rows.append(sample)
                        with (out/'samples.jsonl').open('a') as stream:stream.write(json.dumps(sample)+'\n')
                    finally:
                        if child.poll() is None:child.terminate();child.wait(timeout=10)
            print('shared decoder block',block+1,'complete',flush=True)
        summary=[]
        for r in selected:
            for mode in ['single','prealloc']:
                ratios=[]
                for block in range(5):
                    cell={s['variant']:s for s in rows if s['input']==r['name'] and s['mode']==mode and s['block']==block}
                    ratios.append(cell['shared']['cpu_seconds']/cell['copied']['cpu_seconds'])
                summary.append(dict(input=r['name'],mode=mode,median_paired_cpu_ratio=statistics.median(ratios),ratios=ratios))
        command([SUPPORT/'manager','restore',library,plan],'restore',SUPPORT);registered=False;assert library.read_bytes()==before
        result.update(status='complete',observations=len(rows),summary=summary,restored=True,
            mode_policy='SINGLE and PREALLOC: same contiguous full blocks, malloc services and zlib CRC. PREALLOC reset per repeat. Not native BIO/scatter execution.',
            identity_scope='Representative live process per backing/mode; same harness and materialized instructions, current owner. Earlier ordinary/library block controls are a separate diagnostic version.',
            binaries={n:hashlib.sha256((build/n).read_bytes()).hexdigest() for n in ['vkso_sq_core.ko','libsq-bridge.so']})
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:
        try:
            if registered:command([SUPPORT/'manager','restore',library,plan],'cleanup-restore',SUPPORT)
            for name in reversed(loaded):command(['rmmod',name],'unload-'+name)
            result['modules_unloaded']=True
        finally:save()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
