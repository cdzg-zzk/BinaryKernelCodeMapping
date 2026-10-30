#!/usr/bin/env python3
"""Final-version component ledger with the installed-platform business premise."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'optimization-20261030-01'))
from component_ledger import disk_file

ROOT=Path(__file__).resolve().parents[4]
RAW=ROOT/'test/evaluation-local/runs/iso9660'
def read(p):return json.loads(p.read_text())
def summary(v):return dict(n=len(v),median=statistics.median(v),minimum=min(v),maximum=max(v))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue',type=Path,required=True)
    p.add_argument('--resource-queue',type=Path,default=Path(__file__).with_name('resource-queue.json'))
    p.add_argument('--minimal',type=Path,default=RAW/'squash-refine-minimal-deployment-01/result.json')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    jobs=read(a.queue);records=[];stages=[];modules=None;pages=None;inputs=[]
    for job in jobs:
        if job['kind']!='application-final':continue
        run=Path(job['result']).resolve().parent;state=read(run/'result.json')
        assert state['status']=='complete' and state['restored'] and state['modules_unloaded']
        bench=run/'benchmark';b=read(bench/'result.json');codec=Path(b['image']).stem
        inputs.append(dict(run=str(run),resources_sha256=hashlib.sha256((bench/'resources.json').read_bytes()).hexdigest()))
        for variant,r in read(bench/'resources.json').items():
            for phase in ['before','after']:
                m=r[phase]['helper']['memory']
                records.append(dict(campaign=b['campaign'],codec=codec,variant=variant,phase=phase,
                    rss_kib=m['Rss'],pss_kib=m['Pss'],uss_kib=m['Private_Clean']+m['Private_Dirty'],
                    reported_vm_hwm_kib=m['VmHWM'],threads=m['Threads']))
        shared=read(bench/'vkso-pfns.json');copied=read(bench/'copied-pfns.json')
        assert all(r['shared'] for r in shared['pages']) and all(not r['shared'] for r in copied['pages'])
        assert [(r['offset'],r['mapped_page_sha256']) for r in shared['pages']]==[(r['offset'],r['mapped_page_sha256']) for r in copied['pages']]
        assert shared['private_xz_bindings']['services']==9
        n=len(shared['pages']);assert n==len({r['kernel_pfn'] for r in shared['pages']})
        if pages is None:pages=n
        assert pages==n
        current={r['name']:r['reported_bytes'] for r in read(run/'resident-modules.json')['modules']}
        if modules is None:modules=current
        assert current==modules
        stage={r['stage']:r for l in (run/'stages.jsonl').read_text().splitlines() if (r:=json.loads(l))}
        assert all(r['returncode']==0 for r in stage.values())
        stages.append(dict(campaign=b['campaign'],
            core_export_registration=sum(stage[k]['wall_seconds'] for k in ['krg','export','register']),
            construction_export=sum(stage[k]['wall_seconds'] for k in ['krg','export']),
            business_setup=sum(stage[k]['wall_seconds'] for k in ['load-vkso_sq_core','load-vkso_squashfs','krg','export','register']),
            registration=stage['register']['wall_seconds'],
            restore_unload=sum(r['wall_seconds'] for k,r in stage.items() if k=='restore' or k.startswith('unload-'))))
    assert len(inputs)==9
    controls=[read(Path(j['result'])) for j in jobs if j['kind']=='native-final'];assert len(controls)==3
    native_reference_residencies={v:sorted({r['module_residency'][v]['sq_reference'] for r in controls})
        for v in ['native-small-normal','native-small-relaxed','native-word-normal','native-word-relaxed']}
    assert all(len(v)==1 for v in native_reference_residencies.values())
    reference={r['module_residency']['native-word-normal']['sq_reference'] for r in controls};assert len(reference)==1
    reference=reference.pop()
    module=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029/modules/page_cache_replace.ko'
    sizes=subprocess.check_output(['gdb','-nx','-batch','-q',module,'-ex','p sizeof(struct transaction)','-ex','p sizeof(struct binding)'],text=True)
    tx,binding=[int(l.split('=')[1]) for l in sizes.splitlines() if l.startswith('$')]
    minimal=read(a.minimal)
    assert minimal['status']=='complete' and minimal['copied_modules_absent']
    scale=[]
    scale_jobs=read(a.resource_queue);assert len(scale_jobs)==3
    for job in scale_jobs:
        args=job['argv'];image=Path(args[args.index('--image')+1])
        count=int(image.stem.split('-')[-1]);assert count in [1,4,16]
        run=Path(job['result']).resolve().parent;assert read(run/'result.json')['status']=='complete'
        for variant,r in read(run/'benchmark/resources.json').items():
            m=r['after']['helper']['memory'];before=r['before']['helper']['memory']
            assert r['entries']==count*5866+1
            scale.append(dict(scale=count,entries=count*5866,visited_entries_including_root=r['entries'],variant=variant,
                rss_kib=m['Rss'],pss_kib=m['Pss'],uss_kib=m['Private_Clean']+m['Private_Dirty'],
                reported_vm_hwm_kib=m['VmHWM'],before_pss_kib=before['Pss'],
                after_minus_before_pss_kib=m['Pss']-before['Pss']))
    timing={key:summary([r[key] for r in stages]) for key in stages[0] if key!='campaign'}
    result=dict(status='complete',inputs=inputs,records=records,scale=scale,
        native_reference_residencies={k:v[0] for k,v in native_reference_residencies.items()},
        native_reference_boundary='Word references bundle the optimized XZ decoder in their module without replacing host kernel XZ. Original small references call the host decoder. These residency boundaries differ; neither difference estimates whole-kernel replacement or net machine memory.',
        platform=dict(module='page_cache_replace',resident_bytes=modules['page_cache_replace'],charged_to_business_bytes=0),
        business=dict(owner_resident_bytes=modules['vkso_sq_core'],native_consumer_resident_bytes=modules['vkso_squashfs'],
            native_reference='native-word-normal (bundled optimized XZ)',native_reference_resident_bytes=reference,prepared_native_resident_bytes=modules['vkso_sq_core']+modules['vkso_squashfs'],
            native_preparation_delta_bytes=modules['vkso_sq_core']+modules['vkso_squashfs']-reference,
            shared_backing_avoided_once_bytes=4096*pages,registration_requested_bytes=tx+pages*binding,
            user_only_owner_resident_bytes=modules['vkso_sq_core']),
        registration=dict(transaction_bytes=tx,binding_bytes=binding,pages=pages,debug_type_output=sizes,
            note='Requested metadata, excluding allocator rounding and other kernel allocations.'),
        deployment_stages=stages,deployment_summary=timing,minimal_deployment=minimal,
        premises=['Prepared native already resident: no second owner; avoid one shared code/RO backing, with registration and private state still required.',
            'Original native to prepared native: charge the owner/consumer increment before considering the avoided user backing.',
            'User-only: retain the owner but omit native consumer and construction observer; copied runs after all task modules unload.'],
        scope='RSS/PSS/USS are helper snapshots around include archive, before PFN/debug reads. VmHWM is the process-reported resident high-water mark. Scale runs are separate untimed observations. Module residency, backing, requested metadata, private allocations and process metrics are not summed into a calibrated whole-machine total. Ordinary copied DSOs also share among user processes.',
        setup_scope='Per owner deployment/export/registration, reused by later invocations while owner and registration remain installed. Core version/owner reload needs fresh construction and registration. Times sum stages within each campaign before aggregation, exclude compilation/validation, and do not establish copied setup is free.')
    first=next(j for j in jobs if j['kind']=='application-final')
    build=Path(first['argv'][first['argv'].index('--build')+1]);run=Path(first['result']).parent
    files={name:disk_file(path,name) for name,path in {
        'owner':build/'vkso_sq_core.ko','consumer':build/'vkso_squashfs.ko',
        'bridge':build/'libsq-bridge.so','frontend':build/'vkso-squashfuse',
        'translator':build/'vkso-squash-helper','carrier':run/'carrier/libvkso_sq_core.so',
        'copied':run/'libsq-materialized.so'}.items()}
    common=['bridge','frontend','translator'];scenarios={}
    for name,keys in [('prepared-native-shared',['owner','consumer','carrier']),
            ('prepared-native-copied',['owner','consumer','copied']),
            ('user-only-shared',['owner','carrier']),('user-only-copied',['copied'])]:
        keys=keys+common;unique={(files[k]['device'],files[k]['inode']):files[k] for k in keys}
        scenarios[name]=dict(roles=keys,logical_bytes=sum(v['logical_bytes'] for v in unique.values()),
            allocated_bytes=sum(v['allocated_bytes'] for v in unique.values()))
    result.update(disk_files=files,disk_scenarios=scenarios,
        private_data_cache=dict(entries=48,block_bytes=131072,lazy_data_byte_cap=6291456,
            note='Requested data capacity, excluding actors/pointer arrays, metadata, fragment cache and libfuse nodes.'),
        disk_scope='Evaluated unstripped files, inode-deduplicated st_blocks; common platform, dependencies and images excluded equally. No claim those dependencies are removable.')
    (out/'resources.json').write_text(json.dumps(result,indent=2)+'\n')
    print('ledger',len(records),'snapshots and',len(scale),'scale observations')


if __name__=='__main__':main()
