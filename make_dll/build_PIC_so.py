#!/usr/bin/env python3
"""
Sparse ELF64 shared-object builder for kernel code mapping.
"""

from __future__ import annotations

import argparse
import sys
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

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
SHN_ABS = 0xFFF1

STB_GLOBAL = 1
STT_NOTYPE = 0
STT_OBJECT = 1
STT_FUNC = 2

R_X86_64_64 = 1
R_X86_64_RELATIVE = 8

DT_NULL = 0
DT_NEEDED = 1
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

LIB_SHIM = "libshim.so"
BUILTIN_THUNK_MODULE = "builtin_thunk"

INDIRECT_THUNK_PREFIX = "__x86_indirect_thunk_"
INDIRECT_THUNK_ARRAY = "__x86_indirect_thunk_array"
RETURN_THUNK_PREFIX = "__x86_return_thunk"

# The outer kernel call already pushed the real return address, so these
# built-in user-space thunks tail-jump to the register target.  RSP is omitted:
# entering a thunk with CALL has already changed RSP, so it cannot use the same
# two-byte implementation as the other general-purpose registers.
DIRECT_THUNK_ENCODINGS: Dict[str, bytes] = {
    "rax": b"\xff\xe0",
    "rcx": b"\xff\xe1",
    "rdx": b"\xff\xe2",
    "rbx": b"\xff\xe3",
    "rbp": b"\xff\xe5",
    "rsi": b"\xff\xe6",
    "rdi": b"\xff\xe7",
    "r8": b"\x41\xff\xe0",
    "r9": b"\x41\xff\xe1",
    "r10": b"\x41\xff\xe2",
    "r11": b"\x41\xff\xe3",
    "r12": b"\x41\xff\xe4",
    "r13": b"\x41\xff\xe5",
    "r14": b"\x41\xff\xe6",
    "r15": b"\x41\xff\xe7",
}

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

def indirect_thunk_register(name: str) -> str | None:
    if name == INDIRECT_THUNK_ARRAY:
        return "rax"
    if not name.startswith(INDIRECT_THUNK_PREFIX):
        return None
    register = name[len(INDIRECT_THUNK_PREFIX):]
    return register if register in DIRECT_THUNK_ENCODINGS else None

def split_builtin_thunk_shims(shim_symbols: Set[str]) -> tuple[Set[str], Set[str]]:
    builtin = {name for name in shim_symbols if indirect_thunk_register(name) is not None}
    return shim_symbols - builtin, builtin

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
            magic, version, n_nodes, n_edges, name_blob_bytes,
            _arch, _is_runtime, _reserved,
        ) = self._HEADER_V1.unpack_from(blob, cursor)
        header_version = version
        n_modules = 1
        module_blob_bytes = 0
        if header_version >= 2:
            if len(blob) < self._HEADER_V2.size:
                raise ValueError(f"{self.path}: file too small for v2 header")
            (
                magic, version, n_nodes, n_edges, name_blob_bytes,
                _arch, _is_runtime, _reserved, n_modules, module_blob_bytes,
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
                    name=name, address=node_addresses[idx], size=node_sizes[idx],
                    kind=node_kinds[idx], module_id=node_modules[idx], module_name=module_name,
                )
            )
            self.name_to_id[name] = idx

    def closure(self, symbol_name: str, stop_names: Set[str] | None = None) -> List[KrgResolvedSymbol]:
        try:
            root = self.name_to_id[symbol_name]
        except KeyError as exc:
            raise KeyError(f"{symbol_name}: symbol not found in {self.path}") from exc
        seen = [0] * self.node_count
        stack = [root]
        seen[root] = 1
        while stack:
            node = stack.pop()
            if stop_names and self.nodes[node].name in stop_names:
                continue
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
# ELF64 relocatable (.ko) reader (pseudo-GOT extraction)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class KoSection:
    index: int
    name: str
    sh_type: int
    sh_flags: int
    sh_offset: int
    sh_size: int
    sh_link: int
    sh_info: int
    sh_addralign: int
    sh_entsize: int

    @property
    def is_alloc(self) -> bool:
        return bool(self.sh_flags & SHF_ALLOC)

    @property
    def is_write(self) -> bool:
        return bool(self.sh_flags & SHF_WRITE)

    @property
    def is_exec(self) -> bool:
        return bool(self.sh_flags & SHF_EXECINSTR)

@dataclass(frozen=True)
class KoSymbol:
    name: str
    st_info: int
    st_other: int
    st_shndx: int
    st_value: int
    st_size: int

    @property
    def bind(self) -> int:
        return self.st_info >> 4

    @property
    def typ(self) -> int:
        return self.st_info & 0xF

    @property
    def is_undef(self) -> bool:
        return self.st_shndx == SHN_UNDEF

@dataclass(frozen=True)
class KoDataReloc:
    offset: int  
    sym_idx: int
    symbol_name: str
    sym_shndx: int
    sym_value: int
    addend: int
    r_type: int
    is_undef: bool

@dataclass(frozen=True)
class KoCoreLayout:
    section_offsets: Dict[int, int]
    text_start: int
    text_end: int
    ro_start: int
    ro_end: int
    data_start: int
    data_end: int
    ro_image: bytes
    data_image: bytes
    data_relocs: List[KoDataReloc]

    @property
    def text_size(self) -> int:
        return self.text_end - self.text_start

    @property
    def ro_size(self) -> int:
        return self.ro_end - self.ro_start

    @property
    def data_size(self) -> int:
        return self.data_end - self.data_start

