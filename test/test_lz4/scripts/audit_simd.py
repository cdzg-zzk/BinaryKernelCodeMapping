#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path


REGISTER = re.compile(r"\b(?:(?:xmm|ymm|zmm)[0-9]+|mm[0-7])\b", re.IGNORECASE)
REGISTER_FREE_SIMD = re.compile(r"\b(?:vzeroupper|vzeroall|emms)\b", re.IGNORECASE)
MEMORY_HELPER = re.compile(r"\b(?:memcpy|memmove|memset)(?:@|$)")


def count_simd(path: Path) -> tuple[int, list[str]]:
    output = subprocess.check_output(
        ["objdump", "-d", "-M", "intel", str(path)], text=True
    )
    hits = [
        line.strip()
        for line in output.splitlines()
        if REGISTER.search(line) or REGISTER_FREE_SIMD.search(line)
    ]
    return len(hits), hits[:10]


def undefined_memory_helpers(path: Path) -> list[str]:
    output = subprocess.check_output(
        ["nm", "-D", "--undefined-only", str(path)], text=True
    )
    return [line.strip() for line in output.splitlines() if MEMORY_HELPER.search(line)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--default", type=Path, required=True)
    parser.add_argument("--nosimd", type=Path, required=True)
    parser.add_argument("--kernel-native", type=Path, required=True)
    parser.add_argument("--kernel-nosimd", type=Path, required=True)
    parser.add_argument("--kernel-libc", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    lines = ["# SIMD instruction audit", ""]
    failed = False
    variants = (
        ("user-default", args.default, False),
        ("user-nosimd", args.nosimd, True),
        ("kernel-userspace-native", args.kernel_native, False),
        ("kernel-userspace-nosimd", args.kernel_nosimd, True),
    )
    if args.kernel_libc:
        variants += (("kernel-userspace-libc", args.kernel_libc, False),)
    for label, path, must_be_scalar in variants:
        count, examples = count_simd(path)
        helpers = undefined_memory_helpers(path)
        lines.append(
            f"- `{label}`: {count} disassembly lines contain SIMD/MMX "
            "registers or register-free SIMD state instructions"
        )
        lines.append(
            f"  - unresolved libc memory helpers: "
            f"{', '.join(helpers) if helpers else 'none'}"
        )
        if examples:
            lines += ["", "```asm", *examples, "```", ""]
        if label == "kernel-userspace-libc":
            lines.append("  - scalar algorithm body; external libc helpers may execute SIMD")
            if count or len(helpers) != 3:
                failed = True
        if must_be_scalar and (count or helpers):
            failed = True

    report = "\n".join(lines) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    print(report, end="")
    if failed:
        raise SystemExit(
            "a no-SIMD backend still contains SIMD instructions or external "
            "memory helpers"
        )


if __name__ == "__main__":
    main()
