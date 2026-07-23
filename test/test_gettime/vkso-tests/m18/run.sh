#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m18-build}
WORK=${WORK:-/tmp/vkso-m18-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m17/run.sh"

for marker in \
	"kernel_gettimeofday_timezone=pass" \
	"kernel_gettimeofday_null_combinations=pass combinations=4" \
	"user_gettimeofday_timezone=pass" \
	"user_gettimeofday_timezone_update=pass" \
	"user_gettimeofday_null_combinations=pass combinations=4"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M18 marker: $marker" >&2
		exit 1
	}
done

echo "M18 PASS: $RESULT"
