#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/results"
RAW_DIR="${OUT_DIR}/raw"
VALIDATION_DIR="${OUT_DIR}/validation"
ITERATIONS="${ITERATIONS:-1000000}"
REPEATS="${REPEATS:-31}"
PERF_ITERATIONS="${PERF_ITERATIONS:-5000000}"
PERF_REPEATS="${PERF_REPEATS:-3}"
PERF_EVENTS="${PERF_EVENTS:-cycles,instructions,branches,branch-misses}"
VALIDATION_REPEATS="${VALIDATION_REPEATS:-15}"
CPU_ARG=()

if [[ "${CPU:-}" != "" ]]; then
  CPU_ARG=(-c "${CPU}")
fi

mkdir -p "${OUT_DIR}"
mkdir -p "${RAW_DIR}"
mkdir -p "${VALIDATION_DIR}"
export PGOT_RAW_DIR="${RAW_DIR}"
OUT="${OUT_DIR}/all_results.csv"

{
  echo "# generated_by=scripts/run_all.sh"
  echo "# iterations=${ITERATIONS}"
  echo "# repeats=${REPEATS}"
  if [[ "${CPU:-}" != "" ]]; then
    echo "# cpu=${CPU}"
  fi
  bash "${ROOT_DIR}/scripts/collect_env.sh"
} > "${OUT}"

run_bin() {
  local label="$1"
  local bin="$2"
  echo "==> ${label}" >&2
  "${bin}" -n "${ITERATIONS}" -r "${REPEATS}" "${CPU_ARG[@]}" >> "${OUT}"
}

make -C "${ROOT_DIR}" all

run_bin "layer1 data independent" "${ROOT_DIR}/layer1/01_data_independent/bench"
run_bin "layer1 data dependent" "${ROOT_DIR}/layer1/02_data_dependent/bench"
run_bin "layer1 func stable no-ret" "${ROOT_DIR}/layer1/03_func_stable/bench_noret"
run_bin "layer1 func stable retpoline" "${ROOT_DIR}/layer1/03_func_stable/bench_retpoline"
run_bin "layer1 func entropy no-ret" "${ROOT_DIR}/layer1/04_func_entropy/bench_noret"
run_bin "layer1 func entropy retpoline" "${ROOT_DIR}/layer1/04_func_entropy/bench_retpoline"
run_bin "layer2 density data" "${ROOT_DIR}/layer2/01_density_data/bench"
run_bin "layer2 density func no-ret" "${ROOT_DIR}/layer2/02_density_func/bench_noret"
run_bin "layer2 density func retpoline" "${ROOT_DIR}/layer2/02_density_func/bench_retpoline"

{
  echo "# generated_by=scripts/run_all.sh"
  echo "# perf_iterations=${PERF_ITERATIONS}"
  echo "# perf_repeats=${PERF_REPEATS}"
  echo "# perf_events=${PERF_EVENTS}"
  bash "${ROOT_DIR}/scripts/collect_env.sh"
} > "${VALIDATION_DIR}/environment.txt"

objdump -d "${ROOT_DIR}/layer2/02_density_func/bench_retpoline" \
  > "${VALIDATION_DIR}/objdump_layer2_func_retpoline.txt"

run_distributed_validation() {
  local dist_dir="${VALIDATION_DIR}/distributed"
  mkdir -p "${dist_dir}"
  printf '%s\n' "${dist_dir}" > "${dist_dir}/path.txt"
  local specs=(
    "post:1" "post:2" "post:4" "post:8" "post:16"
    "dist2:2" "dist2:4" "dist2:8" "dist2:16"
    "dist4:4" "dist4:8" "dist4:16"
    "dist8:8" "dist8:16"
  )
  for spec in "${specs[@]}"; do
    local placement="${spec%:*}"
    local ev="${spec#*:}"
    echo "==> distributed validation ${placement} ev${ev}" >&2
    env -u PGOT_RAW_DIR "${ROOT_DIR}/layer2/02_density_func/bench_retpoline" \
      --base-work 64 --pgot-events "${ev}" --placement "${placement}" \
      -n "${ITERATIONS}" -r "${VALIDATION_REPEATS}" "${CPU_ARG[@]}" \
      > "${dist_dir}/${placement}_ev${ev}.txt"
  done
}

run_distributed_validation

run_layer2_func_perf() {
  local bw="$1"
  local ev="$2"
  local name="layer2_func_retpoline_bw${bw}_ev${ev}"
  echo "==> perf ${name}" >&2
  local cmd=(
    perf stat -x, -r "${PERF_REPEATS}" -e "${PERF_EVENTS}"
    -o "${VALIDATION_DIR}/${name}.perf.csv" --
    env -u PGOT_RAW_DIR "${ROOT_DIR}/layer2/02_density_func/bench_retpoline"
    --base-work "${bw}" --pgot-events "${ev}"
    -n "${PERF_ITERATIONS}" -r 1 "${CPU_ARG[@]}"
  )
  if [[ "${SUDO_PASSWORD:-}" != "" ]]; then
    printf '%s\n' "${SUDO_PASSWORD}" | sudo -S "${cmd[@]}"
  else
    "${cmd[@]}"
  fi
}

for bw in 16 64 256 512; do
  run_layer2_func_perf "${bw}" 1
done
for ev in 4 8 16; do
  run_layer2_func_perf 64 "${ev}"
done

echo "wrote ${OUT}" >&2
echo "wrote ${RAW_DIR}" >&2
echo "wrote ${VALIDATION_DIR}" >&2
