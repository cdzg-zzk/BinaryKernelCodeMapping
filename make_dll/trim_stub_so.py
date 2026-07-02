#!/usr/bin/env python3
"""
Trim a synthetic sparse stub DSO produced by build_LKM_so.py.

Goal (microbench only):
  - Drop the empty .rodata PT_LOAD (1 page, all zeros).
  - Drop the unused first page of the RW PT_LOAD (named ".data" in current layout),
    keeping only the dyn metadata page (.dynstr/.dynsym/.gnu.hash/.dynamic).
  - Punch a hole for the dropped .data page so it does not consume disk blocks.

This tool patches ELF headers *in place* on a copied output file to preserve sparseness.
"""

from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PT_NULL = 0
PT_LOAD = 1
PT_DYNAMIC = 2

PF_X = 1
PF_W = 2
PF_R = 4

SHT_NULL = 0
SHT_RELA = 4

# Dynamic tags we may need to strip when dropping the pseudo-GOT data page.
DT_NULL = 0
DT_RELA = 7
DT_RELASZ = 8
DT_RELAENT = 9
# GNU extension: number of relative relocations; safe to drop alongside DT_RELA*.
DT_RELACOUNT = 0x6FFFFFF9


@dataclass(frozen=True)
class Elf64Ehdr:
    e_phoff: int
    e_shoff: int
    e_phentsize: int
    e_phnum: int
    e_shentsize: int
    e_shnum: int
    e_shstrndx: int


@dataclass
class Elf64Phdr:
    p_type: int
    p_flags: int
    p_offset: int
    p_vaddr: int
    p_paddr: int
    p_filesz: int
    p_memsz: int
    p_align: int


@dataclass
class Elf64Shdr:
    sh_name: int
    sh_type: int
    sh_flags: int
    sh_addr: int
    sh_offset: int
    sh_size: int
    sh_link: int
    sh_info: int
    sh_addralign: int
    sh_entsize: int


def _die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _read_exact(path: Path) -> bytes:
    return path.read_bytes()


def _parse_ehdr(data: bytes) -> Elf64Ehdr:
    if data[:4] != b"\x7fELF":
        _die("not an ELF file")
    ei_class = data[4]
    ei_data = data[5]
    if ei_class != 2:
        _die(f"unsupported ELF class: {ei_class} (need ELF64)")
    if ei_data != 1:
        _die(f"unsupported ELF endianness: {ei_data} (need little-endian)")

    # Elf64_Ehdr after e_ident (16 bytes)
    (
        _e_type,
        _e_machine,
        _e_version,
        _e_entry,
        e_phoff,
        e_shoff,
        _e_flags,
        _e_ehsize,
        e_phentsize,
        e_phnum,
        e_shentsize,
        e_shnum,
        e_shstrndx,
    ) = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)

    if e_phentsize != 56:
        _die(f"unexpected e_phentsize={e_phentsize} (need 56)")
    if e_shentsize != 64:
        _die(f"unexpected e_shentsize={e_shentsize} (need 64)")
    return Elf64Ehdr(
        e_phoff=e_phoff,
        e_shoff=e_shoff,
        e_phentsize=e_phentsize,
        e_phnum=e_phnum,
        e_shentsize=e_shentsize,
        e_shnum=e_shnum,
        e_shstrndx=e_shstrndx,
    )


def _parse_phdrs(data: bytes, eh: Elf64Ehdr) -> list[Elf64Phdr]:
    out: list[Elf64Phdr] = []
    for i in range(eh.e_phnum):
        off = eh.e_phoff + i * eh.e_phentsize
        (
            p_type,
            p_flags,
            p_offset,
            p_vaddr,
            p_paddr,
            p_filesz,
            p_memsz,
            p_align,
        ) = struct.unpack_from("<IIQQQQQQ", data, off)
        out.append(
            Elf64Phdr(
                p_type=p_type,
                p_flags=p_flags,
                p_offset=p_offset,
                p_vaddr=p_vaddr,
                p_paddr=p_paddr,
                p_filesz=p_filesz,
                p_memsz=p_memsz,
                p_align=p_align,
            )
        )
    return out


