#!/usr/bin/env python3
"""Check section 6.3 deliverables against retained measurements and current files.

Does not collect performance or change owners. Run after analyze.py and the
independent application/setup replay described in README.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'test/evaluation'))

def read(p): return json.loads(p.read_text())
def rows(p): return list(csv.DictReader(p.open()))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def complete(base, app_replay):
    audit = read(base / 'analysis/audit.json')
    assert audit['status'] == 'complete'
    assert (audit['completed_deployments'], audit['raw_user_rows'], audit['raw_kernel_rows'], audit['comparisons']) == (18, 13239, 17721, 384)
    assert audit['repetition_count']=={'bch':12,'lz4':3,'xz':3}
    assert all(a['status'] == 'pass' and a['exports'] for a in audit['audits'])
    owners = []
    for algorithm, directory in [('lz4', 'test_lz4'), ('bch', 'test_BCH'), ('xz', 'test_xz')]:
        for p in (base / 'owners' / algorithm).iterdir():
            if p.suffix in ('.c', '.h', '.ko') or p.name == 'Makefile':
                current = ROOT / 'test' / directory / 'kmod' / p.name
                assert current.read_bytes() == p.read_bytes(), str(current)
                owners.append(dict(path=str(current.relative_to(ROOT)), sha256=sha(p)))
        user = read(base / 'builds' / algorithm / 'build.json')
        assert user['user_flags'] == ['-O2', '-g', '-fPIC', '-std=gnu11']
        assert user['native_algorithm_edits'] == []
    for p in (base / 'owners/adapted').rglob('*'):
        if p.is_file() and p.suffix in ('.c', '.h'):
            assert p.read_bytes() == (ROOT / 'test/test_BCH/adapted' / p.relative_to(base / 'owners/adapted')).read_bytes()

    # Full BCH raw-vector replay for both independent interventions.
    import diagnose as diag
    diagnostic_rows = {}
    for name, backends in [('bch', ('original-matched', 'cached-matched', 'owner-kernel')),
                           ('bch-helper', ('cached-direct', 'cached-helpers', 'owner-kernel'))]:
        diag.BCH_BACKENDS = backends
        count = 0
        for n in range(3):
            d = base / 'diagnostics' / name / f'load-{n:02d}'
            assert read(d / 'complete.json')['unloaded']
            diag.audit_bch_saved(d)
            record = read(d / 'audit.json')
            assert record['timing_rows'] == 1056 and record['correctness_vectors'] == 128
            assert record['decode_checks'] == 10752 and record['parity_checks'] == 3588
            count += record['timing_rows']
        diagnostic_rows[name] = count
    count = 0
    for n in range(3):
        d = base / 'diagnostics/xz' / f'load-{n:02d}'
        check = read(d / 'audit.json'); raw = rows(d / 'raw.csv')
        assert read(d / 'complete.json')['unloaded'] and check['status'] == 'pass'
        assert check['api_identity'] and len(check['trials']) == len(raw) == 99
        assert all(x['full_output_match'] for x in check['trials'])
        expect = {(case, r, backend) for case in ('bash','libc.so.6','python3') for r in range(11)
                  for backend in ('stock-kernel','owner-kernel-crc','owner-kernel')}
        assert {(r['case'], int(r['outer_run']), r['backend']) for r in raw} == expect
        assert all(r['status']=='pass' and int(r['cpu'])==2 and int(r['elapsed_ns'])>=10000000 for r in raw)
        count += len(raw)
    diagnostic_rows['xz-crc'] = count

    import bch_kernel_audit as checker
    checker.BACKENDS=('stock-kernel','matched-source-kernel','owner-kernel')
    pmu_root=base/'repeat-bch/pmu'
    pmu_audit=read(pmu_root/'analysis-audit.json')
    assert pmu_audit['all_contexts_visit_three_backends'] and pmu_audit['raw_workload_rows']==9504
    for n in range(3):
        assert read(pmu_root/f'load-{n:02d}/complete.json')['unloaded']
        for phase in range(3):
            directory=pmu_root/f'load-{n:02d}/phase-{phase:02d}'
            replay=checker.audit(directory,measure=True,expected_cpu=2,outer_runs=11,sample_ms=10,aligned_inputs=True)
            assert replay['timing_rows']==1056 and replay['decode_checks']==10752
    diagnostic_rows['pmu_context_crossover']=9504

    user_pmu_root=base/'repeat-bch/user-pmu'
    assert read(user_pmu_root/'analysis-audit.json')['event_rows']==15840
    for n in range(3):
        directory=user_pmu_root/f'load-{n:02d}'
        assert read(directory/'complete.json')['owner_unloaded']
        record=read(directory/'results/audit.json')
        assert record['counter_rows']==5280 and record['exports']
        assert rows(directory/'results/user.csv.inputs.csv')==rows(base/'deployment-00-bch/results/user.csv.inputs.csv')
        pmu_rows=rows(directory/'results/pmu.csv')
        assert len(pmu_rows)==5280 and all(int(r['running'])>0 and int(r['running'])>=.99*int(r['enabled']) for r in pmu_rows)
        formal_rows=rows(directory/'results/user.csv')
        assert len(formal_rows)==1056
        log=(directory/'results/user.log').read_text()
        assert all(f'correctness: m=13 t={t} vectors=128 backends=3 ok' in log for t in (4,8))
    diagnostic_rows['user_pmu']=3168

    # Confirm summaries, captions and generated manuscript are reproducible.
    products = ['tables.md','user-plot.csv','kernel-table.csv','kernel-table.tex','section63.tex','section63.md']
    old = {n: sha(base / 'paper-material' / n) for n in products}
    import tables, write_paper
    tables.build(base); write_paper.build(base)
    assert old == {n: sha(base / 'paper-material' / n) for n in products}
    material = base / 'paper-material'
    tex = (material / 'section63.tex').read_text()
    section = (material / 'section63.md').read_text().strip()
    paper_path = ROOT / 'paper/paper_content/Paper Draft.md'
    manuscript = paper_path.read_text()
    assert section in manuscript
    assert '-1.04%' not in manuscript
    assert [int(n) for n in re.findall(r'^\*\*Table (\d+):', manuscript, re.M)] == list(range(1,27))
    environments = []
    for m in re.finditer(r'\\(begin|end)\{([^}]+)\}', tex):
        if m[1] == 'begin': environments.append(m[2])
        else: assert environments.pop() == m[2]
    assert not environments
    braces = 0
    for m in re.finditer(r'(?<!\\)[{}]', tex):
        braces += 1 if m[0]=='{' else -1
        assert braces >= 0
    assert braces == 0
    labels=set(re.findall(r'\\label\{([^}]+)\}',tex))
    assert set(re.findall(r'\\ref\{([^}]+)\}',tex)) <= labels
    for ext in ('pdf','svg','png'):
        assert (material/f'exported_algorithms.{ext}').read_bytes() == (ROOT/f'paper/paper_content/figures/exported_algorithms.{ext}').read_bytes()
    assert (material/'exported_algorithms.pdf').read_bytes().startswith(b'%PDF')
    # Numbers highlighted in the report correspond to the raw-derived summary.
    summary=rows(base/'analysis/summary.csv')
    lookup={(r['algorithm'],r['domain'],r['workload'],r['target'],r['baseline']):r for r in summary}
    for t,e in [(4,2),(8,2),(8,8)]:
        r=lookup['bch','user',f'm=13/t={t}/bytes=512/errors={e}/decode-precomputed','kernel-vkso','native-dso']
        number=abs(100*(float(r['median_cost_ratio'])-1))
        assert f'{number:.1f}\\%' in tex
    for name in ('README.md','methods.md','results/report.md'):
        p=base.parent/name
        assert p.stat().st_size>500
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if '://' in link or link.startswith('#'): continue
            assert (p.parent/link.split('#')[0]).exists(), (p,link)
    for link in re.findall(r'\]\(([^)]+)\)',section):
        if '://' not in link and not link.startswith('#'):
            assert (paper_path.parent/link.split('#')[0]).exists(),link

    app=ROOT/'test/evaluation/results/application-setup'
    assert read(app/'paper-tables/tables.json') == read(app_replay/'paper-tables/tables.json')
    preservation=read(base/'validation/application-preservation.json')
    assert preservation['numeric_facts_unchanged']
    preservation['replayed_after_cleanup']=True
    (base/'validation/application-preservation.json').write_text(json.dumps(preservation,indent=2)+'\n')
    oldroot=ROOT/'test/evaluation/results/section63'
    assert {p.name for p in oldroot.iterdir()}=={'README.md'}
    assert not (ROOT/'test/evaluation/xz-kernel-original').exists()
    assert all((ROOT/f'test/section{n}/README.md').exists() for n in (61,62,63))
    assert not {'vkso_lz4','vkso_bch','vkso_xz','matched_lz4','matched_xz','bch_matched','bch_cached','bch_kernel_bench','page_cache_replace'} & {r.split()[0] for r in Path('/proc/modules').read_text().splitlines()}
    processes=subprocess.check_output(['ps','-eo','args'],text=True).splitlines()
    running=[r for r in processes if re.search(r'^python3 .*test/section63/scripts/(campaign|diagnose|bch_helper_diagnostic|repeat_bch|bch_pmu|bch_user_pmu)\.py (?:collect|prepare)\b',r)]
    assert not running,running
    prose=json.loads(subprocess.check_output([sys.executable, '/home/zzk/.codex/skills/ccf-paper-writer/scripts/check_prose_quality.py',str(material/'section63.tex'),'--scope','section','--format','json'],text=True))
    report=dict(status='complete',formal=audit,diagnostic_raw_rows=diagnostic_rows,owners_unchanged=owners,
                generated_products=old,application_numeric_facts_unchanged=True,old_matched_retired=True,
                no_collection_process=True,experiment_modules_unloaded=True,
                latex='environment/brace/reference/figure checks passed; whole-paper TeX compilation not run',
                prose_check=prose,prose_review='Retained three-version enumeration: these are the experimental controls, not a writing template.',
                known_result_boundary='Use repeat-bch/findings.md for the twelve-load and PMU/context explanation; production owner unchanged.')
    (base/'validation/completion.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('formal','owners_unchanged','generated_products','prose_check')},indent=2))

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--application-replay',type=Path,required=True);a=p.parse_args()
    complete(a.directory.resolve(),a.application_replay.resolve())
