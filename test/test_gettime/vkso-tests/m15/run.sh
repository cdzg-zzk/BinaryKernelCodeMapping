#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m15-build}
WORK=${WORK:-/tmp/vkso-m15-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m14/run.sh"

disassembly=$(objdump -d --disassemble=__vkso_clock_getres \
	"$BUILD/vmlinux")
if grep -Eq '[[:space:]]call[q]?[[:space:]]|[[:space:]]jmp[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "M15 clock_getres contains a call or indirect jump" >&2
	exit 1
fi

for marker in \
	"kernel_clock_getres_hres=pass clocks=5" \
	"user_clock_getres_hres=pass clocks=5"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M15 marker: $marker" >&2
		exit 1
	}
done

echo "M15 static PASS: no call/indirect jump"
echo "M15 PASS: $RESULT"