def _parse_shdrs(data: bytes, eh: Elf64Ehdr) -> list[Elf64Shdr]:
    out: list[Elf64Shdr] = []
    for i in range(eh.e_shnum):
        off = eh.e_shoff + i * eh.e_shentsize
        (
            sh_name,
            sh_type,
            sh_flags,
            sh_addr,
            sh_offset,
            sh_size,
            sh_link,
            sh_info,
            sh_addralign,
            sh_entsize,
        ) = struct.unpack_from("<IIQQQQIIQQ", data, off)
        out.append(
            Elf64Shdr(
                sh_name=sh_name,
                sh_type=sh_type,
                sh_flags=sh_flags,
                sh_addr=sh_addr,
                sh_offset=sh_offset,
                sh_size=sh_size,
                sh_link=sh_link,
                sh_info=sh_info,
                sh_addralign=sh_addralign,
                sh_entsize=sh_entsize,
            )
        )
    return out


def _get_section_names(data: bytes, eh: Elf64Ehdr, shdrs: list[Elf64Shdr]) -> list[str]:
    if eh.e_shstrndx >= len(shdrs):
        _die("e_shstrndx out of range")
    shstr = shdrs[eh.e_shstrndx]
    if shstr.sh_offset + shstr.sh_size > len(data):
        _die("shstrtab out of file bounds")
    blob = data[shstr.sh_offset : shstr.sh_offset + shstr.sh_size]

    names: list[str] = []
    for sh in shdrs:
        if sh.sh_name == 0:
            names.append("")
            continue
        if sh.sh_name >= len(blob):
            names.append("")
            continue
        end = blob.find(b"\x00", sh.sh_name)
        if end == -1:
            end = len(blob)
        names.append(blob[sh.sh_name:end].decode("utf-8", "replace"))
    return names


def _pack_phdr(ph: Elf64Phdr) -> bytes:
    return struct.pack(
        "<IIQQQQQQ",
        ph.p_type,
        ph.p_flags,
        ph.p_offset,
        ph.p_vaddr,
        ph.p_paddr,
        ph.p_filesz,
        ph.p_memsz,
        ph.p_align,
    )


def _pack_shdr(sh: Elf64Shdr) -> bytes:
    return struct.pack(
        "<IIQQQQIIQQ",
        sh.sh_name,
        sh.sh_type,
        sh.sh_flags,
        sh.sh_addr,
        sh.sh_offset,
        sh.sh_size,
        sh.sh_link,
        sh.sh_info,
        sh.sh_addralign,
        sh.sh_entsize,
    )


def _null_shdr() -> Elf64Shdr:
    return Elf64Shdr(
        sh_name=0,
        sh_type=SHT_NULL,
        sh_flags=0,
        sh_addr=0,
        sh_offset=0,
        sh_size=0,
        sh_link=0,
        sh_info=0,
        sh_addralign=0,
        sh_entsize=0,
    )


def _compact_program_headers(dst: Path, eh: Elf64Ehdr, phdrs: list[Elf64Phdr]) -> int:
    kept: list[Elf64Phdr] = [ph for ph in phdrs if ph.p_type != PT_NULL]
    if len(kept) == len(phdrs):
        return len(phdrs)
    if not any(ph.p_type == PT_DYNAMIC for ph in kept):
        _die("PT_DYNAMIC missing after program-header compaction")

    with dst.open("r+b") as f:
        for i, ph in enumerate(kept):
            f.seek(eh.e_phoff + i * eh.e_phentsize)
            f.write(_pack_phdr(ph))
        # Update e_phnum in ELF header (offset 56 in Elf64_Ehdr).
        f.seek(56)
        f.write(struct.pack("<H", len(kept)))
    return len(kept)


