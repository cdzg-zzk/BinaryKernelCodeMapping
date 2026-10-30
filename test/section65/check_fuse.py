#!/usr/bin/env python3
"""Check the mounted filesystem through ordinary VFS calls and a tar workflow."""
import argparse
import ctypes as C
import errno
import json
import os
from pathlib import Path
import random
import stat
import subprocess
import time
import traceback

from reference_guest import manifest

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')

def observe_process(pid, library, output):
    """Read-only observation faults pages in without modifying shared instructions."""
    import export_guest as export
    plan=export.mappings()
    source=export.source_pfns(plan)
    rows=[]
    mem=os.open(f'/proc/{pid}/mem',os.O_RDONLY)
    pagemap=os.open(f'/proc/{pid}/pagemap',os.O_RDONLY)
    try:
        for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
            f=line.split(maxsplit=5)
            if len(f)!=6 or f[5]!=str(library): continue
            start,end=(int(x,16) for x in f[0].split('-'))
            fileoff=int(f[2],16)
            for offset,address,kind,section in plan:
                if fileoff<=offset<fileoff+end-start:
                    user=start+offset-fileoff
                    assert len(os.pread(mem,1,user))==1
                    entry=int.from_bytes(os.pread(pagemap,8,user//4096*8),'little')
                    pfn=entry&((1<<55)-1)
                    assert entry&(1<<63) and pfn
                    rows.append(dict(kind=kind,offset=offset,user_address=hex(user),
                        user_pfn=pfn,kernel_pfn=source[address],shared=pfn==source[address],
                        permissions=f[1]))
        assert len(rows)==len(plan),(len(rows),len(plan))
        assert all(r['shared'] and 'w' not in r['permissions'] for r in rows),rows
    finally:
        os.close(mem);os.close(pagemap)
    write(output,dict(status='pass',pid=pid,pages=rows))
    return rows

def run(frontend, core, bridge, images, reference, output, shared=False, fuse_options=None):
    output.mkdir(parents=True,exist_ok=False)
    mount=output/'mount';mount.mkdir()
    result=dict(status='running',scope='functional mounted filesystem; no performance claim',
                core=core,bridge=str(bridge),single_threaded=True,fuse_options=fuse_options,cases=[])
    cases=json.loads((reference/'result.json').read_text())['cases']
    try:
        for index,case in enumerate(cases):
            args=[str(frontend),core,str(bridge),str(images/case['image']),
                  str(int(case['mode']=='norock')),str(mount)]
            if fuse_options:args.append(fuse_options)
            with (output/f'daemon-{index}.log').open('w') as log:
                child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT)
                try:
                    deadline=time.monotonic()+60
                    while not os.path.ismount(mount):
                        assert child.poll() is None, ('FUSE exited',child.returncode,args)
                        assert time.monotonic()<deadline,'FUSE mount timed out'
                        time.sleep(.1)
                    rows=manifest(mount)
                    expected=json.loads((reference/case['manifest']).read_text())
                    assert rows==expected,case
                    write(output/case['manifest'],rows)
                    rng=random.Random(20261029);checks=0
                    for row in rows:
                        if not stat.S_ISREG(row['mode']):continue
                        with (mount/row['path']).open('rb') as stream:
                            data=stream.read()
                            for off in (0,1,2047,2048,len(data),rng.randrange(len(data)+1)):
                                stream.seek(off)
                                assert stream.read(4099)==data[off:off+4099]
                                checks+=1
                    try:
                        (mount/'__vkso_must_be_readonly__').write_text('unexpected')
                    except OSError as exc:
                        assert exc.errno==errno.EROFS,exc
                    else: raise AssertionError('read-only mount accepted a write')
                    pfn_file=None
                    if shared:
                        pfn_file=f'pfns-{index}.json'
                        observe_process(child.pid,Path(core),output/pfn_file)
                    # A real distribution image processed by an unmodified tool.
                    archive=None
                    if case['image'].startswith('alpine-'):
                        archive=output/'alpine.tar'
                        subprocess.run(['tar','-cf',str(archive),'-C',str(mount),'.'],check=True)
                        unpack=output/'tar-unpacked';unpack.mkdir()
                        subprocess.run(['tar','-xf',str(archive),'-C',str(unpack)],check=True)
                        extracted=manifest(unpack)
                        # Tar permission/ownership policy is external to filesystem parsing.
                        def contents(items):
                            return [{k:r[k] for k in ('path','size','sha256','target') if k in r}
                                    for r in items if not stat.S_ISDIR(r['mode'])]
                        assert contents(extracted)==contents(rows)
                    result['cases'].append(dict(**case,random_and_eof_reads=checks,
                        readonly_rejected=True,shared_pfns=pfn_file,archive=str(archive) if archive else None))
                finally:
                    if os.path.ismount(mount):
                        unmount=['umount',str(mount)] if os.geteuid()==0 else ['fusermount3','-u',str(mount)]
                        subprocess.run(unmount,check=True,timeout=30)
                    if child.poll() is None:
                        try:child.wait(timeout=10)
                        except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10)
                assert child.returncode==0,child.returncode
            print('fuse_case_pass='+case['image']+':'+case['mode'],flush=True)
        result['status']='pass'
    except BaseException:
        result['status']='failed';result['error']=traceback.format_exc();raise
    finally:write(output/'result.json',result)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--frontend',type=Path,required=True)
    p.add_argument('--core',default='-')
    p.add_argument('--bridge',type=Path,required=True)
    p.add_argument('--images',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--shared',action='store_true')
    p.add_argument('--fuse-options')
    a=p.parse_args()
    run(a.frontend.resolve(),a.core,a.bridge.resolve(),a.images.resolve(),a.reference.resolve(),a.output.resolve(),a.shared,a.fuse_options)

if __name__=='__main__':main()
