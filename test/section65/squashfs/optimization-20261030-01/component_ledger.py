#!/usr/bin/env python3
"""Separate saved process memory, physical identity and actual disk allocation."""
import argparse,errno,hashlib,json,os,re,subprocess
from collections import defaultdict
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65'
RUNS=Path('/var/tmp/vkso-section65-optimization-20261030-hBcg9Y')
FIELDS=['Size','Rss','Pss','Shared_Clean','Shared_Dirty','Private_Clean','Private_Dirty','Anonymous','Swap']

def sha(p):
    digest=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):digest.update(block)
    return digest.hexdigest()
def read(p):return json.loads(p.read_text())
def smaps(path):
    rows=[];current=None
    for line in path.read_text().splitlines():
        if re.match(r'^[0-9a-f]+-[0-9a-f]+ ',line):
            words=line.split(maxsplit=5)
            current=dict(address=words[0],permissions=words[1],offset=int(words[2],16),device=words[3],inode=int(words[4]),path=words[5] if len(words)==6 else '')
            rows.append(current)
        elif ':' in line and current is not None:
            key,value=line.split(':',1)
            if key in FIELDS:current[key]=int(value.split()[0])
    groups=defaultdict(lambda:dict.fromkeys(FIELDS,0))
    for row in rows:
        name=row['path'];base=Path(name).name
        if name=='[heap]':group='private_heap_mapping'
        elif not name:group='anonymous_mappings_unattributed'
        elif name.startswith('[stack'):group='stack'
        elif name.startswith('['):group='kernel_supplied_special'
        elif base in ['libvkso_sq_core.so','libsq-materialized.so'] or base.startswith('core-'):group='core_carrier_or_copy'
        elif base.startswith('libsq-bridge'):group='private_bridge_file'
        elif base in ['vkso-squashfuse','frontend']:group='frontend_file'
        elif name.endswith('.sif'):group='image_file'
        elif '.so' in base or base.startswith('ld-'):group='dynamic_library_files'
        else:group='other_file_mappings'
        row['group']=group
        for key in FIELDS:groups[group][key]+=row.get(key,0)
    total={key:sum(r.get(key,0) for r in rows) for key in FIELDS}
    return dict(path=str(path),sha256=sha(path),units='KiB',total=total,groups=dict(groups),mappings=rows)

def disk_file(path,role):
    from elftools.elf.elffile import ELFFile
    actual=path.resolve();st=actual.stat()
    record=dict(path=str(path),resolved=str(actual),role=role,logical_bytes=st.st_size,allocated_bytes=st.st_blocks*512,
        device=st.st_dev,inode=st.st_ino,links=st.st_nlink,sha256=sha(actual))
    with actual.open('rb') as f:
        if f.read(4)==b'\x7fELF':
            f.seek(0);elf=ELFFile(f)
            sections=[dict(name=s.name,type=s['sh_type'],offset=s['sh_offset'],bytes=s['sh_size'],flags=s['sh_flags']) for s in elf.iter_sections()]
            record['sections']=sections
            record['section_file_bytes']={
                'executable':sum(s['bytes'] for s in sections if s['flags']&4 and s['type']!='SHT_NOBITS'),
                'allocated_readonly':sum(s['bytes'] for s in sections if s['flags']&2 and not s['flags']&5 and s['type']!='SHT_NOBITS'),
                'allocated_writable':sum(s['bytes'] for s in sections if s['flags']&3==3 and s['type']!='SHT_NOBITS'),
                'debug':sum(s['bytes'] for s in sections if s['name'].startswith('.debug'))}
    return record

