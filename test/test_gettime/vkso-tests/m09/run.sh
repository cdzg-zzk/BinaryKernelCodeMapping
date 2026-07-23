#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m09-build}
WORK=${WORK:-/tmp/vkso-m09-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m04/run.sh"

"$SCRIPT_DIR/../m04/check_cycles_disassembly.sh" "$BUILD" \
	vkso_clock_gettime_core M09

for marker in \
	"kernel_realtime=pass" \
	"user_realtime=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M09 marker: $marker" >&2
		exit 1
	}
done

echo "M09 static PASS: inline TSC; only direct PV/HV cold calls allowed"
echo "M09 PASS: $RESULT"
