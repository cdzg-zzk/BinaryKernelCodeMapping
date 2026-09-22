#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Validate complete four-case data; summarize medians at the BOOT level."""
import argparse
import csv
import json
import math
from pathlib import Path
import random
import statistics
import sys

from bundle import PROTOCOL, verify_sums, write_json

CASE_NAMES = (
    'clock_gettime_realtime', 'clock_gettime_monotonic', 'clock_gettime_monotonic_raw',
    'clock_gettime_boottime', 'clock_gettime_tai', 'clock_gettime_realtime_coarse',
    'clock_gettime_monotonic_coarse', 'clock_getres_realtime', 'clock_getres_realtime_coarse',
    'gettimeofday_tv', 'time_null', 'time_pointer', 'getcpu_both',
    'clock_gettime_process_cpu_fallback', 'clock_getres_process_cpu_fallback',
    'clock_gettime_realtime_alarm_fallback',
)
GROUPS = ('raw-normal', 'vkso-normal', 'raw-no-retpoline', 'vkso-no-retpoline')
COLUMNS = ('protocol', 'backend', 'case', 'process_index', 'round', 'iterations',
           'tsc_ticks', 'ticks_per_call', 'cpu', 'aux_start', 'aux_end', 'checksum')


def validate_rows(rows, run):
    expected = set()
    remaining = int(run['repeats'])
    processes = int(run['processes'])
    if not 1 <= processes <= remaining <= 10000:
        raise ValueError('invalid repetition layout')
    for process in range(processes):
        count = (remaining + processes - process - 1) // (processes - process)
        for repeat in range(count):
            for name in CASE_NAMES:
                expected.add((process, repeat, name))
        remaining -= count
    seen = set()
    for row in rows:
        if set(row) != set(COLUMNS) or None in row:
            raise ValueError('unexpected CSV schema')
        if row['protocol'] != PROTOCOL or row['backend'] != run['backend']:
            raise ValueError('mixed protocol/backend')
        key = (int(row['process_index']), int(row['round']), row['case'])
        if key not in expected or key in seen:
            raise ValueError('extra or duplicate sample: ' + str(key))
        seen.add(key)
        iterations, ticks = int(row['iterations']), int(row['tsc_ticks'])
        cost = float(row['ticks_per_call'])
        if iterations != run['iterations'] or iterations <= 0 or ticks <= 0:
            raise ValueError('invalid iteration count or counter')
        if not math.isfinite(cost) or abs(cost - ticks / iterations) > 1e-8:
            raise ValueError('cost does not match the raw batch counter')
        if not 0 <= int(row['aux_start']) < 2**32 or not 0 <= int(row['checksum']) < 2**64:
            raise ValueError('invalid AUX/checksum value')
        if int(row['cpu']) != run['cpu'] or row['aux_start'] != row['aux_end']:
            raise ValueError('CPU/migration mismatch')
    if seen != expected:
        raise ValueError('missing samples; fast-only smoke data are not formal data')


def percentile(values, p):
    values = sorted(values)
    index = (len(values) - 1) * p
    low = int(index)
    fraction = index - low
    return values[low] * (1 - fraction) + values[min(low + 1, len(values) - 1)] * fraction


def ratio_interval(raw, vkso, rng, repeats=10000):
    if len(raw) < 3 or len(vkso) < 3:
        return None
    ratios = [statistics.median(rng.choices(vkso, k=len(vkso))) /
              statistics.median(rng.choices(raw, k=len(raw))) for _ in range(repeats)]
    return [percentile(ratios, 0.025), percentile(ratios, 0.975)]