class KoFile:
    _EHDR = struct.Struct("<16sHHIQQQIHHHHHH")
    _SHDR = struct.Struct("<IIQQQQIIQQ")
    _SYMENT = struct.Struct("<IBBHQQ")
    _RELA = struct.Struct("<QQq")
    _NON_CORE_SECTION_PREFIXES = (
        ".modinfo",
        ".return_sites",
        ".retpoline_sites",
    )

    def __init__(self, path: Path) -> None:
        self.path = path
        self._blob = memoryview(path.read_bytes())
        self.sections: List[KoSection] = []
        self._sections_by_name: Dict[str, KoSection] = {}
        self.symbols: List[KoSymbol] = []
        self._sym_by_name: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        blob = self._blob
        if len(blob) < self._EHDR.size:
            raise ValueError(f"{self.path}: file too small for ELF header")
        (e_ident, e_type, e_machine, _e_version, _e_entry, _e_phoff, e_shoff, _e_flags,
         _e_ehsize, _e_phentsize, _e_phnum, e_shentsize, e_shnum, e_shstrndx) = self._EHDR.unpack_from(blob, 0)
        if e_ident[0:4] != b"\x7fELF" or e_ident[4] != ELFCLASS64:
            raise ValueError(f"{self.path}: not an ELF64 file")
        if e_type != 1:
            raise ValueError(f"{self.path}: expected ET_REL (.ko), got e_type={e_type}")
        if e_machine != EM_X86_64:
            raise ValueError(f"{self.path}: expected EM_X86_64, got e_machine={e_machine}")
        if e_shentsize != self._SHDR.size:
            raise ValueError(f"{self.path}: unexpected section header size {e_shentsize}")
        if e_shoff == 0 or e_shnum == 0:
            raise ValueError(f"{self.path}: missing section header table")

        raw_shdrs: List[tuple[int, int, int, int, int, int, int, int, int, int]] = []
        for idx in range(e_shnum):
            off = e_shoff + idx * e_shentsize
            if off + self._SHDR.size > len(blob):
                raise ValueError(f"{self.path}: truncated section header table")
            raw_shdrs.append(self._SHDR.unpack_from(blob, off))

        if e_shstrndx >= e_shnum:
            raise ValueError(f"{self.path}: invalid e_shstrndx {e_shstrndx}")
        shstr = raw_shdrs[e_shstrndx]
        shstr_off = shstr[4]
        shstr_size = shstr[5]
        if shstr_off + shstr_size > len(blob):
            raise ValueError(f"{self.path}: truncated shstrtab")
        shstr_blob = bytes(blob[shstr_off : shstr_off + shstr_size])

        self.sections.clear()
        self._sections_by_name.clear()
        for idx, sh in enumerate(raw_shdrs):
            sh_name, sh_type, _sh_flags, _sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = sh
            name = ""
            if sh_name < len(shstr_blob):
                end = shstr_blob.find(b"\x00", sh_name)
                if end != -1:
                    name = shstr_blob[sh_name:end].decode("utf-8", errors="ignore")
            sec = KoSection(
                index=idx, name=name, sh_type=sh_type, sh_flags=_sh_flags, sh_offset=sh_offset,
                sh_size=sh_size, sh_link=sh_link, sh_info=sh_info, sh_addralign=sh_addralign, sh_entsize=sh_entsize,
            )
            self.sections.append(sec)
            if name and name not in self._sections_by_name:
                self._sections_by_name[name] = sec

        symtab = self._sections_by_name.get(".symtab")
        if symtab is None or symtab.sh_entsize != self._SYMENT.size:
            raise ValueError(f"{self.path}: missing or unsupported .symtab")
        if symtab.sh_link >= len(self.sections):
            raise ValueError(f"{self.path}: invalid .symtab sh_link {symtab.sh_link}")
        strtab = self.sections[symtab.sh_link]
        if strtab.sh_offset + strtab.sh_size > len(blob):
            raise ValueError(f"{self.path}: truncated .strtab")
        str_blob = bytes(blob[strtab.sh_offset : strtab.sh_offset + strtab.sh_size])

        if symtab.sh_offset + symtab.sh_size > len(blob):
            raise ValueError(f"{self.path}: truncated .symtab")
        self.symbols.clear()
        self._sym_by_name.clear()
        for entry_off in range(symtab.sh_offset, symtab.sh_offset + symtab.sh_size, symtab.sh_entsize):
            st_name, st_info, st_other, st_shndx, st_value, st_size = self._SYMENT.unpack_from(
                blob, entry_off
            )
            name = ""
            if st_name < len(str_blob):
                end = str_blob.find(b"\x00", st_name)
                if end != -1:
                    name = str_blob[st_name:end].decode("utf-8", errors="ignore")
            sym = KoSymbol(
                name=name, st_info=st_info, st_other=st_other, st_shndx=st_shndx,
                st_value=st_value, st_size=st_size,
            )
            idx = len(self.symbols)
            self.symbols.append(sym)
            if name and name not in self._sym_by_name:
                self._sym_by_name[name] = idx

    def find_symbol(self, name: str) -> tuple[int, KoSymbol] | None:
        idx = self._sym_by_name.get(name)
        if idx is None:
            return None
        return idx, self.symbols[idx]

    @staticmethod
    def _is_core_section(name: str) -> bool:
        if not name:
            return False
        if name.startswith(".init") or name.startswith(".exit"):
            return False
        for prefix in KoFile._NON_CORE_SECTION_PREFIXES:
            if name == prefix or name.startswith(prefix + "."):
                return False
        return True

    def compute_core_layout(self) -> KoCoreLayout:
        core_alloc = [s for s in self.sections if s.is_alloc and self._is_core_section(s.name)]
        text_secs = [s for s in core_alloc if s.is_exec]
        ro_secs = [s for s in core_alloc if (not s.is_exec) and (not s.is_write)]
        data_secs = [s for s in core_alloc if s.is_write]

        section_offsets: Dict[int, int] = {}
        cursor = 0
        text_start = cursor
        for sec in text_secs:
            cursor = align(cursor, max(1, sec.sh_addralign))
            section_offsets[sec.index] = cursor
            cursor += sec.sh_size
        cursor = align(cursor, PAGE_SIZE)
        text_end = cursor

        ro_start = cursor
        for sec in ro_secs:
            cursor = align(cursor, max(1, sec.sh_addralign))
            section_offsets[sec.index] = cursor
            cursor += sec.sh_size
        cursor = align(cursor, PAGE_SIZE)
        ro_end = cursor

        data_start = cursor
        for sec in data_secs:
            cursor = align(cursor, max(1, sec.sh_addralign))
            section_offsets[sec.index] = cursor
            cursor += sec.sh_size
        cursor = align(cursor, PAGE_SIZE)
        data_end = cursor

        ro_size = ro_end - ro_start
        ro_image = bytearray(ro_size)
        for sec in ro_secs:
            if sec.sh_size == 0:
                continue
            dest_off = section_offsets[sec.index] - ro_start
            if sec.sh_type == SHT_NOBITS:
                continue
            end = sec.sh_offset + sec.sh_size
            if end > len(self._blob):
                raise ValueError(f"{self.path}: truncated section {sec.name}")
            ro_image[dest_off : dest_off + sec.sh_size] = bytes(
                self._blob[sec.sh_offset : end]
            )

        data_size = data_end - data_start
        data_image = bytearray(data_size)
        for sec in data_secs:
            if sec.sh_size == 0:
                continue
            dest_off = section_offsets[sec.index] - data_start
            if sec.sh_type == SHT_NOBITS:
                continue
            end = sec.sh_offset + sec.sh_size
            if end > len(self._blob):
                raise ValueError(f"{self.path}: truncated section {sec.name}")
            data_image[dest_off : dest_off + sec.sh_size] = bytes(
                self._blob[sec.sh_offset : end]
            )

        data_sec_indices = {sec.index for sec in data_secs}
        data_relocs: List[KoDataReloc] = []
        for sec in self.sections:
            if sec.sh_type != SHT_RELA or not sec.name.startswith(".rela."):
                continue
            if sec.sh_info not in data_sec_indices:
                continue
            if sec.sh_entsize != self._RELA.size:
                raise ValueError(f"{self.path}: unexpected rela entsize in {sec.name}")
            target_base = section_offsets.get(sec.sh_info)
            if target_base is None:
                continue
            base_off = target_base - data_start
            end = sec.sh_offset + sec.sh_size
            if end > len(self._blob):
                raise ValueError(f"{self.path}: truncated relocation section {sec.name}")
            for entry_off in range(sec.sh_offset, end, sec.sh_entsize):
                r_offset, r_info, r_addend = self._RELA.unpack_from(self._blob, entry_off)
                sym_idx = (r_info >> 32) & 0xFFFFFFFF
                r_type = r_info & 0xFFFFFFFF
                sym_name = ""
                is_undef = False
                sym_shndx = 0
                sym_value = 0
                if sym_idx < len(self.symbols):
                    sym = self.symbols[sym_idx]
                    sym_name = sym.name
                    is_undef = sym.is_undef
                    sym_shndx = sym.st_shndx
                    sym_value = sym.st_value
                data_relocs.append(
                    KoDataReloc(
                        offset=base_off + r_offset, sym_idx=sym_idx, symbol_name=sym_name,
                        sym_shndx=sym_shndx, sym_value=sym_value, addend=r_addend,
                        r_type=r_type, is_undef=is_undef,
                    )
                )

        return KoCoreLayout(
            section_offsets=section_offsets, text_start=text_start, text_end=text_end,
            ro_start=ro_start, ro_end=ro_end, data_start=data_start, data_end=data_end,
            ro_image=bytes(ro_image), data_image=bytes(data_image), data_relocs=data_relocs,
        )

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
    replace_from_kernel: bool = True

    @property
    def is_import(self) -> bool:
        return not self.defined

