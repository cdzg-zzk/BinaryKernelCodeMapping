#!/usr/bin/env python3
"""Fixed-batch Layer-3 analysis. No outcome-dependent configuration choices."""
import argparse
import csv
import hashlib
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTINES = {
    '01_sha256_transform': [4096, 8192, 16384],
    '02_bch_encode': [64, 128, 256],
    '03_zlib_deflate': [16, 32, 64],
    '04_zstd_decompress': [16, 32, 64, 128, 256],
}
BUILDS = ('no_retpoline', 'retpoline')
VARIANTS = ('data_pgot', 'func_pgot', 'all_pgot')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')

def write_csv(path, rows):
    assert rows, path
    with Path(path).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def read_raw(directory):
    result = []
    for routine in ROUTINES:
        with (Path(directory) / routine / 'raw.csv').open() as f:
            rows = list(csv.DictReader(f))
        seen = set()
        for row in rows:
            row = dict(row, routine=routine)
            if routine.startswith('01_'):
                row['variant'] = 'data_pgot'  # historical all_pgot is an alias
            for key in ('run_id', 'repeat', 'iterations'):
                row[key] = int(row[key])
            for key in ('origin_cycles', 'variant_cycles', 'delta_variant_origin'):
                row[key] = float(row[key])
            assert abs(row['variant_cycles'] - row['origin_cycles'] - row['delta_variant_origin']) < .003
            assert row['build'] in BUILDS and row['variant'] in VARIANTS
            assert row['iterations'] in ROUTINES[routine]
            key = tuple(row[k] for k in ('build','variant','iterations','run_id','repeat'))
            assert key not in seen, key
            seen.add(key)
            result.append(row)
    return result

def aggregate(raw, ci=False):
    """First paired medians within a module load; then equal-weight run medians."""
    groups = defaultdict(list)
    for row in raw:
        groups[tuple(row[k] for k in ('routine','build','variant','iterations','run_id'))].append(row)
    outer = []
    for key, rows in sorted(groups.items()):
        assert sorted(r['repeat'] for r in rows) == list(range(len(rows)))
        origin = st.median(r['origin_cycles'] for r in rows)
        delta = st.median(r['delta_variant_origin'] for r in rows)
        outer.append(dict(zip(('routine','build','variant','iterations','run_id'), key),
                          inner_pairs=len(rows), origin=origin,
                          adapted=st.median(r['variant_cycles'] for r in rows),
                          delta=delta, overhead_pct=100*delta/origin))
    groups = defaultdict(list)
    for row in outer:
        groups[tuple(row[k] for k in ('routine','build','variant','iterations'))].append(row)
    summary = []
    for key, rows in sorted(groups.items()):
        pcts = [r['overhead_pct'] for r in rows]
        row = dict(zip(('routine','build','variant','iterations'), key), outer_runs=len(rows),
                   pairs_per_run=rows[0]['inner_pairs'],
                   origin=st.median(r['origin'] for r in rows),
                   adapted=st.median(r['adapted'] for r in rows),
                   delta=st.median(r['delta'] for r in rows),
                   overhead_pct=st.median(pcts), run_min_pct=min(pcts), run_max_pct=max(pcts),
                   run_min_delta=min(r['delta'] for r in rows),run_max_delta=max(r['delta'] for r in rows))
        assert len({r['inner_pairs'] for r in rows}) == 1
        if ci:
            import numpy as np
            rng = np.random.default_rng(17092026)
            boots = np.median(rng.choice(pcts, (10000, len(pcts)), replace=True), axis=1)
            row['ci_low_pct'],row['ci_high_pct'] = map(float,np.percentile(boots,[2.5,97.5]))
        summary.append(row)
    return outer, summary

def select_batches(raw, calibration):
    # No variant cost, delta, IQR, percentage, sign, or p-value is read here.
    overhead = float(calibration['selection_overhead_tsc'])
    assert overhead > 0
    selected, evidence = {}, []
    for routine, candidates in ROUTINES.items():
        for batch in candidates:
            durations = []
            for build in BUILDS:
                runs = defaultdict(list)
                for r in raw:
                    if (r['routine'], r['iterations'], r['build']) == (routine,batch,build):
                        runs[r['run_id']].append(r['origin_cycles'] * batch)
                assert runs, (routine,batch,build)
                medians = [st.median(v) for v in runs.values()]
                # Conservative across archived module loads, still baseline-only.
                duration = min(medians)
                durations.append(duration)
                evidence.append(dict(routine=routine,build=build,batch=batch,
                                     origin_outer_median_batch_tsc=st.median(medians),
                                     minimum_origin_outer_median_batch_tsc=duration,
                                     timestamp_overhead_tsc=overhead,ratio=duration/overhead,
                                     passes=duration >= 1000*overhead))
            if routine not in selected and min(durations) >= 1000*overhead:
                selected[routine] = batch
        if routine not in selected:
            raise ValueError(f'No existing candidate meets 1000x rule for {routine}; no fallback')
    return selected, evidence

