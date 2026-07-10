#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


SOURCES = [
    "huf_decompress.c",
    "decompress.c",
    "entropy_common.c",
    "fse_decompress.c",
    "zstd_common.c",
]

SYMBOLS = [
    "FSE_versionNumber",
    "FSE_isError",
    "HUF_isError",
    "FSE_readNCount",
    "HUF_readStats_wksp",
    "FSE_buildDTable_wksp",
    "FSE_buildDTable_rle",
    "FSE_buildDTable_raw",
    "FSE_decompress_usingDTable",
    "FSE_decompress_wksp",
    "HUF_readDTableX2_wksp",
    "HUF_decompress1X2_usingDTable",
    "HUF_decompress1X2_DCtx_wksp",
    "HUF_decompress4X2_usingDTable",
    "HUF_decompress4X2_DCtx_wksp",
    "HUF_readDTableX4_wksp",
    "HUF_decompress1X4_usingDTable",
    "HUF_decompress1X4_DCtx_wksp",
    "HUF_decompress4X4_usingDTable",
    "HUF_decompress4X4_DCtx_wksp",
    "HUF_decompress1X_usingDTable",
    "HUF_decompress4X_usingDTable",
    "HUF_selectDecoder",
    "HUF_decompress4X_DCtx_wksp",
    "HUF_decompress4X_hufOnly_wksp",
    "HUF_decompress1X_DCtx_wksp",
    "ZSTD_DCtxWorkspaceBound",
    "ZSTD_decompressBegin",
    "ZSTD_createDCtx_advanced",
    "ZSTD_initDCtx",
    "ZSTD_freeDCtx",
    "ZSTD_copyDCtx",
    "ZSTD_isFrame",
    "ZSTD_getFrameParams",
    "ZSTD_getFrameContentSize",
    "ZSTD_findDecompressedSize",
    "ZSTD_getcBlockSize",
    "ZSTD_decodeLiteralsBlock",
    "ZSTD_decodeSeqHeaders",
    "ZSTD_execSequenceLast7",
    "ZSTD_execSequence",
    "ZSTD_execSequenceLong",
    "ZSTD_decompressBlock",
    "ZSTD_insertBlock",
    "ZSTD_generateNxBytes",
    "ZSTD_findFrameCompressedSize",
    "ZSTD_decompress_usingDict",
    "ZSTD_decompressDCtx",
    "ZSTD_nextSrcSizeToDecompress",
    "ZSTD_nextInputType",
    "ZSTD_isSkipFrame",
    "ZSTD_decompressContinue",
    "ZSTD_decompressBegin_usingDict",
    "ZSTD_DDictWorkspaceBound",
    "ZSTD_initDDict",
    "ZSTD_freeDDict",
    "ZSTD_getDictID_fromDict",
    "ZSTD_getDictID_fromDDict",
    "ZSTD_getDictID_fromFrame",
    "ZSTD_decompress_usingDDict",
    "ZSTD_DStreamWorkspaceBound",
    "ZSTD_initDStream",
    "ZSTD_initDStream_usingDDict",
    "ZSTD_freeDStream",
    "ZSTD_DStreamInSize",
    "ZSTD_DStreamOutSize",
    "ZSTD_resetDStream",
    "ZSTD_decompressStream",
    "ZSTD_malloc",
    "ZSTD_free",
    "ZSTD_initStack",
    "ZSTD_stackAllocAll",
    "ZSTD_stackAlloc",
    "ZSTD_stackFree",
]


