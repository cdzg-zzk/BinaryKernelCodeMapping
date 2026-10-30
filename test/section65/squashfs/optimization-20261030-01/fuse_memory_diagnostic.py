#!/usr/bin/env python3
"""Attribute original-scale retention to live FUSE tables/slabs and bridge counts.

Untimed, ordinary-user, task-owned mounts only. No module or global settings.
The diagnostic frontend differs only by a private nonexistent-path checkpoint.
Matching uninstrumented replays quantify the probe's footprint separately.
"""
import argparse,hashlib,json,os,shlex,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65'
HERE=Path(__file__).resolve().parent;RUNS=(SECTION/'build/squashfs/optimization-runs-01').resolve()
sys.path.insert(0,str(SECTION/'squashfs'))
from check_fuse import mounted

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert os.geteuid()!=0,'use ordinary user for isolated FUSE replay'
    assert read(RUNS/'formal-recovery-queue-01/result.json')['status']=='complete'
    assert read(RUNS/'postprocess-02/result.json')['status']=='complete'
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    base=RUNS/'builds/optimization-cache-01'
    library=Path('/lib/x86_64-linux-gnu/libfuse3.so.3').resolve()
    version=subprocess.check_output(['dpkg-query','-W','-f=${Version}','libfuse3-3'],text=True)
    assert version=='3.10.5-1build1',version
    source=base/'xz-user-source/fuse_frontend.c'
    text=source.read_text();assert text.count('static void *image_handle;')==1
    text=text.replace('static void *image_handle;','static void *image_handle;\n#include "fuse_memory_probe.inc"')
    marker='static int sq_getattr(const char *path, struct stat *st, struct fuse_file_info *fi)\n{'
    assert text.count(marker)==1
    text=text.replace(marker,marker+'\n    if(path && !strcmp(path,"/.vkso-diag-memory-checkpoint")) { probe_memory(); return -ENOENT; }')
    (out/'frontend.c').write_text(text)
    flags=['gcc','-O2','-g','-DVKSO_SQ_DIRECTORY_CACHE','-I'+str(HERE),'-I'+str(SECTION/'build/fuse-deps/usr/include/fuse3'),
           str(out/'frontend.c'),'-Wl,-l:libfuse3.so.3','-ldl','-o',str(out/'frontend')]
    with (out/'build.log').open('w') as log:subprocess.run(flags,stdout=log,stderr=subprocess.STDOUT,check=True)
    core=RUNS/'squash-optimized-application-final-gzip-01/libsq-materialized.so'
    state=dict(status='running',cases=[],build_argv=flags,libfuse_version=version,libfuse_sha256=sha(library),
        inputs={str(x):sha(x) for x in [source,HERE/'fuse_memory_probe.inc',base/'libsq-bridge.so',core]},
        scope='Same original scale SIFs and include-tree tar. Direct FUSE replay excludes Apptainer startup; no timing claim. Private libfuse ABI observations are version/hash-locked and consistency-checked. Slab reservation, hash requested bytes and process PSS are distinct quantities, not an automatic net-memory total.')
    save(out/'result.json',state)
    try:
        for scale in [1,4,16]:
            image=SECTION/'build/squashfs/refine-scale-images-01'/f'scale-{scale}.sif'
            oracle=None
            for variant in ['production','instrumented']:
                case=out/f'scale-{scale}-{variant}';case.mkdir();target=case/'mount';target.mkdir()
                binary=base/'vkso-squashfuse' if variant=='production' else out/'frontend'
                argv=['taskset','-c','1',str(binary),str(core),str(base/'libsq-bridge.so'),str(image),'36864',str(target)]
                row=dict(scale=scale,variant=variant,image_sha256=sha(image),snapshots=[],archives=[])
                with mounted(argv,target,case/'daemon.log') as child:
                    def snapshot(label):
                        maps=Path(f'/proc/{child.pid}/smaps').read_text();(case/(label+'-smaps.txt')).write_text(maps)
                        memory={}
                        for line in Path(f'/proc/{child.pid}/smaps_rollup').read_text().splitlines():
                            fields=line.split()
                            if len(fields)==3 and fields[2]=='kB':memory[fields[0].rstrip(':')]=int(fields[1])
                        item=dict(phase=label,memory_kib=memory)
                        if variant=='instrumented':
                            previous=len((case/'daemon.log').read_text().splitlines())
                            try:(target/'.vkso-diag-memory-checkpoint').stat()
                            except FileNotFoundError:pass
                            else:raise AssertionError('diagnostic path unexpectedly exists')
                            lines=(case/'daemon.log').read_text().splitlines()[previous:]
                            records=[json.loads(l.removeprefix('FUSE_MEMORY ')) for l in lines if l.startswith('FUSE_MEMORY ')]
                            assert len(records)==1,lines;item['live_objects']=records[0]
                            assert records[0]['bridge_inodes']<=2048 and records[0]['bridge_names']<=4096
                        row['snapshots'].append(item)
                    snapshot('before')
                    for index in range(2):
                        archive=case/f'headers-{index}.tar'
                        assert shutil.disk_usage(out).free>2*1024**3
                        with (case/f'tar-{index}.log').open('w') as log:
                            subprocess.run(['tar','-cf',str(archive),'-C',str(target/'opt/linux-headers'),'.'],stdout=log,stderr=subprocess.STDOUT,check=True)
                        snapshot(f'after-{index}')
                        digest=sha(archive)
                        if oracle is None:oracle=digest
                        assert digest==oracle,('archive mismatch',scale,variant,index)
                        row['archives'].append(dict(path=str(archive),sha256=digest,bytes=archive.stat().st_size))
                row.update(unmounted=not os.path.ismount(target),daemon_returncode=child.returncode)
                state['cases'].append(row);save(out/'result.json',state);print(scale,variant,'complete',flush=True)
        state['status']='complete'
    except BaseException:state.update(status='failed',error=traceback.format_exc());raise
    finally:save(out/'result.json',state)

if __name__=='__main__':main()
