#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m22-build}
WORK=${WORK:-/tmp/vkso-m22-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m21/run.sh"

assert_call_order()
{
	local symbol=$1
	local fast_target=$2
	local disassembly fast_line fallback_line

	disassembly=$(objdump -d --disassemble="$symbol" "$BUILD/vmlinux")
	fast_line=$(awk -v target="<$fast_target>" \
		'index($0, target) { print NR; exit }' <<<"$disassembly")
	fallback_line=$(awk \
		'index($0, "<clockid_to_kclock>") { print NR; exit }' \
		<<<"$disassembly")
	if [[ -z "$fast_line" || -z "$fallback_line" ||
	      "$fast_line" -ge "$fallback_line" ]]; then
		echo "M22 $symbol does not enter VKSO before k_clock fallback" >&2
		exit 1
	fi
}

assert_call_order __x64_sys_clock_gettime vkso_time_get_context
assert_call_order __x64_sys_clock_getres __vkso_clock_getres

for symbol in \
	posix_get_realtime_timespec \
	posix_get_monotonic_timespec \
	posix_get_monotonic_raw \
	posix_get_realtime_coarse \
	posix_get_monotonic_coarse \
	posix_get_coarse_res \
	posix_get_boottime_timespec \
	posix_get_tai_timespec \
	posix_get_hrtimer_res; do
	disassembly=$(objdump -d --disassemble="$symbol" "$BUILD/vmlinux")
	if grep -Eq '<(__)?vkso_time_|<__vkso_' <<<"$disassembly"; then
		echo "M22 unrelated reader $symbol still enters VKSO" >&2
		exit 1
	fi
done

echo "M22 static PASS: syscall-first VKSO path and isolated legacy readers"
echo "M22 PASS: $RESULT"
