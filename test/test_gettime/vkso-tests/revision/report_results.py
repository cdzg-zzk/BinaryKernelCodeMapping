#!/usr/bin/env python3
"""Render the completed Normal campaign and saved audits without changing samples."""
import argparse
import collections
import csv
import io
import json
import statistics as st
from pathlib import Path

import analyze
from audit_coverage import digest

METHODS = ('raw', 'vkso', 'compact-split')
PAIRS = (('raw', 'vkso'), ('raw', 'compact-split'), ('compact-split', 'vkso'))


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows]) + '\n'


def save_csv(path, rows):
    with path.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('campaign', type=Path)
    p.add_argument('record_audits', type=Path)
    p.add_argument('writer_audits', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    root = args.campaign.resolve()
    complete = json.loads((root / 'campaign-complete.json').read_text())
    assert digest(root / 'plan.json') == complete['plan_sha256']
    assert digest(root / 'summary.csv') == complete['summary_sha256']
    plan = json.loads((root / 'plan.json').read_text())
    assert len(plan['steps']) == 20
    rows, readers, supports, writers = [], [], [], []
    for step in plan['steps']:
        directory = root / f"step-{step['index']:03d}"
        done = json.loads((directory / 'complete.json').read_text())
        assert digest(directory / 'measurements.csv') == done['measurements_sha256']
        rows.extend(csv.DictReader((directory / 'measurements.csv').open()))
        for suffix, records in [('reader', readers), ('support', supports)]:
            record = json.loads((args.record_audits / f'{directory.name}-{suffix}.json').read_text())
            assert record['step'] == step and record['boot_id'] == done['boot_id']
            records.append(record)
        if step['role'] == 'update':
            for method in step['methods']:
                record = json.loads((args.writer_audits /
                    f"clocktime-writer-{step['index']:03d}-{method}.log").read_text())
                assert Path(record['method_directory']).resolve() == directory / method
                assert record['windows'] == 285
                writers.append(record)
    assert len(rows) == 60195 and len(writers) == 15
    summary = analyze.summarize(rows)
    # Reproduce the frozen campaign's complete CSV, including every bootstrap interval.
    text = io.StringIO(newline='')
    writer = csv.DictWriter(text, fieldnames=list(summary[0]))
    writer.writeheader()
    writer.writerows(summary)
    assert text.getvalue().encode() == (root / 'summary.csv').read_bytes()
    assert len(summary) == 729
    assert all(r['baseline_boots'] == r['candidate_boots'] == 5 for r in summary)
    index = {(r['role'], r['scenario'], r['metric'], r['baseline'], r['candidate']): r
             for r in summary}
    boots = analyze.boot_values(rows)

    def get(role, scenario, metric, pair=('raw', 'vkso')):
        return index[(role, scenario, metric, *pair)]

    def values(role, scenario, metric, scale=1):
        a = get(role, scenario, metric)
        b = get(role, scenario, metric, ('raw', 'compact-split'))
        return [f'{v / scale:.3f}' for v in
                (a['baseline_median'], a['candidate_median'], b['candidate_median'])]

    def interval(r, field='ratio'):
        low, high = ('ci_low', 'ci_high') if field == 'ratio' else ('difference_ci_low', 'difference_ci_high')
        return f"{r[field]:.3f} [{r[low]:.3f}, {r[high]:.3f}]"

    tables = {}
    for name, metric in [('public', 'reader_cycles'), ('kernel', 'kernel_reader_cycles')]:
        scenarios = sorted({r['scenario'] for r in summary if r['role'] == 'read' and r['metric'] == metric})
        data = []
        for s in scenarios:
            data.append([s, *values('read', s, metric),
                         interval(get('read', s, metric), 'difference'),
                         *[interval(get('read', s, metric, pair)) for pair in PAIRS]])
        tables[name] = table(['Path', 'Raw', 'VKSO', 'Copy', 'V−R cycles [95% CI]',
                              'V/R [95% CI]', 'C/R [95% CI]', 'V/C paired [95% CI]'], data)
    public = sorted({r['scenario'] for r in summary if r['role'] == 'read' and r['metric'] == 'reader_cycles'})
    groups = {'All 20 paths': public, '17 non-fallback paths': [s for s in public if 'fallback' not in s],
              '3 fallback paths': [s for s in public if 'fallback' in s],
              '7 clock_gettime fast paths': [s for s in public if s.startswith('clock_gettime_') and 'fallback' not in s]}
    groups.update({prefix: [s for s in public if s.startswith(prefix)]
                   for prefix in ['gettimeofday', 'clock_getres_realtime', 'time_', 'getcpu']})
    tables['groups'] = table(['Group', 'V/R change', 'C/R change', 'V/C paired change'],
        [[label, *[f"{100 * (st.geometric_mean(get('read', s, 'reader_cycles', pair)['ratio'] for s in paths) - 1):+.3f}%"
                    for pair in PAIRS]] for label, paths in groups.items()])
    metrics = ['mean_corrected_cycles', 'median_corrected_cycles', 'p95_corrected_cycles', 'p99_corrected_cycles']
    tables['idle'] = table(['Statistic', 'Raw', 'VKSO', 'Copy', 'V−R cycles [95% CI]',
                            'V/R [95% CI]', 'C/R [95% CI]', 'V/C paired [95% CI]'],
        [[metric.removesuffix('_corrected_cycles'), *values('update', 'idle', metric),
          interval(get('update', 'idle', metric), 'difference'),
          *[interval(get('update', 'idle', metric, pair)) for pair in PAIRS]] for metric in metrics])
    scenarios = sorted({r['scenario'] for r in summary if r['metric'] == 'total_rate'})
    tables['concurrent'] = table(['Load', 'Raw Mcalls/s', 'VKSO Mcalls/s', 'Copy Mcalls/s',
                                  'V/R [95% CI]', 'C/R [95% CI]', 'V/C paired [95% CI]'],
        [[s, *values('update', s, 'total_rate', 1e6),
          *[interval(get('update', s, 'total_rate', pair)) for pair in PAIRS]] for s in scenarios])
    tables['writer'] = table(['Load', 'Raw mean', 'VKSO mean', 'Copy mean',
                              'Mean V/R [95% CI]', 'P99 V/R [95% CI]', 'Mean V/C paired [95% CI]'],
        [[s, *values('update', s, metrics[0]), interval(get('update', s, metrics[0])),
          interval(get('update', s, metrics[3])), interval(get('update', s, metrics[0], PAIRS[2]))]
         for s in scenarios])
    tables['writer_all'] = table(['Load', 'Statistic', 'Raw', 'VKSO', 'Copy',
                                  'V/R [95% CI]', 'C/R [95% CI]', 'V/C paired [95% CI]'],
        [[s, metric.removesuffix('_corrected_cycles'), *values('update', s, metric),
          *[interval(get('update', s, metric, pair)) for pair in PAIRS]]
         for s in ['idle', *scenarios] for metric in metrics])
    tables['reader_all'] = table(['Reader/load', 'Raw cycles', 'VKSO cycles', 'Copy cycles',
                                  'V/R [95% CI]', 'C/R [95% CI]', 'V/C paired [95% CI]'],
        [[s, *values('update', s, 'reader_cycles'),
          *[interval(get('update', s, 'reader_cycles', pair)) for pair in PAIRS]]
         for s in sorted({r['scenario'] for r in summary if r['role'] == 'update' and r['metric'] == 'reader_cycles'})])
    fairness = []
    for s in scenarios:
        a = get('update', s, 'jain_fairness')
        b = get('update', s, 'jain_fairness', PAIRS[1])
        numbers = [a['baseline_median'], a['candidate_median'], b['candidate_median']]
        numbers += [min(sc['fairness']['min'] for r in readers for m in r['methods']
                        if m['method'] == method for sc in m.get('scenarios', [])
                        if sc['scenario'] == s) for method in METHODS]
        fairness.append([s, *[f'{v:.6f}' for v in numbers]])
    tables['fairness'] = table(['Load', 'Raw Jain', 'VKSO Jain', 'Copy Jain',
                                'Raw minimum window', 'VKSO minimum window', 'Copy minimum window'], fairness)
    sequence = collections.defaultdict(list)
    for record in readers:
        for method in record['methods']:
            for row in method['sequence_diagnostics']:
                for field in ['cycles_per_read', 'retries_per_million']:
                    sequence[record['step']['role'], row['reader'], method['method'], field].append(float(row[field]))
    tables['sequence'] = table(['Image role', 'Snapshot', 'Raw cycles', 'VKSO cycles', 'Copy cycles',
                                'Raw retries/M', 'VKSO retries/M', 'Copy retries/M'],
        [[role, protocol, *[f'{st.median(sequence[role, protocol, method, field]):.3f}'
                           for field in ['cycles_per_read', 'retries_per_million'] for method in METHODS]]
         for role in ['read', 'update'] for protocol in ['hres_protocol', 'raw_protocol']])
    cpu0 = [dict(row) for row in rows if row['metric'] in metrics]
    patches = {}
    for record in writers:
        directory = Path(record['method_directory'])
        boot_id = json.loads((directory.parent / 'complete.json').read_text())['boot_id']
        for window in record['non_cpu0_windows']:
            path = Path(window['path'])
            for key, value in window['cpu0_corrected_cycles'].items():
                patches[boot_id, directory.name, str(path.parent), int(path.name[6:8]), key + '_corrected_cycles'] = value
    applied = 0
    for row in cpu0:
        key = (row['boot_id'], row['method'], row['scenario'], int(row['round']), row['metric'])
        if key in patches:
            row['value'] = patches[key]
            applied += 1
    assert applied == len(patches)
    sensitivity = analyze.summarize(cpu0)
    ratio_delta = max(abs(r['ratio'] - get(r['role'], r['scenario'], r['metric'],
                       (r['baseline'], r['candidate']))['ratio']) for r in sensitivity)
    cpu_counts = collections.Counter()
    for record in writers:
        cpu_counts.update(record['cpus'])
    sc = [s for r in readers for m in r['methods'] for s in m.get('scenarios', [])]
    rates = [s['actual_to_target_ratio'] for s in sc if s['actual_to_target_ratio']]
    evidence = dict(campaign=str(root), record_audits=str(args.record_audits), writer_audits=str(args.writer_audits),
                    boots=20, normalized_rows=len(rows), comparisons=len(summary),
                    reconstructed_reader_values=sum(m['normalized_reader_values'] for r in readers for m in r['methods']),
                    writer_windows=sum(w['windows'] for w in writers), writer_samples=sum(w['samples'] for w in writers),
                    writer_cpu_counts=dict(cpu_counts), cpu0_patched_values=applied,
                    max_cpu0_ratio_change=ratio_delta, summary_reproduced_byte_for_byte=True,
                    fixed_rate_ratio_min=min(r['min'] for r in rates), fixed_rate_ratio_max=max(r['max'] for r in rates),
                    late_batches=sum(s['late_batches'] for s in sc),
                    minimum_observed_fairness=min(s['fairness']['min'] for s in sc),
                    abi_logs=sum(len(r['methods']) for r in supports),
                    pfn_observations=sum(m['footprint'] is not None for r in supports for m in r['methods']))
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    save_csv(args.output / 'cpu0-writer-summary.csv', sensitivity)
    save_csv(args.output / 'boot-medians.csv',
             [{**dict(zip(analyze.KEY, key[:-1])), 'method': key[-1], 'boot_id': boot, 'value': value}
              for key, by_boot in sorted(boots.items()) for boot, value in sorted(by_boot.items())])
    for name, content in tables.items():
        (args.output / (name + '.md')).write_text(content)
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
