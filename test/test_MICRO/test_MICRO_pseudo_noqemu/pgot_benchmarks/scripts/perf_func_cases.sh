#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/results/perf"
ITERATIONS="${ITERATIONS:-5000000}"
REPEATS="${REPEATS:-7}"
CPU_ARG=()
EVENTS="cycles,instructions,branches,branch-misses,L1-dcache-loads,L1-dcache-load-misses,iTLB-load-misses,dTLB-load-misses"

if [[ "${CPU:-}" != "" ]]; then
  CPU_ARG=(-c "${CPU}")
fi

mkdir -p "${OUT_DIR}"
{
  echo "# generated_by=scripts/perf_func_cases.sh"
  echo "# iterations=${ITERATIONS}"
  echo "# repeats=${REPEATS}"
  if [[ "${CPU:-}" != "" ]]; then
    echo "# cpu=${CPU}"
  fi
  bash "${ROOT_DIR}/scripts/collect_env.sh"
  echo "# perf_events=${EVENTS}"
} > "${OUT_DIR}/environment.txt"

make -C "${ROOT_DIR}/layer1/03_func_stable" all
make -C "${ROOT_DIR}/layer1/04_func_entropy" all

run_perf() {
  local name="$1"
  shift
  echo "==> perf ${name}" >&2
  perf stat -x, -r "${REPEATS}" -e "${EVENTS}" -o "${OUT_DIR}/${name}.perf.csv" -- "$@"
}

for build in noret retpoline; do
  bin="${ROOT_DIR}/layer1/03_func_stable/bench_${build}"
  PGOT_VARIANT=direct run_perf "stable_${build}_direct" "${bin}" -n "${ITERATIONS}" "${CPU_ARG[@]}"
  PGOT_VARIANT=pgot run_perf "stable_${build}_pgot" "${bin}" -n "${ITERATIONS}" "${CPU_ARG[@]}"

  bin="${ROOT_DIR}/layer1/04_func_entropy/bench_${build}"
  for k in 1 2 4 8 16; do
    PGOT_TARGET_COUNT="${k}" run_perf "entropy_${build}_k${k}" "${bin}" -n "${ITERATIONS}" "${CPU_ARG[@]}"
  done
done

echo "wrote ${OUT_DIR}" >&2
