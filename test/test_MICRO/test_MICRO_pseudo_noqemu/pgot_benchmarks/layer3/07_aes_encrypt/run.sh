#!/usr/bin/env bash
set -euo pipefail

CALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT_ID="07_aes_encrypt"
TARGET_LABEL="aes_encrypt"
GENERATOR="generate_aes_closure.py"
INPUT_LEN="${INPUT_LEN:-16}"
SOURCE_SEMANTICS="copied aes_encrypt closure: data-pgot rewrites AES S-box tables; no memcpy/memset/memmove callsite exists in timed aes_encrypt"
SUMMARY_GOAL="This benchmark copies the generic kernel AES implementation closure into the LKM. Key expansion is performed before timing; the timed body directly calls the copied aes_encrypt closure."
SUMMARY_TRANSFORMS="| variant | transformation |
|---|---|
| origin | copied aes_encrypt/aes_expandkey closure with direct AES S-box references |
| data_pgot | aes_sbox/aes_inv_sbox table references are reached through data slots |
| func_pgot | no memcpy/memset/memmove callsite exists in aes_encrypt, so this is intentionally identical to origin for timed work |
| all_pgot | same data-slot rewrite as data_pgot |"
SUMMARY_STATIC="Expected evidence: data/all variants reference pgot_aes_sbox_table_* and pgot_aes_inv_sbox_table_* in objdump/nm; func_pgot has no mem* table because aes_encrypt has no memcpy/memset/memmove callsite."
NM_GREP=" (body_|pgot_|aes_sbox|aes_inv_sbox|memcpy_table|memmove_table|memset_table)"

source "${CALLER_DIR}/../common_copied_closure_run.sh"
