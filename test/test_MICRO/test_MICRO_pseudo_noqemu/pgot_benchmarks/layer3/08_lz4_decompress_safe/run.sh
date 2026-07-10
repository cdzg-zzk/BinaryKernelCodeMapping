#!/usr/bin/env bash
set -euo pipefail

CALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT_ID="08_lz4_decompress_safe"
TARGET_LABEL="lz4_decompress_safe"
GENERATOR="generate_lz4_decompress_closure.py"
INPUT_LEN="${INPUT_LEN:-1024}"
SOURCE_SEMANTICS="copied LZ4_decompress_safe closure: data-pgot rewrites inc32table/dec64table; func-pgot routes closure-internal LZ4_memcpy/LZ4_memmove/memmove through function slots"
SUMMARY_GOAL="This benchmark copies the kernel LZ4_decompress_safe implementation closure into the LKM. The compressed input is generated during module initialization and the timed region calls only the copied decompressor closure."
SUMMARY_TRANSFORMS="| variant | transformation |
|---|---|
| origin | copied LZ4_decompress_safe closure, direct local static decode tables and direct/inlined mem helpers |
| data_pgot | inc32table and dec64table are reached through data slots inside LZ4_decompress_generic |
| func_pgot | LZ4_memcpy/LZ4_memmove/raw memmove callsites in the copied closure are routed through function slots |
| all_pgot | data_pgot + func_pgot |"
SUMMARY_STATIC="Expected evidence: data/all variants reference pgot_lz4_inc32table_* and pgot_lz4_dec64table_*; func/all variants reference pgot_memcpy_table_* or pgot_memmove_table_*; retpoline objdump should show thunk code around indirect mem-helper calls when they remain calls."
NM_GREP=" (body_|pgot_|LZ4_|memcpy_table|memmove_table|memset_table|inc32|dec64)"

source "${CALLER_DIR}/../common_copied_closure_run.sh"
