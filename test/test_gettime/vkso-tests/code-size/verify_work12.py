#!/usr/bin/env python3
"""Verify every evidence layer needed by Clocktime work 1 and work 2."""
import csv
import json
from pathlib import Path
import subprocess
import sys

from audit_current import REPO, HERE, OUT
from audit_binary_current import CAMPAIGN


def main():
    commands = [
        [sys.executable, str(HERE/'audit_changes.py'), '--check'],
        [sys.executable, str(HERE/'audit_current.py'), '--check'],
        [sys.executable, str(HERE/'audit_binary_current.py'), '--check'],
        [sys.executable, str(HERE/'collect_work12.py'), '--check'],
        [sys.executable, str(HERE/'build_work12_report.py'), '--check'],
        [sys.executable, str(HERE/'check_maintenance_case.py')],
        [sys.executable, '-m', 'unittest', 'discover', '-s', str(HERE), '-p', 'test_audit_current.py'],
        [sys.executable, '-m', 'unittest', 'discover', '-s', str(HERE.parent/'direct-api/tests'), '-p', 'test_kernel_contract.py'],
    ]
    logs, checks = [], []
    for command in commands:
        p = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
        readable = ' '.join(str(x).replace(str(REPO)+'/', '') for x in command)
        logs.append('$ ' + readable + '\n' + p.stdout + p.stderr)
        checks.append({'command': readable, 'exit_code': p.returncode})
        if p.returncode:
            (OUT/'verification.log').write_text('\n'.join(logs))
            raise RuntimeError('verification failed: ' + readable)
    # The immutable integration ledger independently guards against omitting
    # newly added production code from the scoped semantic inventory.
    source = list(csv.DictReader((OUT/'source-lines.csv').open()))
    def repo_path(row):
        return ('test/test_gettime/linux-5.15.198-vkso/' + row['path']
                if row['origin'] in ['VKSO','Platform'] else row['path'])
    counted = {(repo_path(r),r['line']) for r in source if r['system']=='VKSO'}
    ignored = {'diagnostics','experiment_config','native_vdso_withdrawal','platform_scope_cleanup'}
    additions = [r for r in csv.DictReader((HERE/'change-lines.csv').open())
                 if r['side']=='new' and r['category'] not in ignored]
    missing = [r for r in additions if (r['path'],r['line']) not in counted]
    assert not missing, 'production additions omitted: ' + repr(missing)
    totals=json.loads((OUT/'source-totals.json').read_text())['totals']
    assert totals['Raw']['feature']==1487 and totals['VKSO']['feature']==1624
    boots=list(csv.DictReader((OUT/'mechanism-boots.csv').open()))
    assert len(boots)==8 and len({r['boot_id'] for r in boots})==8
    identity_groups={}
    for block in range(1,5):
        for variant in ['normal','no-retpoline']:
            for method in ['raw','vkso']:
                run=json.loads((CAMPAIGN/f'block-{block:02}/read/{method}-{variant}/run.json').read_text())
                key=method,variant
                identity=(run['git_commit'],run['kernel_image_sha256'],run['carrier_sha256'],run['public_library_sha256'])
                identity_groups.setdefault(key,identity)
                assert identity_groups[key]==identity, ('mixed build identities',block,key)
    transfers=list(csv.DictReader((OUT/'binary-user-transfers.csv').open()))
    for variant in ['normal','no-retpoline']:
        assert any(r['variant']==variant and r['artifact']=='libkernel.so' and 'vkso_clock_gettime_hres' in r['disassembly'] for r in transfers)
        assert any(r['variant']==variant and r['artifact'].startswith('kernel:') and 'vkso_clock_gettime_hres' in r['disassembly'] for r in transfers)
    maintenance=json.loads((OUT/'maintenance-validation.json').read_text())
    assert maintenance['cases']==100100 and 'PASS' in maintenance['result']
    for name in ['README.md','tables.md','mechanism.mmd','interfaces.csv','maintenance-aa1855e.patch','kernel-contract-validation.log']:
        assert (OUT/name).stat().st_size>0,name
    result={
        'status':'PASS', 'source_revision':'cf9dc817f29f9c8d6f88dde0c58c4ccb75347aeb',
        'scope':'work 1 and work 2; no new target experiment or performance claim',
        'commands':checks, 'production_addition_lines_accounted':len(additions),
        'missing_production_additions':0, 'independent_vkso_read_boots':8,
        'campaign_read_build_groups_consistent':4,
        'source_feature_sloc':{s:totals[s]['feature'] for s in ['Raw','VKSO']},
        'source_plus_selected_retained_sloc':{s:totals[s]['feature']+totals[s]['retained'] for s in ['Raw','VKSO']},
        'maintenance_helper_cases':maintenance['cases'],
        'deliverables':{
            'responsibilities_and_paths':['README.md','mechanism.mmd','interfaces.csv','binary-user-transfers.csv'],
            'physical_identity':['mechanism-boots.csv','shared-pages.csv','resource-pages.csv'],
            'source_size':['source-manifest.json','source-lines.csv','source-slices.csv','source-summary.csv','source-totals.json'],
            'actual_binary_size':['binary-identities.json','binary-symbols.csv','binary-sections.csv','binary-summary.csv'],
            'maintenance':['maintenance-aa1855e.patch','maintenance-validation.json','maintenance-helper.c','kernel-contract-validation.log'],
        },
    }
    (OUT/'verification.log').write_text('\n'.join(logs)+'\nCross-layer evidence checks: PASS\n')
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['commands','deliverables']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
