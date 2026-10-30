"""Regression for omitted local string pages in a sparse module carrier."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_PIC_so import (KoFile, ManualElfBuilder, PAGE_SIZE, ResolvedSymbol,
                          STT_FUNC, module_referenced_ro_ranges)


class ModuleReadonlyClosureTests(unittest.TestCase):
    def test_local_literal_and_data_addend_without_unselected_function(self):
        assembly = r'''
        .text
        .globl selected
        .type selected, @function
        selected:
            lea .Lliteral(%rip), %rax
            ret
        .size selected, .-selected
        .globl unselected
        .type unselected, @function
        unselected:
            lea .Lunused(%rip), %rax
            ret
        .size unselected, .-unselected
        .section .rodata.strings,"a",@progbits
        .balign 4096
        .skip 4096
        .Lliteral: .asciz "."
        .section .rodata.unrelated,"a",@progbits
        .balign 4096
        .Lunused: .asciz "not referenced by selected code"
        .section .rodata.data_target,"a",@progbits
        .balign 4096
        .Lbase:
        .skip 4096
        .asciz "target reached with an addend"
        .section .data.pointer,"aw",@progbits
        .quad .Lbase + 4096
        .section .note.GNU-stack,"",@progbits
        '''
        base = 0x100000
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source, obj = tmp/'fixture.S', tmp/'fixture.ko'
            source.write_text(assembly)
            subprocess.run(['gcc', '-c', str(source), '-o', str(obj)], check=True)
            ko = KoFile(obj)
            layout = ko.compute_core_layout()
            elf_symbol = ko.find_symbol('selected')[1]
            selected = ResolvedSymbol(name='selected', source='libfixture.so',
                defined=True, exported=True, st_type=STT_FUNC, module_name='fixture',
                size=elf_symbol.st_size,
                address=base+layout.section_offsets[elf_symbol.st_shndx]+elf_symbol.st_value)
            ranges = module_referenced_ro_ranges(ko, layout, [selected], 'fixture', base)
            expected = []
            for name in ['.rodata.strings', '.rodata.data_target']:
                section = ko.find_section(name)
                start = base+layout.section_offsets[section.index]
                expected.append((start, start+section.sh_size))
            self.assertEqual(ranges, sorted(expected))
            self.assertEqual(layout.data_relocs[0].addend, PAGE_SIZE)
            builder = ManualElfBuilder([selected], [], extra_ro_ranges=ranges)
            builder.write(tmp/'libfixture.so')
            pages = {address for _, address, kind, _ in builder.reusable_page_mappings()
                     if kind == 'rodata'}
            for start, _ in expected:
                self.assertIn(start+PAGE_SIZE, pages)
            unused = ko.find_section('.rodata.unrelated')
            self.assertNotIn(base+layout.section_offsets[unused.index], pages)


if __name__ == '__main__':
    unittest.main()
