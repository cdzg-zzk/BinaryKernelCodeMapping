#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m19-build}
WORK=${WORK:-/tmp/vkso-m19-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m18/run.sh"

disassembly=$(objdump -d --disassemble=__vkso_time "$BUILD/vmlinux")
if grep -Eq '[[:space:]]call[q]?[[:space:]]|[[:space:]]jmp[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "M19 time contains a call or indirect jump" >&2
	exit 1
fi

for marker in \
	"kernel_time_null=pass samples=10000" \
	"kernel_time_pointer=pass samples=10000" \
	"user_time_null=pass samples=10000" \
	"user_time_pointer=pass samples=10000"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M19 marker: $marker" >&2
		exit 1
	}
done

echo "M19 static PASS: no call/indirect jump"
echo "M19 PASS: $RESULT"
