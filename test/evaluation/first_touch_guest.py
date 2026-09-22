#!/usr/bin/env python3
"""Exercise the complete raw-sample first-touch protocol in an isolated guest."""
from pathlib import Path
import ctypes,csv,json,os,subprocess,sys,traceback
from lz4_guest_helpers import execute,observe_registered_pages,verify_restored_pages,write_json
ROOT=Path('/work');OUT=ROOT/'validation';WORK=OUT/'export';REPO=ROOT/'repo'

def functional():
    fields=dict(x.split('=',1) for x in (WORK/'vkso/metadata/outputs.env').read_text().splitlines())
    library=Path(fields['library']);native=ROOT/'native/libclone_xxh32.so'
    # Check executed instruction bytes, not merely matching source labels.
    a=ctypes.CDLL(str(library));b=ctypes.CDLL(str(native));oracle=ctypes.CDLL(str(ROOT/'oracle/libxxhash.so.0'))
    fa=a.zzk_xxh32;fb=b.clone_xxh32;fo=oracle.XXH32
    for fn in (fa,fb,fo): fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint32];fn.restype=ctypes.c_uint32
    aa=ctypes.cast(fa,ctypes.c_void_p).value;bb=ctypes.cast(fb,ctypes.c_void_p).value
    kernel_bytes=ctypes.string_at(aa,338);native_bytes=ctypes.string_at(bb,338)
    assert kernel_bytes==native_bytes
    (OUT/'registered-function.bin').write_bytes(kernel_bytes);(OUT/'native-function.bin').write_bytes(native_bytes)
    from applicability_runtime_audit import hash_vectors
    rows=[]
    for index,(kind,length,alignment,seed,data) in enumerate(hash_vectors()):
        buf=ctypes.create_string_buffer(len(data)+alignment+1);address=ctypes.addressof(buf)+alignment
        ctypes.memmove(address,data,len(data));expected=fo(address,length,seed)
        left,right=fa(address,length,seed),fb(address,length,seed)
        assert left==right==expected,(index,left,right,expected)
        rows.append(dict(index=index,kind=kind,length=length,alignment=alignment,seed=seed,expected=expected,stub=left,native=right))
    assert len(rows)==247;write_json(OUT/'functional.json',dict(status='pass',rows=rows,matched_function_bytes=338))
def validate():
    if (ROOT/'first-touch-scenario').exists():
        from first_touch_pressure import validate as pressure_validate
        return pressure_validate()
    fields=dict(x.split('=',1) for x in (WORK/'vkso/metadata/outputs.env').read_text().splitlines())
    library=Path(fields['library']);native=ROOT/'native/libclone_xxh32.so'
    execute(['python3',ROOT/'guest.py','--functional'],OUT/'functional-process.log')
    # The independent validator has exited: no persistent native DSO mapping
    # may keep its code page mapped during the post-drop condition.
    assert str(native) not in Path('/proc/self/maps').read_text()
    (OUT/'controller-maps-before-sampling.txt').write_text(Path('/proc/self/maps').read_text())
    pages=observe_registered_pages(library,Path(fields['page_map']))
    assert len(pages['pages'])==1
    assert int(Path('/sys/module/zzk_xxh32_lkm/refcnt').read_text())==1
    env=dict(os.environ,STUB_DSO=str(library),NATIVE_DSO=str(native),CPU='1',NUM_RUNS='100',
             TARGET_SUCCESSES='5',MAX_ATTEMPTS='20',THRESHOLD_PCT='90.0',
             CSV_FILE=str(OUT/'first-touch.csv'),LOG_DIR=str(OUT/'first-touch.logs'))
    # Preserve incomplete acceptance as evidence, independently of functional
    # success. The runner must never lower its threshold to force a pass.
    with (OUT/'first-touch-runner.log').open('w') as log:
        r=subprocess.run(['bash','run_benchmarks.sh'],cwd=ROOT/'benchmark',env=env,stdout=log,stderr=subprocess.STDOUT)
    assert r.returncode in (0,2),r.returncode
    with (OUT/'first-touch-analysis.json').open('w') as report,(OUT/'first-touch-analysis.stderr').open('w') as err:
        analysis=subprocess.run(['python3',ROOT/'benchmark/analyze_first_touch.py',OUT/'first-touch.logs'],stdout=report,stderr=err)
    assert analysis.returncode==r.returncode,(analysis.returncode,r.returncode)
    observe_registered_pages(library,Path(fields['page_map']))
    write_json(OUT/'collection-status.json',dict(status='complete' if r.returncode==0 else 'incomplete',
        runner_exit=r.returncode,analysis_exit=analysis.returncode,scope='full raw-sample protocol; guest times not physical-host performance'))

def main():
    OUT.mkdir();loaded=[]
    result=dict(status='running',kernel=os.uname().release,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        scope='complete Native/Stub first-touch raw protocol in private exact119 KVM')
    try:
        assert os.geteuid()==0 and os.uname().release=='5.15.0-119-generic'
        for name,path in [('zzk_xxh32_lkm',ROOT/'owner/zzk_xxh32_lkm.ko'),
            ('vkso_kernel_reader',ROOT/'helpers/vkso_kernel_reader.ko'),('page_cache_replace',REPO/'page_cache_replace/page_cache_replace.ko')]:
            execute(['insmod',path],OUT/f'load-{name}.log');loaded.append(name)
        execute([REPO/'vkso','init',WORK,'--symbols',ROOT/'symbols.txt'],OUT/'init.log')
        execute([REPO/'vkso','exec',WORK,'--symbols',ROOT/'symbols.txt','--module',ROOT/'owner/zzk_xxh32_lkm.ko',
            '--owner-ko',ROOT/'owner/zzk_xxh32_lkm.ko','--api-header',ROOT/'api.h','--vmlinux',ROOT/'vmlinux-5.15.0-119-generic',
            '--','python3',ROOT/'guest.py','--validate'],OUT/'export-and-first-touch.log')
        verify_restored_pages();result['restoration_verified']=True
        result['collection']=json.loads((OUT/'collection-status.json').read_text());result['status']='pass'
    except BaseException: result.update(status='fail',error=traceback.format_exc())
    finally:
        log=WORK/'vkso/metadata/page_replace.log';safe=not log.exists() or not log.stat().st_size
        if log.exists():
            try:
                if not result.get('restoration_verified'): verify_restored_pages()
                safe=True
            except BaseException: result['release_error']=traceback.format_exc();result['status']='fail'
        for name in reversed(loaded) if safe else ():
            try: execute(['rmmod',name],OUT/f'unload-{name}.log')
            except BaseException: result.setdefault('cleanup_errors',[]).append(traceback.format_exc());result['status']='fail'
        result['modules_after']=Path('/proc/modules').read_text()
        (OUT/'dmesg.txt').write_text(subprocess.check_output(['dmesg'],text=True))
        write_json(OUT/'status.json',result);os.sync()
    print('first_touch_guest_validation='+result['status'],flush=True)
    return 0 if result['status']=='pass' else 1
if __name__=='__main__':
    if sys.argv[1:]==['--validate']: validate()
    elif sys.argv[1:]==['--functional']: functional()
    else: raise SystemExit(main())
