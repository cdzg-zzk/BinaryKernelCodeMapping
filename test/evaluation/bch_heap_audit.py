#!/usr/bin/env python3
"""Independently replay BCH live-allocation and raw page observations.

All byte counts describe live requested allocations or malloc usable extents;
physical-page sets describe interval coverage, not exclusive allocation ownership.
"""
import argparse
from collections import Counter, defaultdict
import csv
import ctypes
import itertools
import json
from pathlib import Path
import re
import struct

PAGE = 4096
MASK = (1 << 55) - 1
ROLES = ('native-before-owner', 'native-owner-loaded', 'registered-carrier')
PHASES = ('before', 'loaded', 'faulted', 'initialized', 't4-active', 't4-released',
          't8-active', 't8-released', 'controls-released')
MAP_KEYS = ('start', 'end', 'permissions', 'file_offset', 'device', 'inode', 'path')
MAP_LINE = re.compile(r'^[0-9a-f]+-[0-9a-f]+ [rwxps-]{4} ')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise ValueError(f'{path}: cannot read JSON: {error}') from error


def number(value):
    require(not isinstance(value, bool), f'boolean instead of integer: {value!r}')
    if isinstance(value, int):
        return value
    require(isinstance(value, str), f'invalid integer: {value!r}')
    return int(value, 16 if value.lower().startswith('0x') else 10)


def map_rows(text):
    result = []
    for line in text.splitlines():
        require(MAP_LINE.match(line), f'malformed maps line: {line!r}')
        fields = line.split(maxsplit=5)
        start, end = (int(word, 16) for word in fields[0].split('-'))
        require(start < end and start % PAGE == end % PAGE == 0, 'unaligned/empty VMA')
        require(not result or result[-1]['end'] <= start, 'overlapping/unsorted VMAs')
        result.append(dict(zip(MAP_KEYS, (start, end, fields[1], int(fields[2], 16),
            fields[3], int(fields[4]), fields[5] if len(fields) == 6 else ''))))
    return result


