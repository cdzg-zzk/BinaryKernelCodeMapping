#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m20-build}
WORK=${WORK:-/tmp/vkso-m20-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m19/run.sh"

publisher=$(objdump -d --disassemble=vkso_time_publish "$BUILD/vmlinux")
time_reader=$(objdump -d --disassemble=__vkso_time "$BUILD/vmlinux")

if ! grep -Eq 'mov[[:space:]].*<vkso_shared_page\+0x20>' \
	<<<"$publisher"; then
	echo "M20 publisher lacks an aligned 64-bit realtime seconds store" >&2
	exit 1
fi
if ! grep -Eq 'mov[[:space:]]+0x20\(%rax\),%rax' <<<"$time_reader"; then
	echo "M20 time reader does not load the atomic realtime seconds field" >&2
	exit 1
fi
grep -Fq "shared_hot_cacheline=pass bytes=64" "$RESULT" || {
	echo "missing M20 hot-layout marker" >&2
	exit 1
}

echo "M20 static PASS: atomic time publish and one-cacheline hot layout"
echo "M20 PASS: $RESULT"
