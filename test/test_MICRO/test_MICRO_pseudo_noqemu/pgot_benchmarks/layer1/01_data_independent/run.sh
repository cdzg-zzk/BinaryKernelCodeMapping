#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PGOT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${OUT_DIR:-${PGOT_ROOT}/results/layer1/01_data_independent}"
ITERATIONS="${ITERATIONS:-1000000}"
REPEATS="${REPEATS:-31}"
OUTER_RUNS="${OUTER_RUNS:-100}"
CPU="${CPU:-2}"
MODULE="bench_kmod"
KO="${SCRIPT_DIR}/${MODULE}.ko"

sudo_cmd() {
  if [[ "${SUDO_PASSWORD:-}" != "" ]]; then
    printf '%s\n' "${SUDO_PASSWORD}" | sudo -S "$@"
  else
    sudo "$@"
  fi
}

mkdir -p "${OUT_DIR}"
rm -rf "${OUT_DIR}/raw" "${OUT_DIR}/processed" "${OUT_DIR}/kmsg" "${OUT_DIR}/main"
rm -f \
  "${OUT_DIR}/metadata.txt" \
  "${OUT_DIR}/raw.csv" \
  "${OUT_DIR}/processed.csv" \
  "${OUT_DIR}/paper_table.csv" \
  "${OUT_DIR}/.samples_with_outliers.csv" \
  "${OUT_DIR}/config.txt" \
  "${OUT_DIR}/environment.txt"
rm -f "${OUT_DIR}"/.run_*.log

{
  echo "experiment=layer1_data_independent_kmod"
  echo "source_semantics=layer1/01_data_independent kernel-module benchmark"
  echo "iterations=${ITERATIONS}"
  echo "repeats=${REPEATS}"
  echo "outer_runs=${OUTER_RUNS}"
  echo "events=1,2,4,6,8,10,12,14,16,18"
  echo "measured_variants=scheduled,barriered"
  echo "derived_variants=scheduled_empty_adjusted"
  if [[ "${CPU}" != "" ]]; then
    echo "cpu=${CPU}"
  else
    echo "cpu=unpinned"
  fi
  echo "sample_order=interleave"
  echo "raw_fields=empty_cycles,direct_cycles,pgot_cycles,delta_cycles,delta_cycles_per_event"
  echo "raw_delta=pgot_cycles-direct_cycles"
  echo "empty_adjusted_direct=direct_cycles-empty_cycles"
  echo "empty_adjusted_pgot=pgot_cycles-empty_cycles"
  echo "outlier_filter=per-event IQR rule: [Q1-1.5*IQR, Q3+1.5*IQR]"
  echo
  bash "${PGOT_ROOT}/collect_env.sh"
} > "${OUT_DIR}/metadata.txt"

make -C "${SCRIPT_DIR}" all

RAW="${OUT_DIR}/raw.csv"
{
  echo "experiment,variant,run_id,event,repeat,iterations,empty_cycles,direct_cycles,pgot_cycles,delta_cycles,delta_cycles_per_event"
} > "${RAW}"

for ((run_id = 0; run_id < OUTER_RUNS; run_id++)); do
  echo "==> kmod layer1 data independent run ${run_id}" >&2
  sudo_cmd dmesg -C

  args=("iterations=${ITERATIONS}" "repeats=${REPEATS}" "run_id=${run_id}")
  if [[ "${CPU}" != "" ]]; then
    args+=("cpu=${CPU}")
  else
    args+=("cpu=-1")
  fi

  sudo_cmd insmod "${KO}" "${args[@]}"
  sudo_cmd rmmod "${MODULE}"

  run_log="${OUT_DIR}/.run_${run_id}.log"
  sudo_cmd dmesg > "${run_log}"

  awk -F'PGOT_L1DI_RAW,' '/PGOT_L1DI_RAW,/ {print $2}' \
    "${run_log}" >> "${RAW}"
  rm -f "${run_log}"
done

python3 "${PGOT_ROOT}/scripts/process_layer1_data_independent.py" \
  --raw "${RAW}" \
  --processed "${OUT_DIR}/.samples_with_outliers.csv" \
  --summary "${OUT_DIR}/processed.csv" \
  --paper-table "${OUT_DIR}/paper_table.csv"

rm -f "${OUT_DIR}/.samples_with_outliers.csv"

echo "wrote ${OUT_DIR}" >&2
