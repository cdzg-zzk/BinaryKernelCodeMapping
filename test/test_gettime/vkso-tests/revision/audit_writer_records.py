#!/usr/bin/env python3
"""Read-only UPDATE raw writer audit; run after timed collection has ended."""
import argparse
import csv
import json
import math
import re
import statistics
from collections import Counter
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def metrics(values):
    ordered = sorted(values)
    require(bool(ordered), 'no action=0 samples')

    def quantile(fraction):
        index = (len(ordered) - 1) * fraction
        lower = math.floor(index)
        return ordered[lower] + (ordered[math.ceil(index)] - ordered[lower]) * (index - lower)

    return {'mean': statistics.fmean(ordered), 'median': statistics.median(ordered),
            'p95': quantile(.95), 'p99': quantile(.99)}


def same_number(actual, expected, label):
    require(math.isfinite(float(actual)) and
            math.isclose(float(actual), expected, rel_tol=1e-12, abs_tol=1e-9),
            f'{label}: {actual} != {expected}')


def audit_file(path):
    with path.open(newline='') as stream:
        header = stream.readline()
        match = re.fullmatch(r'# tsc_pair_min=(\d+) seen=(\d+) dropped=(\d+)\s*', header)
        require(match is not None, f'{path}: invalid recorder header')
        overhead, seen, dropped = map(int, match.groups())
        require(dropped == 0, f'{path}: dropped={dropped}')
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ['sample', 'cycles', 'action', 'cpu'],
                f'{path}: unexpected columns')
        cpus, actions, selected_cpus = Counter(), Counter(), Counter()
        normal, cpu0 = [], []
        count = 0
        for index, row in enumerate(reader):
            sample, cycles, action, cpu = (int(row[key]) for key in reader.fieldnames)
            require(sample == index, f'{path}: nonsequential sample {sample} at {index}')
            require(min(cycles, action, cpu) >= 0, f'{path}: negative recorder field')
            count += 1
            cpus[cpu] += 1
            actions[action] += 1
            if action == 0:
                normal.append(cycles)
                selected_cpus[cpu] += 1
                if cpu == 0:
                    cpu0.append(cycles)
    require(count == seen, f'{path}: header seen={seen}, rows={count}')
    corrected = [max(0, value - overhead) for value in normal]
    raw_stats, corrected_stats = metrics(normal), metrics(corrected)
    expected = {'count': len(normal), 'other_actions': count - len(normal),
                'tsc_pair_min': overhead, 'min_cycles': min(normal), 'max_cycles': max(normal)}
    expected.update({key + '_cycles': value for key, value in raw_stats.items()})
    expected.update({key + '_corrected_cycles': value for key, value in corrected_stats.items()})
    summary = json.loads(path.with_suffix('.json').read_text())
    require(summary.keys() == expected.keys(), f'{path}: summary fields differ')
    for key, value in expected.items():
        same_number(summary[key], value, f'{path}: {key}')
    return {'samples': count, 'cpus': cpus, 'actions': actions,
            'action0_cpus': selected_cpus, 'corrected_cycles': corrected_stats,
            'cpu0_corrected_cycles': metrics([max(0, value - overhead) for value in cpu0])
            if cpu0 else None}


def audit_method(directory):
    require((directory.parent / 'complete.json').is_file(),
            'method must belong to a completed boot; do not scan active timed collection')
    with (directory.parent / 'measurements.csv').open(newline='') as stream:
        rows = [row for row in csv.DictReader(stream)
                if row['method'] == directory.name and row['role'] == 'update'
                and row['metric'].endswith('_corrected_cycles')]
    expected = {}
    for row in rows:
        path = directory / row['scenario'] / f"round-{int(row['round']):02d}-writer.csv"
        metric = row['metric'].removesuffix('_corrected_cycles')
        values = expected.setdefault(path, {})
        require(metric not in values, f'{path}: duplicate normalized {metric}')
        values[metric] = row['value']
    require(bool(expected), 'no normalized UPDATE writer observations')
    require(set(directory.rglob('*-writer.csv')) == set(expected),
            'raw writer file coverage differs from normalized observations')
    require(set(directory.rglob('*-writer.json')) == {p.with_suffix('.json') for p in expected},
            'writer summary file coverage differs from normalized observations')
    totals = {key: Counter() for key in ('cpus', 'actions', 'action0_cpus')}
    affected, samples = [], 0
    for path, values in sorted(expected.items()):
        report = audit_file(path)
        require(values.keys() == report['corrected_cycles'].keys(),
                f'{path}: incomplete normalized writer metrics')
        for key, value in report['corrected_cycles'].items():
            same_number(values[key], value, f'{path}: normalized {key}')
        samples += report['samples']
        for key in totals:
            totals[key].update(report[key])
        if any(cpu != 0 for cpu in report['cpus']):
            affected.append({'path': str(path.relative_to(directory)), **report})
    return {'scope': 'raw writer coverage, headers, sample indices, summary/normalized agreement',
            'method_directory': str(directory), 'windows': len(expected), 'samples': samples,
            **totals, 'non_cpu0_windows': affected,
            'interpretation': 'Main results retain every action=0 sample. Action=0 does not '
                              'identify a unique caller. CPU0-only statistics are descriptive '
                              'sensitivity diagnostics, not replacements for main results.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('method_directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_method(args.method_directory), indent=2))


if __name__ == '__main__':
    main()
