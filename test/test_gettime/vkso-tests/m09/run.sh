#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m09-build}
WORK=${WORK:-/tmp/vkso-m09-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m04/run.sh"

disassembly=$(objdump -d --disassemble=__vkso_clock_gettime \
	"$BUILD/vmlinux")
grep -Eq '[[:space:]]rdtsc(p)?[[:space:]]*$' <<<"$disassembly" || {
	echo "M09 TSC instruction missing from CLOCK_REALTIME path" >&2
	exit 1
}
if grep -Eq '[[:space:]]call[q]?[[:space:]]|[[:space:]]jmp[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "M09 CLOCK_REALTIME path contains a call or indirect jump" >&2
	exit 1
fi

for marker in \
	"kernel_realtime=pass" \
	"user_realtime=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M09 marker: $marker" >&2
		exit 1
	}
done

echo "M09 static PASS: inline TSC, no call/indirect jump"
echo "M09 PASS: $RESULT"