def _compact_section_headers(dst: Path, eh: Elf64Ehdr, shdrs: list[Elf64Shdr]) -> int:
    if eh.e_shoff == 0 or eh.e_shnum == 0:
        return 0

    keep_indices: list[int] = []
    for i, sh in enumerate(shdrs):
        if i == 0:
            keep_indices.append(i)
            continue
        if sh.sh_type != SHT_NULL:
            keep_indices.append(i)

    if len(keep_indices) == len(shdrs):
        return len(shdrs)

    mapping = {old: new for new, old in enumerate(keep_indices)}
    if eh.e_shstrndx not in mapping:
        _die("section header string table removed unexpectedly")

    new_shdrs: list[Elf64Shdr] = []
    for old_idx in keep_indices:
        sh = shdrs[old_idx]
        if sh.sh_link != 0:
            if sh.sh_link not in mapping:
                _die(f"section sh_link points to removed section: old={old_idx} link={sh.sh_link}")
            sh = Elf64Shdr(
                sh_name=sh.sh_name,
                sh_type=sh.sh_type,
                sh_flags=sh.sh_flags,
                sh_addr=sh.sh_addr,
                sh_offset=sh.sh_offset,
                sh_size=sh.sh_size,
                sh_link=mapping[sh.sh_link],
                sh_info=sh.sh_info,
                sh_addralign=sh.sh_addralign,
                sh_entsize=sh.sh_entsize,
            )
        new_shdrs.append(sh)

    with dst.open("r+b") as f:
        for i, sh in enumerate(new_shdrs):
            f.seek(eh.e_shoff + i * eh.e_shentsize)
            f.write(_pack_shdr(sh))
        # Update e_shnum (offset 60) and e_shstrndx (offset 62) in Elf64_Ehdr.
        f.seek(60)
        f.write(struct.pack("<H", len(new_shdrs)))
        f.write(struct.pack("<H", mapping[eh.e_shstrndx]))
    return len(new_shdrs)