def covering_pages(address, size):
    require(address > 0 and size > 0 and address + size <= (1 << 64),
            'invalid allocation/segment interval')
    return range(address // PAGE * PAGE, (address + size + PAGE - 1) // PAGE * PAGE, PAGE)


def region_at(maps, address):
    region = next((row for row in maps if row['start'] <= address < row['end']), None)
    require(region is not None, f'address {address:#x} outside recorded VMAs')
    return region


def raw_snapshot(directory, pid, identity):
    record = read_json(directory / 'record.json')
    require(record['pid'] == pid, f'{directory}: PID differs')
    for key in ('boot_id', 'kernel'):
        require(record[key] == identity[key], f'{directory}: {key} differs')
    require(record['snapshot_atomic'] is False and record['finished_unix'] >= record['observed_unix'],
            f'{directory}: invalid snapshot interval/atomicity')
    maps = map_rows((directory / 'maps.txt').read_text())
    smaps = '\n'.join(line for line in (directory / 'smaps.txt').read_text().splitlines() if MAP_LINE.match(line))
    require(map_rows(smaps) == maps, f'{directory}: maps/smaps VMA census differs')
    status = dict(line.split(':', 1) for line in (directory / 'status.txt').read_text().splitlines() if ':' in line)
    require(int(status['Pid']) == pid and int(status['Tgid']) == pid,
            f'{directory}: status PID/Tgid differs')
    ranges = record['pagemap_ranges']
    require(len(ranges) == len(maps), f'{directory}: incomplete pagemap range index')
    raw = (directory / 'pagemap.bin').read_bytes()
    entries, missing = {}, []
    offset = 0
    for region, item in zip(maps, ranges):
        require({key: item[key] for key in MAP_KEYS} == region,
                f'{directory}: pagemap range does not match maps')
        requested = (region['end'] - region['start']) // PAGE
        size = item['bytes_read']
        require(item['requested_entries'] == requested and item['binary_offset'] == offset,
                f'{directory}: invalid pagemap range index/offset')
        require(isinstance(size, int) and 0 <= size <= requested * 8 and size % 8 == 0,
                f'{directory}: invalid pagemap byte count')
        require(offset + size <= len(raw), f'{directory}: truncated pagemap binary')
        for index, (entry,) in enumerate(struct.iter_unpack('<Q', raw[offset:offset + size])):
            address = region['start'] + PAGE * index
            require(not (entry & (1 << 63)) or (entry & MASK),
                    f'{directory}: present page has hidden/zero PFN at {address:#x}')
            entries[address] = entry
        if size != requested * 8:
            require(item.get('error') or item.get('short_read'),
                    f'{directory}: unexplained incomplete pagemap range')
            missing.append(dict(start=region['start'] + size // 8 * PAGE,
                                end=region['end'], path=region['path'],
                                error=item.get('error'), short_read=item.get('short_read', False)))
        offset += size
    require(offset == len(raw), f'{directory}: unindexed pagemap bytes')
    seen = set()
    for target in record['target_pages']:
        address = target['address']
        require(address % PAGE == 0 and address not in seen, f'{directory}: duplicate/unaligned target')
        seen.add(address)
        require(address in entries, f'{directory}: explicit target absent from raw pagemap')
        entry = entries[address]
        require(number(target['pagemap_entry']) == entry, f'{directory}: direct/raw pagemap entry differs')
        for key, expected in {'present': bool(entry & (1 << 63)), 'pfn': entry & MASK,
                'file_or_shared_anon': bool(entry & (1 << 61)), 'exclusive_bit': bool(entry & (1 << 56))}.items():
            require(target[key] == expected, f'{directory}: inconsistent target {key}')
        require(target['permissions'] == region_at(maps, address)['permissions'],
                f'{directory}: target VMA permissions differ')
    whole = {entry & MASK for entry in entries.values() if entry & (1 << 63)}
    return record, maps, entries, whole, missing, status


def layout_targets(layouts, maps, plan):
    """Rebuild every PT_LOAD page, including BSS, shared segment edges and shim."""
    output = {}
    for layout in layouts:
        bias, role, path = layout['load_bias'], layout['role'], layout['path']
        require(bias % PAGE == 0, 'unaligned ELF load bias')
        first = min(layout['segments'], key=lambda row: row['p_vaddr'])
        bases = [row for row in maps if row['path'] == path and
                 row['file_offset'] == first['p_offset'] // PAGE * PAGE]
        require(len(bases) == 1 and bases[0]['start'] - first['p_vaddr'] // PAGE * PAGE == bias,
                f'{path}: recorded ELF load bias differs from maps')
        pages = {}
        for segment in layout['segments']:
            require(0 <= segment['p_filesz'] <= segment['p_memsz'], 'invalid ELF segment sizes')
            if not segment['p_memsz']:
                continue
            begin = bias + segment['p_vaddr']
            for address in covering_pages(begin, segment['p_memsz']):
                valid = max(address, begin)
                region = region_at(maps, valid)
                require('r' in region['permissions'], f'{path}: unreadable PT_LOAD page')
                offset = (segment['p_offset'] + valid - begin) // PAGE * PAGE
                file_backed = valid - begin < segment['p_filesz']
                if file_backed:
                    require(region['path'] == path and
                            offset == region['file_offset'] + address - region['start'],
                            f'{path}: PT_LOAD file mapping differs')
                sections = [section['name'] for section in layout['sections']
                    if section['address'] < address + PAGE - bias and
                    section['address'] + section['size'] > address - bias]
                declared = plan.get(offset) if role == 'carrier' and file_backed else None
                item = pages.setdefault(address, dict(address=address, fault_address=valid,
                    library=path, role=role, file_offset=offset if file_backed else None,
                    file_backed_segment=file_backed, permissions=region['permissions'],
                    vma=region, sections=[], segment_flags=[], declared=declared))
                item['sections'] = sorted(set(item['sections'] + sections))
                item['segment_flags'] = sorted(set(item['segment_flags'] + [segment['p_flags']]))
        require(not set(output).intersection(pages), 'different libraries overlap virtual pages')
        output.update(pages)
    return output


class BCHControlABI(ctypes.Structure):
    # vendor/linux-5.15/include/linux/bch.h, SysV x86_64 layout.
    _fields_ = [(name, ctypes.c_uint32) for name in ('m', 'n', 't', 'ecc_bits', 'ecc_bytes')] + \
               [(name, ctypes.c_uint64) for name in ('a_pow_tab', 'a_log_tab', 'mod8_tab',
                'ecc_buf', 'ecc_buf2', 'xi_tab', 'syn', 'cache', 'elp')] + \
               [('poly_2t', ctypes.c_uint64 * 4), ('swap_bits', ctypes.c_bool)]


def control_sizes(t):
    """Fourteen persistent bch_init allocations; generator temporaries excluded."""
    m, n, word_bytes = 13, (1 << 13) - 1, 4
    words = (m * t + 31) // 32
    result = {'bch_control': ctypes.sizeof(BCHControlABI), 'a_pow_tab': (n + 1) * 2,
        'a_log_tab': (n + 1) * 2, 'mod8_tab': words * 1024 * word_bytes,
        'ecc_buf': words * word_bytes, 'ecc_buf2': words * word_bytes,
        'xi_tab': m * word_bytes, 'syn': 2 * t * word_bytes,
        'cache': 2 * t * word_bytes, 'elp': (t + 1) * 12}
    result.update({f'poly_2t[{index}]': 4 + (2 * t + 1) * word_bytes for index in range(4)})
    require(ctypes.sizeof(BCHControlABI) == 136, 'auditor host does not have expected x86_64 ABI')
    return result


def heap_targets(allocations, maps, extent='requested_bytes'):
    pages = {}
    for allocation in allocations:
        for address in covering_pages(allocation['address'], allocation[extent]):
            region = region_at(maps, address)
            require('r' in region['permissions'] and 'w' in region['permissions'],
                    'live allocation does not lie in readable writable VMA')
            item = pages.setdefault(address, dict(address=address, role='heap',
                permissions=region['permissions'], vma=region, allocations=[]))
            item['allocations'].append({key: allocation[key] for key in ('case_index', 't', 'category', 'name')})
    return pages


def page_sets(targets, entries, pid, owner):
    categories = defaultdict(set)
    missing, nonpresent = [], []
    mapping_counts = Counter()
    for address, target in targets.items():
        if target['role'] == 'heap':
            labels = {'live_heap'} | {f'heap_{item["category"]}' for item in target['allocations']}
            labels |= {f'heap_t{item["t"]}_{item["category"]}' for item in target['allocations']}
        else:
            role = target['role']
            labels = {'library' if role in ('native', 'carrier') else role}
            permission = 'writable' if 'w' in target['permissions'] else 'executable' if 'x' in target['permissions'] else 'readonly'
            labels.add(role + '_' + permission)
            if target['declared']:
                labels.add('declared_' + target['declared']['kind'])
        for label in labels:
            mapping_counts[label] += 1
        if address not in entries:
            missing.append(dict(pid=pid, address=address, categories=sorted(labels)))
        elif not entries[address] & (1 << 63):
            nonpresent.append(dict(pid=pid, address=address, categories=sorted(labels), entry=hex(entries[address])))
        else:
            for label in labels:
                categories[label].add(entries[address] & MASK)
    categories['whole_owner'] = set(owner)
    return categories, mapping_counts, missing, nonpresent


def set_summary(categories, mapping_counts, process_sets):
    keys = ('library', 'shim', 'heap_control', 'heap_workload', 'live_heap', 'whole_owner', 'observer')
    for key in keys:
        categories.setdefault(key, set())
    selected = set().union(*(categories[key] for key in ('library', 'shim', 'live_heap', 'whole_owner')))
    overlaps = {a + '__' + b: sorted(categories[a] & categories[b]) for a, b in itertools.combinations(keys, 2)}
    return {'categories': {key: {'pfns': sorted(values), 'pages': len(values),
                'mapping_count': mapping_counts.get(key, 0),
                'distinct_loader_count_by_pfn': ({str(pfn): sum(pfn in sets.get(key, set()) for sets in process_sets)
                                                 for pfn in sorted(values)} if key != 'whole_owner' else None)}
                           for key, values in sorted(categories.items())},
            'overlap_pfns': overlaps, 'selected_union_pfns': sorted(selected),
            'selected_union_pages': len(selected),
            'selected_plus_observer_union_pages': len(selected | categories['observer']),
            'observer_overlap_selected_pfns': sorted(selected & categories['observer'])}


def kernel_reader_records(directory):
    by_address = {}
    files = sorted(directory.glob('pages-*.csv'))
    for path in files:
        requested = [int(word, 16) for word in path.with_name(path.name.replace('pages-', 'addresses-')).with_suffix('.txt').read_text().split()]
        with path.open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            address, pfn = int(row['kernel_vaddr'], 0), int(row['pfn'])
            require(address in requested and address not in by_address and pfn > 0,
                    f'{directory}: duplicate/unrequested/invalid kernel PFN')
            by_address[address] = pfn
    return by_address


def owner_pages(directory, identity):
    system = read_json(directory / 'system.json')
    require(system['identity']['boot_id'] == identity['boot_id'], 'owner snapshot boot differs')
    module = system['modules'].get('vkso_bch')
    if module is None:
        return set(), []
    base, size = module['core_base'], module['core_bytes']
    expected = list(covering_pages(base, size))
    require(base % PAGE == 0 and module['requested_addresses'] == expected, 'owner core interval differs')
    require(int(module['attributes']['initsize']) == 0 and module['attributes']['initstate'] == 'live',
            'owner snapshot is not a live core allocation')
    raw = kernel_reader_records(directory / 'vkso_bch')
    observed = {row['address']: row['pfn'] for row in module['observed_pages']}
    require(len(observed) == len(module['observed_pages']) and observed == raw,
            'owner metadata differs from raw kernel-reader PFNs')
    require(set(raw).issubset(expected), 'owner PFN outside core interval')
    missing = sorted(set(expected) - set(raw))
    require(module['missing_addresses'] == missing, 'owner missing page metadata differs')
    return set(raw.values()), missing


def error_positions(seed, t):
    state, positions = seed, []
    mask = (1 << 64) - 1
    while len(positions) < t:
        state ^= state >> 12
        state ^= (state << 25) & mask
        state ^= state >> 27
        bit = ((state * 2685821657736338717) & mask) % (4096 + 13 * t)
        bit = (bit & ~7) | (7 - (bit & 7))
        if bit < 4096 + 13 * t and bit not in positions:
            positions.append(bit)
    return positions


def verify_probe(state, phase, role, library, maps, previous):
    require(state['schema_version'] == 1 and state['report_ok'] is True and state['last_errno'] == 0,
            'probe did not report a valid successful observation')
    stages = dict(loaded='loaded', faulted='loaded', initialized='initialized',
        **{'t4-active': 'active', 't4-released': 'deactivated', 't8-active': 'active',
           't8-released': 'deactivated', 'controls-released': 'released'})
    require(state['stage'] == stages[phase], f'{phase}: incorrect probe lifecycle stage')
    carrier = role == 'registered-carrier'
    require(state['backend'] == ('kernel-vkso' if carrier else 'kernel-native') and
            state['dso_path'] == library and state['allocator_verified'] is True,
            f'{phase}: backend/allocator identity differs')
    abi = state['abi']
    expected_abi = dict(pointer_bytes=8, unsigned_int_bytes=4, bch_control_bytes=136,
                        gf_poly_bytes=4, gf_poly_deg1_bytes=12,
                        offsets={name: getattr(BCHControlABI, name).offset for name, _ in BCHControlABI._fields_})
    require(abi == expected_abi, 'probe control ABI differs from original header')
    require(set(state['source_identity']) == {'bench_sha256', 'adapted_sha256', 'header_sha256', 'shim_sha256'} and
            all(re.fullmatch('[0-9a-f]{64}', value) for value in state['source_identity'].values()),
            'probe build source identities are missing')
    require(set(state['api_addresses']) == {'init', 'free', 'encode', 'decode'}, 'incomplete BCH API identity')
    require(state['api_symbols'] == {name: ('vkso_' if carrier else '') + 'bch_' + name
            for name in ('init', 'free', 'encode', 'decode')}, 'API symbol names differ from role')
    for name, address in state['api_addresses'].items():
        region = region_at(maps, address)
        require(region['path'] == library and 'x' in region['permissions'], f'{name}: API does not belong to target DSO text')
    allocator = state['allocator']
    libc_paths = set()
    for name in ('malloc', 'calloc', 'free', 'malloc_usable_size'):
        region = region_at(maps, allocator[name])
        require('x' in region['permissions'] and Path(region['path']).name in ('libc.so.6', 'libc-2.35.so'),
                f'{name}: allocator is not the recorded libc executable mapping')
        libc_paths.add(region['path'])
    require(len(libc_paths) == 1, 'allocator functions belong to different libc objects')
    if carrier:
        require(allocator['native_import_targets'] == [0, 0, 0], 'carrier claims native DSO imports')
        require(len(allocator['shim_import_targets']) == 3 and
                allocator['shim_import_targets'][0] == allocator['malloc'] and
                allocator['shim_import_targets'][2] == allocator['free'] and
                allocator['shim_import_targets'][1] in (0, allocator['calloc']),
                'actual shim malloc/free import targets differ from libc')
        require(len(allocator['carrier_helper_targets']) == len(allocator['carrier_slot_addresses']) == 2,
                'incomplete carrier allocator dependency binding')
        for target, slot in zip(allocator['carrier_helper_targets'], allocator['carrier_slot_addresses']):
            region = region_at(maps, target)
            require(Path(region['path']).name == 'libshim.so' and 'x' in region['permissions'],
                    'carrier allocator helper is not shim text')
            region = region_at(maps, slot)
            require(region['path'] == library and 'w' in region['permissions'] and slot % 8 == 0,
                    'carrier allocator slot is not private target data')
    else:
        require(allocator['native_import_targets'] == [allocator[key] for key in ('malloc', 'calloc', 'free')],
                'native allocator imports differ from libc identities')
        require(allocator['carrier_helper_targets'] == allocator['carrier_slot_addresses'] == [0, 0],
                'native role contains carrier bindings')
        require(allocator['shim_import_targets'] == [0, 0, 0], 'native role contains shim imports')

    active = 0 if phase == 't4-active' else 1 if phase == 't8-active' else -1
    require(state['active_case'] == active, 'wrong active workload case')
    initialized = PHASES.index(phase) >= PHASES.index('initialized')
    live_controls = initialized and phase != 'controls-released'
    expected_checks = [int(PHASES.index(phase) >= PHASES.index('t4-active')),
                       int(PHASES.index(phase) >= PHASES.index('t8-active'))]
    require(state['geometry_checks'] == (2 if initialized else 0) and
            state['verification_checks'] == sum(expected_checks), 'probe functional counters differ from phase')
    require(len(state['cases']) == 2, 'probe case matrix incomplete')
    for case_index, (case, t) in enumerate(zip(state['cases'], (4, 8))):
        expected = dict(case_index=case_index, m=13, t=t, len=512,
            ecc_bits=13 * t if initialized else 0, ecc_bytes=(13 * t + 7) // 8 if initialized else 0,
            codeword_seed=0xb4c00000 + case_index, verification_checks=expected_checks[case_index])
        require(case == expected, f'{phase}: t{t} geometry, codeword seed or verification differs')
    if active == -1:
        require(state['active_vector'] is None, 'inactive phase has a live decode vector')
    else:
        t = (4, 8)[active]
        seed = 0x63c5a17e9b ^ (active << 48) ^ t
        vector = state['active_vector']
        require(vector['mode'] == 'decode-full' and vector['trial'] == 0 and vector['errors'] == t and
                vector['seed'] == seed and vector['positions'] == error_positions(seed, t),
                'active workload differs from original full-decode vector')
        returned = vector['verified_returned_positions']
        require(len(returned) == t and len(set(returned)) == t and set(returned) == set(vector['positions']),
                'active decode returned wrong/duplicate error locations')
    expected_allocations = {}
    if live_controls:
        for index, t in enumerate((4, 8)):
            expected_allocations.update({(index, 'control', name): size for name, size in control_sizes(t).items()})
            expected_allocations[(index, 'workload', 'codeword')] = 512 + (13 * t + 7) // 8
    if active != -1:
        t, ecc = (4, 8)[active], (13 * (4, 8)[active] + 7) // 8
        expected_allocations.update({(active, 'workload', name): size for name, size in
                                     {'work': 512 + ecc, 'difference': ecc, 'errloc': 4 * t}.items()})
    observed = {}
    totals = defaultdict(lambda: {'allocation_count': 0, 'requested_bytes': 0, 'usable_bytes': 0})
    intervals = []
    for allocation in state['allocations']:
        key = (allocation['case_index'], allocation['category'], allocation['name'])
        require(key not in observed and key in expected_allocations, f'unknown/duplicate live allocation {key}')
        require(allocation['t'] == (4, 8)[key[0]] and allocation['requested_bytes'] == expected_allocations[key],
                f'{key}: requested size differs from source allocation formula')
        require(isinstance(allocation['usable_bytes'], int) and allocation['usable_bytes'] >= allocation['requested_bytes'],
                f'{key}: usable size smaller than requested allocation')
        require(isinstance(allocation['address'], int) and allocation['address'] > 0, 'invalid live allocation address')
        observed[key] = allocation
        intervals.append((allocation['address'], allocation['address'] + allocation['usable_bytes']))
        for label in ('all', allocation['category'], f't{allocation["t"]}_{allocation["category"]}'):
            totals[label]['allocation_count'] += 1
            for field in ('requested_bytes', 'usable_bytes'):
                totals[label][field] += allocation[field]
        if previous and key in previous:
            require(previous[key] == allocation, f'{key}: persistent live allocation moved/changed without release')
    require(set(observed) == set(expected_allocations), 'missing live allocations for phase')
    intervals.sort()
    require(all(end <= next_begin for (_, end), (next_begin, _) in zip(intervals, intervals[1:])),
            'distinct live malloc allocations overlap usable byte extents')
    for field, value in {'live_allocation_count': len(observed),
                        'live_requested_bytes': totals['all']['requested_bytes'],
                        'live_usable_bytes': totals['all']['usable_bytes']}.items():
        require(state[field] == value, f'{field}: probe summary differs from allocation rows')
    return observed, dict(totals)


def functional_session(directory, identity):
    validation = directory.parent
    session = read_json(validation / 'status.json')
    result = read_json(validation / 'bch-validation.json')
    require(session['status'] == result['status'] == 'pass' and session['restoration_verified'] is True,
            'full functional session or normal restoration failed')
    require(session['boot_id'] == identity['boot_id'] and session['kernel'] == identity['kernel'],
            'functional session and heap observations are from different boots')
    require(not session.get('cleanup_errors') and not session.get('restore_verification_error'),
            'functional session cleanup failed')
    require(not {'vkso_bch', 'vkso_kernel_reader', 'page_cache_replace'}.intersection(
        line.split()[0] for line in session['modules_after'].splitlines()), 'test modules remain loaded')
    coverage = result['coverage']
    require(result['correctness_vectors'] == 128 and coverage['data_length_bytes'] == 512 and
        coverage['parameters'] == [{'m': 13, 't': 4, 'errors': list(range(5))},
                                   {'m': 13, 't': 8, 'errors': list(range(9))}] and
        coverage['backends'] == ['kernel-vkso', 'kernel-native', 'author-standalone'] and
        coverage['decode_modes'] == ['decode-precomputed', 'decode-full'] and
        coverage['decode_checks_from_unchanged_loop'] == 10752, 'full functional coverage differs')
    log = (validation / 'bch-correctness.log').read_text()
    for t in (4, 8):
        require(log.count(f'correctness: m=13 t={t} vectors=128 backends=3 ok') == 1,
                'full benchmark log has missing/duplicated correctness terminal')
    require(log.count('BCH evaluation completed;') == 1, 'full benchmark did not complete once')
    restored = read_json(validation / 'restored-pfns.json')
    require(restored['status'] == 'pass' and restored['pages'] and
            all(row['source_backing_removed'] is True and row['source_pfn'] > 0 and
                row['restored_user_pfn'] > 0 and row['restored_user_pfn'] != row['source_pfn']
                for row in restored['pages']), 'fresh-map restoration evidence failed')
    require(len({row['file_offset'] for row in restored['pages']}) == len(restored['pages']),
            'duplicate fresh-map restoration pages')
    return {'status': 'pass', 'decode_checks_from_unchanged_loop': 10752,
            'basis': 'original complete benchmark and same-session logs; individual decoder records are not emitted by this benchmark',
            'restoration_scope': 'fresh carrier mappings after normal release'}


def audit(directory: Path) -> dict:
    directory = Path(directory)
    result = read_json(directory / 'result.json')
    require(result['status'] == 'pass' and result['functional_status'] == 0 and result['loader_count'] == 63,
            'heap session did not complete all roles/loaders')
    identity = result['identity']
    require(identity['kernel'] == '5.15.0-119-generic', 'unexpected experiment kernel')
    functional = functional_session(directory, identity)
    summaries, snapshots, source_identity = [], 0, None
    for role in ROLES:
        role_directory = directory / role
        role_record = read_json(role_directory / 'role.json')
        require(role_record['role'] == role and role_record['status'] == 'pass' and
                not role_record.get('loader_exit_failures'), f'{role}: role/loader failure')
        require(role_record['identity']['boot_id'] == identity['boot_id'] and
                role_record['identity']['kernel'] == identity['kernel'], f'{role}: identity differs')
        require([group['count'] for group in role_record['groups']] == [1, 4, 16],
                f'{role}: incomplete/duplicated loader-count matrix')
        owner, owner_missing = owner_pages(role_directory / 'initial-system', identity)
        require(set(role_record['owner_core_pfns']) == owner, 'role owner PFNs differ from raw module observations')
        module_names = {line.split()[0] for line in
                        (role_directory / 'initial-system' / 'modules.txt').read_text().splitlines()}
        require(('vkso_bch' in module_names) == (role != 'native-before-owner'),
                'owner preload lifecycle differs from role')
        require(bool(owner) == (role != 'native-before-owner'), 'owner PFNs missing/unexpected for role')
        plan = {}
        for offset, address, kind, section in role_record['plan']:
            require(offset not in plan and offset % PAGE == address % PAGE == 0, 'duplicate/unaligned declared page')
            plan[offset] = dict(kernel_address=address, kind=kind, section=section)
        source = {number(key): value for key, value in role_record['source_pfns'].items()}
        require(bool(plan) == (role == 'registered-carrier'), 'unexpected/missing carrier declaration plan')
        require(set(source) == {row['kernel_address'] for row in plan.values()}, 'source PFN coverage differs from plan')
        if plan:
            require(source == kernel_reader_records(role_directory / 'declared-source'),
                    'declared source metadata differs from kernel-reader records')
            require(set(source.values()).issubset(owner), 'declared BCH pages are outside observed owner core')
        for group_record in role_record['groups']:
            count, pids = group_record['count'], group_record['pids']
            require(group_record['status'] == 'pass' and group_record['phases'] == list(PHASES) and
                    len(pids) == len(set(pids)) == count, 'incomplete/duplicate PID/phase group')
            group = role_directory / f'n{count:02}'
            require({int(path.name) for path in group.iterdir() if path.is_dir() and path.name.isdigit()} == set(pids),
                    'PID directories differ from declared concurrent group')
            previous = {pid: {} for pid in pids}
            fixed = {}
            layouts_by_pid = {}
            for pid in pids:
                folder = group / str(pid)
                require({path.name for path in folder.iterdir() if path.is_dir()} == set(PHASES),
                        f'{folder}: missing/extra phase snapshots')
                loaded = read_json(folder / 'loaded' / 'probe.json')
                require(loaded['pid'] == pid and loaded['phase'] == 'loaded', 'loaded identity differs')
                layouts = loaded['layouts']
                expected_roles = ['carrier', 'observer', 'shim'] if plan else ['native', 'observer']
                require([layout['role'] for layout in layouts] == expected_roles, 'loaded DSO role/layout matrix differs')
                require(layouts[0]['path'] == role_record['library'] and
                        Path(layouts[1]['path']).name == 'libbch_heap_probe.so', 'loaded library/observer path differs')
                layouts_by_pid[pid] = layouts
            previous_phase_end = None
            for phase in PHASES:
                categories = defaultdict(set)
                mapping_counts = Counter()
                process_sets = []
                missing_targets, nonpresent_targets, missing_ranges = [], [], []
                totals = defaultdict(lambda: {'allocation_count': 0, 'requested_bytes': 0, 'usable_bytes': 0})
                process_rows, whole_union, usable_union = [], set(), set()
                phase_begin, phase_end = [], []
                for pid in pids:
                    folder = group / str(pid) / phase
                    probe = read_json(folder / 'probe.json')
                    require(probe['pid'] == pid and probe['phase'] == phase, f'{folder}: probe PID/phase differs')
                    record, maps, entries, whole, omitted, status = raw_snapshot(folder, pid, identity)
                    snapshots += 1
                    phase_begin.append(record['observed_unix'])
                    phase_end.append(record['finished_unix'])
                    whole_union.update(whole)
                    missing_ranges.extend(dict(pid=pid, **item) for item in omitted)
                    layouts = layouts_by_pid[pid]
                    if phase == 'before':
                        require(set(probe) == {'phase', 'pid'} and not record['target_pages'],
                                'before stage unexpectedly has target observations')
                        targets = layout_targets([layout for layout in layouts if layout['role'] == 'observer'], maps, {})
                        allocations, pid_totals = [], {}
                    else:
                        state = probe['probe']
                        observed, pid_totals = verify_probe(state, phase, role, role_record['library'], maps, previous[pid])
                        previous[pid] = observed
                        allocations = state['allocations']
                        immutable = {key: state[key] for key in ('api_addresses', 'api_symbols', 'allocator', 'abi', 'source_identity')}
                        require(fixed.setdefault(pid, immutable) == immutable, 'loaded API/allocator/source identity changed between phases')
                        if source_identity is None:
                            source_identity = state['source_identity']
                        require(state['source_identity'] == source_identity, 'probe source build differs across loaders')
                        targets = layout_targets(layouts, maps, plan)
                        heap = heap_targets(allocations, maps)
                        require(not set(targets).intersection(heap), 'live allocation aliases DSO virtual page')
                        targets.update(heap)
                        supplied = {item['address']: item for item in probe['targets']}
                        require(len(supplied) == len(probe['targets']) and supplied == targets,
                                f'{folder}: probe targets do not cover exact PT_LOAD/allocation intervals')
                        raw_targets = {item['address']: {key: value for key, value in item.items()
                            if key not in ('pagemap_entry', 'present', 'pfn', 'file_or_shared_anon', 'exclusive_bit')}
                            for item in record['target_pages']}
                        require(raw_targets == targets, f'{folder}: snapshot target metadata differs from probe/reconstruction')
                        if phase != 'loaded':
                            declared = [item for item in targets.values() if item.get('declared')]
                            require(len(declared) == len(plan), 'declared PT_LOAD mapping coverage incomplete')
                            for item in declared:
                                entry = entries[item['address']]
                                require(entry & (1 << 63) and 'w' not in item['permissions'] and
                                    entry & MASK == source[item['declared']['kernel_address']],
                                    f'{folder}: faulted declared page does not share source PFN')
                    usable_targets = heap_targets(allocations, maps, 'usable_bytes')
                    usable_missing = [address for address in usable_targets if address not in entries]
                    require(not usable_missing, f'{folder}: usable allocation covering page missing from raw pagemap')
                    usable_pfns = {entries[address] & MASK for address in usable_targets if entries[address] & (1 << 63)}
                    usable_union.update(usable_pfns)
                    sets, counts, missing, nonpresent = page_sets(targets, entries, pid, owner)
                    process_sets.append(sets)
                    for key, values in sets.items():
                        categories[key].update(values)
                    mapping_counts.update(counts)
                    missing_targets.extend(missing)
                    nonpresent_targets.extend(nonpresent)
                    for key, values in pid_totals.items():
                        for field, value in values.items():
                            totals[key][field] += value
                    process_rows.append(dict(pid=pid, allocations=pid_totals,
                        whole_process_observed_pfn_pages=len(whole),
                        usable_heap_covering_pfn_pages=len(usable_pfns),
                        status_kb={key: int(status[key].split()[0]) for key in
                            ('VmRSS', 'VmHWM', 'VmPTE', 'RssAnon', 'RssFile', 'RssShmem') if key in status}))
                require(previous_phase_end is None or min(phase_begin) >= previous_phase_end,
                        'snapshot phases overlap; concurrent-stage census not established')
                previous_phase_end = max(phase_end)
                summary = set_summary(categories, mapping_counts, process_sets)
                summary.update(role=role, loaders=count, phase=phase, pids=pids,
                    allocations=dict(totals), per_process=process_rows,
                    missing_target_pages=missing_targets, nonpresent_target_pages=nonpresent_targets,
                    whole_process_missing_pagemap_ranges=missing_ranges,
                    whole_process_observed_pfn_union_pages=len(whole_union),
                    usable_heap_covering_pfn_union_pages=len(usable_union),
                    usable_heap_covering_pfns=sorted(usable_union),
                    owner_missing_core_addresses=owner_missing,
                    observer_before_derived_from_loaded_layout=phase == 'before')
                summaries.append(summary)
    require(snapshots == 567 and len(summaries) == 81, 'incomplete total snapshot matrix')
    return {'status': 'pass', 'identity': identity, 'snapshots_replayed': snapshots,
        'role_loader_phase_groups': len(summaries), 'source_identity': source_identity,
        'functional_session': functional,
        'source_allocation_formulas': {f'm13_t{t}': {'requested_bytes': sum(control_sizes(t).values()),
            'allocation_sizes': control_sizes(t)} for t in (4, 8)},
        'scope': 'library+shim+live requested heap+whole owner physical-page union; observer separately reported',
        'limitations': [
            'malloc usable bytes and requested bytes are distinct; neither includes all allocator metadata or freed temporaries',
            'covering PFNs can contain other allocations; overlaps are reported and no exclusivity is inferred',
            'whole-process sets include Python/C observer and allocator retention; no post-free PFN change is attributed to BCH alone',
            'nonpresent pages contribute no PFN; unreadable whole-process ranges remain explicitly missing',
            'raw pagemap and direct targets are sequential reads; every recorded explicit target must agree',
            'loaded ELF layouts and allocator relocation checks are recorded by the observer; pagemap does not contain object bytes',
            'guest page observations are not physical-machine performance samples'],
        'groups': summaries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='archived validation/bch_heap directory')
    parser.add_argument('--output', type=Path, help='write complete replay report to this new report file')
    args = parser.parse_args()
    report = audit(args.directory)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({key: report[key] for key in ('status', 'snapshots_replayed', 'role_loader_phase_groups')}))
    else:
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
