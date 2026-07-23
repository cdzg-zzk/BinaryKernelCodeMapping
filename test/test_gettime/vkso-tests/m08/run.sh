#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m08-build}
WORK=${WORK:-/tmp/vkso-m08-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m04/run.sh"

"$SCRIPT_DIR/../m04/check_cycles_disassembly.sh" "$BUILD" \
	__vkso_test_hres_cycle_probe_at M08

for marker in \
	"tsc_cycles_shim=pass" \
	"seq_retry_concurrency=pass"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M08 marker: $marker" >&2
		exit 1
	}
done

echo "M08 static PASS: inline TSC; only direct PV/HV cold calls allowed"
echo "M08 PASS: $RESULT"
