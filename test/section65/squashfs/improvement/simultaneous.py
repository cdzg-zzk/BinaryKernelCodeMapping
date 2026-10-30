#!/usr/bin/env python3
"""Native A and two actual SIF applications B/C: shared instructions, private state."""
import argparse, concurrent.futures, hashlib, json, os
from pathlib import Path
import pwd, shlex, shutil, subprocess, sys, tarfile, tempfile, time, traceback
ROOT=Path(__file__).resolve().parents[4];SECTION=ROOT/'test/section65';HERE=SECTION/'squashfs'
sys.path.insert(0,str(SECTION));sys.path.insert(0,str(HERE))
from squashfs.apptainer_bench import snapshot, descendants
from squashfs.apptainer_preflight import archive_manifest
from squashfs.check_fuse import observe
SUPPORT=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029'

def full_manifest(path):
    rows=archive_manifest(path)
    with tarfile.open(path) as archive:
        for member in archive:rows[member.name]['mtime']=member.mtime
    return rows

def object_pfns(pid,state):
    addresses={k:state[k] for k in ['image_address','filesystem_address','stream_address']}
    for c in state['caches']:
        addresses[c['kind']]=c['cache_address'];addresses[c['kind']+'_buffer']=c['buffer_addresses'][0]
    result={}
    with open(f'/proc/{pid}/mem','rb',buffering=0) as mem,open(f'/proc/{pid}/pagemap','rb',buffering=0) as pm:
        for name,value in addresses.items():
            address=int(value,16);assert 0<address<1<<47
            assert len(os.pread(mem.fileno(),1,address))==1
            entry=int.from_bytes(os.pread(pm.fileno(),8,(address//4096)*8),'little');assert entry>>63
            pfn=entry&((1<<55)-1);assert pfn
            result[name]=dict(address=value,pfn=pfn)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--images',type=Path,required=True);p.add_argument('--build',type=Path,required=True)
    p.add_argument('--trace-xz',action='store_true',help='one hardware breakpoint in a real shared application, outside timing')
    p.add_argument('--user',default='zzk');a=p.parse_args();assert os.geteuid()==0
    account=pwd.getpwnam(a.user);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);out.chmod(0o755)
    build=a.build.resolve();images={c['label']:c for c in json.loads(a.images.read_text())['cases']}
    shutil.copy2(__file__,out/'runner.py');shutil.copy2(a.images,out/'images.json')
    app=SECTION/'build/squashfs/apptainer/jammy/usr/bin/apptainer'
    target=out/'native';target.mkdir();loaded=[];registered=False;library=None;children={};logs=[];known_pids=set();debuggers=[]
    result=dict(status='running',scope='Integration correctness and physical/private-state identity, not timing or throughput.',
        ownership_scope='Native retains image uid/gid; Apptainer supplies uid/gid=invoking user through FUSE mount options. Compare those specified application semantics; preserve differing mode, mtime, content and links.',cases=[],phases=[],binaries={n:hashlib.sha256((build/n).read_bytes()).hexdigest() for n in ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse']})
    write=lambda:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def command(argv,label,cwd=None):
        with (out/(label+'.log')).open('w') as f:subprocess.run(list(map(str,argv)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
    def mount(label,fs):
        c=images[label];command(['mount','-t',fs,'-o','ro,loop,offset='+str(c['offset']),c['image'],target],fs+'-'+label+'-mount')
    def wait(path,child):
        deadline=time.monotonic()+120
        while not path.exists():
            assert child.poll() is None,(str(path),child.returncode)
            assert time.monotonic()<deadline,('timeout',str(path));time.sleep(.005)
    write()
    try:
        oracles={}
        for label in images:
            mount(label,'squashfs');oracles[label]={}
            try:
                for phase in range(8):
                    archive=out/f'oracle-{label}-{phase}.tar';subtree=target/f'opt/domain/phase{phase}'
                    command(['tar','-cf',archive,'-C',subtree,'.'],f'oracle-{label}-{phase}')
                    oracles[label][phase]=dict(manifest=full_manifest(archive),range=(subtree/'data').read_bytes()[4093:4350].hex())
                    archive.unlink()
            finally:command(['umount',target],'oracle-'+label+'-unmount')
        assert len({oracles[l][0]['manifest']['./data']['sha256'] for l in images})==3
        (out/'oracles.json').write_text(json.dumps(oracles,indent=2)+'\n')
        for name in ['vkso_sq_core','vkso_squashfs','vkso_kernel_reader','page_cache_replace']:
            assert not (Path('/sys/module')/name).exists()
            command(['insmod',(build if name in ['vkso_sq_core','vkso_squashfs'] else SUPPORT/'modules')/(name+'.ko')],'load-'+name);loaded.append(name)
        carrier=out/'carrier';carrier.mkdir()
        for name in ['symbols.txt','shim.txt']:shutil.copy2(build/name,carrier/name)
        command([SUPPORT/'krg','build',SUPPORT/'vmlinux','--module',build/'vkso_sq_core.ko','-o',carrier/'out.krg'],'krg')
        command([sys.executable,ROOT/'make_dll/build_PIC_so.py','--symbols',carrier/'symbols.txt','--krg',carrier/'out.krg',
            '--ko',build/'vkso_sq_core.ko','--shim-list',carrier/'shim.txt','--vmlinux',SUPPORT/'vmlinux'],'export',carrier)
        library=next(carrier.glob('lib*.so')).resolve();before=library.read_bytes();plan=carrier/'page_mappings.txt'
        command([SUPPORT/'manager','replace',library,plan],'register',SUPPORT);registered=True
        copied=out/'libsq-materialized.so';copied.write_bytes(library.read_bytes())
        for variant,core in [('copied',copied),('shared',library)]:
            mount('A','vksosquash')
            with tempfile.TemporaryDirectory(prefix='vkso-domain-',dir='/dev/shm') as tmp:
                root=Path(tmp);root.chmod(0o755);work={}
                for label,phases in [('B',8),('C',3)]:
                    w=root/label;w.mkdir();os.chown(w,account.pw_uid,account.pw_gid);work[label]=w
                    d=out/(variant+'-'+label);d.mkdir();d.chmod(0o755)
                    for n in ['cache','config','tmp']:(d/n).mkdir();os.chown(d/n,account.pw_uid,account.pw_gid)
                    trace=d/'trace.jsonl';trace.touch();os.chown(trace,account.pw_uid,account.pw_gid)
                    helper=d/'squashfuse_ll';helper.write_text('#!/bin/sh\nexec '+shlex.join([str(build/'vkso-squash-helper'),'--frontend',str(build/'vkso-squashfuse'),
                        '--kind','reader','--core',str(core),'--bridge',str(build/'libsq-bridge.so'),'--trace',str(trace),'--'])+' "$@"\n');helper.chmod(0o755)
                    conf=d/'apptainer.conf';conf.write_text((app.parent.parent/'etc/apptainer/apptainer.conf').read_text()+'\nbinary path = '+str(d)+':$PATH:/usr/bin:/bin\n')
                    script='set -e; touch /work/ready; '
                    for phase in range(phases):
                        script+=f'while [ ! -e /work/go{phase} ]; do sleep 0.01; done; touch /work/start{phase}; '
                        script+=f'/usr/bin/tar -cf /work/out{phase}.tar -C /opt/domain/phase{phase} .; '
                        script+=f'dd if=/opt/domain/phase{phase}/data of=/work/range{phase} bs=1 skip=4093 count=257 2>/dev/null; touch /work/done{phase}; '
                    script+='while [ ! -e /work/finish ]; do sleep 0.01; done'
                    env=dict(os.environ,APPTAINER_CACHEDIR=str(d/'cache'),APPTAINER_CONFIGDIR=str(d/'config'),APPTAINER_TMPDIR=str(d/'tmp'),
                        LD_LIBRARY_PATH=str(SECTION/'build/squashfs/apptainer/runtime/usr/lib/x86_64-linux-gnu'))
                    argv=['runuser','-u',a.user,'--','taskset','-c','1,2',str(app),'--config',str(conf),'exec','--contain','--cleanenv','--no-home','--no-mount','cwd','--pwd','/work',
                        '--bind',str(w)+':/work',images[label]['image'],'/bin/sh','-c',script]
                    log=(d/'application.log').open('w');logs.append(log)
                    children[label]=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
                for label in children:
                    wait(work[label]/'ready',children[label]);known_pids.update(descendants(children[label].pid))
                observations={}
                for label,child in children.items():
                    pid=snapshot(child.pid,build/'vkso-squashfuse')['helper']['pid'];observations[label]=dict(pid=pid)
                    observe(pid,core,plan,out/(variant+'-'+label)/'application.log',out/f'{variant}-{label}-pfns-before.json',variant=='shared')
                for phase in range(8):
                    live=['B','C'] if phase<3 else ['B'];started=time.monotonic_ns()
                    debugger=None
                    if a.trace_xz and variant=='shared' and phase==3:
                        ready=out/'xz-breakpoint-ready';script=out/'xz-breakpoint.gdb'
                        script.write_text('set pagination off\nset confirm off\nhbreak *vkso_xz_dec_run\ncommands\nsilent\nprintf "XZ_SHARED_EXECUTION rdi=%p rsi=%p\\n", $rdi, $rsi\nx/6gx $rsi\nbt 8\ndisable 1\ndetach\nquit\nend\npython open('+repr(str(ready))+', "w").close()\ncontinue\n')
                        debugger_log=(out/'xz-breakpoint.log').open('w');logs.append(debugger_log)
                        debugger=subprocess.Popen(['gdb','-nx','-batch','-q','-p',str(observations['B']['pid']),'-x',str(script)],stdout=debugger_log,stderr=subprocess.STDOUT)
                        debuggers.append(debugger)
                        wait(ready,debugger)
                    def native_task():
                        start=time.monotonic_ns();wall_start=time.time_ns();archive=root/f'A-{phase}.tar';subtree=target/f'opt/domain/phase{phase}'
                        subprocess.run(['taskset','-c','3','tar','-cf',archive,'-C',subtree,'.'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                        end=time.monotonic_ns();wall_end=time.time_ns();assert full_manifest(archive)==oracles['A'][phase]['manifest'];archive.unlink()
                        with (subtree/'data').open('rb') as f:f.seek(4093);assert f.read(257).hex()==oracles['A'][phase]['range']
                        return dict(start_ns=start,end_ns=end,wall_start_ns=wall_start,wall_end_ns=wall_end)
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        for label in live:(work[label]/f'go{phase}').touch()
                        for label in live:wait(work[label]/f'start{phase}',children[label])
                        future=executor.submit(native_task) if phase<6 else None
                        for label in live:wait(work[label]/f'done{phase}',children[label])
                        native=future.result() if future else None
                    if debugger:
                        assert debugger.wait(timeout=30)==0
                        assert 'XZ_SHARED_EXECUTION' in (out/'xz-breakpoint.log').read_text()
                        observe(observations['B']['pid'],core,plan,out/'shared-B/application.log',out/'shared-B-pfns-after-xz-breakpoint.json',True)
                        result['xz_user_execution']='Hardware breakpoint at the shared decoder entry during actual SIF phase 3; arguments, stack and unchanged shared PFNs recorded.'
                    intervals={label:dict(wall_start_ns=(work[label]/f'start{phase}').stat().st_mtime_ns,
                        wall_end_ns=(work[label]/f'done{phase}').stat().st_mtime_ns) for label in live}
                    if native:intervals['A']={k:native[k] for k in ['wall_start_ns','wall_end_ns']}
                    overlap=min(v['wall_end_ns'] for v in intervals.values())-max(v['wall_start_ns'] for v in intervals.values())
                    for label in live:
                        archive=work[label]/f'out{phase}.tar'
                        observed=full_manifest(archive)
                        (out/f'{variant}-{label}-{phase}-observed.json').write_text(json.dumps(observed,indent=2)+'\n')
                        expected=json.loads(json.dumps(oracles[label][phase]['manifest']))
                        for row in expected.values():row.update(uid=account.pw_uid,gid=account.pw_gid)
                        assert observed==expected,(variant,label,phase)
                        # Apptainer explicitly supplies uid/gid mount overrides; other metadata stays image-specific.
                        assert (work[label]/f'range{phase}').read_bytes().hex()==oracles[label][phase]['range']
                        archive.unlink()
                    result['phases'].append(dict(variant=variant,phase=phase,live=['A',*live] if phase<6 else live,
                        release_ns=started,complete_ns=time.monotonic_ns(),native=native,task_intervals=intervals,
                        task_lifecycle_overlap_ns=max(0,overlap),overlap_scope='Tar/read task envelopes, not sampled simultaneous instruction execution or throughput.',
                        outputs='match own image; content, metadata, links, and boundary range'))
                    if phase==2:
                        private={}
                        for label in ['B','C']:
                            pid=observations[label]['pid'];state_path=out/f'{variant}-{label}-state.json'
                            with (out/f'{variant}-{label}-gdb.log').open('w') as log:
                                subprocess.run(['gdb','-nx','-batch','-q','-p',str(pid),'-ex','add-symbol-file '+str(SECTION/'build/squashfs/debug-types-01/types.o')+' 0',
                                    '-ex','python exec(open('+repr(str(HERE/'private_state_gdb.py'))+').read())'],
                                    env=dict(os.environ,VKSO_SNAPSHOT_OUTPUT=str(state_path)),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
                            state=json.loads(state_path.read_text());assert state['status']=='pass';private[label]=object_pfns(pid,state)
                            observe(pid,core,plan,out/(variant+'-'+label)/'application.log',out/f'{variant}-{label}-pfns-after.json',variant=='shared')
                        assert {r['pfn'] for r in private['B'].values()}.isdisjoint(r['pfn'] for r in private['C'].values())
                        b=json.loads((out/f'{variant}-B-pfns-after.json').read_text());c=json.loads((out/f'{variant}-C-pfns-after.json').read_text())
                        assert b['private_table_pfn']!=c['private_table_pfn']
                        assert [r['user_pfn'] for r in b['pages']]==[r['user_pfn'] for r in c['pages']], 'ordinary copied DSO also shares among users'
                        (out/f'{variant}-private-object-pfns.json').write_text(json.dumps(private,indent=2)+'\n')
                        (work['C']/'finish').touch();assert children['C'].wait(timeout=30)==0;del children['C']
                    if phase==5:command(['umount',target],variant+'-A-unmount')
                    write()
                (work['B']/'finish').touch();assert children['B'].wait(timeout=30)==0;del children['B']
            overlapping=[p['phase'] for p in result['phases'] if p['variant']==variant and p['phase']<3 and p['task_lifecycle_overlap_ns']>0]
            assert overlapping, 'No observed A/B/C task-lifecycle overlap; simultaneous-task evidence incomplete'
            result['cases'].append(dict(variant=variant,status='pass',phases=8,three_consumer_overlap_phases=overlapping,consumer_cleanup_order=['C','A','B'],
                private_objects_disjoint=True,user_code_shared_between_processes=True,user_code_shared_with_kernel=variant=='shared'));write()
        # A fresh native mount after both user cohorts have exited.
        mount('A','vksosquash')
        command(['tar','-cf',out/'native-after.tar','-C',target/'opt/domain/phase7','.'],'native-after')
        assert full_manifest(out/'native-after.tar')==oracles['A'][7]['manifest'];(out/'native-after.tar').unlink()
        command(['umount',target],'native-after-unmount')
        command([SUPPORT/'manager','restore',library,plan],'restore',SUPPORT);registered=False;assert library.read_bytes()==before
        result.update(status='complete',restored=True,native_after=True)
        for label in ['copied-B','copied-C','shared-B','shared-C']:
            trace=[json.loads(line) for line in (out/label/'trace.jsonl').read_text().splitlines()]
            assert trace and all(row['source'].startswith('/proc/self/fd/') and row['offset']>0 for row in trace)
        result['real_fd_and_partition_offsets']=True
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:
        for debugger in debuggers:
            if debugger.poll() is None:
                debugger.terminate()
                try:debugger.wait(timeout=10)
                except subprocess.TimeoutExpired:debugger.kill();debugger.wait()
        for child in children.values():
            if child.poll() is None:child.terminate()
        for child in children.values():
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        for pid in known_pids:
            try:
                commandline=Path('/proc',str(pid),'cmdline').read_bytes()
                if b'vkso-squashfuse' in commandline or b'fuse-overlayfs' in commandline:os.kill(pid,15)
            except (OSError,ProcessLookupError):pass
        time.sleep(.2)
        for log in logs:log.close()
        try:
            if os.path.ismount(target):command(['umount',target],'cleanup-native')
            if registered:command([SUPPORT/'manager','restore',library,plan],'cleanup-restore',SUPPORT)
            for name in reversed(loaded):command(['rmmod',name],'unload-'+name)
            result['modules_unloaded']=True
        except BaseException:result.update(status='failed',cleanup_error=traceback.format_exc());raise
        finally:write()
if __name__=='__main__':main()
