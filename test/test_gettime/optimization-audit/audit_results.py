#!/usr/bin/env python3
"""Reconstruct this investigation's claims from the saved records and ELF files."""
import collections
import csv
import json
from pathlib import Path
import re
import statistics
import struct
import subprocess
from elftools.elf.elffile import ELFFile

ROOT = Path(__file__).resolve().parent / 'results'


def main():
    report = {'scope': 'Clocktime optimization investigation; no new full-system performance claim'}
    memory = json.loads((ROOT / 'memory/memory.json').read_text())
    groups = []
    for group in memory['groups']:
        records = group['records']
        assert len(records) == group['count']
        assert len({r['pid'] for r in records}) == len(records)
        assert len({r['namespace'] for r in records}) == 1
        payloads = {r['mm']['bytes'] for r in records}
        assert len(payloads) == 1
        payload = bytes.fromhex(next(iter(payloads)))
        assert len(payload) == 4096 and struct.unpack_from('<I', payload)[0] == 3
        assert payload[40:] == bytes(4096 - 40)
        mm = {r['mm']['pfn'] for r in records}
        assert len(mm) == len(records)
        item = dict(mode=group['mode'], processes=len(records), namespace=records[0]['namespace'],
                    mm_pages=len(mm), mm_bytes=len(mm)*4096,
                    projected_mm_pages_with_namespace_sharing=1,
                    projected_mm_saving_bytes=(len(mm)-1)*4096)
        if group['carrier_loaded']:
            by = collections.defaultdict(set)
            for record in records:
                assert record['thread_mm_pfns'] == [record['mm']['pfn']] * 4
                assert len(record['carrier']) == 5
                for page in record['carrier']:
                    by[page['offset']].add(page['pfn'])
            assert set(by) == {4096, 8192, 12288, 16384, 20480}
            assert all(len(by[key]) == 1 for key in [4096, 8192, 12288, 16384])
            assert len(by[20480]) == len(records)
            union = set().union(*by.values())
            assert not mm & union
            item.update(carrier_pages=len(union), mm_and_carrier_pages=len(mm | union))
        groups.append(item)
    assert len(groups) == 5
    report['memory'] = groups
    function_sizes = []
    for directory in sorted((ROOT / 'codegen').iterdir()):
        if not directory.is_dir():
            continue
        section_bytes, symbols = [], {}
        for name in ['core.o', 'cycles.o']:
            with (directory/name).open('rb') as stream:
                elf = ELFFile(stream)
                section_bytes.append(int(elf.get_section_by_name('.vkso.text')['sh_size']))
                for symbol in elf.get_section_by_name('.symtab').iter_symbols():
                    if symbol['st_info']['type'] == 'STT_FUNC':
                        symbols[symbol.name] = int(symbol['st_size'])
        function_sizes.append(dict(variant=directory.name, core_section_bytes=section_bytes[0],
            cycles_section_bytes=section_bytes[1], combined_section_bytes=sum(section_bytes), function_bytes=symbols))
    report['codegen'] = function_sizes
    old = json.loads((ROOT/'readers/summary.json').read_text())
    methods = ['baseline','entry-null','coarse-late-offset']
    grouped, identities = collections.defaultdict(list), set()
    count = 0
    for process in range(9):
        for method in methods:
            identities.add((ROOT/f'readers/{process:02}-{method}.log').read_text().strip())
            rows = list(csv.DictReader((ROOT/f'readers/{process:02}-{method}.csv').open()))
            assert len(rows) == 217
            assert len({(r['round'],r['scenario']) for r in rows}) == 217
            for row in rows:
                assert row['cpu_start'] == row['cpu_end'] == '2'
                assert int(row['iterations']) == 500000 and int(row['tsc_ticks']) > 0
                grouped[method,process,row['scenario']].append(int(row['tsc_ticks']) / int(row['iterations']))
                count += 1
    assert len(identities) == 1 and next(iter(identities)).startswith('checks=60002 ')
    medians = {key:statistics.median(value) for key,value in grouped.items()}
    for row in old['summary']:
        scenario, method = row['scenario'], row['method']
        values = [medians[method,p,scenario] for p in range(9)]
        ratios = [medians[method,p,scenario]/medians['baseline',p,scenario] for p in range(9)]
        assert row['median_ticks'] == statistics.median(values)
        assert row['median_paired_ratio'] == statistics.median(ratios)
        assert row['minimum_paired_ratio'] == min(ratios)
        assert row['maximum_paired_ratio'] == max(ratios)
    report['diagnostic_rows'] = count
    report['reader_diagnostic'] = old['summary']
    for method in methods:
        abi = (ROOT/f'functional/{method}-abi.log').read_text()
        assert 'abi_matrix_status=pass' in abi
        assert 'namespace.setns.commit=pass' in abi
        assert 'namespace.exec.lifecycle=pass' in abi
        assert 'event.clocksource_provider_fallback=pass' in (ROOT/f'functional/{method}-provider.log').read_text()
        assert 'lifecycle.execution=pass' in (ROOT/f'functional/{method}-lifecycle.log').read_text()
    for name in ['memory-guest.log','functional-guest.log']:
        content=(ROOT/name).read_text()
        assert 'revision_guest_status=0' in content
        assert not re.search(r'Kernel panic|BUG:|WARNING:',content)
    report['functional_methods'] = methods
    report['status'] = 'pass'
    (ROOT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='pass', memory_groups=len(groups),
        codegen_variants=len(function_sizes), diagnostic_rows=count,
        functional_methods=methods),indent=2))


if __name__ == '__main__':
    main()
