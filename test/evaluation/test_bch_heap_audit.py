#!/usr/bin/env python3
"""Synthetic raw-record fixtures only; these are not BCH experiment results."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('bch_heap_audit', Path(__file__).with_name('bch_heap_audit.py'))
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
IDENTITY = dict(boot_id='synthetic-boot', kernel='5.15.0-119-generic')
PRESENT = 1 << 63


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def layout(path, role, bias):
    return dict(path=path, role=role, load_bias=bias,
        segments=[dict(p_vaddr=4096, p_offset=0, p_filesz=4096, p_memsz=4096, p_flags=5),
                  dict(p_vaddr=8192, p_offset=4096, p_filesz=4096, p_memsz=4096, p_flags=6)],
        sections=[dict(name='.text', address=4096, size=4096, flags=6, type='SHT_PROGBITS'),
                  dict(name='.data', address=8192, size=4096, flags=3, type='SHT_PROGBITS')])


def maps_for(layouts):
    rows = []
    for obj in layouts:
        for segment in obj['segments']:
            rows.append(dict(start=obj['load_bias'] + segment['p_vaddr'],
                end=obj['load_bias'] + segment['p_vaddr'] + segment['p_memsz'],
                permissions='r-xp' if segment['p_flags'] == 5 else 'rw-p',
                file_offset=segment['p_offset'], device='00:01', inode=1, path=obj['path']))
    rows.extend([dict(start=0x80000, end=0x81000, permissions='r-xp', file_offset=0,
                      device='00:01', inode=2, path='/lib/libc.so.6'),
                 dict(start=0x100000, end=0x140000, permissions='rw-p', file_offset=0,
                      device='00:00', inode=0, path='[heap]')])
    return sorted(rows, key=lambda row: row['start'])


def probe_state(phase, carrier=False):
    initialized = A.PHASES.index(phase) >= 3
    active = 0 if phase == 't4-active' else 1 if phase == 't8-active' else -1
    stages = ['loaded', 'loaded', 'initialized', 'active', 'deactivated', 'active', 'deactivated', 'released']
    allocations, address = [], 0x100010
    for case, t in enumerate((4, 8)):
        sizes = [('control', name, size) for name, size in A.control_sizes(t).items()]
        sizes += [('workload', 'codeword', 512 + (13 * t + 7) // 8)]
        if initialized and phase != 'controls-released':
            for category, name, size in sizes:
                usable = (size + 15) // 16 * 16
                allocations.append(dict(case_index=case, t=t, category=category, name=name,
                                        address=address, requested_bytes=size, usable_bytes=usable))
                address += usable + 16
    if active != -1:
        t, ecc = (4, 8)[active], (13 * (4, 8)[active] + 7) // 8
        for name, size in [('work', 512 + ecc), ('difference', ecc), ('errloc', 4 * t)]:
            allocations.append(dict(case_index=active, t=t, category='workload', name=name,
                address=address, requested_bytes=size, usable_bytes=(size + 15) // 16 * 16))
            address += (size + 15) // 16 * 16 + 16
    checks = [int(A.PHASES.index(phase) >= 4), int(A.PHASES.index(phase) >= 6)]
    allocator = dict(malloc=0x80010, calloc=0x80020, free=0x80030, malloc_usable_size=0x80040,
        native_import_targets=[0, 0, 0] if carrier else [0x80010, 0x80020, 0x80030],
        shim_import_targets=[0x80010, 0, 0x80030] if carrier else [0, 0, 0],
        carrier_helper_targets=[0x51010, 0x51020] if carrier else [0, 0],
        carrier_slot_addresses=[0x12000, 0x12008] if carrier else [0, 0])
    state = dict(schema_version=1, stage=stages[A.PHASES.index(phase) - 1], report_ok=True,
        last_errno=0, backend='kernel-vkso' if carrier else 'kernel-native',
        dso_path='/work/libkernel.so' if carrier else '/work/libnative.so',
        allocator_verified=True, active_case=active, allocator=allocator,
        api_addresses={name: 0x11010 + i * 16 for i, name in enumerate(('init', 'free', 'encode', 'decode'))},
        api_symbols={name: ('vkso_' if carrier else '') + 'bch_' + name for name in ('init', 'free', 'encode', 'decode')},
        source_identity={key + '_sha256': 'a' * 64 for key in ('bench', 'adapted', 'header', 'shim')},
        abi=dict(pointer_bytes=8, unsigned_int_bytes=4, bch_control_bytes=136, gf_poly_bytes=4,
            gf_poly_deg1_bytes=12, offsets={name: getattr(A.BCHControlABI, name).offset for name, _ in A.BCHControlABI._fields_}),
        geometry_checks=2 if initialized else 0, verification_checks=sum(checks),
        cases=[dict(case_index=c, m=13, t=t, len=512, ecc_bits=13*t if initialized else 0,
                    ecc_bytes=(13*t+7)//8 if initialized else 0,
                    codeword_seed=0xb4c00000+c, verification_checks=checks[c]) for c, t in enumerate((4, 8))],
        active_vector=None, allocations=allocations, live_allocation_count=len(allocations),
        live_requested_bytes=sum(row['requested_bytes'] for row in allocations),
        live_usable_bytes=sum(row['usable_bytes'] for row in allocations))
    if active != -1:
        t = (4, 8)[active]
        seed = 0x63c5a17e9b ^ (active << 48) ^ t
        positions = A.error_positions(seed, t)
        state['active_vector'] = dict(mode='decode-full', trial=0, errors=t, seed=seed,
            positions=positions, verified_returned_positions=list(reversed(positions)))
    return state


def snapshot(folder, pid, phase, layouts, carrier):
    phase_index = A.PHASES.index(phase)
    maps = maps_for(layouts if phase != 'before' else [layouts[1]])
    plan = {0: dict(kernel_address=0x100000000, kind='text', section='.text')} if carrier else {}
    probe = dict(pid=pid, phase=phase)
    targets = {}
    if phase != 'before':
        state = probe_state(phase, carrier)
        targets = A.layout_targets(layouts, maps, plan)
        targets.update(A.heap_targets(state['allocations'], maps))
        probe.update(probe=state, targets=list(targets.values()))
        if phase == 'loaded':
            probe['layouts'] = layouts
    folder.mkdir(parents=True)
    map_text = ''.join(f'{r["start"]:x}-{r["end"]:x} {r["permissions"]} {r["file_offset"]:08x} {r["device"]} {r["inode"]} {r["path"]}\n' for r in maps)
    (folder / 'maps.txt').write_text(map_text)
    (folder / 'smaps.txt').write_text(map_text)
    (folder / 'status.txt').write_text(f'Pid:\t{pid}\nTgid:\t{pid}\nVmRSS:\t123 kB\nVmPTE:\t8 kB\n')
    raw, ranges, entries = bytearray(), [], {}
    for region in maps:
        item = dict(region, binary_offset=len(raw), requested_entries=(region['end']-region['start'])//4096)
        for address in range(region['start'], region['end'], 4096):
            pfn = 100 if address == 0x11000 and carrier else (address // 4096 if address < 0x100000 else pid * 100 + address // 4096)
            entry = PRESENT | pfn
            # Natural heap nonresidency is valid, including in active phases.
            if address == 0x105000:
                entry = 0
            entries[address] = entry
            raw.extend(struct.pack('<Q', entry))
        item['bytes_read'] = item['requested_entries'] * 8
        ranges.append(item)
    (folder / 'pagemap.bin').write_bytes(raw)
    direct = [dict(target, pagemap_entry=hex(entries[address]), present=bool(entries[address] & PRESENT),
                   pfn=entries[address] & A.MASK, file_or_shared_anon=False, exclusive_bit=False)
              for address, target in targets.items()]
    record = dict(pid=pid, **IDENTITY, observed_unix=phase_index*10, finished_unix=phase_index*10+1,
                  snapshot_atomic=False, pagemap_ranges=ranges, target_pages=direct)
    dump(folder / 'record.json', record)
    dump(folder / 'probe.json', probe)


def kernel_record(directory):
    directory.mkdir(parents=True)
    (directory / 'pages-000.csv').write_text('kernel_vaddr,pfn\n0x100000000,100\n')
    (directory / 'addresses-000.txt').write_text('0x100000000\n')


def full_fixture(directory):
    dump(directory / 'result.json', dict(status='pass', functional_status=0, loader_count=63, identity=IDENTITY))
    validation = directory.parent
    dump(validation / 'status.json', dict(status='pass', restoration_verified=True, modules_after='', **IDENTITY))
    dump(validation / 'bch-validation.json', dict(status='pass', correctness_vectors=128,
        coverage=dict(data_length_bytes=512, parameters=[dict(m=13,t=4,errors=list(range(5))),dict(m=13,t=8,errors=list(range(9)))],
            backends=['kernel-vkso','kernel-native','author-standalone'], decode_modes=['decode-precomputed','decode-full'],
            decode_checks_from_unchanged_loop=10752)))
    (validation / 'bch-correctness.log').write_text('correctness: m=13 t=4 vectors=128 backends=3 ok\ncorrectness: m=13 t=8 vectors=128 backends=3 ok\nBCH evaluation completed;\n')
    dump(validation / 'restored-pfns.json', dict(status='pass', pages=[dict(source_backing_removed=True,
        file_offset=0, source_pfn=100, restored_user_pfn=200)]))
    pid = 1000
    for role in A.ROLES:
        carrier = role == 'registered-carrier'
        library = '/work/libkernel.so' if carrier else '/work/libnative.so'
        layouts = [layout(library, 'carrier' if carrier else 'native', 0x10000),
                   layout('/work/libbch_heap_probe.so', 'observer', 0x30000)]
        if carrier:
            layouts.append(layout('/work/libshim.so', 'shim', 0x50000))
        initial = directory / role / 'initial-system'
        owner = role != 'native-before-owner'
        module = dict(core_base=0x100000000, core_bytes=4096, requested_addresses=[0x100000000],
            attributes=dict(initsize='0', initstate='live'), observed_pages=[dict(address=0x100000000, pfn=100)], missing_addresses=[])
        dump(initial / 'system.json', dict(identity=IDENTITY, modules={'vkso_bch': module} if owner else {}))
        (initial / 'modules.txt').write_text('vkso_bch 4096 0 - Live 0x100000000\n' if owner else '')
        if owner:
            kernel_record(initial / 'vkso_bch')
        if carrier:
            kernel_record(directory / role / 'declared-source')
        groups = []
        for count in (1, 4, 16):
            pids = list(range(pid, pid + count))
            pid += count
            groups.append(dict(count=count, pids=pids, phases=list(A.PHASES), status='pass'))
            for loader in pids:
                for phase in A.PHASES:
                    snapshot(directory / role / f'n{count:02}' / str(loader) / phase, loader, phase, layouts, carrier)
        dump(directory / role / 'role.json', dict(role=role, status='pass', identity=IDENTITY, library=library,
            groups=groups, owner_core_pfns=[100] if owner else [], source_pfns={str(0x100000000):100} if carrier else {},
            plan=[[0, 0x100000000, 'text', '.text']] if carrier else []))


class HeapAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bch-heap-audit-synthetic-')
        self.folder = Path(self.tmp.name)
        self.layouts = [layout('/work/libnative.so', 'native', 0x10000), layout('/work/libbch_heap_probe.so', 'observer', 0x30000)]
        self.maps = maps_for(self.layouts)

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_matrix_replays_and_retains_nonpresent_heap_pages(self):
        directory = self.folder / 'validation' / 'bch_heap'
        full_fixture(directory)
        report = A.audit(directory)
        self.assertEqual(report['snapshots_replayed'], 567)
        self.assertEqual(len(report['groups']), 81)
        group = next(row for row in report['groups'] if row['phase']=='initialized' and row['loaders']==1)
        self.assertEqual(group['allocations']['control']['requested_bytes'], 91344)
        self.assertTrue(group['nonpresent_target_pages'])
        role_path = directory / 'native-before-owner' / 'role.json'
        role = json.loads(role_path.read_text())
        role['groups'][0]['phases'].remove('t8-released')
        dump(role_path, role)
        with self.assertRaisesRegex(ValueError, 'PID/phase group'):
            A.audit(directory)

    def test_formula_totals_are_requested_bytes(self):
        self.assertEqual(sum(A.control_sizes(4).values()), 41448)
        self.assertEqual(sum(A.control_sizes(8).values()), 49896)
        state = probe_state('initialized')
        _, totals = A.verify_probe(state, 'initialized', 'native-before-owner', '/work/libnative.so', self.maps, {})
        self.assertEqual(totals['all']['requested_bytes'], 92388)
        self.assertGreater(totals['all']['usable_bytes'], totals['all']['requested_bytes'])

    def test_missing_or_duplicate_allocation_rejected_despite_adjusted_counts(self):
        for duplicate in (False, True):
            state = probe_state('initialized')
            state['allocations'].pop()
            if duplicate:
                state['allocations'].append(copy.deepcopy(state['allocations'][0]))
            state['live_allocation_count'] = len(state['allocations'])
            state['live_requested_bytes'] = sum(row['requested_bytes'] for row in state['allocations'])
            with self.assertRaisesRegex(ValueError, 'missing live|duplicate live'):
                A.verify_probe(state, 'initialized', 'native-before-owner', '/work/libnative.so', self.maps, {})

    def test_wrong_size_usable_overlap_or_stage_rejected(self):
        for change, message in [('size','source allocation formula'),('overlap','overlap'),('stage','lifecycle stage')]:
            state = probe_state('initialized')
            if change == 'size': state['allocations'][0]['requested_bytes'] += 1
            if change == 'overlap': state['allocations'][1]['address'] = state['allocations'][0]['address']
            if change == 'stage': state['stage'] = 'released'
            with self.assertRaisesRegex(ValueError, message):
                A.verify_probe(state, 'initialized', 'native-before-owner', '/work/libnative.so', self.maps, {})

    def test_persistent_allocation_cannot_move_without_release(self):
        initial = probe_state('initialized')
        previous, _ = A.verify_probe(initial, 'initialized', 'native-before-owner', '/work/libnative.so', self.maps, {})
        state = probe_state('t4-active')
        state['allocations'][0]['address'] += 1
        with self.assertRaisesRegex(ValueError, 'persistent live allocation'):
            A.verify_probe(state, 't4-active', 'native-before-owner', '/work/libnative.so', self.maps, previous)

    def test_wrong_active_return_locations_and_allocator_binding_rejected(self):
        for corruption in ('locations', 'allocator'):
            state = probe_state('t4-active')
            if corruption == 'locations': state['active_vector']['verified_returned_positions'] = [1]*4
            else: state['allocator']['native_import_targets'][0] = 0x80020
            with self.assertRaisesRegex(ValueError, 'returned wrong|allocator imports differ'):
                A.verify_probe(state, 't4-active', 'native-before-owner', '/work/libnative.so', self.maps, {})

    def test_raw_direct_pagemap_disagreement_and_truncation_rejected(self):
        directory = self.folder / 'snapshot'
        snapshot(directory, 123, 'initialized', self.layouts, False)
        A.raw_snapshot(directory, 123, IDENTITY)
        path = directory / 'record.json'
        record = json.loads(path.read_text())
        record['target_pages'][0]['pagemap_entry'] = hex(PRESENT | 999)
        dump(path, record)
        with self.assertRaisesRegex(ValueError, 'direct/raw pagemap entry differs'):
            A.raw_snapshot(directory, 123, IDENTITY)
        raw = directory / 'pagemap.bin'
        raw.write_bytes(raw.read_bytes()[:-8])
        with self.assertRaisesRegex(ValueError, 'truncated pagemap binary'):
            A.raw_snapshot(directory, 123, IDENTITY)

    def test_wrong_pid_range_index_or_elf_bias_rejected(self):
        directory = self.folder / 'snapshot'
        snapshot(directory, 123, 'loaded', self.layouts, False)
        with self.assertRaisesRegex(ValueError, 'PID differs'):
            A.raw_snapshot(directory, 124, IDENTITY)
        path = directory / 'record.json'
        record = json.loads(path.read_text())
        record['pagemap_ranges'][0]['binary_offset'] = 8
        dump(path, record)
        with self.assertRaisesRegex(ValueError, 'range index/offset'):
            A.raw_snapshot(directory, 123, IDENTITY)
        layouts = copy.deepcopy(self.layouts)
        layouts[0]['load_bias'] += 4096
        with self.assertRaisesRegex(ValueError, 'load bias differs'):
            A.layout_targets(layouts, self.maps, {})

    def test_pfn_overlaps_deduplicate_and_observer_is_separate(self):
        sets = {'library': {1,2}, 'shim': {2,3}, 'live_heap': {3,4}, 'heap_control':{3},
                'heap_workload':{4}, 'whole_owner': {1,5}, 'observer': {4,6}}
        report = A.set_summary(sets, {}, [sets, sets])
        self.assertEqual(report['selected_union_pfns'], [1,2,3,4,5])
        self.assertEqual(report['selected_plus_observer_union_pages'], 6)
        self.assertEqual(report['observer_overlap_selected_pfns'], [4])
        self.assertEqual(report['overlap_pfns']['library__whole_owner'], [1])


if __name__ == '__main__':
    unittest.main()
