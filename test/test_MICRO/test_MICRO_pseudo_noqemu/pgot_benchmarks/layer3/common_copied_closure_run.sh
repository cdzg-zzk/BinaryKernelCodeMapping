#!/usr/bin/env bash
set -euo pipefail

if [[ "${EXPERIMENT_ID:-}" == "" || "${TARGET_LABEL:-}" == "" || "${GENERATOR:-}" == "" ]]; then
  echo "EXPERIMENT_ID, TARGET_LABEL, and GENERATOR must be set by the caller" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(cd "${CALLER_DIR:-.}" && pwd)"
PGOT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${OUT_DIR:-${PGOT_ROOT}/results/layer3/${EXPERIMENT_ID}}"

ITERATIONS_LIST="${ITERATIONS_LIST:-512 1024 2048}"
WARMUP="${WARMUP:-auto}"
REPEATS="${REPEATS:-31}"
OUTER_RUNS="${OUTER_RUNS:-3}"
CPU="${CPU:-2}"
IRQ_OFF="${IRQ_OFF:-1}"
INPUT_LEN="${INPUT_LEN:-1024}"
VARIANTS="${VARIANTS:-all_pgot}"

MODULE="bench_kmod"
BUILD_DIR="${OUT_DIR}/.build"
KEEP_BUILD="${KEEP_BUILD:-0}"

NORET_BASE_FLAGS="${NORET_BASE_FLAGS:--mindirect-branch=keep -mfunction-return=keep -DBENCH_NOTRACE=1 -DBENCH_ALIGN64=1 -fno-builtin-memcpy -fno-builtin-memset -fno-builtin-memmove}"
RET_BASE_FLAGS="${RET_BASE_FLAGS:--mindirect-branch=thunk-inline -mindirect-branch-register -mfunction-return=keep -fcf-protection=none -DBENCH_NOTRACE=1 -DBENCH_ALIGN64=1 -fno-builtin-memcpy -fno-builtin-memset -fno-builtin-memmove}"

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

  make -C "${EXP_DIR}" clean
  python3 "${EXP_DIR}/${GENERATOR}" --out-dir "${EXP_DIR}"
  make -C "${EXP_DIR}" all KCFLAGS="${flags}"
  cp "${EXP_DIR}/${MODULE}.ko" "${output}"
}

