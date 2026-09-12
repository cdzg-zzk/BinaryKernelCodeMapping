#!/usr/bin/env python3
"""Compile the complete original/proposed owners only; never load either module."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import subprocess
import sys

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OWNER = Path('test/test_lz4/kmod')
INPUTS = ['Makefile', 'lz4defs.h', 'lz4_compress.c', 'lz4_decompress.c', 'module_meta.c']
HELPERS = {'memcpy', 'memmove', 'memset'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proposal(original):
    proposed = dict(original)
    before = ('#define LZ4_memcpy(dst, src, size) __builtin_memcpy(dst, src, size)\n'
              '#define LZ4_memmove(dst, src, size) __builtin_memmove(dst, src, size)')
    after = '''#ifdef VKSO_LZ4_USERSPACE
#define LZ4_memcpy(dst, src, size) __builtin_memcpy(dst, src, size)
#define LZ4_memmove(dst, src, size) __builtin_memmove(dst, src, size)
#define LZ4_memset(dst, value, size) memset(dst, value, size)
#else
/* Runtime-loaded kernel pointers become private DSO data relocations.
 * Preserve the small constant copies used by the full algorithm's hot loop;
 * the exact supported Kbuild output must contain no out-of-line helper call
 * from the builtin arm. Dynamic and large operations use the private slots.
 */
extern void *(*vkso_lz4_memcpy_slot)(void *, const void *, size_t);
extern void *(*vkso_lz4_memmove_slot)(void *, const void *, size_t);
extern void *(*vkso_lz4_memset_slot)(void *, int, size_t);
#define LZ4_memcpy(dst, src, size) \\
\t((__builtin_constant_p(size) && \\
\t  ((size) == 2 || (size) == 4 || (size) == 8 || (size) == 16)) \\
\t ? __builtin_memcpy((dst), (src), (size)) \\
\t : vkso_lz4_memcpy_slot((dst), (src), (size)))
#define LZ4_memmove(dst, src, size) \\
\tvkso_lz4_memmove_slot((dst), (src), (size))
#define LZ4_memset(dst, value, size) \\
\tvkso_lz4_memset_slot((dst), (value), (size))
#endif'''
    assert proposed['lz4defs.h'].count(before) == 1
    proposed['lz4defs.h'] = proposed['lz4defs.h'].replace(before, after)
    for name, old, new in (
        ('lz4_compress.c', 'memset(LZ4_stream, 0, sizeof(LZ4_stream_t));',
         'LZ4_memset(LZ4_stream, 0, sizeof(LZ4_stream_t));'),
        ('lz4_compress.c', 'memmove(safeBuffer, previousDictEnd - dictSize, dictSize);',
         'LZ4_memmove(safeBuffer, previousDictEnd - dictSize, dictSize);'),
        ('lz4_decompress.c', 'memmove(op, dictEnd - (lowPrefix - match),',
         'LZ4_memmove(op, dictEnd - (lowPrefix - match),'),
    ):
        assert proposed[name].count(old) == 1
        proposed[name] = proposed[name].replace(old, new)
    proposed['module_meta.c'] = proposed['module_meta.c'].replace(
        '#include <linux/module.h>\n', '''#include <linux/module.h>
#include <linux/string.h>

/* The normal module uses native kernel helpers. build_PIC_so converts these
 * pointer initializers into explicit dynamic relocations in private data.
 * Actual user helper/ABI identity is checked by the deployment observer;
 * a dependency's name alone does not identify the implementation selected.
 */
void *(*vkso_lz4_memcpy_slot)(void *, const void *, size_t) = memcpy;
void *(*vkso_lz4_memmove_slot)(void *, const void *, size_t) = memmove;
void *(*vkso_lz4_memset_slot)(void *, int, size_t) = memset;
''')
    return proposed


def inspect(module):
    with module.open('rb') as stream:
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name('.symtab')
        functions = [s for s in symtab.iter_symbols()
                     if s['st_info']['type'] == 'STT_FUNC'
                     and isinstance(s['st_shndx'], int) and s['st_size']]
        slots = [s for s in symtab.iter_symbols() if s.name.startswith('vkso_lz4_')
                 and s.name.endswith('_slot')]
        code = Cs(CS_ARCH_X86, CS_MODE_64)
        code.detail = True
        instruction_maps = {}
        function_instructions = {}
        for f in functions:
            blob = elf.get_section(f['st_shndx']).data()[f['st_value']:f['st_value']+f['st_size']]
            decoded = list(code.disasm(blob, f['st_value']))
            function_instructions[f.name] = decoded
            for ins in decoded:
                instruction_maps.setdefault(f['st_shndx'], []).append((ins.address,
                    ins.address + ins.size, f.name, ins.mnemonic, ins.op_str))
        executable, data = [], []
        for section in elf.iter_sections():
            if not isinstance(section, RelocationSection):
                continue
            symbols = elf.get_section(section['sh_link'])
            target = elf.get_section(section['sh_info'])
            for relocation in section.iter_relocations():
                sym = symbols.get_symbol(relocation['r_info_sym'])
                row = dict(section=target.name, offset=relocation['r_offset'],
                           type=relocation['r_info_type'], target=sym.name,
                           target_undefined=sym['st_shndx']=='SHN_UNDEF',
                           addend=relocation['r_addend'])
                if target['sh_flags'] & 4:
                    covering = next((item for item in instruction_maps.get(section['sh_info'], [])
                        if item[0] <= row['offset'] < item[1]), None)
                    if covering:
                        row.update(function=covering[2], instruction=covering[3], operands=covering[4])
                        if sym.name.endswith('_slot'):
                            # GCC emits a RIP-relative load followed by call *%rax,
                            # not a direct memory-operand call in this exact build.
                            assert covering[3:] == ('mov', 'rax, qword ptr [rip]'), row
                            by_address = {ins.address: ins for ins in function_instructions[covering[2]]}
                            cursor, visited = covering[1], set()
                            row['local_direct_jumps_before_transfer'] = []
                            while cursor in by_address and cursor not in visited:
                                visited.add(cursor)
                                ins = by_address[cursor]
                                if ins.mnemonic == 'jmp' and ins.op_str.startswith('0x'):
                                    row['local_direct_jumps_before_transfer'].append(ins.address)
                                    cursor = int(ins.op_str, 16)
                                    continue
                                if ins.group(1) or ins.group(2) or ins.group(3):
                                    assert ins.mnemonic in ('call', 'jmp') and ins.op_str == 'rax', row
                                    row['indirect_transfer_offset'] = ins.address
                                    row['indirect_transfer'] = ins.mnemonic + ' ' + ins.op_str
                                    break
                                written = {ins.reg_name(reg) for reg in ins.regs_access()[1]}
                                assert not written.intersection({'rax', 'eax', 'ax', 'al', 'ah'}), row
                                cursor += ins.size
                            assert 'indirect_transfer_offset' in row, row
                    executable.append(row)
                elif target['sh_flags'] & 3 == 3:
                    data.append(row)
        return dict(
            module_sha256=sha(module),
            text_bytes=elf.get_section_by_name('.text')['sh_size'],
            function_count=len(functions),
            functions={f.name: {'bytes': f['st_size'], 'offset': f['st_value'],
                               'section': elf.get_section(f['st_shndx']).name}
                       for f in functions},
            selected_three_function_body_text_pages=sorted({page
                for f in functions if f.name in ('LZ4_compress_fast_extState',
                    'vkso_LZ4_compress_default', 'vkso_LZ4_decompress_safe')
                for page in range(f['st_value'] // 4096,
                                  (f['st_value'] + f['st_size'] + 4095) // 4096)}),
            slots=[{'name': s.name, 'bytes': s['st_size'],
                    'section': elf.get_section(s['st_shndx']).name, 'offset': s['st_value']}
                   for s in slots],
            executable_memory_helper_relocations=[r for r in executable if r['target'] in HELPERS],
            executable_slot_references=[r for r in executable if r['target'].endswith('_slot')],
            data_memory_helper_relocations=[r for r in data if r['target'] in HELPERS],
            other_undefined_executable_relocations=[r for r in executable
                if r['target_undefined'] and r['target'] not in HELPERS],
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect-existing', action='store_true',
                        help='re-inspect the preserved compile outputs without rebuilding')
    args = parser.parse_args()
    output = HERE / 'lz4-helper-binding-validation'
    output.mkdir(exist_ok=args.inspect_existing)
    before = {name: sha(ROOT / OWNER / name) for name in INPUTS}
    original = {name: (ROOT / OWNER / name).read_text() for name in INPUTS}
    proposed = proposal(original)
    patch = ''.join(''.join(difflib.unified_diff(original[name].splitlines(True),
        proposed[name].splitlines(True), fromfile='a/' + str(OWNER / name),
        tofile='b/' + str(OWNER / name))) for name in INPUTS)
    (HERE / 'lz4-helper-binding.patch').write_text(patch)
    report = {'scope': 'complete-owner isolated compilation and ELF inspection only; no module load, '
                       'guest, modified application execution or performance observation',
              'source_sha256': before, 'variants': {}}
    for variant, sources in (('original', original), ('proposed', proposed)):
        directory = output / variant
        directory.mkdir(exist_ok=args.inspect_existing)
        for name, content in sources.items():
            if args.inspect_existing:
                assert (directory / name).read_text() == content
            else:
                (directory / name).write_text(content)
        command = ['make', '-C', '/usr/src/linux-headers-5.15.0-119-generic',
                   'M=' + str(directory), 'CC=gcc-11', '-j2', 'modules']
        if not args.inspect_existing:
            with (output / (variant + '-build.log')).open('w') as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        report['variants'][variant] = inspect(directory / 'vkso_lz4.ko')
        report['variants'][variant]['command'] = command
        with (output / (variant + '-elf.txt')).open('w') as log:
            subprocess.run(['readelf', '-rWs', directory / 'vkso_lz4.ko'],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        with (output / (variant + '-disassembly.txt')).open('w') as log:
            subprocess.run(['objdump', '-dr', directory / 'vkso_lz4.ko'],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    old, new = report['variants']['original'], report['variants']['proposed']
    assert old['executable_memory_helper_relocations']
    assert not new['executable_memory_helper_relocations'], new
    assert set(old['functions']) == set(new['functions'])
    assert len(new['slots']) == 3 and all(s['bytes'] == 8 for s in new['slots'])
    assert {r['target'] for r in new['data_memory_helper_relocations']} == HELPERS
    assert all(r['type'] == 1 and r['target_undefined']
               for r in new['data_memory_helper_relocations'])
    assert all(r['type'] == 2 and r.get('indirect_transfer') in ('call rax', 'jmp rax')
               for r in new['executable_slot_references'])
    after = {name: sha(ROOT / OWNER / name) for name in INPUTS}
    assert after == before
    report['source_unchanged'] = True
    shim_source = ROOT / 'make_dll/shim.c'
    shim_before = sha(shim_source)
    bridge_source = HERE / 'lz4-helper-binding-user-bridge.c'
    bridge_library = output / 'libshim-proposed.so'
    bridge_command = ['gcc-11', '-shared', '-fPIC', '-O2', '-Wall', '-Wextra',
                      str(shim_source), str(bridge_source), '-ldl', '-o', str(bridge_library)]
    with (output / 'user-bridge-build.log').open('w') as log:
        subprocess.run(bridge_command, stdout=log, stderr=subprocess.STDOUT, check=True)
    bridge_text = []
    with bridge_library.open('rb') as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name('.symtab')
        code = Cs(CS_ARCH_X86, CS_MODE_64)
        for name in ('vkso_abi_memcpy', 'vkso_abi_memmove', 'vkso_abi_memset'):
            function = symbols.get_symbol_by_name(name)[0]
            section = elf.get_section(function['st_shndx'])
            offset = function['st_value'] - section['sh_addr']
            instructions = list(code.disasm(section.data()[offset:offset+function['st_size']],
                                           function['st_value']))
            align = next(i for i, ins in enumerate(instructions)
                         if ins.mnemonic == 'and' and ins.op_str == 'rsp, 0xfffffffffffffff0')
            call = next(i for i, ins in enumerate(instructions) if ins.mnemonic == 'call')
            assert align < call
            assert instructions[call].op_str.startswith('qword ptr [rip ')
            bridge_text.extend(f'{ins.address:#x}: {ins.mnemonic} {ins.op_str}' for ins in instructions)
    (output / 'user-bridge-disassembly.txt').write_text('\n'.join(bridge_text) + '\n')
    assert sha(shim_source) == shim_before
    report['user_abi_bridge'] = {'command': bridge_command, 'original_shim_sha256': shim_before,
        'addition_sha256': sha(bridge_source), 'library_sha256': sha(bridge_library),
        'unique_entry_count': 3, 'all_entries_align_rsp_to_16_before_indirect_libc_call': True,
        'original_shim_unchanged': True,
        'scope': 'linked and disassembled only; constructors and wrappers were not executed'}
    report['status'] = 'compile-and-relocation-shape-pass; runtime binding remains unverified'
    report['limits'] = [
        'No new live KRG/DSO was generated; old guest KRG cannot describe the changed module.',
        'Native kernel slot initialization and actual user target/ABI require runtime verification.',
        'Existing sanitizer/instrumentation references are listed, not silently removed.',
        'No performance or correctness claim follows from this compilation.',
    ]
    report['validation_note'] = ('Initial ELF audit incorrectly required a memory-operand indirect '
        'call at each slot relocation and stopped after both complete owners compiled. '
        'The corrected audit verifies each actual RIP-relative load into rax reaches an indirect '
        'call/jump through rax, following local unconditional jumps and rejecting other '
        'intervening control transfers or a write to that register. '
        'The preserved build outputs were re-inspected without rebuilding.')
    (HERE / 'lz4-helper-binding-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    subprocess.run(['git', 'apply', '--check', HERE / 'lz4-helper-binding.patch'],
                   cwd=ROOT, check=True)
    print(json.dumps({'status': report['status'], 'functions': new['function_count'],
        'original_direct_helper_sites': len(old['executable_memory_helper_relocations']),
        'proposed_direct_helper_sites': len(new['executable_memory_helper_relocations']),
        'proposed_slot_references': len(new['executable_slot_references']),
        'proposed_data_helper_relocations': len(new['data_memory_helper_relocations']),
        'original_text_bytes': old['text_bytes'], 'proposed_text_bytes': new['text_bytes']}, indent=2))


if __name__ == '__main__':
    main()
