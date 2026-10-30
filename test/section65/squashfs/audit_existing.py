#!/usr/bin/env python3
"""Recheck selected historical and maintenance evidence; never rewrite raw runs."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
RUNS=ROOT/'test/evaluation-local/runs/iso9660'


def load(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    historical=[]
    for name,entry,role in [
      ('squash-native-guest-03','run.json','Five-format original/prepared native semantic oracle; superseded by fixed-owner regression for final implementation.'),
      ('squash-export-04','run.json','Five-format copied/shared functional and physical evidence; final fixed owner independently regressed.'),
      ('squash-apptainer-shared-02','result.json','Real SIF application feasibility with earlier owner and Python translator.'),
      ('squash-apptainer-comparison-01','result.json','Python translator diagnostic, excluded from final performance pooling.'),
      ('squash-apptainer-comparison-02','result.json','C translator single-campaign diagnostic, excluded from fixed-owner formal pooling.'),
      ('squash-native-cost-01','result.json','Single gzip native campaign; superseded, not pooled with final five-format matrix.'),
      ('native-private-20261029-agent-01','result.json','Final historical ISO native preparation, one hardware campaign; no SquashFS inference.'),
      ('lkl-namecache-native-01','result.json','ISO cache-policy diagnostic against LKL; one campaign, distinct adapter.')]:
        path=RUNS/name/entry;result=load(path);assert result['status']=='complete'
        historical.append(dict(run=name,record=str(path.relative_to(ROOT)),sha256=sha(path),role=role,status='executed-complete'))
    legacy=RUNS/'squash-maintenance-01/result.json';assert load(legacy)['status']=='running'
    historical.append(dict(run='squash-maintenance-01',record=str(legacy.relative_to(ROOT)),sha256=sha(legacy),
        recorded_status='running',audited_status='historical interrupted orchestration; not a live campaign',
        cause='Client ENOTCONN 107 violated the old EIO 5 assertion; fixed branch not executed in this attempt.',
        resolution='New multi-signal classification and completed squash-maintenance-02; original failure preserved.'))
    run=RUNS/'squash-maintenance-02';overall=load(run/'result.json');assert overall['status']=='complete'
    old=load(run/'old-guest/evidence/result.json');fixed=load(run/'fixed-guest/evidence/result.json')
    assert old['native_valid']['status']=='pass' and overall['old']['expected_native_panic']
    assert fixed['status']=='complete' and fixed['restored'] and fixed['modules_unloaded']
    assert fixed['native_negative']['errno']==5 and len(fixed['native_regression'])==5
    outcomes=[]
    for label in ['copied','shared']:
        for state,data in [('old',old),('fixed',fixed)]:
            valid=data[label+'_valid'];bad=data[label+'_negative']
            assert valid['client_errno']==0 and valid['bytes']==96 and valid['daemon_returncode']==0
            if state=='old':assert bad['client_errno']==107 and bad['daemon_returncode']==-11 and not bad['daemon_alive_after_read']
            else:assert bad['client_errno']==5 and bad['daemon_returncode']==0 and bad['daemon_alive_after_read']
            outcomes.append(dict(version=state,consumer=label,valid=valid,negative=bad))
        regression=load(run/'fixed-guest/evidence'/('regression-'+label)/'result.json')
        assert regression['status']=='pass'
        assert len(regression['cases'])==6 and sum(c['random_and_boundary_reads'] for c in regression['cases'])==22032
        assert {c['label'] for c in regression['cases']}=={'gzip','xz','lz4','lzo','zstd','fd-offset'}
        assert all(c['hardlink'] and c['xattr'] and c['readonly'] for c in regression['cases'])
    assert overall['owners']['old']!=overall['owners']['fixed']
    for values in overall['unchanged_user_binaries'].values():assert values['old']==values['fixed']
    references=[]
    for name in ['squash-maintenance-reference-01','squash-maintenance-relaxed-reference-01']:
        reference=load(RUNS/name/'guest/evidence/result.json')
        assert reference['status']=='complete' and reference['modules_unloaded']
        assert next(c for c in reference['cases'] if c['image']=='negative.squashfs')['errno']==5
        assert sum(c.get('status')=='pass' for c in reference['cases'])==5
        references.append(dict(run=name,result=reference))
    iso=RUNS/'maintenance-oneshot-01';debug=load(iso/'evidence/debug/result.json')
    assert debug['status']=='pass' and debug['hardware_breakpoint'] and debug['function']=='isofs_get_blocks'
    assert debug['inode_size']==65537 and debug['block']==0 and debug['client']['bytes']==65537
    assert debug['single_step']['before']!=debug['single_step']['after']
    assert 'iso_read_inode_data' in debug['backtrace'] and 'iso_read ' in debug['backtrace']
    before=load(iso/'evidence/debug/pfns-before-step.json');after=load(iso/'evidence/debug/pfns-after-step.json')
    assert before['pages']==after['pages'] and len(before['pages'])==5
    assert all(p['shared'] and p['kernel_pfn']==p['user_pfn'] for p in before['pages'])
    assert load(iso/'evidence/kernel-after-debug/result.json')['status']=='pass'
    assert load(iso/'evidence/result.json')['restoration_verified']
    unchanged=load(iso/'unchanged-user-binaries.json')
    for record in unchanged.values():
        assert record['byte_identical'] and sha(ROOT/record['source'])==sha(ROOT/record['payload'])
    evidence=dict(status='pass',historical=historical,
        squashfs_maintenance=dict(run=str(run.relative_to(ROOT)),outcomes=outcomes,owner_hashes=overall['owners'],
            unchanged_user_binaries=overall['unchanged_user_binaries'],native_fixed=fixed['native_negative'],references=references),
        iso_debug=dict(run=str(iso.relative_to(ROOT)),function=debug['function'],inode_size=65537,block=0,
            single_step=debug['single_step'],shared_pages_before_and_after=5,
            replay_script=str((iso/'payload/fuse_gdb.py').relative_to(ROOT)),replay_script_sha256=sha(iso/'payload/fuse_gdb.py'),
            owner_sha256=sha(iso/'payload/vkso_iso_core.ko'),
            scope='Ubuntu 119 ABI in TCG; debugger feasibility only, separate from final SquashFS and hardware timing.'),
        pooling_policy='No historical performance row enters the final fixed-owner campaign estimates.')
    a.output.write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(dict(status='pass',historical_runs=len(historical),maintenance_user_cells=len(outcomes))))


if __name__=='__main__':main()
