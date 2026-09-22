#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path


def output(*args: str) -> str:
    return subprocess.run(args, check=True, text=True,
                          stdout=subprocess.PIPE).stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--page-map", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    dynamic = output("readelf", "-dW", str(args.library))
    relocations = output("readelf", "-rW", str(args.library))
    symbols = output("nm", "-D", str(args.library))
    expected_relocations = ("__kmalloc", "kfree", "vkso_abi_memcpy", "memmove")
    expected_exports = (
        "vkso_xz_crc32_init",
        "vkso_xz_dec_init",
        "vkso_xz_dec_run",
        "vkso_xz_dec_reset",
        "vkso_xz_dec_end",
    )

    failures: list[str] = []
    if "Shared library: [libshim.so]" not in dynamic:
        failures.append("DT_NEEDED does not contain libshim.so")
    for name in expected_relocations:
        if not re.search(rf"\b{re.escape(name)}\b", relocations):
            failures.append(f"missing DSO relocation for {name}")
    for name in expected_exports:
        if not re.search(rf"\b{re.escape(name)}$", symbols, re.MULTILINE):
            failures.append(f"missing dynamic export {name}")

    mappings = [
        line for line in args.page_map.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not mappings:
        failures.append("page map is empty")
    if len(mappings) > 16:
        failures.append(
            f"unexpectedly large reusable-page closure: {len(mappings)} pages"
        )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    status = "PASS" if not failures else "FAIL"
    lines = [
        "# Generated kernel DSO audit",
        "",
        f"- Status: **{status}**",
        f"- Reusable pages: {len(mappings)}",
        "- Required helper relocations: "
        + ", ".join(expected_relocations),
        "- Required exports: " + ", ".join(expected_exports),
    ]
    if failures:
        lines += ["", "Failures:"] + [f"- {item}" for item in failures]
    args.report.write_text("\n".join(lines) + "\n")
    if failures:
        raise SystemExit("; ".join(failures))


if __name__ == "__main__":
    main()