def strip_exports(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("EXPORT_SYMBOL("):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def rename_prelude(suffix: str) -> str:
    lines = [
        "#include <linux/kernel.h>",
        "#include <linux/module.h>",
        "#include <linux/string.h>",
        "",
        "#ifndef __aligned",
        "#define __aligned(x) __attribute__((aligned(x)))",
        "#endif",
        "#ifndef MAX",
        "#define MAX(a, b) ((a) > (b) ? (a) : (b))",
        "#endif",
        "#ifndef MIN",
        "#define MIN(a, b) ((a) < (b) ? (a) : (b))",
        "#endif",
    ]
    for sym in SYMBOLS:
        lines.append(f"#undef {sym}")
    for sym in SYMBOLS:
        lines.append(f"#define {sym} pgot_{sym}_{suffix}")
    return "\n".join(lines) + "\n\n"


def func_pgot_prelude(suffix: str, enabled: bool, define_tables: bool) -> str:
    if not enabled:
        return "#define PGOT_MEMCPY memcpy\n#define PGOT_MEMSET memset\n#define PGOT_MEMMOVE memmove\n\n"
    storage = "" if not define_tables else f"""
pgot_memcpy_fn_{suffix} pgot_memcpy_table_{suffix}[1] __aligned(64) = {{ memcpy }};
pgot_memset_fn_{suffix} pgot_memset_table_{suffix}[1] __aligned(64) = {{ memset }};
pgot_memmove_fn_{suffix} pgot_memmove_table_{suffix}[1] __aligned(64) = {{ memmove }};
"""
    externs = "" if define_tables else f"""
extern pgot_memcpy_fn_{suffix} pgot_memcpy_table_{suffix}[1];
extern pgot_memset_fn_{suffix} pgot_memset_table_{suffix}[1];
extern pgot_memmove_fn_{suffix} pgot_memmove_table_{suffix}[1];
"""
    return f"""
typedef void *(*pgot_memcpy_fn_{suffix})(void *, const void *, size_t);
typedef void *(*pgot_memset_fn_{suffix})(void *, int, size_t);
typedef void *(*pgot_memmove_fn_{suffix})(void *, const void *, size_t);
{storage}{externs}
#define PGOT_MEMCPY(...) (pgot_memcpy_table_{suffix}[0](__VA_ARGS__))
#define PGOT_MEMSET(...) (pgot_memset_table_{suffix}[0](__VA_ARGS__))
#define PGOT_MEMMOVE(...) (pgot_memmove_table_{suffix}[0](__VA_ARGS__))

"""


def replace_mem_calls(text: str, enabled: bool) -> str:
    if not enabled:
        return text
    text = re.sub(r"\bmemcpy\s*\(", "PGOT_MEMCPY(", text)
    text = re.sub(r"\bmemset\s*\(", "PGOT_MEMSET(", text)
    text = re.sub(r"\bmemmove\s*\(", "PGOT_MEMMOVE(", text)
    return text


def normalize_local_error_macros(text: str) -> str:
    text = text.replace("#define FSE_isError ERR_isError",
                        "#undef FSE_isError\n#define FSE_isError ERR_isError")
    text = text.replace("#define HUF_isError ERR_isError",
                        "#undef HUF_isError\n#define HUF_isError ERR_isError")
    return text


def transform_named_static_array(text: str, name: str, suffix: str) -> str:
    pattern = rf"static const ([^;\n=]+?)\s+{name}(\[[^;=]+?\])\s*=\s*(\{{.*?\n\}});"
    match = re.search(pattern, text, flags=re.S)
    if not match:
        return text
    ctype = match.group(1).strip()
    dims = match.group(2)
    body = match.group(3)
    dim_parts = re.findall(r"\[[^\]]+\]", dims)
    if len(dim_parts) <= 1:
        slot_decl = f"const {ctype} *pgot_{name}_{suffix}[1]"
    else:
        tail_dims = "".join(dim_parts[1:])
        slot_decl = f"const {ctype} (*pgot_{name}_{suffix}[1]){tail_dims}"
    replacement = (
        f"static const {ctype} {name}_storage{dims} = {body};\n"
        f"{slot_decl} __aligned(64) = {{ {name}_storage }};\n"
        f"#define {name} (pgot_{name}_{suffix}[0])"
    )
    return text[:match.start()] + replacement + text[match.end():]


def transform_data_tables(text: str, source_name: str, suffix: str) -> str:
    if source_name == "decompress.c":
        for name in ["LL_defaultDTable", "ML_defaultDTable", "OF_defaultDTable"]:
            text = transform_named_static_array(text, name, suffix)
    if source_name == "huf_decompress.c":
        text = transform_named_static_array(text, "algoTime", suffix)
    return text


def add_noinline_to_key_exports(text: str) -> str:
    names = [
        "ZSTD_DCtxWorkspaceBound",
        "ZSTD_initDCtx",
        "ZSTD_decompressBegin",
        "ZSTD_decompressDCtx",
    ]
    for name in names:
        text = re.sub(rf"\b(size_t|ZSTD_DCtx \*) {name}\(",
                      rf"noinline \1 {name}(", text)
    return text


def make_variant_file(src_dir: Path, out_dir: Path, suffix: str, source_name: str,
                      data_pgot: bool, func_pgot: bool, index: int) -> None:
    text = strip_exports((src_dir / source_name).read_text())
    if data_pgot:
        text = transform_data_tables(text, source_name, suffix)
    text = replace_mem_calls(text, func_pgot)
    text = normalize_local_error_macros(text)
    text = add_noinline_to_key_exports(text)

    output = rename_prelude(suffix)
    output += func_pgot_prelude(suffix, func_pgot, define_tables=index == 0)
    output += f"/* copied from lib/zstd/{source_name} */\n"
    output += text
    stem = source_name.replace(".c", "")
    (out_dir / f"closure_{suffix}_{stem}.c").write_text(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-zstd-dir", type=Path,
                        default=Path("/usr/src/linux-source-5.15.0/linux-source-5.15.0/lib/zstd"))
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
        for index, source_name in enumerate(SOURCES):
            make_variant_file(args.kernel_zstd_dir, args.out_dir, suffix,
                              source_name, data_pgot, func_pgot, index)


if __name__ == "__main__":
    main()
