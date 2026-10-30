#!/usr/bin/env python3
"""Fixed-owner native scan PMU attribution, excluding mount/unmount intervals."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import tempfile
import time
import traceback

ROOT=Path(__file__).resolve().parents[4]
PERF='/usr/lib/linux-tools/5.15.0-119-generic/perf'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=ROOT/'test/section65/build/squashfs/evaluation-fixed-01/build')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=int,default=24)
    p.add_argument('--codecs',nargs='+',default=['gzip','lz4','xz'])
    a=p.parse_args();assert os.geteuid()==0
    os.sched_setaffinity(0,{0})
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    target=out/'mount';target.mkdir();loaded=[];records=[];expected=None
    state=dict(status='running',scope='Diagnostic PMU attribution only; not formal effect estimates.',repeats=a.repeats,cases=records)
    def save():(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    def command(argv,label):
        with (out/(label+'.log')).open('w') as log:subprocess.run(list(map(str,argv)),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    shutil.copy2(__file__,out/'runner.py');save()
    state['module_hashes']={n:hashlib.sha256((a.build/n).read_bytes()).hexdigest() for n in ['vkso_sq_core.ko','vkso_squashfs.ko']}
    state['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    try:
        for name in ['vkso_sq_core','vkso_squashfs']:
            assert not (Path('/sys/module')/name).exists(),name
            command(['insmod',a.build/(name+'.ko')],'load-'+name);loaded.append(name)
        (out/'kallsyms.txt').write_text(Path('/proc/kallsyms').read_text())
        with tempfile.TemporaryDirectory(prefix='sq-native-profile-',dir='/dev/shm') as scratch:
            payload=Path(scratch)/'scan'
            for codec in a.codecs:
                image=ROOT/f'test/section65/build/squashfs/application-images-01/{codec}.sif'
                with image.open('rb') as stream:
                    while stream.read(1<<20):pass
                for variant,fs in [('original','squashfs'),('prepared','vksosquash')]:
                    label=codec+'-'+variant
                    # Separate per-process counters avoid multiplexing the sample recorder.
                    stats=[]
                    for j in range(4):
                        command(['mount','-t',fs,'-o','ro,loop,offset=36864',image,target],label+f'-stat-mount-{j}')
                        try:
                            with payload.open('wb') as output:
                                subprocess.run([PERF,'stat','-x,','-o',str(out/f'{label}-stat-{j}.csv'),
                                    '-e','cycles:k,instructions:k,branches:k,branch-misses:k,cache-misses:k',
                                    '--','taskset','-c','1','find','.','-printf','%P\t%y\t%s\n'],
                                    cwd=target/'opt/linux-headers',stdout=output,check=True,timeout=60)
                            digest=hashlib.sha256(payload.read_bytes()).hexdigest()
                            if expected is None:expected=digest
                            assert digest==expected
                            stats.append(str(out/f'{label}-stat-{j}.csv'))
                        finally:command(['umount',target],label+f'-stat-unmount-{j}')
                    cr,cw=os.pipe();ar,aw=os.pipe()
                    with (out/(label+'-record.log')).open('w') as log:
                        perf=subprocess.Popen([PERF,'record','-a','-C','1','-e','cycles:k','-F','997','-g','-D','-1',
                            f'--control=fd:{cr},{aw}','-o',str(out/(label+'.data'))],pass_fds=(cr,aw),stdout=log,stderr=subprocess.STDOUT)
                        os.close(cr);os.close(aw)
                        def control(msg):
                            assert perf.poll() is None
                            os.write(cw,msg.encode()+b'\n')
                            assert select.select([ar],[],[],15)[0], 'perf ack timeout'
                            assert os.read(ar,64).rstrip(b'\0\r\n')==b'ack'
                        try:
                            for j in range(a.repeats):
                                command(['mount','-t',fs,'-o','ro,loop,offset=36864',image,target],label+f'-sample-mount-{j}')
                                try:
                                    with payload.open('wb') as output:
                                        control('enable')
                                        try:subprocess.run(['taskset','-c','1','find','.','-printf','%P\t%y\t%s\n'],cwd=target/'opt/linux-headers',stdout=output,check=True,timeout=60)
                                        finally:control('disable')
                                    assert hashlib.sha256(payload.read_bytes()).hexdigest()==expected
                                finally:command(['umount',target],label+f'-sample-unmount-{j}')
                        finally:
                            if perf.poll() is None:perf.send_signal(signal.SIGINT)
                            code=perf.wait(timeout=30);os.close(cw);os.close(ar)
                            assert code in [0,-signal.SIGINT],code
                    for view,flag in [('self','--no-children'),('inclusive','--children')]:
                        command([PERF,'report','-i',out/(label+'.data'),'--stdio','--stdio-color','never','--comms','find',
                            '--sort','symbol,dso','--percent-limit','0.2','--kallsyms',out/'kallsyms.txt',flag],label+'-'+view)
                    records.append(dict(codec=codec,variant=variant,stat_files=stats,output_sha256=expected));save()
                    print(label,'complete',flush=True)
        state.update(status='complete',finished=time.time())
    except BaseException:
        state.update(status='failed',error=traceback.format_exc());raise
    finally:
        if os.path.ismount(target):command(['umount',target],'cleanup-unmount')
        for name in reversed(loaded):command(['rmmod',name],'unload-'+name)
        state['modules_unloaded']=True;save()


if __name__=='__main__':main()