run_one_build() {
  local build_name="$1"
  local ko="$2"
  local iter warmup_iter run_log
  local -a args

  for ((run_id = 0; run_id < OUTER_RUNS; run_id++)); do
    for iter in ${ITERATIONS_LIST}; do
      if [[ "${WARMUP}" == "auto" ]]; then
        warmup_iter="${iter}"
      else
        warmup_iter="${WARMUP}"
      fi

      echo "==> kmod layer3 ${TARGET_LABEL} ${build_name} run ${run_id} iterations ${iter} warmup ${warmup_iter}" >&2
      sudo_cmd dmesg -C

      args=(
        "build=${build_name}"
        "iterations=${iter}"
        "warmup=${warmup_iter}"
        "repeats=${REPEATS}"
        "run_id=${run_id}"
        "irq_off=${IRQ_OFF}"
        "input_len=${INPUT_LEN}"
        "variants=${VARIANTS}"
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
      awk -F'PGOT_L3_RAW,' '/PGOT_L3_RAW,/ {print $2}' "${run_log}" >> "${RAW}"
      grep -EHi 'warning|error|fail|BUG|Oops|Call Trace' "${run_log}" \
        | grep -Ev 'module verification failed|signature and/or required key missing' \
        >> "${OUT_DIR}/dmesg_warnings.txt" || true
    done
  done
}

mkdir -p "${OUT_DIR}"
rm -rf "${BUILD_DIR}"
rm -f "${OUT_DIR}/metadata.txt" "${OUT_DIR}/raw.csv" \
  "${OUT_DIR}/processed.csv" "${OUT_DIR}/paper_table.csv" \
  "${OUT_DIR}/summary.md"
rm -rf "${OUT_DIR}/static"
rm -rf "${OUT_DIR}/dmesg"
rm -f "${OUT_DIR}/dmesg_warnings.txt"
mkdir -p "${BUILD_DIR}"
DMESG_DIR="${OUT_DIR}/dmesg"
mkdir -p "${DMESG_DIR}"

{
  echo "experiment=layer3_${TARGET_LABEL}_kmod"
  echo "source_semantics=${SOURCE_SEMANTICS:-copied kernel implementation closure: origin direct internals vs PGOT-rewritten closure internals}"
  echo "iterations_list=${ITERATIONS_LIST}"
  echo "warmup=${WARMUP}"
  echo "repeats=${REPEATS}"
  echo "outer_runs=${OUTER_RUNS}"
  echo "cpu=${CPU}"
  echo "irq_off=${IRQ_OFF}"
  echo "input_len=${INPUT_LEN}"
  echo "variants=${VARIANTS}"
  echo "builds=no_retpoline,retpoline"
  echo "sample_order=ABBA/BAAB paired interleave"
  echo "raw_delta=variant_cycles-origin_cycles"
  echo "noret_base_flags=${NORET_BASE_FLAGS}"
  echo "ret_base_flags=${RET_BASE_FLAGS}"
  echo
  bash "${PGOT_ROOT}/collect_env.sh"
} > "${OUT_DIR}/metadata.txt"

RAW="${OUT_DIR}/raw.csv"
echo "experiment,build,run_id,variant,repeat,iterations,origin_cycles,variant_cycles,delta_variant_origin" > "${RAW}"

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
  | grep -E "${NM_GREP:- (body_|pgot_|memcpy_table|memmove_table|memset_table|hex_asc|sbox|inc32|dec64)}" \
  > "${STATIC_DIR}/nm_no_retpoline.txt" || true
nm -S --size-sort "${STATIC_DIR}/bench_kmod_retpoline.ko" \
  | grep -E "${NM_GREP:- (body_|pgot_|memcpy_table|memmove_table|memset_table|hex_asc|sbox|inc32|dec64)}" \
  > "${STATIC_DIR}/nm_retpoline.txt" || true

objdump -dr --no-show-raw-insn "${STATIC_DIR}/bench_kmod_no_retpoline.ko" \
  > "${STATIC_DIR}/objdump_no_retpoline.txt"
objdump -dr --no-show-raw-insn "${STATIC_DIR}/bench_kmod_retpoline.ko" \
  > "${STATIC_DIR}/objdump_retpoline.txt"

python3 "${PGOT_ROOT}/scripts/process_layer3_generic.py" \
  --raw "${RAW}" \
  --processed "${OUT_DIR}/processed.csv" \
  --paper-table "${OUT_DIR}/paper_table.csv"

{
  echo "# Layer3 ${TARGET_LABEL} Copied-Closure PGOT Experiment"
  echo
  echo "## Goal"
  echo
  echo "${SUMMARY_GOAL:-This benchmark copies the kernel implementation closure into the LKM. The origin version keeps the copied implementation unchanged. The PGOT variants rewrite only closure-internal data references and mem* helper callsites that are visible in the copied closure.}"
  echo
  echo "## Transformations"
  echo
  echo "${SUMMARY_TRANSFORMS:-See the experiment generator and static/objdump_*.txt for exact rewritten symbols.}"
  echo
  echo "## Results"
  echo
  python3 - <<'PY' "${OUT_DIR}/paper_table.csv"
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1])))
print("| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |")
print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for r in rows:
    print(f"| {r['build']} | {r['variant']} | {r['iterations']} | {r['n_raw']} | {float(r['origin_cycles']):.3f} | {float(r['variant_cycles']):.3f} | {float(r['delta_cycles']):.3f} | {float(r['delta_iqr']):.3f} | {float(r['iqr_to_abs_delta']):.2f} | {float(r['overhead_percent']):.2f} |")
PY
  echo
  echo "## Static Validation"
  echo
  echo "${SUMMARY_STATIC:-See static/objdump_*.txt and static/nm_*.txt for data-slot references, mem* function-slot references, and retpoline thunk evidence.}"
} > "${OUT_DIR}/summary.md"

make -C "${EXP_DIR}" clean
if [[ "${KEEP_BUILD}" != "1" ]]; then
  rm -rf "${BUILD_DIR}"
fi

echo "wrote ${OUT_DIR}" >&2
