#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ -s "$HERE/libkernel.so" ]]; then
	PACKAGE=${PACKAGE:-$HERE}
	CONTROL_DIR=${CONTROL_DIR:-$HERE}
else
	PACKAGE=${PACKAGE:-$HERE/../baremetal/artifacts/current-update}
	CONTROL_DIR=${CONTROL_DIR:-$HERE}
fi
RESULTS_DIR=${RESULTS_DIR:-$CONTROL_DIR/results}
STATE=${STATE_FILE:-$CONTROL_DIR/.active-update-run-id}
CPU=${CPU:-2}
REPEATS=${REPEATS:-15}
UPDATE_SECONDS=${UPDATE_SECONDS:-15}
WARMUP=${WARMUP:-100000}
SEQ_ITERATIONS=${SEQ_ITERATIONS:-50000000}
VKSO_ONLY=${VKSO_ONLY:-0}
DEBUGFS=/sys/kernel/debug
BENCH_DIR=$DEBUGFS/timekeeping_update_bench

if [[ $(id -u) -ne 0 ]]; then
	exec sudo --preserve-env=PACKAGE,CONTROL_DIR,RESULTS_DIR,STATE_FILE,CPU,REPEATS,UPDATE_SECONDS,WARMUP,SEQ_ITERATIONS,VKSO_ONLY \
		"$0" "$@"
fi

case "$VKSO_ONLY" in
0|1)
	;;
*)
	echo "VKSO_ONLY must be 0 or 1" >&2
	exit 2
	;;
esac

for file in SHA256SUMS boot-manifest.txt vkso-time-bench \
	raw.config vkso.config libkernel.so compare-update.py \
	raw-abi-matrix vkso-abi-matrix page_mappings.txt \
	page_cache_replace.ko manager; do
	test -s "$PACKAGE/$file" || {
		echo "missing update benchmark artifact: $PACKAGE/$file" >&2
		exit 1
	}
done
(cd "$PACKAGE" && sha256sum -c SHA256SUMS)
grep -Fqx 'build_variant=normal' "$PACKAGE/boot-manifest.txt"
grep -Fqx 'update_bench=1' "$PACKAGE/boot-manifest.txt"

probe=$("$PACKAGE/vkso-time-bench" --probe)
backend=$(printf '%s\n' "$probe" |
	awk -F= '$1 == "backend" { print $2; exit }')
case "$backend" in
raw|vkso)
	;;
*)
	echo "cannot identify booted backend" >&2
	printf '%s\n' "$probe" >&2
	exit 1
	;;
esac

