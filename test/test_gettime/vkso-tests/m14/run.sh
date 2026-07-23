#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m14-build}
WORK=${WORK:-/tmp/vkso-m14-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m13/run.sh"

for marker in \
	"kernel_process_cputime_fallback=pass" \
	"kernel_thread_cputime_fallback=pass" \
	"kernel_realtime_alarm_fallback=pass" \
	"kernel_boottime_alarm_fallback=pass" \
	"kernel_invalid_clock_fallback=pass errno=EINVAL" \
	"user_process_cputime_fallback=pass" \
	"user_thread_cputime_fallback=pass" \
	"user_realtime_alarm_fallback=pass" \
	"user_boottime_alarm_fallback=pass" \
	"user_invalid_clock_fallback=pass errno=EINVAL"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M14 marker: $marker" >&2
		exit 1
	}
done

echo "M14 PASS: $RESULT"
