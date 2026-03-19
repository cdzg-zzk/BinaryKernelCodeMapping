#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULT_DIR="${RESULT_DIR_OVERRIDE:-${ROOT_DIR}/results/$(date -u +%Y%m%dT%H%M%SZ)}"
RAW_DIR="${RESULT_DIR}/raw"
KERNEL_DIR="${ROOT_DIR}/kernel"
MICRO_KO="${KERNEL_DIR}/micro.ko"
MICRO_PSEUDO_KO="${KERNEL_DIR}/micro_pseudo.ko"
CPU="${1:-0}"
OUTER_REPEATS="${OUTER_REPEATS:-5}"
VARIANTS="${VARIANTS:-kernel_native kernel_micro}"
ITERS="${ITERS:-200000}"
WARMUP="${WARMUP:-3}"
REPEAT="${REPEAT:-9}"
SEED="${SEED:-0x1234}"
BATCH_ITERS="${BATCH_ITERS:-8192}"
INPUT_LEN="${INPUT_LEN:-256}"
PERF_EVENTS="${PERF_EVENTS:-cycles,instructions,branches,branch-misses,cache-references,cache-misses,L1-icache-load-misses,iTLB-load-misses}"
AUTO_LOADED_MODULES=0

mkdir -p "${RAW_DIR}"

sudo_run() {
	if [[ -n "${SUDO_PASSWORD:-}" ]]; then
		printf '%s\n' "${SUDO_PASSWORD}" | sudo -S "$@"
	else
		sudo "$@"
	fi
}

cleanup_modules() {
	if [[ "${AUTO_LOADED_MODULES}" != "1" ]]; then
		return
	fi

	sudo_run rmmod micro_pseudo >/dev/null 2>&1 || true
	sudo_run rmmod micro >/dev/null 2>&1 || true
}

ensure_modules_loaded() {
	if [[ -e /proc/micro_pseudo/run ]]; then
		return
	fi

	if [[ ! -f "${MICRO_KO}" || ! -f "${MICRO_PSEUDO_KO}" ]]; then
		echo "missing built modules: ${MICRO_KO} or ${MICRO_PSEUDO_KO}" >&2
		echo "run: make -C ${KERNEL_DIR} KDIR=/lib/modules/\$(uname -r)/build all" >&2
		exit 1
	fi

	sudo_run insmod "${MICRO_KO}"
	sudo_run insmod "${MICRO_PSEUDO_KO}"
	AUTO_LOADED_MODULES=1

	if [[ ! -e /proc/micro_pseudo/run ]]; then
		echo "/proc/micro_pseudo/run not found after loading modules" >&2
		exit 1
	fi
}

trap cleanup_modules EXIT

cat > "${RESULT_DIR}/run_env.txt" <<EOF
benchmark=crc32_le
cpu=${CPU}
outer_repeats=${OUTER_REPEATS}
variants=${VARIANTS}
iters=${ITERS}
warmup=${WARMUP}
repeat=${REPEAT}
seed=${SEED}
batch_iters=${BATCH_ITERS}
input_len=${INPUT_LEN}
perf_events=${PERF_EVENTS}
timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

run_variant() {
	local outer="$1"
	local variant="$2"
	local prefix="${RAW_DIR}/outer${outer}_crc32_le_${variant}"
	local cmd="variant=${variant} iters=${ITERS} warmup=${WARMUP} repeat=${REPEAT} seed=${SEED} cpu=${CPU} batch_iters=${BATCH_ITERS} input_len=${INPUT_LEN}"

	echo "==> outer=${outer} benchmark=crc32_le variant=${variant}"
	if [[ "${CPU}" == "-1" ]]; then
		sudo_run perf stat -x, -e "${PERF_EVENTS}" -o "${prefix}.perf.csv" -- \
			bash -lc "printf '%s\n' '${cmd}' | tee /proc/micro_pseudo/run >/dev/null; cat /proc/micro_pseudo/last_result" \
			| tee "${prefix}.result.txt"
	else
		sudo_run taskset -c "${CPU}" perf stat -x, -e "${PERF_EVENTS}" -o "${prefix}.perf.csv" -- \
			bash -lc "printf '%s\n' '${cmd}' | tee /proc/micro_pseudo/run >/dev/null; cat /proc/micro_pseudo/last_result" \
			| tee "${prefix}.result.txt"
	fi
	sudo_run chown "$(id -u):$(id -g)" "${prefix}.perf.csv"
}

extract_checksum() {
	local file="$1"
	awk -F= '$1 == "checksum" { print $2; exit }' "${file}"
}

ensure_modules_loaded

for outer in $(seq 1 "${OUTER_REPEATS}"); do
	reference_sum=""
	for variant in ${VARIANTS}; do
		run_variant "${outer}" "${variant}"
		current_sum="$(extract_checksum "${RAW_DIR}/outer${outer}_crc32_le_${variant}.result.txt")"
		if [[ -z "${reference_sum}" ]]; then
			reference_sum="${current_sum}"
		elif [[ "${reference_sum}" != "${current_sum}" ]]; then
			echo "checksum mismatch for outer=${outer}: expected=${reference_sum} variant=${variant} actual=${current_sum}" >&2
			exit 1
		fi
	done
done

echo "results written to ${RESULT_DIR}"
