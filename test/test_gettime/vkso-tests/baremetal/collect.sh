#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ -s "$HERE/libkernel.so" ]]; then
	PACKAGE=${PACKAGE:-$HERE}
	CONTROL_DIR=${CONTROL_DIR:-$HERE}
else
	PACKAGE=${PACKAGE:-$HERE/artifacts/current}
	CONTROL_DIR=${CONTROL_DIR:-$HERE}
fi
RESULTS_DIR=${RESULTS_DIR:-$CONTROL_DIR/results}
STATE=${STATE_FILE:-$CONTROL_DIR/.active-run-id}
CPU=${CPU:-2}
ITERATIONS=${ITERATIONS:-500000}
REPEATS=${REPEATS:-31}
WARMUP=${WARMUP:-10000}
PMU=${PMU:-1}
SEQ_ITERATIONS=${SEQ_ITERATIONS:-100000000}
LAYOUT_ITERATIONS=${LAYOUT_ITERATIONS:-200000}
VKSO_ONLY=${VKSO_ONLY:-auto}
VKSO_REFERENCE=${VKSO_REFERENCE:-}
RUN_SEQ=${RUN_SEQ:-auto}
RUN_LAYOUT=${RUN_LAYOUT:-auto}

if [[ $(id -u) -ne 0 ]]; then
	exec sudo --preserve-env=PACKAGE,CONTROL_DIR,RESULTS_DIR,STATE_FILE,CPU,ITERATIONS,REPEATS,WARMUP,PMU,SEQ_ITERATIONS,LAYOUT_ITERATIONS,VKSO_ONLY,VKSO_REFERENCE,RUN_SEQ,RUN_LAYOUT \
		"$0" "$@"
fi

for file in SHA256SUMS boot-manifest.txt vkso-time-bench \
	raw-abi-matrix vkso-abi-matrix libkernel.so page_mappings.txt \
	page_cache_replace.ko manager compare.py compare-vkso.py \
	raw.config vkso.config; do
	test -s "$PACKAGE/$file" || {
		echo "missing package artifact: $PACKAGE/$file" >&2
		exit 1
	}
done
(cd "$PACKAGE" && sha256sum -c SHA256SUMS)

test "$(uname -r)" = 5.15.198 || {
	echo "expected experimental kernel 5.15.198, got $(uname -r)" >&2
	exit 1
}

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

collection_mode=paired
reference_vkso=
if [[ "$backend" == raw ]]; then
	run_id=${1:-$(date -u +%Y%m%dT%H%M%SZ)-baremetal}
	printf '%s\n' "$run_id" >"$STATE"
