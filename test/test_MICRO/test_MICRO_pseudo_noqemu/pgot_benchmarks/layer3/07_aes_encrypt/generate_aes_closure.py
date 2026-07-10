#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


AES_SRC = Path("/usr/src/linux-source-5.15.0/linux-source-5.15.0/lib/crypto/aes.c")

SYMBOLS = [
    "aes_expandkey",
    "aes_encrypt",
    "aes_decrypt",
]


def strip_includes_and_exports(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("#include "):
            continue
        if line.startswith("EXPORT_SYMBOL(") or line.startswith("MODULE_"):
            continue
        if "__alias(" in line:
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def rename_prelude(suffix: str) -> str:
    lines = [
        "#include <crypto/aes.h>",
        "#include <linux/crypto.h>",
        "#include <linux/kernel.h>",
        "#include <linux/module.h>",
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
        f"int pgot_aes_expandkey_{suffix}(struct crypto_aes_ctx *ctx, const u8 *in_key, unsigned int key_len);",
        f"void pgot_aes_encrypt_{suffix}(const struct crypto_aes_ctx *ctx, u8 *out, const u8 *in);",
        f"void pgot_aes_decrypt_{suffix}(const struct crypto_aes_ctx *ctx, u8 *out, const u8 *in);",
        "",
    ])
    return "\n".join(lines)


def replace_array_decl(text: str, name: str, suffix: str) -> str:
    pattern = f"static volatile const u8 ____cacheline_aligned {name}[] = {{"
    replacement = (
        f"static volatile const u8 ____cacheline_aligned pgot_{name}_storage_{suffix}[] = {{"
    )
    if pattern not in text:
        raise RuntimeError(f"{name} declaration not found")
    text = text.replace(pattern, replacement, 1)
    return text


def transform_data_pgot(text: str, suffix: str, enabled: bool) -> str:
    if not enabled:
        return text
    text = replace_array_decl(text, "aes_sbox", suffix)
    text = replace_array_decl(text, "aes_inv_sbox", suffix)
    insert_after_inv = "};\n\n\n\nstatic u32 mul_by_x"
    table_defs = f"""}};

volatile const u8 *pgot_aes_sbox_table_{suffix}[1] __aligned(64) = {{ pgot_aes_sbox_storage_{suffix} }};
volatile const u8 *pgot_aes_inv_sbox_table_{suffix}[1] __aligned(64) = {{ pgot_aes_inv_sbox_storage_{suffix} }};
#define aes_sbox (pgot_aes_sbox_table_{suffix}[0])
#define aes_inv_sbox (pgot_aes_inv_sbox_table_{suffix}[0])

static u32 mul_by_x"""
    if insert_after_inv not in text:
        raise RuntimeError("AES insertion point not found")
    return text.replace(insert_after_inv, table_defs, 1)


def func_pgot_prelude(suffix: str, enabled: bool) -> str:
    del suffix, enabled
    return ""


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--src", type=Path, default=AES_SRC)
    args = ap.parse_args()
    source = args.src.read_text()
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
