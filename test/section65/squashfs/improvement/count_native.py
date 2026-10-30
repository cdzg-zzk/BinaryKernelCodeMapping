#!/usr/bin/env python3
"""Count targeted native calls on fresh scans; instrumentation never supplies timings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import traceback

ROOT=Path(__file__).resolve().parents[4]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--counter',type=Path,required=True)
    p.add_argument('--build',type=Path,default=ROOT/'test/section65/build/squashfs/evaluation-fixed-01/build')
    a=p.parse_args();assert os.geteuid()==0
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    target=out/'mount';target.mkdir();loaded=[];counter_live=False;expected=None
    result=dict(status='running',scope='Dynamic native call counts, not timing. Probes are removed before any physical-sharing test.',cases=[])
    write=lambda:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,label):
        with (out/(label+'.log')).open('w') as log:subprocess.run(list(map(str,argv)),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    shutil.copy2(__file__,out/'runner.py');write()
    try:
        for name in ['vkso_sq_core','vkso_squashfs']:
            assert not (Path('/sys/module')/name).exists()
            run(['insmod',a.build/(name+'.ko')],'load-'+name);loaded.append(name)
        symbols=[l.split() for l in Path('/proc/kallsyms').read_text().splitlines()]
        core_names=['squashfs_read_inode','squashfs_lookup','squashfs_readdir','squashfs_read_metadata','squashfs_copy_data','squashfs_read_data']
        service_names=['squashfs_cache_get','squashfs_cache_put','squashfs_decompress','squashfs_bio_read']
        for variant,fs in [('original','squashfs'),('prepared','vksosquash')]:
            selected=[]
            codec_names=[name for name in ['vkso_LZ4_decompress_safe','vkso_xz_dec_run']
                         if variant=='prepared' and any(r[2]==name for r in symbols)]
            for name in core_names+service_names+(['sq_kernel_uid','sq_kernel_gid','sq_kernel_input_byte'] if variant=='prepared' else [])+codec_names:
                module='[vkso_sq_core]' if name in core_names+codec_names else '[vkso_squashfs]'
                found=[r for r in symbols if r[2]==name and (len(r)==3 if variant=='original' else len(r)==4 and r[3]==module)]
                assert len(found)==1,(variant,name,found)
                selected.append(dict(name=name,address='0x'+found[0][0]))
            run(['insmod',a.counter,'addresses='+','.join(s['address'] for s in selected),'copy_index='+str(core_names.index('squashfs_copy_data'))],variant+'-counter-load');counter_live=True
            ctl=Path('/sys/kernel/debug/vkso_sq_service_count/counts')
            try:
                for codec in ['gzip','lz4','xz']:
                    image=ROOT/f'test/section65/build/squashfs/application-images-01/{codec}.sif'
                    label=variant+'-'+codec
                    run(['mount','-t',fs,'-o','ro,loop,offset=36864',image,target],label+'-mount')
                    try:
                        ctl.write_text('r');ctl.write_text('1')
                        try:
                            r=subprocess.run(['taskset','-c','1','find','.','-printf','%P\t%y\t%s\n'],cwd=target/'opt/linux-headers',capture_output=True,check=True,timeout=180)
                        finally:ctl.write_text('0')
                        digest=hashlib.sha256(r.stdout).hexdigest()
                        if expected is None:expected=digest
                        assert digest==expected
                        counts=[int(l.split()[1]) for l in ctl.read_text().splitlines()]
                        assert len(counts)==len(selected) and counts[0]>0
                        result['cases'].append(dict(variant=variant,codec=codec,output_sha256=digest,
                            counts=[dict(**s,calls=n) for s,n in zip(selected,counts)],
                            copy_request_sizes={k:int(v) for k,v in (line.split() for line in ctl.with_name('copy_sizes').read_text().splitlines())},
                            copy_histogram_scope='Non-null destination requested lengths at copy_data entry; 257 denotes >256, not actual chunk lengths.'));write()
                    finally:run(['umount',target],label+'-unmount')
                    print(label,'counted',flush=True)
            finally:run(['rmmod','service_counter'],variant+'-counter-unload');counter_live=False
        result['status']='complete'
    except BaseException:
        result.update(status='failed',error=traceback.format_exc());raise
    finally:
        if os.path.ismount(target):run(['umount',target],'cleanup-unmount')
        if counter_live:run(['rmmod','service_counter'],'cleanup-counter')
        for name in reversed(loaded):run(['rmmod',name],'unload-'+name)
        result['modules_unloaded']=True;write()


if __name__=='__main__':main()
