#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path


EXPORTS = {
    "vkso_bch_init",
    "vkso_bch_free",
    "vkso_bch_encode",
    "vkso_bch_decode",
}
HELPERS = {"__kmalloc", "kfree", "memcpy", "memset"}
FORBIDDEN = {
    "__fentry__",
    "__stack_chk_fail",
    "__ubsan_handle",
    "__asan_",
    "kmalloc_caches",
    "kmem_cache_alloc_trace",
    "fortify_panic",
}


def output(*command: str) -> str:
    return subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE).stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--module", type=Path, required=True)
    parser.add_argument("--page-map", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dynamic = output("readelf", "-dW", str(args.library))
    symbols = output("nm", "-D", "--defined-only", str(args.library))
    relocations = output("readelf", "-rW", str(args.library))
    module_undefined = output("nm", "-u", str(args.module))
    module_relocations = output("readelf", "-rW", str(args.module))

    exported = {line.split()[-1] for line in symbols.splitlines() if line.split()}
    needed = set(re.findall(r"Shared library: \[([^]]+)\]", dynamic))
    relocation_helpers = {
        helper for helper in HELPERS if re.search(rf"\b{re.escape(helper)}\b", relocations)
    }
    forbidden_hits = {
        marker
        for marker in FORBIDDEN
        if marker in module_undefined or marker in relocations
    }

    in_text = False
    absolute_text = []
    for line in module_relocations.splitlines():
        if line.startswith("Relocation section"):
            in_text = "'.rela.text'" in line or "'.rela.text." in line
            continue
        if in_text and "R_X86_64_32S" in line:
            absolute_text.append(line.strip())

    page_lines = [
        line
        for line in args.page_map.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    checks = [
        ("four requested API exports", EXPORTS <= exported,
         ", ".join(sorted(EXPORTS & exported))),
        ("libshim dependency", "libshim.so" in needed, ", ".join(sorted(needed))),
        ("four helper relocations", relocation_helpers == HELPERS,
         ", ".join(sorted(relocation_helpers))),
        ("no compiler/kernel-only helper dependency", not forbidden_hits,
         ", ".join(sorted(forbidden_hits)) or "none"),
        ("no absolute .text address relocation", not absolute_text,
         "; ".join(absolute_text) or "none"),
        ("non-empty reusable page map", bool(page_lines), f"{len(page_lines)} entries"),
    ]

    lines = [
        "# Exported BCH DSO audit",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for name, passed, evidence in checks:
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {evidence} |")
    lines += [
        "",
        "The owner module's only permitted external algorithm dependencies are "
        "`__kmalloc`, `kfree`, `memcpy`, and `memset`; the generated DSO binds "
        "them through `libshim.so`. The absolute-relocation check is limited to "
        "loadable text relocation sections and intentionally excludes debug data.",
        "",
    ]
    args.output.write_text("\n".join(lines), encoding="utf-8")
    if not all(passed for _, passed, _ in checks):
        raise SystemExit("kernel DSO audit failed")


if __name__ == "__main__":
    main()
