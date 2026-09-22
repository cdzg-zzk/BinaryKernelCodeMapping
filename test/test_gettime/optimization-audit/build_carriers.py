#!/usr/bin/env python3
"""Construct isolated full-carrier candidates; never edit archived packages."""
import argparse
import difflib
import json
from pathlib import Path
import re
import subprocess
from elftools.elf.elffile import ELFFile

HERE = Path(__file__).resolve().parent
TESTS = HERE.parent / 'vkso-tests'


def run(args):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True, text=True)


def update_size(binary, symbol, size):
    import io
    import struct
    elf = ELFFile(io.BytesIO(binary))
    for name in ['.dynsym', '.symtab']:
        section = elf.get_section_by_name(name)
        for index, entry in enumerate(section.iter_symbols()):
            if entry.name == symbol:
                struct.pack_into('<Q', binary,
                    int(section['sh_offset']) + index * int(section['sh_entsize']) + 16, size)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('codegen', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    archived = TESTS / 'revision/results/normal-campaign/step-001/compact-split/package/libkernel.so'
    binary = archived.read_bytes()
    with archived.open('rb') as stream:
        elf = ELFFile(stream)
        syms = {s.name: int(s['st_value']) for s in elf.get_section_by_name('.symtab').iter_symbols()}
    (out / 'baseline.so').write_bytes(binary)
    source = (TESTS / 'functional/vkso_user_entry.S').read_text()
    fallback = '''	.type vkso_user_gettimeofday_failure, @function
vkso_user_gettimeofday_failure:
	movl	$__NR_gettimeofday, %eax
	syscall
	ret
	.size vkso_user_gettimeofday_failure, \\
		.-vkso_user_gettimeofday_failure
'''
    assert fallback in source
    candidate = source.replace(fallback, '')
    candidate = candidate.replace('''__vkso_gettimeofday:
	leaq''', '''__vkso_gettimeofday:
	movq %rdi, %rax
	orq %rsi, %rax
	jz .Lgettimeofday_empty
	leaq''')
    candidate = candidate.replace('''	jmp	vkso_gettimeofday_core
	.size __vkso_gettimeofday''', '''	jmp	vkso_gettimeofday_core
.Lgettimeofday_empty:
	xorl %eax, %eax
	ret
	.size __vkso_gettimeofday''')
    candidate = candidate.replace('\t.section .vkso.user.data, "aw", @progbits',
        '\t.p2align 4\n' + fallback + '\n\t.section .vkso.user.data, "aw", @progbits')
    (out / 'entry-null.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),
        candidate.splitlines(True), fromfile='a/vkso_user_entry.S', tofile='b/vkso_user_entry.S')))
    kernel = HERE.parent / 'linux-5.15.198-vkso'
    for name, text in [('entry-baseline', source), ('entry-null', candidate)]:
        assembly = out / f'{name}.S'
        obj = out / f'{name}.o'
        linked = out / f'{name}.elf'
        assembly.write_text(text)
        run(['gcc', '-c', '-I' + str(kernel / 'include'),
             '-I' + str(kernel / 'arch/x86/include/generated/uapi'), assembly, '-o', obj])
        definitions = [f'--defsym={key}={value}' for key, value in syms.items()
                       if key and not key.startswith('__vkso_')]
        run(['ld', '--section-start=.vkso.user.text=0x1601000',
             '--section-start=.vkso.user.data=0x1602000', *definitions, obj, '-o', linked])
        blob = out / f'{name}.bin'
        run(['objcopy', '-O', 'binary', '-j', '.vkso.user.text', linked, blob])
        payload = blob.read_bytes()
        assert len(payload) < 4096
        if name == 'entry-baseline':
            assert payload == binary[0x3000:0x3000 + len(payload)], 'baseline entry reconstruction differs'
        else:
            changed = bytearray(binary)
            changed[0x3000:0x4000] = payload.ljust(4096, b'\0')
            with linked.open('rb') as stream:
                size = int(ELFFile(stream).get_section_by_name('.symtab').get_symbol_by_name('__vkso_gettimeofday')[0]['st_size'])
            update_size(changed, '__vkso_gettimeofday', size)
            (out / f'{name}.so').write_bytes(changed)
        (out / f'{name}.asm').write_text(run(['objdump', '-d', linked]).stdout)
    # Relocate the complete Kbuild object so the coarse function lands at its
    # archived virtual address. Extract only that complete function; all other
    # live runtime-patched functions and offsets stay byte-identical.
    for name in ['baseline', 'coarse-late-offset']:
        obj = args.codegen / name / 'core.o'
        with obj.open('rb') as stream:
            elf = ELFFile(stream)
            symbol = elf.get_section_by_name('.symtab').get_symbol_by_name('vkso_clock_gettime_coarse')[0]
            offset, size = int(symbol['st_value']), int(symbol['st_size'])
        start = syms['vkso_clock_gettime_coarse'] - offset
        linked = out / f'{name}-core.elf'
        run(['ld', f'--section-start=.vkso.text={start:#x}',
             f"--defsym=vkso_shared_page={syms['vkso_shared_page']}",
             f"--defsym=vkso_cycles_read_cold={syms['vkso_cycles_read_cold']}",
             f"--defsym=__x86_return_thunk={syms['its_return_thunk']}",
             f"--defsym=__x86_indirect_thunk_rax={syms['__x86_indirect_thunk_rax']}", obj, '-o', linked])
        with linked.open('rb') as stream:
            elf = ELFFile(stream)
            payload = elf.get_section_by_name('.vkso.text').data()[offset:offset + size]
        assert size <= 144
        if name == 'baseline':
            assert payload == binary[0x1220:0x1220 + size], 'baseline coarse reconstruction differs'
        else:
            changed = bytearray(binary)
            changed[0x1220:0x12b0] = payload.ljust(144, b'\x90')
            update_size(changed, 'vkso_clock_gettime_coarse', size)
            (out / 'coarse-late-offset.so').write_bytes(changed)
    (out / 'identity.json').write_text(json.dumps(dict(source=str(archived),
        baseline_reconstruction='entry and full coarse body match the archived live bytes',
        methods=['baseline', 'entry-null', 'coarse-late-offset'],
        limits='coarse candidate uses copied user text; entry candidate modifies only private wrapper'), indent=2))
    print('carrier_reconstruction=pass')


if __name__ == '__main__':
    main()
