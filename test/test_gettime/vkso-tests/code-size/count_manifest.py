#!/usr/bin/env python3
"""Count ranges selected by the human-maintained semantic manifest.

This program deliberately contains no policy about what belongs to VKSO or
Raw vDSO.  It only validates paths/ranges and performs reproducible arithmetic
over source-manifest.tsv.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
DEFAULT_ROOTS = {
    "VKSO_PROJECT": REPO,
    "VKSO_KERNEL": REPO / "test/test_gettime/linux-5.15.198-vkso",
    "RAW_KERNEL": Path(os.environ.get(
        "RAW_KERNEL_ROOT", "/tmp/vkso-raw-audit-src-git"
    )),
}


def git43_tree() -> Path:
    override = os.environ.get("VKSO_GIT43_ROOT")
    if override:
        return Path(override)
    target = Path(tempfile.gettempdir()) / "vkso-code-size-git43"
    if not target.exists():
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(target), "43d41b2"],
            cwd=REPO, check=True, stdout=subprocess.DEVNULL,
        )
    return target


def parse_ranges(spec: str, line_count: int) -> list[int]:
    selected: set[int] = set()
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start_s, end_s = item.split("-", 1)
            start = int(start_s)
            end = int(end_s)
        else:
            start = end = int(item)
        if start < 1 or end < start:
            raise ValueError(f"invalid range {item!r}")
        if end > line_count:
            raise ValueError(
                f"range {item!r} exceeds file length {line_count}"
            )
        selected.update(range(start, end + 1))
    return sorted(selected)


def lexical_code_flags(path: Path, lines: list[str]) -> list[bool]:
    """Classify nonblank, non-comment lines; source semantics stay in TSV."""
    shell_style = (
        path.suffix in {".py", ".sh"}
        or path.name.startswith("Makefile")
        or path.name.startswith("Kconfig")
        or path.name in {"vkso"}
    )
    flags: list[bool] = []
    in_block = False
    for original in lines:
        text = original
        if shell_style:
            stripped = text.strip()
            flags.append(bool(stripped and not stripped.startswith("#")))
            continue
        out = ""
        i = 0
        while i < len(text):
            if in_block:
                end = text.find("*/", i)
                if end < 0:
                    i = len(text)
                    continue
                in_block = False
                i = end + 2
                continue
            block = text.find("/*", i)
            slash = text.find("//", i)
            candidates = [p for p in (block, slash) if p >= 0]
            if not candidates:
                out += text[i:]
                break
            first = min(candidates)
            out += text[i:first]
            if first == slash:
                break
            in_block = True
            i = first + 2
        flags.append(bool(out.strip()))
    return flags


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("source-manifest.tsv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("source-counts.csv"),
    )
    args = parser.parse_args()

    roots = dict(DEFAULT_ROOTS)
    rows: list[dict[str, str | int]] = []
    with args.manifest.open(encoding="utf-8", newline="") as source:
        records = csv.reader(
            (line for line in source if line.strip() and not line.startswith("#")),
            delimiter="\t",
        )
        for fields in records:
            if len(fields) != 8:
                raise ValueError(
                    f"manifest record has {len(fields)} fields, expected 8: {fields}"
                )
            view, system, layer, status, root_name, relpath, ranges, reason = fields
            if root_name == "VKSO_GIT43":
                roots[root_name] = git43_tree()
            if root_name not in roots:
                raise ValueError(f"unknown root {root_name}")
            path = roots[root_name] / relpath
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            selected = parse_ranges(ranges, len(lines))
            code_flags = lexical_code_flags(path, lines)
            physical = len(selected)
            nonblank = sum(bool(lines[n - 1].strip()) for n in selected)
            lexical = sum(code_flags[n - 1] for n in selected)
            rows.append({
                "view": view,
                "system": system,
                "layer": layer,
                "status": status,
                "root": root_name,
                "path": relpath,
                "ranges": ranges,
                "physical_lines": physical,
                "nonblank_lines": nonblank,
                "lexical_sloc": lexical,
                "reason": reason,
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    totals: dict[tuple[str, str, str], list[int]] = defaultdict(
        lambda: [0, 0, 0]
    )
    for row in rows:
        key = (str(row["view"]), str(row["system"]), str(row["status"]))
        totals[key][0] += int(row["physical_lines"])
        totals[key][1] += int(row["nonblank_lines"])
        totals[key][2] += int(row["lexical_sloc"])
    print("view,system,status,physical_lines,nonblank_lines,lexical_sloc")
    for key in sorted(totals):
        values = totals[key]
        print(",".join((*key, *(str(value) for value in values))))


if __name__ == "__main__":
    main()
