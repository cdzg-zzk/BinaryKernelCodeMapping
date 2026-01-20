#!/usr/bin/env python3
"""
Position-independent shared object builder with explicit GOT/REL support.

Workflow:
  - Read root symbols from symbols.txt (all must come from the same module/kernel)
  - Resolve them (and their closures) via out.krg, optionally dumping resolved_symbol_addresses.txt
  - Emit a sparse .so named after the owning module: kernel -> libkernel.so, module `foo` -> libfoo.so
  - Dependencies (DT_NEEDED) are other modules seen in the closure; self is omitted

No export-map is required; krg supplies addresses/sizes. GOT/RELA remain empty when no unresolved cross-module imports exist.

Usage:
  python3 build_PIC_so.py --symbols symbols.txt --krg ../kernel_cgd/src/out.krg
"""

from __future__ import annotations

import argparse
import sys
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set

# -----------------------------------------------------------------------------
# ELF constants
# -----------------------------------------------------------------------------

EI_NIDENT = 16
ELFCLASS64 = 2
ELFDATA2LSB = 1
EV_CURRENT = 1

ET_DYN = 3
EM_X86_64 = 62

PT_LOAD = 1
PT_DYNAMIC = 2

PF_X = 1
PF_W = 2
PF_R = 4

SHT_NULL = 0
SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_RELA = 4
SHT_DYNAMIC = 6
SHT_NOBITS = 8
SHT_DYNSYM = 11
SHT_GNU_HASH = 0x6FFFFFF6

SHF_WRITE = 0x1
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4

SHN_UNDEF = 0

STB_GLOBAL = 1
STT_NOTYPE = 0
STT_OBJECT = 1
STT_FUNC = 2

R_X86_64_GLOB_DAT = 6

DT_NULL = 0
DT_NEEDED = 1
DT_PLTGOT = 3
DT_STRTAB = 5
DT_SYMTAB = 6
DT_RELA = 7
DT_RELASZ = 8
DT_RELAENT = 9
DT_STRSZ = 10
DT_SYMENT = 11
DT_GNU_HASH = 0x6FFFFEF5

# -----------------------------------------------------------------------------
# Layout configuration
# -----------------------------------------------------------------------------

PAGE_SIZE = 0x1000
TEXT_BASE_VADDR = 0x1000
TEXT_BASE_OFFSET = 0x1000
DEFAULT_EXPORT_STUB_SIZE = 0x10

LIB_KERNEL = "libkernel.so"
LIB_SELF = "libA.so"
LIB_SHIM = "libshim.so"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def align(value: int, alignment: int) -> int:
    if alignment == 0:
        return value
    return (value + alignment - 1) & ~(alignment - 1)


def align_down(value: int, alignment: int) -> int:
    if alignment == 0:
        return value
    return value & ~(alignment - 1)


def parse_symbol_requests(path: Path) -> List[str]:
    names: List[str] = []
    seen: Set[str] = set()
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        token = line.split()[0]
        if not token or token in seen:
            continue
        seen.add(token)
        names.append(token)
    return names


def load_shim_symbols(path: Path | None) -> Set[str]:
    if path is None or not path.exists():
        return set()
    return set(parse_symbol_requests(path))


def gnu_hash(name: str) -> int:
    h = 5381
    for ch in name:
        h = ((h * 33) + ord(ch)) & 0xFFFFFFFF
    return h


# -----------------------------------------------------------------------------
# KrgGraph loader
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class KrgResolvedSymbol:
    name: str
    address: int
    size: int
    kind: int
    module_id: int = 0
    module_name: str = "kernel"


