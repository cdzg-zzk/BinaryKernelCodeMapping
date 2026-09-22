#!/usr/bin/env python3
"""Shared ELF/source checks and compatibility entry for the current section 6.3 audit."""
import argparse
import json
from pathlib import Path
import sys
from elftools.elf.elffile import ELFFile
ROOT = Path(__file__).resolve().parents[2]

def entry_pages(directory):
    metadata = directory / 'work/vkso/metadata'
    outputs = dict(line.split('=', 1) for line in (metadata / 'outputs.env').read_text().splitlines())
    mapping = {}
    for line in (metadata / 'page_mappings.txt').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        offset, kernel, kind, section = line.split(',')
        mapping[int(offset, 0)] = (int(kernel, 0), kind)
    exports = []
    with Path(outputs['library']).open('rb') as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name('.dynsym')
        for line in (metadata / 'resolved_symbol_addresses.txt').read_text().splitlines():
            name, address, size, provider, role = line.split(',')
            if role != 'export':
                continue
            matches = symbols.get_symbol_by_name(name)
            assert matches and len(matches) == 1
            symbol = matches[0]
            assert symbol['st_info']['type'] == 'STT_FUNC'
            value, length = symbol['st_value'], symbol['st_size']
            assert length > 0
            # ELF virtual address -> file offset -> declared owner page.
            for pos in range(value, value + length):
                load = [s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD'
                        and s['p_vaddr'] <= pos < s['p_vaddr'] + s['p_filesz']]
                assert len(load) == 1 and load[0]['p_flags'] & 1
                offset = pos - load[0]['p_vaddr'] + load[0]['p_offset']
                page, kind = mapping[offset & ~4095]
                assert kind == 'text' and page + (offset & 4095) == int(address, 0) + pos - value
            exports.append(name)
    assert exports
    return exports


def function_source(path, declaration):
    text = path.read_text()
    start = text.index(declaration)
    return text[start:text.index('\n}', start) + 2]



def audit(base, paper=False):
    sys.path.insert(0, str(ROOT / 'test/section63/scripts'))
    from analyze import analyze
    result = analyze(base.resolve())
    if paper:
        section = (base / 'paper-material/section63.md').read_text().strip()
        assert section in (ROOT / 'paper/paper_content/Paper Draft.md').read_text()
        result['paper_section_match'] = True
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--paper', action='store_true')
    args = p.parse_args()
    print(json.dumps(audit(args.directory, args.paper), indent=2))