def role_for_symbol(sym: ResolvedSymbol, owner_module: str) -> str:
    if not sym.replace_from_kernel:
        return "synthetic"
    if not sym.defined:
        return "import"
    return "export" if sym.exported else "internal"

def build_builtin_thunk_pages(
    symbols: Sequence[ResolvedSymbol], configured_thunks: Set[str]
) -> Dict[int, bytes]:
    """Build direct-jump thunk pages selected through shim.txt.

    Kernel callers contain fixed rel32 calls to the thunk virtual addresses, so
    the generated code must remain at those same relative addresses.  The whole
    page becomes synthetic because page-cache replacement operates per page.
    """
    configured_registers = {
        register
        for name in configured_thunks
        if (register := indirect_thunk_register(name)) is not None
    }
    selected = [
        sym for sym in symbols
        if sym.defined and indirect_thunk_register(sym.name) in configured_registers
    ]
    if not selected:
        return {}

    synthetic_page_addrs = {align_down(sym.address, PAGE_SIZE) for sym in selected}
    pages = {page: bytearray(b"\xcc" * PAGE_SIZE) for page in synthetic_page_addrs}

    for sym in symbols:
        page = align_down(sym.address, PAGE_SIZE) if sym.defined and sym.address else None
        if page not in synthetic_page_addrs:
            continue

        register = indirect_thunk_register(sym.name)
        is_return_thunk = sym.name.startswith(RETURN_THUNK_PREFIX)
        if register is None and not is_return_thunk:
            raise ValueError(
                f"cannot synthesize thunk page 0x{page:x}: "
                f"non-thunk dependency {sym.name} shares the page"
            )
        if register is not None and register not in configured_registers:
            raise ValueError(
                f"cannot synthesize thunk page 0x{page:x}: "
                f"{sym.name} is required but is not enabled in shim.txt"
            )

        offset = sym.address - page
        code = b"\xc3" if is_return_thunk else DIRECT_THUNK_ENCODINGS[register]
        if offset + len(code) > PAGE_SIZE:
            raise ValueError(f"{sym.name}: synthetic thunk crosses a page boundary")
        pages[page][offset:offset + len(code)] = code
        sym.module_name = BUILTIN_THUNK_MODULE
        sym.source = BUILTIN_THUNK_MODULE
        sym.replace_from_kernel = False

    return {page: bytes(data) for page, data in pages.items()}

def resolve_requested_symbols(
    requested_names: Sequence[str], graph: KrgGraph, shim_symbols: Set[str]
) -> tuple[List[ResolvedSymbol], List[str], str, str, List[str]]:
    if not requested_names:
        raise ValueError("at least one symbol is required")

    export_order = {name: idx for idx, name in enumerate(requested_names)}
    # An explicitly requested API is a native export even when the same name is
    # listed as a user-space replacement for dependency closure traversal.
    dependency_shim_symbols = shim_symbols - set(export_order)
    resolved: Dict[str, ResolvedSymbol] = {}
    ordered: List[ResolvedSymbol] = []
    missing: List[str] = []
    needed_libs: List[str] = []
    dep_modules: List[str] = []
    owner_module: str | None = None

    def module_to_lib(module: str) -> str:
        if module == "shim": return LIB_SHIM
        base = Path(module).name
        for ext in (".ko.xz", ".ko.gz", ".ko.zst", ".ko"):
            if base.endswith(ext):
                base = base[: -len(ext)]
                break
        return f"lib{base}.so"

    def module_for_entry(entry: KrgResolvedSymbol) -> str:
        if entry.name in dependency_shim_symbols: return "shim"
        return entry.module_name or "kernel"

    first_lookup = graph.lookup(requested_names[0])
    if first_lookup is None:
        raise ValueError(f"{requested_names[0]}: symbol not found in {graph.path}")
    owner_module = module_for_entry(first_lookup)
    for name in requested_names:
        entry = graph.lookup(name)
        if entry is None: continue
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
            is_shim = module_name == "shim"
            if sym is None:
                sym = ResolvedSymbol(
                    name=entry.name, source=module_to_lib(owner_module or module_name),
                    defined=not is_shim, exported=is_export, st_type=expected_type,
                    size=entry.size, address=entry.address,
                    export_order=export_order.get(entry.name, len(ordered)),
                    original_order=len(ordered), module_id=entry.module_id, module_name=module_name,
                )
                resolved[entry.name] = sym
                ordered.append(sym)
            if is_shim:
                if LIB_SHIM not in needed_libs: needed_libs.append(LIB_SHIM)
                if module_name not in dep_modules: dep_modules.append(module_name)
        if name not in resolved:
            missing.append(name)
            print(f"{name}: symbol missing after resolution", file=sys.stderr)

    if missing and len(missing) == len(requested_names):
        raise ValueError("None of the requested symbols were found; cannot build shared object")
    owner_module = owner_module or "kernel"
    owner_lib = module_to_lib(owner_module)
    return ordered, needed_libs, owner_module, owner_lib, dep_modules

