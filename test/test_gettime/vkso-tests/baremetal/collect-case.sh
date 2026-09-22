#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CASE=${1:?usage: collect-case.sh CASE RUN_ID}
RUN_ID=${2:?usage: collect-case.sh CASE RUN_ID}
NORMAL_PACKAGE=${NORMAL_PACKAGE:-$HERE/artifacts/final-normal}
NO_RETPOLINE_PACKAGE=${NO_RETPOLINE_PACKAGE:-$HERE/artifacts/final-no-retpoline}
RESULTS_DIR=${RESULTS_DIR:-$HERE/results}
STATE=${STATE_FILE:-$HERE/.experiment-state}
RESULT_ROOT=$RESULTS_DIR/$RUN_ID
EXPERIMENT_MANIFEST=$RESULT_ROOT/experiment-manifest.txt

if [[ $(id -u) -ne 0 ]]; then
	exec sudo --preserve-env=NORMAL_PACKAGE,NO_RETPOLINE_PACKAGE,RESULTS_DIR,STATE_FILE \
		"$0" "$@"
fi

manifest_value()
{
	local file=$1 key=$2

	awk -F= -v key="$key" '$1 == key {
		sub(/^[^=]*=/, ""); print; exit
	}' "$file"
}

case "$CASE" in
raw-normal)
	BACKEND=raw
	VARIANT=normal
	PACKAGE=$NORMAL_PACKAGE
	IMAGE=/boot/vkso-final-raw-normal-5.15.198.bzImage
	;;
vkso-normal)
	BACKEND=vkso
	VARIANT=normal
	PACKAGE=$NORMAL_PACKAGE
	IMAGE=/boot/vkso-final-vkso-normal-5.15.198.bzImage
	;;
raw-no-retpoline)
	BACKEND=raw
	VARIANT=no-retpoline
	PACKAGE=$NO_RETPOLINE_PACKAGE
	IMAGE=/boot/vkso-final-raw-no-retpoline-5.15.198.bzImage
	;;
vkso-no-retpoline)
	BACKEND=vkso
	VARIANT=no-retpoline
	PACKAGE=$NO_RETPOLINE_PACKAGE
	IMAGE=/boot/vkso-final-vkso-no-retpoline-5.15.198.bzImage
	;;
*)
	echo "invalid experiment case: $CASE" >&2
	exit 2
	;;
esac

test -s "$EXPERIMENT_MANIFEST"
test -s "$STATE"
test "$(manifest_value "$STATE" run_id)" = "$RUN_ID"
test "$(manifest_value "$STATE" status)" = active
test "$(manifest_value "$PACKAGE/boot-manifest.txt" build_variant)" = \
	"$VARIANT"
case_order=$(manifest_value "$EXPERIMENT_MANIFEST" case_order)
if [[ " $case_order " == *" raw-no-retpoline "* ]]; then
	"$HERE/verify-packages.sh" \
		"$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE" >/dev/null
else
	(
		cd "$NORMAL_PACKAGE"
		sha256sum -c SHA256SUMS >/dev/null
	)
fi
(cd "$PACKAGE" && sha256sum -c SHA256SUMS >/dev/null)

config_sha=$(sha256sum "$HERE/experiment.conf" | awk '{print $1}')
test "$config_sha" = \
	"$(manifest_value "$EXPERIMENT_MANIFEST" experiment_config_sha256)"
