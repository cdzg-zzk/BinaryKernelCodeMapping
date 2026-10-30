#!/usr/bin/env python3
"""Freeze the finite data-cache confirmation; reuse only identical native runs."""
import copy, hashlib, json, time
from pathlib import Path
from elftools.elf.elffile import ELFFile
from prerequisite import ROOT, RUNS, verify

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'optimization-20261030-01'
BUILD=RUNS/'builds/data-cache-controls-02/data-48'
CONTROLS=RUNS/'builds/data48-decoder-controls-01'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')

def main():
    verify()
    gates={}
    for name,leaf in [('data48-cache-sanitize-01','sanitizer.json'),
            ('data48-functional-01','result.json'),('data48-bcj-01','result.json'),
            ('data48-lifetime-01','result.json'),('data48-guest-01','result.json'),
            ('data48-simultaneous-01','result.json'),('data48-minimal-01','result.json')]:
        p=RUNS/name/leaf;assert read(p)['status']=='complete',p;gates[str(p)]=sha(p)
    base=RUNS/'builds/optimization-cache-01'
    for n in ['vkso_sq_core.ko','vkso_squashfs.ko']:
        assert sha(BUILD/n)==sha(base/n),n
    frontend_identity={}
    for n in ['vkso-squashfuse','vkso-squash-helper']:
        with (BUILD/n).open('rb') as f,(base/n).open('rb') as g:
            current,old=ELFFile(f),ELFFile(g);checked=[]
            for section in old.iter_sections():
                if not section['sh_flags']&2 or section['sh_type']=='SHT_NOBITS':continue
                peer=current.get_section_by_name(section.name)
                assert section['sh_addr']==peer['sh_addr'] and section['sh_size']==peer['sh_size']
                if section.name=='.note.gnu.build-id':continue
                assert section.data()==peer.data(),(n,section.name)
                checked.append(section.name)
        frontend_identity[n]=dict(current_sha256=sha(BUILD/n),previous_sha256=sha(base/n),
            identical_allocated_sections=checked,
            scope='Same runtime section contents and addresses except GNU build ID; rebuild paths/debug metadata differ. Whole ELF files are not byte-identical.')
    assert sha(BUILD/'libsq-bridge.so')!=sha(base/'libsq-bridge.so')
    previous=RUNS/'confirmation-recovery-01'
    jobs=read(previous/'selected-queue.json');oldreg=read(previous/'selected-registration.json')
    for name,digest in oldreg['identities'].items():assert sha(Path(name))==digest,name
    readers=read(CONTROLS/'readers.json');readers['copied-small']={'build':str(base)}
    save(HERE/'final-readers.json',readers)
    planned={p['name']:p for p in oldreg['expected_campaigns']}
    expected=[];reused=[];pending=[];identities=dict(oldreg['identities'])
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    for job in jobs:
        original=job['name'];p=copy.deepcopy(planned[original]);args=job['argv'];kind=job['kind']
        if kind.startswith('native') and Path(job['result']).exists():
            run=Path(job['result']).parent;state=read(run/'result.json')
            assert state['status']=='complete' and state['modules_unloaded']
            assert read(run/'environment.json')['boot_id']==boot
            reused.append(dict(name=original,result=job['result'],samples_sha256=sha(run/'samples.jsonl'),
                result_sha256=sha(run/'result.json'),observations=p['observations']))
        else:
            name=original.replace('squash-optimized-','squash-data48-',1)
            # The predecessor's interrupted application replacement keeps its
            # suffix only as a name; no interrupted samples are imported.
            job['name']=p['name']=name
            for opt,value in {'--campaign':name,'--output':str(RUNS/name),
                    '--build':str(BUILD),'--extra-readers':str(HERE/'final-readers.json')}.items():
                if opt in args:args[args.index(opt)+1]=value
            if kind in ['application-final','heldout']:
                i=args.index('--variant-set')+1
                while i<len(args) and not args[i].startswith('--'):i+=1
                args.insert(i,'copied-small');p['variants'].append('copied-small')
                p['observations']+=p['blocks']*len(p['workloads'])
                if '--extra-readers' not in args:args+=['--extra-readers',str(HERE/'final-readers.json')]
            job['result']=str(RUNS/name/'result.json');assert not Path(job['result']).parent.exists()
            pending.append(job)
        expected.append(p)
    assert len(jobs)==30 and len(reused)==4 and len(pending)==26
    total=sum(p['observations'] for p in expected);assert total==8172
    for folder in [BUILD,CONTROLS]:
        for p in folder.rglob('*'):
            if p.is_file() and (p.suffix in ['.c','.h','.inc','.ko','.so'] or p.name in ['vkso-squashfuse','vkso-squash-helper','Makefile']):identities[str(p)]=sha(p)
    for name in ['final-readers.json','SELECTION.md','CACHE_PROTOCOL.md','build_data_cache.py']:
        p=HERE/name;identities[str(p)]=sha(p)
    save(HERE/'formal-queue.json',jobs);save(HERE/'pending-queue.json',pending)
    save(HERE/'registration.json',dict(created=time.time(),selection=read(BUILD.parent/'result.json'),
        selection_decision=str(HERE/'SELECTION.md'),build=str(BUILD),validation=gates,frontend_identity=frontend_identity,
        expected_campaigns=expected,expected_observations=total,identities=identities,
        queue_sha256=sha(HERE/'formal-queue.json'),pending_queue_sha256=sha(HERE/'pending-queue.json'),
        reused_native=reused,reused_native_observations=sum(x['observations'] for x in reused),
        prior_registration=str(previous/'selected-registration.json'),prior_registration_sha256=sha(previous/'selected-registration.json'),
        historical_closeout=str(RUNS/'budget-closeout-01'),
        scope='Same-core native reuse only. All user measurements are new; old pilots and interrupted user records remain excluded. Three campaigns per cell, fixed 8172 observations, one boot.'))
    print('Registered 8172 observations: 2688 native reused, 5484 pending; 30 campaigns')

if __name__=='__main__':main()
