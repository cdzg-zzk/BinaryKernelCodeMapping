#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True)


def parse_sections(elf: Path) -> dict[str, tuple[int, int, int]]:
    out = run(["readelf", "-SW", str(elf)])
    sections: dict[str, tuple[int, int, int]] = {}
    pattern = re.compile(
        r"^\s*\[\s*(\d+)\]\s+(\S+)\s+\S+\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)"
    )
    for line in out.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        idx = match.group(1)
        name = match.group(2)
        addr = int(match.group(3), 16)
        off = int(match.group(4), 16)
        size = int(match.group(5), 16)
        sections[name] = (addr, off, size)
        sections[idx] = (addr, off, size)
    return sections


def parse_symbol(elf: Path, symbol: str) -> tuple[int, int, str]:
    out = run(["readelf", "-sW", str(elf)])
    pattern = re.compile(
        r"^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+)\s+\S+\s+\S+\s+\S+\s+(\S+)\s+(\S+)$"
    )
    for line in out.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        if match.group(4) != symbol:
            continue
        value = int(match.group(1), 16)
        size = int(match.group(2), 10)
        section = match.group(3)
        return value, size, section
    raise SystemExit(f"{elf}: symbol {symbol} not found")


def symbol_bytes(elf: Path, symbol: str) -> bytes:
    sections = parse_sections(elf)
    value, size, section = parse_symbol(elf, symbol)
    if section not in sections:
        raise SystemExit(f"{elf}: section {section} for {symbol} not found")
    section_addr, section_off, section_size = sections[section]
    offset_in_section = value - section_addr
    if offset_in_section < 0 or offset_in_section + size > section_size:
        raise SystemExit(f"{elf}: symbol {symbol} is outside section {section}")
    data = elf.read_bytes()
    start = section_off + offset_in_section
    return data[start : start + size]


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: compare_xxh32_bytes.py <zzk_xxh32_lkm.ko> <libclone_xxh32.so>", file=sys.stderr)
        return 2

    kernel_elf = Path(sys.argv[1])
    native_elf = Path(sys.argv[2])

    kernel = symbol_bytes(kernel_elf, "zzk_xxh32")
    native = symbol_bytes(native_elf, "clone_xxh32")

    common_len = len(native)
    if len(kernel) < common_len:
        print(f"FAIL: kernel symbol is shorter than native ({len(kernel)} < {common_len})")
        return 1

    if kernel[:common_len] != native:
        for idx, (kb, nb) in enumerate(zip(kernel, native)):
            if kb != nb:
                print(f"FAIL: byte mismatch at +0x{idx:x}: kernel=0x{kb:02x}, native=0x{nb:02x}")
                return 1
        print("FAIL: byte mismatch")
        return 1

    tail = kernel[common_len:]
    if tail and tail != b"\xcc" * len(tail):
        print(f"FAIL: kernel has non-int3 trailing bytes after native body: {tail.hex()}")
        return 1

    print(f"OK: first {common_len} bytes match exactly")
    if tail:
        print(f"OK: ignored {len(tail)} kernel-only int3 byte(s) after ret")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