CPU=$(manifest_value "$EXPERIMENT_MANIFEST" cpu)
HOUSEKEEPING_CPUS=$(manifest_value "$EXPERIMENT_MANIFEST" housekeeping_cpus)
ISOLATED_CPUS=$(manifest_value "$EXPERIMENT_MANIFEST" isolated_cpus)
ISOLATED_CPUS=${ISOLATED_CPUS:-$CPU}
MACRO_ENABLED=$(manifest_value "$EXPERIMENT_MANIFEST" macro_enabled)
ITERATIONS=$(manifest_value "$EXPERIMENT_MANIFEST" iterations)
REPEATS=$(manifest_value "$EXPERIMENT_MANIFEST" repeats)
PERF_PROCESSES=$(manifest_value "$EXPERIMENT_MANIFEST" perf_processes)
WARMUP=$(manifest_value "$EXPERIMENT_MANIFEST" warmup)
PMU=$(manifest_value "$EXPERIMENT_MANIFEST" pmu)
SEQ_ITERATIONS=$(manifest_value "$EXPERIMENT_MANIFEST" seq_iterations)

for value in "$CPU" "$ITERATIONS" "$REPEATS" "$PERF_PROCESSES" \
	"$WARMUP" "$PMU" "$SEQ_ITERATIONS"; do
	[[ "$value" =~ ^[0-9]+$ ]]
done
(( PERF_PROCESSES > 0 && PERF_PROCESSES <= REPEATS ))
# Reject old packages/configurations rather than falling back to old metrics.
test "$MACRO_ENABLED" = 0
test "$PMU" = 0
test -s "$PACKAGE/public-api/manifest.json"
test -x "$PACKAGE/public-api/raw-public-bench"
test -x "$PACKAGE/public-api/vkso-public-bench"


test "$(uname -r)" = 5.15.198 || {
	echo "expected experimental kernel 5.15.198, got $(uname -r)" >&2
	exit 1
}
command -v setarch >/dev/null
BENCHMARK_RUNNER=(setarch "$(uname -m)" -R)
probe=$("${BENCHMARK_RUNNER[@]}" "$PACKAGE/vkso-time-bench" --probe)
detected_backend=$(printf '%s\n' "$probe" |
	awk -F= '$1 == "backend" { print $2; exit }')
reader_measurement_window=$(printf '%s\n' "$probe" |
	awk -F= '$1 == "reader_measurement_window" { print $2; exit }')
test "$detected_backend" = "$BACKEND" || {
	echo "wrong kernel backend: expected $BACKEND, got $detected_backend" >&2
	exit 1
}
test "$reader_measurement_window" = direct-user-api-steady-batch-v3 || {
	echo "unsupported reader measurement window: ${reader_measurement_window:-missing}" >&2
	exit 1
}
boot_image=$(awk '{
	for (i = 1; i <= NF; ++i) {
		if ($i ~ /^BOOT_IMAGE=/) {
			sub(/^BOOT_IMAGE=/, "", $i)
			print $i
			exit
		}
	}
}' /proc/cmdline)
test "${boot_image##*/}" = "${IMAGE##*/}" || {
	echo "wrong boot image: expected ${IMAGE##*/}, got ${boot_image:-missing}" >&2
	exit 1
}
test "$(sha256sum "$IMAGE" | awk '{print $1}')" = \
	"$(sha256sum "$PACKAGE/$BACKEND-bzImage" | awk '{print $1}')" || {
	echo "installed image differs from experiment package: $IMAGE" >&2
	exit 1
}
expected_uts=$(manifest_value "$PACKAGE/boot-manifest.txt" \
	"${BACKEND}_uts_version")
test -n "$expected_uts"
test "$(uname -v)" = "$expected_uts" || {
	echo "running kernel build identity does not match the package" >&2
	echo "running: $(uname -v)" >&2
	echo "package: $expected_uts" >&2
	exit 1
}

clocksource=$(cat /sys/devices/system/clocksource/clocksource0/current_clocksource)
test "$clocksource" = tsc
for argument in nokaslr nosmt "clocksource=tsc" "tsc=reliable" \
	"isolcpus=domain,managed_irq,$ISOLATED_CPUS" "nohz_full=$ISOLATED_CPUS" \
	"rcu_nocbs=$ISOLATED_CPUS" "irqaffinity=$HOUSEKEEPING_CPUS" idle=poll \
	nmi_watchdog=0 nowatchdog audit=0; do
	grep -qw "$argument" /proc/cmdline || {
		echo "missing controlled boot argument: $argument" >&2
		exit 1
	}