def main():
    p=argparse.ArgumentParser();p.add_argument('--smaps',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.smaps:
        result=smaps(a.smaps);a.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(total=result['total'],groups=result['groups']),indent=2));return
    assert read(RUNS/'formal-recovery-queue-01/result.json')['status']=='complete'
    assert read(RUNS/'postprocess-02/result.json')['status']=='complete'
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    mapped=[]
    for scale in [1,4,16]:
        folder=RUNS/f'resource-scale-{scale:02d}-01/benchmark';resources=read(folder/'resources.json')
        for variant in resources:
            for phase in ['before','after']:
                row=smaps(folder/f'{variant}-helper-smaps-{phase}.txt')
                row.update(scale=scale,variant=variant,phase=phase)
                # Same phase; raw per-VMA integer PSS rounding can differ slightly
                # from smaps_rollup. Keep both rather than forcing equality.
                row['reported_process_snapshot']=resources[variant][phase]['helper']['memory']
                mapped.append(row)
    run=RUNS/'squash-optimized-application-final-gzip-01';build=RUNS/'builds/optimization-cache-01'
    inputs={
        'owner':build/'vkso_sq_core.ko','native-consumer':build/'vkso_squashfs.ko',
        'bridge':build/'libsq-bridge.so','frontend':build/'vkso-squashfuse','translator':build/'vkso-squash-helper',
        'carrier':run/'carrier/libvkso_sq_core.so','copied':run/'libsq-materialized.so',
        'platform':ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029/modules/page_cache_replace.ko'}
    files={key:disk_file(path,key) for key,path in inputs.items()}
    ldd_logs={};dependencies=set()
    for key in ['bridge','frontend','translator','carrier','copied']:
        check=subprocess.run(['ldd',str(inputs[key])],capture_output=True,text=True)
        ldd_logs[key]=dict(returncode=check.returncode,stdout=check.stdout,stderr=check.stderr)
        assert check.returncode==0,(key,check.stderr)
        assert 'not found' not in check.stdout
        for line in check.stdout.splitlines():
            for value in line.strip().split():
                if value.startswith('/') and Path(value).is_file():dependencies.add(Path(value).resolve())
    deps=[disk_file(path,'existing_dynamic_dependency') for path in sorted(dependencies)]
    def footprint(keys):
        selected={ (files[k]['device'],files[k]['inode']):files[k] for k in keys }
        return dict(roles=keys,unique_inodes=len(selected),logical_bytes=sum(v['logical_bytes'] for v in selected.values()),
            allocated_bytes=sum(v['allocated_bytes'] for v in selected.values()))
    common=['bridge','frontend','translator']
    scenarios={
        'prepared_native_plus_shared':footprint(['owner','native-consumer','carrier',*common]),
        'same_prepared_native_plus_copied':footprint(['owner','native-consumer','copied',*common]),
        'user_only_shared_business':footprint(['owner','carrier',*common]),
        'user_only_copied_business':footprint(['copied',*common])}
    plan=[int(line.split(',')[0],0) for line in (run/'carrier/page_mappings.txt').read_text().splitlines() if line and not line.startswith('#')]
    assert len(plan)==9
    page_contents=[]
    with inputs['carrier'].open('rb') as c,inputs['copied'].open('rb') as d:
        for offset in plan:
            c.seek(offset);d.seek(offset);left=c.read(4096);right=d.read(4096)
            assert len(left)==len(right)==4096
            page_contents.append(dict(offset=offset,carrier_all_zero=not any(left),copy_all_zero=not any(right),
                carrier_sha256=hashlib.sha256(left).hexdigest(),copied_sha256=hashlib.sha256(right).hexdigest()))
    images=[]
    for directory in ['application-images-01','heldout-python-images-01','refine-scale-images-01']:
        for image in sorted((SECTION/'build/squashfs'/directory).glob('*.sif')):
            images.append(disk_file(image,'unchanged_common_workload_image'))
    deployment=[disk_file(path,'deployment_or_diagnostic_metadata') for path in sorted((run/'carrier').iterdir()) if path.is_file() and path!=inputs['carrier']]
    minimal=read(RUNS/'minimal-deployment-01/result.json');assert minimal['status']=='complete'
    result=dict(status='complete',memory_mappings=mapped,disk=dict(files=files,dependencies=deps,dependency_resolution=ldd_logs,
        matched_scenarios=scenarios,shared_page_content=page_contents,images=images,deployment_metadata=deployment),
        boundaries=[
            'Scenario file totals include unstripped evaluated files including debug sections; no stripped-production execution is claimed.',
            'Logical length differs from filesystem allocated blocks. Counts are inode-deduplicated within a scenario; not a claim about compression, reflinks, backup or storage-wide net physical usage.',
            'The generic platform is a separately shown installed prerequisite, not charged per filesystem. Include it when asking about a machine without that platform.',
            'Existing dynamic dependencies and identical application images are reported separately and shared across consumers. Removing a DT_NEEDED entry does not prove a library can be deleted system-wide.',
            'Per-run carriers, copied diagnostic controls, build trees, raw samples, debug tools and archives are evaluation storage, not repeated required per-application deployment costs.',
            'The original native kernel implementation still exists in this prototype. Owner+consumer or bundled-reference module differences do not measure its removal or a whole-machine memory/disk saving.',
            'Saved process smaps buckets are measured mappings. Anonymous areas are not relabeled as bridge caches without further allocation evidence. RSS/PSS, PFN identity, module residency and requested registration allocations are separate ledgers.'])
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(scenarios,indent=2))

if __name__=='__main__':main()
