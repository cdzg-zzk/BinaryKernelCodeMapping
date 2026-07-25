#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m26-build}

BUILD="$BUILD" "$SCRIPT_DIR/../m25/run.sh"

grep -Fqx 'CONFIG_HYPERV_TIMER=y' "$BUILD/.config"

cold=$(objdump -d --disassemble=vkso_read_cycles_cold "$BUILD/vmlinux")
clock_readers=$(
	for symbol in vkso_clock_gettime_realtime \
		vkso_clock_gettime_monotonic vkso_clock_gettime_other; do
		objdump -d --disassemble="$symbol" "$BUILD/vmlinux"
	done
)
provider=$(objdump -d --disassemble=hv_init_clocksource \
	"$BUILD/vmlinux")

grep -Eq '[[:space:]]rdtsc(p)?[[:space:]]*$' <<<"$cold"
grep -Eq '[[:space:]]mul[q]?[[:space:]]' <<<"$cold"
if grep -Eq '[[:space:]](call|jmp)[q]?[[:space:]]+\*|[[:space:]]call[q]?[[:space:]]' \
	<<<"$cold"; then
	echo "M26 Hyper-V cold path contains a call/indirect branch" >&2
	exit 1
fi
grep -Fq '<vkso_read_cycles_cold>' <<<"$clock_readers"
grep -Fq '<vkso_time_set_hvclock_page>' <<<"$provider"

echo "M26 static PASS: Hyper-V TSC page registered; unified cold reader is self-contained"
