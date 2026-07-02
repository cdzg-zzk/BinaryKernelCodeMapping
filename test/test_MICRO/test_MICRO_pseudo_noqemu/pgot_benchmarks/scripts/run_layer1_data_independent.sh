#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH_DIR="${ROOT_DIR}/layer1/01_data_independent"
OUT_DIR="${ROOT_DIR}/results/validation/layer1-data-independent"
ITERATIONS="${ITERATIONS:-1000000}"
REPEATS="${REPEATS:-31}"
OUTER_RUNS="${OUTER_RUNS:-100}"
CPU="${CPU:-2}"

CPU_ARG=()
if [[ "${CPU}" != "" ]]; then
  CPU_ARG=(-c "${CPU}")
fi

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

{
  echo "experiment=layer1_data_independent"
  echo "generated_by=scripts/run_layer1_data_independent.sh"
  echo "iterations=${ITERATIONS}"
  echo "repeats=${REPEATS}"
  echo "outer_runs=${OUTER_RUNS}"
  if [[ "${CPU}" != "" ]]; then
    echo "cpu=${CPU}"
  else
    echo "cpu=unpinned"
  fi
  echo "sample_order=interleave"
  echo "raw_delta=pgot_cycles-direct_cycles"
  echo "outlier_filter=per-event IQR rule: [Q1-1.5*IQR, Q3+1.5*IQR]"
} > "${OUT_DIR}/config.txt"

make -C "${BENCH_DIR}" all

RAW="${OUT_DIR}/raw.csv"
RUN_SUMMARIES="${OUT_DIR}/run_summaries.csv"

for ((run_id = 0; run_id < OUTER_RUNS; run_id++)); do
  echo "==> layer1 data independent run ${run_id}" >&2
  PGOT_RUN_ID="${run_id}" PGOT_RAW_FILE="${RAW}" \
    "${BENCH_DIR}/bench" -n "${ITERATIONS}" -r "${REPEATS}" "${CPU_ARG[@]}" \
    >> "${RUN_SUMMARIES}"
done

python3 "${ROOT_DIR}/scripts/process_layer1_data_independent.py" \
  --raw "${RAW}" \
  --processed "${OUT_DIR}/processed.csv" \
  --summary "${OUT_DIR}/summary.csv" \
  --paper-table "${OUT_DIR}/paper_table.csv"

echo "wrote ${OUT_DIR}" >&2
