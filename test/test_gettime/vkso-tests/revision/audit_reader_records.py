#!/usr/bin/env python3
"""Audit a completed step's reader CSVs against normalized measurements.

Read-only: no runtime probes or collection changes. Writer samples, ABI logs
and physical-page records have separate audits. Recorded user cycle averages
can be compared, but their absent raw TSC totals cannot be reconstructed.
"""
import argparse
import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from audit_coverage import CLOCKS, PUBLIC_APIS, KEY, verify_rows
from campaign import digest

LOAD_PROTOCOL = 'direct-user-api-multiprocess-batch-v1'
READER_METRICS = {'reader_cycles', 'kernel_reader_cycles', 'actual_total_rate',
                  'late_batches', 'total_rate', 'jain_fairness'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive(value):
    value = float(value)
    require(math.isfinite(value) and value > 0, f'invalid positive value: {value}')
    return value


def rows(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames is not None and
                len(set(reader.fieldnames)) == len(reader.fieldnames), f'{path}: bad header')
        result = list(reader)
    require(result and all(None not in r and None not in r.values() for r in result),
            f'{path}: empty or malformed CSV')
    return result


def add(values, scenario, metric, unit, protocol, repeat, value):
    key = (scenario, metric, unit, protocol, str(repeat))
    require(key not in values, f'duplicate raw observation: {key}')
    require(math.isfinite(value) and value >= 0, f'invalid raw value: {key}')
    values[key] = value


def reconstruct_window(items, clock, count, rate, p, backend):
    require(len(items) == count and Counter(int(r['reader']) for r in items) ==
            Counter(range(count)), 'missing or duplicate reader IDs')
    cpus = [int(c) for c in p['reader_cpus'].split(',')]
    shared = ('scheduled_start_ns', 'scheduled_end_ns', 'writer_start_ns', 'writer_end_ns')
    require(all(len({int(r[k]) for r in items}) == 1 for k in shared),
            'inconsistent shared window timestamps')
    scheduled_start, scheduled_end, writer_start, writer_end = (
        int(items[0][k]) for k in shared)
    require(scheduled_start > 0 and scheduled_end - scheduled_start == p['seconds'] * 10**9,
            'scheduled duration differs from frozen protocol')
    require(writer_start < writer_end, 'invalid writer interval')
    iterations = p['paced_iterations'] if rate else p['iterations']
    warmup = p['paced_warmup'] if rate else p['warmup']
    observed = []
    for r in sorted(items, key=lambda r: int(r['reader'])):
        reader = int(r['reader'])
        require(r['backend'] == backend and r['api'] == 'clock_gettime_' + clock,
                'reader backend/API mismatch')
        require(int(r['cpu']) == cpus[reader] and int(r['readers']) == count,
                'reader CPU/count mismatch')
        require(r['measurement_window'] == LOAD_PROTOCOL and
                int(r['target_total_calls_per_second']) == rate, 'load protocol mismatch')
        start, end = int(r['start_ns']), int(r['end_ns'])
        require(scheduled_start <= start < writer_start < writer_end < end and
                end >= scheduled_end, 'writer interval is not inside reader load window')
        batches, late = int(r['measured_batches']), int(r['late_batches'])
        require(batches > 0 and 0 <= late <= batches, 'invalid batch counters')
        measured, conditioning = int(r['measured_calls']), int(r['conditioning_calls'])
        require(measured == batches * iterations and conditioning == batches * warmup,
                'call counts disagree with frozen batch sizes')
        observed.append(dict(reader=reader, start=start, end=end, calls=measured + conditioning,
                             cycles=positive(r['tsc_cycles_per_call']), late=late, batches=batches,
                             rate=(measured + conditioning) * 1e9 / (end - start)))
    rates = [r['rate'] for r in observed]
    span = max(r['end'] for r in observed) - min(r['start'] for r in observed)
    total = sum(r['calls'] for r in observed) * 1e9 / span
    fairness = sum(rates)**2 / (count * sum(r*r for r in rates))
    return observed, total, fairness, dict(
        writer_envelope_seconds=(writer_end - writer_start) / 1e9,
        leading_margin_seconds=(writer_start - max(r['start'] for r in observed)) / 1e9,
        trailing_margin_seconds=(min(r['end'] for r in observed) - writer_end) / 1e9)


def reconstruct_read(target, backend, p):
    values = {}
    files = {target / f'read-process-{i:02d}.csv' for i in range(p['processes'])}
    require(set(target.glob('read-process-*.csv')) == files, 'READ process-file coverage mismatch')
    offset = 0
    public_path = 'raw_vdso' if backend == 'raw' else 'vkso_wrapper'
    for process, path in enumerate(sorted(files)):
        count = p['rounds'] // p['processes'] + (process < p['rounds'] % p['processes'])
        data = rows(path)
        expected = Counter((api, repeat, kind) for api in PUBLIC_APIS
                           for repeat in range(count) for kind in ('syscall', public_path))
        require(Counter((r['api'], int(r['repeat']), r['path']) for r in data) == expected,
                f'{path}: API/repeat/path coverage mismatch')
        for r in data:
            require(r['backend'] == backend and int(r['pmu_enabled']) == 0,
                    f'{path}: backend or PMU mismatch')
            cycles = positive(r['tsc_cycles_per_call'])
            if r['path'] == public_path:
                add(values, r['api'], 'reader_cycles', 'TSC cycles/call',
                    'direct-user-api-steady-batch-v3', offset + int(r['repeat']), cycles)
        offset += count
    data = rows(target / 'kernel-reader.csv')
    require(Counter((r['api'], int(r['round'])) for r in data) ==
            Counter((clock, repeat) for clock in CLOCKS for repeat in range(p['rounds'])),
            'kernel reader API/round coverage mismatch')
    for r in data:
        require(int(r['cpu']) == p['cpu'] and int(r['iterations']) == p['iterations'],
                'kernel reader CPU/iterations mismatch')
        total = int(r['total_tsc_cycles'])
        positive(total)
        add(values, r['api'], 'kernel_reader_cycles', 'TSC cycles/call',
            'ordinary-kernel-api-batch-v1', int(r['round']), total / p['iterations'])
    return values, {'reader_files': len(files) + 1}


def range_summary(values):
    return dict(min=min(values), median=statistics.median(values), max=max(values))


def reconstruct_update(target, backend, p):
    values, files, scenarios = {}, set(), []
    for clock in CLOCKS:
        for count in (1, 2, 3):
            for rate in (0, p['rate']):
                scenario = f'{clock}/readers-{count}/rate-{rate}'
                observations, windows = [], []
                totals, fairness_values = [], []
                for repeat in range(p['update_rounds']):
                    path = target / scenario / f'round-{repeat:02d}-reader.csv'
                    files.add(path)
                    try:
                        observed, total, fairness, window = reconstruct_window(
                            rows(path), clock, count, rate, p, backend)
                    except (ValueError, KeyError) as error:
                        raise ValueError(f'{path}: {error}') from error
                    observations.extend(observed)
                    windows.append(window)
                    totals.append(total)
                    fairness_values.append(fairness)
                    for r in observed:
                        reader_scenario = scenario + f"/reader-{r['reader']}"
                        for metric, unit, value in (
                            ('reader_cycles', 'TSC cycles/call', r['cycles']),
                            ('actual_total_rate', 'calls/s', r['rate']),
                            ('late_batches', 'batches', r['late'])):
                            add(values, reader_scenario, metric, unit, LOAD_PROTOCOL, repeat, value)
                    add(values, scenario, 'total_rate', 'calls/s', LOAD_PROTOCOL, repeat, total)
                    add(values, scenario, 'jain_fairness', 'fraction', LOAD_PROTOCOL, repeat, fairness)
                scenarios.append(dict(
                    scenario=scenario, windows=len(windows), reader_observations=len(observations),
                    actual_calls_per_second_per_reader=range_summary([r['rate'] for r in observations]),
                    actual_to_target_ratio=range_summary([r['rate']/rate for r in observations]) if rate else None,
                    total_calls_per_second=range_summary(totals), fairness=range_summary(fairness_values),
                    late_batches=sum(r['late'] for r in observations),
                    measured_batches=sum(r['batches'] for r in observations),
                    observations_with_late_batches=sum(r['late'] > 0 for r in observations),
                    **{k: range_summary([w[k] for w in windows]) for k in windows[0]}))
    require(set(target.glob('*/readers-*/rate-*/round-*-reader.csv')) == files,
            'concurrent reader-file coverage mismatch')
    return values, {'reader_files': len(files), 'scenarios': scenarios}


def verify_sequence(target, backend):
    data = rows(target / 'sequence-diagnostic.csv')
    require(Counter(r['reader'] for r in data) == Counter(('hres_protocol', 'raw_protocol')),
            'sequence diagnostic coverage mismatch')
    for r in data:
        require(r['backend'] == backend and int(r['completed']) == 100000000,
                'sequence backend/completed count mismatch')
        retries, odd, changed = (int(r[k]) for k in ('retries', 'odd_seq', 'changed_seq'))
        require(min(retries, odd, changed) >= 0 and retries == odd + changed,
                'sequence retry counters disagree')
        require(math.isclose(float(r['retries_per_million']), retries / 100,
                             rel_tol=0, abs_tol=5e-10), 'sequence retry rate mismatch')
        positive(r['cycles_per_read'])
    return data


def compare_values(data, method, values):
    normalized = {tuple(r[k] for k in KEY[1:]): float(r['value']) for r in data
                  if r['method'] == method and r['metric'] in READER_METRICS}
    require(normalized.keys() == values.keys(), f'{method}: reconstructed coverage mismatch')
    for key, value in values.items():
        require(math.isclose(normalized[key], value, rel_tol=1e-12, abs_tol=1e-9),
                f'{method}/{key}: normalized={normalized[key]}, raw={value}')


def audit(target):
    target = target.resolve()
    root = target.parent
    record = json.loads((target / 'complete.json').read_text())
    plan = json.loads((root / 'plan.json').read_text())
    p = json.loads((root / 'protocol.json').read_text())['parameters']
    step = record['step']
    require(target.name == f"step-{step['index']:03d}" and
            step == plan['steps'][step['index']], 'step identity differs from plan')
    for filename, field in (('plan.json', 'plan_sha256'), ('protocol.json', 'protocol_sha256')):
        require(digest(root / filename) == record[field], f'{filename}: completion identity mismatch')
    require(all(record['parameters'][k] == v for k, v in p.items()), 'parameter identity mismatch')
    require(digest(target / 'measurements.csv') == record['measurements_sha256'],
            'measurements changed after completion')
    data = rows(target / 'measurements.csv')
    package = plan['packages'][step['role']]
    verify_rows(data, step, p, record['boot_id'], package['variant'],
                digest(Path(package['path']) / f"{step['backend']}-bzImage"))
    methods = []
    for method in step['methods']:
        directory = target / method
        reconstruct = reconstruct_read if step['role'] == 'read' else reconstruct_update
        values, report = reconstruct(directory, step['backend'], p)
        compare_values(data, method, values)
        methods.append(dict(method=method, normalized_reader_values=len(values), **report,
                            sequence_diagnostics=verify_sequence(directory, step['backend'])))
    return dict(scope='one completed step: reader CSVs, normalized values and sequence counters',
                step=step, boot_id=record['boot_id'], methods=methods,
                interpretation=('Rates include conditioning calls. Rate deviations and late batches are retained; '
                                'ranges describe observations within this boot. Writer timestamps bracket control '
                                'requests, not exact sample timestamps. ABI/PFN and writer raw audits are separate.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', type=Path, help='completed campaign step directory')
    args = parser.parse_args()
    try:
        result = audit(args.step)
    except (OSError, ValueError, KeyError, IndexError) as error:
        parser.exit(1, f'audit failed: {error}\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
