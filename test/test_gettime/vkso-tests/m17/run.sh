#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m17-build}
WORK=${WORK:-/tmp/vkso-m17-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m16/run.sh"

disassembly=$(objdump -d --disassemble=__vkso_gettimeofday \
	"$BUILD/vmlinux")
if grep -Eq '[[:space:]]call[q]?[[:space:]]|[[:space:]]jmp[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "M17 gettimeofday contains a call or indirect jump" >&2
	exit 1
fi

for marker in \
	"kernel_gettimeofday_timeval=pass samples=10000" \
	"user_gettimeofday_timeval=pass samples=10000"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M17 marker: $marker" >&2
		exit 1
	}
done

echo "M17 static PASS: no call/indirect jump"
echo "M17 PASS: $RESULT"
