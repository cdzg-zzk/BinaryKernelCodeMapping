#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m16-build}
WORK=${WORK:-/tmp/vkso-m16-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m15/run.sh"

for marker in \
	"kernel_clock_getres_coarse=pass clocks=2" \
	"kernel_clock_getres_null=pass" \
	"kernel_clock_getres_fallback=pass" \
	"kernel_clock_getres_invalid=pass errno=EINVAL" \
	"user_clock_getres_coarse=pass clocks=2" \
	"user_clock_getres_null=pass" \
	"user_clock_getres_fallback=pass" \
	"user_clock_getres_invalid=pass errno=EINVAL"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M16 marker: $marker" >&2
		exit 1
	}
done

echo "M16 PASS: $RESULT"
