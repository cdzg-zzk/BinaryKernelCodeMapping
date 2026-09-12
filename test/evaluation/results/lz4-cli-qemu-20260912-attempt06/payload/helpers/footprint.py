#!/usr/bin/env python3
"""Observe the loaded Clocktime carrier's PFNs; keep symbol sizes distinct."""
import argparse
import csv
import ctypes
import io
import json
import os
import struct
from pathlib import Path
from carrier import mappings


def observe(carrier, original_map, method):
    plan = mappings(original_map)
    library = ctypes.CDLL(str(carrier.resolve()))
    regions = []
    for line in Path("/proc/self/maps").read_text().splitlines():
        columns = line.split(maxsplit=5)
        if len(columns) == 6 and columns[5] == str(carrier.resolve()):
            start, end = [int(v, 16) for v in columns[0].split("-")]
            regions.append((start, end, int(columns[2], 16), columns[1]))
    kernel = Path("/sys/kernel/debug/vkso_kernel_reader")
    (kernel / "page_addresses").write_text(" ".join(hex(r[1]) for r in plan))
    kernel_pfns = {int(r["kernel_vaddr"], 0): int(r["pfn"])
                   for r in csv.DictReader(io.StringIO((kernel / "pages").read_text()))}
    pages = []
    with Path("/proc/self/pagemap").open("rb") as stream:
        for offset, address, kind, section in plan:
            # ld.so reserves the large holes between this carrier's PT_LOADs.
            # Those PROT_NONE VMAs can have overlapping apparent file offsets.
            region = next((r for r in regions if 'r' in r[3]
                           and r[2] <= offset < r[2] + r[1] - r[0]), None)
            if region is None:
                raise ValueError(f"carrier offset {offset:#x} is not mapped by ld.so")
            virtual = region[0] + offset - region[2]
            ctypes.string_at(virtual, 1)  # fault in the actual loader mapping
            stream.seek((virtual // 4096) * 8)
            entry, = struct.unpack("Q", stream.read(8))
            user_pfn = entry & ((1 << 55) - 1)
            if not entry & (1 << 63) or not user_pfn or address not in kernel_pfns:
                raise ValueError("PFN unavailable; root with pagemap access is required")
            shared = user_pfn == kernel_pfns[address]
            expected = method == "vkso" or kind == "shared_data"
            if shared != expected:
                raise ValueError(f"unexpected physical backing for {section}: shared={shared}")
            if "w" in region[3]:
                raise ValueError("reusable code/state page is user writable")
            pages.append(dict(kind=kind, section=section, file_offset=offset,
                              user_pfn=user_pfn, kernel_pfn=kernel_pfns[address], shared=shared))
    # Preserve real mapping accounting, including carrier-private support pages.
    smaps, selected = [], False
    for line in Path("/proc/self/smaps").read_text().splitlines():
        if line and "-" in line.split()[0]:
            selected = line.endswith(str(carrier.resolve()))
        if selected:
            smaps.append(line)
    return dict(method=method, pages=pages, carrier_smaps=smaps,
                distinct_source_pfns=len({r["kernel_pfn"] for r in pages}),
                distinct_user_pfns=len({r["user_pfn"] for r in pages}),
                source_user_union_pfns=len({r[k] for r in pages for k in ("user_pfn", "kernel_pfn")}),
                scope="declared closure pages; smaps adds carrier support, not whole-system net memory")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("carrier", type=Path)
    parser.add_argument("original_map", type=Path)
    parser.add_argument("method", choices=("vkso", "compact-split"))
    args = parser.parse_args()
    print(json.dumps(observe(args.carrier, args.original_map, args.method), indent=2))
