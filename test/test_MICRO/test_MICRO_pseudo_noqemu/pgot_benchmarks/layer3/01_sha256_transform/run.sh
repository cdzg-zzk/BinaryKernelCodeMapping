#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PGOT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${OUT_DIR:-${PGOT_ROOT}/results/layer3/01_sha256_transform}"

# For SHA-256, very large iteration windows can increase external disturbance.
# Keep the default grid moderate; override from environment if needed.
ITERATIONS_LIST="${ITERATIONS_LIST:-4096 8192 16384}"
REPEATS="${REPEATS:-31}"
WARMUPS="${WARMUPS:-5}"
OUTER_RUNS="${OUTER_RUNS:-3}"
CPU="${CPU:-2}"
IRQ_OFF="${IRQ_OFF:-0}"

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

run_one_build() {
  local build_name="$1"
  local ko="$2"
  local iter
  local run_log
  local -a args

  for ((run_id = 0; run_id < OUTER_RUNS; run_id++)); do
    for iter in ${ITERATIONS_LIST}; do
      echo "==> kmod layer3 sha256 ${build_name} run ${run_id} iterations ${iter}" >&2
      sudo_cmd dmesg -C

      args=(
        "build=${build_name}"
        "iterations=${iter}"
        "repeats=${REPEATS}"
        "warmups=${WARMUPS}"
        "run_id=${run_id}"
        "irq_off=${IRQ_OFF}"
      )

      if [[ "${CPU}" != "" ]]; then
        args+=("cpu=${CPU}")
      else
        args+=("cpu=-1")
      fi

      sudo_cmd insmod "${ko}" "${args[@]}"
      sudo_cmd rmmod "${MODULE}"

      run_log="${DMESG_DIR}/${build_name}_${run_id}_${iter}.log"
      sudo_cmd dmesg > "${run_log}"
      awk -F'PGOT_L3SHA_RAW,' '/PGOT_L3SHA_RAW,/ {print $2}' "${run_log}" >> "${RAW}"
      grep -EHi 'warning|error|fail|BUG|Oops|Call Trace' "${run_log}" \
        >> "${OUT_DIR}/dmesg_warnings.txt" || true
    done
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
rm -rf "${OUT_DIR}/dmesg"
rm -f "${OUT_DIR}/dmesg_warnings.txt"
mkdir -p "${BUILD_DIR}"
DMESG_DIR="${OUT_DIR}/dmesg"
mkdir -p "${DMESG_DIR}"

{
  echo "experiment=layer3_sha256_transform_kmod"
  echo "source_semantics=SHA-256 transform copied closure: origin vs all PGOT"
  echo "iterations_list=${ITERATIONS_LIST}"
  echo "repeats=${REPEATS}"
  echo "warmups=${WARMUPS}"
  echo "outer_runs=${OUTER_RUNS}"
  echo "cpu=${CPU}"
  echo "irq_off=${IRQ_OFF}"
  echo "variants=all_pgot"
  echo "builds=no_retpoline,retpoline"
  echo "sample_order=ABBA/BAAB paired interleave"
  echo "raw_delta=variant_cycles-origin_cycles"
  echo "noret_base_flags=${NORET_BASE_FLAGS}"
  echo "ret_base_flags=${RET_BASE_FLAGS}"
  echo
  bash "${PGOT_ROOT}/collect_env.sh"
} > "${OUT_DIR}/metadata.txt"

RAW="${OUT_DIR}/raw.csv"
{
  echo "experiment,build,run_id,variant,repeat,iterations,origin_cycles,variant_cycles,delta_variant_origin"
} > "${RAW}"

NORET_KO="${BUILD_DIR}/bench_kmod_no_retpoline.ko"
RET_KO="${BUILD_DIR}/bench_kmod_retpoline.ko"

build_module "${NORET_BASE_FLAGS}" "${NORET_KO}"
build_module "${RET_BASE_FLAGS}" "${RET_KO}"

run_one_build "no_retpoline" "${NORET_KO}"
run_one_build "retpoline" "${RET_KO}"

STATIC_DIR="${OUT_DIR}/static"
mkdir -p "${STATIC_DIR}"
cp "${NORET_KO}" "${STATIC_DIR}/bench_kmod_no_retpoline.ko"
cp "${RET_KO}" "${STATIC_DIR}/bench_kmod_retpoline.ko"

nm -S --size-sort "${STATIC_DIR}/bench_kmod_no_retpoline.ko" \
  | grep -E ' (sha256_transform_|body_|pgot_|sha256_k_origin)' \
  > "${STATIC_DIR}/nm_no_retpoline.txt" || true
nm -S --size-sort "${STATIC_DIR}/bench_kmod_retpoline.ko" \
  | grep -E ' (sha256_transform_|body_|pgot_|sha256_k_origin)' \
  > "${STATIC_DIR}/nm_retpoline.txt" || true

objdump -dr --no-show-raw-insn "${STATIC_DIR}/bench_kmod_no_retpoline.ko" \
  > "${STATIC_DIR}/objdump_no_retpoline.txt"
objdump -dr --no-show-raw-insn "${STATIC_DIR}/bench_kmod_retpoline.ko" \
  > "${STATIC_DIR}/objdump_retpoline.txt"

python3 "${PGOT_ROOT}/scripts/process_layer3_sha256.py" \
  --raw "${RAW}" \
  --processed "${OUT_DIR}/processed.csv" \
  --paper-table "${OUT_DIR}/paper_table.csv"

python3 "${PGOT_ROOT}/scripts/generate_layer3_sha256_summary.py" \
  --metadata "${OUT_DIR}/metadata.txt" \
  --paper-table "${OUT_DIR}/paper_table.csv" \
  --nm-no-retpoline "${STATIC_DIR}/nm_no_retpoline.txt" \
  --nm-retpoline "${STATIC_DIR}/nm_retpoline.txt" \
  --objdump-no-retpoline "${STATIC_DIR}/objdump_no_retpoline.txt" \
  --objdump-retpoline "${STATIC_DIR}/objdump_retpoline.txt" \
  --summary "${OUT_DIR}/summary.md"

make -C "${SCRIPT_DIR}" clean
if [[ "${KEEP_BUILD}" != "1" ]]; then
  rm -rf "${BUILD_DIR}"
fi

echo "wrote ${OUT_DIR}" >&2
