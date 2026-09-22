#!/usr/bin/env python3
"""Replay typed API observations against independent XXH32 and sorting oracles.

The input is the launcher's extracted evidence/validation directory. Missing
user records are reported as unvalidated, never promoted from checker PASS.
No benchmark timing or Linux-wide applicability percentage is computed.
"""
import argparse
import csv
import ctypes
import ctypes.util
import itertools
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile

LENGTHS = (0, 1, 2, 3, 4, 5, 7, 8, 15, 16, 17, 18, 19, 20, 31, 32, 33, 4095, 4096, 4097)
SEEDS = (0, 1, 0xffffffff, 0x9e3779b1)
KATS = (b'', b'a', b'abc', b'message digest', b'abcdefghijklmnopqrstuvwxyz',
        b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', b'1234567890' * 8)
PATTERNS = ('ascending', 'descending', 'duplicates', 'permuted')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text())


def random_words(state):
    while True:
        state ^= (state << 13) & 0xffffffff
        state ^= state >> 17
        state ^= (state << 5) & 0xffffffff
        yield state


def hash_vectors():
    for data in KATS:
        yield 'known-answer', len(data), 0, 0, data
    for length, alignment, seed in itertools.product(LENGTHS, (0, 1, 3), SEEDS):
        rng = random_words(0x5eeda17e ^ seed ^ length)
        yield 'boundary', length, alignment, seed, bytes(next(rng) & 255 for _ in range(length))


def sort_vectors():
    for num, width, alignment, pattern, direction, mode in itertools.product(
            (0, 1, 2, 3, 17, 64), (1, 3, 4, 8, 12, 16), (0, 1), PATTERNS, (1, -1), ('default', 'custom')):
        values = [num - 1 - i if pattern == 'descending' else i % 4 if pattern == 'duplicates' else i
                  for i in range(num)]
        elements = [bytes([v] + [(v * 37 + j * 13) & 255 for j in range(1, width)]) for v in values]
        if pattern == 'permuted':
            rng = random_words(0x5eeda17e ^ num ^ (width << 16))
            for i in range(num, 1, -1):
                chosen = next(rng) % i
                elements[i - 1], elements[chosen] = elements[chosen], elements[i - 1]
        yield (num, width, alignment, pattern, direction, mode,
               b''.join(elements), b''.join(sorted(elements, reverse=direction < 0)))


def load_rows(path, count):
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == count, f'{path}: incomplete matrix: {len(rows)} != {count}')
    require([r['case_id'] for r in rows] == list(map(str, range(count))), f'{path}: duplicate/missing/reordered IDs')
    return rows


def check_status(status, roots, backend):
    for key, expected in dict(schema_version=1, backend=backend, status='pass', errno=0, roots=roots,
                              xxh32_checks=247 if roots & 1 else 0, xxh32_kats=7 if roots & 1 else 0,
                              sort_checks=1152 if roots & 2 else 0, failed_case=-1,
                              callback_swap_size_bytes=4, pointer_bytes=8, size_t_bytes=8,
                              workload_buffers_released=True, measurement=False).items():
        require(status.get(key) == expected, f'status {key}: {status.get(key)!r} != {expected!r}')


def check_hash(path, oracle):
    rows = load_rows(path, 247)
    for i, (row, vector) in enumerate(zip(rows, hash_vectors())):
        kind, length, alignment, seed, data = vector
        expected = oracle(data, length, seed)
        for field, value in dict(vector_kind=kind, length=length, alignment=alignment, seed=seed,
                                 input_hex=data.hex(), expected=expected, actual=expected,
                                 input_unchanged=1, guards_ok=1, **{'pass': 1}).items():
            require(row[field] == str(value), f'{path} case {i}: {field} differs')
    return rows


