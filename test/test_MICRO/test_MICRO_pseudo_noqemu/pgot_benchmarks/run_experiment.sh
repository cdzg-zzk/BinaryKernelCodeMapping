#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"

ITERATIONS="${ITERATIONS:-1000000}"
REPEATS="${REPEATS:-31}"
OUTER_RUNS="${OUTER_RUNS:-100}"
PERF_ITERATIONS="${PERF_ITERATIONS:-5000000}"
PERF_REPEATS="${PERF_REPEATS:-3}"
PERF_EVENTS="${PERF_EVENTS:-cycles,instructions,branches,branch-misses,L1-dcache-loads,L1-dcache-load-misses,iTLB-load-misses,dTLB-load-misses}"
SAMPLE_ORDER="${SAMPLE_ORDER:-interleave}"
RUN_VALIDATION="${RUN_VALIDATION:-1}"
RUN_PERF="${RUN_PERF:-0}"
CLEAR_RESULTS="${CLEAR_RESULTS:-1}"

CPU_ARG=()
if [[ "${CPU:-}" != "" ]]; then
  CPU_ARG=(-c "${CPU}")
fi

usage() {
  cat <<'EOF'
Usage:
  ./run_experiment.sh list
  ./run_experiment.sh all
  ./run_experiment.sh <experiment>

Experiments:
  layer1-data-independent
  layer1-data-dependent
  layer1-func-stable
  layer1-func-entropy
  layer2-data-placement
  layer2-func-placement

Common environment variables:
  CPU=2
  ITERATIONS=1000000
  REPEATS=31
  OUTER_RUNS=100                 used by layer1 kernel-module runs
  SAMPLE_ORDER=interleave        layer2 placement experiments
  RUN_VALIDATION=1               objdump/distributed validation where available
  RUN_PERF=0                     set to 1 to collect perf auxiliary evidence
  CLEAR_RESULTS=1                clear this experiment's old result directory first
EOF
}

list_experiments() {
  printf '%s\n' \
    layer1-data-independent \
    layer1-data-dependent \
    layer1-func-stable \
    layer1-func-entropy \
    layer2-data-placement \
    layer2-func-placement
}

prepare_exp_dir() {
  local dir="$1"
  if [[ "${CLEAR_RESULTS}" == "1" ]]; then
    rm -rf "${dir}"
  fi
  mkdir -p "${dir}/main"
}

write_environment() {
  local file="$1"
  local experiment="$2"
  {
    echo "# generated_by=run_experiment.sh"
    echo "# experiment=${experiment}"
    echo "# iterations=${ITERATIONS}"
    echo "# repeats=${REPEATS}"
    if [[ "${CPU:-}" != "" ]]; then
      echo "# cpu=${CPU}"
    else
      echo "# cpu=unpinned"
    fi
    bash "${ROOT_DIR}/collect_env.sh"
  } > "${file}"
}

run_bench_to_csv() {
  local label="$1"
  local bin="$2"
  local out="$3"
  shift 3
  echo "==> ${label}" >&2
  "${bin}" -n "${ITERATIONS}" -r "${REPEATS}" "${CPU_ARG[@]}" "$@" >> "${out}"
}

run_perf_stat() {
  local out="$1"
  shift
  local cmd=(
    perf stat -x, -r "${PERF_REPEATS}" -e "${PERF_EVENTS}"
    -o "${out}" --
    "$@"
  )
  if [[ "${SUDO_PASSWORD:-}" != "" ]]; then
    printf '%s\n' "${SUDO_PASSWORD}" | sudo -S "${cmd[@]}"
  else
    "${cmd[@]}"
  fi
}

