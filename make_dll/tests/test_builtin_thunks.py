#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path


MAKE_DLL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MAKE_DLL))

from build_PIC_so import (  # noqa: E402
    BUILTIN_THUNK_MODULE,
    DIRECT_THUNK_ENCODINGS,
    ManualElfBuilder,
    PAGE_SIZE,
    ResolvedSymbol,
    STT_FUNC,
    build_builtin_thunk_pages,
    role_for_symbol,
    split_builtin_thunk_shims,
)


class BuiltinThunkTests(unittest.TestCase):
    def make_symbol(self, name: str, address: int, size: int = 0x20) -> ResolvedSymbol:
        return ResolvedSymbol(
            name=name,
            source="libkernel.so",
            defined=True,
            st_type=STT_FUNC,
            size=size,
            address=address,
        )

    def test_split_keeps_normal_shims_external(self) -> None:
        regular, builtin = split_builtin_thunk_shims({
            "kmalloc",
            "__x86_indirect_thunk_array",
            "__x86_indirect_thunk_r11",
        })
        self.assertEqual(regular, {"kmalloc"})
        self.assertEqual(
            builtin,
            {"__x86_indirect_thunk_array", "__x86_indirect_thunk_r11"},
        )

    def test_array_alias_generates_rax_jump_and_return(self) -> None:
        page = 0x12345000
        array = self.make_symbol("__x86_indirect_thunk_array", page + 0x240)
        ret = self.make_symbol("__x86_return_thunk", page + 0x580, 2)

        pages = build_builtin_thunk_pages(
            [array, ret], {"__x86_indirect_thunk_rax"}
        )

        self.assertEqual(set(pages), {page})
        self.assertEqual(pages[page][0x240:0x242], DIRECT_THUNK_ENCODINGS["rax"])
        self.assertEqual(pages[page][0x580], 0xC3)
        self.assertEqual(array.module_name, BUILTIN_THUNK_MODULE)
        self.assertEqual(ret.module_name, BUILTIN_THUNK_MODULE)
        self.assertEqual(role_for_symbol(array, "kernel"), "synthetic")

    def test_extended_register_encoding_is_emitted(self) -> None:
        page = 0x20000000
        r14 = self.make_symbol("__x86_indirect_thunk_r14", page + 0x400)
        pages = build_builtin_thunk_pages(
            [r14], {"__x86_indirect_thunk_r14"}
        )
        self.assertEqual(pages[page][0x400:0x403], b"\x41\xff\xe6")

    def test_rejects_non_thunk_dependency_on_synthetic_page(self) -> None:
        page = 0x30000000
        thunk = self.make_symbol("__x86_indirect_thunk_rax", page + 0x240)
        other = self.make_symbol("unrelated_function", page + 0x900)
        with self.assertRaisesRegex(ValueError, "non-thunk dependency"):
            build_builtin_thunk_pages(
                [thunk, other], {"__x86_indirect_thunk_rax"}
            )

    def test_manual_builder_writes_synthetic_page(self) -> None:
        page = 0x40000000
        thunk = self.make_symbol("__x86_indirect_thunk_rax", page + 0x240)
        pages = build_builtin_thunk_pages(
            [thunk], {"__x86_indirect_thunk_rax"}
        )
        builder = ManualElfBuilder(
            symbols=[thunk],
            needed_libraries=[],
            synthetic_text_pages=pages,
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "libkernel.so"
            builder.write(output)
            blob = output.read_bytes()
        self.assertEqual(blob[PAGE_SIZE + 0x240:PAGE_SIZE + 0x242], b"\xff\xe0")


if __name__ == "__main__":
    unittest.main()
