#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PGOT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MAIN_OUT_DIR="${OUT_DIR:-${PGOT_ROOT}/results/layer2/01_func_placement}"
DIAG_DIR="${DIAG_DIR:-${MAIN_OUT_DIR}/diagnostics/fence_modes}"
ITERATIONS="${ITERATIONS:-100000}"
REPEATS="${REPEATS:-15}"
OUTER_RUNS="${OUTER_RUNS:-3}"
CPU="${CPU:-2}"
MODULE="bench_kmod"
BUILD_DIR="${DIAG_DIR}/.build"
KEEP_BUILD="${KEEP_BUILD:-0}"

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
  local fence_name="$1"
  local ko="$2"

  for ((run_id = 0; run_id < OUTER_RUNS; run_id++)); do
    echo "==> kmod layer2 func placement retpoline/${fence_name} diagnostic run ${run_id}" >&2
    sudo_cmd dmesg -C

    args=("build=retpoline" "fence_mode=${fence_name}" "iterations=${ITERATIONS}" "repeats=${REPEATS}" "run_id=${run_id}")
    if [[ "${CPU}" != "" ]]; then
      args+=("cpu=${CPU}")
    else
      args+=("cpu=-1")
    fi

    sudo_cmd insmod "${ko}" "${args[@]}"
    sudo_cmd rmmod "${MODULE}"

    run_log="${DIAG_DIR}/.run_retpoline_${fence_name}_${run_id}.log"
    sudo_cmd dmesg > "${run_log}"
    awk -F'PGOT_L2FP_RAW,' '/PGOT_L2FP_RAW,/ {print $2}' "${run_log}" >> "${RAW}"
    rm -f "${run_log}"
  done
}

mkdir -p "${DIAG_DIR}"
rm -rf "${BUILD_DIR}"
rm -f \
  "${DIAG_DIR}/metadata.txt" \
  "${DIAG_DIR}/raw.csv" \
  "${DIAG_DIR}/processed.csv" \
  "${DIAG_DIR}/paper_table.csv" \
  "${DIAG_DIR}/summary.md" \
  "${DIAG_DIR}/summary_append.md"
rm -rf "${DIAG_DIR}/static"
rm -f "${DIAG_DIR}"/.run_*.log
mkdir -p "${BUILD_DIR}"

{
  echo "experiment=layer2_func_placement_fence_diagnostics"
  echo "source_semantics=Retpoline fence diagnostics for workload visible-overhead collapse"
  echo "iterations=${ITERATIONS}"
  echo "repeats=${REPEATS}"
  echo "outer_runs=${OUTER_RUNS}"
  echo "event=1"
  echo "placements=none,work_only,before,inside,after"
  echo "workloads=0,1,2,3,4,5,6,8,16,32,64"
  echo "builds=retpoline"
  echo "fence_modes=unfenced,post_fenced,iter_fenced,pre_post_iter_fenced"
  echo "sample_order=interleave"
  echo "raw_delta=pgot_cycles-direct_cycles"
  echo "ret_base_flags=${RET_BASE_FLAGS}"
  echo
  bash "${PGOT_ROOT}/collect_env.sh"
} > "${DIAG_DIR}/metadata.txt"

RAW="${DIAG_DIR}/raw.csv"
{
  echo "experiment,build,fence,run_id,placement,workload,repeat,iterations,direct_cycles,pgot_cycles,delta_pgot_direct"
} > "${RAW}"

declare -A MODE_FLAGS=(
  [unfenced]=""
  [post_fenced]="-DBENCH_FENCE_AFTER_CALL=1"
  [iter_fenced]="-DBENCH_FENCE_ITERATION=1"
  [pre_post_iter_fenced]="-DBENCH_FENCE_BEFORE_CALL=1 -DBENCH_FENCE_AFTER_CALL=1 -DBENCH_FENCE_ITERATION=1"
)

STATIC_DIR="${DIAG_DIR}/static"
mkdir -p "${STATIC_DIR}"

for mode in unfenced post_fenced iter_fenced pre_post_iter_fenced; do
  ko="${BUILD_DIR}/bench_kmod_retpoline_${mode}.ko"
  build_module "${RET_BASE_FLAGS} ${MODE_FLAGS[$mode]}" "${ko}"
  cp "${ko}" "${STATIC_DIR}/bench_kmod_retpoline_${mode}.ko"
  nm -S --size-sort "${ko}" \
    | grep -E ' (target_work_|body_WORK_only_|body_(DIRECT|PGOT)_(none|before|inside|after)_)' \
    > "${STATIC_DIR}/nm_retpoline_${mode}.txt"
  objdump -d --no-show-raw-insn "${ko}" \
    > "${STATIC_DIR}/objdump_retpoline_${mode}.txt"
  run_one_variant "${mode}" "${ko}"
done

python3 "${PGOT_ROOT}/scripts/process_layer2_func_placement.py" \
  --raw "${RAW}" \
  --processed "${DIAG_DIR}/processed.csv" \
  --paper-table "${DIAG_DIR}/paper_table.csv"

python3 "${PGOT_ROOT}/scripts/summarize_layer2_fence_diagnostics.py" \
  --metadata "${DIAG_DIR}/metadata.txt" \
  --paper-table "${DIAG_DIR}/paper_table.csv" \
  --static-dir "${STATIC_DIR}" \
  --summary "${DIAG_DIR}/summary.md" \
  --append "${DIAG_DIR}/summary_append.md"

if [[ -f "${MAIN_OUT_DIR}/summary.md" ]]; then
  python3 "${PGOT_ROOT}/scripts/replace_markdown_section.py" \
    --file "${MAIN_OUT_DIR}/summary.md" \
    --start "<!-- fence-diagnostics:start -->" \
    --end "<!-- fence-diagnostics:end -->" \
    --replacement "${DIAG_DIR}/summary_append.md"
fi

make -C "${SCRIPT_DIR}" clean
if [[ "${KEEP_BUILD}" != "1" ]]; then
  rm -rf "${BUILD_DIR}"
fi

echo "wrote ${DIAG_DIR}" >&2