def check_sort(path, status):
    rows = load_rows(path, 1152)
    comparisons = swaps = 0
    for i, (row, vector) in enumerate(zip(rows, sort_vectors())):
        num, width, alignment, pattern, direction, mode, data, expected = vector
        for field, value in dict(num=num, width=width, alignment=alignment, pattern=pattern,
                                 direction=direction, swap_mode=mode, input_hex=data.hex(),
                                 expected_hex=expected.hex(), actual_hex=expected.hex(), guards_ok=1,
                                 sorted_ok=1, permutation_ok=1, exact_match=1,
                                 callback_arguments_ok=1, **{'pass': 1}).items():
            require(row[field] == str(value), f'{path} case {i}: {field} differs')
        cmp_count, swap_count = int(row['cmp_calls']), int(row['swap_calls'])
        require(cmp_count >= 0 and swap_count >= 0, f'{path}: negative callback count')
        require(int(row['cmp_address']) == status['callback_addresses']['comparator'] != 0,
                f'{path}: comparator binding differs')
        require(int(row['swap_address']) == (status['callback_addresses']['swap'] if mode == 'custom' else 0),
                f'{path}: swap binding differs')
        require(not (num < 2 and (cmp_count or swap_count)), f'{path}: empty/singleton invokes callback')
        require(not (mode == 'default' and swap_count), f'{path}: default mode invokes custom swap')
        require(num < 2 or cmp_count > 0, f'{path}: no comparator calls')
        comparisons += cmp_count
        swaps += swap_count
    require((comparisons, swaps) == (status['cmp_calls'], status['swap_calls']), 'callback totals disagree')
    require(swaps > 0, 'custom swap never invoked')
    return rows


