#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${ROOT_DIR}/results/layer3"

sudo_preflight() {
  if [[ "${SUDO_PASSWORD:-}" != "" ]]; then
    printf '%s\n' "${SUDO_PASSWORD}" | sudo -S -v
  else
    sudo -v
  fi
}

run_one() {
  local name="$1"
  echo "==> layer3 stability ${name}" >&2
  "${ROOT_DIR}/run_experiment.sh" "${name}"
}

sudo_preflight
run_one layer3-sha256-transform
run_one layer3-bch-encode
run_one layer3-zlib-deflate
run_one layer3-zstd-decompress
run_one layer3-crc32-le
run_one layer3-lz4-compress-fast
run_one layer3-aes-encrypt
run_one layer3-lz4-decompress-safe
run_one layer3-hex-dump-to-buffer
run_one layer3-string-escape-mem

python3 "${ROOT_DIR}/scripts/select_layer3_stable_rows.py" \
  --results-dir "${RESULTS_DIR}" \
  --out-csv "${RESULTS_DIR}/paper_table_selected.csv" \
  --out-md "${RESULTS_DIR}/paper_table_selected.md"

python3 "${ROOT_DIR}/scripts/diagnose_layer3_stability.py" \
  --results-dir "${RESULTS_DIR}" \
  --out-md "${RESULTS_DIR}/stability_diagnosis.md"

echo "wrote ${RESULTS_DIR}/paper_table_selected.csv" >&2
echo "wrote ${RESULTS_DIR}/paper_table_selected.md" >&2
echo "wrote ${RESULTS_DIR}/stability_diagnosis.md" >&2
