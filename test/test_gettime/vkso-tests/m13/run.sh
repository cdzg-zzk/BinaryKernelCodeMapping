#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m13-build}
WORK=${WORK:-/tmp/vkso-m13-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m12/run.sh"

"$SCRIPT_DIR/../m04/check_cycles_disassembly.sh" "$BUILD" \
	vkso_clock_gettime_core M13

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

echo "M13 static PASS: inline TSC; only direct PV/HV cold calls allowed"
echo "M13 PASS: $RESULT"
