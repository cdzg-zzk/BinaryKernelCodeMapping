#!/usr/bin/env python3
"""End-to-end evidence checks independent of the collector's status label."""
import csv
import json
import re
import subprocess
from pathlib import Path
from layer3_v2 import ROOT, ROUTINES, BUILDS, sha, dump, read_raw

fixed=ROOT/'results/layer3-fixed-batch-v2';campaign=ROOT/'results/layer3-confirmatory-v2'
history=json.loads((fixed/'historical-hashes.json').read_text())
assert len(history)==323 and all(sha(ROOT/p)==h for p,h in history.items())
config=json.loads((fixed/'fixed-batches.json').read_text())
assert json.loads((campaign/'fixed-batches.json').read_text())==config
assert sha(fixed/'calibration/calibration.json')==config['calibration_sha256']
for name,h in config['raw_sha256'].items():assert sha(ROOT/'results/layer3'/name/'raw.csv')==h
for p,h in json.loads((campaign/'source-hashes.json').read_text()).items():assert sha(campaign/'source'/p)==h
sessions=json.loads((campaign/'sessions.json').read_text())
expected={(n,b,r) for n in ROUTINES for b in BUILDS for r in range(8)}
assert {(s['routine'],s['build'],s['run_id']) for s in sessions}==expected and len(sessions)==64
nlogs=0
for s in sessions:
    d=campaign/s['routine'];work=d/s['build'];log=d/f"{s['build']}-run-{s['run_id']}.log"
    text=log.read_text();record=json.loads(log.with_suffix('.json').read_text())
    for key in ('module_sha256','start','end','loaded','unloaded','marker','command'):assert s[key]==record[key]
    assert s['loaded'] and s['unloaded'] and s['start']<s['end']
    assert s['module_sha256']==sha(work/'bench_kmod.ko')
    assert s['batch']==config['batches'][s['routine']]
    assert 'cpu=2' in s['command'] and 'irq_off=1' in s['command'] and 'repeats=15' in s['command']
    assert 'PGOT_V2_CORRECTNESS,pass' in text and re.search(r'PGOT_L3(?:SHA)?_DONE,.*ret=0',text)
    assert not re.search(r'VALIDATE_FAIL|BUG:|Oops:|WARNING:|Call Trace:',text)
    raw=re.findall(r'PGOT_L3(?:SHA)?_RAW,([^\n]+)',text)
    csvrows=list(csv.DictReader((d/'raw.csv').open()))
    relevant=[r for r in csvrows if r['build']==s['build'] and int(r['run_id'])==s['run_id']]
    assert len(relevant)==len(raw)==(15 if s['routine'].startswith('01') else 45)
    assert [','.join(r.values()) for r in relevant]==raw
    nlogs+=1
for n in ROUTINES:
    for b in BUILDS:
        work=campaign/n/b
        for p,h in json.loads((work/'object-hashes.json').read_text()).items():assert sha(work/p)==h
        nm=(work/'nm.txt').read_text();assert 'diag_memcpy' not in nm and 'diagnose_helpers' not in nm
        assert '-DPGOT_DIAGNOSTIC' not in (work/'flags.txt').read_text()
assert len(read_raw(campaign))==2400
counters=list(csv.DictReader((campaign/'diagnostics/bch-helper-counts.csv').open()))
assert len(counters)==32 and all(r['calls']=='1' for r in counters)
for b in BUILDS:
    d=campaign/'diagnostics'/b;text=(d/'diagnostic.log').read_text()
    assert 'PGOT_L3_RAW' not in text and text.count('PGOT_V2_BCH_HELPER,')==16
    assert 'PGOT_DIAGNOSTIC=1' in (d/'flags.txt').read_text()
for d in [fixed,campaign]:
    assert len(list(csv.DictReader((d/'ablation.csv').open())))==20
    assert len(list(csv.DictReader((d/'origin-and-variants.csv').open())))==40
    assert sha(d/'ablation.csv')==sha(d/'figures/plot-data.csv')
    assert sha(d/'outer-runs.csv')==sha(d/'figures/plot-outer-runs.csv')
    assert (d/'figures/ablation.pdf').read_bytes().startswith(b'%PDF')
    assert (d/'figures/ablation.png').read_bytes().startswith(b'\x89PNG')
    for row in csv.DictReader((d/'ablation.csv').open()):
        assert not (row['routine'].startswith('01') and row['variant']!='data_pgot')
# Compare manuscript diff section to the state saved before this revision.
before=(fixed/'worktree-before.patch').read_text()
after=subprocess.check_output(['git','diff','HEAD'],text=True)
def paper_section(patch):
    return next((s for s in re.split(r'(?=^diff --git )',patch,flags=re.M) if s.startswith('diff --git ') and 'paper/paper_content/Paper Draft.md' in s.splitlines()[0]),'')
assert paper_section(before)==paper_section(after),'paper changed since pre-revision snapshot'
assert not Path('/sys/module/bench_kmod').exists() and not Path('/sys/module/pgot_timestamp').exists()
unit=subprocess.run(['python3',str(ROOT/'scripts/test_layer3_v2.py')],text=True,capture_output=True)
assert unit.returncode==0,unit.stderr
(fixed/'methodology-tests.txt').write_text(unit.stdout+unit.stderr)
dump(fixed/'verification.json',dict(status='pass',historical_files_unchanged=323,formal_logs_verified=nlogs,
    raw_pairs_verified=2400,outer_comparisons=160,ablation_comparisons=20,diagnostic_counts_verified=32,
    formal_counters_absent=True,paper_diff_unchanged=True,benchmark_modules_unloaded=True,
    figure_csv_matches_analysis=True,source_and_object_hashes_verified=True,methodology_tests=3))
print('Verified archive preservation, all 64 formal logs/raw records, object identities, diagnostics, figures and unchanged paper.')