class KrgGraph:
    """Minimal loader for the out.krg dependency graph."""

    _HEADER_V1 = struct.Struct("<8I")
    _HEADER_V2 = struct.Struct("<10I")
    _NODE_V1 = struct.Struct("<QIB3x")
    _NODE_V2 = struct.Struct("<QIHBx")

    def __init__(self, path: Path) -> None:
        data = path.read_bytes()
        self.path = path
        self.nodes: List[KrgResolvedSymbol] = []
        self.name_to_id: Dict[str, int] = {}
        self.node_count = 0
        self.row_ptr: List[int] = []
        self.col_idx: List[int] = []
        self.modules: List[str] = ["kernel"]
        self._load(memoryview(data))

    def _load(self, blob: memoryview) -> None:
        cursor = 0
        if len(blob) < self._HEADER_V1.size:
            raise ValueError(f"{self.path}: file too small for header")
        (
            magic,
            version,
            n_nodes,
            n_edges,
            name_blob_bytes,
            _arch,
            _is_runtime,
            _reserved,
        ) = self._HEADER_V1.unpack_from(blob, cursor)
        header_version = version
        n_modules = 1
        module_blob_bytes = 0
        if header_version >= 2:
            if len(blob) < self._HEADER_V2.size:
                raise ValueError(f"{self.path}: file too small for v2 header")
            (
                magic,
                version,
                n_nodes,
                n_edges,
                name_blob_bytes,
                _arch,
                _is_runtime,
                _reserved,
                n_modules,
                module_blob_bytes,
            ) = self._HEADER_V2.unpack_from(blob, 0)
            cursor = self._HEADER_V2.size
        else:
            cursor += self._HEADER_V1.size
        if magic != 0x3147524B or header_version not in (1, 2):
            raise ValueError(f"{self.path}: unsupported krg header")

        node_addresses: List[int] = []
        node_sizes: List[int] = []
        node_kinds: List[int] = []
        node_modules: List[int] = []
        node_struct = self._NODE_V2 if header_version >= 2 else self._NODE_V1
        self.node_count = n_nodes
        for _ in range(n_nodes):
            if cursor + node_struct.size > len(blob):
                raise ValueError(f"{self.path}: truncated node table")
            if header_version >= 2:
                addr, size, module_id, kind = node_struct.unpack_from(blob, cursor)
            else:
                addr, size, kind = node_struct.unpack_from(blob, cursor)
                module_id = 0
            cursor += node_struct.size
            node_addresses.append(addr)
            node_sizes.append(size)
            node_kinds.append(kind)
            node_modules.append(module_id)

        row_entries = n_nodes + 1
        row_ptr_size = row_entries * 4
        if cursor + row_ptr_size > len(blob):
            raise ValueError(f"{self.path}: truncated row_ptr table")
        if row_entries:
            self.row_ptr = list(struct.unpack_from(f"<{row_entries}I", blob, cursor))
        else:
            self.row_ptr = []
        cursor += row_ptr_size

        col_idx_size = n_edges * 4
        if cursor + col_idx_size > len(blob):
            raise ValueError(f"{self.path}: truncated col_idx table")
        if n_edges:
            self.col_idx = list(struct.unpack_from(f"<{n_edges}I", blob, cursor))
        else:
            self.col_idx = []
        cursor += col_idx_size

        name_off_size = n_nodes * 4
        if cursor + name_off_size > len(blob):
            raise ValueError(f"{self.path}: truncated name offsets")
        name_offsets = list(struct.unpack_from(f"<{n_nodes}I", blob, cursor))
        cursor += name_off_size

        if cursor + name_blob_bytes > len(blob):
            raise ValueError(f"{self.path}: truncated name blob")
        name_blob = bytes(blob[cursor : cursor + name_blob_bytes])
        cursor += name_blob_bytes

        modules: List[str] = ["kernel"]
        if header_version >= 2:
            module_offsets: List[int] = []
            if cursor + (n_modules * 4) > len(blob):
                raise ValueError(f"{self.path}: truncated module offsets")
            module_offsets = list(struct.unpack_from(f"<{n_modules}I", blob, cursor))
            cursor += n_modules * 4
            if cursor + module_blob_bytes > len(blob):
                raise ValueError(f"{self.path}: truncated module blob")
            module_blob = bytes(blob[cursor : cursor + module_blob_bytes])
            modules = []
            for off in module_offsets:
                if off >= len(module_blob):
                    raise ValueError(f"{self.path}: invalid module offset {off}")
                end = module_blob.find(b"\x00", off)
                if end == -1:
                    raise ValueError(f"{self.path}: unterminated module string at {off}")
                modules.append(module_blob[off:end].decode("utf-8", errors="ignore"))
        if not modules:
            modules = ["kernel"]
        self.modules = modules

        for idx, off in enumerate(name_offsets):
            if off >= len(name_blob):
                raise ValueError(f"{self.path}: invalid name offset {off}")
            end = name_blob.find(b"\x00", off)
            if end == -1:
                raise ValueError(f"{self.path}: unterminated string at offset {off}")
            name = name_blob[off:end].decode("utf-8", errors="ignore")
            module_name = "kernel"
            if node_modules[idx] < len(modules):
                module_name = modules[node_modules[idx]]
            self.nodes.append(
                KrgResolvedSymbol(
                    name=name,
                    address=node_addresses[idx],
                    size=node_sizes[idx],
                    kind=node_kinds[idx],
                    module_id=node_modules[idx],
                    module_name=module_name,
                )
            )
            self.name_to_id[name] = idx

    def closure(self, symbol_name: str) -> List[KrgResolvedSymbol]:
        try:
            root = self.name_to_id[symbol_name]
        except KeyError as exc:
            raise KeyError(f"{symbol_name}: symbol not found in {self.path}") from exc
        seen = [0] * self.node_count
        stack = [root]
        seen[root] = 1
        while stack:
            node = stack.pop()
            row_start = self.row_ptr[node]
            row_end = self.row_ptr[node + 1]
            for edge_idx in range(row_start, row_end):
                target = self.col_idx[edge_idx]
                if not seen[target]:
                    seen[target] = 1
                    stack.append(target)
        return [self.nodes[idx] for idx, flag in enumerate(seen) if flag]

    def lookup(self, symbol_name: str) -> KrgResolvedSymbol | None:
        idx = self.name_to_id.get(symbol_name)
        if idx is None:
            return None
        return self.nodes[idx]


# -----------------------------------------------------------------------------
# Symbol classification
# -----------------------------------------------------------------------------


@dataclass
class ResolvedSymbol:
    name: str
    source: str
    defined: bool
    st_type: int
    module_id: int = 0
    module_name: str = "kernel"
    exported: bool = False
    size: int = 0
    address: int = 0
    virtual_address: int = 0
    section_name: str | None = None
    export_order: int = 0
    original_order: int = 0
    dynsym_index: int = 0
    got_offset: int = 0
    gnu_hash_value: int = 0
    gnu_bucket: int = 0

    @property
    def is_import(self) -> bool:
        return not self.defined


def role_for_symbol(sym: ResolvedSymbol, owner_module: str) -> str:
    if sym.module_name == owner_module:
        return "export" if sym.exported else "internal"
    return "import"


