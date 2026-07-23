#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m07-build}
WORK=${WORK:-/tmp/vkso-m07-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m04/run.sh"

grep -Fq "hres_snapshot=pass" "$RESULT" || {
	echo "missing M07 marker: hres_snapshot=pass" >&2
	exit 1
}

echo "M07 PASS: $RESULT"