run_layer1_data_independent() {
  local exp_dir="${RESULTS_DIR}/layer1/01_data_independent"
  local bench_dir="${ROOT_DIR}/layer1/01_data_independent"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer1_data_dependent() {
  local exp_dir="${RESULTS_DIR}/layer1/02_data_dependent"
  local bench_dir="${ROOT_DIR}/layer1/02_data_dependent"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer1_func_stable() {
  local exp_dir="${RESULTS_DIR}/layer1/03_func_stable"
  local bench_dir="${ROOT_DIR}/layer1/03_func_stable"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer1_func_entropy() {
  local exp_dir="${RESULTS_DIR}/layer1/func_entropy"
  local bench_dir="${ROOT_DIR}/layer1/04_func_entropy"
  prepare_exp_dir "${exp_dir}"
  write_environment "${exp_dir}/environment.txt" "layer1-func-entropy"
  make -C "${bench_dir}" all
  run_bench_to_csv "layer1 func entropy no-ret" "${bench_dir}/bench_noret" "${exp_dir}/main/results.csv"
  run_bench_to_csv "layer1 func entropy retpoline" "${bench_dir}/bench_retpoline" "${exp_dir}/main/results.csv"
  echo "wrote ${exp_dir}" >&2
}

run_layer2_data_perf() {
  local exp_dir="$1"
  local bench="${ROOT_DIR}/layer2/01_density_data/bench"
  mkdir -p "${exp_dir}/perf"
  {
    echo "# generated_by=run_experiment.sh"
    echo "# experiment=layer2-data-placement"
    echo "# perf_iterations=${PERF_ITERATIONS}"
    echo "# perf_repeats=${PERF_REPEATS}"
    echo "# perf_events=${PERF_EVENTS}"
    bash "${ROOT_DIR}/collect_env.sh"
  } > "${exp_dir}/perf/environment.txt"

  local specs=("dist1:16" "dist8:16" "dist1:32" "dist8:32")
  for spec in "${specs[@]}"; do
    local placement="${spec%:*}"
    local ev="${spec#*:}"
    local name="bw64_${placement}_ev${ev}"
    echo "==> perf layer2 data ${name}" >&2
    run_perf_stat "${exp_dir}/perf/${name}.perf.csv" \
      env -u PGOT_RAW_DIR "${bench}" --base-work 64 --placement "${placement}" \
      --pgot-events "${ev}" --sample-order "${SAMPLE_ORDER}" \
      -n "${PERF_ITERATIONS}" -r 1 "${CPU_ARG[@]}"
  done
}

run_layer2_data_placement() {
  local exp_dir="${RESULTS_DIR}/layer2/data_placement"
  local bench_dir="${ROOT_DIR}/layer2/01_density_data"
  prepare_exp_dir "${exp_dir}"
  mkdir -p "${exp_dir}/raw"
  write_environment "${exp_dir}/environment.txt" "layer2-data-placement"
  make -C "${bench_dir}" all
  PGOT_RAW_DIR="${exp_dir}/raw" \
    run_bench_to_csv "layer2 data placement" "${bench_dir}/bench" "${exp_dir}/main/results.csv" \
      --sample-order "${SAMPLE_ORDER}"

  if [[ "${RUN_PERF}" == "1" ]]; then
    run_layer2_data_perf "${exp_dir}"
  fi

  echo "wrote ${exp_dir}" >&2
}

run_layer2_func_distributed_validation() {
  local exp_dir="$1"
  local bin="${ROOT_DIR}/layer2/02_density_func/bench_retpoline"
  local dist_dir="${exp_dir}/validation/distributed"
  mkdir -p "${dist_dir}"
  local specs=(
    "dist1:1" "dist1:2" "dist1:4" "dist1:8" "dist1:16"
    "dist2:2" "dist2:4" "dist2:8" "dist2:16"
    "dist4:4" "dist4:8" "dist4:16"
    "dist8:8" "dist8:16"
  )
  for spec in "${specs[@]}"; do
    local placement="${spec%:*}"
    local ev="${spec#*:}"
    echo "==> distributed validation ${placement} ev${ev}" >&2
    env -u PGOT_RAW_DIR "${bin}" \
      --base-work 64 --placement "${placement}" --pgot-events "${ev}" \
      --sample-order "${SAMPLE_ORDER}" \
      -n "${ITERATIONS}" -r "${REPEATS}" "${CPU_ARG[@]}" \
      > "${dist_dir}/${placement}_ev${ev}.txt"
  done
}

run_layer2_func_perf() {
  local exp_dir="$1"
  local bin="${ROOT_DIR}/layer2/02_density_func/bench_retpoline"
  mkdir -p "${exp_dir}/perf"
  {
    echo "# generated_by=run_experiment.sh"
    echo "# experiment=layer2-func-placement"
    echo "# perf_iterations=${PERF_ITERATIONS}"
    echo "# perf_repeats=${PERF_REPEATS}"
    echo "# perf_events=${PERF_EVENTS}"
    bash "${ROOT_DIR}/collect_env.sh"
  } > "${exp_dir}/perf/environment.txt"

  local specs=(
    "64:dist1:1" "64:dist8:1"
    "64:dist1:16" "64:dist8:16"
    "32:dist1:16" "128:dist1:16"
  )
  for spec in "${specs[@]}"; do
    local bw="${spec%%:*}"
    local rest="${spec#*:}"
    local placement="${rest%:*}"
    local ev="${rest#*:}"
    local name="retpoline_bw${bw}_${placement}_ev${ev}"
    echo "==> perf layer2 func ${name}" >&2
    run_perf_stat "${exp_dir}/perf/${name}.perf.csv" \
      env -u PGOT_RAW_DIR "${bin}" --base-work "${bw}" --placement "${placement}" \
      --pgot-events "${ev}" --sample-order "${SAMPLE_ORDER}" \
      -n "${PERF_ITERATIONS}" -r 1 "${CPU_ARG[@]}"
  done
}

run_layer2_func_placement() {
  local exp_dir="${RESULTS_DIR}/layer2/func_placement"
  local bench_dir="${ROOT_DIR}/layer2/02_density_func"
  prepare_exp_dir "${exp_dir}"
  mkdir -p "${exp_dir}/raw"
  write_environment "${exp_dir}/environment.txt" "layer2-func-placement"
  make -C "${bench_dir}" all
  PGOT_RAW_DIR="${exp_dir}/raw" \
    run_bench_to_csv "layer2 func placement no-ret" "${bench_dir}/bench_noret" "${exp_dir}/main/results.csv" \
      --sample-order "${SAMPLE_ORDER}"
  PGOT_RAW_DIR="${exp_dir}/raw" \
    run_bench_to_csv "layer2 func placement retpoline" "${bench_dir}/bench_retpoline" "${exp_dir}/main/results.csv" \
      --sample-order "${SAMPLE_ORDER}"

  if [[ "${RUN_VALIDATION}" == "1" ]]; then
    mkdir -p "${exp_dir}/validation"
    objdump -d "${bench_dir}/bench_retpoline" \
      > "${exp_dir}/validation/objdump_func_placement_retpoline.txt"
    run_layer2_func_distributed_validation "${exp_dir}"
  fi

  if [[ "${RUN_PERF}" == "1" ]]; then
    run_layer2_func_perf "${exp_dir}"
  fi

  echo "wrote ${exp_dir}" >&2
}

run_all() {
  run_layer1_data_independent
  run_layer1_data_dependent
  run_layer1_func_stable
  run_layer2_data_placement
  run_layer2_func_placement
}

case "${1:-}" in
  list)
    list_experiments
    ;;
  all)
    run_all
    ;;
  layer1-data-independent)
    run_layer1_data_independent
    ;;
  layer1-data-dependent)
    run_layer1_data_dependent
    ;;
  layer1-func-stable)
    run_layer1_func_stable
    ;;
  layer1-func-entropy)
    run_layer1_func_entropy
    ;;
  layer2-data-placement)
    run_layer2_data_placement
    ;;
  layer2-func-placement)
    run_layer2_func_placement
    ;;
  -h|--help|"")
    usage
    ;;
  *)
    echo "unknown experiment: $1" >&2
    usage >&2
    exit 2
    ;;
esac
