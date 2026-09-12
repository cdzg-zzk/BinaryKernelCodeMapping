#!/usr/bin/env python3
"""Observe live allocations of the unchanged full BCH implementation in KVM.

The C probe reuses the original benchmark's allocation/verification helpers.
The original complete three-backend correctness matrix runs separately in the
same registration session. No performance samples are collected here.
"""
from pathlib import Path
import ctypes
import json
import os
import subprocess
import sys
import traceback

sys.path.insert(0, '/work/helpers')
import bch_resources as resource

OUT = Path('/work/validation/bch_heap')
PROBE = Path('/work/helpers/libbch_heap_probe.so')
PHASES = ('initialized', 't4-active', 't4-released', 't8-active',
          't8-released', 'controls-released')


def allocation_pages(allocations):
    """Cover requested bytes, retaining overlapping allocation memberships."""
    rows = resource.map_rows(Path('/proc/self/maps').read_text())
    pages = {}
    for item in allocations:
        start, size = item['address'], item['requested_bytes']
        assert start > 0 and size > 0 and item['usable_bytes'] >= size, item
        for address in range(start // resource.PAGE * resource.PAGE,
                             (start + size + resource.PAGE - 1) // resource.PAGE * resource.PAGE,
                             resource.PAGE):
            region = next(row for row in rows if row['start'] <= address < row['end'])
            assert 'r' in region['permissions'] and 'w' in region['permissions'], region
            page = pages.setdefault(address, {'address': address, 'role': 'heap',
                'permissions': region['permissions'], 'vma': region, 'allocations': []})
            page['allocations'].append({key: item[key] for key in
                                       ('case_index', 't', 'category', 'name')})
    return list(pages.values())


def loader_main(library_path, role, plan_path):
    library_path = Path(library_path).resolve()
    probe = ctypes.CDLL(str(PROBE))
    probe.probe_load.argtypes = [ctypes.c_char_p, ctypes.c_int]
    probe.probe_activate.argtypes = [ctypes.c_int]
    probe.probe_report.restype = ctypes.c_char_p

    def command(expected, function=None, *args):
        assert sys.stdin.readline().strip() == expected
        if function:
            result = function(*args)
            assert result == 0, (expected, result, probe.probe_report())

    def probe_state(phase):
        state = json.loads(probe.probe_report())
        assert state['report_ok'] and state['last_errno'] == 0, state
        expected = {'loaded': ('loaded', -1), 'faulted': ('loaded', -1),
                    'initialized': ('initialized', -1), 't4-active': ('active', 0),
                    't4-released': ('deactivated', -1), 't8-active': ('active', 1),
                    't8-released': ('deactivated', -1), 'controls-released': ('released', -1)}
        assert (state['stage'], state['active_case']) == expected[phase], state
        assert state['allocator_verified'], state
        return state

    def report(phase, targets):
        state = probe_state(phase)
        print(json.dumps({'phase': phase, 'pid': os.getpid(), 'probe': state,
                          'targets': targets + allocation_pages(state['allocations'])}), flush=True)

    print(json.dumps({'phase': 'before', 'pid': os.getpid()}), flush=True)
    command('load', probe.probe_load, os.fsencode(library_path), int(role == 'carrier'))
    plan = {int(row[0]): {'kernel_address': row[1], 'kind': row[2], 'section': row[3]}
            for row in resource.mappings(Path(plan_path))} if plan_path != '-' else {}
    paths = [(library_path, role), (PROBE, 'observer')]
    if role == 'carrier':
        paths.append((library_path.parent / 'libshim.so', 'shim'))
    layouts, targets = [], []
    for path, kind in paths:
        layout = resource.elf_layout(path)
        base = resource.base_address(layout)
        layouts.append(dict(layout, load_bias=base, role=kind))
        targets += resource.loaded_pages(layout, base, kind, plan)
    print(json.dumps({'phase': 'loaded', 'pid': os.getpid(), 'targets': targets,
                      'layouts': layouts, 'probe': probe_state('loaded')}), flush=True)
    command('fault')
    checksum = 0
    for item in targets:
        checksum ^= ctypes.c_ubyte.from_address(item['fault_address']).value
    report('faulted', targets)
    command('initialize', probe.probe_initialize)
    report('initialized', targets)
    command('activate-t4', probe.probe_activate, 0)
    report('t4-active', targets)
    command('deactivate-t4', probe.probe_deactivate)
    report('t4-released', targets)
    command('activate-t8', probe.probe_activate, 1)
    report('t8-active', targets)
    command('deactivate-t8', probe.probe_deactivate)
    report('t8-released', targets)
    command('free-controls', probe.probe_release)
    report('controls-released', targets)
    command('release')


