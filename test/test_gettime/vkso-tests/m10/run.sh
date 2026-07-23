#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m10-build}
WORK=${WORK:-/tmp/vkso-m10-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m09/run.sh"

disassembly=$(objdump -d --disassemble=__vkso_clock_gettime \
	"$BUILD/vmlinux")
grep -Eq '[[:space:]]rdtsc(p)?[[:space:]]*$' <<<"$disassembly" || {
	echo "M10 TSC instruction missing from CLOCK_MONOTONIC path" >&2
	exit 1
}
if grep -Eq '[[:space:]]call[q]?[[:space:]]|[[:space:]]jmp[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "M10 CLOCK_MONOTONIC path contains a call or indirect jump" >&2
	exit 1
fi

for marker in \
	"kernel_monotonic=pass" \
	"user_monotonic=pass" \
	"monotonic_hres_namespace_offset=pass" \
	"unsupported_clock_fallback=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M10 marker: $marker" >&2
		exit 1
	}
done

echo "M10 static PASS: inline TSC, no call/indirect jump"
echo "M10 PASS: $RESULT"
