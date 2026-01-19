#!/usr/bin/env python3
"""
Manual ELF64 shared library builder (Sparse Edition).

This tool reads `symbols.txt`, remaps the provided kernel symbols into a
synthetic address space, and emits a minimal yet linkable ELF shared object.

CHANGES:
- Uses sparse file techniques (lseek) for .text and .rodata sections.
- Physical disk usage is minimal, while logical size matches kernel mapping requirements.
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set

# -----------------------------------------------------------------------------
# Basic ELF constants
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
SHT_DYNAMIC = 6
SHT_NOBITS = 8
SHT_DYNSYM = 11
SHT_GNU_HASH = 0x6ffffff6

SHF_WRITE = 0x1
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4

SHN_UNDEF = 0

STB_GLOBAL = 1
STT_NOTYPE = 0
STT_OBJECT = 1
STT_FUNC = 2

DT_NULL = 0
DT_GNU_HASH = 0x6ffffef5
DT_STRTAB = 5
DT_SYMTAB = 6
DT_STRSZ = 10
DT_SYMENT = 11

# -----------------------------------------------------------------------------
# Layout configuration
# -----------------------------------------------------------------------------

PAGE_SIZE = 0x1000
TEXT_BASE_VADDR = 0x1000
TEXT_BASE_OFFSET = 0x1000

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------


def align(value: int, alignment: int) -> int:
    if alignment == 0:
        return value
    return (value + alignment - 1) & ~(alignment - 1)


def align_down(value: int, alignment: int) -> int:
    if alignment == 0:
        return value
    return value & ~(alignment - 1)


def gnu_hash(name: str) -> int:
    h = 5381
    for ch in name:
        h = ((h * 33) + ord(ch)) & 0xFFFFFFFF
    return h


@dataclass
class Symbol:
    name: str
    elf_name: str
    address: int
    size: int
    kind: int
    exported: bool = False
    export_order: int | None = None
    section_name: str | None = None
    virtual_address: int = 0
    dynsym_index: int = 0
    original_order: int = 0
    gnu_hash_value: int = 0
    gnu_bucket: int = 0


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


def parse_symbol_requests(path: Path) -> List[str]:
    names: List[str] = []
    seen: Set[str] = set()
    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        token = line.split()[0]
        if not token:
            continue
        if token in seen:
            continue
        seen.add(token)
        names.append(token)
    if not names:
        raise ValueError(f"{path}: no symbol names provided")
    return names


@dataclass(frozen=True)
class KrgResolvedSymbol:
    name: str
    address: int
    size: int
    kind: int


class KrgGraph:
    """Minimal loader for the out.krg dependency graph."""

    _HEADER_STRUCT = struct.Struct("<8I")
    _NODE_STRUCT = struct.Struct("<QIB3x")

    def __init__(self, path: Path) -> None:
        data = path.read_bytes()
        self.path = path
        self._load(memoryview(data))

    def _load(self, blob: memoryview) -> None:
        cursor = 0
        if len(blob) < self._HEADER_STRUCT.size:
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
        ) = self._HEADER_STRUCT.unpack_from(blob, cursor)
        cursor += self._HEADER_STRUCT.size
        if magic != 0x3147524B or version != 1:
            raise ValueError(f"{self.path}: unsupported krg header")

        self.node_count = n_nodes
        node_addresses: List[int] = []
        node_sizes: List[int] = []
        node_kinds: List[int] = []
        for _ in range(n_nodes):
            if cursor + self._NODE_STRUCT.size > len(blob):
                raise ValueError(f"{self.path}: truncated node table")
            addr, size, kind = self._NODE_STRUCT.unpack_from(blob, cursor)
            cursor += self._NODE_STRUCT.size
            node_addresses.append(addr)
            node_sizes.append(size)
            node_kinds.append(kind)

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
        if n_nodes:
            name_offsets = list(struct.unpack_from(f"<{n_nodes}I", blob, cursor))
        else:
            name_offsets = []
        cursor += name_off_size

        if cursor + name_blob_bytes > len(blob):
            raise ValueError(f"{self.path}: truncated name blob")
        name_blob = bytes(blob[cursor : cursor + name_blob_bytes])

        if len(name_offsets) != len(node_addresses):
            raise ValueError(f"{self.path}: node/name count mismatch")
        self.nodes: List[KrgResolvedSymbol] = []
        self.name_to_id: Dict[str, int] = {}
        for idx, off in enumerate(name_offsets):
            if off >= len(name_blob):
                raise ValueError(f"{self.path}: invalid name offset {off}")
            end = name_blob.find(b"\x00", off)
            if end == -1:
                raise ValueError(f"{self.path}: unterminated string at offset {off}")
            name = name_blob[off:end].decode("utf-8", errors="ignore")
            self.nodes.append(
                KrgResolvedSymbol(
                    name=name,
                    address=node_addresses[idx],
                    size=node_sizes[idx],
                    kind=node_kinds[idx],
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


def resolve_requested_symbols(
    requested_names: Sequence[str], graph: KrgGraph
) -> List[Symbol]:
    if not requested_names:
        raise ValueError("at least one symbol is required")

    export_order = {name: idx for idx, name in enumerate(requested_names)}
    resolved: Dict[str, Symbol] = {}
    ordered: List[Symbol] = []
    missing: List[str] = []

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
            if sym is None:
                exported = entry.name in export_order
                sym = Symbol(
                    name=entry.name,
                    elf_name=entry.name,
                    address=entry.address,
                    size=entry.size,
                    kind=entry.kind,
                    exported=exported,
                    export_order=export_order.get(entry.name),
                )
                sym.original_order = len(ordered)
                resolved[entry.name] = sym
                ordered.append(sym)
            else:
                if (
                    sym.address != entry.address
                    or sym.size != entry.size
                    or sym.kind != entry.kind
                ):
                    raise ValueError(
                        f"{entry.name}: inconsistent metadata between queries"
                    )
        if name not in resolved:
            missing.append(name)
            print(
                f"{name}: symbol missing after resolution", file=sys.stderr
            )

    if missing and len(missing) == len(requested_names):
        raise ValueError(
            "None of the requested symbols were found; cannot build shared object"
        )
    return ordered


def infer_default_krg_path() -> Path | None:
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        candidate = parent / "KernelCodeMappingFinal/kernel-cgd/src/out.krg"
        if candidate.exists():
            return candidate
    return None


class ManualElfBuilder:
    def __init__(self, symbols: List[Symbol]):
        self.symbols = symbols
        self.exported_symbols = [sym for sym in self.symbols if sym.exported]
        self.sections: Dict[str, SectionDef] = {}
        self.text_min_page = 0
        self.dynstr_offsets: Dict[str, int] = {}
        self.strtab_offsets: Dict[str, int] = {}
        self.shstr_offsets: Dict[str, int] = {}
        self.section_order: List[str] = []
        self.section_indices: Dict[str, int] = {}
        self.rw_segment_start_offset = 0
        self.rw_segment_start_addr = 0
        self.rw_segment_file_end = 0
        self.rw_segment_mem_end = 0
        self.section_headers_offset = 0
        self.symbol_count = len(self.exported_symbols)
        if self.symbol_count:
            self.gnu_nbuckets = max(3, self.symbol_count)
            self.gnu_bloom_size = max(1, (self.symbol_count + 63) // 64)
        else:
            self.gnu_nbuckets = 1
            self.gnu_bloom_size = 1
        self.gnu_bloom_shift = 6
        self.dynamic_symbols: List[Symbol] = []
        self.text_regions: List[Region] = []
        self.ro_regions: List[Region] = []
        self.region_by_name: Dict[str, Region] = {}
        self.text_section_names: List[str] = []
        self.ro_section_names: List[str] = []

    def write(self, output_path: Path) -> None:
        """Calculates layout and writes the sparse ELF image directly to disk."""
        self._prepare_symbol_virtual_addresses()
        self._derive_section_order()
        self._reorder_symbols_for_hash()
        self._build_content_sections()
        self._assign_offsets_and_addresses()
        self._finalize_dynamic_section()
        
        # Open file in binary write mode
        with open(output_path, "wb") as f:
            # 1. Write ELF Header and Program Headers (Always at start)
            ph_entries = self._build_program_headers()
            
            # Write ELF Header (Offset 0)
            f.seek(0)
            self._write_elf_header_to_file(f, len(ph_entries))
            
            # Write Program Headers (Immediately following ELF Header usually)
            f.seek(64)
            for ph in ph_entries:
                f.write(ph)

            # 2. Write Sections (Sparse-aware)
            # We iterate through sections. If a section has data, we seek and write.
            # If it is sparse (data is empty but size > 0), we DO NOT write.
            # We rely on the seek for the NEXT section to create the hole.
            for name in self.section_order:
                section = self._section(name)
                if section.sh_type == SHT_NOBITS:
                    continue
                
                # Check if we have actual data to write
                if len(section.data) > 0:
                    f.seek(section.offset)
                    f.write(section.data)
                
                # If len(section.data) == 0 but section.size > 0, it's a sparse hole.
                # We simply do nothing. The next f.seek() will jump over it.

            # 3. Write Section Headers (At the end)
            f.seek(self.section_headers_offset)
            # Write null section header
            f.write(bytes(64))
            
            for name in self.section_order:
                section = self._section(name)
                sh_name = self._shstr_offset(name)
                shdr = struct.pack(
                    "<IIQQQQIIQQ",
                    sh_name,
                    section.sh_type,
                    section.sh_flags,
                    section.addr or 0,
                    section.offset,
                    section.content_size,
                    section.link,
                    section.info,
                    section.align,
                    section.entsize,
                )
                f.write(shdr)
            
            # 4. Final Truncate
            # Ensure the file reports the correct size even if the last write
            # wasn't at the very end (though SHDRs are usually last).
            total_size = self.section_headers_offset + (len(self.section_order) + 1) * 64
            f.truncate(total_size)

    # ------------------------------------------------------------------
    # Symbol preparation
    # ------------------------------------------------------------------

    def _prepare_symbol_virtual_addresses(self) -> None:
        code_symbols = [sym for sym in self.symbols if sym.kind == 0]
        ro_symbols = [sym for sym in self.symbols if sym.kind == 1]
        overall_min_page = (
            align_down(min(sym.address for sym in self.symbols), PAGE_SIZE)
            if self.symbols
            else 0
        )

        if code_symbols:
            self.text_min_page = align_down(
                min(sym.address for sym in code_symbols), PAGE_SIZE
            )
        else:
            self.text_min_page = overall_min_page

        for sym in self.symbols:
            sym.virtual_address = TEXT_BASE_VADDR + (sym.address - self.text_min_page)

        self.region_by_name.clear()
        self.text_regions = self._build_regions(code_symbols, ".text")
        self.ro_regions = self._build_regions(ro_symbols, ".rodata")
        self.text_section_names = [region.name for region in self.text_regions]
        self.ro_section_names = [region.name for region in self.ro_regions]
        self._assign_symbol_sections(code_symbols, self.text_regions)
        self._assign_symbol_sections(ro_symbols, self.ro_regions)

    def _build_regions(self, symbols: List[Symbol], base_name: str) -> List[Region]:
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
        self, symbols: List[Symbol], regions: List[Region]
    ) -> None:
        if not symbols:
            return
        for sym in symbols:
            region = self._find_region_for_address(sym.address, regions)
            if region is None:
                raise ValueError(
                    f"{sym.name}: no region covers address 0x{sym.address:x}"
                )
            sym.section_name = region.name

    @staticmethod
    def _find_region_for_address(
        address: int, regions: List[Region]
    ) -> Region | None:
        for region in regions:
            if region.start <= address < region.end:
                return region
        return None

    def _derive_section_order(self) -> None:
        order: List[str] = []
        order.extend(self.text_section_names)
        order.extend(self.ro_section_names)
        order.extend(
            [
                ".dynstr",
                ".dynsym",
                ".gnu.hash",
                ".dynamic",
                ".strtab",
                ".symtab",
                ".shstrtab",
            ]
        )
        self.section_order = order
        names_with_null = [".null"] + order
        self.section_indices = {name: idx for idx, name in enumerate(names_with_null)}

    def _reorder_symbols_for_hash(self) -> None:
        if not self.exported_symbols:
            self.dynamic_symbols = []
            return
        for sym in self.exported_symbols:
            sym.gnu_hash_value = gnu_hash(sym.elf_name)
            sym.gnu_bucket = sym.gnu_hash_value % self.gnu_nbuckets
        self.dynamic_symbols = sorted(
            self.exported_symbols,
            key=lambda sym: (
                sym.gnu_bucket,
                sym.export_order if sym.export_order is not None else sym.original_order,
            ),
        )

    # ------------------------------------------------------------------

    def _build_content_sections(self) -> None:
        # SPASE FILE CHANGE:
        # Instead of allocating bytes with \xC3 or \x00, we set data to empty bytes
        # but set the logical size.
        for region in self.text_regions:
            self.sections[region.name] = SectionDef(
                name=region.name,
                sh_type=SHT_PROGBITS,
                sh_flags=SHF_ALLOC | SHF_EXECINSTR,
                align=PAGE_SIZE,
                data=b"", # No physical data
                size=region.size # Logical size
            )
        for region in self.ro_regions:
            self.sections[region.name] = SectionDef(
                name=region.name,
                sh_type=SHT_PROGBITS,
                sh_flags=SHF_ALLOC,
                align=PAGE_SIZE,
                data=b"", # No physical data
                size=region.size # Logical size
            )

        dynstr = self._build_dynstr()
        dynsym = self._build_dynsym()
        gnu_hash_data = self._build_gnu_hash()

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
        # Placeholder, filled once addresses are known
        self.sections[".dynamic"] = SectionDef(
            name=".dynamic",
            sh_type=SHT_DYNAMIC,
            sh_flags=SHF_ALLOC | SHF_WRITE,
            align=8,
            data=bytes(16 * 6),
            link=self.section_indices[".dynstr"],
            entsize=16,
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
            self.dynstr_offsets[sym.elf_name] = len(data)
            data.extend(sym.elf_name.encode("ascii") + b"\x00")
        return bytes(data)

    def _build_dynsym(self) -> bytes:
        entries = [self._pack_sym_entry(0, STT_NOTYPE, SHN_UNDEF, 0, 0, 0)]
        for idx, sym in enumerate(self.dynamic_symbols, start=1):
            st_name = self.dynstr_offsets[sym.elf_name]
            st_info = (STB_GLOBAL << 4) | (
                STT_FUNC if sym.kind == 0 else STT_OBJECT
            )
            target_section = sym.section_name
            st_shndx = self.section_indices.get(target_section, SHN_UNDEF)
            entries.append(
                self._pack_sym_entry(
                    st_name=st_name,
                    st_type=st_info,
                    st_shndx=st_shndx,
                    st_value=sym.virtual_address,
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
            self.strtab_offsets[sym.elf_name] = len(data)
            data.extend(sym.elf_name.encode("ascii") + b"\x00")
        return bytes(data)

    def _build_symtab(self) -> bytes:
        entries = [self._pack_sym_entry(0, STT_NOTYPE, SHN_UNDEF, 0, 0, 0)]
        for sym in self.symbols:
            st_name = self.strtab_offsets[sym.elf_name]
            st_info = (STB_GLOBAL << 4) | (
                STT_FUNC if sym.kind == 0 else STT_OBJECT
            )
            target_section = sym.section_name
            st_shndx = self.section_indices.get(target_section, SHN_UNDEF)
            entries.append(
                self._pack_sym_entry(
                    st_name=st_name,
                    st_type=st_info,
                    st_shndx=st_shndx,
                    st_value=sym.virtual_address,
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

    def _section(self, name: str) -> SectionDef:
        return self.sections[name]

    def _assign_offsets_and_addresses(self) -> None:
        current_offset = TEXT_BASE_OFFSET
        text_end_addr = TEXT_BASE_VADDR
        for idx, name in enumerate(self.text_section_names):
            section = self._section(name)
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
            section = self._section(name)
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
            section = self._section(name)
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
            section = self._section(name)
            non_alloc_cursor = align(non_alloc_cursor, max(1, section.align))
            section.offset = non_alloc_cursor
            section.addr = 0
            non_alloc_cursor += section.content_size

        self.section_headers_offset = align(non_alloc_cursor, 8)

    # ------------------------------------------------------------------

    def _finalize_dynamic_section(self) -> None:
        dynamic = self._section(".dynamic")
        entries = [
            (DT_GNU_HASH, self._section(".gnu.hash").addr),
            (DT_STRTAB, self._section(".dynstr").addr),
            (DT_SYMTAB, self._section(".dynsym").addr),
            (DT_STRSZ, self._section(".dynstr").content_size),
            (DT_SYMENT, 24),
            (DT_NULL, 0),
        ]
        payload = bytearray()
        for tag, value in entries:
            payload.extend(struct.pack("<QQ", tag, value))
        dynamic.data = bytes(payload)
        dynamic.size = len(dynamic.data)

    # ------------------------------------------------------------------

    def _write_elf_header_to_file(self, f, ph_count: int) -> None:
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

    def _build_program_headers(self) -> List[bytes]:
        entries: List[bytes] = []
        for name in self.text_section_names:
            entries.append(self._make_ph_load(self._section(name), PF_R | PF_X))
        for name in self.ro_section_names:
            entries.append(self._make_ph_load(self._section(name), PF_R))
        if self.rw_segment_file_end > self.rw_segment_start_offset:
            entries.append(self._make_ph_rw_segment())
        entries.append(self._make_ph_dynamic())
        return entries

    def _make_ph_load(self, section: SectionDef, flags: int) -> bytes:
        filesz = section.content_size
        memsz = section.content_size
        return struct.pack(
            "<IIQQQQQQ",
            PT_LOAD,
            flags,
            section.offset,
            section.addr or 0,
            section.addr or 0,
            filesz,
            memsz,
            PAGE_SIZE,
        )

    def _make_ph_rw_segment(self) -> bytes:
        filesz = self.rw_segment_file_end - self.rw_segment_start_offset
        memsz = self.rw_segment_mem_end - self.rw_segment_start_addr
        return struct.pack(
            "<IIQQQQQQ",
            PT_LOAD,
            PF_R | PF_W,
            self.rw_segment_start_offset,
            self.rw_segment_start_addr,
            self.rw_segment_start_addr,
            filesz,
            memsz,
            PAGE_SIZE,
        )

    def _make_ph_dynamic(self) -> bytes:
        dynamic = self._section(".dynamic")
        return struct.pack(
            "<IIQQQQQQ",
            PT_DYNAMIC,
            PF_R | PF_W,
            dynamic.offset,
            dynamic.addr,
            dynamic.addr,
            dynamic.content_size,
            dynamic.content_size,
            8,
        )

    def _shstr_offset(self, name: str) -> int:
        if name == "":
            return 0
        if name not in self.shstr_offsets:
            raise ValueError(f"missing shstr entry for {name}")
        return self.shstr_offsets[name]

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


def dump_symbol_addresses(symbols: Sequence[Symbol], output_path: Path) -> None:
    """Persist symbol_name,address,size for downstream consumers."""

    lines = [f"{sym.name},0x{sym.address:x},0x{sym.size:x}\n" for sym in symbols]
    output_path.write_text("".join(lines))


def build_shared_object(
    symbols_path: Path,
    krg_path: Path,
    output_path: Path,
    symbol_dump_path: Path | None = None,
) -> None:
    requested = parse_symbol_requests(symbols_path)
    graph = KrgGraph(krg_path)
    symbols = resolve_requested_symbols(requested, graph)
    if not any(sym.exported for sym in symbols):
        raise ValueError("no exported symbols resolved from input list")
    if symbol_dump_path is not None:
        dump_symbol_addresses(symbols, symbol_dump_path)
    for sym in symbols:
        if sym.exported:
            sym.elf_name = f"{sym.name}_reuse"
    builder = ManualElfBuilder(symbols)
    # Changed usage: call write() with path, not build() -> bytes
    builder.write(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual ELF shared library builder (Sparse)")
    parser.add_argument(
        "--symbols",
        type=Path,
        default=Path("symbols.txt"),
        help="Path to input symbol description (default: symbols.txt)",
    )
    parser.add_argument(
        "--symbol-addresses",
        type=Path,
        default=Path("resolved_symbol_addresses.txt"),
        help=(
            "Path for the intermediate symbol_name,address dump "
            "(default: resolved_symbol_addresses.txt)"
        ),
    )
    parser.add_argument(
        "--skip-symbol-addresses",
        action="store_true",
        help="Disable writing the intermediate symbol address file.",
    )
    parser.add_argument(
        "--krg",
        type=Path,
        default=None,
        help="Path to out.krg used for dependency queries (default: autodetect)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("libgenerated_library.so"),
        help="Output shared object path (default: libgenerated_library.so)",
    )
    args = parser.parse_args()
    krg_path = args.krg
    if krg_path is None:
        krg_path = infer_default_krg_path()
        if krg_path is None:
            parser.error("Unable to locate out.krg automatically; use --krg")
    if not krg_path.exists():
        parser.error(f"{krg_path} does not exist")
    symbol_dump_path = None if args.skip_symbol_addresses else args.symbol_addresses
    build_shared_object(args.symbols, krg_path, args.output, symbol_dump_path)


if __name__ == "__main__":
    main()