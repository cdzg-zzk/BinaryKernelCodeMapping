#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m08-build}
WORK=${WORK:-/tmp/vkso-m08-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m04/run.sh"

disassembly=$(objdump -d --disassemble=__vkso_test_hres_cycle_probe_at \
	"$BUILD/vmlinux")
grep -Eq '[[:space:]]rdtsc(p)?[[:space:]]*$' <<<"$disassembly" || {
	echo "M08 TSC instruction missing from common core" >&2
	exit 1
}
if grep -Eq '[[:space:]]call[q]?[[:space:]]|[[:space:]]jmp[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "M08 cycles path contains a call or indirect jump" >&2
	exit 1
fi

for marker in \
	"tsc_cycles_shim=pass" \
	"seq_retry_concurrency=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M08 marker: $marker" >&2
		exit 1
	}
done

echo "M08 static PASS: inline TSC, no call/indirect jump"
echo "M08 PASS: $RESULT"
