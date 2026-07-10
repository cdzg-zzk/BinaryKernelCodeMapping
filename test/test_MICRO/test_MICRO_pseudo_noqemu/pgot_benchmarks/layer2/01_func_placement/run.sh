#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PGOT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${OUT_DIR:-${PGOT_ROOT}/results/layer2/01_func_placement}"
ITERATIONS="${ITERATIONS:-1000000}"
REPEATS="${REPEATS:-31}"
OUTER_RUNS="${OUTER_RUNS:-5}"
CPU="${CPU:-2}"
MODULE="bench_kmod"
BUILD_DIR="${OUT_DIR}/.build"
KEEP_BUILD="${KEEP_BUILD:-0}"

NORET_BASE_FLAGS="${NORET_BASE_FLAGS:--mindirect-branch=keep -mfunction-return=keep -DBENCH_NOTRACE=1 -DBENCH_ALIGN64=1}"
RET_BASE_FLAGS="${RET_BASE_FLAGS:--mindirect-branch=thunk-inline -mindirect-branch-register -mfunction-return=keep -fcf-protection=none -DBENCH_NOTRACE=1 -DBENCH_ALIGN64=1}"

sudo_cmd() {
  if [[ "${SUDO_PASSWORD:-}" != "" ]]; then
    printf '%s\n' "${SUDO_PASSWORD}" | sudo -S "$@"
  else
    sudo "$@"
  fi
}

build_module() {
  local flags="$1"
  local output="$2"

  make -C "${SCRIPT_DIR}" clean
  make -C "${SCRIPT_DIR}" all KCFLAGS="${flags}"
  cp "${SCRIPT_DIR}/${MODULE}.ko" "${output}"
}

run_one_variant() {
  local build_name="$1"
  local fence_name="$2"
  local ko="$3"

  for ((run_id = 0; run_id < OUTER_RUNS; run_id++)); do
    echo "==> kmod layer2 func placement ${build_name}/${fence_name} run ${run_id}" >&2
    sudo_cmd dmesg -C

    args=("build=${build_name}" "fence_mode=${fence_name}" "iterations=${ITERATIONS}" "repeats=${REPEATS}" "run_id=${run_id}")
    if [[ "${CPU}" != "" ]]; then
      args+=("cpu=${CPU}")
    else
      args+=("cpu=-1")
    fi

    sudo_cmd insmod "${ko}" "${args[@]}"
    sudo_cmd rmmod "${MODULE}"

    run_log="${OUT_DIR}/.run_${build_name}_${fence_name}_${run_id}.log"
    sudo_cmd dmesg > "${run_log}"
    awk -F'PGOT_L2FP_RAW,' '/PGOT_L2FP_RAW,/ {print $2}' "${run_log}" >> "${RAW}"
    rm -f "${run_log}"
  done
}

mkdir -p "${OUT_DIR}"
rm -rf "${BUILD_DIR}"
rm -f \
  "${OUT_DIR}/metadata.txt" \
  "${OUT_DIR}/raw.csv" \
  "${OUT_DIR}/processed.csv" \
  "${OUT_DIR}/paper_table.csv" \
  "${OUT_DIR}/summary.md"
rm -rf "${OUT_DIR}/static"
rm -rf "${OUT_DIR}/stability"
rm -f "${OUT_DIR}"/.run_*.log
mkdir -p "${BUILD_DIR}"

{
  echo "experiment=layer2_func_placement_kmod"
  echo "source_semantics=Layer2 func-pgot unfenced placement/workload sensitivity"
  echo "iterations=${ITERATIONS}"
  echo "repeats=${REPEATS}"
  echo "outer_runs=${OUTER_RUNS}"
  echo "event=1"
  echo "placements=none,work_only,before,inside,after"
  echo "workloads=0,1,2,3,4,5,6,8,16,32,64"
  echo "builds=no_retpoline,retpoline"
  echo "fence_modes=unfenced"
  echo "sample_order=interleave"
  echo "raw_delta=pgot_cycles-direct_cycles"
  echo "noret_base_flags=${NORET_BASE_FLAGS}"
  echo "ret_base_flags=${RET_BASE_FLAGS}"
  echo
  bash "${PGOT_ROOT}/collect_env.sh"
} > "${OUT_DIR}/metadata.txt"

RAW="${OUT_DIR}/raw.csv"
{
  echo "experiment,build,fence,run_id,placement,workload,repeat,iterations,direct_cycles,pgot_cycles,delta_pgot_direct"
} > "${RAW}"

NORET_UNFENCED_KO="${BUILD_DIR}/bench_kmod_noret_unfenced.ko"
RET_UNFENCED_KO="${BUILD_DIR}/bench_kmod_ret_unfenced.ko"

build_module "${NORET_BASE_FLAGS}" "${NORET_UNFENCED_KO}"
build_module "${RET_BASE_FLAGS}" "${RET_UNFENCED_KO}"

run_one_variant "no_retpoline" "unfenced" "${NORET_UNFENCED_KO}"
run_one_variant "retpoline" "unfenced" "${RET_UNFENCED_KO}"

STATIC_DIR="${OUT_DIR}/static"
mkdir -p "${STATIC_DIR}"
cp "${NORET_UNFENCED_KO}" "${STATIC_DIR}/bench_kmod_no_retpoline.ko"
cp "${RET_UNFENCED_KO}" "${STATIC_DIR}/bench_kmod_retpoline.ko"
nm -S --size-sort "${STATIC_DIR}/bench_kmod_no_retpoline.ko" \
  | grep -E ' (target_work_|body_WORK_only_|body_(DIRECT|PGOT)_(none|before|inside|after)_)' \
  > "${STATIC_DIR}/nm_no_retpoline.txt"
nm -S --size-sort "${STATIC_DIR}/bench_kmod_retpoline.ko" \
  | grep -E ' (target_work_|body_WORK_only_|body_(DIRECT|PGOT)_(none|before|inside|after)_)' \
  > "${STATIC_DIR}/nm_retpoline.txt"
objdump -d --no-show-raw-insn "${STATIC_DIR}/bench_kmod_no_retpoline.ko" \
  > "${STATIC_DIR}/objdump_no_retpoline.txt"
objdump -d --no-show-raw-insn "${STATIC_DIR}/bench_kmod_retpoline.ko" \
  > "${STATIC_DIR}/objdump_retpoline.txt"

python3 "${PGOT_ROOT}/scripts/process_layer2_func_placement.py" \
  --raw "${RAW}" \
  --processed "${OUT_DIR}/processed.csv" \
  --paper-table "${OUT_DIR}/paper_table.csv"

python3 "${PGOT_ROOT}/scripts/generate_layer2_func_placement_summary.py" \
  --metadata "${OUT_DIR}/metadata.txt" \
  --paper-table "${OUT_DIR}/paper_table.csv" \
  --nm-retpoline "${STATIC_DIR}/nm_retpoline.txt" \
  --objdump-retpoline "${STATIC_DIR}/objdump_retpoline.txt" \
  --objdump-no-retpoline "${STATIC_DIR}/objdump_no_retpoline.txt" \
  --summary "${OUT_DIR}/summary.md"

make -C "${SCRIPT_DIR}" clean
if [[ "${KEEP_BUILD}" != "1" ]]; then
  rm -rf "${BUILD_DIR}"
fi

echo "wrote ${OUT_DIR}" >&2
