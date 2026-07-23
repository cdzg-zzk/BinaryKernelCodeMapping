#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m17-build}
WORK=${WORK:-/tmp/vkso-m17-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m16/run.sh"

"$SCRIPT_DIR/../m04/check_cycles_disassembly.sh" "$BUILD" \
	vkso_gettimeofday_core M17

for marker in \
	"kernel_gettimeofday_timeval=pass samples=10000" \
	"user_gettimeofday_timeval=pass samples=10000"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M17 marker: $marker" >&2
		exit 1
	}
done

echo "M17 static PASS: inline TSC; only direct PV/HV cold calls allowed"
echo "M17 PASS: $RESULT"
