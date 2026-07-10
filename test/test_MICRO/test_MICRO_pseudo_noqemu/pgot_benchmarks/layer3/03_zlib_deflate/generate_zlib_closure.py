#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


SYMBOLS = [
    "zlib_deflateInit2",
    "zlib_deflateInit",
    "zlib_deflateReset",
    "zlib_deflate",
    "zlib_deflateEnd",
    "zlib_deflate_workspacesize",
    "zlib_deflate_dfltcc_enabled",
    "zlib_tr_init",
    "zlib_tr_tally",
    "zlib_tr_flush_block",
    "zlib_tr_align",
    "zlib_tr_stored_block",
    "zlib_tr_stored_type_only",
]

DATA_NAMES = [
    "configuration_table",
    "extra_lbits",
    "extra_dbits",
    "extra_blbits",
    "bl_order",
    "static_ltree",
    "static_dtree",
    "dist_code",
    "length_code",
    "base_length",
    "base_dist",
]


def strip_includes(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("#include "):
            continue
        if line.startswith("#  include "):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def rename_api_prelude(suffix: str) -> str:
    lines = [
        "#include <linux/module.h>",
        "#include <linux/kernel.h>",
        "#include <linux/string.h>",
        "#include <linux/zutil.h>",
        "#include <linux/bitrev.h>",
        "",
        "#ifndef __aligned",
        "#define __aligned(x) __attribute__((aligned(x)))",
        "#endif",
    ]
    for sym in SYMBOLS:
        lines.append(f"#undef {sym}")
    for sym in SYMBOLS:
        lines.append(f"#define {sym} pgot_{sym}_{suffix}")
    lines.append('#include "/usr/src/linux-source-5.15.0/linux-source-5.15.0/lib/zlib_deflate/defutil.h"')
    lines.extend([
        f"int pgot_zlib_deflateInit2_{suffix}(z_streamp strm, int level, int method, int windowBits, int memLevel, int strategy);",
        f"int pgot_zlib_deflateInit_{suffix}(z_streamp strm, int level);",
        f"int pgot_zlib_deflateReset_{suffix}(z_streamp strm);",
        f"int pgot_zlib_deflate_{suffix}(z_streamp strm, int flush);",
        f"int pgot_zlib_deflateEnd_{suffix}(z_streamp strm);",
        f"int pgot_zlib_deflate_workspacesize_{suffix}(int windowBits, int memLevel);",
    ])
    return "\n".join(lines) + "\n\n"


def func_pgot_prelude(suffix: str, enabled: bool) -> str:
    if not enabled:
        return "#define PGOT_MEMCPY memcpy\n#define PGOT_MEMSET memset\n\n"
    return f"""
typedef void *(*pgot_memcpy_fn_{suffix})(void *, const void *, size_t);
typedef void *(*pgot_memset_fn_{suffix})(void *, int, size_t);
pgot_memcpy_fn_{suffix} pgot_memcpy_table_{suffix}[1] __aligned(64) = {{ memcpy }};
pgot_memset_fn_{suffix} pgot_memset_table_{suffix}[1] __aligned(64) = {{ memset }};
#define PGOT_MEMCPY(...) (pgot_memcpy_table_{suffix}[0](__VA_ARGS__))
#define PGOT_MEMSET(...) (pgot_memset_table_{suffix}[0](__VA_ARGS__))

"""


def replace_calls(text: str, func_pgot: bool) -> str:
    text = re.sub(r"\bmemcpy\s*\(", "PGOT_MEMCPY(", text)
    text = re.sub(r"\bmemset\s*\(", "PGOT_MEMSET(", text)
    if not func_pgot:
        text = text.replace("PGOT_MEMCPY", "memcpy")
        text = text.replace("PGOT_MEMSET", "memset")
    return text


def transform_configuration_table(text: str, suffix: str) -> str:
    marker = "static const config configuration_table[10] = {"
    replacement = "static const config configuration_table_storage[10] = {"
    text = text.replace(marker, replacement, 1)
    end = "/* 9 */ {32, 258, 258, 4096, deflate_slow}}; /* maximum compression */\n"
    insert = (
        "/* 9 */ {32, 258, 258, 4096, deflate_slow}}; /* maximum compression */\n"
        f"const config *pgot_configuration_table_{suffix}[1] __aligned(64) = {{ configuration_table_storage }};\n"
        f"#define configuration_table (pgot_configuration_table_{suffix}[0])\n"
    )
    if end not in text:
        raise RuntimeError("configuration_table terminator not found")
    return text.replace(end, insert, 1)


def transform_tree_data(text: str, suffix: str) -> str:
    declarations = [
        (
            r"static const int extra_lbits\[LENGTH_CODES\] /\* extra bits for each length code \*/\n\s*= \{([^;]+?)\};",
            "static const int extra_lbits_storage[LENGTH_CODES] /* extra bits for each length code */\n   = {@@BODY@@};\n"
            f"const int *pgot_extra_lbits_{suffix}[1] __aligned(64) = {{ extra_lbits_storage }};",
        ),
        (
            r"static const int extra_dbits\[D_CODES\] /\* extra bits for each distance code \*/\n\s*= \{([^;]+?)\};",
            "static const int extra_dbits_storage[D_CODES] /* extra bits for each distance code */\n   = {@@BODY@@};\n"
            f"const int *pgot_extra_dbits_{suffix}[1] __aligned(64) = {{ extra_dbits_storage }};",
        ),
        (
            r"static const int extra_blbits\[BL_CODES\]/\* extra bits for each bit length code \*/\n\s*= \{([^;]+?)\};",
            "static const int extra_blbits_storage[BL_CODES]/* extra bits for each bit length code */\n   = {@@BODY@@};\n"
            f"const int *pgot_extra_blbits_{suffix}[1] __aligned(64) = {{ extra_blbits_storage }};",
        ),
        (
            r"static const uch bl_order\[BL_CODES\]\n\s*= \{([^;]+?)\};",
            "static const uch bl_order_storage[BL_CODES]\n   = {@@BODY@@};\n"
            f"const uch *pgot_bl_order_{suffix}[1] __aligned(64) = {{ bl_order_storage }};",
        ),
    ]
    for pattern, repl in declarations:
        def sub(match):
            body = match.group(1).strip()
            if body.startswith("{") and body.endswith("}"):
                body = body[1:-1].strip()
            return repl.replace("@@BODY@@", body)
        text, count = re.subn(pattern, sub, text, count=1, flags=re.S)
        if count != 1:
            raise RuntimeError(f"tree const data pattern not found: {pattern}")

    simple_repls = {
        "static ct_data static_ltree[L_CODES+2];":
            f"static ct_data static_ltree_storage[L_CODES+2];\nct_data *pgot_static_ltree_{suffix}[1] __aligned(64) = {{ static_ltree_storage }};",
        "static ct_data static_dtree[D_CODES];":
            f"static ct_data static_dtree_storage[D_CODES];\nct_data *pgot_static_dtree_{suffix}[1] __aligned(64) = {{ static_dtree_storage }};",
        "static uch dist_code[512];":
            f"static uch dist_code_storage[512];\nuch *pgot_dist_code_{suffix}[1] __aligned(64) = {{ dist_code_storage }};",
        "static uch length_code[MAX_MATCH-MIN_MATCH+1];":
            f"static uch length_code_storage[MAX_MATCH-MIN_MATCH+1];\nuch *pgot_length_code_{suffix}[1] __aligned(64) = {{ length_code_storage }};",
        "static int base_length[LENGTH_CODES];":
            f"static int base_length_storage[LENGTH_CODES];\nint *pgot_base_length_{suffix}[1] __aligned(64) = {{ base_length_storage }};",
        "static int base_dist[D_CODES];":
            f"static int base_dist_storage[D_CODES];\nint *pgot_base_dist_{suffix}[1] __aligned(64) = {{ base_dist_storage }};",
    }
    for old, new in simple_repls.items():
        if old not in text:
            raise RuntimeError(f"tree data declaration not found: {old}")
        text = text.replace(old, new, 1)

    descriptor_repls = {
        "{static_ltree, extra_lbits, LITERALS+1, L_CODES, MAX_BITS}":
            "{static_ltree_storage, extra_lbits_storage, LITERALS+1, L_CODES, MAX_BITS}",
        "{static_dtree, extra_dbits, 0,          D_CODES, MAX_BITS}":
            "{static_dtree_storage, extra_dbits_storage, 0,          D_CODES, MAX_BITS}",
        "{(const ct_data *)0, extra_blbits, 0,   BL_CODES, MAX_BL_BITS}":
            "{(const ct_data *)0, extra_blbits_storage, 0,   BL_CODES, MAX_BL_BITS}",
    }
    for old, new in descriptor_repls.items():
        if old not in text:
            raise RuntimeError(f"descriptor initializer not found: {old}")
        text = text.replace(old, new, 1)

    marker = (
        "static static_tree_desc  static_bl_desc =\n"
        "{(const ct_data *)0, extra_blbits_storage, 0,   BL_CODES, MAX_BL_BITS};"
    )
    macros = "\n".join(
        [
            f"#define extra_lbits (pgot_extra_lbits_{suffix}[0])",
            f"#define extra_dbits (pgot_extra_dbits_{suffix}[0])",
            f"#define extra_blbits (pgot_extra_blbits_{suffix}[0])",
            f"#define bl_order (pgot_bl_order_{suffix}[0])",
            f"#define static_ltree (pgot_static_ltree_{suffix}[0])",
            f"#define static_dtree (pgot_static_dtree_{suffix}[0])",
            f"#define dist_code (pgot_dist_code_{suffix}[0])",
            f"#define length_code (pgot_length_code_{suffix}[0])",
            f"#define base_length (pgot_base_length_{suffix}[0])",
            f"#define base_dist (pgot_base_dist_{suffix}[0])",
        ]
    )
    if marker not in text:
        raise RuntimeError("static_bl_desc marker not found")
    return text.replace(marker, marker + "\n" + macros, 1)


def add_noinline_to_exports(text: str) -> str:
    for name in [
        "zlib_deflateInit2",
        "zlib_deflateInit",
        "zlib_deflateReset",
        "zlib_deflate",
        "zlib_deflateEnd",
        "zlib_deflate_workspacesize",
    ]:
        text = re.sub(rf"\bint {name}\(", f"noinline int {name}(", text)
    return text


def make_variant(src_dir: Path, out_dir: Path, suffix: str, data_pgot: bool, func_pgot: bool) -> None:
    deflate = strip_includes((src_dir / "deflate.c").read_text())
    tree = strip_includes((src_dir / "deftree.c").read_text())

    if data_pgot:
        deflate = transform_configuration_table(deflate, suffix)
        tree = transform_tree_data(tree, suffix)
    deflate = replace_calls(deflate, func_pgot)
    tree = replace_calls(tree, func_pgot)
    deflate = add_noinline_to_exports(deflate)

    text = rename_api_prelude(suffix)
    text += func_pgot_prelude(suffix, func_pgot)
    text += "/* copied from lib/zlib_deflate/deflate.c */\n"
    text += deflate
    text += "\n/* copied from lib/zlib_deflate/deftree.c */\n"
    text += tree
    text += f"""

int pgot_zlib_deflateInit_{suffix}(z_streamp strm, int level)
{{
    return pgot_zlib_deflateInit2_{suffix}(strm, level, Z_DEFLATED,
                                          MAX_WBITS, DEF_MEM_LEVEL,
                                          Z_DEFAULT_STRATEGY);
}}
"""

    (out_dir / f"closure_{suffix}.c").write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-zlib-dir", type=Path,
                        default=Path("/usr/src/linux-source-5.15.0/linux-source-5.15.0/lib/zlib_deflate"))
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    variants = [
        ("origin", False, False),
        ("data_pgot", True, False),
        ("func_pgot", False, True),
        ("all_pgot", True, True),
    ]
    for suffix, data_pgot, func_pgot in variants:
        make_variant(args.kernel_zlib_dir, args.out_dir, suffix, data_pgot, func_pgot)


if __name__ == "__main__":
    main()