def audit(directory):
    libname = ctypes.util.find_library('xxhash')
    require(libname is not None, 'independent installed libxxhash is required')
    library = ctypes.CDLL(libname)
    library.XXH32.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32)
    library.XXH32.restype = ctypes.c_uint32
    library.XXH_versionNumber.restype = ctypes.c_uint
    guest = read_json(directory / 'status.json')
    require(guest['kernel'] == '5.15.0-119-generic' and guest['boot_id'], 'wrong/missing guest identity')
    kernel = read_json(directory / 'kernel/status')
    check_status(kernel, 3, 'kernel-public-imports')
    kernel_hash = check_hash(directory / 'kernel/xxh32.csv', library.XXH32)
    kernel_sort = check_sort(directory / 'kernel/sort.csv', kernel)
    symbols = {}
    for line in (directory / 'kallsyms.txt').read_text().splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] in ('xxh32', 'sort'):
            symbols[fields[2]] = int(fields[0], 16)
    require(symbols == kernel['api_addresses'], 'kernel import addresses differ from built-in symbols')
    report = dict(status='pass', scope='functional evidence replay; no performance conclusion',
                  kernel=guest['kernel'], boot_id=guest['boot_id'], xxhash_oracle=libname,
                  xxhash_version=library.XXH_versionNumber(), kernel_checks=1399, cases=[])
    for name, roots, originals in (('xxh32', 1, kernel_hash), ('sort', 2, kernel_sort)):
        case = read_json(directory / name / 'case.json')
        item = dict(root=name, carrier=case['carrier'], command_exit_code=case.get('command_exit_code'),
                    functional_status='unvalidated', reason=case.get('error', case.get('runtime')))
        report['cases'].append(item)
        status_path = directory / name / 'user/status.json'
        if not status_path.exists():
            report['status'] = 'partial'
            continue
        status = read_json(status_path)
        check_status(status, roots, 'registered-user-api')
        observed = (check_hash(directory / name / 'user/xxh32.csv', library.XXH32) if roots == 1
                    else check_sort(directory / name / 'user/sort.csv', status))
        # Address spaces differ; the deterministic target's other observations must agree.
        for original, row in zip(originals, observed):
            require({k: v for k, v in row.items() if k not in ('cmp_address', 'swap_address')} ==
                    {k: v for k, v in original.items() if k not in ('cmp_address', 'swap_address')},
                    f'{name}: kernel/user raw observations differ')
        active = read_json(directory / name / 'registered-pfns.json')
        restored = read_json(directory / name / 'restored-pfns.json')
        require(active['status'] == restored['status'] == 'pass' and active['pages'], 'missing PFN evidence')
        require(status[name + '_path'] == status[name + '_dladdr_path'] == active['library'], 'wrong API DSO')
        require(status['api_addresses'][name] > status[name + '_dladdr_fbase'] > 0, 'invalid API address')
        with (directory / name / 'export/vkso/lib/libkernel.so').open('rb') as stream:
            elf = ELFFile(stream)
            symbol = elf.get_section_by_name('.dynsym').get_symbol_by_name(name)
            require(symbol is not None and len(symbol) == 1, 'missing/ambiguous actual ELF export')
            value = symbol[0]['st_value']
            first_vaddr = min(s['p_vaddr'] // 4096 * 4096 for s in elf.iter_segments()
                              if s['p_type'] == 'PT_LOAD')
            require(status['api_addresses'][name] == status[name + '_dladdr_fbase'] + value - first_vaddr,
                    'API address differs from the actual carrier ELF symbol')
            segments = [s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD'
                        and s['p_vaddr'] <= value < s['p_vaddr'] + s['p_filesz'] and s['p_flags'] & 1]
            require(len(segments) == 1, 'API does not belong to a unique executable segment')
            segment = segments[0]
            root_offset = segment['p_offset'] + value - segment['p_vaddr']
            executable_offsets = {offset for s in elf.iter_segments()
                                  if s['p_type'] == 'PT_LOAD' and s['p_flags'] & 1
                                  for offset in range(s['p_offset'] // 4096 * 4096,
                                      (s['p_offset'] + s['p_filesz'] + 4095) // 4096 * 4096, 4096)}
            synthetic_offsets = set()
            resolved = (directory / name / 'export/vkso/metadata/resolved_symbol_addresses.txt').read_text()
            thunk_encodings = {'__x86_indirect_thunk_rbx': b'\xff\xe3',
                               '__x86_indirect_thunk_rcx': b'\xff\xe1',
                               '__x86_indirect_thunk_array': b'\xff\xe0',
                               '__x86_indirect_thunk_r12': b'\x41\xff\xe4',
                               '__x86_return_thunk': b'\xc3'}
            for line in resolved.splitlines():
                fields = line.split(',')
                if fields[-1] != 'synthetic':
                    continue
                require(fields[3] == 'builtin_thunk' and fields[0] in thunk_encodings, 'unknown synthetic dependency')
                entry = elf.get_section_by_name('.symtab').get_symbol_by_name(fields[0])[0]
                section = elf.get_section(entry['st_shndx'])
                within = entry['st_value'] - section['sh_addr']
                code = thunk_encodings[fields[0]]
                require(section.data()[within:within + len(code)] == code, 'synthetic thunk bytes differ')
                synthetic_offsets.add((section['sh_offset'] + within) // 4096 * 4096)
        root_pages = [p for p in active['pages'] if p['file_offset'] <= root_offset < p['file_offset'] + 4096]
        require(len(root_pages) == 1 and int(root_pages[0]['kernel_address'], 0) +
                root_offset - root_pages[0]['file_offset'] == symbols[name],
                'exported API does not map to the actual built-in root')
        plan = {}
        for line in (directory / name / 'export/vkso/metadata/page_mappings.txt').read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#'):
                fields = line.split(',')
                plan[int(fields[0], 0)] = int(fields[1], 0)
        require(plan == {p['file_offset']: int(p['kernel_address'], 0) for p in active['pages']},
                'declared/observed page coverage differs')
        require(not synthetic_offsets.intersection(plan) and executable_offsets == set(plan) | synthetic_offsets,
                'executable page backing classification differs')
        sources = {int(r['kernel_vaddr'], 0): int(r['pfn']) for r in
                   csv.DictReader((directory / name / 'source-pages.csv').read_text().splitlines())}
        offsets = set()
        for page in active['pages']:
            entry = int(page['pagemap_entry'], 0)
            pfn = entry & ((1 << 55) - 1)
            require(entry & (1 << 63) and pfn != 0 and
                    pfn == page['user_pfn'] == page['kernel_pfn'] == sources[int(page['kernel_address'], 0)],
                    'source/user/raw PFN mismatch')
            require('w' not in page['permissions'], 'writable shared source page')
            require(page['file_offset'] not in offsets, 'duplicate registered offset')
            offsets.add(page['file_offset'])
        require({p['file_offset'] for p in restored['pages']} == offsets, 'restoration coverage differs')
        require(len(restored['pages']) == len(offsets), 'duplicate restored offset')
        active_pfns = {p['file_offset']: p['kernel_pfn'] for p in active['pages']}
        require(all(p['source_pfn'] == active_pfns[p['file_offset']] for p in restored['pages']),
                'restoration source differs from registered source')
        require(all(p['source_backing_removed'] and p['restored_user_pfn'] != p['source_pfn']
                    for p in restored['pages']), 'fresh mappings retain source backing')
        require(case['status'] == 'pass' and case['command_exit_code'] == 0, 'failed actual export command')
        item.update(functional_status='pass', checks=len(observed), shared_pages=len(offsets),
                    generated_thunk_pages=len(synthetic_offsets),
                    callback_calls=dict(comparator=status['cmp_calls'], swap=status['swap_calls']),
                    fresh_mapping_restoration='pass', reason=None)
    remaining = {line.split()[0] for line in guest['modules_after'].splitlines()}
    require(not guest.get('cleanup_errors') and not remaining.intersection(
        ('applicability_runtime', 'page_cache_replace', 'vkso_kernel_reader')), 'experiment modules remain loaded')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.directory), indent=2))
