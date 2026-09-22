#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Invoked INSIDE the existing verified registration/cleanup window.
Does not load modules, register pages, change affinity policy, or reboot.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

PROTOCOL = 'public-direct-v1'
FIELDS = ('protocol,implementation,api,repeat,iterations,tsc_cycles_total,'
          'tsc_cycles_per_call,aux_start,aux_end,status').split(',')
APIS = {
    'clock_gettime_realtime', 'clock_gettime_monotonic', 'clock_gettime_monotonic_raw',
    'clock_gettime_boottime', 'clock_gettime_tai', 'clock_gettime_realtime_coarse',
    'clock_gettime_monotonic_coarse', 'clock_gettime_process_cpu_fallback',
    'clock_gettime_realtime_alarm_fallback', 'clock_getres_realtime',
    'clock_getres_realtime_coarse', 'clock_getres_process_cpu_fallback',
    'gettimeofday_tv', 'time_null', 'time_pointer', 'getcpu_both', 'getcpu_null',
}

def validate_rows(rows, implementation, repeats, iterations, offset=0):
    if repeats < 1 or iterations < 1 or offset < 0:
        raise ValueError('invalid repetition or batch size')
    expected = {(api, r) for api in APIS for r in range(offset, offset + repeats)}
    seen = set()
    for row in rows:
        if set(row) != set(FIELDS) or None in row.values():
            raise ValueError('incorrect CSV fields')
        key = (row['api'], int(row['repeat']))
        if key not in expected or key in seen:
            raise ValueError(f'unexpected or duplicate observation: {key}')
        seen.add(key)
        if row['protocol'] != PROTOCOL or row['implementation'] != implementation:
            raise ValueError('mixed protocol or implementation')
        if row['status'] != 'OK' or row['aux_start'] != row['aux_end']:
            raise ValueError('rejected batch (not silently filtered)')
        n = int(row['iterations'])
        total = int(row['tsc_cycles_total'])
        cost = float(row['tsc_cycles_per_call'])
        if n != iterations or total <= 0 or not math.isfinite(cost) or cost <= 0:
            raise ValueError('invalid timing observation')
        if not math.isclose(cost, total / n, rel_tol=1e-9, abs_tol=1e-8):
            raise ValueError('per-call time does not match raw batch time')
    if seen != expected:
        raise ValueError('incomplete API/repeat matrix')

def collect(args):
    if args.repeats < 1 or not 1 <= args.processes <= args.repeats:
        raise ValueError('require 1 <= processes <= repeats')
    if args.iterations < 1 or args.warmup < 0 or args.cpu < 0:
        raise ValueError('invalid measurement parameters')
    if os.environ.get('LD_PRELOAD') is not None or os.environ.get('LD_AUDIT') is not None:
        raise ValueError('LD_PRELOAD/LD_AUDIT are forbidden')
    package = args.package.resolve()
    meta = json.loads((package / 'public-api/manifest.json').read_text())
    if meta['protocol'] != PROTOCOL or meta['api_count'] != len(APIS):
        raise ValueError('unsupported public protocol')
    implementation = {'raw': 'native-libc', 'vkso': 'vkso-direct'}[args.backend]
    binary = package / f'public-api/{args.backend}-public-bench'
    args.output.mkdir()  # parent belongs to the guarded collector
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = str(package)
    prefix = ['setarch', platform.machine(), '-R', str(binary), '--cpu', str(args.cpu)]
    # Separate processes: validation filters/instrumentation never reach timing.
    for mode in ('--check', '--check-fastpath'):
        with (args.output / (mode[2:] + '.log')).open('w') as log:
            subprocess.run(prefix + [mode], env=env, stdout=log, stderr=log, check=True)
    all_rows = []
    offset = 0
    for process in range(args.processes):
        repeats = (args.repeats - offset + args.processes - process - 1) // (args.processes - process)
        path = args.output / f'process-{process:02}.csv'
        with path.open('w') as out, path.with_suffix('.stderr').open('w') as err:
            subprocess.run(prefix + ['--iterations', str(args.iterations),
                           '--warmup', str(args.warmup), '--repeats', str(repeats),
                           '--offset', str(offset)], env=env, stdout=out, stderr=err, check=True)
        with path.open(newline='') as inp:
            reader = csv.DictReader(inp)
            if reader.fieldnames != FIELDS:
                raise ValueError('unexpected CSV header')
            rows = list(reader)
        validate_rows(rows, implementation, repeats, args.iterations, offset)
        all_rows.extend(rows)
        offset += repeats
    validate_rows(all_rows, implementation, args.repeats, args.iterations)
    with (args.output / 'public.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)
    # Full manifests and source patch are evidence, not a hash-only reference.
    for name in ('boot-manifest.txt', 'source.patch'):
        shutil.copy2(package / name, args.output / name)
    shutil.copy2(package / 'SHA256SUMS', args.output / 'package-SHA256SUMS')
    shutil.copytree(package / 'public-api/source', args.output / 'source')
    shutil.copy2(package / 'public-api/manifest.json', args.output / 'build-manifest.json')
    record = dict(protocol=PROTOCOL, backend=args.backend, implementation=implementation,
                  case=args.case, run_id=args.run_id, cpu=args.cpu, warmup=args.warmup,
                  iterations=args.iterations, repeats=args.repeats, processes=args.processes,
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                  carrier_sha256=meta['carrier_sha256'],
                  uname=list(platform.uname()), libc=platform.libc_ver(),
                  timing='elapsed TSC ticks per complete public call; batch mean',
                  validation='public API + separate syscall-denial process PASS',
                  physical_page_identity='NOT_MEASURED_BY_THIS_COLLECTOR',
                  status='complete')
    (args.output / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n')
    paths = sorted(p for p in args.output.rglob('*') if p.is_file())
    (args.output / 'SHA256SUMS').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' +
        str(p.relative_to(args.output)) + '\n' for p in paths))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=('raw', 'vkso'), required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--run-id', required=True)
    for name in ('cpu', 'iterations', 'repeats', 'processes', 'warmup'):
        parser.add_argument('--' + name, type=int, required=True)
    try:
        collect(parser.parse_args())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'public collection failed: {error}', file=sys.stderr)
        sys.exit(1)
