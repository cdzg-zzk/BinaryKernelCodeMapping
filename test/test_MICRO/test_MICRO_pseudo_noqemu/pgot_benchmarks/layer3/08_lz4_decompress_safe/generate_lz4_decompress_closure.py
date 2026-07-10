#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


LZ4_SRC = Path("/usr/src/linux-source-5.15.0/linux-source-5.15.0/lib/lz4")

SYMBOLS = [
    "LZ4_decompress_safe",
    "LZ4_decompress_safe_partial",
    "LZ4_decompress_fast",
    "LZ4_setStreamDecode",
    "LZ4_decompress_safe_continue",
    "LZ4_decompress_fast_continue",
    "LZ4_decompress_safe_usingDict",
    "LZ4_decompress_fast_usingDict",
    "LZ4_decompress_safe_forceExtDict",
]


def strip_includes_and_exports(text: str) -> str:
    lines = []
    skip_ifndef_static = False
    for line in text.splitlines():
        if line.startswith("#include "):
            continue
        if line.startswith("#ifndef STATIC"):
            skip_ifndef_static = True
            continue
        if skip_ifndef_static:
            if line.startswith("#endif"):
                skip_ifndef_static = False
            continue
        if line.startswith("EXPORT_SYMBOL(") or line.startswith("MODULE_"):
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
        f"int pgot_LZ4_decompress_safe_{suffix}(const char *source, char *dest, int compressedSize, int maxDecompressedSize);",
        f"int pgot_LZ4_decompress_safe_partial_{suffix}(const char *src, char *dst, int compressedSize, int targetOutputSize, int dstCapacity);",
        f"int pgot_LZ4_decompress_fast_{suffix}(const char *source, char *dest, int originalSize);",
        f"int pgot_LZ4_setStreamDecode_{suffix}(LZ4_streamDecode_t *LZ4_streamDecode, const char *dictionary, int dictSize);",
        f"int pgot_LZ4_decompress_safe_continue_{suffix}(LZ4_streamDecode_t *LZ4_streamDecode, const char *source, char *dest, int compressedSize, int maxOutputSize);",
        f"int pgot_LZ4_decompress_fast_continue_{suffix}(LZ4_streamDecode_t *LZ4_streamDecode, const char *source, char *dest, int originalSize);",
        f"int pgot_LZ4_decompress_safe_usingDict_{suffix}(const char *source, char *dest, int compressedSize, int maxOutputSize, const char *dictStart, int dictSize);",
        f"int pgot_LZ4_decompress_fast_usingDict_{suffix}(const char *source, char *dest, int originalSize, const char *dictStart, int dictSize);",
    ])
    lines.append(f'#include "{LZ4_SRC / "lz4defs.h"}"')
    lines.append("")
    return "\n".join(lines) + "\n"


def data_pgot_prelude(suffix: str, enabled: bool) -> str:
    if not enabled:
        return ""
    return f"""
static const unsigned int pgot_lz4_inc32table_storage_{suffix}[8] __aligned(64) = {{0, 1, 2, 1, 0, 4, 4, 4}};
static const int pgot_lz4_dec64table_storage_{suffix}[8] __aligned(64) = {{0, 0, 0, -1, -4, 1, 2, 3}};
const unsigned int *pgot_lz4_inc32table_{suffix}[1] __aligned(64) = {{ pgot_lz4_inc32table_storage_{suffix} }};
const int *pgot_lz4_dec64table_{suffix}[1] __aligned(64) = {{ pgot_lz4_dec64table_storage_{suffix} }};

"""


def transform_data_pgot(text: str, suffix: str, enabled: bool) -> str:
    if not enabled:
        return text
    old = (
        "\tstatic const unsigned int inc32table[8] = {0, 1, 2, 1, 0, 4, 4, 4};\n"
        "\tstatic const int dec64table[8] = {0, 0, 0, -1, -4, 1, 2, 3};"
    )
    new = (
        f"\tconst unsigned int *inc32table = pgot_lz4_inc32table_{suffix}[0];\n"
        f"\tconst int *dec64table = pgot_lz4_dec64table_{suffix}[0];"
    )
    if old not in text:
        raise RuntimeError("LZ4 decode tables not found")
    return text.replace(old, new, 1)


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
    out += data_pgot_prelude(suffix, data_pgot)
    out += func_pgot_prelude(suffix, func_pgot)
    out += text
    (out_dir / f"closure_{suffix}.c").write_text(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--src-dir", type=Path, default=LZ4_SRC)
    args = ap.parse_args()
    source = (args.src_dir / "lz4_decompress.c").read_text()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    variants = [
        ("origin", False, False),
        ("data_pgot", True, False),
        ("func_pgot", False, True),
        ("all_pgot", True, True),
    ]
    for suffix, data_pgot, func_pgot in variants:
        make_variant(source, args.out_dir, suffix, data_pgot, func_pgot)


if __name__ == "__main__":
    main()
