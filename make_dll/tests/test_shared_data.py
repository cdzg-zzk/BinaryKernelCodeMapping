#!/usr/bin/env python3

import struct
import sys
import tempfile
import unittest
from pathlib import Path


MAKE_DLL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MAKE_DLL))

from build_PIC_so import (  # noqa: E402
    ManualElfBuilder,
    PAGE_SIZE,
    PF_R,
    PF_W,
    PF_X,
    PT_LOAD,
    ResolvedSymbol,
    STT_FUNC,
    STT_OBJECT,
)


class SharedDataTests(unittest.TestCase):
    @staticmethod
    def symbol(name, address, size, st_type, reuse_kind=None):
        return ResolvedSymbol(
            name=name,
            source="libkernel.so",
            defined=True,
            st_type=st_type,
            size=size,
            address=address,
            reuse_kind=reuse_kind,
        )

    def test_shared_page_is_reusable_read_only_and_nx(self):
        text = self.symbol("vkso_read", 0x100000, 0x40, STT_FUNC)
        shared = self.symbol(
            "vkso_shared_page", 0x103000, PAGE_SIZE,
            STT_OBJECT, "shared_data",
        )
        private = self.symbol("private_state", 0x105000, 8, STT_OBJECT)
        builder = ManualElfBuilder(
            [text, shared, private], [], data_bytes=b"\0" * 8
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "libkernel.so"
            page_map = Path(tmp) / "page_mappings.txt"
            builder.write(output, page_map)
            blob = output.read_bytes()
            map_text = page_map.read_text()

        shared_section = builder.sections[shared.section_name]
        self.assertEqual(shared.section_name, ".shared_data")
        self.assertEqual(shared_section.sh_flags, 0x2)  # SHF_ALLOC only
        self.assertIn(",shared_data,.shared_data\n", map_text)
        self.assertNotIn(",shared_data,.data\n", map_text)
        self.assertEqual(
            shared.virtual_address - text.virtual_address,
            shared.address - text.address,
        )

        phoff = struct.unpack_from("<Q", blob, 32)[0]
        phentsize = struct.unpack_from("<H", blob, 54)[0]
        phnum = struct.unpack_from("<H", blob, 56)[0]
        shared_load_flags = None
        for index in range(phnum):
            p_type, p_flags, _off, vaddr = struct.unpack_from(
                "<IIQQ", blob, phoff + index * phentsize
            )
            if p_type == PT_LOAD and vaddr == shared.virtual_address:
                shared_load_flags = p_flags
                break
        self.assertEqual(shared_load_flags, PF_R)
        self.assertFalse(shared_load_flags & (PF_W | PF_X))

    def test_rejects_partial_shared_page(self):
        text = self.symbol("vkso_read", 0x200000, 0x40, STT_FUNC)
        shared = self.symbol(
            "unsafe", 0x203000, 64, STT_OBJECT, "shared_data"
        )
        with self.assertRaisesRegex(ValueError, "occupy whole pages"):
            ManualElfBuilder([text, shared], []).write(Path("unused.so"))

    def test_rejects_private_object_on_shared_page(self):
        text = self.symbol("vkso_read", 0x300000, 0x40, STT_FUNC)
        shared = self.symbol(
            "shared", 0x303000, PAGE_SIZE, STT_OBJECT, "shared_data"
        )
        alias = self.symbol("private_alias", 0x303100, 8, STT_OBJECT)
        with self.assertRaisesRegex(ValueError, "overlaps a shared_data page"):
            ManualElfBuilder([text, shared, alias], []).write(Path("unused.so"))


if __name__ == "__main__":
    unittest.main()
