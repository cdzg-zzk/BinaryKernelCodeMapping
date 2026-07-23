#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m12-build}
WORK=${WORK:-/tmp/vkso-m12-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m11/run.sh"

"$SCRIPT_DIR/../m04/check_cycles_disassembly.sh" "$BUILD" \
	vkso_clock_gettime_core M12

for marker in \
	"kernel_boottime=pass" \
	"user_boottime=pass" \
	"boottime_namespace_offset=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M12 marker: $marker" >&2
		exit 1
	}
done

echo "M12 static PASS: inline TSC; only direct PV/HV cold calls allowed"
echo "M12 PASS: $RESULT"
