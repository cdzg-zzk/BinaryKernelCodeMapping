#!/usr/bin/env python3
"""Reconstruct first-touch filtering from archived raw-v1 attempts (read-only)."""
import argparse
import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames is not None and len(set(reader.fieldnames)) == len(reader.fieldnames),
                f'{path}: missing or duplicate CSV header')
        rows = list(reader)
    require(all(None not in r and None not in r.values() for r in rows), f'{path}: malformed CSV')
    return rows


def distribution(values):
    if not values:
        return {'calls': 0}
    values = sorted(values)
    n = len(values)
    return dict(calls=n, minimum=values[0], maximum=values[-1], mean=statistics.mean(values),
                stddev=statistics.pstdev(values),
                **{name: values[n * numerator // 100]
                   for name, numerator in (('p25', 25), ('median', 50), ('p75', 75),
                                           ('p95', 95), ('p99', 99))})


def reconstruct(rows, target, condition):
    require([int(r['sample']) for r in rows] == list(range(len(rows))),
            'sample order/identity mismatch')
    measured, failed = [], []
    for r in rows:
        require(r['target'] == target and r['condition'] == condition, 'target/condition mismatch')
        status = int(r['preparation_status'])
        require(status in (0, -1, -2), 'unknown preparation status')
        if status:
            require(all(r[k] == '' for k in ('cycles', 'minflt', 'majflt')),
                    'failed preparation has latency/fault values')
            failed.append(int(r['sample']))
            continue
        item = {k: int(r[k]) for k in ('cycles', 'minflt', 'majflt')}
        require(item['cycles'] > 0 and item['minflt'] >= 0 and item['majflt'] >= 0,
                'invalid cycle or fault count')
        measured.append(item)
    require(not failed or failed == [len(rows) - 1], 'collection continued after preparation failure')
    faults = (0, 0) if condition == 'hot' else (
        (0, 1) if condition == 'post-drop' and target == 'native' else (1, 0))
    expected = sorted((r['cycles'] for r in measured if (r['minflt'], r['majflt']) == faults))
    retained, bounds = [], None
    if expected:
        q1, q3 = expected[len(expected)//4], expected[3*len(expected)//4]
        bounds = (q1 - 1.5*(q3-q1), q3 + 1.5*(q3-q1))
        retained = [value for value in expected if bounds[0] <= value <= bounds[1]]
    return dict(all_prepared_calls=[r['cycles'] for r in measured], expected_fault_calls=expected,
                iqr_retained_calls=retained, preparation_failures=len(failed), iqr_bounds=bounds,
                fault_classes=Counter(f"{r['minflt']}/{r['majflt']}" for r in measured))


def verify_summary(path, views, total):
    summaries = {}
    for line in path.read_text().splitlines():
        if ': ' in line:
            key, value = line.split(': ', 1)
            require(key not in summaries, f'{path}: duplicate statistic {key}')
            summaries[key] = value.split()[0]
    expected = len(views['expected_fault_calls'])
    retained = views['iqr_retained_calls']
    for key, value in (('Total Runs', total), ('Expected-Fault Runs', expected),
                       ('Valid Runs (IQR)', len(retained)), ('Fault Mismatches', total-expected)):
        require(int(summaries[key]) == value, f'{path}: {key} disagrees with raw records')
    stats = distribution(retained)
    for key, stat, tolerance in (('Median Cycles', 'median', 0), ('P25 Cycles', 'p25', 0),
                                  ('P75 Cycles', 'p75', 0), ('P95 Cycles', 'p95', 0),
                                  ('Mean Cycles', 'mean', .0051), ('Std Deviation', 'stddev', .0051)):
        require(math.isclose(float(summaries[key]), stats[stat], rel_tol=0, abs_tol=tolerance),
                f'{path}: {key} disagrees with raw records')


def audit(root):
    environment = dict(line.split('=', 1) for line in (root/'environment.txt').read_text().splitlines()
                       if '=' in line)
    require(environment['protocol'] == 'first-touch-raw-v1', 'unsupported collection protocol')
    targets, conditions = environment['targets'].split(), environment['conditions'].split()
    require(set(targets) == {'native', 'stub'} and len(targets) == 2, 'invalid target matrix')
    require(conditions and len(set(conditions)) == len(conditions) and
            set(conditions) <= {'hot', 'pte-cold', 'post-drop'}, 'invalid condition matrix')
    runs, goal, limit = (int(environment[k]) for k in
                         ('runs_per_attempt', 'target_successes', 'max_attempts'))
    threshold = float(environment['threshold_pct'])
    require(min(runs, goal, limit) > 0 and 0 <= threshold <= 100, 'invalid collection parameters')
    attempts = read_csv(root/'attempts.csv')
    seen, groups, referenced_raw = set(), {}, set()
    complete = True
    for target in targets:
        for condition in conditions:
            ledger = [r for r in attempts if (r['target'], r['condition']) == (target, condition)]
            require([int(r['attempt']) for r in ledger] == list(range(1, len(ledger)+1)) and
                    len(ledger) <= limit, f'{target}/{condition}: attempt order/budget mismatch')
            values = {key: [] for key in ('all_prepared_calls', 'expected_fault_calls',
                                         'iqr_retained_calls', 'accepted_batch_calls')}
            batch_stats, decisions, faults = [], Counter(), Counter()
            preparation_failures, unavailable = 0, 0
            for entry in ledger:
                identity = (target, condition, int(entry['attempt']))
                require(identity not in seen, 'duplicate attempt')
                seen.add(identity)
                prefix = root / target / condition / f"attempt-{identity[2]:02d}"
                raw_path = Path(str(prefix)+'.samples.csv')
                if raw_path.exists():
                    referenced_raw.add(raw_path)
                success = int(entry['exit_status']) == 0
                require(Path(str(prefix)+'.stdout').exists() and Path(str(prefix)+'.stderr').exists(),
                        f'{prefix}: missing output log')
                available = raw_path.exists() and raw_path.stat().st_size > 0
                require(available or not success, f'{prefix}: successful attempt lacks raw records')
                rows = read_csv(raw_path) if available else []
                require(len(rows) <= runs, f'{prefix}: too many samples')
                views = reconstruct(rows, target, condition)
                if success:
                    require(len(rows) == runs and not views['preparation_failures'],
                            f'{prefix}: incomplete successful attempt')
                    expected, retained = len(views['expected_fault_calls']), len(views['iqr_retained_calls'])
                    require(retained > 0, f'{prefix}: successful attempt retained no samples')
                    for name, number in (('total_runs', runs), ('expected_fault_runs', expected),
                                         ('iqr_retained', retained), ('fault_mismatches', runs-expected)):
                        require(int(entry[name]) == number, f'{prefix}: ledger {name} mismatch')
                    displayed = float(f'{retained * 100.0 / runs:.1f}')
                    require(float(entry['retained_pct']) == displayed, f'{prefix}: retained percentage mismatch')
                    accepted = displayed >= threshold
                    decision = 'accepted' if accepted else 'rejected'
                    reason = 'retention_threshold_met' if accepted else 'retention_below_threshold'
                    require(entry['decision'] == decision and entry['reason'] == reason,
                            f'{prefix}: acceptance decision mismatch')
                    verify_summary(Path(str(prefix)+'.stdout'), views, runs)
                    if accepted:
                        batch_stats.append(distribution(views['iqr_retained_calls']))
                        values['accepted_batch_calls'].extend(views['iqr_retained_calls'])
                        if len(batch_stats) == goal:
                            require(entry is ledger[-1], f'{prefix}: continued after accepted-batch target')
                else:
                    require(entry['decision'] == 'failed', f'{prefix}: error not marked failed')
                    require(entry is attempts[-1], f'{prefix}: continued after failed attempt')
                    unavailable += not available
                decisions[entry['decision']] += 1
                preparation_failures += views['preparation_failures']
                faults.update(views['fault_classes'])
                for key in ('all_prepared_calls', 'expected_fault_calls', 'iqr_retained_calls'):
                    values[key].extend(views[key])
            achieved = len(batch_stats) == goal and not decisions['failed']
            complete &= achieved
            groups[f'{target}/{condition}'] = dict(
                attempts=len(ledger), decisions=dict(decisions), accepted_target_reached=achieved,
                preparation_failures=preparation_failures, attempts_without_raw_records=unavailable,
                fault_classes=dict(faults),
                fault_class_excluded=len(values['all_prepared_calls'])-len(values['expected_fault_calls']),
                iqr_excluded=len(values['expected_fault_calls'])-len(values['iqr_retained_calls']),
                views={key: distribution(data) for key, data in values.items()},
                mean_accepted_batch_statistics={name: statistics.mean(r[name] for r in batch_stats)
                                                for name in ('median', 'mean', 'stddev', 'p25', 'p75', 'p95')}
                if batch_stats else None)
    require(len(seen) == len(attempts), 'ledger contains observations outside the configured matrix')
    require(set(root.glob('*/*/attempt-*.samples.csv')) == referenced_raw,
            'raw sample file has no attempt-ledger entry')
    marked = (root/'complete.txt').exists()
    require(not marked or complete, 'completion marker conflicts with collected evidence')
    return dict(complete=complete and marked, environment=environment, groups=groups,
                quantiles='sorted zero-based floor(n*p), including upper-middle median',
                scope='within-collection descriptive call distributions; calls are not independent deployments')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logs', type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.logs)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'analysis failed: {error}\n')
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
