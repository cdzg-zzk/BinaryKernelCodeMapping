#!/usr/bin/env python3
"""Account final-core process snapshots, dependency removal and deployment separately."""
import argparse,collections,hashlib,json,re,statistics,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
RAW=ROOT/'test/evaluation-local/runs/iso9660'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def describe(v):return dict(n=len(v),median=statistics.median(v),minimum=min(v),maximum=max(v))
def smaps(path):
    rows=[]
    for line in path.read_text().splitlines():
        if re.match(r'^[0-9a-f]+-[0-9a-f]+ ',line):
            parts=line.split(maxsplit=5);rows.append(dict(mapping=parts[5] if len(parts)>5 else '',permissions=parts[1],metrics={}))
        elif rows and re.match(r'^[A-Za-z_]+:\s+\d+ kB$',line):
            name,value,_=line.split();rows[-1]['metrics'][name[:-1]]=int(value)
    assert rows
    return rows
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--queue',required=True,type=Path)
    p.add_argument('--minimal',required=True,type=Path);p.add_argument('--directory',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    runs=[Path(j['result']).resolve().parent for j in load(a.queue) if 'application-improved' in j['name']]
    assert len(runs)==9
    records=[];metrics=collections.defaultdict(list);stage_groups=collections.defaultdict(list);deployment=[];private=[];dependencies=[];inputs=[]
    module_reference=None;shared_count=None
    for run in runs:
        state=load(run/'result.json');assert state['status']=='complete' and state['restored'] and state['modules_unloaded']
        bench=run/'benchmark';r=load(bench/'result.json');assert not r['pilot'] and 'precede PFN' in r['resource_observation_order']
        codec=Path(r['image']).stem;campaign=r['campaign'];resources=load(bench/'resources.json')
        inputs.append(dict(run=str(run),resources_sha256=sha(bench/'resources.json')))
        for variant,data in resources.items():
            for phase in ['before','after']:
                mem=data[phase]['helper']['memory'];maps=smaps(bench/f'{variant}-helper-smaps-{phase}.txt')
                library=[m for m in maps if re.search(r'/liblz4\.so',m['mapping'])]
                if variant in ['copied','vkso']:assert not library,(campaign,variant,phase)
                if variant.startswith('copied-'):assert library,(campaign,variant,phase)
                record=dict(campaign=campaign,codec=codec,variant=variant,phase=phase,rss_kib=mem['Rss'],pss_kib=mem['Pss'],
                    uss_kib=mem['Private_Clean']+mem['Private_Dirty'],threads=mem['Threads'],
                    descendant_pss_kib=data[phase]['descendant_pss_kib'],liblz4_mappings=len(library),
                    liblz4_rss_kib=sum(m['metrics'].get('Rss',0) for m in library),liblz4_pss_kib=sum(m['metrics'].get('Pss',0) for m in library))
                records.append(record)
                for key in ['rss_kib','pss_kib','uss_kib','threads','descendant_pss_kib','liblz4_rss_kib','liblz4_pss_kib']:
                    metrics[codec,variant,phase,key].append(record[key])
        physical=load(bench/'vkso-pfns.json')['pages'];copied=load(bench/'copied-pfns.json')['pages']
        n=len({v['kernel_pfn'] for v in physical});assert n==len(physical) and all(v['shared'] for v in physical)
        assert all(not v['shared'] for v in copied)
        assert [(v['offset'],v['mapped_page_sha256']) for v in copied]==[(v['offset'],v['mapped_page_sha256']) for v in physical]
        if shared_count is None:shared_count=n
        assert n==shared_count
        modules={m['name']:m['reported_bytes'] for m in load(run/'resident-modules.json')['modules']}
        if module_reference is None:module_reference=modules
        assert modules==module_reference
        for variant in ['copied','vkso']:
            private.append(dict(campaign=campaign,codec=codec,variant=variant,**load(bench/f'{variant}-private-state.json')))
        stages=[json.loads(line) for line in (run/'stages.jsonl').read_text().splitlines()]
        by_name={s['stage']:s for s in stages};assert len(by_name)==len(stages) and all(s['returncode']==0 for s in stages)
        for name,s in by_name.items():
            if name.startswith(('load-','unload-')) or name in ['krg','export','register','restore']:stage_groups[name].append(dict(campaign=campaign,seconds=s['wall_seconds']))
        setup=['load-'+n for n in ['vkso_sq_core','vkso_squashfs','vkso_kernel_reader','page_cache_replace']]+['krg','export','register']
        teardown=['restore']+['unload-'+n for n in ['vkso_sq_core','vkso_squashfs','vkso_kernel_reader','page_cache_replace']]
        deployment.append(dict(campaign=campaign,setup_command_sum_seconds=sum(by_name[s]['wall_seconds'] for s in setup),
            teardown_command_sum_seconds=sum(by_name[s]['wall_seconds'] for s in teardown),export_construction_seconds=by_name['krg']['wall_seconds']+by_name['export']['wall_seconds']))
    support=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029';registration=support/'modules/page_cache_replace.ko'
    sizes=subprocess.check_output(['gdb','-nx','-batch','-q',str(registration),'-ex','p sizeof(struct transaction)','-ex','p sizeof(struct binding)'],text=True)
    tx,binding=[int(l.split('=')[1]) for l in sizes.splitlines() if l.startswith('$')]
    assert sha(registration)=='c483fee64b76d3a50cb0e7ad871c2fa665388d8531a53025cebf0ce48ac91b30'
    minimal=load(a.minimal/'result.json');assert minimal['status']=='complete' and minimal['copied_modules_absent']
    assert {m['name'] for m in minimal['runtime_modules']}=={'vkso_sq_core','page_cache_replace'}
    directory=load(a.directory/'result.json');assert directory['status']=='complete'
    for path in sorted(a.minimal.glob('*-resources.txt')):
        fields={}
        for line in path.read_text().splitlines():
            for key,name in [('Maximum resident set size (kbytes):','maxrss_kib'),('User time (seconds):','user_seconds'),('System time (seconds):','system_seconds')]:
                if line.strip().startswith(key):fields[name]=float(line.strip()[len(key):])
        assert len(fields)==3;dependencies.append(dict(stage=path.name.removesuffix('-resources.txt'),**fields))
    paired=[]
    for codec in ['gzip','lz4']:
        for phase in ['before','after']:
            for metric in ['rss_kib','pss_kib','uss_kib']:
                differences=[]
                for campaign in sorted({r['campaign'] for r in records if r['codec']==codec}):
                    values={r['variant']:r[metric] for r in records if r['campaign']==campaign and r['phase']==phase}
                    differences.append(dict(campaign=campaign,difference=values['copied']-values['copied-library']))
                paired.append(dict(codec=codec,phase=phase,metric=metric,comparison='copied minus copied-library',samples=differences,**describe([r['difference'] for r in differences])))
    references=[]
    for kind in ['normal-module','relaxed-module']:
        source=RAW/f'squash-native-{kind}-formal-01/resident-modules.json';m={r['name']:r['reported_bytes'] for r in load(source)['modules']}
        references.append(dict(reference=kind,source=str(source),reference_module_bytes=m['sq_reference'],
            final_prepared_module_bytes=module_reference['vkso_sq_core']+module_reference['vkso_squashfs'],
            residency_delta_bytes=module_reference['vkso_sq_core']+module_reference['vkso_squashfs']-m['sq_reference']))
    optimized_references=[]
    controls=[j for j in load(a.queue.parent/'bounded-control-queue.json') if 'bounded-control-formal' in j['name']];assert len(controls)==3
    for job in controls:
        path=Path(job['result']).resolve();r=load(path);assert r['status']=='complete'
        optimized_references.append(dict(source=str(path),modules=r['module_residency']))
    result=dict(status='complete',scope='Idle helper snapshots around include-tree archive, preceding PFN/debugger observation. Descriptive campaign ranges; not peaks or net machine savings.',
        inputs=inputs,records=records,summaries=[dict(codec=k[0],variant=k[1],phase=k[2],metric=k[3],**describe(v)) for k,v in sorted(metrics.items())],
        library_removal_paired_differences=paired,shared_pages=shared_count,unique_shared_bytes=4096*shared_count,private_state=private,
        directory_live_storage=directory,kernel_module_residency=module_reference,native_preparation_module_residency=references,optimized_native_module_residency=optimized_references,
        registration=dict(binary_sha256=sha(registration),dwarf_size_output=sizes,transaction_requested_bytes=tx,binding_requested_bytes=binding,direct_requested_bytes=tx+shared_count*binding,
            mechanism='Successful grafting releases displaced carrier-page references; restoring reloads the unchanged on-disk carrier. Requested metadata excludes allocation rounding, file/xarray structures, page tables and messages.'),
        stages=[dict(stage=k,samples=v,seconds=describe([r['seconds'] for r in v])) for k,v in sorted(stage_groups.items())],
        deployment_command_sums=deployment,deployment_summary={k:describe([r[k] for r in deployment]) for k in ['setup_command_sum_seconds','teardown_command_sum_seconds','export_construction_seconds']},
        minimal_deployment=dict(source=str(a.minimal.resolve()),result=minimal,command_resources=dependencies,stages=[json.loads(l) for l in (a.minimal/'stages.jsonl').read_text().splitlines()]),
        accounting_cases=[
          dict(assumption='Prepared core and registration support already resident',duplicate_backing_avoided_once_bytes=4096*shared_count,additional_registration_requested_bytes=tx+shared_count*binding,
            interpretation='Avoided backing is shared across ordinary copied consumers as well; no process-count multiplier. Private objects and kernel allocations remain additional.'),
          dict(assumption='Prepared native core resident, registration dedicated',registration_module_bytes=module_reference['page_cache_replace'],
            interpretation='Registration module exceeds avoided code/rodata backing even before per-registration metadata; core-backing accounting does not establish a net saving.'),
          dict(assumption='Core and support deployed solely for user use',runtime_module_bytes=sum(m['reported_bytes'] for m in minimal['runtime_modules']),copied_runtime_task_modules=0,
            interpretation='Observed user-only deployment omits the native consumer and construction observer; copied executes after all task modules unload.'),
          dict(assumption='Full native and user deployment',runtime_module_bytes=sum(v for k,v in module_reference.items() if k!='vkso_kernel_reader'),construction_observer_bytes=module_reference['vkso_kernel_reader'])],
        limitations=['Module residency omits dynamic allocations; process PSS and module bytes must not be added as a calibrated whole-machine total.',
          'Library removal benefits copied and VKSO and is not a saving caused solely by physical sharing.',
          'RSS/PSS/USS snapshots exclude host backing cache, FUSE kernel caches, tmpfs output and page tables. GNU time maxrss is not simultaneous process-tree PSS.',
          'Deployment sums use stages within each campaign, exclude compilation and validation, and include the construction observer. Minimal-deployment commands have one observed workflow, not timing confidence intervals.',
          'The retained temporary decoded-output buffer still costs 128 KiB; direct decoding removes a copy, not this allocation.'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print('resource ledger complete',len(records),'snapshots')
if __name__=='__main__':main()