done
test -d "/sys/devices/system/cpu/cpu$CPU"
test "$(cat /sys/devices/system/cpu/cpu$CPU/online 2>/dev/null || echo 1)" = 1
isolated=$(cat /sys/devices/system/cpu/isolated)
printf '%s\n' "$isolated" | awk -v cpu="$CPU" '
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
'
if [[ -r /sys/devices/system/cpu/smt/active ]]; then
	test "$(cat /sys/devices/system/cpu/smt/active)" = 0
fi

set_sysfs_value()
{
	local path=$1 expected=$2

	[[ -r "$path" ]] || return 0
	if [[ $(cat "$path") != "$expected" ]]; then
		printf '%s\n' "$expected" >"$path"
	fi
	test "$(cat "$path")" = "$expected"
}

set_sysfs_value /sys/devices/system/cpu/intel_pstate/no_turbo 1
set_sysfs_value /sys/devices/system/cpu/intel_pstate/min_perf_pct 100
set_sysfs_value /sys/devices/system/cpu/intel_pstate/max_perf_pct 100
for governor in /sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do
	[[ -e "$governor" ]] &&
		set_sysfs_value "$governor" performance
done

zcat /proc/config.gz >"$RESULT_ROOT/.running-config-$CASE.tmp"
cmp -s "$PACKAGE/$BACKEND.config" \
	"$RESULT_ROOT/.running-config-$CASE.tmp" || {
	rm -f "$RESULT_ROOT/.running-config-$CASE.tmp"
	echo "running config differs from package $BACKEND.config" >&2
	exit 1
}

FINAL=$RESULT_ROOT/$CASE
test ! -e "$FINAL" || {
	echo "case result already exists and will not be overwritten: $FINAL" >&2
	exit 1
}
PARTIAL=$RESULT_ROOT/.partial-$CASE-$(date -u +%Y%m%dT%H%M%SZ)-$$
mkdir -p "$PARTIAL"
mv "$RESULT_ROOT/.running-config-$CASE.tmp" "$PARTIAL/running.config"

module_loaded=0
clock_module_loaded=0
replaced=0
irqbalance_was_active=0
completed=0
operation_active=0

# If the shell is interrupted while a child may still use the carrier, do
# not restore/unload behind that child. Leave an explicit recovery failure.
run_guarded()
{
    local status=0
    operation_active=1
    "$@" || status=$?
    operation_active=0
    return "$status"
}

# Kept as a separate function so failure paths can be tested without root.
# A failed restore must never be followed by unloading its backing module.
release_resources()
{
    local failed=0
    if [[ "$operation_active" != 0 ]]; then
        echo "child operation may still be active; stop consumers before manual restore" >&2
        return 1
    fi
    if [[ "$replaced" == 1 ]]; then
        if run_guarded "$PACKAGE/manager" restore "$PACKAGE/libkernel.so" \
                "$PACKAGE/page_mappings.txt" >>"$PARTIAL/graft-restore.log" 2>&1; then
            replaced=0
        else
            echo "restore failed; page_cache_replace remains loaded; recover manually" >&2
            failed=1
        fi
    fi
    if [[ "$module_loaded" == 1 && "$replaced" == 0 ]]; then
        if rmmod page_cache_replace; then
            module_loaded=0
        else
            failed=1
        fi
    fi
    if [[ "$clock_module_loaded" == 1 ]]; then
        if rmmod vkso_m09_clock; then
            clock_module_loaded=0
        else
            failed=1
        fi
    fi
    if [[ "$irqbalance_was_active" == 1 ]]; then
        if systemctl start irqbalance; then
            irqbalance_was_active=0
        else
            failed=1
        fi
    fi
    return "$failed"
}

