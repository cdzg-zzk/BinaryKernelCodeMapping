#!/usr/bin/env python3
"""Reconstruct BCH loader accounting from saved guest records; no live accesses."""
from pathlib import Path
import argparse
import json
import struct

PAGE = 4096
MASK = (1 << 55) - 1


def read(path):
    return json.loads(path.read_text())


def raw_pfns(directory):
    record = read(directory / 'record.json')
    data = (directory / 'pagemap.bin').read_bytes()
    pfns, by_address = set(), {}
    missing = []
    for row in record['pagemap_ranges']:
        if row.get('error') or row.get('short_read'):
            missing.append(row)
        start, length = row['binary_offset'], row['bytes_read']
        assert length % 8 == 0
        assert start + length <= len(data)
        for index, (entry,) in enumerate(struct.iter_unpack('<Q', data[start:start + length])):
            address = row['start'] + index * PAGE
            if entry & (1 << 63):
                pfn = entry & MASK
                assert pfn, ('present PFN hidden', directory, address)
                pfns.add(pfn)
            if any(target['address'] == address for target in record['target_pages']):
                by_address[address] = entry
    for target in record['target_pages']:
        assert by_address[target['address']] == int(target['pagemap_entry'], 16), (directory, target)
    return pfns, missing


def status(path, field):
    return next(int(line.split()[1]) for line in path.read_text().splitlines()
                if line.startswith(field + ':'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    validation = root / 'evidence/validation'
    base = validation / 'bch_resources'
    result = read(base / 'result.json')
    assert result['status'] == 'pass'
    boot = result['identity']['boot_id']
    overall = {'status': 'running', 'boot_id': boot, 'groups': [], 'module_core': {},
               'scope': 'same-session loader PFN accounting; no timing and no whole-system net-saving claim'}
    source_csv = validation / 'source-pages.csv'
    import csv
    source_rows = list(csv.DictReader(source_csv.open()))
    source = {int(row['kernel_vaddr'], 0): int(row['pfn']) for row in source_rows}
    declared = set(source.values())
    assert len(source) == len(declared) == 4
    all_pids = set()
    owner_pfns = None
    for role in ('native-before-owner', 'native-owner-loaded', 'registered-carrier'):
        directory = base / role
        role_record = read(directory / 'role.json')
        assert role_record['status'] == 'pass' and role_record['identity']['boot_id'] == boot
        assert [group['loader_count'] for group in role_record['groups']] == [1, 4, 16]
        initial = read(directory / 'initial-system/system.json')
        assert initial['identity']['boot_id'] == boot
        if role == 'native-before-owner':
            assert not initial['modules']
            assert 'vkso_bch ' not in (directory / 'initial-system/modules.txt').read_text()
        else:
            for name, module in initial['modules'].items():
                assert module['attributes']['initstate'] == 'live'
                assert int(module['attributes']['initsize']) == 0
                assert not module['missing_addresses'], (role, name)
                addresses = {row['address'] for row in module['observed_pages']}
                assert addresses == set(module['requested_addresses'])
                assert module['core_bytes'] == module['rounded_core_bytes']
                pfns = {row['pfn'] for row in module['observed_pages']}
                assert len(pfns) * PAGE == module['core_bytes']
                previous = overall['module_core'].get(name)
                item = {'core_bytes': module['core_bytes'], 'pfns': sorted(pfns),
                        'pages': len(pfns), 'coverage': 'all coresize pages observed; init size zero',
                        'section_annotations': module['observed_pages']}
                if previous:
                    assert previous['pfns'] == item['pfns']
                overall['module_core'][name] = item
                if name == 'vkso_bch':
                    owner_pfns = pfns
                    assert declared.issubset(owner_pfns)
                    assert all(next(row['pfn'] for row in module['observed_pages']
                                    if row['address'] == address) == pfn for address, pfn in source.items())
        for count in (1, 4, 16):
            group = directory / f'n{count:02}'
            recorded = read(group / 'summary.json')
            pids = recorded['loader_pids']
            assert len(pids) == len(set(pids)) == count and not all_pids.intersection(pids)
            all_pids.update(pids)
            aggregate, targets, declared_user, ptes, deltas, missing = set(), set(), set(), [], [], []
            private_support = set()
            for pid in pids:
                process = group / str(pid)
                for phase in ('before', 'loaded', 'faulted'):
                    phase_record = read(process / phase / 'record.json')
                    assert phase_record['pid'] == pid and phase_record['boot_id'] == boot
                    raw, omitted = raw_pfns(process / phase)
                    # x86 vsyscall is outside normal pagemap coverage; preserve it explicitly.
                    assert all(row['path'] == '[vsyscall]' for row in omitted), omitted
                    if phase == 'faulted':
                        aggregate.update(raw)
                        missing.extend(omitted)
                        for row in phase_record['target_pages']:
                            assert row['present'] and row['pfn']
                            targets.add(row['pfn'])
                            if row['declared']:
                                assert row['pfn'] == source[row['declared']['kernel_address']]
                                assert 'w' not in row['permissions']
                                declared_user.add(row['pfn'])
                            elif row['role'] in ('carrier', 'shim') and not row['file_or_shared_anon']:
                                private_support.add(row['pfn'])
                after = status(process / 'faulted/status.txt', 'VmPTE')
                before = status(process / 'before/status.txt', 'VmPTE')
                ptes.append(after)
                deltas.append(after - before)
            assert targets == set(recorded['target_pfn_union'])
            if role == 'registered-carrier':
                assert declared_user == declared
                assert recorded['declared_loader_mappings'] == count * 4
                assert len(recorded['categories']['declared-text']['pfn_union']) == 3
                assert len(recorded['categories']['declared-rodata']['pfn_union']) == 1
                assert not private_support.intersection(owner_pfns)
                for key in ('declared-text', 'declared-rodata'):
                    assert set(recorded['categories'][key]['pfn_distinct_process_count'].values()) == {count}
            item = {'role': role, 'loaders': count,
                    'target_library_and_shim_pfn_union_pages': len(targets),
                    'declared_user_pfn_union_pages': len(declared_user),
                    'declared_kernel_user_union_pages': len(declared_user | declared) if role == 'registered-carrier' else None,
                    'target_plus_owner_core_union_pages': len(targets | owner_pfns) if role != 'native-before-owner' else None,
                    'all_loader_vma_union_pages': len(aggregate),
                    'VmPTE_kb_per_loader': ptes, 'VmPTE_delta_kb_per_loader': deltas,
                    'VmPTE_kb_sum': sum(ptes), 'VmPTE_delta_kb_sum': sum(deltas),
                    'categories': recorded['categories'],
                    'pagemap_unread_ranges': len(missing)}
            if role == 'registered-carrier':
                manager = group / 'manager'
                manager_pfns, omitted = raw_pfns(manager)
                assert all(row['path'] == '[vsyscall]' for row in omitted)
                manager_pid = read(manager / 'record.json')['pid']
                assert manager_pid == int((group / 'manager.pid').read_text())
                item['manager'] = {'pid': manager_pid, 'observed_vma_union_pages': len(manager_pfns),
                    'VmPTE_kb': status(manager / 'status.txt', 'VmPTE'),
                    'VmRSS_kb': status(manager / 'status.txt', 'VmRSS'),
                    'RssAnon_kb': status(manager / 'status.txt', 'RssAnon'),
                    'RssFile_kb': status(manager / 'status.txt', 'RssFile'),
                    'Pss_kb': status(manager / 'smaps_rollup.txt', 'Pss'),
                    'loader_manager_union_pages': len(aggregate | manager_pfns)}
            overall['groups'].append(item)
    assert len(all_pids) == 63
    restored = read(base / 'restored-before-module-unload/system.json')
    for name, module in restored['modules'].items():
        assert sorted(row['pfn'] for row in module['observed_pages']) == overall['module_core'][name]['pfns']
    correctness = read(validation / 'bch-validation.json')
    assert correctness['status'] == 'pass'
    assert correctness['coverage']['decode_checks_from_unchanged_loop'] == 10752
    assert read(validation / 'status.json')['restoration_verified'] is True
    overall.update(status='pass', total_distinct_loaders=len(all_pids),
                   declared_source_pfns=sorted(declared), correctness_status='pass',
                   limitations=result['limitations'])
    (root / 'bch_resource-audit.json').write_text(json.dumps(overall, indent=2) + '\n')
    print(json.dumps({key: overall[key] for key in ('status', 'boot_id', 'total_distinct_loaders')}, indent=2))
    for row in overall['groups']:
        print(row['role'], row['loaders'], 'target_pages', row['target_library_and_shim_pfn_union_pages'],
              'target+owner', row['target_plus_owner_core_union_pages'], 'VmPTE_delta_kb', row['VmPTE_delta_kb_sum'])


if __name__ == '__main__':
    main()
