#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MAKE_DLL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MAKE_DLL))

from build_PIC_so import KoFile, PAGE_SIZE  # noqa: E402


class KoCoreLayoutTests(unittest.TestCase):
    def test_ro_after_init_group_precedes_data_with_page_padding(self) -> None:
        assembly = r'''
            .text
            ret
            .section .rodata, "a", @progbits
            .quad 1
            .data
            .quad external_target
            .section __jump_table, "aw", @progbits
            .skip 24
            .section .data..ro_after_init, "aw", @progbits
            .quad 2
            .section .bss, "aw", @nobits
            .balign 16
            .skip 448
            .section .note.GNU-stack, "", @progbits
        '''
        with tempfile.TemporaryDirectory() as tmp:
            source, obj = Path(tmp)/'groups.S', Path(tmp)/'groups.ko'
            source.write_text(assembly)
            subprocess.run(['gcc', '-c', str(source), '-o', str(obj)], check=True)
            ko = KoFile(obj)
            layout = ko.compute_core_layout()
        offset = lambda name: layout.section_offsets[ko.find_section(name).index]
        self.assertEqual(offset('__jump_table'), layout.ro_end)
        self.assertEqual(offset('.data..ro_after_init'), layout.ro_end+24)
        self.assertEqual(offset('.data'), layout.ro_end+PAGE_SIZE)
        self.assertEqual(offset('.bss'), layout.ro_end+PAGE_SIZE+16)
        self.assertEqual(len(layout.data_image), 2*PAGE_SIZE)
        self.assertEqual(layout.data_relocs[0].offset, PAGE_SIZE)

    def test_layout_is_computed_by_ko_file(self) -> None:
        assembly = r"""
            .section .text.core, "ax", @progbits
            .globl core_function
            .type core_function, @function
        core_function:
            ret
            .size core_function, .-core_function

            .section .rodata.core, "a", @progbits
            .quad 0x1122334455667788

            .section .data.core, "aw", @progbits
            .globl data_pointer
        data_pointer:
            .quad external_target

            .section .bss.core, "aw", @nobits
            .balign 8
            .skip 8

            .section .init.text, "ax", @progbits
            nop
            .section .note.GNU-stack, "", @progbits
        """
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "layout.S"
            obj = Path(tmp) / "layout.ko"
            source.write_text(assembly)
            subprocess.run(
                ["gcc", "-c", "-o", str(obj), str(source)],
                check=True,
            )
            ko = KoFile(obj)
            layout = ko.compute_core_layout()

        text = ko.find_section(".text.core")
        rodata = ko.find_section(".rodata.core")
        data = ko.find_section(".data.core")
        bss = ko.find_section(".bss.core")
        init = ko.find_section(".init.text")
        self.assertIsNotNone(text)
        self.assertIsNotNone(rodata)
        self.assertIsNotNone(data)
        self.assertIsNotNone(bss)
        self.assertIsNotNone(init)

        self.assertEqual(layout.text_start, 0)
        self.assertEqual(layout.text_end % PAGE_SIZE, 0)
        self.assertEqual(layout.ro_start, layout.text_end)
        self.assertEqual(layout.data_start, layout.ro_end)
        self.assertEqual(layout.data_end % PAGE_SIZE, 0)
        self.assertNotIn(init.index, layout.section_offsets)
        self.assertEqual(
            layout.ro_image[
                layout.section_offsets[rodata.index] - layout.ro_start:
                layout.section_offsets[rodata.index] - layout.ro_start + 8
            ],
            bytes.fromhex("8877665544332211"),
        )
        self.assertEqual(len(layout.data_relocs), 1)
        self.assertEqual(layout.data_relocs[0].symbol_name, "external_target")
        self.assertTrue(layout.data_relocs[0].is_undef)
        self.assertEqual(
            layout.data_image[
                layout.section_offsets[bss.index] - layout.data_start:
                layout.section_offsets[bss.index] - layout.data_start + 8
            ],
            bytes(8),
        )


if __name__ == "__main__":
    unittest.main()
