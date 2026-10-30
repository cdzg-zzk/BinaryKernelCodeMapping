#!/usr/bin/env python3
"""Check final XZ-composed delivery against raw runs, identities and cleanup (no publication)."""
import argparse
import hashlib
import json
import subprocess
import os
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
RAW=ROOT/'test/evaluation-local/runs/iso9660'
RUNS=(ROOT/'test/section65/build/squashfs/optimization-runs-01').resolve()
BUILD=ROOT/'test/section65/build/squashfs'
def label(p):
    p=p.resolve()
    if p.is_relative_to(ROOT):return str(p.relative_to(ROOT))
    assert p.is_relative_to(RUNS),p
    return str(Path('test/section65/build/squashfs/optimization-runs-01')/p.relative_to(RUNS))
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['analysis','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();analysis=a.analysis.resolve()
    data=read(analysis/'analysis.json');audit=read(analysis/'audit.json')
    resources=read(analysis/'resource-ledger/resources.json')
    assert data['status']==audit['status']==resources['status']=='complete'
    assert data['observations']==audit['observations']==8172 and len(data['inputs'])==30
    assert audit['analysis_sha256']==sha(analysis/'analysis.json') and audit['excluded_observations']==0
    build=RUNS/'builds/data-cache-controls-02/data-48'
    identity={n:sha(build/n) for n in ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse']}
    checked=[]
    for folder in [RUNS/'data48-functional-01',RUNS/'data48-guest-01',RUNS/'data48-simultaneous-01',RUNS/'data48-bcj-01']:
        path=folder/'result.json';result=read(path);checked.append(path)
        assert result['status']=='complete' and result['restored'] and result['modules_unloaded']
        assert all(result['binaries'][n]==value for n,value in identity.items())
    functional=read(checked[0]);bcj=read(checked[3]);functional['cases']+=bcj['cases'];assert len(functional['cases'])==30 and all(c['status']=='pass' for c in functional['cases'])
    for codec in ['gzip','xz','zstd','lz4','lzo','xz-bcj']:
        hashes=[]
        for variant in ['copied','shared']:
            record=read(RUNS/('data48-bcj-01' if codec=='xz-bcj' else 'data48-functional-01')/f'{variant}-{codec}-pfns.json')
            assert record['status']=='pass' and len(record['pages'])==9
            assert all(r['shared']==(variant=='shared') for r in record['pages'])
            assert record['private_table_distinct_from_native'] and all(int(v,16)==0 for v in record['operation_table_targets'])
            assert len(record['private_codec_bindings'])==3
            assert all(0<int(s['target'],16)<2**47 and s['user_pfn']!=s['kernel_pfn'] for s in record['private_codec_bindings'])
            xz=record['private_xz_bindings'];assert xz['services']==9 and xz['user_pfn']!=xz['kernel_pfn']
            assert len(xz['targets'])==9 and all(0<int(v,16)<2**47 for v in xz['targets'])
            hashes.append({r['offset']:r['mapped_page_sha256'] for r in record['pages']})
        assert hashes[0]==hashes[1]
    guest=read(checked[1]);assert guest['native_negative']['errno']==5
    for variant in ['copied','shared']:
        assert guest[variant]['client_errno']==5 and guest[variant]['daemon_alive_after_read']
        regression=read(RUNS/'data48-guest-01/guest/evidence'/f'regression-{variant}/result.json')
        assert regression['status']=='pass' and len(regression['cases'])==6
        assert sum(c['random_and_boundary_reads'] for c in regression['cases'])==22032
    simultaneous=read(checked[2]);assert len(simultaneous['phases'])==16 and len(simultaneous['cases'])==2
    assert simultaneous['native_after'] and simultaneous['real_fd_and_partition_offsets']
    assert all(c['three_consumer_overlap_phases'] and c['consumer_cleanup_order']==['C','A','B'] and c['private_objects_disjoint'] for c in simultaneous['cases'])
    debug=RUNS/'data48-simultaneous-01'
    before=read(debug/'shared-B-pfns-before.json');after=read(debug/'shared-B-pfns-after-xz-breakpoint.json')
    assert all(r['shared'] for r in after['pages']) and len(after['pages'])==9
    assert [(r['user_pfn'],r['kernel_pfn']) for r in before['pages']]==[(r['user_pfn'],r['kernel_pfn']) for r in after['pages']]
    assert 'vkso_xz_dec_run' in (debug/'xz-breakpoint.log').read_text()
    assert [4,33] in bcj['xz_filter_chains']
    for name in ['native-calls-01','hardening-01','data48-metadata-work-01','data48-minimal-01','shared-decoder-01','cache-scale-direct-01']:
        path=RUNS/name/'result.json';assert read(path)['status']=='complete';checked.append(path)
    # Retained contiguous-decoder observations exercise the unchanged owner;
    # new bridge correctness, PFNs and real applications are checked separately.
    decoder=read(RUNS/'shared-decoder-01/result.json');assert decoder['observations']==160 and decoder['restored'] and decoder['modules_unloaded']
    for mode in ['single','prealloc']:
        shared=read(RUNS/'shared-decoder-01'/f'shared-{mode}-pfns.json')
        copied=read(RUNS/'shared-decoder-01'/f'copied-{mode}-pfns.json')
        assert all(p['shared'] for p in shared['pages']) and all(not p['shared'] for p in copied['pages'])
        assert [(p['offset'],p['mapped_page_sha256']) for p in shared['pages']]==[(p['offset'],p['mapped_page_sha256']) for p in copied['pages']]
    for variant in ['copied','shared']:
        lifetime=read(RUNS/'shared-decoder-01'/('lifetime-'+variant)/'result.json')
        assert lifetime['status']=='complete' and lifetime['unmounted'] and lifetime['daemon_returncode']==0
        assert lifetime['content_checks']==561 and lifetime['retained_file_handles']==64 and lifetime['cursor_roundtrips']==3
    direct=read(RUNS/'cache-scale-direct-01/result.json')
    assert len(direct['cases'])==3
    for case in direct['cases']:
        for row in case['snapshots']:
            assert row['cache'][0]<=2048 and row['cache'][1]<=4096
            if row['phase'].startswith('scan-'):assert row['entries']==case['scale']*5866+1
    dictionary=BUILD/'optimization-xz-valid-01/result.json';d=read(dictionary)
    assert d['status']=='pass' and d['dictionary_states']==65536 and d['decoder_checks']==244
    checked.append(dictionary)
    for name in ['optimization-cache-valid-01','optimization-cache-sanitize-01']:
        path=BUILD/name/'result.json';r=read(path);assert r['status']=='complete'
        assert r['distinct_regular_files']==8192 and r['churn_passes']==3
        released=r['snapshots']['all-test-handles-released'];assert released[0]<=2048 and released[1]<=4096
        assert r['snapshots']['over-budget-live-handles'][0]>2048
        checked.append(path)
    sanitizer=RUNS/'data48-cache-sanitize-01/sanitizer.json'
    assert read(sanitizer)['status']=='complete';checked.append(sanitizer)
    current_cache=RUNS/'data48-cache-sanitize-01/result.json';r=read(current_cache)
    assert r['status']=='complete' and r['distinct_regular_files']==8192 and r['churn_passes']==3
    released=r['snapshots']['all-test-handles-released'];assert released[0]<=2048 and released[1]<=4096
    assert r['snapshots']['over-budget-live-handles'][0]>2048
    checked.append(current_cache)
    fresh_lifetime=read(RUNS/'data48-lifetime-01/result.json');assert fresh_lifetime['status']=='complete' and fresh_lifetime['content_checks']==561 and fresh_lifetime['unmounted']
    checked.append(RUNS/'data48-lifetime-01/result.json')
    controls=RUNS/'native-controls-guest-01/result.json'
    assert read(controls)['status']=='complete';checked.append(controls)
    for item in data['inputs']:
        run=Path(item['run']);state=read(run/'result.json')
        assert state['status']=='complete' and state['modules_unloaded']
        if not (run/'benchmark').is_dir():continue
        bench=read(run/'benchmark/result.json')
        for variant in ['copied','vkso']:
            trace=[json.loads(l) for l in (run/'benchmark'/f'{variant}-helper/trace.jsonl').read_text().splitlines()]
            assert len(trace)>=bench['blocks'] and all(r['source'].startswith('/proc/self/fd/') and r['offset']>0 for r in trace)
    assert resources['platform']['resident_bytes']==32768 and resources['platform']['charged_to_business_bytes']==0
    for key,value in [('shared_backing_avoided_once_bytes',36864),
                      ('registration_requested_bytes',1264),('owner_resident_bytes',69632)]:
        assert resources['business'][key]==value
    assert len(resources['scale'])==21 and resources['minimal_deployment']['copied_modules_absent']
    b=resources['business']
    assert b['native_reference_resident_bytes']==resources['native_reference_residencies']['native-word-normal']
    assert b['native_preparation_delta_bytes']==b['prepared_native_resident_bytes']-b['native_reference_resident_bytes']
    costs=read(analysis/'costs.json')
    assert len(costs['moved_functions'])==34 and sum(r['original_lines'] for r in costs['moved_functions'])==2103
    assert sum(r['body_changed'] for r in costs['moved_functions'])==3
    assert costs['native_changed_file_count']==16 and costs['lkl_application_added_lines']==30
    assert costs['xz_composition']['original_algorithm_physical_lines']==2604
    assert costs['xz_composition']['candidate_algorithm_physical_lines']==2637
    assert costs['xz_composition']['edited_algorithm_bodies']==['dict_repeat']
    for row in costs['xz_composition']['original_sources']:
        assert sha(Path(row['path']))==row['sha256']
    for row in costs['xz_composition']['algorithm_deltas']:
        assert sha(build/row['file'])==row['candidate_sha256']
        assert row['unchanged']==(row['file']!='xz_dec_lzma2.c')
    for policy in ['normal','relaxed']:
        reference=BUILD/'optimization-native-controls-01'/('native-word-'+policy)/'xz_dec_lzma2.c'
        assert sha(reference)==sha(build/'xz_dec_lzma2.c'), 'native algorithm differs from shared candidate'
    assert sha(build/'shared_core.c')==sha(ROOT/'test/section65/build/squashfs/evaluation-improved-01/build/shared_core.c')
    assert sum(r['physical_lines'] for r in costs['source_lines'] if r['category']=='generated_native_support')==390
    for row in costs['source_lines']:
        path=Path(row['path']);path=path if path.is_absolute() else ROOT/path
        assert sha(path)==row['sha256']
        assert len(path.read_text().splitlines())==row['physical_lines']
    # Publication is deliberately deferred. Check existing manuscript artifacts
    # against the checkpoint; this audit neither builds nor rewrites them.
    preserved=[]
    for name in ['paper/filesystem-section.tex','paper/filesystem-section-preview.pdf',
                 'paper/paper_content/sections/06-evaluation.tex']:
        previous=subprocess.check_output(['git','show','ebe40754:'+name],cwd=ROOT)
        assert (ROOT/name).read_bytes()==previous, ('publication changed',name)
        preserved.append(dict(path=name,sha256=sha(ROOT/name)))
    modules={line.split()[0] for line in Path('/proc/modules').read_text().splitlines()}
    task_modules={'sq_reference','vkso_sq_core','vkso_squashfs','page_cache_replace','vkso_kernel_reader'}
    assert not modules.intersection(task_modules),modules.intersection(task_modules)
    processes=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
        try:argv=(proc/'cmdline').read_bytes().split(b'\0')
        except (OSError,PermissionError):continue
        # Match actual interpreter argv, not a shell containing this check.
        if not argv:continue
        exe=Path(os.fsdecode(argv[0])).name
        runner=exe.startswith('python') and any(Path(os.fsdecode(x)).name in ['campaign_queue.py','postprocess.py','native_compare.py','apptainer_shared.py'] for x in argv[1:3])
        helper=exe in ['vkso-squashfuse','squashfuse_ll','lklfuse','lklfuse-cache','qemu-system-x86_64']
        if (runner or helper) and any(b'section65' in x or b'data48-' in x or str(RUNS).encode() in x for x in argv):
            processes.append(dict(pid=int(proc.name),argv=[os.fsdecode(x) for x in argv if x]))
    assert not processes,processes
    records=checked+[analysis/'analysis.json',analysis/'audit.json',analysis/'resource-ledger/resources.json',
        analysis/'costs.json',analysis/'reuse-audit/result.json',analysis/'EXPERIMENT_REPORT.md',
        RUNS/'data48-recovery-01/recovery.json',RUNS/'data48-confirmation-queue-02/result.json',
        RUNS/'data48-postprocess-02/result.json']
    assert read(records[-1])['status']=='awaiting-review'
    result=dict(status='complete',version='xz-word-data48-bounded-cache',campaigns=30,timed_observations=8172,
        completed_at=time.time(),reused_native_observations=2688,new_observations=5484,
        excluded_partial_observations=790,publication='Deferred at user request; existing manuscript and PDF unchanged.',
        accounting='Installed generic platform; business preparation, per-core metadata and private runtime retained.',
        scope='Experiment report and raw evidence, one host/boot. No hardening-equivalence, human-time or whole-machine net-saving claim.',
        task_modules_unloaded=True,active_task_processes=processes,preserved_publication=preserved,
        records=[dict(path=label(p),sha256=sha(p)) for p in records])
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('Final experiment and cleanup audit complete')

if __name__=='__main__':main()
