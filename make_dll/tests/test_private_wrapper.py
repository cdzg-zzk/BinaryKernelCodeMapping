#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


MAKE_DLL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MAKE_DLL))

from build_PIC_so import (  # noqa: E402
    private_wrapper_dependencies,
    resolve_requested_symbols,
)


class FakeGraph:
    path = Path("fake.krg")

    def __init__(self):
        self.entries = {
            name: SimpleNamespace(
                name=name,
                kind=0,
                module_id=0,
                module_name="kernel",
                size=16,
                address=address,
            )
            for name, address in (
                ("public_api", 0x1000),
                ("wrapper_dependency", 0x1100),
            )
        }

    def lookup(self, name):
        return self.entries.get(name)

    def closure(self, name, stop_names):
        del stop_names
        if name not in self.entries:
            raise KeyError(name)
        return [self.entries[name]]


class PrivateWrapperTests(unittest.TestCase):
    def test_undefined_text_references_become_dependency_roots(self):
        assembly = """
            .section .vkso.user.text, "ax", @progbits
            .globl wrapper
            .type wrapper, @function
        wrapper:
            call wrapper_dependency
            leaq shared_page(%rip), %rax
            ret
            .size wrapper, .-wrapper
            .section .vkso.user.data, "aw", @progbits
            .quad 0
            .section .note.GNU-stack, "", @progbits
        """
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "wrapper.S"
            obj = Path(tmp) / "wrapper.o"
            source.write_text(assembly)
            subprocess.run(
                ["gcc", "-c", "-fPIC", "-o", str(obj), str(source)],
                check=True,
            )
            dependencies = private_wrapper_dependencies(obj)

        self.assertEqual(
            dependencies, ["wrapper_dependency", "shared_page"]
        )

    def test_dependency_root_is_not_exported(self):
        resolved, *_ = resolve_requested_symbols(
            ["public_api", "wrapper_dependency"],
            FakeGraph(),
            set(),
            exported_names=["public_api"],
        )
        by_name = {symbol.name: symbol for symbol in resolved}

        self.assertTrue(by_name["public_api"].exported)
        self.assertFalse(by_name["wrapper_dependency"].exported)


if __name__ == "__main__":
    unittest.main()
