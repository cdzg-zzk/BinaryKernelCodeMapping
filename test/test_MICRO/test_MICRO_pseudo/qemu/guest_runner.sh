#!/bin/busybox sh
set -eu

CMDLINE="$(cat /proc/cmdline)"

get_arg() {
	local key="$1"
	local token
	for token in ${CMDLINE}; do
		case "${token}" in
			"${key}"=*)
				echo "${token#*=}"
				return 0
				;;
		esac
	done
	return 1
}

OUTER_REPEATS="$(get_arg outer_repeats || true)"
OUTER_REPEATS="${OUTER_REPEATS:-5}"
WARMUP="$(get_arg warmup || true)"
WARMUP="${WARMUP:-3}"
REPEAT="$(get_arg repeat || true)"
REPEAT="${REPEAT:-9}"
SEED="$(get_arg seed || true)"
SEED="${SEED:-0x1234}"
BATCH_ITERS="$(get_arg batch_iters || true)"
BATCH_ITERS="${BATCH_ITERS:-8192}"
INPUT_LEN="$(get_arg input_len || true)"
INPUT_LEN="${INPUT_LEN:-256}"
TARGET_CALLS="$(get_arg target_calls || true)"
TARGET_CALLS="${TARGET_CALLS:-200000}"
ITERS="$(get_arg iters || true)"
ITERS="${ITERS:-0}"
VARIANTS="kernel_native kernel_micro"
BENCHMARK="crc32_le"
PERF_EVENTS="cycles,instructions,branches,branch-misses,cache-references,cache-misses,L1-icache-load-misses,iTLB-load-misses"

emit_file() {
	local relpath="$1"
	local src="$2"
	echo "@@BEGIN_FILE@@ path=${relpath}"
	cat "${src}"
	echo "@@END_FILE@@"
}

extract_checksum() {
	/bin/grep '^checksum=' "$1" | /bin/sed -n '1s/^checksum=//p'
}

run_variant() {
	local outer="$1"
	local variant="$2"
	local prefix="/tmp/outer${outer}_${BENCHMARK}_${variant}"
	local cmd="variant=${variant} iters=${ITERS} warmup=${WARMUP} repeat=${REPEAT} seed=${SEED} cpu=0 batch_iters=${BATCH_ITERS} input_len=${INPUT_LEN}"

	echo "@@RUN@@ outer=${outer} benchmark=${BENCHMARK} variant=${variant}"
	/usr/bin/perf stat -x, -e "${PERF_EVENTS}" -o "${prefix}.perf.csv" -- \
		/bin/sh -c "printf '%s\n' '${cmd}' > /proc/micro_pseudo/run; cat /proc/micro_pseudo/last_result" \
		> "${prefix}.result.txt"

	emit_file "raw/outer${outer}_${BENCHMARK}_${variant}.result.txt" "${prefix}.result.txt"
	emit_file "raw/outer${outer}_${BENCHMARK}_${variant}.perf.csv" "${prefix}.perf.csv"
}

if [ "${ITERS}" = "0" ]; then
	ITERS="${TARGET_CALLS}"
fi

outer=1
while [ "${outer}" -le "${OUTER_REPEATS}" ]; do
	reference_sum=""
	for variant in ${VARIANTS}; do
		run_variant "${outer}" "${variant}"
		current_sum="$(extract_checksum "/tmp/outer${outer}_${BENCHMARK}_${variant}.result.txt")"
		if [ -z "${reference_sum}" ]; then
			reference_sum="${current_sum}"
		elif [ "${reference_sum}" != "${current_sum}" ]; then
			echo "@@FATAL@@ checksum mismatch outer=${outer} variant=${variant} expected=${reference_sum} actual=${current_sum}"
			exit 1
		fi
	done
	outer=$(( outer + 1 ))
done
