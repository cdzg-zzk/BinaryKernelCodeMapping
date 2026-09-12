#!/usr/bin/env python3
"""Read eight selected caller bodies from exact119 ELF; no checker execution.

Only the instruction windows around the specified direct control transfers and
printable constants referenced by those windows are emitted. The output is
static image evidence, not a live-kernel or dynamic-reachability observation.
"""
import argparse
import hashlib
import json
from pathlib import Path

from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP
from elftools.elf.elffile import ELFFile


PAIRS = [
    ('hex_dump_to_buffer', 'snprintf'),
    ('snprintf', 'vsnprintf'),
    ('vsnprintf', 'format_decode'),
    ('format_decode', '__warn_printk'),
    ('__warn_printk', 'vprintk'),
    ('__schedule', 'panic'),
    ('swap_do_scheduled_discard', 'blkdev_issue_discard'),
    ('bio_associate_blkg_from_css', 'blkg_create'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, default=Path('/usr/lib/debug/boot/vmlinux-5.15.0-119-generic'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    wanted = {name for pair in PAIRS for name in pair}
    with args.elf.open('rb') as stream:
        elf = ELFFile(stream)
        sections = list(elf.iter_sections())
        symtab = elf.get_section_by_name('.symtab')
        symbols = {symbol.name: symbol for symbol in symtab.iter_symbols()
                   if symbol.name in wanted and symbol['st_info']['type'] == 'STT_FUNC'}
        assert set(symbols) == wanted
        build_ids = [note['n_desc'] for section in sections if section['sh_type'] == 'SHT_NOTE'
                     for note in section.iter_notes()
                     if note['n_type'] == 'NT_GNU_BUILD_ID' and note['n_name'] == 'GNU']

        def read_virtual(address, length):
            for section in sections:
                start = section['sh_addr']
                if section['sh_flags'] & 2 and start <= address < start + section['sh_size']:
                    if section['sh_type'] == 'SHT_NOBITS':
                        return None
                    stream.seek(section['sh_offset'] + address - start)
                    return section.name, stream.read(min(length, start + section['sh_size'] - address))
            return None

        disassembler = Cs(CS_ARCH_X86, CS_MODE_64)
        disassembler.detail = True
        rows = []
        for source, target in PAIRS:
            symbol = symbols[source]
            base = symbol['st_value']
            section_name, code = read_virtual(base, symbol['st_size'])
            instructions = list(disassembler.disasm(code, base))
            locations = [i for i, insn in enumerate(instructions)
                         if insn.mnemonic in ('call', 'jmp') and insn.operands
                         and insn.operands[0].type == X86_OP_IMM
                         and (insn.operands[0].imm & ((1 << 64) - 1)) == symbols[target]['st_value']]
            assert locations, (source, target)
            windows = []
            for index in locations:
                window = []
                for insn in instructions[max(0, index - 10):index + 3]:
                    constants = []
                    for operand in insn.operands:
                        address = None
                        if operand.type == X86_OP_IMM and insn.mnemonic not in ('call', 'jmp'):
                            address = operand.imm & ((1 << 64) - 1)
                        elif operand.type == X86_OP_MEM and operand.mem.base == X86_REG_RIP:
                            address = insn.address + insn.size + operand.mem.disp
                        value = read_virtual(address, 192) if address is not None else None
                        if value:
                            content = value[1].split(b'\0', 1)[0]
                            if len(content) >= 3 and all(32 <= c < 127 or c in (9, 10, 13) for c in content):
                                constants.append(dict(address=hex(address), section=value[0], text=content.decode()))
                    window.append(dict(address=hex(insn.address), offset=hex(insn.address - base),
                                       bytes=insn.bytes.hex(), mnemonic=insn.mnemonic,
                                       operands=insn.op_str, printable_constants=constants))
                windows.append(dict(transfer_address=hex(instructions[index].address), instructions=window))
            rows.append(dict(source=source, target=target, source_address=hex(base),
                             target_address=hex(symbols[target]['st_value']), source_section=section_name,
                             source_bytes=len(code), source_sha256=hashlib.sha256(code).hexdigest(),
                             direct_control_transfers=len(locations), windows=windows))
        result = dict(status='PASS', elf=str(args.elf), elf_bytes=args.elf.stat().st_size,
                      elf_mtime_ns=args.elf.stat().st_mtime_ns, build_ids=build_ids,
                      scope='Eight selected static ELF edge checks; no path-feasibility proof, runtime execution, or second checker run.',
                      edges=rows)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(dict(status=result['status'], build_ids=build_ids,
                              edges=[dict(source=r['source'], target=r['target'], transfers=r['direct_control_transfers'],
                                          strings=[c['text'] for w in r['windows'] for i in w['instructions']
                                                   for c in i['printable_constants']]) for r in rows]), indent=2))


if __name__ == '__main__':
    main()
