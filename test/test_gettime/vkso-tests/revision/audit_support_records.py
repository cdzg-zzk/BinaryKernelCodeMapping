#!/usr/bin/env python3
"""Read-only ABI-log and declared-closure PFN audit for one completed step.

This checks saved observations, not current mappings, general VM operations,
module lifetime, whole-system memory or performance. The ABI contract below
is the default abi_matrix.c mode used by the frozen Clocktime collector.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

from audit_reader_records import require
from campaign import digest
from carrier import mappings

FAST_CLOCKS = ('realtime', 'monotonic', 'monotonic_raw', 'boottime', 'tai',
               'realtime_coarse', 'monotonic_coarse')
NATIVE_CLOCKS = ('process_cpu', 'thread_cpu', 'realtime_alarm', 'boottime_alarm')


def abi_contract():
    expected = Counter()

    def add(prefix, names, status='pass'):
        expected.update((prefix + name, status) for name in names)

    add('semantics.clock_gettime.', FAST_CLOCKS + NATIVE_CLOCKS + (
        'encoded_process_cpu', 'encoded_thread_cpu', 'invalid', 'dynamic_invalid_fd',
        'invalid_positive', 'null', 'dynamic_success'))
    add('semantics.clock_getres.', FAST_CLOCKS + NATIVE_CLOCKS + (
        'invalid_null', 'encoded_cpu', 'dynamic_invalid_fd', 'invalid_positive', 'dynamic_success'))
    add('semantics.gettimeofday.', ('tv', 'tz', 'both', 'null'))
    add('', ('semantics.time.null_pointer', 'semantics.getcpu.outputs_null_cache',
             'semantics.multicpu_threads', 'path.fallback.single_syscall',
             'security.mapping_permissions', 'namespace.fast_paths', 'namespace.fast_paths',
             'namespace.exec.child', 'namespace.exec.lifecycle', 'namespace.offsets_frozen',
             'namespace.setns.commit', 'namespace.lifecycle_status', 'abi_matrix_status'))
    add('path.clock_gettime.', FAST_CLOCKS + ('realtime_null',), 'fast')
    add('path.clock_gettime.', NATIVE_CLOCKS + (
        'encoded_process_cpu', 'encoded_thread_cpu', 'dynamic', 'invalid', 'invalid_slot',
        'invalid_large', 'process_cpu_null', 'dynamic_success'), 'fallback')
    add('path.clock_getres.', FAST_CLOCKS + ('realtime_null',), 'fast')
    add('path.clock_getres.', (
        'process_cpu', 'process_cpu_null', 'encoded_process_cpu', 'dynamic', 'invalid',
        'invalid_null', 'invalid_slot', 'invalid_large_null', 'dynamic_success',
        'dynamic_success_null'), 'fallback')
    add('path.gettimeofday.', ('tv', 'tz', 'both', 'null'), 'fast')
    add('path.time.', ('null', 'pointer'), 'fast')
    add('path.getcpu.', ('both', 'cpu', 'node', 'null', 'cache'), 'fast')
    return expected


def verify_abi(text, backend):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    abi_backend = 'raw-vdso' if backend == 'raw' else backend
    require(lines and lines[0] == f'backend={abi_backend}' and lines[-1] == 'abi_matrix_status=pass',
            'ABI backend/final status mismatch')
    records, details = Counter(), {}
    for line in lines[1:]:
        words = line.split()
        require('=' in words[0], f'malformed ABI line: {line}')
        key, status = words[0].split('=', 1)
        records[(key, status)] += 1
        attrs = dict(word.split('=', 1) for word in words[1:])
        details.setdefault(key, []).append(attrs)
    expected = abi_contract()
    require(records == expected,
            f'ABI coverage/status mismatch: missing={list((expected-records).items())[:4]}, '
            f'extra={list((records-expected).items())[:4]}')
    threads = int(details['semantics.multicpu_threads'][0]['threads'])
    require(threads > 0, 'ABI thread count must be positive')
    require(details['security.mapping_permissions'] == [dict(code='R-X', data='R--', context='R--')],
            'ABI mapping permissions mismatch')
    require(details['path.fallback.single_syscall'] == [dict(cases='3')],
            'single-syscall case count mismatch')
    require(details['namespace.fast_paths'] == [dict(clocks='5'), dict(clocks='5')],
            'namespace fast-path count mismatch')
    require(details['namespace.offsets_frozen'] == [dict(errno='EACCES')],
            'namespace offset outcome mismatch')
    return dict(pass_records=sum(n for (_, status), n in records.items() if status == 'pass'),
                path_records=sum(n for (_, status), n in records.items() if status in ('fast', 'fallback')),
                thread_count=threads, multiple_cpus_exercised=threads > 1,
                scope='default ABI matrix, including namespace exec/setns; event modes are separate')


def smaps_regions(lines, carrier_suffix):
    regions = []
    for line in lines:
        columns = line.split(maxsplit=5)
        if not columns or not re.fullmatch(r'[0-9a-f]+-[0-9a-f]+', columns[0]):
            continue
        require(len(columns) == 6 and columns[5].endswith('/' + carrier_suffix),
                'smaps carrier identity mismatch')
        start, end = (int(v, 16) for v in columns[0].split('-'))
        require(start < end, 'invalid smaps address interval')
        regions.append((int(columns[2], 16), end - start, columns[1]))
    require(regions, 'missing carrier smaps headers')
    return regions


def verify_footprint(record, plan, method, carrier_suffix):
    require(method in ('vkso', 'compact-split') and record['method'] == method,
            'footprint method mismatch')
    pages = record['pages']
    expected = Counter((offset, kind, section) for offset, _, kind, section in plan)
    actual = Counter((r['file_offset'], r['kind'], r['section']) for r in pages)
    require(actual == expected, 'footprint page coverage differs from original page plan')
    require(record['scope'] ==
            'declared closure pages; smaps adds carrier support, not whole-system net memory',
            'footprint accounting scope mismatch')
    regions = smaps_regions(record['carrier_smaps'], carrier_suffix)
    for r in pages:
        require(all(type(r[k]) is int and r[k] > 0 for k in ('user_pfn', 'kernel_pfn')),
                'invalid or unavailable PFN')
        shared = r['user_pfn'] == r['kernel_pfn']
        require(type(r['shared']) is bool and r['shared'] == shared,
                'recorded shared flag disagrees with PFNs')
        require(shared == (method == 'vkso' or r['kind'] == 'shared_data'),
                'unexpected copied/shared backing')
        # Loader reservations can overlap apparent file offsets; inspect the
        # actual readable mapping covering the entire declared page.
        perms = [perm for offset, length, perm in regions if perm.startswith('r') and
                 offset <= r['file_offset'] and r['file_offset'] + 4096 <= offset + length]
        require(perms == ['r-xp' if r['kind'] == 'text' else 'r--p'],
                f"unexpected readable mapping permissions for {r['section']}: {perms}")
    source = {r['kernel_pfn'] for r in pages}
    user = {r['user_pfn'] for r in pages}
    require(len(source) == len(pages) and len(user) == len(pages),
            'distinct declared pages alias the same PFN')
    if method == 'compact-split':
        copied = {r['user_pfn'] for r in pages if r['kind'] != 'shared_data'}
        require(not copied & source, 'copied page aliases another kernel source page')
    counts = dict(distinct_source_pfns=len(source), distinct_user_pfns=len(user),
                  source_user_union_pfns=len(source | user))
    require(all(type(record[k]) is int and record[k] == v for k, v in counts.items()),
            'footprint totals disagree with PFN sets')
    return dict(**counts, shared_pages=sum(r['shared'] for r in pages),
                copied_pages=sum(not r['shared'] for r in pages),
                scope='declared closure only; normal loader mapping permissions')


def verify_same_boot_sources(records):
    sources = [{r['file_offset']: r['kernel_pfn'] for r in record['pages']} for record in records]
    require(sources and all(source == sources[0] for source in sources[1:]),
            'VKSO/copy source PFNs differ within the same boot')


def audit(target):
    target = target.resolve()
    root = target.parent
    complete = json.loads((target / 'complete.json').read_text())
    plan = json.loads((root / 'plan.json').read_text())
    step = complete['step']
    require(target.name == f"step-{step['index']:03d}" and
            step == plan['steps'][step['index']], 'step identity differs from plan')
    for filename, field in (('plan.json', 'plan_sha256'), ('protocol.json', 'protocol_sha256')):
        require(digest(root / filename) == complete[field], f'{filename}: completion identity mismatch')
    require(digest(target / 'measurements.csv') == complete['measurements_sha256'],
            'measurements changed after completion')
    original_map = mappings(Path(plan['packages'][step['role']]['path']) / 'page_mappings.txt')
    methods, footprints = [], []
    for method in step['methods']:
        directory = target / method
        report = dict(method=method, abi=verify_abi((directory / 'functional.log').read_text(),
                                                   step['backend']))
        if method != 'raw':
            record = json.loads((directory / 'footprint.json').read_text())
            suffix = f'{target.name}/{method}/package/libkernel.so'
            report['footprint'] = verify_footprint(record, original_map, method, suffix)
            footprints.append(record)
        else:
            report['footprint'] = None
        methods.append(report)
    if footprints:
        verify_same_boot_sources(footprints)
    return dict(step=step, boot_id=complete['boot_id'], methods=methods,
                scope='saved ABI and PFN observations in one completed step; no live runtime probes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', type=Path, help='completed campaign step directory')
    args = parser.parse_args()
    try:
        result = audit(args.step)
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        parser.exit(1, f'audit failed: {error}\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
