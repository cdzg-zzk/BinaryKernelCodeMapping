#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m06-build}
WORK=${WORK:-/tmp/vkso-m06-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m04/run.sh"

for marker in \
	"kernel_monotonic_coarse=pass" \
	"user_monotonic_coarse=pass" \
	"monotonic_namespace_offset=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M06 marker: $marker" >&2
		exit 1
	}
done

echo "M06 PASS: $RESULT"
