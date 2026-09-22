#!/usr/bin/env python3
"""File/VMA boundaries exercised as the ordinary owner inside the private guest."""
import ctypes as C
import errno
import json
import mmap
import os
from pathlib import Path
import sys


def main(path):
    assert os.geteuid() == 65534
    libc = C.CDLL(None, use_errno=True)
    libc.mmap.argtypes = [C.c_void_p,C.c_size_t,C.c_int,C.c_int,C.c_int,C.c_long]
    libc.mmap.restype = C.c_void_p
    for name in ('mprotect','madvise','msync'):
        getattr(libc,name).argtypes = [C.c_void_p,C.c_size_t,C.c_int]
    libc.munmap.argtypes = [C.c_void_p,C.c_size_t]
    records = {}
    operations = {
        'open-rdwr': lambda p: os.close(os.open(p,os.O_RDWR)),
        'truncate': lambda p: os.truncate(p,p.stat().st_size),
        'rename': lambda p: os.rename(p,p.with_suffix('.renamed')),
        'unlink': lambda p: os.unlink(p),
        'hardlink': lambda p: os.link(p,p.with_suffix('.linked')),
        'chmod': lambda p: os.chmod(p,0o666),
        'utime': lambda p: os.utime(p,None),
    }
    # The same UID, parent directory and mount permit every ordinary operation.
    for name, operation in operations.items():
        control = path.parent / ('control-'+name)
        control.write_bytes(b'ordinary file')
        operation(control)
        records[name] = {'ordinary_file':'allowed'}
        for target in (path,path.parent/'alias.bin'):
            try: operation(target)
            except OSError as e:
                assert e.errno == errno.EPERM,(name,e)
                records[name][target.name]=e.errno
            else: raise AssertionError(name+' unexpectedly changed registered inode')
    fd = os.open(path,os.O_RDONLY)
    address = libc.mmap(None,4096,mmap.PROT_READ,mmap.MAP_SHARED,fd,4096)
    assert address != C.c_void_p(-1).value
    original = C.string_at(address,4096)
    assert original != b'Z'*4096
    assert libc.mprotect(address,4096,mmap.PROT_READ|mmap.PROT_WRITE)==-1
    assert C.get_errno()==errno.EACCES
    records['shared-write-upgrade']=errno.EACCES
    assert libc.mprotect(address,4096,mmap.PROT_READ|mmap.PROT_EXEC)==0
    records['shared-executable-read']='allowed; bytes unchanged; no fixture execution'
    assert libc.msync(address,4096,4)==0 # MS_SYNC
    assert libc.madvise(address,4096,mmap.MADV_DONTNEED)==0
    assert C.string_at(address,4096)==original
    os.posix_fadvise(fd,4096,4096,os.POSIX_FADV_DONTNEED)
    assert C.string_at(address,4096)==original
    records['msync-madvise-fadvise']='success; original resident bytes preserved'
    private = libc.mmap(None,4096,mmap.PROT_READ,mmap.MAP_PRIVATE,fd,4096)
    assert private != C.c_void_p(-1).value
    assert libc.mprotect(private,4096,mmap.PROT_READ|mmap.PROT_WRITE)==0
    C.c_ubyte.from_address(private).value=ord('Q')
    assert C.string_at(address,4096)==original
    child=os.fork()
    if child==0:
        C.c_ubyte.from_address(private).value=ord('R')
        os._exit(0 if C.string_at(address,4096)==original else 1)
    _,status=os.waitpid(child,0)
    assert status==0 and C.c_ubyte.from_address(private).value==ord('Q')
    records['private-write-and-fork']='private writes isolated in parent and child'
    libc.munmap(private,4096);libc.munmap(address,4096);os.close(fd)
    print(json.dumps({'status':'pass','uid':os.geteuid(),'operations':records},indent=2))


if __name__=='__main__': main(Path(sys.argv[1]))