else
	if [[ $# -gt 0 ]]; then
		run_id=$1
		if [[ ! -s "$RESULTS_DIR/$run_id/raw/perf.csv" ]]; then
			collection_mode=vkso-only
		fi
	elif [[ "$VKSO_ONLY" != 1 && -r "$STATE" ]]; then
		saved_run_id=$(cat "$STATE")
		saved_root=$RESULTS_DIR/$saved_run_id
		if [[ -s "$saved_root/raw/perf.csv" &&
		      ! -e "$saved_root/vkso/perf.csv" ]]; then
			run_id=$saved_run_id
		else
			run_id=$(date -u +%Y%m%dT%H%M%SZ)-vkso-opt
			collection_mode=vkso-only
			if [[ -s "$saved_root/vkso/perf.csv" ]]; then
				reference_vkso=$saved_root/vkso
			fi
		fi
	else
		run_id=$(date -u +%Y%m%dT%H%M%SZ)-vkso-opt
		collection_mode=vkso-only
	fi
	if [[ "$VKSO_ONLY" == 1 ]]; then
		collection_mode=vkso-only
	fi
	if [[ "$collection_mode" == vkso-only && -n "$VKSO_REFERENCE" ]]; then
		reference_vkso=$VKSO_REFERENCE
		[[ -s "$reference_vkso/perf.csv" ]] ||
			reference_vkso=$VKSO_REFERENCE/vkso
	fi
	if [[ "$collection_mode" == vkso-only &&
	      ! -s "$reference_vkso/perf.csv" ]]; then
		echo "cannot locate prior VKSO baseline; set VKSO_REFERENCE" >&2
		exit 1
	fi
fi

if [[ "$RUN_SEQ" == auto ]]; then
	[[ "$collection_mode" == paired ]] && RUN_SEQ=1 || RUN_SEQ=0
fi
if [[ "$RUN_LAYOUT" == auto ]]; then
	[[ "$collection_mode" == paired ]] && RUN_LAYOUT=1 || RUN_LAYOUT=0
fi

clocksource=$(cat /sys/devices/system/clocksource/clocksource0/current_clocksource)
test "$clocksource" = tsc || {
	echo "expected clocksource tsc, got $clocksource" >&2
	exit 1
}
grep -qw nokaslr /proc/cmdline || {
	echo "experimental entry must use nokaslr" >&2
	exit 1
}
test -d "/sys/devices/system/cpu/cpu$CPU" || {
	echo "CPU $CPU does not exist" >&2
	exit 1
}
test "$(cat /sys/devices/system/cpu/cpu$CPU/online 2>/dev/null || echo 1)" = 1
isolated=$(cat /sys/devices/system/cpu/isolated)
if ! printf '%s\n' "$isolated" |
	awk -v cpu="$CPU" '
	{
		n = split($0, ranges, ",")
		for (i = 1; i <= n; ++i) {
			if (ranges[i] ~ /-/) {
				split(ranges[i], bounds, "-")
				if (cpu >= bounds[1] && cpu <= bounds[2])
					found = 1
			} else if (ranges[i] == cpu) {
				found = 1
			}
		}
	}
	END { exit !found }
	'; then
	echo "CPU $CPU is not isolated: $isolated" >&2
	exit 1
fi
if [[ -r /sys/devices/system/cpu/smt/active ]]; then
	test "$(cat /sys/devices/system/cpu/smt/active)" = 0 || {
		echo "SMT is active; use the experiment GRUB entry" >&2
		exit 1
	}
fi

set_sysfs_value()
{
	local path=$1
	local expected=$2
	local current

	[[ -r "$path" ]] || return 0
	current=$(cat "$path")
	[[ "$current" == "$expected" ]] && return 0
	if ! printf '%s\n' "$expected" >"$path"; then
		current=$(cat "$path")
		echo "cannot set $path=$expected (current=$current)" >&2
		return 1
	fi
	current=$(cat "$path")
	[[ "$current" == "$expected" ]] || {
		echo "$path rejected $expected (current=$current)" >&2
		return 1
	}
}

set_sysfs_value /sys/devices/system/cpu/intel_pstate/no_turbo 1
set_sysfs_value /sys/devices/system/cpu/intel_pstate/min_perf_pct 100
set_sysfs_value /sys/devices/system/cpu/intel_pstate/max_perf_pct 100
for governor in /sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do
	[[ -e "$governor" ]] && set_sysfs_value "$governor" performance
done

result_root=$RESULTS_DIR/$run_id
out=$result_root/$backend
mkdir -p "$out"
printf '%s\n' "$probe" >"$out/backend-probe.txt"
zcat /proc/config.gz >"$out/running.config"
cmp -s "$PACKAGE/$backend.config" "$out/running.config" || {
	echo "running kernel config does not match package $backend.config" >&2
	exit 1
}

kernel_cmdline_common=$(sed -E 's/(^| )BOOT_IMAGE=[^ ]+//;s/^ +//;s/  +/ /g' \
	</proc/cmdline)
smt_active=$(cat /sys/devices/system/cpu/smt/active 2>/dev/null || echo unknown)
{
	date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
	printf 'backend=%s\n' "$backend"
	printf 'run_id=%s\n' "$run_id"
	printf 'kernel=%s\n' "$(uname -r)"
	printf 'cpu=%s\n' "$CPU"
	printf 'iterations=%s\n' "$ITERATIONS"
	printf 'repeats=%s\n' "$REPEATS"
	printf 'warmup=%s\n' "$WARMUP"
	printf 'pmu=%s\n' "$PMU"
	printf 'seq_iterations=%s\n' "$SEQ_ITERATIONS"
	printf 'layout_iterations=%s\n' "$LAYOUT_ITERATIONS"
	printf 'collection_mode=%s\n' "$collection_mode"
	printf 'run_seq=%s\n' "$RUN_SEQ"
	printf 'run_layout=%s\n' "$RUN_LAYOUT"
	printf 'reference_vkso=%s\n' "$reference_vkso"
	printf 'clocksource=%s\n' "$clocksource"
	printf 'smt_active=%s\n' "$smt_active"
	printf 'isolated=%s\n' "$isolated"
	printf 'kernel_cmdline_common=%s\n' "$kernel_cmdline_common"
	printf 'package=%s\n' "$PACKAGE"
	printf 'package_manifest_sha256=%s\n' \
		"$(sha256sum "$PACKAGE/boot-manifest.txt" | awk '{print $1}')"
	printf 'package_git_commit=%s\n' \
		"$(awk -F= '$1 == "git_commit" { print $2; exit }' \
			"$PACKAGE/boot-manifest.txt")"
	printf 'package_vkso_image_sha256=%s\n' \
		"$(awk -F= '$1 == "vkso_image_sha256" { print $2; exit }' \
			"$PACKAGE/boot-manifest.txt")"
	printf 'package_libkernel_sha256=%s\n' \
		"$(sha256sum "$PACKAGE/libkernel.so" | awk '{print $1}')"
	for file in \
		/sys/devices/system/cpu/intel_pstate/no_turbo \
		/sys/devices/system/cpu/intel_pstate/min_perf_pct \
		/sys/devices/system/cpu/intel_pstate/max_perf_pct \
		/sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do
		[[ -r "$file" ]] && printf '%s=%s\n' "$file" "$(cat "$file")"
	done
	lscpu
} >"$out/environment.txt"
cat /proc/interrupts >"$out/interrupts-before.txt"
dmesg >"$out/dmesg-before.txt"

module_loaded=0
replaced=0
cleanup_vkso()
{
	local status=0

	set +e
	if [[ "$replaced" == 1 ]]; then
		"$PACKAGE/manager" restore "$PACKAGE/libkernel.so" \
			"$PACKAGE/page_mappings.txt" ||
			status=$?
		replaced=0
	fi
	if [[ "$module_loaded" == 1 ]]; then
		rmmod page_cache_replace || status=$?
		module_loaded=0
	fi
	set -e
	return "$status"
}
trap 'cleanup_vkso || true' EXIT INT TERM

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

LD_LIBRARY_PATH="$PACKAGE" "$PACKAGE/vkso-time-bench" \
	--backend "$backend" --mode perf --cpu "$CPU" \
	--iterations "$ITERATIONS" --repeats "$REPEATS" \
	--warmup "$WARMUP" --pmu "$PMU" >"$out/perf.csv"
if [[ "$RUN_SEQ" == 1 ]]; then
	LD_LIBRARY_PATH="$PACKAGE" "$PACKAGE/vkso-time-bench" \
		--backend "$backend" --mode seq --cpu "$CPU" \
		--seq-iterations "$SEQ_ITERATIONS" >"$out/seq.csv"
fi
if [[ "$backend" == vkso ]]; then
	if [[ "$RUN_LAYOUT" == 1 ]]; then
		LD_LIBRARY_PATH="$PACKAGE" "$PACKAGE/vkso-time-bench" \
			--backend "$backend" --mode layout --cpu "$CPU" \
			--layout-iterations "$LAYOUT_ITERATIONS" \
			--repeats "$REPEATS" >"$out/layout.csv"
	fi
	cleanup_vkso
	trap - EXIT INT TERM
fi

cat /proc/interrupts >"$out/interrupts-after.txt"
dmesg >"$out/dmesg-after.txt"
sync

if [[ "$backend" == raw ]]; then
	echo "raw_result=$out"
	echo "active_run_id=$run_id"
	echo "next_step=$CONTROL_DIR/boot-vkso.sh"
else
	if [[ "$collection_mode" == paired ]]; then
		"$PACKAGE/compare.py" "$result_root"
		comparison=$result_root/research-questions.csv
		summary=$result_root/SUMMARY.md
	else
		"$PACKAGE/compare-vkso.py" "$reference_vkso" "$out" \
			"$result_root"
		comparison=$result_root/vkso-optimization.csv
		summary=$result_root/VKSO-OPT-SUMMARY.md
	fi
	archive=$RESULTS_DIR/$run_id.tar.gz
	tar -C "$RESULTS_DIR" -czf "$archive" "$run_id"
	if [[ -n ${SUDO_UID:-} && -n ${SUDO_GID:-} ]]; then
		chown -R "$SUDO_UID:$SUDO_GID" "$result_root" "$archive"
	fi
	echo "vkso_result=$out"
	echo "comparison=$comparison"
	echo "summary=$summary"
	echo "archive=$archive"
fi