def clean_stub_so_headers(src: Path, dst: Path) -> None:
    if not src.is_file():
        _die(f"no such file: {src}")
    if dst.exists():
        _die(f"output exists: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    _run(["cp", "--sparse=always", "--", str(src), str(dst)])

    data = _read_exact(dst)
    eh = _parse_ehdr(data)
    phdrs = _parse_phdrs(data, eh)
    shdrs = _parse_shdrs(data, eh) if eh.e_shoff and eh.e_shnum else []
    _compact_program_headers(dst, eh, phdrs)
    if shdrs:
        _compact_section_headers(dst, eh, shdrs)


def trim_stub_so(src: Path, dst: Path, *, page_size: int = 0x1000, punch_data_hole: bool = True) -> None:
    if not src.is_file():
        _die(f"no such file: {src}")
    if dst.exists():
        _die(f"output exists: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    # Preserve sparseness by copying with cp --sparse=always, then patch in-place.
    _run(["cp", "--sparse=always", "--", str(src), str(dst)])

    data = _read_exact(dst)
    eh = _parse_ehdr(data)
    phdrs = _parse_phdrs(data, eh)
    shdrs = _parse_shdrs(data, eh)
    names = _get_section_names(data, eh, shdrs)
    sec_index = {n: i for i, n in enumerate(names) if n}

    def sec(name: str) -> tuple[int, Elf64Shdr]:
        if name not in sec_index:
            _die(f"missing section {name} in {src.name}")
        idx = sec_index[name]
        return idx, shdrs[idx]

    ro_idx, ro_sh = sec(".rodata")
    da_idx, da_sh = sec(".data")
    dynstr_idx, dynstr_sh = sec(".dynstr")
    dynamic_idx, dynamic_sh = sec(".dynamic")
    rela_idx = sec_index.get(".rela.dyn")
    rela_sh = shdrs[rela_idx] if rela_idx is not None else None

    if ro_sh.sh_size != page_size:
        _die(f".rodata size is {ro_sh.sh_size:#x}, expected {page_size:#x}")
    if da_sh.sh_size != page_size:
        _die(f".data size is {da_sh.sh_size:#x}, expected {page_size:#x}")
    if dynstr_sh.sh_offset != da_sh.sh_offset + page_size:
        _die(
            f"unexpected layout: .dynstr offset {dynstr_sh.sh_offset:#x} "
            f"!= .data+page ({da_sh.sh_offset + page_size:#x})"
        )
    if dynamic_sh.sh_offset < dynstr_sh.sh_offset or dynamic_sh.sh_offset >= dynstr_sh.sh_offset + page_size:
        _die("unexpected layout: .dynamic is not in the dyn-metadata page")

    # Verify .rodata page is all zeros (safe to drop).
    ro_blob = data[ro_sh.sh_offset : ro_sh.sh_offset + ro_sh.sh_size]
    if any(b != 0 for b in ro_blob):
        _die(".rodata contains non-zero bytes; refusing to drop it")

    # Verify dynamic section has no pointers into the dropped .data page.
    data_addr_lo = da_sh.sh_addr
    data_addr_hi = da_sh.sh_addr + da_sh.sh_size
    dyn_blob = data[dynamic_sh.sh_offset : dynamic_sh.sh_offset + dynamic_sh.sh_size]
    if len(dyn_blob) % 16 != 0:
        _die("unexpected .dynamic size (not multiple of Elf64_Dyn)")
    dyn_entries: list[tuple[int, int]] = []
    for off in range(0, len(dyn_blob), 16):
        d_tag, d_val = struct.unpack_from("<QQ", dyn_blob, off)
        dyn_entries.append((d_tag, d_val))
        if d_tag == DT_NULL:
            break
        if data_addr_lo <= d_val < data_addr_hi:
            _die(f".dynamic entry points into .data page: tag={d_tag:#x} val={d_val:#x}")

    # If the stub includes pseudo-GOT relocations (.rela.dyn), trimming away the first RW page
    # would leave relocation targets unmapped. For disk/memory microbench stubs we do not need
    # relocations; drop them by:
    #  - removing DT_RELA/DT_RELASZ/DT_RELAENT (and DT_RELACOUNT if present) from .dynamic
    #  - hiding the .rela.dyn section (tools-only; loader ignores SHT_*)
    strip_relocations = False
    if rela_sh is not None and rela_sh.sh_type == SHT_RELA and rela_sh.sh_size:
        if rela_sh.sh_offset + rela_sh.sh_size > len(data):
            _die(".rela.dyn out of file bounds")
        if rela_sh.sh_entsize not in (0, 24):
            _die(f"unexpected .rela.dyn sh_entsize={rela_sh.sh_entsize} (need 24)")
        if rela_sh.sh_size % 24 != 0:
            _die(f"unexpected .rela.dyn sh_size={rela_sh.sh_size} (not multiple of 24)")

        # Sanity check: ensure all relocation writes target the dropped .data page.
        # If not, trimming this stub would silently break required relocations.
        for off in range(rela_sh.sh_offset, rela_sh.sh_offset + rela_sh.sh_size, 24):
            r_offset, _r_info, _r_addend = struct.unpack_from("<QQq", data, off)
            if not (data_addr_lo <= r_offset < data_addr_hi):
                _die(
                    "refusing to trim: .rela.dyn contains relocation with r_offset outside .data page "
                    f"(r_offset={r_offset:#x}, data=[{data_addr_lo:#x},{data_addr_hi:#x}))"
                )
        strip_relocations = True

    # Find the PT_LOAD covering .rodata and .data.
    ro_ph = None
    da_ph = None
    for i, ph in enumerate(phdrs):
        if ph.p_type != PT_LOAD:
            continue
        if ph.p_offset == ro_sh.sh_offset and ph.p_vaddr == ro_sh.sh_addr and ph.p_filesz == ro_sh.sh_size:
            ro_ph = i
        if ph.p_offset == da_sh.sh_offset and ph.p_vaddr == da_sh.sh_addr and ph.p_filesz >= da_sh.sh_size + 0x10:
            da_ph = i
    if ro_ph is None:
        _die("failed to locate PT_LOAD for .rodata")
    if da_ph is None:
        _die("failed to locate PT_LOAD for .data/.dyn*")

    # Sanity: expect .rodata PT_LOAD to be R-only, and data PT_LOAD to be RW.
    if phdrs[ro_ph].p_flags != PF_R:
        _die(f"unexpected .rodata PT_LOAD flags: {phdrs[ro_ph].p_flags:#x}")
    if phdrs[da_ph].p_flags != (PF_R | PF_W):
        _die(f"unexpected RW PT_LOAD flags: {phdrs[da_ph].p_flags:#x}")

    # Patch program headers.
    phdrs[ro_ph] = Elf64Phdr(p_type=PT_NULL, p_flags=0, p_offset=0, p_vaddr=0, p_paddr=0, p_filesz=0, p_memsz=0, p_align=0)

    rw = phdrs[da_ph]
    if rw.p_align != page_size:
        _die(f"unexpected RW PT_LOAD p_align={rw.p_align:#x} (need {page_size:#x})")
    if rw.p_offset % page_size != 0 or rw.p_vaddr % page_size != 0:
        _die("RW PT_LOAD is not page-aligned")
    if rw.p_filesz < page_size or rw.p_memsz < page_size:
        _die("RW PT_LOAD too small to drop the first page")
    rw.p_offset += page_size
    rw.p_vaddr += page_size
    rw.p_paddr += page_size
    rw.p_filesz -= page_size
    rw.p_memsz -= page_size
    if rw.p_filesz == 0 or rw.p_memsz == 0:
        _die("RW PT_LOAD became empty after trimming; refusing")
    phdrs[da_ph] = rw

    # Null out section headers for .rodata/.data (tools-only; loader ignores SHT_*).
    # We'll compact them away afterward so readelf output is clean.
    shdrs[ro_idx] = _null_shdr()
    shdrs[da_idx] = _null_shdr()
    if strip_relocations and rela_idx is not None:
        shdrs[rela_idx] = _null_shdr()

    # Write patched headers back.
    with dst.open("r+b") as f:
        # If requested, strip relocation-related dynamic tags in-place.
        if strip_relocations:
            kept: list[tuple[int, int]] = []
            for d_tag, d_val in dyn_entries:
                if d_tag in (DT_RELA, DT_RELASZ, DT_RELAENT, DT_RELACOUNT):
                    continue
                if d_tag == DT_NULL:
                    break
                kept.append((d_tag, d_val))

            total_slots = dynamic_sh.sh_size // 16
            needed_slots = len(kept) + 1  # + DT_NULL
            if needed_slots > total_slots:
                _die("internal error: stripped .dynamic does not fit in-place")

            f.seek(dynamic_sh.sh_offset)
            for d_tag, d_val in kept:
                f.write(struct.pack("<QQ", d_tag, d_val))
            f.write(struct.pack("<QQ", DT_NULL, 0))
            f.write(b"\x00" * ((total_slots - needed_slots) * 16))

        for i, ph in ((ro_ph, phdrs[ro_ph]), (da_ph, phdrs[da_ph])):
            off = eh.e_phoff + i * eh.e_phentsize
            f.seek(off)
            f.write(_pack_phdr(ph))
        for i in (ro_idx, da_idx):
            off = eh.e_shoff + i * eh.e_shentsize
            f.seek(off)
            f.write(_pack_shdr(shdrs[i]))
        if strip_relocations and rela_idx is not None:
            off = eh.e_shoff + rela_idx * eh.e_shentsize
            f.seek(off)
            f.write(_pack_shdr(shdrs[rela_idx]))

    # Remove the disk blocks contributed by the dropped .data page.
    if punch_data_hole:
        _run(
            [
                "fallocate",
                "--punch-hole",
                "--keep-size",
                "--offset",
                str(da_sh.sh_offset),
                "--length",
                str(da_sh.sh_size),
                str(dst),
            ]
        )

    # Compact away PT_NULL and extra SHT_NULL entries to avoid confusing readelf output.
    # This does not change runtime behavior (dynamic loader uses program headers only),
    # but makes the artifact easier to inspect and less error-prone for scripts.
    _compact_program_headers(dst, eh, phdrs)
    _compact_section_headers(dst, eh, shdrs)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Trim synthetic sparse stub DSOs (drop empty .rodata/.data pages).")
    ap.add_argument("so", nargs="+", type=Path, help="Input .so path(s)")
    ap.add_argument("--suffix", default=".trim.so", help="Output suffix (default: .trim.so)")
    ap.add_argument("--no-punch", action="store_true", help="Do not punch a hole for the dropped .data page")
    ap.add_argument(
        "--clean-only",
        action="store_true",
        help="Only compact ELF headers (remove PT_NULL / extra SHT_NULL); do not trim segments",
    )
    args = ap.parse_args(argv)

    for src in args.so:
        if src.suffix != ".so":
            _die(f"expected .so input, got: {src}")
        dst = src.with_name(src.stem + args.suffix)
        if args.clean_only:
            clean_stub_so_headers(src, dst)
            print(f"cleaned: {src} -> {dst}")
        else:
            trim_stub_so(src, dst, punch_data_hole=not args.no_punch)
            print(f"trimmed: {src} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
