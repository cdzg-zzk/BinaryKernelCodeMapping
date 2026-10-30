#!/usr/bin/env python3
"""Check actual SquashFS/FUSE mounts against the independent native oracle."""
import argparse
import contextlib
import csv
import errno
import hashlib
import json
import io
import os
from pathlib import Path
import random
import re
import stat
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
SECTION=HERE.parent
sys.path.insert(0,str(SECTION))
from reference_guest import manifest


@contextlib.contextmanager
def mounted(command,target,log_path,pass_fds=()):
    with log_path.open('w') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,pass_fds=pass_fds)
        try:
            deadline=time.monotonic()+30
            while not os.path.ismount(target):
                assert child.poll() is None, (child.returncode,log_path)
                assert time.monotonic()<deadline, 'mount timed out'
                time.sleep(.05)
            target.stat()
            yield child
        finally:
            if os.path.ismount(target):
                subprocess.run(['fusermount3','-u',str(target)] if os.geteuid() else ['umount',str(target)],check=True,timeout=15)
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.terminate();child.wait(timeout=5)
        assert child.returncode==0, (child.returncode,log_path)


def check(target,expected,out,label):
    rows=manifest(target)
    (out/(label+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    assert rows==expected, label
    assert (target/'pattern').stat().st_ino==(target/'hardlink').stat().st_ino
    assert os.getxattr(target/'pattern','user.vkso_fixture')==b'metadata retained'
    assert 'user.vkso_fixture' in os.listxattr(target/'pattern')
    rng=random.Random(20261029); checks=0
    for row in rows:
        if not stat.S_ISREG(row['mode']):continue
        with (target/row['path']).open('rb') as stream:
            data=stream.read()
            for offset in (0,1,4095,4096,131071,131072,len(data),len(data)+1,rng.randrange(len(data)+1)):
                stream.seek(offset)
                assert stream.read(131079)==data[offset:offset+131079], (label,row['path'],offset)
                checks+=1
    try: (target/'write-rejected').write_bytes(b'x')
    except OSError as exc: assert exc.errno==errno.EROFS,exc
    else: raise AssertionError('write accepted')
    assert os.statvfs(target).f_blocks>0
    # The same complete mounted image also drives an unmodified archive tool.
    archive=out/(label+'.tar')
    subprocess.run(['tar','-cf',str(archive),'-C',str(target),'.'],check=True)
    return dict(label=label,entries=len(rows),random_and_boundary_reads=checks,
                xattr=True,hardlink=True,readonly=True,tar=str(archive))


def observe(pid,library,plan_path,log_path,output,shared):
    from elftools.elf.elffile import ELFFile
    plan=[(int(o,0),int(a,0),kind) for line in plan_path.read_text().splitlines()
          if line and not line.startswith('#') for o,a,kind,section in [line.split(',')]]
    reader=Path('/sys/kernel/debug/vkso_kernel_reader')
    tables=[int(fields[0],16) for line in Path('/proc/kallsyms').read_text().splitlines()
            if len(fields:=line.split())==4 and fields[2]=='sq_support' and fields[3]=='[vkso_sq_core]']
    assert len(tables)==1 and tables[0], 'native owner binding table must be identifiable'
    native_table_page=tables[0]&~4095
    (reader/'page_addresses').write_text(' '.join(hex(a) for a in [*(a for _,a,_ in plan),native_table_page]))
    source={int(r['kernel_vaddr'],0):int(r['pfn']) for r in csv.DictReader(io.StringIO((reader/'pages').read_text()))}
    rows=[]
    with open(f'/proc/{pid}/mem','rb',buffering=0) as mem,open(f'/proc/{pid}/pagemap','rb',buffering=0) as pm:
        def pfn(address):
            assert len(os.pread(mem.fileno(),1,address))==1
            entry=int.from_bytes(os.pread(pm.fileno(),8,address//4096*8),'little')
            assert entry&(1<<63) and entry&((1<<55)-1)
            return entry&((1<<55)-1)
        library_mappings=[]
        for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
            f=line.split(maxsplit=5)
            if len(f)!=6 or f[5]!=str(library):continue
            start,end=(int(v,16) for v in f[0].split('-'));off=int(f[2],16)
            library_mappings.append((start,end,off))
            for offset,address,kind in plan:
                if off<=offset<off+end-start:
                    actual=pfn(start+offset-off)
                    rows.append(dict(kind=kind,offset=offset,kernel_pfn=source[address],user_pfn=actual,
                                     shared=actual==source[address],permissions=f[1],
                                     mapped_page_sha256=hashlib.sha256(os.pread(mem.fileno(),4096,start+offset-off)).hexdigest()))
        assert len(rows)==len(plan) and all(r['shared']==shared and 'w' not in r['permissions'] for r in rows)
        # Apptainer consumes successful helper output internally. Locate the
        # private table from ELF and /proc, without depending on forwarded logs.
        with library.open('rb') as stream:
            elf=ELFFile(stream)
            symbol=elf.get_section_by_name('.symtab').get_symbol_by_name('sq_support')[0]
            section=elf.get_section(symbol['st_shndx'])
            file_offset=section['sh_offset']+symbol['st_value']-section['sh_addr']
        addresses=[start+file_offset-off for start,end,off in library_mappings
                   if off<=file_offset<off+end-start]
        assert len(addresses)==1
        table=addresses[0]
        match=re.search(r'sq_private_bindings=(0x[0-9a-f]+)',log_path.read_text())
        if match:assert table==int(match[1],16)
        values=[int.from_bytes(os.pread(mem.fileno(),8,table+i*8),'little') for i in range(46)]
        assert all(v and v<(1<<63) for v in values)
        operation_values=[int.from_bytes(os.pread(mem.fileno(),8,table+i*8),'little') for i in range(46,56)]
        assert all(v==0 for v in operation_values), 'User bridge must not retain native VFS operation tables'
        result=dict(status='pass',pages=rows,private_table_address=hex(table),private_table_pfn=pfn(table),
                    kernel_table_address=hex(tables[0]),kernel_table_pfn=source[native_table_page],
                    private_table_distinct_from_native=pfn(table)!=source[native_table_page],
                    binding_targets=[hex(v) for v in values],
                    operation_table_targets=[hex(v) for v in operation_values])
        assert result['private_table_distinct_from_native']
        # Optional composed LZ4 owner: each process binds its own memory helpers.
        codec=[]
        with library.open('rb') as stream:
            elf=ELFFile(stream);symbols=elf.get_section_by_name('.symtab')
            for name in ['vkso_lz4_memcpy_slot','vkso_lz4_memmove_slot','vkso_lz4_memset_slot']:
                matches=symbols.get_symbol_by_name(name)
                if not matches:continue
                symbol=matches[0];section=elf.get_section(symbol['st_shndx'])
                offset=section['sh_offset']+symbol['st_value']-section['sh_addr']
                addresses=[start+offset-off for start,end,off in library_mappings if off<=offset<off+end-start]
                assert len(addresses)==1
                address=addresses[0];value=int.from_bytes(os.pread(mem.fileno(),8,address),'little')
                assert 0<value<(1<<47)
                native=[int(f[0],16) for line in Path('/proc/kallsyms').read_text().splitlines()
                        if len(f:=line.split())==4 and f[2]==name and f[3]=='[vkso_sq_core]']
                assert len(native)==1
                (reader/'page_addresses').write_text(hex(native[0]&~4095))
                native_pfn=int(next(csv.DictReader(io.StringIO((reader/'pages').read_text())))['pfn'])
                assert pfn(address)!=native_pfn
                codec.append(dict(name=name,address=hex(address),target=hex(value),user_pfn=pfn(address),kernel_pfn=native_pfn))
        assert len(codec) in [0,3]
        if codec:result['private_codec_bindings']=codec
        # Optional XZ closure has one table of nine domain-private services.
        with library.open('rb') as stream:
            elf=ELFFile(stream)
            matches=elf.get_section_by_name('.symtab').get_symbol_by_name('sq_xz_services')
            if matches:
                symbol=matches[0];section=elf.get_section(symbol['st_shndx'])
                offset=section['sh_offset']+symbol['st_value']-section['sh_addr']
                addresses=[start+offset-off for start,end,off in library_mappings if off<=offset<off+end-start]
                assert len(addresses)==1 and symbol['st_size']==9*8
                address=addresses[0]
                values=[int.from_bytes(os.pread(mem.fileno(),8,address+8*i),'little') for i in range(9)]
                assert all(0<v<(1<<47) for v in values)
                native=[int(f[0],16) for line in Path('/proc/kallsyms').read_text().splitlines()
                        if len(f:=line.split())==4 and f[2]=='sq_xz_services' and f[3]=='[vkso_sq_core]']
                assert len(native)==1
                (reader/'page_addresses').write_text(hex(native[0]&~4095))
                native_pfn=int(next(csv.DictReader(io.StringIO((reader/'pages').read_text())))['pfn'])
                assert pfn(address)!=native_pfn
                result['private_xz_bindings']=dict(address=hex(address),targets=[hex(v) for v in values],
                    user_pfn=pfn(address),kernel_pfn=native_pfn,services=9)
    output.write_text(json.dumps(result,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=SECTION/'build/squashfs/reader-adapted')
    p.add_argument('--images',type=Path,default=SECTION/'build/squashfs/fixtures')
    p.add_argument('--reference',type=Path,default=SECTION.parent/'evaluation-local/runs/iso9660/squash-native-guest-02/evidence')
    p.add_argument('--core',default='-')
    p.add_argument('--bridge',type=Path)
    p.add_argument('--pfn-plan',type=Path)
    p.add_argument('--expect-shared',action='store_true')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); out=args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    build=args.build.resolve(); images=args.images.resolve(); target=out/'mount';target.mkdir()
    bridge=(args.bridge or build/'libsq-copy.so').resolve()
    result=dict(status='running',scope='mounted filesystem correctness; no performance or physical-sharing claim',cases=[])
    if args.pfn_plan:
        os.environ['VKSO_SQ_STATE']='1'
        result['scope']='mounted filesystem correctness and observed physical-page identity; no performance claim'
    try:
        for image in sorted(images.glob('*.squashfs')):
            expected=json.loads((args.reference/(image.stem+'-squashfs.json')).read_text())
            command=[str(build/'vkso-squashfuse'),args.core,str(bridge),str(image),'0',str(target)]
            with mounted(command,target,out/(image.stem+'.log')) as child:
                result['cases'].append(check(target,expected,out,image.stem))
                if args.pfn_plan:
                    observe(child.pid,Path(args.core),args.pfn_plan,out/(image.stem+'.log'),
                            out/(image.stem+'-pfns.json'),args.expect_shared)
            print('pass',image.name,flush=True)
        # SIF-style partition input: byte offset plus an inherited descriptor.
        offset=1048576+4097
        padded=out/'offset-image.bin'
        with padded.open('wb') as stream:
            stream.write(b'container-prefix'.ljust(offset,b'\0'))
            stream.write((images/'gzip.squashfs').read_bytes())
        fd=os.open(padded,os.O_RDONLY)
        try:
            command=[str(build/'vkso-squashfuse'),args.core,str(bridge),f'/proc/self/fd/{fd}',str(offset),str(target)]
            expected=json.loads((args.reference/'gzip-squashfs.json').read_text())
            with mounted(command,target,out/'fd-offset.log',pass_fds=(fd,)):
                result['cases'].append(check(target,expected,out,'fd-offset'))
        finally:os.close(fd)
        result['status']='pass'
    except BaseException:
        result.update(status='failed',error=traceback.format_exc());raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
