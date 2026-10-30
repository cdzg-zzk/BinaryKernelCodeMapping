#!/usr/bin/env python3
"""Interleave original and multiple prepared builds, reloading outside each timing."""
import argparse, hashlib, json, os
from pathlib import Path
import random, resource, subprocess, tempfile, time, traceback
ROOT=Path(__file__).resolve().parents[4]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--builds',type=Path,required=True);p.add_argument('--image-set',type=Path,required=True)
    p.add_argument('--references',type=Path,help='Additional native-module controls, each with module and filesystem')
    p.add_argument('--workloads',nargs='+',choices=['archive','scan'],default=['archive','scan'])
    p.add_argument('--subtree',default='opt/linux-headers')
    p.add_argument('--blocks',type=int,default=12);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--pilot',action='store_true');p.add_argument('--campaign',required=True);a=p.parse_args()
    assert os.geteuid()==0 and a.blocks>=4
    assert not Path(a.subtree).is_absolute() and '..' not in Path(a.subtree).parts
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);target=out/'mount';target.mkdir()
    builds={k:Path(v).resolve() for k,v in json.loads(a.builds.read_text()).items()};assert 'original' not in builds
    references=json.loads(a.references.read_text()) if a.references else {}
    assert not set(references)&({'original'}|set(builds))
    cases=json.loads(a.image_set.read_text())['cases'];loaded=[];active=None;rng=random.Random(a.seed);expected={};rows=[];order=[]
    result=dict(status='running',campaign=a.campaign,pilot=a.pilot,blocks=a.blocks,variants=['original',*builds,*references],
        scope='Fresh mount then one warm traversal, warm compressed-image cache; entire process execution timed. Modules reloaded outside timing whenever prepared variant changes.',
        phases=['fresh-mount','warm'],cpus=[1],subtree=a.subtree,order=order,module_residency={})
    write=lambda:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'runner.py').write_bytes(Path(__file__).read_bytes());write()
    def command(argv):
        start=time.time();r=subprocess.run(list(map(str,argv)),capture_output=True,text=True,timeout=120)
        with (out/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(argv=list(map(str,argv)),returncode=r.returncode,stderr=r.stderr,stdout=r.stdout,start=start,end=time.time()))+'\n')
        r.check_returncode()
    def unload():
        nonlocal active
        while loaded:command(['rmmod',loaded[-1]]);loaded.pop()
        active=None
    def select(label):
        nonlocal active
        if label=='original':return
        if label==active:return
        unload()
        if label in references:
            path=Path(references[label]['module']).resolve()
            assert not (Path('/sys/module')/path.stem).exists();command(['insmod',path]);loaded.append(path.stem);active=label
            record_residency(label);return
        for name in ['vkso_sq_core','vkso_squashfs']:
            assert not (Path('/sys/module')/name).exists();command(['insmod',builds[label]/(name+'.ko')]);loaded.append(name)
        active=label
        record_residency(label)
    def record_residency(label):
        if label in result['module_residency']:return
        result['module_residency'][label]={r[0]:int(r[1]) for line in Path('/proc/modules').read_text().splitlines() if (r:=line.split())[0] in loaded}
        write()
    try:
        environment=dict(argv=os.sys.argv,uname=list(os.uname()),affinity=sorted(os.sched_getaffinity(0)),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),cpuinfo=Path('/proc/cpuinfo').read_text(),meminfo=Path('/proc/meminfo').read_text(),
            loadavg=Path('/proc/loadavg').read_text(),governors={str(p):p.read_text().strip() for p in Path('/sys/devices/system/cpu').glob('cpu*/cpufreq/scaling_governor')},
            binaries={label:{n:dict(path=str(path/n),sha256=hashlib.sha256((path/n).read_bytes()).hexdigest()) for n in ['vkso_sq_core.ko','vkso_squashfs.ko']} for label,path in builds.items()},images=cases)
        for label,reference in references.items():
            path=Path(reference['module']).resolve();environment['binaries'][label]={path.name:dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())}
        (out/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')
        for c in cases:
            h=hashlib.sha256()
            with open(c['image'],'rb') as f:
                while data:=f.read(1<<20):h.update(data)
            assert h.hexdigest()==c['sha256']
        with tempfile.TemporaryDirectory(prefix='vkso-native-compare-',dir='/dev/shm') as scratch:
            payload=Path(scratch)/'output'
            for block in range(a.blocks):
                cells=[(c,w) for c in cases for w in a.workloads];rng.shuffle(cells)
                for c,w in cells:
                    variants=['original',*builds,*references];rng.shuffle(variants)
                    for label in variants:
                        select(label);order.append(dict(block=block,compressor=c['compressor'],workload=w,variant=label))
                        fs='squashfs' if label=='original' else references[label]['filesystem'] if label in references else 'vksosquash'
                        command(['mount','-t',fs,'-o',f"ro,loop,offset={c.get('offset',0)}",c['image'],target])
                        try:
                            for repeat in range(2):
                                argv=['tar','-cf','-','-C',str(target/a.subtree),'.'] if w=='archive' else ['find','.','-printf','%P\t%y\t%s\n']
                                before=resource.getrusage(resource.RUSAGE_CHILDREN)
                                with payload.open('wb') as f:
                                    start=time.perf_counter();r=subprocess.run(['taskset','-c','1',*argv],cwd=target/a.subtree,stdout=f,stderr=subprocess.PIPE,timeout=90);elapsed=time.perf_counter()-start
                                after=resource.getrusage(resource.RUSAGE_CHILDREN);assert r.returncode==0,r.stderr
                                data=payload.read_bytes();digest=hashlib.sha256(data).hexdigest();assert expected.setdefault(w,digest)==digest,(label,c,w)
                                row=dict(campaign=a.campaign,sequence=len(rows),block=block,compressor=c['compressor'],workload=w,variant=label,phase='fresh-mount' if repeat==0 else 'warm',repeat=repeat,
                                    wall_seconds=elapsed,cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,bytes=len(data),digest=digest)
                                rows.append(row)
                                with (out/'samples.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
                        finally:command(['umount',target])
                result['completed_blocks']=block+1;write();print('block',block+1,flush=True)
        assert len(rows)==a.blocks*len(cases)*len(a.workloads)*(len(builds)+len(references)+1)*2
        result.update(status='complete',observations=len(rows))
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:
        try:
            if os.path.ismount(target):command(['umount',target])
            unload();result['modules_unloaded']=True
        except BaseException:result.update(status='failed',cleanup_error=traceback.format_exc());raise
        finally:write()
if __name__=='__main__':main()