def dump_symbol_addresses_all(module_symbols: Sequence[tuple[str, Sequence[ResolvedSymbol]]], output_path: Path) -> None:
    lines: List[str] = []
    for owner_module, symbols in module_symbols:
        for sym in symbols:
            lines.append(f"{sym.name},0x{sym.address:x},0x{sym.size:x},{sym.module_name},{role_for_symbol(sym, owner_module)}\n")
    output_path.write_text("".join(lines))

def format_module_deps(owner_module: str, dep_modules: Sequence[str], symbols: Sequence[ResolvedSymbol]) -> List[str]:
    dep_to_symbols: Dict[str, List[str]] = {}
    for sym in symbols:
        if sym.module_name == owner_module: continue
        dep_to_symbols.setdefault(sym.module_name, []).append(sym.name)
    lines: List[str] = []
    for mod in dep_modules:
        syms = dep_to_symbols.get(mod, [])
        sym_list = " ".join(sorted(set(syms)))
        lines.append(f"{owner_module} -> {mod}: {sym_list}\n")
    return lines

def dump_dep_symbol_lists(dep_modules: Sequence[str], symbols: Sequence[ResolvedSymbol], base_dir: Path) -> None:
    for mod in dep_modules:
        names = sorted({sym.name for sym in symbols if sym.module_name == mod})
        if not names: continue
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
    def size(self) -> int: return self.end - self.start

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
    def content_size(self) -> int: return self.size if self.size is not None else len(self.data)

    @property
    def is_alloc(self) -> bool: return bool(self.sh_flags & SHF_ALLOC)

@dataclass(frozen=True)
class DataRelocation:
    offset: int  
    symbol: ResolvedSymbol | None
    addend: int = 0
    r_type: int = R_X86_64_64

