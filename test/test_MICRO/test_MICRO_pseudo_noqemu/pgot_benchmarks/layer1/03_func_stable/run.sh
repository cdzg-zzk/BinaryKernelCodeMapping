#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PGOT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${OUT_DIR:-${PGOT_ROOT}/results/layer1/03_func_stable}"
ITERATIONS="${ITERATIONS:-1000000}"
REPEATS="${REPEATS:-31}"
OUTER_RUNS="${OUTER_RUNS:-10}"
CPU="${CPU:-2}"
MODULE="bench_kmod"
BUILD_DIR="${OUT_DIR}/.build"
KEEP_BUILD="${KEEP_BUILD:-0}"
BUILDS="${BUILDS:-both}"

NORET_KCFLAGS="${NORET_KCFLAGS:--mindirect-branch=keep -mfunction-return=keep -DBENCH_NOTRACE=1 -DBENCH_ALIGN64=1}"
RET_KCFLAGS="${RET_KCFLAGS:--mindirect-branch=thunk-inline -mindirect-branch-register -mfunction-return=keep -fcf-protection=none -DBENCH_NOTRACE=1 -DBENCH_ALIGN64=1}"

sudo_cmd() {
  if [[ "${SUDO_PASSWORD:-}" != "" ]]; then
    printf '%s\n' "${SUDO_PASSWORD}" | sudo -S "$@"
  else
    sudo "$@"
  fi
}

build_module() {
  local build_name="$1"
  local flags="$2"
  local output="$3"

  make -C "${SCRIPT_DIR}" clean
  make -C "${SCRIPT_DIR}" all KCFLAGS="${flags}"
  cp "${SCRIPT_DIR}/${MODULE}.ko" "${output}"
}

run_one_build() {
  local build_name="$1"
  local ko="$2"

  for ((run_id = 0; run_id < OUTER_RUNS; run_id++)); do
    echo "==> kmod layer1 func stable ${build_name} run ${run_id}" >&2
    sudo_cmd dmesg -C

    args=("build=${build_name}" "iterations=${ITERATIONS}" "repeats=${REPEATS}" "run_id=${run_id}")
    if [[ "${CPU}" != "" ]]; then
      args+=("cpu=${CPU}")
    else
      args+=("cpu=-1")
    fi

    sudo_cmd insmod "${ko}" "${args[@]}"
    sudo_cmd rmmod "${MODULE}"

    run_log="${OUT_DIR}/.run_${build_name}_${run_id}.log"
    sudo_cmd dmesg > "${run_log}"

    awk -F'PGOT_L1FS_RAW,' '/PGOT_L1FS_RAW,/ {print $2}' \
      "${run_log}" >> "${RAW}"
    rm -f "${run_log}"
  done
}

mkdir -p "${OUT_DIR}"
rm -rf "${BUILD_DIR}" "${OUT_DIR}/raw" "${OUT_DIR}/processed" "${OUT_DIR}/kmsg" "${OUT_DIR}/main"
rm -f \
  "${OUT_DIR}/metadata.txt" \
  "${OUT_DIR}/raw.csv" \
  "${OUT_DIR}/processed.csv" \
  "${OUT_DIR}/paper_table.csv" \
  "${OUT_DIR}/paper_main.csv" \
  "${OUT_DIR}/paper_diagnostics.csv" \
  "${OUT_DIR}/.samples_with_outliers.csv" \
  "${OUT_DIR}/config.txt" \
  "${OUT_DIR}/environment.txt"
rm -f "${OUT_DIR}"/.run_*.log
mkdir -p "${BUILD_DIR}"

{
  echo "experiment=layer1_func_stable_kmod"
  echo "source_semantics=layer1/03_func_stable kernel-module benchmark"
  echo "iterations=${ITERATIONS}"
  echo "repeats=${REPEATS}"
  echo "outer_runs=${OUTER_RUNS}"
  echo "events=1,2,4,8,16"
  echo "builds=${BUILDS}"
  echo "target_pattern=stable"
  echo "benchmark_controls=notrace,align64"
  if [[ "${CPU}" != "" ]]; then
    echo "cpu=${CPU}"
  else
    echo "cpu=unpinned"
  fi
  echo "sample_order=interleave"
  echo "raw_fields=empty_cycles,direct_cycles,cached_indirect_cycles,slot_direct_cycles,pgot_cycles,delta_cached_direct,delta_slot_direct,delta_pgot_cached,delta_pgot_direct"
  echo "raw_delta_cached_direct=cached_indirect_cycles-direct_cycles"
  echo "raw_delta_slot_direct=slot_direct_cycles-direct_cycles"
  echo "raw_delta_pgot_cached=pgot_cycles-cached_indirect_cycles"
  echo "raw_delta_pgot_direct=pgot_cycles-direct_cycles"
  echo "paper_main=primary direct-vs-pgot results, raw and empty-adjusted"
  echo "paper_diagnostics=mechanism-split support data"
  echo "empty_adjusted_direct=direct_cycles-empty_cycles"
  echo "empty_adjusted_pgot=pgot_cycles-empty_cycles"
  echo "noret_kcflags=${NORET_KCFLAGS}"
  echo "ret_kcflags=${RET_KCFLAGS}"
  echo "outlier_filter=per-build,event IQR rule: [Q1-1.5*IQR, Q3+1.5*IQR]"
  echo
  bash "${PGOT_ROOT}/collect_env.sh"
} > "${OUT_DIR}/metadata.txt"

NORET_KO="${BUILD_DIR}/bench_kmod_noret.ko"
RET_KO="${BUILD_DIR}/bench_kmod_retpoline.ko"

RAW="${OUT_DIR}/raw.csv"
{
  echo "experiment,build,run_id,event,repeat,iterations,empty_cycles,direct_cycles,cached_indirect_cycles,slot_direct_cycles,pgot_cycles,delta_cached_direct,delta_slot_direct,delta_pgot_cached,delta_pgot_direct"
} > "${RAW}"

case "${BUILDS}" in
  both)
    build_module "no_retpoline" "${NORET_KCFLAGS}" "${NORET_KO}"
    build_module "retpoline" "${RET_KCFLAGS}" "${RET_KO}"
    run_one_build "no_retpoline" "${NORET_KO}"
    run_one_build "retpoline" "${RET_KO}"
    ;;
  no_retpoline)
    build_module "no_retpoline" "${NORET_KCFLAGS}" "${NORET_KO}"
    run_one_build "no_retpoline" "${NORET_KO}"
    ;;
  retpoline)
    build_module "retpoline" "${RET_KCFLAGS}" "${RET_KO}"
    run_one_build "retpoline" "${RET_KO}"
    ;;
  *)
    echo "invalid BUILDS=${BUILDS}; expected both, no_retpoline, or retpoline" >&2
    exit 2
    ;;
esac

python3 "${PGOT_ROOT}/scripts/process_layer1_func_stable.py" \
  --raw "${RAW}" \
  --processed "${OUT_DIR}/.samples_with_outliers.csv" \
  --summary "${OUT_DIR}/processed.csv" \
  --paper-table "${OUT_DIR}/paper_table.csv" \
  --paper-main "${OUT_DIR}/paper_main.csv" \
  --paper-diagnostics "${OUT_DIR}/paper_diagnostics.csv"

rm -f "${OUT_DIR}/.samples_with_outliers.csv"
make -C "${SCRIPT_DIR}" clean
if [[ "${KEEP_BUILD}" != "1" ]]; then
  rm -rf "${BUILD_DIR}"
fi

echo "wrote ${OUT_DIR}" >&2
