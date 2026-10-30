#!/usr/bin/env python3
"""Freeze selection and explicit original-workload confirmation before sampling."""
import hashlib,json,shutil,time
from collections import Counter
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65';HERE=Path(__file__).resolve().parent
RUNS=(SECTION/'build/squashfs/optimization-runs-01').resolve()
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    assert not p.exists(),p
    p.write_text(json.dumps(v,indent=2)+'\n')
def values(args,opt,default=None):
    if opt not in args:return default
    result=[]
    for a in args[args.index(opt)+1:]:
        if a.startswith('--'):break
        result.append(a)
    return result
def main():
    validation=read(RUNS/'validation-queue-01/result.json')
    assert validation['status']=='complete' and len(validation['jobs'])==7
    assert read(RUNS/'pilot-queue-01/result.json')['status']=='complete'
    build=RUNS/'builds/optimization-cache-01'
    # Final acceptance is for confirmation, not a claim of universal superiority.
    selection=dict(status='selected-for-confirmation',created=time.time(),build=str(build),
        accepted=['Common scalar dictionary copy optimization, original hardening/ISA flags.',
            'Private inode/name LRU budgets 2048/4096 with live-handle pins and directory-list exclusions.'],
        rationale=['Valid-stream, guest-negative, native, shared-PFN and live-handle tests passed.',
            'Fixed pilots improve compressible XZ stream; cache-only ordinary/Python points show no >5% slowdown.',
            'Original metadata scale ladder completed; resource details are separate from timed results.'],
        unresolved=['Python XZ compilation remains about 16% slower than default stock in pilots; do not erase this.',
            'Warm native XZ archive point +5.5% triggered review: one wall delay with near-equal CPU; cause unproven.',
            'gzip startup pilot has adverse wall points; all samples retained, no equivalence claim.',
            'Hardening gap is inherited, not resolved or further relaxed. Three same-boot campaigns are not cross-boot replication.'],
        rejected=['Jump tables','small service inlining','O3','branchless rc_bit masks'],
        stopping_rule='One frozen selected candidate; fixed original block counts and three campaigns, no significance-based stopping or benchmark-input substitution.',
        validation_sha256=sha(RUNS/'validation-queue-01/result.json'))
    # Stage previously built control binaries onto the same filesystem, needed
    # by the equal-loader hardlink diagnostic. No recompilation or relabeling.
    original=SECTION/'build/squashfs/optimization-decoder-controls-01'
    controls=RUNS/'builds/optimization-decoder-controls-01'
    assert not controls.exists();shutil.copytree(original,controls)
    control_ids={}
    for p in original.rglob('*'):
        if p.is_file():
            q=controls/p.relative_to(original);assert sha(p)==sha(q)
            control_ids[str(p.relative_to(original))]=sha(q)
    readers=read(original/'readers.json')
    for row in readers.values():row['build']=str(controls/Path(row['build']).name)
    save(HERE/'decoder-readers.json',readers)
    basequeue=SECTION/'squashfs/refinement/formal-queue.json';jobs=read(basequeue);assert len(jobs)==30
    expected=[]
    for job in jobs:
        old=job['name'];name=old.replace('squash-refine-','squash-optimized-',1)
        assert name!=old;job['name']=name;args=job['argv'];kind=job['kind']
        changes={'--build':str(build),'--builds':str(HERE/'native-builds.json'),
            '--references':str(HERE/'native-references.json'),'--extra-readers':str(HERE/'decoder-readers.json'),
            '--output':str(RUNS/name),'--campaign':name}
        for option,new in changes.items():
            if option in args:args[args.index(option)+1]=new
        job['result']=str(RUNS/name/'result.json');assert not (RUNS/name).exists()
        blocks=int(values(args,'--blocks')[0])
        if kind.startswith('native'):
            builds=read(HERE/'native-builds.json');refs=read(HERE/'native-references.json')
            variants=['original',*builds,*refs];images=read(ROOT/values(args,'--image-set')[0])
            workloads=values(args,'--workloads',['archive','scan'])
            count=blocks*len(variants)*len(images['cases'])*len(workloads)*2
        else:
            variants=values(args,'--variant-set');workloads=values(args,'--workloads')
            count=blocks*len(variants)*len(workloads)*int(values(args,'--repeats')[0])
        expected.append(dict(name=name,kind=kind,blocks=blocks,variants=variants,workloads=workloads,observations=count))
    total=sum(r['observations'] for r in expected);assert total==7692,total
    bykind=Counter()
    for row in expected:bykind[row['kind']]+=row['observations']
    # Freeze execution/source hashes (not temporary compiler products).
    tracked={}
    for folder in [build,controls,SECTION/'build/squashfs/optimization-native-controls-01']:
        for p in folder.rglob('*'):
            if p.is_file() and (p.suffix in ['.c','.h','.inc','.ko','.so'] or p.name in ['vkso-squashfuse','vkso-squash-helper','Makefile']):tracked[str(p)]=sha(p)
    for p in HERE.glob('*'):
        if p.is_file() and (p.suffix in ['.c','.h','.inc'] or p.name in ['build_candidate.py','build_native_controls.py','PROTOCOL.md','native-builds.json','native-references.json','decoder-readers.json']):tracked[str(p)]=sha(p)
    for name in ['apptainer_shared.py','improvement/native_compare.py','campaign_queue.py','apptainer_bench.py','apptainer_preflight.py','check_fuse.py']:
        p=SECTION/'squashfs'/name
        assert p.is_file(),p
        tracked[str(p)]=sha(p)
    save(HERE/'formal-queue.json',jobs)
    save(HERE/'confirmation-registration.json',dict(selection=selection,expected_campaigns=expected,
        expected_observations=total,observations_by_kind=dict(bykind),
        baseline_queue_sha256=sha(basequeue),queue_sha256=sha(HERE/'formal-queue.json'),
        staged_decoder_control_identities=control_ids,identities=tracked))
    print('registered',len(jobs),'campaigns',total,'fresh observations',dict(bykind))
if __name__=='__main__':main()
