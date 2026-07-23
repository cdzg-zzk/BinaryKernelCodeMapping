#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m10-build}
WORK=${WORK:-/tmp/vkso-m10-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m09/run.sh"

"$SCRIPT_DIR/../m04/check_cycles_disassembly.sh" "$BUILD" \
	vkso_clock_gettime_core M10

for marker in \
	"kernel_monotonic=pass" \
	"user_monotonic=pass" \
	"monotonic_hres_namespace_offset=pass" \
	"unsupported_clock_fallback=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M10 marker: $marker" >&2
		exit 1
	}
done

echo "M10 static PASS: inline TSC; only direct PV/HV cold calls allowed"
echo "M10 PASS: $RESULT"