def resolve_requested_symbols(
    requested_names: Sequence[str], graph: KrgGraph, shim_symbols: Set[str]
) -> tuple[List[ResolvedSymbol], List[str], str, str, List[str]]:
    """
    Resolve requested symbols by walking the krg dependency graph.
    Requested symbols become exports; symbols in the same module are defined, others are imports.

    Returns:
        (resolved_symbols, needed_libraries, owner_module_name, owner_library_name)
    """

    if not requested_names:
        raise ValueError("at least one symbol is required")

    export_order = {name: idx for idx, name in enumerate(requested_names)}
    resolved: Dict[str, ResolvedSymbol] = {}
    ordered: List[ResolvedSymbol] = []
    missing: List[str] = []
    needed_libs: List[str] = []
    dep_modules: List[str] = []
    owner_module: str | None = None

    def module_to_lib(module: str) -> str:
        if module == "kernel":
            return LIB_KERNEL
        if module == "shim":
            return LIB_SHIM
        return f"lib{module}.so"

    def module_for_entry(entry: KrgResolvedSymbol) -> str:
        if entry.name in shim_symbols:
            return "shim"
        return entry.module_name or "kernel"

    # Determine owning module from the first requested symbol and sanity check all exports
    first_lookup = graph.lookup(requested_names[0])
    if first_lookup is None:
        raise ValueError(f"{requested_names[0]}: symbol not found in {graph.path}")
    owner_module = module_for_entry(first_lookup)
    for name in requested_names:
        entry = graph.lookup(name)
        if entry is None:
            continue
        mod = module_for_entry(entry)
        if mod != owner_module:
            raise ValueError(f"export set crosses modules: {owner_module} vs {mod}")

    for name in requested_names:
        try:
            closure = graph.closure(name)
        except KeyError as exc:
            missing.append(name)
            print(str(exc), file=sys.stderr)
            continue
        if not closure:
            raise ValueError(f"{name}: empty dependency set returned by {graph.path}")
        for entry in closure:
            sym = resolved.get(entry.name)
            expected_type = STT_FUNC if entry.kind == 0 else STT_OBJECT
            module_name = module_for_entry(entry)
            lib_name = module_to_lib(module_name)
            is_export = entry.name in export_order
            is_owner_module = module_name == owner_module
            if sym is None:
                sym = ResolvedSymbol(
                    name=entry.name,
                    source=module_to_lib(owner_module or module_name) if is_owner_module else lib_name,
                    defined=is_owner_module,
                    exported=is_export,
                    st_type=expected_type,
                    size=entry.size,
                    address=entry.address,
                    export_order=export_order.get(entry.name, len(ordered)),
                    original_order=len(ordered),
                    module_id=entry.module_id,
                    module_name=module_name,
                )
                resolved[entry.name] = sym
                ordered.append(sym)
            else:
                if (
                    sym.address != entry.address
                    or sym.size != entry.size
                    or sym.st_type != expected_type
                    or sym.module_name != module_name
                ):
                    raise ValueError(
                        f"{entry.name}: inconsistent metadata between queries"
                    )
            if not is_owner_module:
                if lib_name not in needed_libs:
                    needed_libs.append(lib_name)
                if module_name not in dep_modules:
                    dep_modules.append(module_name)
        if name not in resolved:
            missing.append(name)
            print(f"{name}: symbol missing after resolution", file=sys.stderr)

    if missing and len(missing) == len(requested_names):
        raise ValueError(
            "None of the requested symbols were found; cannot build shared object"
        )
    owner_module = owner_module or "kernel"
    owner_lib = module_to_lib(owner_module)
    needed_libs = [lib for lib in needed_libs if lib != owner_lib]
    dep_modules = [m for m in dep_modules if m != owner_module]
    return ordered, needed_libs, owner_module, owner_lib, dep_modules


def dump_symbol_addresses_all(
    module_symbols: Sequence[tuple[str, Sequence[ResolvedSymbol]]], output_path: Path
) -> None:
    lines: List[str] = []
    for owner_module, symbols in module_symbols:
        for sym in symbols:
            lines.append(
                f"{sym.name},0x{sym.address:x},0x{sym.size:x},{sym.module_name},{role_for_symbol(sym, owner_module)}\n"
            )
    output_path.write_text("".join(lines))


def format_module_deps(
    owner_module: str, dep_modules: Sequence[str], symbols: Sequence[ResolvedSymbol]
) -> List[str]:
    dep_to_symbols: Dict[str, List[str]] = {}
    for sym in symbols:
        if sym.module_name == owner_module:
            continue
        dep_to_symbols.setdefault(sym.module_name, []).append(sym.name)
    lines: List[str] = []
    for mod in dep_modules:
        syms = dep_to_symbols.get(mod, [])
        sym_list = " ".join(sorted(set(syms)))
        lines.append(f"{owner_module} -> {mod}: {sym_list}\n")
    return lines


def dump_dep_symbol_lists(
    dep_modules: Sequence[str], symbols: Sequence[ResolvedSymbol], base_dir: Path
) -> None:
    for mod in dep_modules:
        names = sorted({sym.name for sym in symbols if sym.module_name == mod})
        if not names:
            continue
        target = base_dir / f"symbols_{mod}.txt"
        target.write_text("\n".join(names) + "\n")


# -----------------------------------------------------------------------------
# Manual ELF builder
# -----------------------------------------------------------------------------


@dataclass
class Region:
    name: str
    start: int
    end: int

    @property
    def size(self) -> int:
        return self.end - self.start


