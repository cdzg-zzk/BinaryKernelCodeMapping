#!/usr/bin/env python3
"""Separate process snapshots, unique backing, support residency and deployment."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import statistics
import subprocess


def load(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def describe(values):
    return dict(n=len(values),median=statistics.median(values),minimum=min(values),maximum=max(values))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--observer-free',type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();a.runs=[r.resolve() for r in a.runs]
    if a.observer_free:a.observer_free=a.observer_free.resolve()
    records=[];metrics=collections.defaultdict(list);stages=collections.defaultdict(list)
    deployment_sums=[]
    for run in a.runs:
        result=load(run/'result.json');assert result['status']=='complete'
        bench=run/'benchmark';r=load(bench/'result.json');assert not r['pilot']
        codec=Path(r['image']).stem
        resources=load(bench/'resources.json')
        for variant,data in resources.items():
            for phase in ['before','after']:
                mem=data[phase]['helper']['memory']
                record=dict(run=str(run),campaign=r['campaign'],codec=codec,variant=variant,phase=phase,
                    rss_kib=mem['Rss'],pss_kib=mem['Pss'],uss_kib=mem['Private_Clean']+mem['Private_Dirty'],
                    threads=mem['Threads'],descendant_pss_kib=data[phase]['descendant_pss_kib'])
                records.append(record)
                for metric in ['rss_kib','pss_kib','uss_kib','threads','descendant_pss_kib']:
                    metrics[codec,variant,phase,metric].append(record[metric])
        physical=load(bench/'vkso-pfns.json')['pages']
        assert len({v['kernel_pfn'] for v in physical})==6 and all(v['shared'] for v in physical)
        stage_values={}
        for line in (run/'stages.jsonl').read_text().splitlines():
            stage=json.loads(line);assert stage['returncode']==0
            assert stage['stage'] not in stage_values
            stage_values[stage['stage']]=stage['wall_seconds']
            if stage['stage'].startswith(('load-','unload-')) or stage['stage'] in ['krg','export','register','restore']:
                stages[stage['stage']].append(dict(campaign=r['campaign'],seconds=stage['wall_seconds']))
        setup=['load-'+name for name in ['vkso_sq_core','vkso_squashfs','vkso_kernel_reader','page_cache_replace']]+['krg','export','register']
        teardown=['restore']+['unload-'+name for name in ['vkso_sq_core','vkso_squashfs','vkso_kernel_reader','page_cache_replace']]
        deployment_sums.append(dict(campaign=r['campaign'],
            setup_command_sum_seconds=sum(stage_values[s] for s in setup),
            teardown_command_sum_seconds=sum(stage_values[s] for s in teardown),
            export_construction_seconds=stage_values['krg']+stage_values['export']))
    first=a.runs[0];module_rows=load(first/'resident-modules.json')['modules']
    for run in a.runs:
        assert {m['name']:m['reported_bytes'] for m in load(run/'resident-modules.json')['modules']}=={
            m['name']:m['reported_bytes'] for m in module_rows}
    root=Path(__file__).resolve().parents[3]
    support=root/'test/evaluation-local/packages/iso9660-native-optimized-20261029'
    binary=support/'modules/page_cache_replace.ko'
    source=root/'test/section65/build/native/modules/registration/page_cache_replace.c'
    build_binary=source.parent/'page_cache_replace.ko'
    assert sha(binary)==sha(build_binary)
    artifacts=[]
    env=load(first/'benchmark/environment.json')
    for filename,expected in env['binaries'].items():
        path=Path(filename);assert sha(path)==expected
        artifacts.append(dict(path=str(path.relative_to(root)),bytes=path.stat().st_size,sha256=expected,
            role='Evaluated executable or library; includes alternative backends, not a summed deployment package.'))
    for path,role in [(binary,'Registration module'),(support/'manager','One-shot registration/restore command'),
                      (support/'krg','Offline export construction tool'),(support/'vmlinux','Offline matching-kernel export input'),
                      (support/'modules/vkso_kernel_reader.ko','Optional PFN observation module')]:
        artifacts.append(dict(path=str(path.relative_to(root)),bytes=path.stat().st_size,sha256=sha(path),role=role))
    carrier=next((first/'carrier').glob('lib*.so'))
    artifacts.append(dict(path=str(carrier.relative_to(root)),bytes=carrier.stat().st_size,sha256=sha(carrier),
        role='One completed campaign carrier after restoration; disk footprint, not unique live physical backing.'))
    sizes=subprocess.check_output(['gdb','-nx','-batch','-q',str(binary),
        '-ex','p sizeof(struct transaction)','-ex','p sizeof(struct binding)'],text=True)
    values=[int(line.split('=')[1]) for line in sizes.splitlines() if line.startswith('$')]
    assert len(values)==2
    tx,binding=values
    registration=dict(binary=str(binary.relative_to(root)),sha256=sha(binary),
        source=str(source.relative_to(root)),source_sha256=sha(source),dwarf_size_output=sizes,
        transaction_requested_bytes=tx,binding_requested_bytes=binding,shared_pages=6,
        direct_requested_bytes=tx+6*binding,
        mechanism='kzalloc(transaction) and kvcalloc(page_count,binding). Successful apply drops both references to displaced ordinary pages; restore reloads unchanged carrier data from its filesystem.',
        exclusions=['slab rounding and allocator metadata','netlink sockets and transient messages',
                    'file/inode/xarray objects','page tables','exporter and manager peak memory'])
    native_preparation=[]
    for kind in ['normal-module','relaxed-module']:
        for i in range(1,4):
            run=root/'test/evaluation-local/runs/iso9660'/f'squash-native-{kind}-formal-{i:02d}'
            if not (run/'result.json').exists():continue
            state=load(run/'result.json')
            if state['status']!='complete':continue
            sizes={m['name']:m['reported_bytes'] for m in load(run/'resident-modules.json')['modules']}
            prepared=sizes['vkso_sq_core']+sizes['vkso_squashfs']
            native_preparation.append(dict(source=str(run),reference=kind,
                reference_module_bytes=sizes['sq_reference'],prepared_owner_and_consumer_bytes=prepared,
                preparation_residency_delta_bytes=prepared-sizes['sq_reference'],
                scope='Same-version patched module comparison; reported resident module bytes only. Dynamic allocations and the original built-in driver are excluded from both sides.'))
    observer=None
    deployment_resources=[]
    if a.observer_free:
        observer=load(a.observer_free/'result.json')
        assert observer['status']=='complete' and observer['observer_free_application']['status']=='pass'
        for path in sorted(a.observer_free.glob('*-resource.txt')):
            fields={}
            for line in path.read_text().splitlines():
                for key,name in [('Maximum resident set size (kbytes):','maxrss_kib'),
                                 ('User time (seconds):','user_seconds'),('System time (seconds):','system_seconds')]:
                    if line.strip().startswith(key):fields[name]=float(line.strip()[len(key):])
            assert len(fields)==3,path
            deployment_resources.append(dict(stage=path.name.removesuffix('-resource.txt'),
                source=str(path),sha256=sha(path),**fields))
        assert deployment_resources
    result=dict(status='complete',scope='Untimed per-campaign idle snapshots before/after include archive; descriptive ranges, not memory peaks or net machine savings.',
        records=records,summaries=[dict(codec=k[0],variant=k[1],phase=k[2],metric=k[3],**describe(v)) for k,v in sorted(metrics.items())],
        stages=[dict(stage=k,samples=v,seconds=describe([r['seconds'] for r in v])) for k,v in sorted(stages.items())],
        deployment_command_sums=deployment_sums,
        deployment_scope='Measured setup/teardown sums include loading/unloading the optional PFN observer used by this evidence harness. Individual stages are retained. Observer-free evidence proves subsequent real application execution without that module; it is not a separately measured observer-free construction workflow.',
        deployment_summary={key:describe([r[key] for r in deployment_sums]) for key in
            ['setup_command_sum_seconds','teardown_command_sum_seconds','export_construction_seconds']},
        kernel_module_residency=module_rows,registration=registration,
        deployment_artifact_files=artifacts,
        deployment_artifact_scope='Raw file sizes identify retained deployment/construction inputs with their respective debug/symbol information; this is not a normalized stripped-binary comparison. They are not summed into an installed-package total: shared dynamic libraries, Python, kernel SDK/source and ordinary application assets are separate prerequisites. vmlinux/krg are offline construction inputs, not resident helper processes.',
        native_preparation_module_residency=native_preparation,
        unique_shared_bytes=6*4096,private_state=[dict(run=str(run),variant=v,**load(run/'benchmark'/(v+'-private-state.json'))) for run in a.runs for v in ['copied','vkso']],
        observer_free_evidence=dict(path=str(a.observer_free),result=observer) if observer else None,
        deployment_command_resources=deployment_resources,
        accounting_cases=[
          dict(assumption='Prepared owner and native consumer already resident for kernel work; registration support already deployed.',
               scope='24 KiB of duplicate file backing avoided once per common core, with per-registration metadata and user-private state additional. No N-times code saving over an ordinary shared DSO.'),
          dict(assumption='Prepared owner and native consumer already resident; registration module dedicated to this user task.',
               scope='32 KiB registration module alone exceeds the 24 KiB duplicated code/rodata removed; this deployment does not establish net memory savings.'),
          dict(assumption='Owner, native consumer and registration added solely for user reuse.',
               scope='52+40+32 KiB reported module residency, plus dynamic allocation. Original built-in SquashFS remains resident in this experiment. Optional observation module adds 20 KiB during evidence collection.')],
        limitations=['PFN count is physical reuse, not process RSS or net savings.',
          'Process PSS does not account kernel-owner residency; summing it with module bytes is not a calibrated whole-machine total.',
          'Resident module sizes omit dynamic allocations; source-request accounting is a subset.',
          'Process snapshots omit host backing-image cache, FUSE kernel caches, tmpfs output and page tables.',
          'Archive snapshots do not establish peak memory or concurrent scaling.',
          'GNU time maxrss describes the maximum resident-set counter returned for the command/children, not simultaneous process-tree PSS or whole-machine peak memory.',
          'Setup command sums add actual stages within each campaign, excluding compilation, package acquisition and functional validation between stages. They are not sums of unrelated medians.',
          'Deployment stage samples are whole command durations; startup and cleanup components are not obtained by subtracting unrelated medians.'])
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(campaigns=len(a.runs),snapshots=len(records),registration_requested_bytes=tx+6*binding)))


if __name__=='__main__':main()
