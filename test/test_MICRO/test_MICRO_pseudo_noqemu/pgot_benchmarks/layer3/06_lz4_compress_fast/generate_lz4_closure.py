#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


LZ4_SRC = Path("/usr/src/linux-source-5.15.0/linux-source-5.15.0/lib/lz4")

SYMBOLS = [
    "LZ4_compress_fast",
    "LZ4_compress_default",
    "LZ4_compress_destSize",
    "LZ4_resetStream",
    "LZ4_loadDict",
    "LZ4_saveDict",
    "LZ4_compress_fast_continue",
]


def strip_includes_and_exports(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("#include "):
            continue
        if line.startswith("EXPORT_SYMBOL("):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def rename_prelude(suffix: str) -> str:
    lines = [
        "#include <linux/module.h>",
        "#include <linux/kernel.h>",
        "#include <linux/lz4.h>",
        "#include <linux/string.h>",
        "#include <asm/unaligned.h>",
        "",
        "#ifndef __aligned",
        "#define __aligned(x) __attribute__((aligned(x)))",
        "#endif",
        "",
    ]
    for sym in SYMBOLS:
        lines.append(f"#undef {sym}")
    for sym in SYMBOLS:
        lines.append(f"#define {sym} pgot_{sym}_{suffix}")
    lines.extend([
        "",
        f"int pgot_LZ4_compress_fast_{suffix}(const char *source, char *dest, int inputSize, int maxOutputSize, int acceleration, void *wrkmem);",
        f"int pgot_LZ4_compress_default_{suffix}(const char *source, char *dest, int inputSize, int maxOutputSize, void *wrkmem);",
        f"int pgot_LZ4_compress_destSize_{suffix}(const char *source, char *dest, int *sourceSizePtr, int targetDestSize, void *wrkmem);",
        f"void pgot_LZ4_resetStream_{suffix}(LZ4_stream_t *LZ4_stream);",
        f"int pgot_LZ4_loadDict_{suffix}(LZ4_stream_t *LZ4_dict, const char *dictionary, int dictSize);",
        f"int pgot_LZ4_saveDict_{suffix}(LZ4_stream_t *LZ4_dict, char *safeBuffer, int dictSize);",
        f"int pgot_LZ4_compress_fast_continue_{suffix}(LZ4_stream_t *LZ4_stream, const char *source, char *dest, int inputSize, int maxOutputSize, int acceleration);",
    ])
    lines.append(f'#include "{LZ4_SRC / "lz4defs.h"}"')
    lines.append("")
    return "\n".join(lines) + "\n"


def transform_data_pgot(text: str, suffix: str, enabled: bool) -> str:
    if not enabled:
        return text

    replacements = [
        (
            "static const int LZ4_minLength = (MFLIMIT + 1);",
            "static const int LZ4_minLength_storage = (MFLIMIT + 1);\n"
            f"const int *pgot_LZ4_minLength_{suffix}[1] __aligned(64) = {{ &LZ4_minLength_storage }};\n"
            f"#define LZ4_minLength (*pgot_LZ4_minLength_{suffix}[0])",
        ),
        (
            "static const int LZ4_64Klimit = ((64 * KB) + (MFLIMIT - 1));",
            "static const int LZ4_64Klimit_storage = ((64 * KB) + (MFLIMIT - 1));\n"
            f"const int *pgot_LZ4_64Klimit_{suffix}[1] __aligned(64) = {{ &LZ4_64Klimit_storage }};\n"
            f"#define LZ4_64Klimit (*pgot_LZ4_64Klimit_{suffix}[0])",
        ),
    ]
    for old, new in replacements:
        if old not in text:
            raise RuntimeError(f"LZ4 data declaration not found: {old}")
        text = text.replace(old, new, 1)
    return text


def func_pgot_prelude(suffix: str, enabled: bool) -> str:
    if not enabled:
        return ""
    return f"""
typedef void *(*pgot_memcpy_fn_{suffix})(void *, const void *, size_t);
typedef void *(*pgot_memmove_fn_{suffix})(void *, const void *, size_t);
typedef void *(*pgot_memset_fn_{suffix})(void *, int, size_t);
pgot_memcpy_fn_{suffix} pgot_memcpy_table_{suffix}[1] __aligned(64) = {{ memcpy }};
pgot_memmove_fn_{suffix} pgot_memmove_table_{suffix}[1] __aligned(64) = {{ memmove }};
pgot_memset_fn_{suffix} pgot_memset_table_{suffix}[1] __aligned(64) = {{ memset }};
#undef LZ4_memcpy
#undef LZ4_memmove
#define PGOT_MEMCPY_{suffix}(...) (pgot_memcpy_table_{suffix}[0](__VA_ARGS__))
#define PGOT_MEMMOVE_{suffix}(...) (pgot_memmove_table_{suffix}[0](__VA_ARGS__))
#define PGOT_MEMSET_{suffix}(...) (pgot_memset_table_{suffix}[0](__VA_ARGS__))
#define LZ4_memcpy(...) PGOT_MEMCPY_{suffix}(__VA_ARGS__)
#define LZ4_memmove(...) PGOT_MEMMOVE_{suffix}(__VA_ARGS__)

"""


def transform_func_pgot_calls(text: str, suffix: str, enabled: bool) -> str:
    if not enabled:
        return text
    text = re.sub(r"\bmemcpy\s*\(", f"PGOT_MEMCPY_{suffix}(", text)
    text = re.sub(r"\bmemmove\s*\(", f"PGOT_MEMMOVE_{suffix}(", text)
    text = re.sub(r"\bmemset\s*\(", f"PGOT_MEMSET_{suffix}(", text)
    return text


def make_variant(source: str, out_dir: Path, suffix: str, data_pgot: bool, func_pgot: bool) -> None:
    text = strip_includes_and_exports(source)
    text = transform_data_pgot(text, suffix, data_pgot)
    text = transform_func_pgot_calls(text, suffix, func_pgot)
    out = rename_prelude(suffix)
    out += func_pgot_prelude(suffix, func_pgot)
    out += text
    (out_dir / f"closure_{suffix}.c").write_text(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--src-dir", type=Path, default=LZ4_SRC)
    args = parser.parse_args()

    source = (args.src_dir / "lz4_compress.c").read_text()
    variants = [
        ("origin", False, False),
        ("data_pgot", True, False),
        ("func_pgot", False, True),
        ("all_pgot", True, True),
    ]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for suffix, data_pgot, func_pgot in variants:
        make_variant(source, args.out_dir, suffix, data_pgot, func_pgot)


if __name__ == "__main__":
    main()
