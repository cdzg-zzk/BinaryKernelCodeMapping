#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Separate scalar-kernel diagnostic; never changes campaign state or boots.

collect --execute uses the existing package/preflight/tuning controls and loads
only its matching kernel-reader module. Scalar data cannot enter the formal
three-interface kernel CSV. Summary reports equal-boot means, not equivalence.
"""
import argparse
import csv
import fcntl
import io
import json
import os
from pathlib import Path
import statistics
import sys

from bundle import kv_file, sha256, verify_sums, write_json
from collect import CASES, logged, preflight
from package_check import check
from supplemental import controlled_tuning

PROTOCOL = 'clocktime-kernel-scalar-v1'
APIS = ('ktime_get', 'ktime_get_raw', 'ktime_get_real', 'ktime_get_boottime', 'ktime_get_tai')
COLUMNS = ('api', 'round', 'cpu', 'iterations', 'total_tsc_cycles', 'checksum')
DEBUGFS = Path('/sys/kernel/debug/vkso_kernel_reader')


def validate(text, cpu, iterations, rounds):
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != list(COLUMNS):
        raise ValueError('unexpected scalar CSV header')
    expected = {(api, r) for api in APIS for r in range(rounds)}
    seen, values = set(), {api: [] for api in APIS}
    for row in reader:
        if set(row) != set(COLUMNS) or None in row or any(v is None for v in row.values()):
            raise ValueError('malformed scalar CSV row')
        key = row['api'], int(row['round'])
        if key not in expected or key in seen:
            raise ValueError('duplicate/unexpected scalar sample')
        if int(row['cpu']) != cpu or int(row['iterations']) != iterations:
            raise ValueError('scalar CPU/iteration mismatch')
        ticks, checksum = int(row['total_tsc_cycles']), int(row['checksum'])
        if not 0 < ticks < 2**64 or not 0 <= checksum < 2**64:
            raise ValueError('invalid scalar counter/checksum')
        values[key[0]].append(ticks / iterations)
        seen.add(key)
    if seen != expected:
        raise ValueError('missing scalar samples')
    return {api: statistics.mean(v) for api, v in values.items()}


def inventory(out):
    (out / 'SHA256SUMS').write_text(''.join(sha256(f) + '  ' + f.name + '\n'
        for f in sorted(out.iterdir()) if f.is_file() and f.name != 'SHA256SUMS'))


def collect_scalar(a):
    package = a.package.resolve()
    build = check(package)
    if a.case.split('-', 1)[1] != build['build_variant']:
        raise ValueError('package/case variant mismatch')
    if not a.execute:
        print('NOT_RUN: package valid; --execute requires a matching READ boot and root')
        return
    if os.geteuid() != 0:
        raise ValueError('--execute requires root; do not run a parallel campaign')
    out = a.out.resolve()
    if out == package or package in out.parents:
        raise ValueError('output must be outside the immutable package')
    backend = a.case.split('-', 1)[0]
    out.mkdir(parents=True, exist_ok=False)
    record = dict(protocol=PROTOCOL, status='FAIL', label=a.label, case=a.case,
                  cpu=a.cpu, iterations=a.iterations, rounds=a.rounds, warmup=a.warmup,
                  scope='separate kernel diagnostic; no carrier registration or campaign update',
                  tool_sha256=sha256(__file__))
    old_affinity = os.sched_getaffinity(0)
    try:
        with open('/run/vkso-direct-api.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with controlled_tuning(package, backend):
                _, _, _, environment = preflight(package / 'direct', a.case, a.cpu)
                record['environment'] = environment
                record['module_sha256'] = sha256(package / (backend + '-kernel-reader.ko'))
                record['manifest'] = kv_file(package / 'boot-manifest.txt')
                os.sched_setaffinity(0, {0})
                loaded = False
                try:
                    logged(['insmod', str(package / (backend + '-kernel-reader.ko'))],
                           out / 'reader-load.log', dict(os.environ))
                    loaded = True
                    if not (DEBUGFS / 'scalar_control').is_file():
                        raise ValueError('package reader lacks scalar suite; rebuild matching package')
                    (DEBUGFS / 'scalar_control').write_text(
                        f'{a.cpu} {a.iterations} {a.rounds} {a.warmup}\n')
                    text = (DEBUGFS / 'scalar_samples').read_text()
                    (out / 'samples.csv').write_text(text)
                    record['mean_ticks_per_call'] = validate(text, a.cpu, a.iterations, a.rounds)
                finally:
                    if loaded:
                        logged(['rmmod', 'vkso_kernel_reader'], out / 'reader-unload.log', dict(os.environ))
        record['status'] = 'COMPLETE'
    except BaseException as exc:
        record['status'] = 'FAIL'
        record['error'] = str(exc)
        raise
    finally:
        try:
            os.sched_setaffinity(0, old_affinity)
        except OSError as exc:
            record['status'] = 'FAIL'
            record['affinity_restore_error'] = str(exc)
            raise
        finally:
            write_json(out / 'scalar.json', record)
            inventory(out)
    print('scalar_diagnostic=COMPLETE out=' + str(out))


def summarize(directories):
    groups, boots, signature, identities = {}, set(), None, {}
    for directory in directories:
        verify_sums(directory, {'scalar.json', 'samples.csv'})
        r = json.loads((directory / 'scalar.json').read_text())
        if r['protocol'] != PROTOCOL or r['status'] != 'COMPLETE':
            raise ValueError('not a complete scalar diagnostic')
        e = r['environment']
        if e['boot_id'] in boots:
            raise ValueError('same boot counted twice; reboot for an independent observation')
        boots.add(e['boot_id'])
        current = (r['cpu'], r['iterations'], r['rounds'], r['warmup'],
                   e['compiler_version'], json.dumps(e['cpu_info'], sort_keys=True),
                   json.dumps(e['tuning'], sort_keys=True))
        if signature is not None and current != signature:
            raise ValueError('workload/compiler/hardware/tuning mismatch')
        signature = current
        key = r['label'] + ':' + r['case']
        identity = (e['kernel_image_sha256'], r['module_sha256'])
        if key in identities and identities[key] != identity:
            raise ValueError('mixed kernels or modules within a group')
        identities[key] = identity
        means = validate((directory / 'samples.csv').read_text(), r['cpu'], r['iterations'], r['rounds'])
        groups.setdefault(key, []).append(dict(boot_id=e['boot_id'], means=means, path=str(directory)))
    if not groups:
        raise ValueError('no scalar observations')
    return dict(protocol=PROTOCOL, unit='TSC ticks/call', estimator='mean within boot, equally weighted boots',
                inference='descriptive means/ranges only; no equivalence or confidence claim',
                groups={key: dict(boots=len(runs), observations=runs,
                    apis={api: dict(mean=statistics.mean(x['means'][api] for x in runs),
                                    minimum=min(x['means'][api] for x in runs),
                                    maximum=max(x['means'][api] for x in runs)) for api in APIS})
                        for key, runs in groups.items()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('collect')
    c.add_argument('--package', type=Path, required=True)
    c.add_argument('--case', choices=CASES, required=True)
    c.add_argument('--label', choices=['reference', 'candidate'], required=True)
    c.add_argument('--out', type=Path, required=True)
    c.add_argument('--cpu', type=int, default=2)
    c.add_argument('--iterations', type=int, default=500000)
    c.add_argument('--rounds', type=int, default=31)
    c.add_argument('--warmup', type=int, default=10000)
    c.add_argument('--execute', action='store_true')
    s = sub.add_parser('summarize')
    s.add_argument('runs', type=Path, nargs='+')
    s.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.command == 'collect':
        if not (a.cpu >= 0 and 1 <= a.iterations <= 1000000 and 1 <= a.rounds <= 1000
                and 0 <= a.warmup <= 1000000):
            p.error('invalid scalar workload')
        collect_scalar(a)
    else:
        write_json(a.out, summarize(a.runs))
        print('scalar_summary=' + str(a.out))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        sys.exit('scalar refused/failed: ' + str(exc))