class ManualElfBuilder:
    def __init__(
        self, symbols: List[ResolvedSymbol], needed_libraries: List[str],
        export_stub_size: int = DEFAULT_EXPORT_STUB_SIZE, ro_bytes: bytes = b"",
        data_bytes: bytes = b"", data_relocations: List[DataRelocation] | None = None,
        rw_base_vaddr: int | None = None, extra_text_ranges: List[tuple[int, int]] | None = None,
        extra_ro_ranges: List[tuple[int, int]] | None = None, owner_module_name: str | None = None,
        include_data: bool = True, text_min_override: int | None = None,
        synthetic_text_pages: Dict[int, bytes] | None = None,
    ) -> None:
        self.symbols = symbols
        self.defined_symbols = [sym for sym in symbols if sym.defined]
        self.exports = [sym for sym in self.defined_symbols if sym.exported]
        self.imports = [sym for sym in symbols if sym.is_import]
        self.needed_libraries = needed_libraries
        self.export_stub_size = export_stub_size
        self.ro_bytes = ro_bytes
        self.data_bytes = data_bytes
        self.data_relocations = data_relocations or []
        self.rw_base_vaddr = rw_base_vaddr
        self.extra_text_ranges = extra_text_ranges or []
        self.extra_ro_ranges = extra_ro_ranges or []
        self.owner_module_name = owner_module_name
        self.include_data = include_data
        self.text_min_override = text_min_override
        self.synthetic_text_pages = dict(synthetic_text_pages or {})
        for page, data in self.synthetic_text_pages.items():
            if page % PAGE_SIZE:
                raise ValueError(f"synthetic text page 0x{page:x} is not page-aligned")
            if len(data) != PAGE_SIZE:
                raise ValueError(f"synthetic text page 0x{page:x} is not {PAGE_SIZE} bytes")
        self.sections: Dict[str, SectionDef] = {}
        self.section_order: List[str] = []
        self.section_indices: Dict[str, int] = {}
        self.shstr_offsets: Dict[str, int] = {}
        self.dynstr_offsets: Dict[str, int] = {}
        self.dynstr_needed_offsets: Dict[str, int] = {}
        self.strtab_offsets: Dict[str, int] = {}
        reloc_syms: List[ResolvedSymbol] = [
            reloc.symbol for reloc in (data_relocations or []) if reloc.symbol is not None
        ]
        dynsyms_ordered: List[ResolvedSymbol] = []
        seen_ids = set()
        for sym in self.exports + self.imports + reloc_syms:
            sid = id(sym)
            if sid in seen_ids: continue
            dynsyms_ordered.append(sym)
            seen_ids.add(sid)
        self.dynamic_symbols: List[ResolvedSymbol] = dynsyms_ordered
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

    def write(self, output_path: Path) -> None:
        self._prepare_symbol_virtual_addresses()
        self._derive_section_order()
        self._reorder_symbols_for_hash()
        self._build_content_sections()
        self._assign_offsets_and_addresses()
        self.build_relocations()
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
                    "<IIQQQQIIQQ", sh_name, section.sh_type, section.sh_flags,
                    section.addr or 0, section.offset or 0, section.content_size,
                    section.link, section.info, section.align, section.entsize,
                )
                f.write(shdr)
            total_size = self.section_headers_offset + (len(self.section_order) + 1) * 64
            f.truncate(total_size)

    def _prepare_symbol_virtual_addresses(self) -> None:
        def keep(sym: ResolvedSymbol) -> bool:
            if self.owner_module_name is None: return True
            return sym.module_name == self.owner_module_name

        code_symbols = [sym for sym in self.defined_symbols if sym.st_type == STT_FUNC and keep(sym)]
        ro_symbols = [sym for sym in self.defined_symbols if sym.st_type == STT_OBJECT and keep(sym) and sym.name.startswith(".rodata")]
        data_symbols = [sym for sym in self.defined_symbols if sym.st_type == STT_OBJECT and keep(sym) and sym not in ro_symbols]

        cursor = TEXT_BASE_VADDR
        for sym in self.defined_symbols:
            if sym.size == 0: sym.size = self.export_stub_size
            if sym.address == 0:
                sym.address = cursor
                cursor += self.export_stub_size

        overall_min_page = (align_down(min(sym.address for sym in self.defined_symbols), PAGE_SIZE) if self.defined_symbols else TEXT_BASE_VADDR)
        if self.text_min_override is not None:
            self.text_min_page = align_down(self.text_min_override, PAGE_SIZE)
        else:
            candidate_text_min = None
            if code_symbols: candidate_text_min = min(sym.address for sym in code_symbols)
            if self.extra_text_ranges:
                extra_min = min(start for start, _ in self.extra_text_ranges)
                candidate_text_min = extra_min if candidate_text_min is None else min(candidate_text_min, extra_min)
            if candidate_text_min is not None: self.text_min_page = align_down(candidate_text_min, PAGE_SIZE)
            else: self.text_min_page = overall_min_page
        for sym in self.defined_symbols:
            sym.virtual_address = TEXT_BASE_VADDR + (sym.address - self.text_min_page)

        self.region_by_name.clear()
        self.text_regions = self._build_regions(code_symbols, ".text", self.extra_text_ranges)
        self.ro_regions = self._build_regions(ro_symbols, ".rodata", self.extra_ro_ranges)
        for region in self.text_regions + self.ro_regions:
            self.region_by_name[region.name] = region
        self.text_section_names = [region.name for region in self.text_regions]
        self.ro_section_names = [region.name for region in self.ro_regions]
        self._assign_symbol_sections(code_symbols, self.text_regions)
        self._assign_symbol_sections(ro_symbols, self.ro_regions)
        for sym in data_symbols: sym.section_name = ".data"

    def _build_regions(self, symbols: List[ResolvedSymbol], base_name: str, extra_ranges: List[tuple[int, int]] | None = None) -> List[Region]:
        if not symbols: symbols = []
        intervals: List[tuple[int, int]] = []
        for sym in symbols:
            size = max(sym.size, 1)
            start = align_down(sym.address, PAGE_SIZE)
            end = align(sym.address + size, PAGE_SIZE)
            if end == start: end += PAGE_SIZE
            intervals.append((start, end))
        for start, end in (extra_ranges or []):
            s = align_down(start, PAGE_SIZE)
            e = align(end, PAGE_SIZE)
            if e == s: e += PAGE_SIZE
            intervals.append((s, e))
        if not intervals: return []
        intervals.sort()
        merged: List[List[int]] = []
        for start, end in intervals:
            if not merged or start > merged[-1][1]: merged.append([start, end])
            else: merged[-1][1] = max(merged[-1][1], end)
        regions: List[Region] = []
        if len(merged) == 1: names = [base_name]
        else: names = [f"{base_name}{idx + 1}" for idx in range(len(merged))]
        for name, bounds in zip(names, merged):
            start, end = bounds
            region = Region(name=name, start=start, end=end)
            regions.append(region)
            self.region_by_name[name] = region
        return regions

    def _assign_symbol_sections(self, symbols: List[ResolvedSymbol], regions: List[Region]) -> None:
        if not symbols: return
        for sym in symbols:
            region = self._find_region_for_address(sym.address, regions)
            if region is None: raise ValueError(f"{sym.name}: no region covers address 0x{sym.address:x}")
            sym.section_name = region.name

    @staticmethod
    def _find_region_for_address(address: int, regions: List[Region]) -> Region | None:
        for region in regions:
            if region.start <= address < region.end: return region
        return None

    def _derive_section_order(self) -> None:
        order: List[str] = []
        order.extend(self.text_section_names)
        order.extend(self.ro_section_names)
        if self.include_data: order.append(".data")
        order.extend([".dynstr", ".dynsym", ".gnu.hash"])
        if self.include_data and self.data_relocations: order.append(".rela.dyn")
        order.extend([".dynamic", ".strtab", ".symtab", ".shstrtab"])
        self.section_order = order
        names_with_null = [".null"] + order
        self.section_indices = {name: idx for idx, name in enumerate(names_with_null)}

    def _reorder_symbols_for_hash(self) -> None:
        for sym in self.dynamic_symbols:
            sym.gnu_hash_value = gnu_hash(sym.name)
            sym.gnu_bucket = sym.gnu_hash_value % self.gnu_nbuckets
        self.dynamic_symbols.sort(key=lambda sym: (sym.gnu_bucket, 0 if sym.defined else 1, sym.export_order, sym.original_order))

    def _build_content_sections(self) -> None:
        for region in self.text_regions:
            region_data: bytearray | None = None
            for page, data in self.synthetic_text_pages.items():
                if not (region.start <= page and page + PAGE_SIZE <= region.end):
                    continue
                if region_data is None:
                    region_data = bytearray(region.size)
                offset = page - region.start
                region_data[offset:offset + PAGE_SIZE] = data
            self.sections[region.name] = SectionDef(
                name=region.name, sh_type=SHT_PROGBITS,
                sh_flags=SHF_ALLOC | SHF_EXECINSTR, align=PAGE_SIZE,
                data=bytes(region_data) if region_data is not None else b"",
                size=region.size,
            )
        for region in self.ro_regions:
            self.sections[region.name] = SectionDef(name=region.name, sh_type=SHT_PROGBITS, sh_flags=SHF_ALLOC, align=PAGE_SIZE, data=b"", size=region.size)
        if self.include_data:
            self.sections[".data"] = SectionDef(name=".data", sh_type=SHT_PROGBITS, sh_flags=SHF_ALLOC | SHF_WRITE, align=8, data=self.data_bytes, size=len(self.data_bytes))
        dynstr = self._build_dynstr()
        dynsym = self._build_dynsym()
        gnu_hash_data = self._build_gnu_hash()
        dynamic_guess_entries = len(self.needed_libraries) + 10
        self.sections[".dynstr"] = SectionDef(name=".dynstr", sh_type=SHT_STRTAB, sh_flags=SHF_ALLOC, align=1, data=dynstr)
        self.sections[".dynsym"] = SectionDef(name=".dynsym", sh_type=SHT_DYNSYM, sh_flags=SHF_ALLOC, align=8, data=dynsym, link=self.section_indices.get(".dynstr", 0), info=1, entsize=24)
        self.sections[".gnu.hash"] = SectionDef(name=".gnu.hash", sh_type=SHT_GNU_HASH, sh_flags=SHF_ALLOC, align=8, data=gnu_hash_data, link=self.section_indices.get(".dynsym", 0))
        if ".rela.dyn" in self.section_order:
            rela_size = len(self.data_relocations) * 24
            self.sections[".rela.dyn"] = SectionDef(name=".rela.dyn", sh_type=SHT_RELA, sh_flags=SHF_ALLOC, align=8, data=bytes(rela_size), size=rela_size, link=self.section_indices.get(".dynsym", 0), info=0, entsize=24)
        self.sections[".dynamic"] = SectionDef(name=".dynamic", sh_type=SHT_DYNAMIC, sh_flags=SHF_ALLOC | SHF_WRITE, align=8, data=bytes(dynamic_guess_entries * 16), entsize=16, link=self.section_indices.get(".dynstr", 0))
        strtab = self._build_strtab()
        symtab = self._build_symtab()
        self.sections[".strtab"] = SectionDef(name=".strtab", sh_type=SHT_STRTAB, sh_flags=0, align=1, data=strtab)
        self.sections[".symtab"] = SectionDef(name=".symtab", sh_type=SHT_SYMTAB, sh_flags=0, align=8, data=symtab, link=self.section_indices.get(".strtab", 0), info=1, entsize=24)
        shstrtab = self._build_shstrtab()
        self.sections[".shstrtab"] = SectionDef(name=".shstrtab", sh_type=SHT_STRTAB, sh_flags=0, align=1, data=shstrtab)

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
            if sym.section_name is None: st_shndx = SHN_ABS if sym.defined else SHN_UNDEF
            else: st_shndx = self.section_indices.get(sym.section_name, SHN_UNDEF)
            entries.append(self._pack_sym_entry(st_name=st_name, st_type=st_info, st_shndx=st_shndx, st_value=(sym.virtual_address if sym.defined else 0) & 0xFFFFFFFFFFFFFFFF, st_size=sym.size))
            sym.dynsym_index = idx
        return b"".join(entries)

    def _build_gnu_hash(self) -> bytes:
        if not self.dynamic_symbols: return b""
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
                if prev_bucket is not None and last_index is not None: chains[last_index - first_sym] |= 1
            elif bucket_idx != prev_bucket and prev_bucket is not None and last_index is not None:
                chains[last_index - first_sym] |= 1
            chains[dyn_index - first_sym] = h & ~1
            prev_bucket = bucket_idx
            last_index = dyn_index
        if last_index is not None: chains[last_index - first_sym] |= 1
        payload = bytearray()
        payload.extend(struct.pack("<IIII", self.gnu_nbuckets, first_sym, self.gnu_bloom_size, self.gnu_bloom_shift))
        for word in bloom: payload.extend(struct.pack("<Q", word))
        for bucket in buckets: payload.extend(struct.pack("<I", bucket))
        for chain in chains: payload.extend(struct.pack("<I", chain))
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
            if sym.section_name is None: st_shndx = SHN_ABS if sym.defined else SHN_UNDEF
            else: st_shndx = self.section_indices.get(sym.section_name, SHN_UNDEF)
            entries.append(self._pack_sym_entry(st_name=st_name, st_type=st_info, st_shndx=st_shndx, st_value=(sym.virtual_address if sym.defined else 0) & 0xFFFFFFFFFFFFFFFF, st_size=sym.size))
        return b"".join(entries)

    def _build_shstrtab(self) -> bytes:
        names = [""]
        names.extend(self.section_order)
        data = bytearray()
        for name in names:
            self.shstr_offsets[name] = len(data)
            data.extend(name.encode("ascii") + b"\x00")
        return bytes(data)

    def _assign_offsets_and_addresses(self) -> None:
        current_offset = TEXT_BASE_OFFSET
        text_end_addr = TEXT_BASE_VADDR
        for idx, name in enumerate(self.text_section_names):
            section = self.sections[name]
            if idx == 0: section.offset = TEXT_BASE_OFFSET
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

        rw_sections = [name for name in self.section_order if self.sections[name].is_alloc and name not in self.text_section_names and name not in self.ro_section_names]

        cursor_offset = align(current_offset, PAGE_SIZE)
        cursor_addr_default = align(last_alloc_addr, PAGE_SIZE)
        cursor_addr = cursor_addr_default
        if self.rw_base_vaddr is not None: cursor_addr = align(self.rw_base_vaddr, PAGE_SIZE)

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

    def build_relocations(self) -> None:
        if not self.data_relocations: return
        rela_sec = self.sections.get(".rela.dyn")
        if rela_sec is None: raise ValueError("internal error: data relocations present but .rela.dyn missing")
        data_sec = self.sections[".data"]
        if data_sec.addr is None: raise ValueError(".data has no assigned address")
        rela_entries: List[bytes] = []
        for reloc in self.data_relocations:
            r_offset = data_sec.addr + reloc.offset
            if reloc.r_type == R_X86_64_RELATIVE: sym_index = 0
            else:
                if reloc.symbol is None: raise ValueError(f"relocation at .data+0x{reloc.offset:x} missing symbol")
                sym_index = reloc.symbol.dynsym_index
            r_info = (sym_index << 32) | reloc.r_type
            rela_entries.append(struct.pack("<QQq", r_offset, r_info, reloc.addend))
        rela_sec.data = b"".join(rela_entries)
        rela_sec.size = len(rela_sec.data)

    def _finalize_dynamic_section(self) -> None:
        dynamic = self.sections[".dynamic"]
        entries: List[tuple[int, int]] = []
        for lib in self.needed_libraries: entries.append((DT_NEEDED, self.dynstr_needed_offsets[lib]))
        entries.extend([
            (DT_GNU_HASH, self.sections[".gnu.hash"].addr or 0),
            (DT_STRTAB, self.sections[".dynstr"].addr or 0),
            (DT_SYMTAB, self.sections[".dynsym"].addr or 0),
        ])
        rela_sec = self.sections.get(".rela.dyn")
        if rela_sec is not None and rela_sec.content_size:
            entries.extend([
                (DT_RELA, rela_sec.addr or 0),
                (DT_RELASZ, rela_sec.content_size),
                (DT_RELAENT, 24),
            ])
        entries.extend([
            (DT_STRSZ, self.sections[".dynstr"].content_size),
            (DT_SYMENT, 24),
            (DT_NULL, 0),
        ])
        payload = bytearray()
        for tag, value in entries: payload.extend(struct.pack("<QQ", tag, value))
        dynamic.data = bytes(payload)
        dynamic.size = len(dynamic.data)

    def _build_program_headers(self) -> List[bytes]:
        entries: List[bytes] = []
        for name in self.text_section_names:
            section = self.sections[name]
            entries.append(self._make_ph_load(offset=section.offset or 0, addr=section.addr or 0, file_size=section.content_size, mem_size=section.content_size, flags=PF_R | PF_X))
        for name in self.ro_section_names:
            section = self.sections[name]
            entries.append(self._make_ph_load(offset=section.offset or 0, addr=section.addr or 0, file_size=section.content_size, mem_size=section.content_size, flags=PF_R))
        if self.rw_segment_file_end > self.rw_segment_start_offset:
            file_size = max(0, self.rw_segment_file_end - self.rw_segment_start_offset)
            mem_size = self.rw_segment_mem_end - self.rw_segment_start_addr
            entries.append(self._make_ph_load(offset=self.rw_segment_start_offset, addr=self.rw_segment_start_addr, file_size=file_size, mem_size=mem_size, flags=PF_R | PF_W))
        entries.append(self._make_ph_dynamic())
        return entries

    def _make_ph_load(self, offset: int, addr: int, file_size: int, mem_size: int, flags: int) -> bytes:
        return struct.pack("<IIQQQQQQ", PT_LOAD, flags, offset, addr, addr, file_size, mem_size, PAGE_SIZE)

    def _make_ph_dynamic(self) -> bytes:
        dynamic = self.sections[".dynamic"]
        return struct.pack("<IIQQQQQQ", PT_DYNAMIC, PF_R | PF_W, dynamic.offset or 0, dynamic.addr or 0, dynamic.addr or 0, dynamic.content_size, dynamic.content_size, 8)

    @staticmethod
    def _pack_sym_entry(st_name: int, st_type: int, st_shndx: int, st_value: int, st_size: int, st_other: int = 0) -> bytes:
        return struct.pack("<IBBHQQ", st_name, st_type, st_other, st_shndx, st_value, st_size)

    def _write_elf_header(self, f, ph_count: int) -> None:
        e_ident = bytearray(EI_NIDENT)
        e_ident[0:4] = b"\x7fELF"
        e_ident[4] = ELFCLASS64
        e_ident[5] = ELFDATA2LSB
        e_ident[6] = EV_CURRENT
        e_ident[7] = 0
        e_ident[8] = 0
        ehdr = struct.pack(
            "<16sHHIQQQIHHHHHH", bytes(e_ident), ET_DYN, EM_X86_64, EV_CURRENT,
            TEXT_BASE_VADDR, 64, self.section_headers_offset, 0, 64, 56, ph_count, 64,
            len(self.section_order) + 1, self.section_indices.get(".shstrtab", 0)
        )
        f.write(ehdr)

