#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m13-build}
WORK=${WORK:-/tmp/vkso-m13-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m12/run.sh"

disassembly=$(objdump -d --disassemble=__vkso_clock_gettime \
	"$BUILD/vmlinux")
grep -Eq '[[:space:]]rdtsc(p)?[[:space:]]*$' <<<"$disassembly" || {
	echo "M13 TSC instruction missing from CLOCK_TAI path" >&2
	exit 1
}
if grep -Eq '[[:space:]]call[q]?[[:space:]]|[[:space:]]jmp[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "M13 CLOCK_TAI path contains a call or indirect jump" >&2
	exit 1
fi

for marker in \
	"kernel_tai=pass" \
	"user_tai=pass" \
	"tai_offset=pass seconds=37" \
	"tai_namespace_independent=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M13 marker: $marker" >&2
		exit 1
	}
done

echo "M13 static PASS: inline TSC, no call/indirect jump"
echo "M13 PASS: $RESULT"
