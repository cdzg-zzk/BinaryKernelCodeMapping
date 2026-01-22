#!/usr/bin/env python3
"""
LKM pseudo-GOT shared library builder.

Inputs:
  - symbols.txt     : root export symbols (one per line, # comments)
  - kernel_cgd/src/out.krg : dependency closure with runtime addresses
  - shim.txt        : symbols that must remain imports (DT_NEEDED: libshim.so)

Outputs:
  - resolved_symbol_addresses.txt (name,addr,size,module_path)
  - lib<module>.so  : sparse ET_DYN preserving module/kernel layout, pseudo-GOT via .rela.dyn

Simplified rules:
  - All roots must belong to the same LKM owner; only [kernel] and that LKM may appear.
  - Any additional LKM in the closure -> hard error.
  - Pseudo-GOT relocations come from the owner's .ko .rela.data; only R_X86_64_64 handled.
  - Relocations are kept only when the target symbol is in the resolved closure.
  - Shim symbols stay undefined, add DT_NEEDED libshim.so; everything else is defined inside.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

# Reuse heavy lifting from build_PIC_so
from build_PIC_so import (
    DataRelocation,
    LIB_SHIM,
    ManualElfBuilder,
    PAGE_SIZE,
    R_X86_64_64,
    SHN_UNDEF,
    STT_FUNC,
    STT_OBJECT,
    TEXT_BASE_VADDR,
    align_down,
    parse_symbol_requests,
    load_shim_symbols,
    KoFile,
    KrgGraph,
    ResolvedSymbol,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def module_name_from_path(module_path: str) -> str:
    if module_path == "[kernel]":
        return "kernel"
    base = Path(module_path).name
    for ext in (".ko.xz", ".ko.gz", ".ko.zst", ".ko"):
        if base.endswith(ext):
            base = base[: -len(ext)]
            break
    return base


def module_to_lib(module_path: str) -> str:
    return f"lib{module_name_from_path(module_path)}.so"


def compute_text_min_page(
    symbols: Sequence[ResolvedSymbol],
    extra_ranges: Sequence[Tuple[int, int]],
    data_start: int | None = None,
) -> int:
    addrs: List[int] = [
        sym.address for sym in symbols if sym.defined and sym.st_type == STT_FUNC and sym.address
    ]
    if extra_ranges:
        addrs.append(min(start for start, _ in extra_ranges))
    if data_start is not None:
        addrs.append(data_start)
    if not addrs:
        return TEXT_BASE_VADDR
    return align_down(min(addrs), PAGE_SIZE)


def write_resolved_addresses(
    entries: Sequence[Tuple[str, int, int, int, str]], output_path: Path
) -> None:
    lines: List[str] = []
    for name, addr, size, kind, module in entries:
        lines.append(f"{name},0x{addr:x},0x{size:x},{module},{kind}\n")
    output_path.write_text("".join(lines))


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------


def build_lkm_so(
    symbols_path: Path,
    krg_path: Path,
    shim_list_path: Path,
    shim_lib_path: Path,
) -> None:
    requested = parse_symbol_requests(symbols_path)
    if not requested:
        raise ValueError("symbols.txt provided no symbols")

    shim_symbols = load_shim_symbols(shim_list_path)
    shim_label = str(shim_lib_path.resolve())
    graph = KrgGraph(krg_path)
    base_stop_names: Set[str] = {
        "__kmalloc",
        "kmalloc",
        "kfree",
        "printk",
        "vprintk",
        "kstrdup",
        "ktime_get",
        "ktime_get_ns",
        "ktime_get_real_ts64",
        "do_gettimeofday",
    }

    # Resolve root symbols and owner module
    owner_module_path: str | None = None
    resolved_nodes: Dict[str, Tuple[str, int, int, int, str]] = {}
    for name in requested:
        node = graph.lookup(name)
        if node is None:
            raise ValueError(f"{name}: not found in {krg_path}")
        if owner_module_path is None and node.module_name != "[kernel]":
            owner_module_path = node.module_name
        resolved_nodes[name] = (node.name, node.address, node.size, node.kind, node.module_name)
    if owner_module_path is None:
        raise ValueError("Root symbols belong to [kernel]; expected an LKM owner")

    owner_lib = module_to_lib(owner_module_path)

    # Load owner .ko layout and compute which data relocations are shim-provided.
    ko_path = Path(owner_module_path)
    if not ko_path.exists():
        raise FileNotFoundError(f"{ko_path} not found (owner module .ko required)")
    ko = KoFile(ko_path)
    layout = ko.compute_core_layout()
    shim_reloc_targets: Set[str] = {
        r.symbol_name
        for r in layout.data_relocs
        if r.is_undef and r.symbol_name
    } & shim_symbols

    # Closure traversal stops at base_stop_names and any data-reloc symbol provided by shim.
    stop_names = set(base_stop_names) | shim_reloc_targets

    # Traverse closure for all requested symbols
    modules_seen: Set[str] = set()
    for root in requested:
        for node in graph.closure(root, stop_names=stop_names):
            modules_seen.add(node.module_name)
            if node.name not in resolved_nodes:
                resolved_nodes[node.name] = (
                    node.name,
                    node.address,
                    node.size,
                    node.kind,
                    node.module_name,
                )

    # Enforce module constraint: only owner + [kernel]
    extra_modules = {m for m in modules_seen if m not in {owner_module_path, "[kernel]", "kernel"}}
    if extra_modules:
        raise ValueError(f"Unexpected modules in closure: {', '.join(sorted(extra_modules))}")

    # Anchor module base using any owner symbol present in both ko and krg
    def infer_module_core_base(resolved_ordered_norm) -> int:
        for sym_name, addr, _, _, module_name in resolved_ordered_norm:
            if module_name != owner_module_path:
                continue
            found = ko.find_symbol(sym_name)
            if found is None:
                continue
            _, sym = found
            if sym.is_undef or sym.st_shndx == SHN_UNDEF:
                continue
            sec_off = layout.section_offsets.get(sym.st_shndx)
            if sec_off is None:
                continue
            return addr - (sec_off + sym.st_value)
        raise ValueError(f"{ko_path}: unable to anchor module layout; no shared symbol with out.krg")

    def module_label(m: str) -> str:
        if m in ("[kernel]", "kernel"):
            return "kernel"
        if m == "shim":
            return shim_label
        return m

    # Build symbol table (include code + data/rodata to surface dependencies)
    export_order = {name: idx for idx, name in enumerate(requested)}
    resolved_syms: List[ResolvedSymbol] = []
    by_name: Dict[str, ResolvedSymbol] = {}
    needed_libs: List[str] = []
    # Initial order to anchor module base
    resolved_ordered_raw = sorted(resolved_nodes.values(), key=lambda x: x[0])
    resolved_ordered = []
    for name, addr, size, kind, mod in resolved_ordered_raw:
        use_shim = name in shim_reloc_targets
        mod_out = shim_label if use_shim else module_label(mod)
        resolved_ordered.append((name, addr, size, kind, mod_out))

    module_core_base = infer_module_core_base(resolved_ordered)
    text_kernel_start = module_core_base + layout.text_start
    text_kernel_end = module_core_base + layout.text_end
    ro_kernel_start = module_core_base + layout.ro_start
    ro_kernel_end = module_core_base + layout.ro_end
    data_kernel_start = module_core_base + layout.data_start

    # Add rodata dependencies (defined in owner .ko) so they appear in resolved_symbol_addresses.txt
    # Filter: reloc target is alloc ro (SHF_ALLOC set, no WRITE, no EXEC)
    SHF_WRITE = 0x1
    SHF_ALLOC = 0x2
    SHF_EXECINSTR = 0x4
    for reloc in layout.data_relocs:
        if reloc.is_undef:
            continue
        sec_idx = reloc.sym_shndx
        if sec_idx is None or sec_idx >= len(ko.sections):
            continue
        sec = ko.sections[sec_idx]
        if not (sec.sh_flags & SHF_ALLOC):
            continue
        if (sec.sh_flags & SHF_WRITE) or (sec.sh_flags & SHF_EXECINSTR):
            continue
        name = reloc.symbol_name or f".rodata+0x{reloc.sym_value:x}"
        if name in resolved_nodes:
            continue
        sec_off = layout.section_offsets.get(sec_idx)
        if sec_off is None:
            continue
        addr = module_core_base + sec_off + reloc.sym_value
        size = max(0, ro_kernel_end - addr)
        resolved_nodes[name] = (name, addr, size, 1, owner_module_path)

    # Recompute ordered list including rodata
    resolved_ordered_raw = sorted(resolved_nodes.values(), key=lambda x: x[0])
    resolved_ordered = []
    for name, addr, size, kind, mod in resolved_ordered_raw:
        use_shim = name in shim_reloc_targets
        mod_out = shim_label if use_shim else module_label(mod)
        resolved_ordered.append((name, addr, size, kind, mod_out))

    # Use actual ranges from module layout to place logical text/rodata.
    extra_text_ranges: List[Tuple[int, int]] = [(text_kernel_start, text_kernel_end)]
    extra_ro_ranges: List[Tuple[int, int]] = [(ro_kernel_start, ro_kernel_end)]

    def normalize_module(m: str) -> str:
        return "kernel" if m in ("[kernel]", "kernel") else m

    def is_ro_symbol(sym_name: str) -> bool:
        # Treat synthetic .rodata+... as ro
        if sym_name.startswith(".rodata+"):
            return True
        found = ko.find_symbol(sym_name)
        if not found:
            return False
        _, sym = found
        if sym.is_undef or sym.st_shndx == SHN_UNDEF:
            return False
        sec = ko.sections[sym.st_shndx]
        flags = sec.sh_flags
        SHF_WRITE = 0x1
        SHF_ALLOC = 0x2
        SHF_EXECINSTR = 0x4
        return (flags & SHF_ALLOC) and not (flags & SHF_WRITE) and not (flags & SHF_EXECINSTR)

    for name, addr, size, kind, module_name in resolved_ordered:
        is_shim = name in shim_reloc_targets
        if is_shim and LIB_SHIM not in needed_libs:
            needed_libs.append(LIB_SHIM)
        st_type = STT_FUNC if kind == 0 else STT_OBJECT
        if kind == 1 and not is_ro_symbol(name):
            continue
        sym = ResolvedSymbol(
            name=name,
            source=LIB_SHIM if is_shim else owner_lib,
            defined=not is_shim,
            exported=name in export_order,
            st_type=st_type,
            size=size,
            address=addr if not is_shim else 0,
            export_order=export_order.get(name, len(resolved_syms)),
            original_order=len(resolved_syms),
            module_id=0,
            module_name=shim_label if is_shim else module_label(module_name),
        )
        resolved_syms.append(sym)
        by_name[name] = sym

    # Build .rela.dyn from .rela.data (pseudo-GOT)
    resolved_name_set = set(by_name.keys())
    data_relocs: List[DataRelocation] = []
    skipped_relocs = 0
    for reloc in layout.data_relocs:
        if reloc.r_type != R_X86_64_64:
            raise ValueError(f"{ko_path}: unsupported relocation type {reloc.r_type} (expect R_X86_64_64)")
        sym_name = reloc.symbol_name
        if not sym_name and not reloc.is_undef:
            if reloc.sym_shndx is not None and reloc.sym_shndx < len(ko.sections):
                sec_name = ko.sections[reloc.sym_shndx].name or ".rodata"
                sym_name = f"{sec_name}+0x{reloc.sym_value:x}"
            else:
                sym_name = f".rodata+0x{reloc.sym_value:x}"
        if not sym_name:
            raise ValueError(f"{ko_path}: relocation with empty symbol name (idx={reloc.sym_idx})")

        # Determine if target is rodata (defined in owner, RO section)
        is_ro_target = False
        if not reloc.is_undef and reloc.sym_shndx is not None and reloc.sym_shndx < len(ko.sections):
            sec = ko.sections[reloc.sym_shndx]
            flags = sec.sh_flags
            SHF_WRITE = 0x1
            SHF_ALLOC = 0x2
            SHF_EXECINSTR = 0x4
            is_ro_target = (flags & SHF_ALLOC) and not (flags & SHF_WRITE) and not (flags & SHF_EXECINSTR)

        is_shim_target = sym_name in shim_reloc_targets
        target = by_name.get(sym_name)
        if target is None:
            if reloc.is_undef:
                node = graph.lookup(sym_name)
                if node is None:
                    raise ValueError(f"{ko_path}: relocation target {sym_name} not present in out.krg")
                if node.module_name not in {owner_module_path, "[kernel]", "kernel"}:
                    raise ValueError(f"{ko_path}: relocation target {node.name} is in unexpected module {node.module_name}")
                st_type_extra = STT_FUNC if node.kind == 0 else STT_OBJECT
                target = ResolvedSymbol(
                    name=node.name,
                    source=LIB_SHIM if is_shim_target else owner_lib,
                    defined=not is_shim_target,
                    exported=False,
                    st_type=st_type_extra,
                    size=node.size,
                    address=0 if is_shim_target else node.address,
                    export_order=len(resolved_syms),
                    original_order=len(resolved_syms),
                    module_id=node.module_id,
                    module_name=shim_label if is_shim_target else module_label(node.module_name),
                )
                resolved_nodes[node.name] = (
                    node.name,
                    node.address,
                    node.size,
                    node.kind,
                    shim_label if is_shim_target else module_label(node.module_name),
                )
            else:
                # Defined target (e.g., rodata), synthesize symbol
                sec_off = layout.section_offsets.get(reloc.sym_shndx)
                if sec_off is None:
                    skipped_relocs += 1
                    continue
                addr = module_core_base + sec_off + reloc.sym_value
                st_type_extra = STT_OBJECT
                size_extra = max(0, ro_kernel_end - addr)
                target = ResolvedSymbol(
                    name=reloc.symbol_name,
                    source=owner_lib,
                    defined=True,
                    exported=False,
                    st_type=st_type_extra,
                    size=size_extra,
                    address=addr,
                    export_order=len(resolved_syms),
                    original_order=len(resolved_syms),
                    module_id=0,
                    module_name=owner_module_path,
                )
                resolved_nodes[target.name] = (target.name, addr, 0, 1, owner_module_path)
            resolved_syms.append(target)
            by_name[target.name] = target
            resolved_name_set.add(target.name)

        if is_shim_target and LIB_SHIM not in needed_libs:
            needed_libs.append(LIB_SHIM)
        # If target is rodata defined symbol, ensure it is treated as defined and not shim
        data_relocs.append(
            DataRelocation(
                offset=reloc.offset,
                symbol=target,
                addend=reloc.addend,
                r_type=R_X86_64_64,
            )
        )

    # Build address ranges for code and data (module + kernel), preserving original spacing.
    text_min_page = compute_text_min_page(
        resolved_syms,
        extra_text_ranges,
        data_kernel_start if layout.data_image else None,
    )
    builder = ManualElfBuilder(
        symbols=resolved_syms,
        needed_libraries=needed_libs,
        export_stub_size=1,
        ro_bytes=layout.ro_image,
        data_bytes=layout.data_image,
        data_relocations=data_relocs,
        rw_base_vaddr=TEXT_BASE_VADDR + (data_kernel_start - text_min_page),
        extra_text_ranges=extra_text_ranges,
        extra_ro_ranges=extra_ro_ranges,
        owner_module_name=None,
        include_data=True,
        text_min_override=text_min_page,
    )
    output_path = Path(module_to_lib(owner_module_path))
    builder.write(output_path)

    # Emit resolved_symbol_addresses.txt with all krg-derived symbols (normalized modules)
    resolved_out = []
    for name, addr, size, kind, mod in sorted(resolved_nodes.values(), key=lambda x: x[0]):
        if kind == 1:
            size = size if size > 0 else max(0, ro_kernel_end - addr)
        if kind == 1 and not is_ro_symbol(name):
            continue
        use_shim = name in shim_reloc_targets
        mod_out = shim_label if use_shim else module_label(mod)
        resolved_out.append((name, addr, size, kind, mod_out))
    write_resolved_addresses(resolved_out, symbols_path.parent / "resolved_symbol_addresses.txt")

    print(f"Built {output_path} (shim deps: {', '.join(needed_libs) if needed_libs else 'none'}, skipped_relocs={skipped_relocs})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Build sparse .so for a single LKM with pseudo-GOT.")
    parser.add_argument("--symbols", type=Path, default=Path("symbols.txt"), help="Root export symbols file")
    parser.add_argument("--krg", type=Path, default=Path("../kernel_cgd/src/out.krg"), help="out.krg path")
    parser.add_argument("--shim", type=Path, default=Path("shim.txt"), help="shim symbol list")
    parser.add_argument("--shim-lib", type=Path, default=Path("libshim.so"), help="shim library path label")
    args = parser.parse_args()

    if not args.krg.exists():
        parser.error(f"{args.krg} does not exist")

    build_lkm_so(
        symbols_path=args.symbols,
        krg_path=args.krg,
        shim_list_path=args.shim,
        shim_lib_path=args.shim_lib,
    )


if __name__ == "__main__":
    main()
