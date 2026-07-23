#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m11-build}
WORK=${WORK:-/tmp/vkso-m11-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m10/run.sh"

"$SCRIPT_DIR/../m04/check_cycles_disassembly.sh" "$BUILD" \
	vkso_clock_gettime_core M11

for marker in \
	"kernel_monotonic_raw=pass" \
	"user_monotonic_raw=pass" \
	"monotonic_raw_hres_namespace_offset=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M11 marker: $marker" >&2
		exit 1
	}
done

echo "M11 static PASS: inline TSC; only direct PV/HV cold calls allowed"
echo "M11 PASS: $RESULT"
