#!/usr/bin/env python3
"""Exercise complete image access with Linux-isofs user adapter; compare kernel manifests."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import stat
import time

HERE = Path(__file__).resolve().parent
class Metadata(C.Structure):
    _fields_ = [(n,t) for n,t in [('size',C.c_uint64),('ino',C.c_uint64),
        ('mtime_sec',C.c_int64),('mtime_nsec',C.c_int64),('mode',C.c_uint32),
        ('uid',C.c_uint32),('gid',C.c_uint32),('nlink',C.c_uint32)]]
EMIT = C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p,C.c_int)

def load(path):
    lib = C.CDLL(str(path.resolve()))
    signatures = {
        'iso_open_image':([C.c_char_p,C.c_int],C.c_void_p),
        'iso_close_image':([C.c_void_p],None),
        'iso_root_inode':([C.c_void_p],C.c_void_p),
        'iso_lookup_child':([C.c_void_p,C.c_char_p,C.c_uint],C.c_void_p),
        'iso_inode_metadata':([C.c_void_p,C.POINTER(Metadata)],None),
        'iso_list_inode':([C.c_void_p,EMIT,C.c_void_p],C.c_int),
        'iso_inode_readlink':([C.c_void_p,C.c_void_p,C.c_size_t],C.c_int),
        'iso_read_inode_data':([C.c_void_p,C.c_void_p,C.c_size_t,C.c_uint64],C.c_ssize_t),
    }
    for name,(args,result) in signatures.items():
        fn = getattr(lib,name); fn.argtypes=args; fn.restype=result
    return lib

def manifest(lib, image, norock):
    handle = lib.iso_open_image(str(image).encode(), int(norock))
    if not handle: raise RuntimeError('open failed: '+str(image))
    rows, checks = [], dict(random_reads=0,eof_reads=0,missing_lookups=0)
    rng = random.Random(20261028)
    def visit(parent, path, depth=0):
        if depth > 64: raise RuntimeError('directory cycle/depth exceeded')
        names = []
        @EMIT
        def emit(_, name, n): names.append(C.string_at(name,n)); return 0
        assert lib.iso_list_inode(parent,emit,None) == 0
        assert not lib.iso_lookup_child(parent,b'__no_such_iso_entry__',21)
        checks['missing_lookups'] += 1
        assert len(names) == len(set(names)), (path,'duplicate names')
        for name in sorted(names):
            inode = lib.iso_lookup_child(parent,name,len(name))
            assert inode, (path,name,'lookup failed')
            meta = Metadata(); lib.iso_inode_metadata(inode,C.byref(meta))
            fullpath = path + name.decode('utf-8')
            row = dict(path=fullpath,mode=meta.mode,size=meta.size,uid=meta.uid,gid=meta.gid,
                       nlink=meta.nlink,mtime_ns=meta.mtime_sec*10**9+meta.mtime_nsec)
            if stat.S_ISREG(meta.mode):
                data, pos = bytearray(), 0
                while pos < meta.size:
                    # Unaligned 65,537-byte reads deliberately cross disk blocks.
                    n = min(65537,meta.size-pos); buf=C.create_string_buffer(n)
                    got=lib.iso_read_inode_data(inode,buf,n,pos)
                    assert got == n,(fullpath,pos,got,n)
                    data.extend(buf.raw); pos += n
                row['sha256']=hashlib.sha256(data).hexdigest()
                buf=C.create_string_buffer(4099)
                for start in [0,1,2047,2048,max(0,meta.size-1),rng.randrange(meta.size+1)]:
                    got=lib.iso_read_inode_data(inode,buf,4099,start)
                    expected=bytes(data[start:start+4099])
                    assert got == len(expected) and buf.raw[:got] == expected,(fullpath,start,got)
                    checks['random_reads'] += 1
                assert lib.iso_read_inode_data(inode,buf,4099,meta.size) == 0
                checks['eof_reads'] += 1
            elif stat.S_ISLNK(meta.mode):
                buf=C.create_string_buffer(4096)
                assert lib.iso_inode_readlink(inode,buf,4096) == 0
                row['target']=buf.value.decode('utf-8')
            rows.append(row)
            if stat.S_ISDIR(meta.mode): visit(inode,fullpath+'/',depth+1)
    try: visit(lib.iso_root_inode(handle),'')
    finally: lib.iso_close_image(handle)
    return sorted(rows,key=lambda r:r['path']),checks

def run(library, images, reference, output):
    output.mkdir(parents=True,exist_ok=False)
    lib=load(library)
    cases=json.loads((reference/'result.json').read_text())['cases']
    result=dict(status='running',library=str(library),scope='functionality, not performance',cases=[])
    try:
        for case in cases:
            start=time.monotonic()
            rows,checks=manifest(lib,images/case['image'],case['mode']=='norock')
            expected=json.loads((reference/case['manifest']).read_text())
            expected=sorted(expected,key=lambda r:r['path'])
            (output/case['manifest']).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
            differences=[]
            a={r['path']:r for r in expected}; b={r['path']:r for r in rows}
            for name in sorted(a.keys()|b.keys()):
                if a.get(name) != b.get(name): differences.append(dict(path=name,kernel=a.get(name),user=b.get(name)))
            result['cases'].append(dict(**case,checks=checks,differences=differences,
                                        elapsed_functional_seconds=time.monotonic()-start))
            print(case['image'],case['mode'],len(rows),'differences',len(differences),flush=True)
        result['status']='pass' if all(not c['differences'] for c in result['cases']) else 'fail'
    except BaseException as exc:
        result['status']='error'; result['error']=repr(exc); raise
    finally: (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result['status']=='pass'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library',type=Path,default=HERE/'build/adapted/libisofs-copy.so')
    p.add_argument('--images',type=Path,default=HERE/'build/images')
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    raise SystemExit(0 if run(a.library,a.images,a.reference,a.output) else 1)
if __name__ == '__main__': main()