@dataclass
class SectionDef:
    name: str
    sh_type: int
    sh_flags: int
    align: int
    data: bytes = b""
    size: int | None = None
    link: int = 0
    info: int = 0
    entsize: int = 0
    offset: int | None = None
    addr: int | None = None

    @property
    def content_size(self) -> int:
        return self.size if self.size is not None else len(self.data)

    @property
    def is_alloc(self) -> bool:
        return bool(self.sh_flags & SHF_ALLOC)


class ManualElfBuilder:
    def __init__(
        self,
        symbols: List[ResolvedSymbol],
        needed_libraries: List[str],
        export_stub_size: int = DEFAULT_EXPORT_STUB_SIZE,
    ) -> None:
        self.symbols = symbols
        self.defined_symbols = [sym for sym in symbols if sym.defined]
        self.exports = [sym for sym in self.defined_symbols if sym.exported]
        self.imports = [sym for sym in symbols if sym.is_import]
        self.needed_libraries = needed_libraries
        self.export_stub_size = export_stub_size
        self.sections: Dict[str, SectionDef] = {}
        self.section_order: List[str] = []
        self.section_indices: Dict[str, int] = {}
        self.shstr_offsets: Dict[str, int] = {}
        self.dynstr_offsets: Dict[str, int] = {}
        self.dynstr_needed_offsets: Dict[str, int] = {}
        self.strtab_offsets: Dict[str, int] = {}
        self.dynamic_symbols: List[ResolvedSymbol] = list(self.symbols)
        self.gnu_nbuckets = max(3, len(self.dynamic_symbols)) if self.dynamic_symbols else 1
        self.gnu_bloom_size = max(1, (len(self.dynamic_symbols) + 63) // 64) if self.dynamic_symbols else 1
        self.gnu_bloom_shift = 6
        self.text_size = PAGE_SIZE
        self.section_headers_offset = 0
        self.text_regions: List[Region] = []
        self.text_section_names: List[str] = []
        self.ro_regions: List[Region] = []
        self.ro_section_names: List[str] = []
        self.region_by_name: Dict[str, Region] = {}
        self.rw_segment_start_offset = 0
        self.rw_segment_start_addr = 0
        self.rw_segment_file_end = 0
        self.rw_segment_mem_end = 0
        self.text_min_page = TEXT_BASE_VADDR

    # ------------------------------------------------------------------
    # Top-level write
    # ------------------------------------------------------------------

    def write(self, output_path: Path) -> None:
        self._prepare_symbol_virtual_addresses()
        self._derive_section_order()
        self._reorder_symbols_for_hash()
        self._build_content_sections()
        self._assign_offsets_and_addresses()
        self.build_got_and_relocs()
        self._finalize_dynamic_section()
        ph_entries = self._build_program_headers()
        with open(output_path, "wb") as f:
            self._write_elf_header(f, len(ph_entries))
            f.seek(64)
            for ph in ph_entries:
                f.write(ph)
            for name in self.section_order:
                section = self.sections[name]
                if section.sh_type == SHT_NOBITS or section.content_size == 0:
                    continue
                if section.data:
                    f.seek(section.offset)
                    f.write(section.data)
            f.seek(self.section_headers_offset)
            f.write(bytes(64))
            for name in self.section_order:
                section = self.sections[name]
                sh_name = self.shstr_offsets.get(name, 0)
                shdr = struct.pack(
                    "<IIQQQQIIQQ",
                    sh_name,
                    section.sh_type,
                    section.sh_flags,
                    section.addr or 0,
                    section.offset or 0,
                    section.content_size,
                    section.link,
                    section.info,
                    section.align,
                    section.entsize,
                )
                f.write(shdr)
            total_size = self.section_headers_offset + (len(self.section_order) + 1) * 64
            f.truncate(total_size)

    # ------------------------------------------------------------------
    # Preparation steps
    # ------------------------------------------------------------------

    def _prepare_symbol_virtual_addresses(self) -> None:
        code_symbols = [sym for sym in self.defined_symbols if sym.st_type == STT_FUNC]
        ro_symbols = [sym for sym in self.defined_symbols if sym.st_type == STT_OBJECT]

        cursor = TEXT_BASE_VADDR
        for sym in self.defined_symbols:
            if sym.size == 0:
                sym.size = self.export_stub_size
            if sym.address == 0:
                sym.address = cursor
                cursor += self.export_stub_size

        overall_min_page = (
            align_down(min(sym.address for sym in self.defined_symbols), PAGE_SIZE)
            if self.defined_symbols
            else TEXT_BASE_VADDR
        )
        if code_symbols:
            self.text_min_page = align_down(min(sym.address for sym in code_symbols), PAGE_SIZE)
        else:
            self.text_min_page = overall_min_page

        for sym in self.defined_symbols:
            sym.virtual_address = TEXT_BASE_VADDR + (sym.address - self.text_min_page)

        self.region_by_name.clear()
        self.text_regions = self._build_regions(code_symbols, ".text")
        self.ro_regions = self._build_regions(ro_symbols, ".rodata")
        for region in self.text_regions + self.ro_regions:
            self.region_by_name[region.name] = region
        self.text_section_names = [region.name for region in self.text_regions]
        self.ro_section_names = [region.name for region in self.ro_regions]
        self._assign_symbol_sections(code_symbols, self.text_regions)
        self._assign_symbol_sections(ro_symbols, self.ro_regions)

    def _build_regions(self, symbols: List[ResolvedSymbol], base_name: str) -> List[Region]:
        if not symbols:
            return []
        intervals: List[tuple[int, int]] = []
        for sym in symbols:
            size = max(sym.size, 1)
            start = align_down(sym.address, PAGE_SIZE)
            end = align(sym.address + size, PAGE_SIZE)
            if end == start:
                end += PAGE_SIZE
            intervals.append((start, end))
        intervals.sort()
        merged: List[List[int]] = []
        for start, end in intervals:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        regions: List[Region] = []
        if len(merged) == 1:
            names = [base_name]
        else:
            names = [f"{base_name}{idx + 1}" for idx in range(len(merged))]
        for name, bounds in zip(names, merged):
            start, end = bounds
            region = Region(name=name, start=start, end=end)
            regions.append(region)
            self.region_by_name[name] = region
        return regions

    def _assign_symbol_sections(
        self, symbols: List[ResolvedSymbol], regions: List[Region]
    ) -> None:
        if not symbols:
            return
        for sym in symbols:
            region = self._find_region_for_address(sym.address, regions)
            if region is None:
                raise ValueError(f"{sym.name}: no region covers address 0x{sym.address:x}")
            sym.section_name = region.name

    @staticmethod
    def _find_region_for_address(address: int, regions: List[Region]) -> Region | None:
        for region in regions:
            if region.start <= address < region.end:
                return region
        return None

    def _derive_section_order(self) -> None:
        order: List[str] = []
        order.extend(self.text_section_names)
        order.extend(
            [
                ".dynstr",
                ".dynsym",
                ".gnu.hash",
                ".rela.dyn",
                ".dynamic",
                ".got",
                ".strtab",
                ".symtab",
                ".shstrtab",
            ]
        )
        self.section_order = order
        names_with_null = [".null"] + order
        self.section_indices = {name: idx for idx, name in enumerate(names_with_null)}

    def _reorder_symbols_for_hash(self) -> None:
        for sym in self.dynamic_symbols:
            sym.gnu_hash_value = gnu_hash(sym.name)
            sym.gnu_bucket = sym.gnu_hash_value % self.gnu_nbuckets
        self.dynamic_symbols.sort(
            key=lambda sym: (
                sym.gnu_bucket,
                0 if sym.defined else 1,
                sym.export_order,
                sym.original_order,
            )
        )

    # ------------------------------------------------------------------

    def _build_content_sections(self) -> None:
        for region in self.text_regions:
            self.sections[region.name] = SectionDef(
                name=region.name,
                sh_type=SHT_PROGBITS,
                sh_flags=SHF_ALLOC | SHF_EXECINSTR,
                align=PAGE_SIZE,
                data=b"",
                size=region.size,
            )
        for region in self.ro_regions:
            self.sections[region.name] = SectionDef(
                name=region.name,
                sh_type=SHT_PROGBITS,
                sh_flags=SHF_ALLOC,
                align=PAGE_SIZE,
                data=b"",
                size=region.size,
            )
        dynstr = self._build_dynstr()
        dynsym = self._build_dynsym()
        gnu_hash_data = self._build_gnu_hash()
        rela_size = len(self.imports) * 24
        dynamic_guess_entries = len(self.needed_libraries) + 10
        self.sections[".dynstr"] = SectionDef(
            name=".dynstr",
            sh_type=SHT_STRTAB,
            sh_flags=SHF_ALLOC,
            align=1,
            data=dynstr,
        )
        self.sections[".dynsym"] = SectionDef(
            name=".dynsym",
            sh_type=SHT_DYNSYM,
            sh_flags=SHF_ALLOC,
            align=8,
            data=dynsym,
            link=self.section_indices[".dynstr"],
            info=1,
            entsize=24,
        )
        self.sections[".gnu.hash"] = SectionDef(
            name=".gnu.hash",
            sh_type=SHT_GNU_HASH,
            sh_flags=SHF_ALLOC,
            align=8,
            data=gnu_hash_data,
            link=self.section_indices[".dynsym"],
        )
        self.sections[".rela.dyn"] = SectionDef(
            name=".rela.dyn",
            sh_type=SHT_RELA,
            sh_flags=SHF_ALLOC,
            align=8,
            data=bytes(rela_size),
            size=rela_size,
            link=self.section_indices[".dynsym"],
            info=0,
            entsize=24,
        )
        self.sections[".dynamic"] = SectionDef(
            name=".dynamic",
            sh_type=SHT_DYNAMIC,
            sh_flags=SHF_ALLOC | SHF_WRITE,
            align=8,
            data=bytes(dynamic_guess_entries * 16),
            entsize=16,
            link=self.section_indices[".dynstr"],
        )
        self.sections[".got"] = SectionDef(
            name=".got",
            sh_type=SHT_PROGBITS,
            sh_flags=SHF_ALLOC | SHF_WRITE,
            align=8,
            data=bytes(len(self.imports) * 8),
            size=len(self.imports) * 8,
        )
        strtab = self._build_strtab()
        symtab = self._build_symtab()
        self.sections[".strtab"] = SectionDef(
            name=".strtab",
            sh_type=SHT_STRTAB,
            sh_flags=0,
            align=1,
            data=strtab,
        )
        self.sections[".symtab"] = SectionDef(
            name=".symtab",
            sh_type=SHT_SYMTAB,
            sh_flags=0,
            align=8,
            data=symtab,
            link=self.section_indices[".strtab"],
            info=1,
            entsize=24,
        )
        shstrtab = self._build_shstrtab()
        self.sections[".shstrtab"] = SectionDef(
            name=".shstrtab",
            sh_type=SHT_STRTAB,
            sh_flags=0,
            align=1,
            data=shstrtab,
        )

    # ------------------------------------------------------------------

    def _build_dynstr(self) -> bytes:
        data = bytearray(b"\x00")
        for sym in self.dynamic_symbols:
            if sym.name not in self.dynstr_offsets:
                self.dynstr_offsets[sym.name] = len(data)
                data.extend(sym.name.encode("ascii") + b"\x00")
        for lib in self.needed_libraries:
            if lib not in self.dynstr_offsets:
                self.dynstr_offsets[lib] = len(data)
                data.extend(lib.encode("ascii") + b"\x00")
            self.dynstr_needed_offsets[lib] = self.dynstr_offsets[lib]
        return bytes(data)

    def _build_dynsym(self) -> bytes:
        entries = [self._pack_sym_entry(0, STT_NOTYPE, SHN_UNDEF, 0, 0, 0)]
        for idx, sym in enumerate(self.dynamic_symbols, start=1):
            st_name = self.dynstr_offsets[sym.name]
            st_info = (STB_GLOBAL << 4) | sym.st_type
            st_shndx = self.section_indices.get(sym.section_name, SHN_UNDEF)
            entries.append(
                self._pack_sym_entry(
                    st_name=st_name,
                    st_type=st_info,
                    st_shndx=st_shndx,
                    st_value=sym.virtual_address if sym.defined else 0,
                    st_size=sym.size,
                )
            )
            sym.dynsym_index = idx
        return b"".join(entries)

    def _build_gnu_hash(self) -> bytes:
        if not self.dynamic_symbols:
            return b""
        first_sym = 1
        symbol_count = len(self.dynamic_symbols)
        bloom = [0] * self.gnu_bloom_size
        buckets = [0] * self.gnu_nbuckets
        chains = [0] * symbol_count
        prev_bucket = None
        last_index = None
        for dyn_index, sym in enumerate(self.dynamic_symbols, start=first_sym):
            h = sym.gnu_hash_value
            bucket_idx = sym.gnu_bucket
            word = (h // 64) % self.gnu_bloom_size
            bitmask = (1 << (h % 64)) | (1 << ((h >> self.gnu_bloom_shift) % 64))
            bloom[word] |= bitmask
            if buckets[bucket_idx] == 0:
                buckets[bucket_idx] = dyn_index
                if prev_bucket is not None and last_index is not None:
                    chains[last_index - first_sym] |= 1
            elif bucket_idx != prev_bucket and prev_bucket is not None and last_index is not None:
                chains[last_index - first_sym] |= 1
            chains[dyn_index - first_sym] = h & ~1
            prev_bucket = bucket_idx
            last_index = dyn_index
        if last_index is not None:
            chains[last_index - first_sym] |= 1
        payload = bytearray()
        payload.extend(
            struct.pack(
                "<IIII",
                self.gnu_nbuckets,
                first_sym,
                self.gnu_bloom_size,
                self.gnu_bloom_shift,
            )
        )
        for word in bloom:
            payload.extend(struct.pack("<Q", word))
        for bucket in buckets:
            payload.extend(struct.pack("<I", bucket))
        for chain in chains:
            payload.extend(struct.pack("<I", chain))
        return bytes(payload)

    def _build_strtab(self) -> bytes:
        data = bytearray(b"\x00")
        for sym in self.symbols:
            if sym.name not in self.strtab_offsets:
                self.strtab_offsets[sym.name] = len(data)
                data.extend(sym.name.encode("ascii") + b"\x00")
        return bytes(data)

    def _build_symtab(self) -> bytes:
        entries = [self._pack_sym_entry(0, STT_NOTYPE, SHN_UNDEF, 0, 0, 0)]
        for sym in self.symbols:
            st_name = self.strtab_offsets[sym.name]
            st_info = (STB_GLOBAL << 4) | sym.st_type
            st_shndx = self.section_indices.get(sym.section_name, SHN_UNDEF)
            entries.append(
                self._pack_sym_entry(
                    st_name=st_name,
                    st_type=st_info,
                    st_shndx=st_shndx,
                    st_value=sym.virtual_address if sym.defined else 0,
                    st_size=sym.size,
                )
            )
        return b"".join(entries)

    def _build_shstrtab(self) -> bytes:
        names = [""]
        names.extend(self.section_order)
        data = bytearray()
        for name in names:
            self.shstr_offsets[name] = len(data)
            data.extend(name.encode("ascii") + b"\x00")
        return bytes(data)

    # ------------------------------------------------------------------

    def _assign_offsets_and_addresses(self) -> None:
        current_offset = TEXT_BASE_OFFSET
        text_end_addr = TEXT_BASE_VADDR
        for idx, name in enumerate(self.text_section_names):
            section = self.sections[name]
            if idx == 0:
                section.offset = TEXT_BASE_OFFSET
            else:
                current_offset = align(current_offset, PAGE_SIZE)
                section.offset = current_offset
            region = self.region_by_name[name]
            section.addr = TEXT_BASE_VADDR + (region.start - self.text_min_page)
            current_offset = section.offset + section.content_size
            text_end_addr = max(text_end_addr, section.addr + section.content_size)

        ro_end_addr = text_end_addr
        for name in self.ro_section_names:
            section = self.sections[name]
            current_offset = align(current_offset, PAGE_SIZE)
            section.offset = current_offset
            region = self.region_by_name[name]
            section.addr = TEXT_BASE_VADDR + (region.start - self.text_min_page)
            current_offset += section.content_size
            ro_end_addr = max(ro_end_addr, section.addr + section.content_size)

        last_alloc_addr = ro_end_addr if self.ro_section_names else text_end_addr

        rw_sections = [
            name
            for name in self.section_order
            if self.sections[name].is_alloc
            and name not in self.text_section_names
            and name not in self.ro_section_names
        ]

        cursor_offset = align(current_offset, PAGE_SIZE)
        cursor_addr = align(last_alloc_addr, PAGE_SIZE)

        rw_start_offset: int | None = None
        rw_start_addr: int | None = None

        for name in rw_sections:
            section = self.sections[name]
            cursor_offset = align(cursor_offset, max(1, section.align))
            cursor_addr = align(cursor_addr, max(1, section.align))
            if rw_start_offset is None:
                rw_start_offset = cursor_offset
                rw_start_addr = cursor_addr
            section.offset = cursor_offset
            section.addr = cursor_addr
            cursor_offset += section.content_size
            cursor_addr += section.content_size

        if rw_start_offset is None:
            self.rw_segment_start_offset = 0
            self.rw_segment_start_addr = 0
            self.rw_segment_file_end = cursor_offset
            self.rw_segment_mem_end = cursor_addr
        else:
            self.rw_segment_start_offset = rw_start_offset
            self.rw_segment_start_addr = rw_start_addr or 0
            self.rw_segment_file_end = cursor_offset
            self.rw_segment_mem_end = cursor_addr

        non_alloc_cursor = cursor_offset
        for name in [".strtab", ".symtab", ".shstrtab"]:
            section = self.sections[name]
            non_alloc_cursor = align(non_alloc_cursor, max(1, section.align))
            section.offset = non_alloc_cursor
            section.addr = 0
            non_alloc_cursor += section.content_size

        self.section_headers_offset = align(non_alloc_cursor, 8)

    # ------------------------------------------------------------------
    # GOT/RELA and dynamic finalization
    # ------------------------------------------------------------------

    def build_got_and_relocs(self) -> None:
        got_sec = self.sections[".got"]
        rela_sec = self.sections[".rela.dyn"]
        if not self.imports:
            rela_sec.data = b""
            rela_sec.size = 0
            got_sec.data = b""
            got_sec.size = 0
            got_sec.offset = 0
            got_sec.addr = 0
            return
        rela_entries: List[bytes] = []
        for idx, sym in enumerate(self.imports):
            sym.got_offset = idx * 8
            r_offset = (got_sec.addr or 0) + sym.got_offset
            r_info = (sym.dynsym_index << 32) | R_X86_64_GLOB_DAT
            rela_entries.append(struct.pack("<QQq", r_offset, r_info, 0))
        rela_sec.data = b"".join(rela_entries)
        rela_sec.size = len(rela_sec.data)
        if not got_sec.data:
            got_sec.data = bytes(got_sec.content_size)
        got_sec.size = got_sec.content_size

    def _finalize_dynamic_section(self) -> None:
        dynamic = self.sections[".dynamic"]
        entries: List[tuple[int, int]] = []
        for lib in self.needed_libraries:
            entries.append((DT_NEEDED, self.dynstr_needed_offsets[lib]))
        entries.extend(
            [
                (DT_GNU_HASH, self.sections[".gnu.hash"].addr or 0),
                (DT_STRTAB, self.sections[".dynstr"].addr or 0),
                (DT_SYMTAB, self.sections[".dynsym"].addr or 0),
                (DT_RELA, self.sections[".rela.dyn"].addr or 0),
                (DT_RELASZ, self.sections[".rela.dyn"].content_size),
                (DT_RELAENT, 24),
                (DT_STRSZ, self.sections[".dynstr"].content_size),
                (DT_SYMENT, 24),
                (DT_NULL, 0),
            ]
        )
        got_sec = self.sections[".got"]
        if got_sec.content_size:
            entries.insert(
                -1,
                (DT_PLTGOT, got_sec.addr or 0),
            )
        payload = bytearray()
        for tag, value in entries:
            payload.extend(struct.pack("<QQ", tag, value))
        dynamic.data = bytes(payload)
        dynamic.size = len(dynamic.data)

    # ------------------------------------------------------------------

    def _build_program_headers(self) -> List[bytes]:
        entries: List[bytes] = []
        for name in self.text_section_names:
            section = self.sections[name]
            entries.append(
                self._make_ph_load(
                    offset=section.offset or 0,
                    addr=section.addr or 0,
                    size=section.content_size,
                    flags=PF_R | PF_X,
                )
            )
        for name in self.ro_section_names:
            section = self.sections[name]
            entries.append(
                self._make_ph_load(
                    offset=section.offset or 0,
                    addr=section.addr or 0,
                    size=section.content_size,
                    flags=PF_R,
                )
            )
        if self.rw_segment_file_end > self.rw_segment_start_offset:
            entries.append(
                self._make_ph_load(
                    offset=self.rw_segment_start_offset,
                    addr=self.rw_segment_start_addr,
                    size=self.rw_segment_mem_end - self.rw_segment_start_addr,
                    flags=PF_R | PF_W,
                )
            )
        entries.append(self._make_ph_dynamic())
        return entries

    def _make_ph_load(self, offset: int, addr: int, size: int, flags: int) -> bytes:
        return struct.pack(
            "<IIQQQQQQ",
            PT_LOAD,
            flags,
            offset,
            addr,
            addr,
            size,
            size,
            PAGE_SIZE,
        )

    def _make_ph_dynamic(self) -> bytes:
        dynamic = self.sections[".dynamic"]
        return struct.pack(
            "<IIQQQQQQ",
            PT_DYNAMIC,
            PF_R | PF_W,
            dynamic.offset or 0,
            dynamic.addr or 0,
            dynamic.addr or 0,
            dynamic.content_size,
            dynamic.content_size,
            8,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _pack_sym_entry(
        st_name: int,
        st_type: int,
        st_shndx: int,
        st_value: int,
        st_size: int,
        st_other: int = 0,
    ) -> bytes:
        return struct.pack(
            "<IBBHQQ",
            st_name,
            st_type,
            st_other,
            st_shndx,
            st_value,
            st_size,
        )

    def _write_elf_header(self, f, ph_count: int) -> None:
        e_ident = bytearray(EI_NIDENT)
        e_ident[0:4] = b"\x7fELF"
        e_ident[4] = ELFCLASS64
        e_ident[5] = ELFDATA2LSB
        e_ident[6] = EV_CURRENT
        e_ident[7] = 0
        e_ident[8] = 0
        ehdr = struct.pack(
            "<16sHHIQQQIHHHHHH",
            bytes(e_ident),
            ET_DYN,
            EM_X86_64,
            EV_CURRENT,
            TEXT_BASE_VADDR,
            64,
            self.section_headers_offset,
            0,
            64,
            56,
            ph_count,
            64,
            len(self.section_order) + 1,
            self.section_indices[".shstrtab"],
        )
        f.write(ehdr)


# -----------------------------------------------------------------------------
# CLI glue
# -----------------------------------------------------------------------------


def infer_default_krg_path() -> Path | None:
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        candidate = parent / "KernelCodeMappingFinal/kernel-cgd/src/out.krg"
        if candidate.exists():
            return candidate
    return None


def build_shared_object(
    symbols_path: Path,
    krg_path: Path,
    export_stub_size: int = DEFAULT_EXPORT_STUB_SIZE,
    symbol_dump_path: Path | None = None,
    shim_list_path: Path | None = None,
) -> None:
    graph = KrgGraph(krg_path)
    shim_symbols = load_shim_symbols(shim_list_path)
    pending: List[tuple[str | None, List[str]]] = [(None, parse_symbol_requests(symbols_path))]
    built: Set[str] = set()
    dep_lines: List[str] = []
    all_symbol_groups: List[tuple[str, List[ResolvedSymbol]]] = []

    while pending:
        _, sym_names = pending.pop(0)
        resolved, needed_libs, owner_module, owner_lib, dep_modules = resolve_requested_symbols(
            sym_names, graph, shim_symbols
        )
        if owner_module in built:
            continue
        built.add(owner_module)
        out_so = Path(owner_lib)
        all_symbol_groups.append((owner_module, resolved))
        dep_lines.extend(format_module_deps(owner_module, dep_modules, resolved))
        builder = ManualElfBuilder(
            symbols=resolved,
            needed_libraries=needed_libs,
            export_stub_size=export_stub_size,
        )
        builder.write(out_so)
        for mod in dep_modules:
            if mod in built:
                continue
            if any(item[0] == mod for item in pending):
                continue
            if mod == "shim":
                continue
            dep_syms = sorted({sym.name for sym in resolved if sym.module_name == mod})
            if dep_syms:
                pending.append((mod, dep_syms))

    if dep_lines:
        module_deps_path = symbols_path.parent / "module_deps.txt"
        module_deps_path.write_text("".join(dep_lines))
    if symbol_dump_path is not None and all_symbol_groups:
        dump_symbol_addresses_all(all_symbol_groups, symbol_dump_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a GOT-only shared object (libA.so)")
    parser.add_argument("--symbols", type=Path, default=Path("symbols.txt"), help="List of root symbols to export")
    parser.add_argument(
        "--symbol-addresses",
        type=Path,
        default=Path("resolved_symbol_addresses.txt"),
        help="Where to write resolved symbol_name,address,size (default: resolved_symbol_addresses.txt)",
    )
    parser.add_argument(
        "--skip-symbol-addresses",
        action="store_true",
        help="Disable writing the resolved symbol address dump",
    )
    parser.add_argument(
        "--krg",
        type=Path,
        default=None,
        help="Path to out.krg for kernel symbol resolution",
    )
    parser.add_argument(
        "--export-stub-size",
        type=lambda x: int(x, 0),
        default=DEFAULT_EXPORT_STUB_SIZE,
        help="Logical size reserved for any zero-sized resolved symbols in ghost .text",
    )
    parser.add_argument(
        "--shim-list",
        type=Path,
        default=Path("shim.txt"),
        help="Optional file listing shim-provided symbols (defaults to builtin list)",
    )
    args = parser.parse_args()
    krg_path = args.krg
    if krg_path is None:
        krg_path = infer_default_krg_path()
        if krg_path is None:
            parser.error("Unable to locate out.krg automatically; provide --krg")
    if not krg_path.exists():
        parser.error(f"{krg_path} does not exist")
    symbol_dump_path = None if args.skip_symbol_addresses else args.symbol_addresses
    build_shared_object(
        symbols_path=args.symbols,
        krg_path=krg_path,
        export_stub_size=args.export_stub_size,
        symbol_dump_path=symbol_dump_path,
        shim_list_path=args.shim_list,
    )


if __name__ == "__main__":
    main()
