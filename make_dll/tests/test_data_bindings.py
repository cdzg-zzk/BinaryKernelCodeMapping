#!/usr/bin/env python3
"""Private pointer relocation and unchanged executable binding regression tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_PIC_so as B

ASSEMBLY = '''
.text
.globl direct,indirect
.type direct,@function
direct: call helper
ret
.size direct,.-direct
.type indirect,@function
indirect: call *slot(%rip)
ret
.size indirect,.-indirect
.data
.balign 8
.globl slot,other
.type slot,@object
slot: .quad helper
.size slot,8
.type other,@object
other: .quad helper+1
.size other,8
.section .rodata,"a",@progbits
.globl immutable
.type immutable,@object
immutable: .quad helper
.size immutable,8
.section .note.GNU-stack,"",@progbits
'''


class DataBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vkso-bindings-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        assembly = self.root / 'input.S'
        assembly.write_text(ASSEMBLY)
        self.obj = self.root / 'input.o'
        subprocess.run(['as', '--64', assembly, '-o', self.obj], check=True)
        self.ko = B.KoFile(self.obj)
        self.layout = self.ko.compute_core_layout()
        self.record = dict(slot='slot', kernel_symbol='helper', user_symbol='user_bridge',
                           user_library='libshim.so', signature='void *(void *, const void *, size_t)')
        self.path = self.root / 'bindings.json'

    def validate(self, records=None):
        self.path.write_text(json.dumps(dict(format='vkso-private-data-bindings-v1',
                                            bindings=records or [self.record])))
        return B.private_data_bindings(self.ko, self.layout, self.path, {'helper'})

    def test_owner_management_page_cannot_leak_private_pointers(self):
        assembly = self.root / 'owner.S'
        assembly.write_text(ASSEMBLY + '\n.section .vkso_owner,"aw",@progbits\n'
                            '.balign 4096\n.quad 0x564b534f4f574e52\n'
                            '.quad __this_module\n.zero 4080\n')
        obj = self.root / 'owner.o'
        subprocess.run(['as', '--64', assembly, '-o', obj], check=True)
        ko = B.KoFile(obj)
        layout = ko.compute_core_layout()
        descriptor = ko.find_section('.vkso_owner')
        offset = layout.section_offsets[descriptor.index] - layout.data_start
        self.assertEqual(int.from_bytes(ko.section_bytes(descriptor)[:8], 'little'), 0x564b534f4f574e52)
        self.assertEqual(layout.data_image[offset:offset + 4096], bytes(4096))
        self.assertNotIn('__this_module', [r.symbol_name for r in layout.data_relocs])
        self.assertIn('helper', [r.symbol_name for r in layout.data_relocs])

    def test_valid_slot_leaves_original_object_unchanged(self):
        original = self.obj.read_bytes()
        bindings = self.validate()
        self.assertEqual(list(bindings), [0])
        self.assertEqual(bindings[0]['user_symbol'], 'user_bridge')
        self.assertEqual(self.obj.read_bytes(), original)

    def test_wrong_initializer_and_read_only_object_rejected(self):
        for slot, error in [('other', 'initializer'), ('immutable', 'private 8-byte'), ('absent', 'one defined slot')]:
            with self.subTest(slot=slot):
                self.record['slot'] = slot
                with self.assertRaisesRegex(ValueError, error):
                    self.validate()

    def test_duplicate_slot_and_implicit_name_binding_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate or overlapping'):
            self.validate([self.record, self.record])
        self.record['user_symbol'] = 'helper'
        with self.assertRaisesRegex(ValueError, 'distinct target'):
            self.validate()

    def test_bound_data_does_not_authorize_a_direct_text_reference(self):
        self.validate()
        imported = B.ResolvedSymbol(name='helper', source='libshim.so', defined=False,
                                    st_type=B.STT_FUNC, module_name='shim')
        for name, rejected in [('direct', True), ('indirect', False)]:
            symbol = self.ko.find_symbol(name)[1]
            selected = B.ResolvedSymbol(name=name, source='libowner.so', defined=True,
                exported=True, st_type=B.STT_FUNC, module_name='owner', size=symbol.st_size)
            with self.subTest(name=name):
                if rejected:
                    with self.assertRaises(ValueError):
                        B.validate_executable_shim_bindings(self.ko, [selected, imported], 'owner')
                else:
                    B.validate_executable_shim_bindings(self.ko, [selected, imported], 'owner')


if __name__ == '__main__':
    unittest.main()
