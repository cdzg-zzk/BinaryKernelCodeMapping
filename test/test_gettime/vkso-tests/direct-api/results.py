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

from bundle import PROTOCOL, verify_sums, write_json, kv_file

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


KERNEL_APIS = ('monotonic', 'monotonic_raw', 'monotonic_coarse')
KERNEL_COLUMNS = ('api', 'round', 'cpu', 'iterations', 'total_tsc_cycles', 'checksum')


def validate_kernel_rows(rows, run):
    """Check the existing kernel-reader CSV without changing its schema/unit."""
    expected = {(api, repeat) for api in KERNEL_APIS for repeat in range(run['repeats'])}
    seen = set()
    for row in rows:
        if set(row) != set(KERNEL_COLUMNS):
            raise ValueError('unexpected kernel-reader CSV schema')
        key = (row['api'], int(row['round']))
        if key not in expected or key in seen:
            raise ValueError('extra or duplicate kernel-reader sample')
        if (int(row['cpu']) != run['cpu'] or int(row['iterations']) != run['iterations'] or
                not 0 < int(row['total_tsc_cycles']) < 2**64 or
                not 0 <= int(row['checksum']) < 2**64):
            raise ValueError('invalid kernel-reader sample')
        seen.add(key)
    if seen != expected:
        raise ValueError('missing kernel-reader samples')


def validate_sharing(sharing):
    """Validate the existing sharing.py output, not a new PFN observation.

    sharing.py already rejects writable/executable permission mismatches before
    emitting this record. PFN identity is checked again here so an incomplete
    evidence set cannot be treated as a validated VKSO acquisition.
    """
    if not isinstance(sharing, dict) or sharing.get('method') != 'vkso':
        raise ValueError('wrong sharing observation method')
    pages = sharing.get('pages')
    if not isinstance(pages, list) or not pages:
        raise ValueError('empty sharing observation')
    offsets, source_pfns, user_pfns, kinds = set(), set(), set(), set()
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError('invalid sharing page record')
        offset = page.get('file_offset')
        source, user = page.get('kernel_pfn'), page.get('user_pfn')
        kind = page.get('kind')
        if (type(offset) is not int or offset < 0 or offset % 4096 or offset in offsets or
                type(source) is not int or not 0 < source < 2**55 or
                type(user) is not int or not 0 < user < 2**55 or
                page.get('shared') is not True or source != user or
                kind not in ('text', 'rodata', 'shared_data')):
            raise ValueError('invalid or unshared PFN page record')
        offsets.add(offset)
        source_pfns.add(source)
        user_pfns.add(user)
        kinds.add(kind)
    if not {'text', 'shared_data'}.issubset(kinds):
        raise ValueError('sharing observation lacks Clocktime text/state pages')
    counts = {'distinct_source_pfns': len(source_pfns),
              'distinct_user_pfns': len(user_pfns),
              'source_user_union_pfns': len(source_pfns | user_pfns)}
    for key, count in counts.items():
        if type(sharing.get(key)) is not int or sharing[key] != count:
            raise ValueError('inconsistent sharing PFN count: ' + key)


def validate_evidence(directory, run, checksums):
    """Use files already produced by collect.py; Raw never requires a carrier."""
    if 'kernel-reader.csv' not in checksums:
        raise ValueError('missing checksummed kernel-reader.csv')
    status = run.get('kernel_reader')
    if not isinstance(status, str) or status.split(';', 1)[0] != 'PASS':
        raise ValueError('kernel reader evidence was not completed')
    with (directory / 'kernel-reader.csv').open() as stream:
        validate_kernel_rows(list(csv.DictReader(stream)), run)
    if run['backend'] == 'vkso-direct':
        if run.get('pfn_identity') != 'PASS' or 'sharing.json' not in checksums:
            raise ValueError('missing completed/checksummed VKSO PFN evidence')
        validate_sharing(json.loads((directory / 'sharing.json').read_text()))
    elif run.get('pfn_identity') != 'SKIP: Raw does not graft a carrier':
        raise ValueError('unexpected Raw PFN evidence status')


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
    package_identities = {}
    signature = None
    blocks = {}
    for directory in directories:
        checksums = verify_sums(directory, {'run.json', 'samples.csv', 'check.log', 'check-fast.log', 'legacy-abi.log'})
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
        validate_evidence(directory, run, checksums)
        # Raw and VKSO of one mitigation variant come from the SAME package.
        # The two benchmark executables intentionally differ; do not compare them.
        variant = run['case'].split('-', 1)[1]
        package_identity = tuple(run.get(key) for key in (
            'package_manifest_sha256', 'package_checksums_sha256',
            'public_library_sha256', 'carrier_sha256'))
        if not all(isinstance(value, str) and value for value in package_identity):
            raise ValueError('missing paired package identity')
        if variant in package_identities and package_identities[variant] != package_identity:
            raise ValueError('Raw/VKSO package mismatch within variant: ' + variant)
        package_identities[variant] = package_identity
        for key in ('git_commit', 'dirty_patch_sha256'):
            if not isinstance(run.get(key), str) or not run[key]:
                raise ValueError('missing kernel source identity: ' + key)
        identity = (run['package_manifest_sha256'], run['binary_sha256'],
                    run['package_checksums_sha256'], run['public_library_sha256'])
        if run['case'] in group_identities and group_identities[run['case']] != identity:
            raise ValueError('mixed kernel package or executable within one group')
        group_identities[run['case']] = identity
        source_manifest = directory / 'package-boot-manifest.txt'
        if source_manifest.exists():
            if 'package-boot-manifest.txt' not in checksums:
                raise ValueError('kernel source manifest not checksummed')
            provenance = kv_file(source_manifest)
            trees = {k: provenance[k] for k in ('raw_source_tree_sha256', 'vkso_source_tree_sha256')}
            if 'kernel_source_trees' in run and run['kernel_source_trees'] != trees:
                raise ValueError('kernel source identity mismatch')
            source_identity = json.dumps(trees, sort_keys=True)
        else:
            source_identity = (run['git_commit'], run['dirty_patch_sha256'])
        current = (source_identity, run['source_fingerprint'], run['base_cflags'], run['iterations'], run['warmup'], run['repeats'], run['processes'], run['cpu'],
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