# -----------------------------------------------------------------------------
# CLI glue
# -----------------------------------------------------------------------------

def infer_default_krg_path() -> Path | None:
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        candidate = parent / "KernelCodeMappingFinal/kernel-cgd/src/out.krg"
        if candidate.exists(): return candidate
    return None

def build_shared_object(
    symbols_path: Path, krg_path: Path, export_stub_size: int = DEFAULT_EXPORT_STUB_SIZE,
    symbol_dump_path: Path | None = None, shim_list_path: Path | None = None, ko_path: Path | None = None,
) -> None:
    graph = KrgGraph(krg_path)
    shim_symbols = load_shim_symbols(shim_list_path)
    requested = parse_symbol_requests(symbols_path)
    # shim.txt defines dependency boundaries, not replacements for APIs the
    # user explicitly asked this DSO to export.
    shim_symbols.difference_update(requested)
    if INDIRECT_THUNK_ARRAY in requested or f"{INDIRECT_THUNK_PREFIX}rax" in requested:
        shim_symbols.discard(INDIRECT_THUNK_ARRAY)
        shim_symbols.discard(f"{INDIRECT_THUNK_PREFIX}rax")
    shim_symbols, builtin_thunk_shims = split_builtin_thunk_shims(shim_symbols)
    resolved, needed_libs, owner_module, owner_lib, dep_modules = resolve_requested_symbols(requested, graph, shim_symbols)

    extra_text_ranges: List[tuple[int, int]] = []
    extra_ro_ranges: List[tuple[int, int]] = []
    data_bytes = b""
    data_relocations: List[DataRelocation] = []
    rw_base_vaddr: int | None = None

    def compute_text_min_page(symbols: Sequence[ResolvedSymbol], text_ranges: Sequence[tuple[int, int]]) -> int:
        addrs = [sym.address for sym in symbols if sym.defined and sym.st_type == STT_FUNC and sym.address]
        if text_ranges: addrs.append(min(start for start, _ in text_ranges))
        if not addrs: addrs = [sym.address for sym in symbols if sym.defined and sym.address]
        if not addrs: return TEXT_BASE_VADDR
        return align_down(min(addrs), PAGE_SIZE)

    if ko_path is not None:
        ko = KoFile(ko_path)
        layout = ko.compute_core_layout()

        def infer_module_core_base_kernel() -> int:
            for name in requested:
                found = ko.find_symbol(name)
                if found is None: continue
                _, ko_sym = found
                if ko_sym.is_undef: continue
                sec_off = layout.section_offsets.get(ko_sym.st_shndx)
                if sec_off is None: continue
                entry = graph.lookup(name)
                if entry is None: continue
                return entry.address - (sec_off + ko_sym.st_value)
            raise ValueError(f"{ko_path}: unable to anchor module layout to out.krg; no common symbol found")

        module_core_base_kernel = infer_module_core_base_kernel()
        text_kernel_start = module_core_base_kernel + layout.text_start
        text_kernel_end = module_core_base_kernel + layout.text_end
        if text_kernel_end > text_kernel_start: extra_text_ranges.append((text_kernel_start, text_kernel_end))
        ro_kernel_start = module_core_base_kernel + layout.ro_start
        ro_kernel_end = module_core_base_kernel + layout.ro_end
        if ro_kernel_end > ro_kernel_start: extra_ro_ranges.append((ro_kernel_start, ro_kernel_end))
        data_kernel_start = module_core_base_kernel + layout.data_start
        data_bytes = layout.data_image
        export_order = {name: idx for idx, name in enumerate(requested)}
        by_name: Dict[str, ResolvedSymbol] = {sym.name: sym for sym in resolved}

        def add_krg_closure(root_name: str) -> None:
            try: closure = graph.closure(root_name)
            except KeyError as exc: raise ValueError(f"{ko_path}: relocation references {root_name} but out.krg has no such symbol") from exc
            for entry in closure:
                module_name = "shim" if entry.name in shim_symbols else (entry.module_name or "kernel")
                is_shim = module_name == "shim"
                expected_type = STT_FUNC if entry.kind == 0 else STT_OBJECT
                is_export = entry.name in export_order
                sym = by_name.get(entry.name)
                if sym is None:
                    sym = ResolvedSymbol(
                        name=entry.name, source=LIB_SHIM if is_shim else owner_lib, defined=not is_shim,
                        exported=is_export, st_type=expected_type, size=entry.size,
                        address=entry.address if not is_shim else 0,
                        export_order=export_order.get(entry.name, len(resolved)), original_order=len(resolved),
                        module_id=entry.module_id, module_name=module_name,
                    )
                    resolved.append(sym)
                    by_name[entry.name] = sym
                else:
                    if is_export and not sym.exported:
                        sym.exported = True
                        sym.export_order = export_order[entry.name]
                if is_shim and LIB_SHIM not in needed_libs: needed_libs.append(LIB_SHIM)

        # 核心修复 1&2：扩展依赖闭包，包括外部 undef 和内部 data/bss/rodata
        for reloc in layout.data_relocs:
            if reloc.r_type != R_X86_64_64: continue
            
            name = reloc.symbol_name
            if not name:
                if reloc.sym_shndx is not None and reloc.sym_shndx < len(ko.sections):
                    sec_name = ko.sections[reloc.sym_shndx].name or ".internal"
                    name = f"{sec_name}+0x{reloc.sym_value:x}"
                else:
                    name = f".internal+0x{reloc.sym_value:x}"

            if reloc.is_undef:
                if name in shim_symbols:
                    if name not in by_name:
                        sym = ResolvedSymbol(
                            name=name, source=LIB_SHIM, defined=False, exported=False,
                            st_type=STT_FUNC, module_name="shim",
                            export_order=export_order.get(name, len(resolved)), original_order=len(resolved)
                        )
                        resolved.append(sym)
                        by_name[name] = sym
                    if LIB_SHIM not in needed_libs: needed_libs.append(LIB_SHIM)
                elif name not in by_name:
                    add_krg_closure(name)
            else:
                # 处理内部已定义符号的绝对地址重定位
                if name not in by_name:
                    sec_off = layout.section_offsets.get(reloc.sym_shndx, 0)
                    addr = module_core_base_kernel + sec_off + reloc.sym_value
                    st_type_extra = STT_OBJECT
                    if reloc.sym_shndx is not None and reloc.sym_shndx < len(ko.sections):
                        if ko.sections[reloc.sym_shndx].sh_flags & SHF_EXECINSTR:
                            st_type_extra = STT_FUNC
                    sym = ResolvedSymbol(
                        name=name, source=owner_lib, defined=True, exported=False,
                        st_type=st_type_extra, size=0, address=addr, module_name=owner_module,
                        export_order=len(resolved), original_order=len(resolved),
                    )
                    resolved.append(sym)
                    by_name[name] = sym

        text_min_page = compute_text_min_page(resolved, extra_text_ranges)
        rw_base_vaddr = TEXT_BASE_VADDR + (data_kernel_start - text_min_page)

        # 核心修复 3：生成 .so 重定位，将内部/外部目标全部无差别写入 .rela.dyn
        for reloc in layout.data_relocs:
            if reloc.r_type != R_X86_64_64:
                raise ValueError(f"{ko_path}: unsupported pseudo-GOT relocation type {reloc.r_type}")
            name = reloc.symbol_name
            if not name:
                if reloc.sym_shndx is not None and reloc.sym_shndx < len(ko.sections):
                    name = f"{ko.sections[reloc.sym_shndx].name}+0x{reloc.sym_value:x}"
                else:
                    name = f".internal+0x{reloc.sym_value:x}"
            target = by_name[name]
            data_relocations.append(DataRelocation(offset=reloc.offset, symbol=target, addend=reloc.addend, r_type=R_X86_64_64))

    synthetic_text_pages = build_builtin_thunk_pages(resolved, builtin_thunk_shims)

    dep_modules = ["shim"] if LIB_SHIM in needed_libs else []
    module_deps_path = symbols_path.parent / "module_deps.txt"
    module_deps_path.write_text("".join(format_module_deps(owner_module, dep_modules, resolved)))
    if symbol_dump_path is not None:
        dump_symbol_addresses_all([(owner_module, resolved)], symbol_dump_path)

    builder = ManualElfBuilder(
        symbols=resolved, needed_libraries=needed_libs, export_stub_size=export_stub_size,
        data_bytes=data_bytes, data_relocations=data_relocations, rw_base_vaddr=rw_base_vaddr,
        extra_text_ranges=extra_text_ranges, extra_ro_ranges=extra_ro_ranges,
        synthetic_text_pages=synthetic_text_pages,
    )
    builder.write(Path(owner_lib))

