#!/usr/bin/env python3
"""Read-only audit of normalized coverage; does not certify raw-sample quality."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from analyze import boot_values
from campaign import digest, pending

CLOCKS = ('monotonic', 'monotonic_raw', 'monotonic_coarse')
PUBLIC_APIS = (
    'clock_gettime_realtime', 'clock_gettime_monotonic',
    'clock_gettime_monotonic_raw', 'clock_gettime_boottime', 'clock_gettime_tai',
    'clock_gettime_realtime_coarse', 'clock_gettime_monotonic_coarse',
    'clock_gettime_process_cpu_fallback', 'clock_gettime_realtime_alarm_fallback',
    'clock_getres_realtime', 'clock_getres_realtime_coarse',
    'clock_getres_process_cpu_fallback', 'gettimeofday_tv', 'gettimeofday_timezone',
    'gettimeofday_both', 'gettimeofday_null', 'time_null', 'time_pointer',
    'getcpu_both', 'getcpu_null',
)
KEY = ('method', 'scenario', 'metric', 'unit', 'protocol', 'round')


def expected_rows(step, parameters):
    expected = Counter()

    def add(method, scenario, metric, unit, protocol, rounds):
        for repeat in range(rounds):
            expected[(method, scenario, metric, unit, protocol, str(repeat))] += 1

    for method in step['methods']:
        if step['role'] == 'read':
            for api in PUBLIC_APIS:
                add(method, api, 'reader_cycles', 'TSC cycles/call',
                    'direct-user-api-steady-batch-v3', parameters['rounds'])
            for clock in CLOCKS:
                add(method, clock, 'kernel_reader_cycles', 'TSC cycles/call',
                    'ordinary-kernel-api-batch-v1', parameters['rounds'])
            continue
        if step['role'] != 'update':
            raise ValueError('unknown collection role')
        scenarios = [('idle', 0)] + [
            (f'{clock}/readers-{count}/rate-{rate}', count)
            for clock in CLOCKS for count in (1, 2, 3)
            for rate in (0, parameters['rate'])]
        for scenario, count in scenarios:
            rounds = parameters['update_rounds']
            for metric in ('mean', 'median', 'p95', 'p99'):
                add(method, scenario, metric + '_corrected_cycles', 'TSC cycles/update',
                    'full-writer-load-interior-v1' if count else 'full-writer-idle-v1', rounds)
            if not count:
                continue
            protocol = 'direct-user-api-multiprocess-batch-v1'
            for metric, unit in (('total_rate', 'calls/s'), ('jain_fairness', 'fraction')):
                add(method, scenario, metric, unit, protocol, rounds)
            for reader in range(count):
                for metric, unit in (('reader_cycles', 'TSC cycles/call'),
                                     ('actual_total_rate', 'calls/s'), ('late_batches', 'batches')):
                    add(method, f'{scenario}/reader-{reader}', metric, unit, protocol, rounds)
    return expected


def verify_rows(rows, step, parameters, boot_id, variant, image_sha256):
    for row in rows:
        for field, value in (('boot_id', boot_id), ('role', step['role']),
                             ('variant', variant), ('image_sha256', image_sha256)):
            if row[field] != value:
                raise ValueError(f'inconsistent {field}: {row[field]}')
    boot_values(rows)  # Reject duplicate observations and invalid numeric values.
    actual = Counter(tuple(row[key] for key in KEY) for row in rows)
    expected = expected_rows(step, parameters)
    missing, extra = expected - actual, actual - expected
    if missing or extra:
        raise ValueError(f'coverage mismatch: missing={list(missing.items())[:5]}, '
                         f'extra={list(extra.items())[:5]}')


def audit(root):
    plan = json.loads((root / 'plan.json').read_text())
    parameters = json.loads((root / 'protocol.json').read_text())['parameters']
    next_step = pending(root, plan)  # Check completion identities and file digests.
    completed = len(plan['steps']) if next_step is None else next_step['index']
    reports = []
    image_digests = {}
    for step in plan['steps'][:completed]:
        target = root / f"step-{step['index']:03d}"
        record = json.loads((target / 'complete.json').read_text())
        package = plan['packages'][step['role']]
        image = Path(package['path']) / f"{step['backend']}-bzImage"
        if image not in image_digests:
            image_digests[image] = digest(image)
        with (target / 'measurements.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        verify_rows(rows, step, parameters, record['boot_id'],
                    package['variant'], image_digests[image])
        reports.append({'step': step['index'], 'boot_id': record['boot_id'],
                        'rows': len(rows), 'methods': step['methods']})
    return {'scope': 'normalized coverage and completion identities; raw-sample audit separate',
            'complete_campaign': next_step is None, 'planned_boots': len(plan['steps']),
            'audited_boots': completed, 'steps': reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path)
    args = parser.parse_args()
    result = audit(args.campaign)
    print(json.dumps(result, indent=2))
    # A successful partial audit must not look like a completed campaign.
    return 0 if result['complete_campaign'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