cleanup()
{
    local status=$?
    trap - EXIT INT TERM HUP
    set +e
    # Do not retry an already failed restore or hide the first failure.
    if [[ "$release_attempted" == 0 ]]; then
        release_attempted=1
        release_resources || status=1
    fi
    if [[ "$completed" != 1 && -d "$PARTIAL" ]]; then
        (( status != 0 )) || status=1
        printf 'case=%s\nstatus=incomplete\nexit_status=%s\n' "$CASE" "$status" \
            >"$PARTIAL/failure.txt"
        mkdir -p "$RESULT_ROOT/incomplete"
        incomplete=$RESULT_ROOT/incomplete/${PARTIAL##*/}
        mv "$PARTIAL" "$incomplete"
        echo "incomplete_result=$incomplete" >&2
    fi
    if [[ -n ${SUDO_UID:-} && -n ${SUDO_GID:-} ]]; then
        chown -R "$SUDO_UID:$SUDO_GID" "$RESULT_ROOT" || status=1
    fi
    exit "$status"
}
release_attempted=0
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

if command -v systemctl >/dev/null &&
	systemctl is-active --quiet irqbalance; then
	systemctl stop irqbalance
	irqbalance_was_active=1
fi

printf '%s\n' "$probe" >"$PARTIAL/backend-probe.txt"
{
	date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
	printf 'case=%s\n' "$CASE"
	printf 'backend=%s\n' "$BACKEND"
	printf 'build_variant=%s\n' "$VARIANT"
	printf 'run_id=%s\n' "$RUN_ID"
	printf 'cpu=%s\n' "$CPU"
	printf 'housekeeping_cpus=%s\n' "$HOUSEKEEPING_CPUS"
	printf 'iterations=%s\n' "$ITERATIONS"
	printf 'repeats=%s\n' "$REPEATS"
	printf 'perf_processes=%s\n' "$PERF_PROCESSES"
	printf 'warmup=%s\n' "$WARMUP"
	printf 'pmu=%s\n' "$PMU"
	printf 'seq_iterations=%s\n' "$SEQ_ITERATIONS"
	printf 'legacy_probe_measurement_window=%s\n' \
		"$reader_measurement_window"
	printf 'reader_measurement_window=public-direct-v1\n'
	printf 'user_address_layout=fixed-setarch-R\n'
	printf 'clocksource=%s\n' "$clocksource"
	printf 'isolated=%s\n' "$isolated"
	printf 'cmdline=%s\n' "$(cat /proc/cmdline)"
	printf 'package=%s\n' "$(realpath "$PACKAGE")"
	printf 'package_manifest_sha256=%s\n' \
		"$(sha256sum "$PACKAGE/boot-manifest.txt" | awk '{print $1}')"
	printf 'image_sha256=%s\n' \
		"$(sha256sum "$PACKAGE/$BACKEND-bzImage" | awk '{print $1}')"
	printf 'test_binary_sha256=%s\n' \
		"$(sha256sum "$PACKAGE/public-api/$BACKEND-public-bench" | awk '{print $1}')"
	printf 'collector_sha256=%s\n' \
		"$(sha256sum "$0" | awk '{print $1}')"
	printf 'package_collector_sha256=%s\n' \
		"$(sha256sum "$PACKAGE/collect-case.sh" | awk '{print $1}')"
	printf 'collector_git_commit=%s\n' \
		"$(git -C "$HERE/../../../.." rev-parse HEAD)"
	printf 'irqbalance_stopped=%s\n' "$irqbalance_was_active"
	printf 'uname=%s\n' "$(uname -a)"
	printf 'uname_version=%s\n' "$(uname -v)"
	printf 'compiler=%s\n' \
		"$(manifest_value "$PACKAGE/boot-manifest.txt" cc_version)"
	printf 'benchmark_cflags=%s\n' \
		"$(manifest_value "$PACKAGE/boot-manifest.txt" benchmark_cflags)"
	for file in \
		/sys/devices/system/cpu/intel_pstate/no_turbo \
		/sys/devices/system/cpu/intel_pstate/min_perf_pct \
		/sys/devices/system/cpu/intel_pstate/max_perf_pct \
		/sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do
		[[ -r "$file" ]] && printf '%s=%s\n' "$file" "$(cat "$file")"
	done
	printf '%s\n' '--- lscpu ---'
	lscpu
	printf '%s\n' '--- clocksource_available ---'
	cat /sys/devices/system/clocksource/clocksource0/available_clocksource
	printf '%s\n' '--- default_irq_affinity ---'
	cat /proc/irq/default_smp_affinity
	printf '%s\n' '--- processes ---'
	ps -eLo pid,tid,psr,cls,rtprio,pri,ni,comm,args
} >"$PARTIAL/environment.txt"
cat /proc/interrupts >"$PARTIAL/interrupts-before.txt"
dmesg >"$PARTIAL/dmesg-before.txt"

if grep -q '^vkso_m09_clock ' /proc/modules; then
	echo "vkso_m09_clock is already loaded" >&2
	exit 1
fi
insmod "$PACKAGE/vkso_m09_clock.ko"
clock_module_loaded=1
for _ in $(seq 1 50); do
	[[ -c /dev/vkso-m09-clock ]] && break
	sleep 0.1
done
test -c /dev/vkso-m09-clock || {
	echo "vkso_m09_clock did not create /dev/vkso-m09-clock" >&2
	exit 1
}

if [[ "$BACKEND" == vkso ]]; then
	if grep -q '^page_cache_replace ' /proc/modules; then
		echo "page_cache_replace is already loaded" >&2
		exit 1
	fi
	insmod "$PACKAGE/page_cache_replace.ko"
	module_loaded=1
	run_guarded "$PACKAGE/manager" validate "$PACKAGE/libkernel.so" \
		"$PACKAGE/page_mappings.txt" >"$PARTIAL/graft-validate.log" 2>&1
	# Mark the attempt before execution: a failing replace can be partial.
	replaced=1
	run_guarded "$PACKAGE/manager" replace "$PACKAGE/libkernel.so" \
		"$PACKAGE/page_mappings.txt" >"$PARTIAL/graft-replace.log" 2>&1
	VKSO_TEST_DYNAMIC_CLOCK=/dev/vkso-m09-clock \
		LD_LIBRARY_PATH="$PACKAGE" run_guarded "$PACKAGE/vkso-abi-matrix" \
		>"$PARTIAL/functional.log" 2>&1
else
	VKSO_TEST_DYNAMIC_CLOCK=/dev/vkso-m09-clock \
		LD_LIBRARY_PATH="$PACKAGE" run_guarded "$PACKAGE/raw-abi-matrix" \
		>"$PARTIAL/functional.log" 2>&1
fi
grep -Fq 'abi_matrix_status=pass' "$PARTIAL/functional.log"
tr -d '\r' <"$PARTIAL/functional.log" |
	grep -E '^(semantics|path|namespace)\.' \
	>"$PARTIAL/functional.matrix"

# Protocol v5: two public paths only. The old probe and ABI matrix remain
# validation tools; their v3 measurements are not relabelled as native libc.
run_guarded python3 "$PACKAGE/public-api/collect.py" \
    --package "$PACKAGE" --output "$PARTIAL/public" \
    --backend "$BACKEND" --case "$CASE" --run-id "$RUN_ID" \
    --cpu "$CPU" --iterations "$ITERATIONS" --repeats "$REPEATS" \
    --processes "$PERF_PROCESSES" --warmup "$WARMUP"

cat /proc/interrupts >"$PARTIAL/interrupts-after.txt"
dmesg >"$PARTIAL/dmesg-after.txt"
release_attempted=1
release_resources || exit 1
printf 'case=%s\nstatus=complete\n' "$CASE" >"$PARTIAL/complete"
sync

mv "$PARTIAL" "$FINAL"
completed=1
echo "case_result=$FINAL"
