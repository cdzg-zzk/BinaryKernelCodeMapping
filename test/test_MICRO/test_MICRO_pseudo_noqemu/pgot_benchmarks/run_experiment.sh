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
  layer2-func-placement
  layer2-func-fence-diagnostics
  layer3-sha256-transform
  layer3-bch-encode
  layer3-zlib-deflate
  layer3-zstd-decompress
  layer3-crc32-le
  layer3-lz4-compress-fast
  layer3-aes-encrypt
  layer3-lz4-decompress-safe
  layer3-hex-dump-to-buffer
  layer3-string-escape-mem

Common environment variables:
  CPU=2
  ITERATIONS=1000000
  REPEATS=31
  OUTER_RUNS=100                 used by layer1 kernel-module runs
  ITERATIONS_LIST='64 128 256'   layer3 batch-size sweep, if supported
  IRQ_OFF=1                      layer3: disable local IRQs inside timed window
  SAMPLE_ORDER=interleave        user-space placement experiments, if available
  RUN_VALIDATION=1               validation where available
  RUN_PERF=0                     set to 1 to collect perf auxiliary evidence, if available
  CLEAR_RESULTS=1                clear this experiment's old result directory first
EOF
}

list_experiments() {
  printf '%s\n' \
    layer1-data-independent \
    layer1-data-dependent \
    layer1-func-stable \
    layer1-func-entropy \
    layer2-func-placement \
    layer2-func-fence-diagnostics \
    layer3-sha256-transform \
    layer3-bch-encode \
    layer3-zlib-deflate \
    layer3-zstd-decompress \
    layer3-crc32-le \
    layer3-lz4-compress-fast \
    layer3-aes-encrypt \
    layer3-lz4-decompress-safe \
    layer3-hex-dump-to-buffer \
    layer3-string-escape-mem
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

run_layer2_func_placement() {
  local exp_dir="${RESULTS_DIR}/layer2/01_func_placement"
  local bench_dir="${ROOT_DIR}/layer2/01_func_placement"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer2_func_fence_diagnostics() {
  local exp_dir="${RESULTS_DIR}/layer2/01_func_placement"
  local bench_dir="${ROOT_DIR}/layer2/01_func_placement"
  OUT_DIR="${exp_dir}" "${bench_dir}/run_fence_diagnostics.sh"
}

run_layer3_sha256_transform() {
  local exp_dir="${RESULTS_DIR}/layer3/01_sha256_transform"
  local bench_dir="${ROOT_DIR}/layer3/01_sha256_transform"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer3_bch_encode() {
  local exp_dir="${RESULTS_DIR}/layer3/02_bch_encode"
  local bench_dir="${ROOT_DIR}/layer3/02_bch_encode"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer3_zlib_deflate() {
  local exp_dir="${RESULTS_DIR}/layer3/03_zlib_deflate"
  local bench_dir="${ROOT_DIR}/layer3/03_zlib_deflate"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer3_zstd_decompress() {
  local exp_dir="${RESULTS_DIR}/layer3/04_zstd_decompress"
  local bench_dir="${ROOT_DIR}/layer3/04_zstd_decompress"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer3_crc32_le() {
  local exp_dir="${RESULTS_DIR}/layer3/05_crc32_le"
  local bench_dir="${ROOT_DIR}/layer3/05_crc32_le"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer3_lz4_compress_fast() {
  local exp_dir="${RESULTS_DIR}/layer3/06_lz4_compress_fast"
  local bench_dir="${ROOT_DIR}/layer3/06_lz4_compress_fast"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer3_aes_encrypt() {
  local exp_dir="${RESULTS_DIR}/layer3/07_aes_encrypt"
  local bench_dir="${ROOT_DIR}/layer3/07_aes_encrypt"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer3_lz4_decompress_safe() {
  local exp_dir="${RESULTS_DIR}/layer3/08_lz4_decompress_safe"
  local bench_dir="${ROOT_DIR}/layer3/08_lz4_decompress_safe"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer3_hex_dump_to_buffer() {
  local exp_dir="${RESULTS_DIR}/layer3/09_hex_dump_to_buffer"
  local bench_dir="${ROOT_DIR}/layer3/09_hex_dump_to_buffer"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_layer3_string_escape_mem() {
  local exp_dir="${RESULTS_DIR}/layer3/10_string_escape_mem"
  local bench_dir="${ROOT_DIR}/layer3/10_string_escape_mem"
  OUT_DIR="${exp_dir}" "${bench_dir}/run.sh"
}

run_all() {
  run_layer1_data_independent
  run_layer1_data_dependent
  run_layer1_func_stable
  run_layer2_func_placement
  run_layer3_sha256_transform
  run_layer3_bch_encode
  run_layer3_zlib_deflate
  run_layer3_zstd_decompress
  run_layer3_crc32_le
  run_layer3_lz4_compress_fast
  run_layer3_aes_encrypt
  run_layer3_lz4_decompress_safe
  run_layer3_hex_dump_to_buffer
  run_layer3_string_escape_mem
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
  layer2-func-placement)
    run_layer2_func_placement
    ;;
  layer2-func-fence-diagnostics)
    run_layer2_func_fence_diagnostics
    ;;
  layer3-sha256-transform)
    run_layer3_sha256_transform
    ;;
  layer3-bch-encode)
    run_layer3_bch_encode
    ;;
  layer3-zlib-deflate)
    run_layer3_zlib_deflate
    ;;
  layer3-zstd-decompress)
    run_layer3_zstd_decompress
    ;;
  layer3-crc32-le)
    run_layer3_crc32_le
    ;;
  layer3-lz4-compress-fast)
    run_layer3_lz4_compress_fast
    ;;
  layer3-aes-encrypt)
    run_layer3_aes_encrypt
    ;;
  layer3-lz4-decompress-safe)
    run_layer3_lz4_decompress_safe
    ;;
  layer3-hex-dump-to-buffer)
    run_layer3_hex_dump_to_buffer
    ;;
  layer3-string-escape-mem)
    run_layer3_string_escape_mem
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
