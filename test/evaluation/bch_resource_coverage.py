#!/usr/bin/env python3
"""Independently check an extracted BCH resource artifact; print JSON, write nothing.

Usage: python3 bch_resource_coverage.py ATTEMPT_DIRECTORY > coverage.json
Requires pyelftools. The directory must contain the archived evidence/payload
trees (extract bch_resource-evidence.tar.gz into a separate directory if needed).
No guest, target library, saved Python module, or other inferior is executed.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import struct

from elftools.elf.elffile import ELFFile

PAGE = 4096
MASK = (1 << 55) - 1
ROLES = ('native-before-owner', 'native-owner-loaded', 'registered-carrier')


def read(path):
    return json.loads(path.read_text())


def elf_loads(path):
    with path.open('rb') as stream:
        return [{key: int(segment[key]) for key in
                 ('p_vaddr', 'p_offset', 'p_filesz', 'p_memsz', 'p_flags')}
                for segment in ELFFile(stream).iter_segments()
                if segment['p_type'] == 'PT_LOAD']


def raw_pages(directory):
    record = read(directory / 'record.json')
    assert not record.get('read_errors'), (directory, record.get('read_errors'))
    data = (directory / 'pagemap.bin').read_bytes()
    entries, pfns, omitted = {}, set(), []
    offset = 0
    for region in record['pagemap_ranges']:
        assert region['binary_offset'] == offset, (directory, region)
        length = region['bytes_read']
        assert length % 8 == 0 and offset + length <= len(data)
        if region.get('error') or region.get('short_read'):
            assert region['path'] == '[vsyscall]', (directory, region)
            omitted.append(region['path'])
        else:
            assert length == region['requested_entries'] * 8, (directory, region)
        for index, (entry,) in enumerate(struct.iter_unpack('<Q', data[offset:offset + length])):
            address = region['start'] + index * PAGE
            assert address not in entries, (directory, address)
            entries[address] = entry
            if entry & (1 << 63):
                assert entry & MASK, (directory, 'present PFN unavailable', address)
                pfns.add(entry & MASK)
        offset += length
    assert offset == len(data), directory
    for target in record['target_pages']:
        entry = entries[target['address']]
        assert entry == int(target['pagemap_entry'], 16), (directory, target)
        assert target['present'] == bool(entry & (1 << 63))
        assert target['pfn'] == entry & MASK
        assert target['file_or_shared_anon'] == bool(entry & (1 << 61))
        assert target['exclusive_bit'] == bool(entry & (1 << 56))
    return record, pfns, omitted


def status(path, key):
    return next(int(line.split()[1]) for line in path.read_text().splitlines()
                if line.startswith(key + ':'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attempt', type=Path)
    args = parser.parse_args()
    root = args.attempt.resolve()
    validation = root / 'evidence/validation'
    base = validation / 'bch_resources'
    audit = read(root / 'bch_resource-audit.json')
    assert audit['status'] == 'pass'
    boot = audit['boot_id']
    outputs = dict(line.split('=', 1) for line in
                   (validation / 'export/vkso/metadata/outputs.env').read_text().splitlines())
    native_path = '/work/binaries/libbch-kernel-native.so'
    carrier_path = outputs['library']
    shim_path = str(Path(carrier_path).parent / 'libshim.so')
    report = {'status': 'running', 'boot_id': boot, 'groups': [],
              'scope': 'independent offline ELF coverage, raw PFN/category and manager/PTE checks',
              'raw_loader_snapshots_checked': 0, 'loader_count': 0,
              'module_censuses_checked_against_raw_csv': 0,
              'unread_ranges': {}, 'manager_groups': []}

    def resolve(guest_path):
        if guest_path.startswith('/work/validation/'):
            return validation / guest_path.removeprefix('/work/validation/')
        assert guest_path.startswith('/work/'), guest_path
        return root / 'payload' / guest_path.removeprefix('/work/')

    seen_pids = set()
    for role in ROLES:
        initial = base / role / 'initial-system'
        for name, module in read(initial / 'system.json')['modules'].items():
            source = {}
            for path in (initial / name).glob('pages-*.csv'):
                with path.open() as stream:
                    source.update({int(row['kernel_vaddr'], 0): int(row['pfn'])
                                   for row in csv.DictReader(stream)})
            assert source == {row['address']: row['pfn'] for row in module['observed_pages']}
            assert set(source) == set(range(module['core_base'],
                module['core_base'] + module['core_bytes'], PAGE))
            assert not module['missing_addresses']
            assert module['attributes']['initsize'] == '0'
            assert module['attributes']['initstate'] == 'live'
            report['module_censuses_checked_against_raw_csv'] += 1
        for count in (1, 4, 16):
            group = base / role / f'n{count:02}'
            summary = read(group / 'summary.json')
            audited = next(row for row in audit['groups']
                           if row['role'] == role and row['loaders'] == count)
            assert len(summary['loader_pids']) == count
            targets_union, all_union, categories = set(), set(), {}
            virtual_count, ptes, deltas = 0, [], []
            for pid in summary['loader_pids']:
                assert pid not in seen_pids
                seen_pids.add(pid)
                process = group / str(pid)
                loader = read(process / 'loader.json')
                for phase in ('before', 'loaded', 'faulted'):
                    record, pfns, omitted = raw_pages(process / phase)
                    assert record['pid'] == pid and record['boot_id'] == boot
                    report['raw_loader_snapshots_checked'] += 1
                    for name in omitted:
                        report['unread_ranges'][name] = report['unread_ranges'].get(name, 0) + 1
                    if phase == 'faulted':
                        all_union.update(pfns)
                actual = {row['address']: row for row in record['target_pages']}
                assert len(actual) == len(record['target_pages'])
                expected = {}
                expected_libraries = {carrier_path, shim_path} if role == 'registered-carrier' else {native_path}
                assert len(loader['layouts']) == len(expected_libraries)
                assert {layout['path'] for layout in loader['layouts']} == expected_libraries
                for layout in loader['layouts']:
                    # Re-read real ELF headers, rather than accepting recorded targets.
                    segments = elf_loads(resolve(layout['path']))
                    assert segments == layout['segments']
                    first = min(segments, key=lambda row: row['p_vaddr'])
                    matches = [row for row in record['pagemap_ranges']
                               if row['path'] == layout['path']
                               and row['file_offset'] == first['p_offset'] // PAGE * PAGE]
                    assert len(matches) == 1, (pid, layout['path'], matches)
                    bias = matches[0]['start'] - first['p_vaddr'] // PAGE * PAGE
                    for segment in segments:
                        begin = bias + segment['p_vaddr']
                        end = begin + segment['p_memsz']
                        for address in range(begin // PAGE * PAGE,
                                             (end + PAGE - 1) // PAGE * PAGE, PAGE):
                            if address in expected:
                                assert expected[address] == layout['path']
                            expected[address] = layout['path']
                assert set(expected) == set(actual), (role, count, pid, 'PT_LOAD coverage')
                assert all(actual[address]['library'] == path for address, path in expected.items())
                for address, path in expected.items():
                    expected_role = 'native' if path == native_path else 'shim' if path == shim_path else 'carrier'
                    assert actual[address]['role'] == expected_role
                virtual_count += len(expected)
                for row in actual.values():
                    assert row['present'] and row['pfn']
                    targets_union.add(row['pfn'])
                    if row['declared']:
                        category = 'declared-' + row['declared']['kind']
                    elif row['role'] == 'native':
                        category = 'native-' + ('executable' if 'x' in row['permissions']
                            else 'writable' if 'w' in row['permissions'] else 'readonly')
                    else:
                        category = ('carrier-support' if row['role'] == 'carrier' else 'shim')
                        category += '-' + ('writable' if 'w' in row['permissions'] else 'readonly')
                    categories.setdefault(category, []).append((pid, row['pfn']))
                after = status(process / 'faulted/status.txt', 'VmPTE')
                ptes.append(after)
                deltas.append(after - status(process / 'before/status.txt', 'VmPTE'))
            assert targets_union == set(summary['target_pfn_union'])
            assert len(targets_union) == audited['target_library_and_shim_pfn_union_pages']
            assert len(all_union) == audited['all_loader_vma_union_pages']
            assert set(categories) == set(summary['categories'])
            for category, rows in categories.items():
                old = summary['categories'][category]
                pfns = {pfn for _, pfn in rows}
                assert old['mapping_count'] == len(rows) and set(old['pfn_union']) == pfns
                assert old['distinct_pfns'] == len(pfns)
                assert old['pfn_distinct_process_count'] == {
                    str(pfn): len({pid for pid, other in rows if other == pfn}) for pfn in pfns}
            assert ptes == audited['VmPTE_kb_per_loader']
            assert deltas == audited['VmPTE_delta_kb_per_loader']
            report['groups'].append({'role': role, 'loaders': count,
                'complete_target_virtual_pages': virtual_count,
                'distinct_target_pfns': len(targets_union),
                'VmPTE_delta_kb_per_loader': deltas})
            if 'manager' in audited:
                manager_record, manager_pfns, omitted = raw_pages(group / 'manager')
                assert manager_record['boot_id'] == boot
                manager = audited['manager']
                assert manager_record['pid'] == manager['pid']
                assert len(manager_pfns) == manager['observed_vma_union_pages']
                assert len(all_union | manager_pfns) == manager['loader_manager_union_pages']
                assert manager['VmPTE_kb'] == status(group / 'manager/status.txt', 'VmPTE')
                report['manager_groups'].append({'loaders': count,
                    'manager_pfns': len(manager_pfns),
                    'manager_loader_intersection_pfns': len(manager_pfns & all_union),
                    'loader_manager_union_pfns': len(manager_pfns | all_union),
                    'manager_VmPTE_kb': manager['VmPTE_kb'], 'unread_ranges': omitted})
    assert len(seen_pids) == 63 and report['raw_loader_snapshots_checked'] == 189
    report.update(status='pass', loader_count=len(seen_pids),
        complete_PT_LOAD_coverage='all 63 loader target sets equal independently reconstructed ELF pages',
        sparse_bias='actual file-offset VMA minus page-rounded first PT_LOAD virtual address',
        categories='mapping counts, PFN unions and per-PFN distinct-process counts recomputed',
        limits=['read-only artifact check; no guest or target code execution',
                'read-only loader pages exclude BCH control objects and workload heaps',
                'conditional owner preloading does not prove original kernel demand',
                'VmPTE is a separate process metric; zero delta does not mean zero PTE cost',
                'PFN observations are sequential; no atomic whole-system memory claim'],
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
