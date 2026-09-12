#!/usr/bin/env python3
"""Materialize an ACTIVE carrier's code without changing its ELF layout."""
import argparse
import json
import os
from pathlib import Path

PAGE = 4096


def mappings(path):
    result = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        offset, address, kind, section = line.split(",")
        item = (int(offset, 0), int(address, 0), kind, section)
        if item[0] % PAGE or item[1] % PAGE or kind not in {"text", "rodata", "shared_data"}:
            raise ValueError("unsupported or unaligned carrier mapping")
        result.append(item)
    if not result or len({r[0] for r in result}) != len(result):
        raise ValueError("missing/duplicate carrier mappings")
    return result


def materialize(active_carrier, page_map, destination):
    plan = mappings(page_map)
    if not any(row[2] == "shared_data" for row in plan):
        raise ValueError("Clocktime comparison requires shared_data")
    # Explicit reads see the registered page cache. Do not use filesystem cloning.
    data = bytearray(active_carrier.read_bytes())
    if data[:4] != b"\x7fELF":
        raise ValueError("carrier is not ELF")
    shared = []
    for offset, address, kind, section in plan:
        if offset + PAGE > len(data):
            raise ValueError("mapping exceeds carrier size")
        if kind == "shared_data":
            shared.append(f"{offset:#x},{address:#x},{kind},{section}\n")
            data[offset:offset + PAGE] = bytes(PAGE)
        elif kind == "text" and not any(data[offset:offset + PAGE]):
            raise ValueError("source text is sparse: source carrier must be actively registered")
    destination.mkdir()
    (destination / "libkernel.so").write_bytes(data)
    (destination / "page_mappings.txt").write_text(
        "# file_offset,kernel_vaddr,kind,section\n" + "".join(shared))
    (destination / "materialization.json").write_text(json.dumps({
        "method": "compact-split", "source": str(active_carrier.resolve()),
        "code_layout": "unchanged ELF offsets and full runtime page bytes",
        "copied_pages": sum(r[2] != "shared_data" for r in plan),
        "shared_state_pages": len(shared),
        "kernel_implementation": "unchanged VKSO kernel",
    }, indent=2) + "\n")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("active_carrier", type=Path)
    parser.add_argument("page_map", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("run inside the controlled active-registration collection session")
    materialize(args.active_carrier, args.page_map, args.destination)


if __name__ == "__main__":
    main()
