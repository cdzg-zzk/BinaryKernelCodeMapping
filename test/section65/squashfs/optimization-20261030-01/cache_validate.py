#!/usr/bin/env python3
"""Valid-image cache lifetime differential and churn checks; never formal timing."""
import argparse, ctypes as C, hashlib, json, os, random, shutil, subprocess, sys
from pathlib import Path

ROOT=Path('/home/zzk/BinaryKernelCodeMapping')
SECTION=ROOT/'test/section65'
class Meta(C.Structure):
    _fields_=[(n,C.c_uint64) for n in ['size','ino','blocks','rdev']]+[(n,C.c_int64) for n in ['mtime_sec','mtime_nsec']]+[(n,C.c_uint32) for n in ['mode','uid','gid','nlink']]

def fixture(out):
    root=out/'rootfs';root.mkdir();paths=[]
    for d in range(32):
        directory=root/f'd{d:02}';directory.mkdir()
        for j in range(256):
            path=directory/f'f{j:03}';path.write_bytes((f'cache-lifetime {d:02}/{j:03}\n'.encode())*7)
            paths.append(str(path.relative_to(root)))
    os.link(root/paths[0],root/'hardlink-a');os.link(root/paths[0],root/'d31/hardlink-b')
    (root/'link').symlink_to(paths[0]);(root/('n'*255)).write_bytes(b'long-name\n')
    os.setxattr(root/paths[0],'user.cache-test',b'cache-lifetime')
    (out/'paths.json').write_text(json.dumps(paths))
    with (out/'fixture.log').open('w') as log:
        subprocess.run(['mksquashfs',root,out/'valid.squashfs','-noappend','-processors','1','-comp','xz',
            '-all-time','1700000000','-mkfs-time','1700000000','-no-progress'],stdout=log,stderr=subprocess.STDOUT,check=True)

def exercise(build,out):
    api=C.CDLL(str(build/'libsq-copy.so'),mode=C.RTLD_GLOBAL)
    emit=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_char_p,C.c_int)
    specs={
        'open_image':([C.c_char_p,C.c_uint64],C.c_void_p),'close_image':([C.c_void_p],None),
        'root_inode':([C.c_void_p],C.c_void_p),'lookup_child':([C.c_void_p,C.c_char_p,C.c_uint],C.c_void_p),
        'inode_pin':([C.c_void_p],None),'inode_release':([C.c_void_p],None),
        'inode_metadata':([C.c_void_p,C.POINTER(Meta)],None),
        'read_inode_data':([C.c_void_p,C.c_void_p,C.c_size_t,C.c_uint64],C.c_ssize_t),
        'inode_readlink':([C.c_void_p,C.c_void_p,C.c_size_t],C.c_int),
        'inode_getxattr':([C.c_void_p,C.c_char_p,C.c_void_p,C.c_size_t],C.c_int),
        'list_inode':([C.c_void_p,emit,C.c_void_p],C.c_int),
        'cache_stats':([C.c_void_p,C.POINTER(C.c_uint64)],None)}
    for name,(args,ret) in specs.items():
        f=getattr(api,'sq_'+name);f.argtypes=args;f.restype=ret
    im=api.sq_open_image(str(out/'valid.squashfs').encode(),0);assert im
    root=out/'rootfs';paths=json.loads((out/'paths.json').read_text());snapshots={};checks=0
    def lookup(path):
        i=api.sq_root_inode(im)
        for part in path.split('/'):
            i=api.sq_lookup_child(i,part.encode(),len(part));assert i,path
        return i
    def metadata(i):
        m=Meta();api.sq_inode_metadata(i,C.byref(m));return m
    def read(i,path):
        nonlocal checks
        ref=(root/path).read_bytes();buf=C.create_string_buffer(len(ref)+17)
        n=api.sq_read_inode_data(i,buf,len(buf),0);assert n==len(ref) and buf.raw[:n]==ref,path;checks+=1
    def stats(name):
        v=(C.c_uint64*8)();api.sq_cache_stats(im,v);snapshots[name]=list(v);return list(v)
    held=[]
    try:
        for path in paths[:4]:
            i=lookup(path);api.sq_inode_pin(i);held.append((i,path,metadata(i).ino))
        directory=lookup('d00');api.sq_inode_pin(directory)
        a=lookup('hardlink-a');assert a==held[0][0]
        api.sq_inode_pin(a)
        assert lookup('d31/hardlink-b')==a and metadata(a).nlink==3
        # First name survives while its unpinned inode gets evicted and reloaded.
        saved=metadata(lookup(paths[16])).ino
        for path in paths[256:256+2200]:lookup(path)
        assert metadata(lookup(paths[16])).ino==saved;read(lookup(paths[16]),paths[16])
        stats('name-hit-after-inode-eviction')
        for pass_index in range(3):
            order=list(paths);random.Random(653100+pass_index).shuffle(order)
            for k,path in enumerate(order):
                i=lookup(path);m=metadata(i);ref=(root/path).stat()
                assert m.size==ref.st_size and m.mode==ref.st_mode
                if k%31==0:read(i,path)
            for i,path,ino in held:
                assert metadata(i).ino==ino;read(i,path)
            names=[]
            @emit
            def collect(arg,name,n):names.append(C.string_at(name,n).decode());return 0
            assert api.sq_list_inode(directory,collect,None)==0
            assert sorted(names)==sorted(p.name for p in (root/'d00').iterdir())
            v=stats('churn-'+str(pass_index));assert v[0]<=2048 and v[1]<=4096
        i=lookup('link');buf=C.create_string_buffer(1024)
        assert api.sq_inode_readlink(i,buf,len(buf))==0 and buf.value.decode()==paths[0]
        assert api.sq_inode_getxattr(a,b'user.cache-test',buf,len(buf))==14 and buf.raw[:14]==b'cache-lifetime'
        read(lookup('n'*255),'n'*255)
        # More live handles than the cache budget must remain valid. Releasing
        # them restores the configured retained-cache bound.
        many=[]
        for path in paths[100:2500]:
            i=lookup(path);api.sq_inode_pin(i);many.append((i,path))
        v=stats('over-budget-live-handles');assert v[0]>2048 and v[0]<=len(many)+len(held)+8
        for i,path in many[::127]:read(i,path)
        for i,path in many:api.sq_inode_release(i)
        v=stats('released-handles');assert v[0]<=2048 and v[1]<=4096
        api.sq_inode_release(a);api.sq_inode_release(directory)
        for i,path,ino in held:api.sq_inode_release(i)
        v=stats('all-test-handles-released');assert v[2]>20000 and v[3]>15000
    finally:api.sq_close_image(im)
    result=dict(status='complete',scope='valid-image API lifetime checks, not FUSE/shared-PFN/native/timing evidence',
        distinct_regular_files=len(paths),churn_passes=3,content_checks=checks,snapshots=snapshots,
        stats_order=['retained_inodes','retained_names','inode_evictions','name_evictions','peak_inodes','peak_names','inode_budget','name_budget'],
        image_sha256=hashlib.sha256((out/'valid.squashfs').read_bytes()).hexdigest(),
        bridge_sha256=hashlib.sha256((build/'libsq-copy.so').read_bytes()).hexdigest())
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--existing-fixture',action='store_true');a=p.parse_args();out=a.output.resolve()
    if not a.existing_fixture:out.mkdir(parents=True,exist_ok=False);fixture(out)
    exercise(a.build.resolve(),out)

if __name__=='__main__':main()