def main() -> None:
    parser = argparse.ArgumentParser(description="Build a sparse kernel-mapped .so")
    parser.add_argument("--symbols", type=Path, default=Path("symbols.txt"))
    parser.add_argument("--symbol-addresses", type=Path, default=Path("resolved_symbol_addresses.txt"))
    parser.add_argument("--skip-symbol-addresses", action="store_true")
    parser.add_argument("--krg", type=Path, default=None)
    parser.add_argument("--export-stub-size", type=lambda x: int(x, 0), default=DEFAULT_EXPORT_STUB_SIZE)
    parser.add_argument("--shim-list", type=Path, default=Path("shim.txt"))
    parser.add_argument("--ko", type=Path, default=None)
    args = parser.parse_args()
    krg_path = args.krg
    if krg_path is None:
        krg_path = infer_default_krg_path()
        if krg_path is None: parser.error("Unable to locate out.krg automatically; provide --krg")
    if not krg_path.exists(): parser.error(f"{krg_path} does not exist")
    symbol_dump_path = None if args.skip_symbol_addresses else args.symbol_addresses
    build_shared_object(symbols_path=args.symbols, krg_path=krg_path, export_stub_size=args.export_stub_size, symbol_dump_path=symbol_dump_path, shim_list_path=args.shim_list, ko_path=args.ko)

if __name__ == "__main__":
    main()
