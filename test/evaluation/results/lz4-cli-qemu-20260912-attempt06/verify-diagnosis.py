#!/usr/bin/env python3
"""Recompute the LZ4 failure diagnosis from archived raw records only."""
from pathlib import Path
import csv
import json
import re

ROOT = Path(__file__).resolve().parent
V = ROOT / 'evidence/validation'


def main():
    gdb = (V / 'full-cli-gdb-diagnostic.log').read_text()
    checker = re.sub(r'\x1b\[[0-9;]*m', '',
        (V / 'export/vkso/metadata/checks/vkso_LZ4_compress_default.log').read_text())
    resolved = list(csv.reader((V / 'export/vkso/metadata/resolved_symbol_addresses.txt').open()))
    kernel_target = int(next(row[1] for row in resolved if row[0] == 'memset'), 0)
    call = re.search(r'LZ4_compress_fast_extState \(\+0x28 \| 运行基址: (0x[0-9a-f]+)\) -> call memset', checker)
    assert call is not None and 'PASS' in checker
    kernel_call = int(call[1], 0)
    decoded = re.search(r'(0x[0-9a-f]+) <LZ4_compress_fast_extState\+40>:\s+call\s+(0x[0-9a-f]+)', gdb)
    assert decoded is not None
    user_call, decoded_target = (int(value, 0) for value in decoded.groups())
    displacement = kernel_target - kernel_call - 5
    predicted = user_call + 5 + displacement
    rip = int(re.search(r'^rip\s+(0x[0-9a-f]+)', gdb, re.M)[1], 0)
    ranges = [(int(a, 0), int(b, 0)) for a, b in re.findall(
        r'^\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+0x[0-9a-f]+\s+0x[0-9a-f]+\s+[-rwxps]{4}\s', gdb, re.M)]
    assert ranges and predicted == decoded_target == rip
    assert not any(start <= rip < end for start, end in ranges)
    rsi = int(re.search(r'^rsi\s+(0x[0-9a-f]+)', gdb, re.M)[1], 0)
    rdx = int(re.search(r'^rdx\s+(0x[0-9a-f]+)', gdb, re.M)[1], 0)
    assert (rsi, rdx) == (0, 16416)
    active = json.loads((V / 'registered-pfns.json').read_text())
    restored = json.loads((V / 'restored-pfns.json').read_text())
    assert active['status'] == restored['status'] == 'pass'
    assert len(active['pages']) == len(restored['pages']) == 4
    with (V / 'source-pages.csv').open() as stream:
        source = {int(row['kernel_vaddr'], 0): int(row['pfn']) for row in csv.DictReader(stream)}
    original = {row['file_offset']: row['kernel_pfn'] for row in active['pages']}
    assert len(original) == 4 and set(original.values()) == set(source.values())
    for row in active['pages']:
        entry = int(row['pagemap_entry'], 0)
        assert entry & (1 << 63)
        assert entry & ((1 << 55) - 1) == row['user_pfn'] == row['kernel_pfn']
        assert source[int(row['kernel_address'], 0)] == row['kernel_pfn']
        assert row['permissions'] == ('r-xp' if row['kind'] == 'text' else 'r--p')
    assert {row['file_offset'] for row in restored['pages']} == set(original)
    for row in restored['pages']:
        assert row['source_pfn'] == original[row['file_offset']]
        assert row['restored_user_pfn'] not in set(original.values())
    cli = json.loads((V / 'cli-validation.json').read_text())
    commands = [json.loads(line) for line in (V / 'commands.jsonl').read_text().splitlines()]
    crashes = [row for row in commands if row['returncode'] == -11]
    unloads = [row for row in commands if row['argv'][0] == 'rmmod']
    assert cli['status'] == 'fail' and cli['cases'] == [] and len(crashes) == 1
    assert crashes[0]['argv'][0] == '/work/cli/lz4-adapted'
    assert '-B4' in crashes[0]['argv'] and '/work/corpus/dickens' in crashes[0]['argv']
    assert [row['argv'][1] for row in unloads] == ['page_cache_replace', 'vkso_kernel_reader', 'vkso_lz4']
    assert all(row['returncode'] == 0 for row in unloads)
    status = json.loads((V / 'status.json').read_text())
    assert all(name not in status['modules_after'] for name in ('vkso_lz4', 'vkso_kernel_reader', 'page_cache_replace'))
    result = dict(status='pass', scope='archived failure evidence consistency; application remains failed',
        kernel_call=hex(kernel_call), kernel_target=hex(kernel_target), displacement=displacement,
        user_call=hex(user_call), predicted_target=hex(predicted), observed_rip=hex(rip),
        mapped_ranges_checked=len(ranges), target_mapped=False, rsi=rsi, rdx=rdx,
        separate_loader_pfn_matches=len(active['pages']),
        fresh_restored_mappings_outside_source_pfn_set=len(restored['pages']),
        completed_input_block_pairs=len(cli['cases']), module_unloads_verified=len(unloads))
    (ROOT / 'evidence-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