def summarize(directories):
    groups = {name: [] for name in GROUPS}
    boots = set()
    group_identities = {}
    signature = None
    blocks = {}
    for directory in directories:
        verify_sums(directory, {'run.json', 'samples.csv', 'check.log', 'check-fast.log', 'legacy-abi.log'})
        run = json.loads((directory / 'run.json').read_text())
        if run.get('error') or run.get('cleanup_errors') or run['status'] != 'COMPLETE' or run['protocol'] != PROTOCOL or run['case'] not in groups:
            raise ValueError('incomplete or unknown acquisition: ' + str(directory))
        if run['boot_id'] in boots:
            raise ValueError('same boot counted twice: ' + run['boot_id'])
        boots.add(run['boot_id'])
        block = run.get('block')
        if not isinstance(block, int) or block < 1:
            raise ValueError('missing independent block identity')
        if run['case'] in blocks.setdefault(block, set()):
            raise ValueError('duplicate case in a boot block')
        blocks[block].add(run['case'])
        for name, marker in [('check.log', 'public_api_check=PASS scope=full'),
                             ('check-fast.log', 'time_syscall_denial_check=PASS'),
                             ('legacy-abi.log', 'abi_matrix_status=pass')]:
            if marker not in (directory / name).read_text():
                raise ValueError('missing functional evidence: ' + name)
        expected_backend = 'native-libc' if run['case'].startswith('raw-') else 'vkso-direct'
        if run['backend'] != expected_backend:
            raise ValueError('case/backend mismatch')
        identity = (run['package_manifest_sha256'], run['binary_sha256'],
                    run['package_checksums_sha256'], run['public_library_sha256'])
        if run['case'] in group_identities and group_identities[run['case']] != identity:
            raise ValueError('mixed kernel package or executable within one group')
        group_identities[run['case']] = identity
        current = (run['source_fingerprint'], run['base_cflags'], run['iterations'], run['warmup'], run['repeats'], run['processes'], run['cpu'],
                   run['compiler_version'], run['benchmark_source_sha256'], run['header_sha256'],
                   run['cpu_info'].get('model name'), run['cpu_info'].get('microcode'),
                   json.dumps(run['tuning'], sort_keys=True))
        if signature is not None and current != signature:
            raise ValueError('mixed workload, source, compiler, CPU or tuning')
        signature = current
        with (directory / 'samples.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        validate_rows(rows, run)
        medians = {name: statistics.median(float(r['ticks_per_call']) for r in rows if r['case'] == name)
                   for name in CASE_NAMES}
        groups[run['case']].append({'boot_id': run['boot_id'], 'path': str(directory), 'medians': medians})
    if not all(groups.values()):
        raise ValueError('all four groups are required; no missing group silently omitted')
    if any(cases != set(GROUPS) for cases in blocks.values()):
        raise ValueError('incomplete independent boot block')
    rng = random.Random(20260922)
    comparisons = []
    for variant in ('normal', 'no-retpoline'):
        for name in CASE_NAMES:
            raw = [x['medians'][name] for x in groups['raw-' + variant]]
            vkso = [x['medians'][name] for x in groups['vkso-' + variant]]
            comparisons.append({
                'variant': variant, 'api': name,
                'raw_boots': len(raw), 'vkso_boots': len(vkso),
                'raw_median_ticks': statistics.median(raw), 'vkso_median_ticks': statistics.median(vkso),
                'raw_boot_range': [min(raw), max(raw)], 'vkso_boot_range': [min(vkso), max(vkso)],
                'vkso_over_raw': statistics.median(vkso) / statistics.median(raw),
                'pointwise_bootstrap_95pct': ratio_interval(raw, vkso, rng),
            })
    return {'protocol': PROTOCOL, 'unit': 'TSC ticks/call',
            'estimator': 'median within each boot, then equally weighted median of boot medians',
            'ratio_direction': 'VKSO/Raw cost; above 1 means slower VKSO',
            'inference': 'independent boot resampling; no cross-kernel round pairing; '
                         'CI omitted below 3 boots/group; not an equivalence test or multiplicity correction',
            'groups': groups, 'comparisons': comparisons}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = summarize(args.runs)
        write_json(args.out, result)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('RESULTS REFUSED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