def run_role(role, library, plan_path=None):
    destination = OUT / role
    destination.mkdir(parents=True, exist_ok=False)
    initial = resource.system_snapshot(destination / 'initial-system',
                                       observe_modules=role != 'native-before-owner')
    owner = [row['pfn'] for row in initial['modules'].get('vkso_bch', {}).get('observed_pages', [])]
    plan = resource.mappings(plan_path) if plan_path else []
    source = resource.kernel_pages([row[1] for row in plan], destination / 'declared-source') if plan else {}
    if plan:
        assert set(source) == {row[1] for row in plan}, (source, plan)
        assert set(source.values()).issubset(owner), (source, owner)
    role_record = {'role': role, 'library': str(library), 'identity': resource.identity(),
                   'plan': plan, 'owner_core_pfns': owner, 'source_pfns': source,
                   'groups': [], 'status': 'running'}
    resource.write(destination / 'role.json', role_record)
    try:
        for count in (1, 4, 16):
            group = destination / f'n{count:02}'
            group.mkdir()
            processes, errors = [], []
            try:
                for index in range(count):
                    error = (group / f'loader-{index:02}.stderr').open('w')
                    errors.append(error)
                    process = subprocess.Popen([sys.executable, '/work/guest.py', '--heap-loader',
                        str(library), 'carrier' if plan else 'native', str(plan_path) if plan else '-'],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error, text=True, bufsize=1)
                    processes.append(process)

                def collect(phase):
                    # Every process is alive at the same stage throughout the census.
                    replies = [resource.receive(process, phase) for process in processes]
                    for process, reply in zip(processes, replies):
                        folder = group / str(process.pid) / phase
                        record = resource.snapshot(process.pid, folder, reply.get('targets'))
                        resource.write(folder / 'probe.json', reply)
                        if plan and phase != 'before':
                            declared_rows = [row for row in record['target_pages'] if row.get('declared')]
                            assert len(declared_rows) == len(plan), (phase, declared_rows, plan)
                            assert {(row['file_offset'], row['declared']['kernel_address'])
                                    for row in declared_rows} == {(row[0], row[1]) for row in plan}
                        for row in record['target_pages']:
                            declared = row.get('declared')
                            if declared and phase != 'loaded':
                                assert row['present'] and row['pfn'] == source[declared['kernel_address']], row
                                assert 'w' not in row['permissions'], row
                    return replies

                def advance(command, phase):
                    for process in processes:
                        process.stdin.write(command + '\n')
                        process.stdin.flush()
                    return collect(phase)

                collect('before')
                advance('load', 'loaded')
                advance('fault', 'faulted')
                advance('initialize', 'initialized')
                advance('activate-t4', 't4-active')
                advance('deactivate-t4', 't4-released')
                advance('activate-t8', 't8-active')
                advance('deactivate-t8', 't8-released')
                final = advance('free-controls', 'controls-released')
                assert all(not reply['probe']['allocations'] for reply in final), final
                if plan:
                    manager_pid = int((resource.RUNTIME / 'manager.pid').read_text())
                    resource.snapshot(manager_pid, group / 'manager')
                resource.system_snapshot(group / 'final-system')
                role_record['groups'].append({'count': count, 'pids': [p.pid for p in processes],
                    'phases': ['before', 'loaded', 'faulted', *PHASES], 'status': 'pass'})
                print(f'bch_heap_role={role} loaders={count}:pass', flush=True)
            finally:
                for process in processes:
                    if process.poll() is None:
                        try:
                            process.stdin.write('release\n')
                            process.stdin.flush()
                            process.wait(timeout=10)
                        except (BrokenPipeError, subprocess.TimeoutExpired):
                            process.terminate()
                            process.wait(timeout=10)
                    if process.returncode:
                        role_record.setdefault('loader_exit_failures', []).append(
                            {'pid': process.pid, 'returncode': process.returncode})
                for error in errors:
                    error.close()
            assert not role_record.get('loader_exit_failures'), role_record
            resource.write(destination / 'role.json', role_record)
        role_record['status'] = 'pass'
    except BaseException:
        role_record['status'] = 'fail'
        role_record['error'] = traceback.format_exc()
        raise
    finally:
        resource.write(destination / 'role.json', role_record)


def main():
    functional = resource.functional
    original_execute = functional.execute
    restored = False

    def execute_hook(command, log, environment=None):
        nonlocal restored
        words = list(map(str, command))
        if words[:1] == ['insmod'] and words[1].endswith('/vkso_bch.ko'):
            run_role('native-before-owner', resource.NATIVE)
        if len(words) > 1 and words[:2] == ['/work/repo/vkso', 'exec']:
            run_role('native-owner-loaded', resource.NATIVE)
        if words[:1] == ['rmmod'] and not restored:
            restored = True
            resource.system_snapshot(OUT / 'restored-before-module-unload', observe_modules=True)
        return original_execute(command, log, environment)

    functional.execute = execute_hook
    result = functional.main()
    roles = [json.loads((OUT / role / 'role.json').read_text()) for role in
             ('native-before-owner', 'native-owner-loaded', 'registered-carrier')
             if (OUT / role / 'role.json').exists()]
    passed = result == 0 and len(roles) == 3 and all(row['status'] == 'pass' for row in roles)
    resource.write(OUT / 'result.json', {'status': 'pass' if passed else 'fail',
        'identity': resource.identity(), 'functional_status': result, 'loader_count': 63,
        'scope': 'two persistent m13 t4/t8 controls and codewords per independent loader; one full-decode context at a time; original complete correctness separately in same session',
        'limitations': ['requested live allocations and their resident-page coverage exclude allocator metadata and freed transient allocations',
                        'covering PFNs may contain unrelated allocations; PFN exclusivity is not inferred from VMA/exclusive flags',
                        'after-free whole-process observations include allocator retention and observer activity; freed addresses are not dereferenced',
                        'sequential snapshots and generic Python/C observer overhead are not application-only total footprint',
                        'dedicated owner preload is controlled, not evidence of original kernel demand',
                        'guest observations are not physical-machine performance measurements']})
    print('bch_heap_validation=' + ('pass' if passed else 'fail'), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    if sys.argv[1:2] == ['--heap-loader']:
        loader_main(*sys.argv[2:])
    elif sys.argv[1:] == ['--validate-bch']:
        fields = dict(line.split('=', 1) for line in
                      (resource.functional.WORK / 'vkso/metadata/outputs.env').read_text().splitlines())
        run_role('registered-carrier', Path(fields['library']).resolve(), Path(fields['page_map']))
        resource.functional.validate_bch()
    else:
        raise SystemExit(main())
