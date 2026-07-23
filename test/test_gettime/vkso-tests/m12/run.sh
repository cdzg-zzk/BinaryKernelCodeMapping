#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m12-build}
WORK=${WORK:-/tmp/vkso-m12-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m11/run.sh"

disassembly=$(objdump -d --disassemble=__vkso_clock_gettime \
	"$BUILD/vmlinux")
grep -Eq '[[:space:]]rdtsc(p)?[[:space:]]*$' <<<"$disassembly" || {
	echo "M12 TSC instruction missing from CLOCK_BOOTTIME path" >&2
	exit 1
}
if grep -Eq '[[:space:]]call[q]?[[:space:]]|[[:space:]]jmp[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "M12 CLOCK_BOOTTIME path contains a call or indirect jump" >&2
	exit 1
fi

for marker in \
	"kernel_boottime=pass" \
	"user_boottime=pass" \
	"boottime_namespace_offset=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M12 marker: $marker" >&2
		exit 1
	}
done

echo "M12 static PASS: inline TSC, no call/indirect jump"
echo "M12 PASS: $RESULT"
