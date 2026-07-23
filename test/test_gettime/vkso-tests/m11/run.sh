#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m11-build}
WORK=${WORK:-/tmp/vkso-m11-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m10/run.sh"

disassembly=$(objdump -d --disassemble=__vkso_clock_gettime \
	"$BUILD/vmlinux")
grep -Eq '[[:space:]]rdtsc(p)?[[:space:]]*$' <<<"$disassembly" || {
	echo "M11 TSC instruction missing from CLOCK_MONOTONIC_RAW path" >&2
	exit 1
}
if grep -Eq '[[:space:]]call[q]?[[:space:]]|[[:space:]]jmp[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "M11 CLOCK_MONOTONIC_RAW path contains a call or indirect jump" >&2
	exit 1
fi

for marker in \
	"kernel_monotonic_raw=pass" \
	"user_monotonic_raw=pass" \
	"monotonic_raw_hres_namespace_offset=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M11 marker: $marker" >&2
		exit 1
	}
done

echo "M11 static PASS: inline TSC, no call/indirect jump"
echo "M11 PASS: $RESULT"
