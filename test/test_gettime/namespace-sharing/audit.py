#!/usr/bin/env python3
"""Recompute the resource and code evidence from archived observations."""
import importlib.util
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile

HERE = Path(__file__).resolve().parent
RESULTS = HERE / 'results'
OLD = HERE.parent / 'optimization-audit/results'


def reader(path):
    with path.open('rb') as f:
        elf = ELFFile(f)
        text = elf.get_section_by_name('.vkso.text').data()
        reloc = elf.get_section_by_name('.rela.vkso.text')
        symbols = elf.get_section(reloc['sh_link'])
        entries = [(r['r_offset'], r['r_info_type'], r['r_addend'],
                    symbols.get_symbol(r['r_info_sym']).name)
                   for r in reloc.iter_relocations()]
        return text, entries


def main():
    before = json.loads((OLD / 'memory/memory.json').read_text())['groups']
    report = json.loads((RESULTS / 'guest/sharing.json').read_text())
    assert len(before) == len(report['groups']) == 5
    memory = []
    for old, new in zip(before, report['groups']):
        for key in ('count', 'mode', 'carrier_loaded'):
            assert old[key] == new[key]
        old_pages = {r['mm']['pfn'] for r in old['records']}
        new_pages = {r['mm']['pfn'] for r in new['records']}
        assert len(old_pages) == old['count'] and len(new_pages) == 1
        assert len({r['mm']['bytes'] for r in new['records']}) == 1
        row = {key: new[key] for key in ('count', 'mode', 'carrier_loaded')}
        row.update(before_mm_pages=len(old_pages), after_mm_pages=len(new_pages),
                   saved_mm_bytes=4096 * (len(old_pages) - len(new_pages)))
        if new['carrier_loaded']:
            def union(group):
                return len({p for r in group['records']
                            for p in [r['mm']['pfn'], *[m['pfn'] for m in r['carrier']]]})
            row.update(before_carrier_and_mm_pages=union(old),
                       after_carrier_and_mm_pages=union(new))
            assert union(new) == 5 + new['count']
        memory.append(row)
    spec = importlib.util.spec_from_file_location('counter',
        HERE.parent / 'vkso-tests/code-size/count_manifest.py')
    counter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(counter)
    code = []
    for old in sorted((HERE / 'before').rglob('*')):
        if not old.is_file():
            continue
        relative = old.relative_to(HERE / 'before')
        new = RESULTS / 'source' / relative
        code.append(dict(path=str(relative),
            before=sum(counter.lexical_code_flags(old, old.read_text().splitlines())),
            after=sum(counter.lexical_code_flags(new, new.read_text().splitlines()))))
    readers = []
    for name in ('core', 'cycles'):
        old = reader(OLD / 'codegen/baseline' / (name + '.o'))
        new = reader(RESULTS / 'objects' / (name + '.o'))
        assert old == new
        readers.append(dict(object=name, bytes=len(new[0]), bytes_and_relocations_equal=True))
    for name, marker in [('abi', 'abi_matrix_status=pass'),
                         ('provider', 'event.clocksource_provider_fallback=pass'),
                         ('lifecycle', 'lifecycle.execution=pass'),
                         ('sharing', 'namespace_sharing_probe=pass'),
                         ('suspend', 'event.suspend_resume=pass')]:
        assert marker in (RESULTS / 'guest' / (name + '.log')).read_text()
    events = (RESULTS / 'guest/time-events.log').read_text()
    for event in ('settime', 'tai_update', 'ntp_frequency', 'leap_schedule', 'leap_transition'):
        assert f'event.{event}=pass' in events
    assert json.loads((RESULTS / 'guest/complete.json').read_text())['status'] == 'pass'
    output = dict(status='pass', memory=memory, source_sloc=code,
        source_sloc_delta=sum(r['after'] - r['before'] for r in code),
        reader_objects=readers, performance_claim='not measured')
    (RESULTS / 'audit.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
