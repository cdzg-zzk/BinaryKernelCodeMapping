#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m26-build}

BUILD="$BUILD" "$SCRIPT_DIR/../m25/run.sh"

grep -Fqx 'CONFIG_HYPERV_TIMER=y' "$BUILD/.config"

cold=$(objdump -d --disassemble=vkso_read_hvclock_cycles "$BUILD/vmlinux")
clock_gettime=$(objdump -d --disassemble=vkso_clock_gettime_core \
	"$BUILD/vmlinux")
provider=$(objdump -d --disassemble=hv_init_clocksource \
	"$BUILD/vmlinux")

grep -Eq '[[:space:]]rdtsc(p)?[[:space:]]*$' <<<"$cold"
grep -Eq '[[:space:]]mul[q]?[[:space:]]' <<<"$cold"
if grep -Eq '[[:space:]](call|jmp)[q]?[[:space:]]+\*|[[:space:]]call[q]?[[:space:]]' \
	<<<"$cold"; then
	echo "M26 Hyper-V cold path contains a call/indirect branch" >&2
	exit 1
fi
grep -Fq '<vkso_read_hvclock_cycles>' <<<"$clock_gettime"
grep -Fq '<vkso_time_set_hvclock_page>' <<<"$provider"

echo "M26 static PASS: Hyper-V TSC page registered; cold reader is self-contained"
