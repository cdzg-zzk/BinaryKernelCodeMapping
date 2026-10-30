#!/usr/bin/env python3
"""Valid-image xattr semantics across original/prepared/copied/shared readers."""
import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import traceback
from check_fuse import mounted, observe
from reference_guest import manifest

ROOT=Path(__file__).resolve().parents[3]
SUPPORT=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=ROOT/'test/section65/build/squashfs/evaluation-fixed-01/build')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--formats',nargs='+',choices=['gzip','xz','zstd','lz4','lzo','xz-bcj'],default=['gzip','xz','zstd','lz4','lzo']);a=p.parse_args()
    assert os.geteuid()==0
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);build=a.build.resolve()
    (out/'runner.py').write_bytes(Path(__file__).read_bytes())
    result=dict(status='running',scope='Additional valid-image semantics, no timing. Empty capability set carries no privileges.',cases=[])
    write=lambda:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    loaded=[];registered=False;library=None;write()
    def command(argv,label,cwd=None):
        argv=list(map(str,argv))
        with (out/(label+'.log')).open('w') as log:
            r=subprocess.run(argv,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        with (out/'commands.jsonl').open('a') as log:log.write(json.dumps(dict(stage=label,argv=argv,returncode=r.returncode))+'\n')
        r.check_returncode()
    attrs={'user.vkso_fixture':b'metadata retained','user.empty':b'',
           'user.large':bytes(range(256))*8,
           'security.capability':struct.pack('<5I',0x02000000,0,0,0,0)}
    libc=ctypes.CDLL(None,use_errno=True)
    libc.getxattr.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_void_p,ctypes.c_size_t]
    libc.getxattr.restype=ctypes.c_ssize_t
    libc.listxattr.argtypes=[ctypes.c_char_p,ctypes.c_void_p,ctypes.c_size_t]
    libc.listxattr.restype=ctypes.c_ssize_t
    payload=bytes(range(256))*1025+b'end'
    if 'xz-bcj' in a.formats:
        # Repeated calls to one absolute target become highly compressible
        # after x86 BCJ conversion; verify the image actually selects BCJ.
        payload=b''.join(b'\xe8'+struct.pack('<i',0x10000-offset-5)+b'\x90'*11 for offset in range(0,262400,16))+b'end'
    def check(target,label,expected=None):
        rows=manifest(target)
        if expected is not None:assert rows==expected,label
        (out/(label+'-manifest.json')).write_text(json.dumps(rows,indent=2)+'\n')
        path=target/'pattern';encoded=os.fsencode(path)
        assert sorted(os.listxattr(path))==sorted(attrs), (label,os.listxattr(path))
        list_bytes=sum(len(n.encode())+1 for n in attrs)
        assert libc.listxattr(encoded,None,0)==list_bytes
        small=ctypes.create_string_buffer(1);ctypes.set_errno(0)
        assert libc.listxattr(encoded,small,1)==-1 and ctypes.get_errno()==errno.ERANGE
        evidence=[]
        for name,value in attrs.items():
            observed=os.getxattr(path,name);assert observed==value,(label,name,observed)
            assert libc.getxattr(encoded,name.encode(),None,0)==len(value)
            small_error=None
            if len(value)>1:
                buffer=ctypes.create_string_buffer(1);ctypes.set_errno(0)
                assert libc.getxattr(encoded,name.encode(),buffer,1)==-1
                small_error=ctypes.get_errno();assert small_error==errno.ERANGE,(label,name,small_error)
            evidence.append(dict(name=name,bytes=len(value),hex=observed.hex(),undersized_buffer_errno=small_error))
        try:os.getxattr(path,'user.absent')
        except OSError as exc:assert exc.errno==errno.ENODATA
        else:raise AssertionError('missing xattr unexpectedly returned')
        assert path.stat().st_ino==(target/'hardlink').stat().st_ino
        assert (target/'symlink').read_bytes()==payload
        with path.open('rb') as stream:
            for offset in [0,4095,4096,131071,131072,len(payload)-1,len(payload),len(payload)+1]:
                stream.seek(offset);assert stream.read(131079)==payload[offset:offset+131079]
        result['cases'].append(dict(label=label,status='pass',entries=len(rows),attributes=evidence,
            absent_errno=errno.ENODATA,list_bytes=list_bytes,list_undersized_errno=errno.ERANGE,
            boundary_reads=8,hardlink=True,symlink=True));write()
        return rows
    def native(image,fs,label,expected=None):
        command(['mount','-t',fs,'-o','ro,loop',image,target],label+'-mount')
        try:return check(target,label,expected)
        finally:command(['umount',target],label+'-unmount')
    try:
        source=out/'source';source.mkdir();(source/'pattern').write_bytes(payload)
        for name,value in attrs.items():os.setxattr(source/'pattern',name,value)
        os.link(source/'pattern',source/'hardlink');(source/'symlink').symlink_to('pattern')
        (source/'empty').write_bytes(b'');(source/'directory').mkdir()
        images=[]
        for codec in a.formats:
            image=out/(codec+'.squashfs')
            command(['mksquashfs',source,image,'-noappend','-processors','1','-comp','xz' if codec=='xz-bcj' else codec,
                '-b','131072','-force-uid','123','-force-gid','456','-all-time','1700000000',
                '-mkfs-time','1700000000','-no-progress',*(['-Xbcj','x86'] if codec=='xz-bcj' else [])],'image-'+codec)
            images.append(image)
            if codec=='xz-bcj':
                data=image.read_bytes();headers=[];position=0;filter_chains=[]
                while (position:=data.find(b'\xfd7zXZ\x00',position))>=0:
                    h=data[position+12:position+1036]
                    if len(h)>=4:
                        headers.append(h[:24].hex());cursor=2
                        def vli():
                            nonlocal cursor
                            value=shift=0
                            while True:
                                byte=h[cursor];cursor+=1;value|=(byte&127)<<shift
                                if not byte&128:return value
                                shift+=7;assert shift<=63
                        if h[1]&64:vli()
                        if h[1]&128:vli()
                        filters=[]
                        for _ in range((h[1]&3)+1):
                            filters.append(vli());size=vli();cursor+=size
                        filter_chains.append(filters)
                    position+=6
                assert [4,33] in filter_chains, 'Image must select the x86 BCJ + LZMA2 filter chain'
                result['xz_block_header_prefixes']=headers
                result['xz_filter_chains']=filter_chains
        result['images']=[dict(path=str(i),sha256=hashlib.sha256(i.read_bytes()).hexdigest()) for i in images]
        result['binaries']={n:hashlib.sha256((build/n).read_bytes()).hexdigest() for n in
            ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse']}
        target=out/'mount';target.mkdir();oracles={}
        for image in images:oracles[image.stem]=native(image,'squashfs','original-'+image.stem)
        assert all(rows==oracles[images[0].stem] for rows in oracles.values())
        for name in ['vkso_sq_core','vkso_squashfs','vkso_kernel_reader','page_cache_replace']:
            assert not (Path('/sys/module')/name).exists()
            path=build/(name+'.ko') if name in ['vkso_sq_core','vkso_squashfs'] else SUPPORT/'modules'/(name+'.ko')
            command(['insmod',path],'load-'+name);loaded.append(name)
        for image in images:native(image,'vksosquash','prepared-before-'+image.stem,oracles[image.stem])
        carrier=out/'carrier';carrier.mkdir()
        shutil.copy2(build/'symbols.txt',carrier/'symbols.txt');shutil.copy2(build/'shim.txt',carrier/'shim.txt')
        command([SUPPORT/'krg','build',SUPPORT/'vmlinux','--module',build/'vkso_sq_core.ko','-o',carrier/'out.krg'],'krg')
        command([sys.executable,ROOT/'make_dll/build_PIC_so.py','--symbols',carrier/'symbols.txt',
            '--krg',carrier/'out.krg','--ko',build/'vkso_sq_core.ko','--shim-list',carrier/'shim.txt',
            '--vmlinux',SUPPORT/'vmlinux'],'export',carrier)
        library=next(carrier.glob('lib*.so')).resolve();before=library.read_bytes()
        command([SUPPORT/'manager','replace',library,carrier/'page_mappings.txt'],'register',SUPPORT);registered=True
        copied=out/'libsq-materialized.so';copied.write_bytes(library.read_bytes())
        for label,core in [('copied',copied),('shared',library)]:
            for image in images:
                name=label+'-'+image.stem;log=out/(name+'.log')
                with mounted([str(build/'vkso-squashfuse'),str(core),str(build/'libsq-bridge.so'),str(image),'0',str(target)],target,log) as child:
                    check(target,name,oracles[image.stem])
                    observe(child.pid,core,carrier/'page_mappings.txt',log,out/(name+'-pfns.json'),label=='shared')
        for image in images:native(image,'vksosquash','prepared-after-'+image.stem,oracles[image.stem])
        command([SUPPORT/'manager','restore',library,carrier/'page_mappings.txt'],'restore',SUPPORT);registered=False
        assert library.read_bytes()==before
        result.update(status='complete',restored=True)
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:
        try:
            if registered:command([SUPPORT/'manager','restore',library,carrier/'page_mappings.txt'],'cleanup-restore',SUPPORT)
            for name in reversed(loaded):command(['rmmod',name],'unload-'+name)
            result['modules_unloaded']=True
        except BaseException:result.update(status='failed',cleanup_error=traceback.format_exc());raise
        finally:write()


if __name__=='__main__':main()
