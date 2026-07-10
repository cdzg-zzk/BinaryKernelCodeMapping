#!/usr/bin/env bash
set -euo pipefail

CALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT_ID="10_string_escape_mem"
TARGET_LABEL="string_escape_mem"
GENERATOR="generate_string_escape_closure.py"
SOURCE_SEMANTICS="copied string_escape_mem closure: data-pgot rewrites the hex_asc table used by escape_hex; no mem* callsite exists in this closure path"
SUMMARY_GOAL="This benchmark copies the kernel string_escape_mem closure into the LKM and exercises the ESCAPE_HEX path, which uses hex_asc through escape_hex. The outer benchmark call remains a direct call to the copied closure."
SUMMARY_TRANSFORMS="| variant | transformation |
|---|---|
| origin | copied string_escape_mem closure with direct hex_asc table references |
| data_pgot | escape_hex reaches hex_asc through a data slot |
| func_pgot | no memcpy/memset/memmove callsite exists in this closure, so this is intentionally identical to origin |
| all_pgot | same data-slot rewrite as data_pgot |"
SUMMARY_STATIC="Expected evidence: data/all variants reference pgot_hex_asc_table_* in objdump/nm; func_pgot has no mem* table because this closure has no memcpy/memset/memmove callsite."
NM_GREP=" (body_|pgot_|hex_asc|memcpy_table|memmove_table|memset_table)"

source "${CALLER_DIR}/../common_copied_closure_run.sh"
