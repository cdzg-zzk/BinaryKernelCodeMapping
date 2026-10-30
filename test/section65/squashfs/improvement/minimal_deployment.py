#!/usr/bin/env python3
"""Actual user-only deployment without native consumer; copied survives full unload."""
import argparse,hashlib,json,os
from pathlib import Path
import pwd,shutil,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[4];HERE=ROOT/'test/section65/squashfs';SECTION=HERE.parent
SUPPORT=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--build',type=Path,required=True)
    p.add_argument('--image',type=Path,required=True);p.add_argument('--user',default='zzk');a=p.parse_args();assert os.geteuid()==0
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);account=pwd.getpwnam(a.user);os.chown(out,account.pw_uid,account.pw_gid)
    build=a.build.resolve();image=a.image.resolve();loaded=[];registered=False;library=None
    result=dict(status='running',scope='Real SIF application with only owner+registration resident; then identical copied image after all task modules unload.',
        binaries={n:hashlib.sha256((build/n).read_bytes()).hexdigest() for n in ['vkso_sq_core.ko','libsq-bridge.so','vkso-squashfuse']})
    write=lambda:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def command(argv,label,cwd=None):
        start=time.monotonic();args=list(map(str,argv))
        with (out/(label+'.log')).open('w') as log:
            r=subprocess.run(['/usr/bin/time','-v','-o',str(out/(label+'-resources.txt')),*args],stdout=log,stderr=subprocess.STDOUT,cwd=cwd,timeout=300)
        with (out/'stages.jsonl').open('a') as f:f.write(json.dumps(dict(stage=label,argv=args,returncode=r.returncode,wall_seconds=time.monotonic()-start))+'\n')
        r.check_returncode()
    def application(core,label):
        assert not Path('/sys/module/vkso_squashfs').exists()
        command(['runuser','-u',a.user,'--',sys.executable,HERE/'apptainer_preflight.py','--build',build,'--image',image,'--core',core,'--bridge',build/'libsq-bridge.so','--output',out/label],label,ROOT)
        evidence=json.loads((out/label/'result.json').read_text());assert evidence['status']=='pass'
        return evidence
    write()
    try:
        for name in ['vkso_sq_core','vkso_squashfs','page_cache_replace','vkso_kernel_reader']:assert not (Path('/sys/module')/name).exists()
        for name,path in [('vkso_sq_core',build/'vkso_sq_core.ko'),('vkso_kernel_reader',SUPPORT/'modules/vkso_kernel_reader.ko'),('page_cache_replace',SUPPORT/'modules/page_cache_replace.ko')]:
            command(['insmod',path],'load-'+name);loaded.append(name)
        carrier=out/'carrier';carrier.mkdir()
        for name in ['symbols.txt','shim.txt']:shutil.copy2(build/name,carrier/name)
        command([SUPPORT/'krg','build',SUPPORT/'vmlinux','--module',build/'vkso_sq_core.ko','-o',carrier/'out.krg'],'krg')
        command([sys.executable,ROOT/'make_dll/build_PIC_so.py','--symbols',carrier/'symbols.txt','--krg',carrier/'out.krg','--ko',build/'vkso_sq_core.ko',
            '--shim-list',carrier/'shim.txt','--vmlinux',SUPPORT/'vmlinux'],'export',carrier)
        library=next(carrier.glob('lib*.so')).resolve();before=library.read_bytes();plan=carrier/'page_mappings.txt'
        command([SUPPORT/'manager','replace',library,plan],'register',SUPPORT);registered=True
        copied=out/'libsq-materialized.so';start=time.monotonic();copied.write_bytes(library.read_bytes())
        result['copy_materialization']=dict(wall_seconds=time.monotonic()-start,bytes=copied.stat().st_size,sha256=hashlib.sha256(copied.read_bytes()).hexdigest())
        command(['rmmod','vkso_kernel_reader'],'remove-construction-observer');loaded.remove('vkso_kernel_reader')
        modules=[line.split() for line in Path('/proc/modules').read_text().splitlines() if line.split()[0] in loaded]
        result['runtime_modules']=[dict(name=r[0],reported_bytes=int(r[1])) for r in modules];write()
        result['shared_application']=application(library,'shared-application');write()
        command([SUPPORT/'manager','restore',library,plan],'restore',SUPPORT);registered=False;assert library.read_bytes()==before
        while loaded:command(['rmmod',loaded[-1]],'unload-'+loaded[-1]);loaded.pop()
        result['copied_modules_absent']=all(not (Path('/sys/module')/n).exists() for n in ['vkso_sq_core','vkso_squashfs','page_cache_replace','vkso_kernel_reader'])
        assert result['copied_modules_absent'];result['copied_application']=application(copied,'copied-after-unload')
        result.update(status='complete',restored=True,modules_unloaded=True)
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:
        try:
            if registered:command([SUPPORT/'manager','restore',library,plan],'cleanup-restore',SUPPORT)
            while loaded:command(['rmmod',loaded[-1]],'cleanup-unload-'+loaded[-1]);loaded.pop()
        except BaseException:result.update(status='failed',cleanup_error=traceback.format_exc());raise
        finally:write()
if __name__=='__main__':main()
