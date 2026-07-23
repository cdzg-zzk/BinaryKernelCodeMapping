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

if [[ $(id -u) -ne 0 ]]; then
	exec sudo --preserve-env=PACKAGE,CONTROL_DIR,RESULTS_DIR,STATE_FILE,CPU,ITERATIONS,REPEATS,WARMUP,PMU,SEQ_ITERATIONS,LAYOUT_ITERATIONS \
		"$0" "$@"
fi

for file in SHA256SUMS boot-manifest.txt vkso-time-bench \
	raw-abi-matrix vkso-abi-matrix libkernel.so page_mappings.txt \
	page_cache_replace.ko manager compare.py raw.config vkso.config; do
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

if [[ "$backend" == raw ]]; then
	run_id=${1:-$(date -u +%Y%m%dT%H%M%SZ)-baremetal}
	printf '%s\n' "$run_id" >"$STATE"
else
	if [[ $# -gt 0 ]]; then
		run_id=$1
	elif [[ -r "$STATE" ]]; then
		run_id=$(cat "$STATE")
	else
		echo "no raw run id; pass the same run id explicitly" >&2
		exit 1
	fi
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

if [[ -w /sys/devices/system/cpu/intel_pstate/no_turbo ]]; then
	echo 1 >/sys/devices/system/cpu/intel_pstate/no_turbo
fi
if [[ -w /sys/devices/system/cpu/intel_pstate/min_perf_pct ]]; then
	echo 100 >/sys/devices/system/cpu/intel_pstate/min_perf_pct
fi
if [[ -w /sys/devices/system/cpu/intel_pstate/max_perf_pct ]]; then
	echo 100 >/sys/devices/system/cpu/intel_pstate/max_perf_pct
fi
for governor in /sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do
	[[ -e "$governor" ]] && echo performance >"$governor"
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
	printf 'clocksource=%s\n' "$clocksource"
	printf 'smt_active=%s\n' "$smt_active"
	printf 'isolated=%s\n' "$isolated"
	printf 'kernel_cmdline_common=%s\n' "$kernel_cmdline_common"
	printf 'package=%s\n' "$PACKAGE"
	printf 'package_manifest_sha256=%s\n' \
		"$(sha256sum "$PACKAGE/boot-manifest.txt" | awk '{print $1}')"
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
LD_LIBRARY_PATH="$PACKAGE" "$PACKAGE/vkso-time-bench" \
	--backend "$backend" --mode seq --cpu "$CPU" \
	--seq-iterations "$SEQ_ITERATIONS" >"$out/seq.csv"
if [[ "$backend" == vkso ]]; then
	LD_LIBRARY_PATH="$PACKAGE" "$PACKAGE/vkso-time-bench" \
		--backend "$backend" --mode layout --cpu "$CPU" \
		--layout-iterations "$LAYOUT_ITERATIONS" \
		--repeats "$REPEATS" >"$out/layout.csv"
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
	"$PACKAGE/compare.py" "$result_root"
	archive=$RESULTS_DIR/$run_id.tar.gz
	tar -C "$RESULTS_DIR" -czf "$archive" "$run_id"
	if [[ -n ${SUDO_UID:-} && -n ${SUDO_GID:-} ]]; then
		chown -R "$SUDO_UID:$SUDO_GID" "$result_root" "$archive"
	fi
	echo "vkso_result=$out"
	echo "comparison=$result_root/research-questions.csv"
	echo "summary=$result_root/SUMMARY.md"
	echo "archive=$archive"
fi
