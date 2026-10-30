#!/usr/bin/env python3
"""Isolated guest VKSO proof: real kernel consumer, complete reads, PFNs, restoration."""
import csv
import ctypes as C
import io
import json
import mmap
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import sys
import time
import traceback

WORK=Path('/work'); OUT=WORK/'evidence'; CARRIER=WORK/'carrier'
def write(path,data): path.write_text(json.dumps(data,indent=2)+'\n')
def command(argv, name, cwd=None):
    with (OUT/(name+'.log')).open('w') as stream:
        p=subprocess.run(list(map(str,argv)),cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
    with (OUT/'commands.jsonl').open('a') as f: f.write(json.dumps(dict(argv=list(map(str,argv)),returncode=p.returncode))+'\n')
    if p.returncode: raise RuntimeError(name+' returned '+str(p.returncode))
def mappings():
    return [(int(o,0),int(a,0),k,s) for line in (CARRIER/'page_mappings.txt').read_text().splitlines()
            if line and not line.startswith('#') for o,a,k,s in [line.split(',')]]
def source_pfns(plan):
    reader=Path('/sys/kernel/debug/vkso_kernel_reader')
    (reader/'page_addresses').write_text(' '.join(hex(a) for _,a,_,_ in plan))
    raw=(reader/'pages').read_text(); (OUT/'source-pages.csv').write_text(raw)
    return {int(r['kernel_vaddr'],0):int(r['pfn']) for r in csv.DictReader(io.StringIO(raw))}
def page_pfn(address):
    C.c_ubyte.from_address(address).value
    fd=os.open('/proc/self/pagemap',os.O_RDONLY)
    try: entry,=struct.unpack('Q',os.pread(fd,8,address//4096*8))
    finally: os.close(fd)
    assert entry & (1<<63)
    pfn=entry&((1<<55)-1); assert pfn
    return pfn
def observe(lib, output, expected_shared):
    plan=mappings(); kernel=source_pfns(plan); rows=[]
    for line in Path('/proc/self/maps').read_text().splitlines():
        fields=line.split(maxsplit=5)
        if len(fields)!=6 or fields[5]!=str(lib): continue
        start,end=(int(x,16) for x in fields[0].split('-')); off=int(fields[2],16)
        for offset,address,kind,section in plan:
            if off<=offset<off+end-start:
                pfn=page_pfn(start+offset-off)
                row=dict(offset=offset,kernel_address=hex(address),kernel_pfn=kernel[address],user_pfn=pfn,
                         shared=pfn==kernel[address],kind=kind,permissions=fields[1])
                assert row['shared']==expected_shared and 'w' not in fields[1],row
                rows.append(row)
    assert len(rows)==len(plan),(len(rows),len(plan))
    write(output,dict(status='pass',pages=rows))
def worker(mode):
    import check_user
    lib=next(CARRIER.glob('lib*.so')).resolve()
    if mode=='copied': lib=WORK/'materialized/libiso-copied.so'
    core=C.CDLL(str(lib),mode=C.RTLD_GLOBAL)
    # Bind the per-process dependency table before any common code call.
    bridge=WORK/'libiso-bridge.so'
    handle=check_user.load(bridge)
    dest=OUT/mode
    assert check_user.run(bridge,WORK/'images',WORK/'reference',dest)
    observe(lib,dest/'pfns.json',mode!='copied')
    # The writable table lives in this process, despite shared instructions.
    core.iso_support_address.restype=C.c_void_p
    table=(C.c_void_p*29).from_address(core.iso_support_address())
    entries=list(table)
    assert all(p and p < (1<<63) for p in entries),entries
    write(dest/'bindings.json',dict(table_address=hex(C.addressof(table)),table_pfn=page_pfn(C.addressof(table)),
                                   targets=[hex(p) for p in entries]))
    if mode.startswith('vkso-parallel'):
        (dest/'ready').touch()
        deadline=time.monotonic()+90
        while not (WORK/'release-workers').exists():
            assert time.monotonic()<deadline,'private-state rendezvous timed out'
            time.sleep(.05)
    print('iso_user_worker_pass='+mode,flush=True)
def kernel_cases(label='adapted-kernel'):
    from reference_guest import manifest
    mountpoint=Path('/mnt/iso'); mountpoint.mkdir(exist_ok=True,parents=True)
    dest=OUT/label; dest.mkdir()
    cases=json.loads((WORK/'reference/result.json').read_text())['cases']
    results=[]
    for index,c in enumerate(cases):
        options='ro,loop'+(',norock' if c['mode']=='norock' else '')
        command(['mount','-t','vksoiso','-o',options,WORK/'images'/c['image'],mountpoint],'mount-'+str(index))
        try: rows=manifest(mountpoint)
        finally: command(['umount',mountpoint],'unmount-'+str(index))
        expected=json.loads((WORK/'reference'/c['manifest']).read_text())
        write(dest/c['manifest'],rows)
        assert rows==expected,c
        results.append(c)
    write(dest/'result.json',dict(status='pass',cases=results))
def maintenance_kernel(fstype, label, fixed):
    if not (WORK/'maintenance').exists(): return
    from check_maintenance import observe
    mount=WORK/'maintenance-mount';mount.mkdir(exist_ok=True)
    expected=json.loads((WORK/'maintenance/expected.json').read_text())
    command(['mount','-t',fstype,'-o','ro,loop',WORK/'maintenance/long-joliet.iso',mount],label+'-mount')
    try:
        result=observe(mount,expected,fixed)
        write(OUT/(label+'.json'),result)
    finally:
        command(['umount',mount],label+'-unmount')

def restored(lib):
    plan=mappings(); source=source_pfns(plan); result=[]
    with lib.open('rb') as stream:
        for offset,address,_,_ in plan:
            with mmap.mmap(stream.fileno(),4096,access=mmap.ACCESS_COPY,offset=offset) as mapping:
                location=C.addressof(C.c_ubyte.from_buffer(mapping))
                pfn=page_pfn(location)
                assert pfn!=source[address]
                result.append(dict(offset=offset,user_pfn=pfn,kernel_pfn=source[address]))
    write(OUT/'restored.json',dict(status='pass',pages=result))
def main():
    OUT.mkdir(); CARRIER.mkdir()
    status=dict(status='running',scope='TCG functional proof only; no performance conclusion',stage='load')
    manager=None; fifo_fd=None; restored_ok=False
    registration_mode=(WORK/'registration-mode').read_text().strip() if (WORK/'registration-mode').exists() else 'hold'
    assert registration_mode in ('hold','oneshot')
    registered=False;lib=None;log=None
    status['registration_mode']=registration_mode
    try:
        for module in ('vkso_iso_core','vkso_isofs','vkso_kernel_reader','page_cache_replace'):
            command(['insmod',WORK/(module+'.ko')],'load-'+module)
        write(OUT/'modules.json',dict(modules=Path('/proc/modules').read_text()))
        status['stage']='kernel-reference'; write(OUT/'result.json',status)
        kernel_cases()
        maintenance_kernel('vksoiso','maintenance-kernel-fixed',True)
        status['stage']='krg'; write(OUT/'result.json',status)
        command([WORK/'krg','build',WORK/'vmlinux','--module',WORK/'vkso_iso_core.ko','-o',CARRIER/'out.krg'],'krg')
        status['stage']='carrier'; write(OUT/'result.json',status)
        command(['python3',WORK/'build_PIC_so.py','--symbols',WORK/'symbols.txt','--krg',CARRIER/'out.krg',
                 '--ko',WORK/'vkso_iso_core.ko','--shim-list',WORK/'shim.txt','--vmlinux',WORK/'vmlinux'],
                 'build-carrier',cwd=CARRIER)
        lib=next(CARRIER.glob('lib*.so')).resolve()
        # Preserve file zero pages for post-restore comparison.
        write(OUT/'carrier-before.json',dict(bytes=lib.stat().st_size,mappings=mappings()))
        status['stage']='register'; write(OUT/'result.json',status)
        if registration_mode=='oneshot':
            command([WORK/'manager','replace',lib,CARRIER/'page_mappings.txt'],'manager-register-oneshot')
            # Completion of the synchronous registration command establishes that
            # its process has exited before any user consumer is launched.
            running=[]
            for proc in Path('/proc').iterdir():
                if not proc.name.isdigit():continue
                try:
                    if (proc/'exe').resolve()==WORK/'manager':running.append(int(proc.name))
                except (FileNotFoundError,PermissionError):pass
            assert not running,running
            write(OUT/'registration-lifecycle.json',dict(mode='oneshot',registration_process_exited=True,
                live_manager_pids=running,release='explicit restore after consumers finish'))
        else:
            fifo=WORK/'notify'; os.mkfifo(fifo); fifo_fd=os.open(fifo,os.O_RDWR|os.O_NONBLOCK)
            log=(OUT/'manager.log').open('w')
            manager=subprocess.Popen([str(WORK/'manager'),'replace',str(lib),str(CARRIER/'page_mappings.txt'),
                                      '--hold','--notify-fifo',str(fifo)],stdout=log,stderr=subprocess.STDOUT)
            events=b''; deadline=time.monotonic()+60
            while b'READY 0 ' not in events:
                assert manager.poll() is None, 'manager exited'
                assert time.monotonic()<deadline,'registration timed out'
                if select.select([fifo_fd],[],[],1)[0]: events+=os.read(fifo_fd,4096)
            (OUT/'manager-events.txt').write_bytes(events)
            (OUT/'manager-smaps-rollup.txt').write_text(Path('/proc',str(manager.pid),'smaps_rollup').read_text())
            (OUT/'manager-status.txt').write_text(Path('/proc',str(manager.pid),'status').read_text())
            (OUT/'manager-maps.txt').write_text(Path('/proc',str(manager.pid),'maps').read_text())
        registered=True
        status['stage']='active-user'; write(OUT/'result.json',status)
        (WORK/'materialized').mkdir()
        # Explicit read copies active kernel page bytes, retaining all ELF offsets.
        (WORK/'materialized/libiso-copied.so').write_bytes(lib.read_bytes())
        for mode in ('vkso','copied'):
            command(['python3',WORK/'guest.py','--worker',mode],mode)
        # Two separate processes execute simultaneously with independent tables/caches.
        children=[]
        for mode in ('vkso-parallel-a','vkso-parallel-b'):
            stream=(OUT/(mode+'.log')).open('w')
            children.append((subprocess.Popen(['python3',str(WORK/'guest.py'),'--worker',mode],stdout=stream,stderr=subprocess.STDOUT),stream))
        # Exercise the real kernel consumer while the user mappings remain active.
        kernel_cases('kernel-while-shared')
        deadline=time.monotonic()+60
        while not all((OUT/m/'ready').exists() for m in ('vkso-parallel-a','vkso-parallel-b')):
            assert all(child.poll() is None for child,_ in children),'parallel worker exited early'
            assert time.monotonic()<deadline,'parallel workers timed out'
            time.sleep(.05)
        tables=[json.loads((OUT/m/'bindings.json').read_text())['table_pfn'] for m in ('vkso-parallel-a','vkso-parallel-b')]
        assert tables[0]!=tables[1],tables
        write(OUT/'private-state.json',dict(status='pass',simultaneous_table_pfns=tables))
        (WORK/'release-workers').touch()
        for child,stream in children:
            assert child.wait()==0; stream.close()
        status['parallel_workers']=2
        if (WORK/'vkso-isofuse').exists():
            status['stage']='fuse';write(OUT/'result.json',status)
            os.environ['LD_LIBRARY_PATH']=str(WORK)
            if not Path('/dev/fuse').exists():
                import stat
                os.mknod('/dev/fuse',stat.S_IFCHR|0o600,os.makedev(10,229))
            for mode,selected in [('vkso',lib),('copied',WORK/'materialized/libiso-copied.so')]:
                argv=['python3',WORK/'check_fuse.py','--frontend',WORK/'vkso-isofuse',
                    '--core',selected,'--bridge',WORK/'libiso-bridge.so','--images',WORK/'images',
                    '--reference',WORK/'reference','--output',OUT/('fuse-'+mode)]
                if mode=='vkso':argv.append('--shared')
                command(argv,'fuse-'+mode)
            status['stage']='gdb';write(OUT/'result.json',status)
            (WORK/'debug-mount').mkdir()
            command(['gdb','-q','-nx','-batch','-ex','source /work/fuse_gdb.py','--args',
                WORK/'vkso-isofuse',lib,WORK/'libiso-bridge.so',WORK/'images/mixed.iso','0',
                WORK/'debug-mount'],'gdb')
            assert json.loads((OUT/'debug/result.json').read_text())['status']=='pass'
            kernel_cases('kernel-after-debug')
            status['fuse_and_debug']='pass'
            if (WORK/'maintenance').exists():
                for name,core,fixed,shared in [('before',WORK/'maintenance-before.so',False,False),
                    ('fixed-copy',WORK/'materialized/libiso-copied.so',True,False),
                    ('fixed-vkso',lib,True,True)]:
                    argv=['python3',WORK/'check_maintenance.py','--frontend',WORK/'vkso-isofuse',
                        '--core',core,'--bridge',WORK/'libiso-bridge.so','--case',WORK/'maintenance',
                        '--output',OUT/('maintenance-'+name)]
                    if fixed: argv.append('--fixed')
                    if shared: argv.append('--shared')
                    command(argv,'maintenance-'+name)
                status['maintenance']='pass'
        status['stage']='restore'; write(OUT/'result.json',status)
        if registration_mode=='oneshot':
            command([WORK/'manager','restore',lib,CARRIER/'page_mappings.txt'],'manager-restore-oneshot')
        else:
            manager.send_signal(signal.SIGTERM); assert manager.wait(timeout=30)==0; manager=None; log.close()
        restored(lib); restored_ok=True
        # Unload the consumer first, then the common owner, proving normal release.
        for module in ('vkso_isofs','vkso_iso_core','page_cache_replace','vkso_kernel_reader'):
            command(['rmmod',module],'unload-'+module)
        command(['insmod',WORK/'isofs_probe.ko'],'load-original-footprint')
        maintenance_kernel('iso9660','maintenance-kernel-original',False)
        (OUT/'original-modules.txt').write_text(Path('/proc/modules').read_text())
        command(['rmmod','isofs_probe'],'unload-original-footprint')
        status['status']='complete'; status['stage']='complete'
    except BaseException:
        status['status']='failed'; status['error']=traceback.format_exc(); raise
    finally:
        if manager and manager.poll() is None:
            manager.terminate(); manager.wait(timeout=30)
        if registration_mode=='oneshot' and registered and not restored_ok:
            try:
                command([WORK/'manager','restore',lib,CARRIER/'page_mappings.txt'],'manager-restore-after-failure')
            except BaseException:
                status['cleanup_error']=traceback.format_exc()
        if fifo_fd is not None: os.close(fifo_fd)
        status['restoration_verified']=restored_ok
        write(OUT/'result.json',status)
        # Raw KRG is reproducible and large; archive compact deployment metadata.
        import shutil
        (OUT/'carrier-metadata').mkdir(exist_ok=True)
        for p in CARRIER.glob('*.txt'): shutil.copy2(p,OUT/'carrier-metadata'/p.name)
if __name__=='__main__':
    if len(sys.argv)>1: worker(sys.argv[2])
    else: main()