expected_image=vkso-time-$backend-update-5.15.198.bzImage
boot_image=$(awk '{
	for (i = 1; i <= NF; ++i) {
		if ($i ~ /^BOOT_IMAGE=/) {
			sub(/^BOOT_IMAGE=/, "", $i)
			print $i
			exit
		}
	}
}' /proc/cmdline)
if [[ ${boot_image##*/} != "$expected_image" ]]; then
	echo "boot/package mismatch: expected $expected_image, got ${boot_image:-missing}" >&2
	exit 1
fi

test "$(uname -r)" = 5.15.198
grep -Fqx 'CONFIG_TIMEKEEPING_UPDATE_BENCH=y' \
	"$PACKAGE/$backend.config"
if ! mountpoint -q "$DEBUGFS"; then
	mount -t debugfs debugfs "$DEBUGFS"
fi
test -w "$BENCH_DIR/control"
test -r "$BENCH_DIR/samples"

clocksource=$(cat /sys/devices/system/clocksource/clocksource0/current_clocksource)
test "$clocksource" = tsc || {
	echo "expected TSC clocksource, got $clocksource" >&2
	exit 1
}
grep -qw nokaslr /proc/cmdline
test -d "/sys/devices/system/cpu/cpu$CPU"
test "$(cat /sys/devices/system/cpu/cpu$CPU/online 2>/dev/null || echo 1)" = 1
if [[ -r /sys/devices/system/cpu/smt/active ]]; then
	test "$(cat /sys/devices/system/cpu/smt/active)" = 0 || {
		echo "SMT is active; use the update-bench GRUB entry" >&2
		exit 1
	}
fi

set_sysfs_value()
{
	local path=$1 expected=$2

	[[ -r "$path" ]] || return 0
	[[ $(cat "$path") == "$expected" ]] && return 0
	printf '%s\n' "$expected" >"$path"
	[[ $(cat "$path") == "$expected" ]]
}

set_sysfs_value /sys/devices/system/cpu/intel_pstate/no_turbo 1
set_sysfs_value /sys/devices/system/cpu/intel_pstate/min_perf_pct 100
set_sysfs_value /sys/devices/system/cpu/intel_pstate/max_perf_pct 100
for governor in /sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do
	[[ -e "$governor" ]] && set_sysfs_value "$governor" performance
done

collection_mode=paired
if [[ "$backend" == raw ]]; then
	if [[ "$VKSO_ONLY" == 1 ]]; then
		echo "VKSO_ONLY=1 requires the VKSO update-bench kernel" >&2
		exit 1
	fi
	run_id=${1:-$(date -u +%Y%m%dT%H%M%SZ)-update}
	printf '%s\n' "$run_id" >"$STATE"
elif [[ "$VKSO_ONLY" == 1 ]]; then
	collection_mode=vkso-only
	run_id=${1:-$(date -u +%Y%m%dT%H%M%SZ)-vkso-update}
else
	if [[ $# -gt 0 ]]; then
		run_id=$1
	elif [[ -r "$STATE" ]]; then
		run_id=$(cat "$STATE")
	else
		echo "missing Raw update run; boot Raw and collect first" >&2
		exit 1
	fi
	test -s "$RESULTS_DIR/$run_id/raw/metadata.txt" || {
		echo "Raw update result is missing for run $run_id" >&2
		exit 1
	}
fi

result_root=$RESULTS_DIR/$run_id
out=$result_root/$backend
if [[ -e "$out/complete" ]]; then
	echo "$backend update result already complete: $out" >&2
	exit 1
fi
mkdir -p "$out/3.2-idle" "$out/3.3-concurrent"
printf '%s\n' "$probe" >"$out/backend-probe.txt"
zcat /proc/config.gz >"$out/running.config"
cmp -s "$PACKAGE/$backend.config" "$out/running.config"
{
	date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
	printf 'backend=%s\n' "$backend"
	printf 'run_id=%s\n' "$run_id"
	printf 'cpu=%s\n' "$CPU"
	printf 'repeats=%s\n' "$REPEATS"
	printf 'update_seconds=%s\n' "$UPDATE_SECONDS"
	printf 'warmup=%s\n' "$WARMUP"
	printf 'seq_iterations=%s\n' "$SEQ_ITERATIONS"
	printf 'collection_mode=%s\n' "$collection_mode"
	printf 'clocksource=%s\n' "$clocksource"
	printf 'cmdline=%s\n' "$(cat /proc/cmdline)"
	printf 'package=%s\n' "$PACKAGE"
} >"$out/metadata.txt"

recorder_running=0
module_loaded=0
replaced=0
cleanup_all()
{
	local status=0

	set +e
	if [[ "$recorder_running" == 1 ]]; then
		printf 'stop\n' >"$BENCH_DIR/control" || status=$?
		recorder_running=0
	fi
	if [[ "$replaced" == 1 ]]; then
		"$PACKAGE/manager" restore "$PACKAGE/libkernel.so" \
			"$PACKAGE/page_mappings.txt" || status=$?
		replaced=0
	fi
	if [[ "$module_loaded" == 1 ]]; then
		rmmod page_cache_replace || status=$?
		module_loaded=0
	fi
	set -e
	return "$status"
}
trap 'cleanup_all || true' EXIT INT TERM

if [[ "$backend" == vkso ]]; then
	if grep -q '^page_cache_replace ' /proc/modules; then
		echo "page_cache_replace is already loaded; restore prior run first" >&2
		exit 1
	fi
	insmod "$PACKAGE/page_cache_replace.ko"
	module_loaded=1
	"$PACKAGE/manager" validate "$PACKAGE/libkernel.so" \
		"$PACKAGE/page_mappings.txt"
	"$PACKAGE/manager" replace "$PACKAGE/libkernel.so" \
		"$PACKAGE/page_mappings.txt"
	replaced=1
	LD_LIBRARY_PATH="$PACKAGE" "$PACKAGE/vkso-abi-matrix" \
		>"$out/functional.log" 2>&1
else
	LD_LIBRARY_PATH="$PACKAGE" "$PACKAGE/raw-abi-matrix" \
		>"$out/functional.log" 2>&1
fi
grep -Fq 'abi_matrix_status=pass' "$out/functional.log"
tr -d '\r' <"$out/functional.log" |
	grep -E '^(semantics|path|namespace)\.' >"$out/functional.matrix"

record_command()
{
	local sample_file=$1
	shift

	printf 'start\n' >"$BENCH_DIR/control"
	recorder_running=1
	"$@"
	printf 'stop\n' >"$BENCH_DIR/control"
	recorder_running=0
	cp "$BENCH_DIR/samples" "$sample_file"
}

for ((round = 0; round < REPEATS; round++)); do
	index=$(printf '%02d' "$round")
	printf 'update round=%d/%d scenario=idle\n' "$((round + 1))" "$REPEATS"
	record_command "$out/3.2-idle/round-$index-writer.csv" \
		sleep "$UPDATE_SECONDS"

	for operation in monotonic monotonic_raw monotonic_coarse; do
		printf 'update round=%d/%d scenario=%s\n' \
			"$((round + 1))" "$REPEATS" "$operation"
		scenario=$out/3.3-concurrent/$operation
		mkdir -p "$scenario"
		record_command "$scenario/round-$index-writer.csv" \
			"$PACKAGE/vkso-time-bench" \
			--backend "$backend" --mode load --cpu "$CPU" \
			--operation "$operation" --seconds "$UPDATE_SECONDS" \
			--warmup "$WARMUP" \
			>"$scenario/round-$index-reader.csv"
	done

	scenario=$out/3.3-concurrent/seq_protocol
	printf 'update round=%d/%d scenario=seq_protocol\n' \
		"$((round + 1))" "$REPEATS"
	mkdir -p "$scenario"
	record_command "$scenario/round-$index-writer.csv" \
		"$PACKAGE/vkso-time-bench" \
		--backend "$backend" --mode seq --cpu "$CPU" \
		--seq-iterations "$SEQ_ITERATIONS" \
		>"$scenario/round-$index-reader.csv"
done

printf 'stop\n' >"$BENCH_DIR/control"
cleanup_all
"$PACKAGE/compare-update.py" --backend-dir "$out"
touch "$out/complete"
trap - EXIT INT TERM

if [[ "$backend" == raw ]]; then
	echo "raw_update_result=$out"
	echo "active_run_id=$run_id"
	echo "next_step=$CONTROL_DIR/boot-vkso-update.sh"
else
	echo "vkso_update_result=$out"
	if [[ "$collection_mode" == paired ]]; then
		"$PACKAGE/compare-update.py" --result-root "$result_root"
		echo "comparison=$result_root/update-comparison.csv"
		echo "summary=$result_root/UPDATE_SUMMARY.md"
	else
		echo "backend_summary=$out/update-summary.csv"
	fi
fi
