#!/usr/bin/env bash
set -euo pipefail

CALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT_ID="09_hex_dump_to_buffer"
TARGET_LABEL="hex_dump_to_buffer"
GENERATOR="generate_hex_closure.py"
SOURCE_SEMANTICS="copied hex_dump_to_buffer closure: data-pgot rewrites the closure-local hex_asc table; no mem* callsite exists in this target path"
SUMMARY_GOAL="This benchmark copies the kernel hex_dump_to_buffer implementation into the LKM and times direct calls to the copied closure. The benchmark uses groupsize=1/ascii=true so the normal hex_asc table path is exercised without snprintf callsites."
SUMMARY_TRANSFORMS="| variant | transformation |
|---|---|
| origin | copied hex_dump_to_buffer closure with direct hex_asc table references |
| data_pgot | hex_asc is reached through a data slot before hex_asc_hi/lo indexing |
| func_pgot | no mem* callsite exists here, so this is intentionally identical to origin |
| all_pgot | same data-slot rewrite as data_pgot |"
SUMMARY_STATIC="Expected evidence: data/all variants reference pgot_hex_asc_table_* in objdump/nm; func_pgot has no mem* table because hex_dump_to_buffer has no memcpy/memset/memmove callsite in this measured path."
NM_GREP=" (body_|pgot_|hex_asc|memcpy_table|memmove_table|memset_table)"

source "${CALLER_DIR}/../common_copied_closure_run.sh"
