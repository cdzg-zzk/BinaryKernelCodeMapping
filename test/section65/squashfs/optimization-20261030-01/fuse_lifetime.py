#!/usr/bin/env python3
"""Valid-image FUSE handles and directory cursors across metadata eviction."""
import argparse, ctypes as C, errno, json, os, random, sys, traceback
from pathlib import Path

ROOT=Path('/home/zzk/BinaryKernelCodeMapping')
sys.path.insert(0,str(ROOT/'test/section65/squashfs'))
from check_fuse import mounted, observe

class Dirent(C.Structure):
    _fields_=[('ino',C.c_ulong),('offset',C.c_long),('reclen',C.c_ushort),('type',C.c_ubyte),('name',C.c_char*256)]

def main():
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True)
    p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--core',default='-');p.add_argument('--plan',type=Path)
    p.add_argument('--expect-shared',action='store_true');a=p.parse_args();build=a.build.resolve();fixture=a.fixture.resolve()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);target=out/'mount';target.mkdir()
    record={'status':'running','scope':'FUSE valid-image lifetime/contents/cursors, not performance'}
    libc=C.CDLL(None,use_errno=True)
    libc.opendir.argtypes=[C.c_char_p];libc.opendir.restype=C.c_void_p
    libc.readdir.argtypes=[C.c_void_p];libc.readdir.restype=C.POINTER(Dirent)
    libc.telldir.argtypes=[C.c_void_p];libc.telldir.restype=C.c_long
    libc.seekdir.argtypes=[C.c_void_p,C.c_long];libc.seekdir.restype=None
    libc.closedir.argtypes=[C.c_void_p];libc.closedir.restype=C.c_int
    root=fixture/'rootfs';paths=json.loads((fixture/'paths.json').read_text())
    try:
        bridge=build/('libsq-copy.so' if a.core=='-' else 'libsq-bridge.so')
        with mounted([str(build/'vkso-squashfuse'),a.core,str(bridge),str(fixture/'valid.squashfs'),'0',str(target)],target,out/'daemon.log') as child:
            if a.plan:observe(child.pid,Path(a.core),a.plan,out/'daemon.log',out/'pfns-before.json',a.expect_shared)
            fds=[];directory=None;checks=0;snapshots=[]
            def snapshot():
                data={}
                for line in Path(f'/proc/{child.pid}/smaps_rollup').read_text().splitlines():
                    key,sep,value=line.partition(':')
                    if sep and value.strip().endswith('kB'):data[key]=int(value.split()[0])
                snapshots.append(data)
            try:
                for path in paths[:64]:fds.append((os.open(target/path,os.O_RDONLY),path))
                directory=libc.opendir(os.fsencode(target/'d00'));assert directory
                first=libc.readdir(directory);assert first
                cursor=libc.telldir(directory);next_name=bytes(libc.readdir(directory).contents.name)
                snapshot()
                for pass_index in range(3):
                    order=list(paths);random.Random(653200+pass_index).shuffle(order)
                    for k,path in enumerate(order):
                        st=(target/path).stat();assert st.st_size==(root/path).stat().st_size
                        if k%67==0:assert (target/path).read_bytes()==(root/path).read_bytes();checks+=1
                    for fd,path in fds:assert os.pread(fd,256,0)==(root/path).read_bytes();checks+=1
                    libc.seekdir(directory,cursor)
                    assert bytes(libc.readdir(directory).contents.name)==next_name
                    snapshot()
                assert os.fstat(fds[0][0]).st_ino==(target/'hardlink-a').stat().st_ino==(target/'d31/hardlink-b').stat().st_ino
                assert os.getxattr(target/'hardlink-a','user.cache-test')==b'cache-lifetime'
                assert (target/'link').read_bytes()==(root/paths[0]).read_bytes()
                assert (target/('n'*255)).read_bytes()==b'long-name\n'
                try:os.open(target/'must-not-create',os.O_WRONLY|os.O_CREAT,0o600)
                except OSError as e:assert e.errno==errno.EROFS
                else:raise AssertionError('read-only mount accepted create')
                record.update(content_checks=checks,retained_file_handles=len(fds),cursor_roundtrips=3,memory_snapshots=snapshots)
                if a.plan:observe(child.pid,Path(a.core),a.plan,out/'daemon.log',out/'pfns-after.json',a.expect_shared)
            finally:
                for fd,path in fds:os.close(fd)
                if directory:assert libc.closedir(directory)==0
        record.update(status='complete',daemon_returncode=child.returncode,unmounted=not os.path.ismount(target))
    except BaseException:record.update(status='failed',error=traceback.format_exc());raise
    finally:(out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