def baseline_rows(summary):
    # Baseline stays paired to each comparison (not an invented single Origin).
    out=[]
    for r in summary:
        out.append(dict(r, backend='origin', comparison=r['variant'], cost=r['origin'],
                        overhead_pct=0, delta=0, run_min_pct=0, run_max_pct=0,
                        run_min_delta=0, run_max_delta=0,
                        **({'ci_low_pct':0, 'ci_high_pct':0} if 'ci_low_pct' in r else {})))
        out.append(dict(r, backend=r['variant'], comparison=r['variant'], cost=r['adapted']))
    return out

def conclusions(summary):
    lookup={(r['routine'],r['build'],r['variant']):r for r in summary}
    lines=['# Fixed-workload interpretation', '',
           'Values below summarize module-load medians. Ranges span outer runs.', '']
    for routine in ROUTINES:
        for build in BUILDS:
            rows=[lookup[routine,build,v] for v in VARIANTS if (routine,build,v) in lookup]
            lines.append(f'## {routine} / {build}')
            for r in rows:
                lines.append(f"- {r['variant']}: {r['overhead_pct']:+.3f}% "
                             f"[{r['run_min_pct']:+.3f}, {r['run_max_pct']:+.3f}], "
                             f"paired delta {r['delta']:+.3f} TSC ticks/op.")
            if len(rows)==3:
                d,f,a=rows
                lines.append(f"Func-only versus All: {f['delta']:+.3f} versus {a['delta']:+.3f} "
                             'ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.')
            lines.append('')
    lines += ['Small negative results are not attributed to a PGOT optimization. '
              'The fixed-input builds can differ in code generation and layout. '
              'There is no causal cross-build retpoline subtraction.']
    return '\n'.join(lines)+'\n'

def reanalyze(args):
    out=args.output; out.mkdir(parents=True,exist_ok=True)
    raw=read_raw(args.archive)
    outer, scan=aggregate(raw)
    # Verify complete original grid, including all three module loads and 31 rounds.
    for routine, candidates in ROUTINES.items():
        vs=('data_pgot',) if routine.startswith('01_') else VARIANTS
        for b in BUILDS:
            for v in vs:
                for n in candidates:
                    rows=[r for r in raw if (r['routine'],r['build'],r['variant'],r['iterations'])==(routine,b,v,n)]
                    assert len(rows)==93 and {r['run_id'] for r in rows}=={0,1,2}
    write_csv(out/'complete-scan-outer.csv',outer)
    write_csv(out/'complete-scan.csv',scan)
    calibration=json.loads(args.calibration.read_text())
    sizes, evidence=select_batches(raw,calibration)
    write_csv(out/'batch-selection-evidence.csv',evidence)
    config=dict(schema=2,batches=sizes,outer_runs=8,paired_repeats=15,cpu=2,irq_off=1,
                rule='smallest candidate with minimum outer-run Origin median batch >= 1000 x timestamp overhead in both builds',
                calibration=str(args.calibration.resolve()),calibration_sha256=sha(args.calibration),
                archive=str(args.archive.resolve()),
                raw_sha256={k:sha(args.archive/k/'raw.csv') for k in ROUTINES},
                selection_overhead_tsc=calibration['selection_overhead_tsc'])
    # Freeze: regeneration must reproduce the same config.
    target=out/'fixed-batches.json'
    if target.exists():
        frozen=json.loads(target.read_text())
        # Recorded absolute provenance paths may differ in a relocated checkout.
        semantic=lambda c:{k:v for k,v in c.items() if k not in ('archive','calibration')}
        assert semantic(frozen)==semantic(config),'frozen config changed'
    else:
        dump(target,config)
    fixed=[r for r in raw if r['iterations']==sizes[r['routine']]]
    outer,summary=aggregate(fixed)
    write_csv(out/'outer-runs.csv',outer);write_csv(out/'ablation.csv',summary)
    write_csv(out/'origin-and-variants.csv',baseline_rows(summary))
    (out/'findings.md').write_text(conclusions(summary))
    historical=list(csv.DictReader((args.archive/'paper_table_selected.csv').open()))
    comparisons=[]
    for h in historical:
        routine=h['experiment'];v=h['variant']
        if routine not in ROUTINES: continue
        if routine.startswith('01_'): v='data_pgot'
        old=[r for r in raw if (r['routine'],r['build'],r['variant'],r['iterations'])==
             (routine,h['build'],v,int(h['iterations']))]
        _, old_summary=aggregate(old); old_s=old_summary[0]
        new=next(r for r in summary if (r['routine'],r['build'],r['variant'])==(routine,h['build'],v))
        pooled_delta=st.median(r['delta_variant_origin'] for r in old)
        matches=abs(pooled_delta-float(h['delta_cycles']))<.003
        comparisons.append(dict(routine=routine,build=h['build'],variant=v,
            historical_batch=int(h['iterations']),historical_reported_origin=float(h['origin_cycles']),
            historical_reported_adapted=float(h['variant_cycles']),historical_reported_delta=float(h['delta_cycles']),
            historical_reported_pct=float(h['overhead_percent']),historical_report_matches_raw=matches,
            historical_report_outer_variability='unavailable: selected report not linked to available raw',
            old_batch_raw_origin=old_s['origin'],old_batch_raw_adapted=old_s['adapted'],
            old_batch_raw_delta=old_s['delta'],old_batch_raw_pct=old_s['overhead_pct'],
            old_batch_raw_run_min_pct=old_s['run_min_pct'],old_batch_raw_run_max_pct=old_s['run_max_pct'],
            fixed_batch=new['iterations'],fixed_origin=new['origin'],fixed_adapted=new['adapted'],
            fixed_delta=new['delta'],fixed_pct=new['overhead_pct'],
            fixed_run_min_pct=new['run_min_pct'],fixed_run_max_pct=new['run_max_pct']))
    write_csv(out/'historical-vs-fixed.csv',comparisons)
    lines=['# Historical selection versus fixed batches','',
           'Historical reported values lack matching raw provenance. The middle column applies '
           'the historical batch choice to the available archive using outer-run aggregation. '
           'The last column uses the frozen batch and the same aggregation. Brackets are outer-run ranges.','',
           '| Routine/build/variant | Historical reported % (batch) | Available raw at old batch % [range] | Fixed % [range] (batch) |',
           '|---|---:|---:|---:|']
    for r in comparisons:
        lines.append(f"| {r['routine']}/{r['build']}/{r['variant']} | {r['historical_reported_pct']:+.3f} ({r['historical_batch']}) | "
                     f"{r['old_batch_raw_pct']:+.3f} [{r['old_batch_raw_run_min_pct']:+.3f}, {r['old_batch_raw_run_max_pct']:+.3f}] | "
                     f"{r['fixed_pct']:+.3f} [{r['fixed_run_min_pct']:+.3f}, {r['fixed_run_max_pct']:+.3f}] ({r['fixed_batch']}) |")
    (out/'historical-vs-fixed.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(batches=sizes,scan_configurations=len(scan),comparisons=len(summary),
                         selected_report_matching_rows=sum(r['historical_report_matches_raw'] for r in comparisons))))

