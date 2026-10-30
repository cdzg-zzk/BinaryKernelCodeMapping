#!/usr/bin/env python3
"""Exercise real directory cookies, independent handles and directory fstat."""
import ctypes
import os

libc=ctypes.CDLL(None,use_errno=True)
libc.opendir.argtypes=[ctypes.c_char_p];libc.opendir.restype=ctypes.c_void_p
libc.readdir.argtypes=[ctypes.c_void_p];libc.readdir.restype=ctypes.c_void_p
libc.telldir.argtypes=[ctypes.c_void_p];libc.telldir.restype=ctypes.c_long
libc.seekdir.argtypes=[ctypes.c_void_p,ctypes.c_long]
libc.rewinddir.argtypes=[ctypes.c_void_p]
libc.closedir.argtypes=[ctypes.c_void_p]
libc.dirfd.argtypes=[ctypes.c_void_p];libc.dirfd.restype=ctypes.c_int


def check(path):
    first=libc.opendir(os.fsencode(path));second=libc.opendir(os.fsencode(path))
    assert first and second,(path,ctypes.get_errno())
    def read(handle):
        ctypes.set_errno(0);p=libc.readdir(handle)
        if not p:assert ctypes.get_errno()==0;return None
        # Linux x86-64 struct dirent: ino/off/reclen/type/name.
        return ctypes.string_at(p+19)
    try:
        assert os.fstat(libc.dirfd(first)).st_ino==os.stat(path).st_ino
        names=[];cookies=[libc.telldir(first)]
        while (name:=read(first)) is not None:
            names.append(name);cookies.append(libc.telldir(first))
        assert len(names)==len(set(names))
        assert set(names)=={b'.',b'..',*map(os.fsencode,os.listdir(path))}
        positions=sorted({0,1,2,17,33,len(names)//2,len(names)-1,len(names)})
        positions=[i for i in positions if i<=len(names)]
        for i in reversed(positions):
            libc.seekdir(first,cookies[i])
            assert [read(first) for _ in range(min(5,len(names)-i))]==names[i:i+5]
        libc.rewinddir(first)
        for expected in names[:100]:
            assert read(first)==read(second)==expected
        libc.closedir(first);first=None
        # Releasing one directory handle leaves the other valid.
        for expected in names[100:]:assert read(second)==expected
        assert read(second) is None
        return dict(entries=len(names),seek_positions=positions,independent_handles=True,directory_fstat=True)
    finally:
        if first:libc.closedir(first)
        if second:libc.closedir(second)