def confirm_analysis(args):
    config=json.loads(args.config.read_text());raw=read_raw(args.campaign)
    for name in ROUTINES:
        vs=('data_pgot',) if name.startswith('01_') else VARIANTS
        for b in BUILDS:
            for v in vs:
                rows=[r for r in raw if (r['routine'],r['build'],r['variant'])==(name,b,v)]
                assert len(rows)==config['outer_runs']*config['paired_repeats']
                assert {r['iterations'] for r in rows}=={config['batches'][name]}
                assert {r['run_id'] for r in rows}==set(range(config['outer_runs']))
    sessions=json.loads((args.campaign/'sessions.json').read_text())
    assert len(sessions)==len(ROUTINES)*2*config['outer_runs']
    assert all(s['status']=='pass' for s in sessions)
    args.output.mkdir(parents=True,exist_ok=True)
    outer,summary=aggregate(raw,ci=True)
    write_csv(args.output/'outer-runs.csv',outer);write_csv(args.output/'ablation.csv',summary)
    write_csv(args.output/'origin-and-variants.csv',baseline_rows(summary))
    (args.output/'findings.md').write_text(conclusions(summary))
    dump(args.output/'analysis.json',dict(status='complete',sessions=len(sessions),inner_records=len(raw),
        outer_comparisons=len(outer),config_sha256=sha(args.config),unit='module-load run',
        estimator='median of outer-run paired-delta medians; percent computed within each outer run',
        ci='10000 percentile bootstrap resamples of outer-run percentages, seed 17092026',
        raw_sha256={k:sha(args.campaign/k/'raw.csv') for k in ROUTINES}))
    print('complete',len(raw),'inner pairs;',len(sessions),'module loads')

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('reanalyze');q.add_argument('--archive',type=Path,required=True);q.add_argument('--calibration',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.set_defaults(fn=reanalyze)
    q=sub.add_parser('summarize');q.add_argument('--campaign',type=Path,required=True);q.add_argument('--config',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.set_defaults(fn=confirm_analysis)
    a=p.parse_args();a.fn(a)
