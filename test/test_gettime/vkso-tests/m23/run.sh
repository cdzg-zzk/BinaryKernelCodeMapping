#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m23-build}
WORK=${WORK:-/tmp/vkso-m23-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m22/run.sh"

if nm "$BUILD/vmlinux" | grep -Fq " vkso_time_get_context"; then
	echo "M23 retained the redundant syscall context helper" >&2
	exit 1
fi
grep -Fq "root_namespace_null_context=pass" "$RESULT" || {
	echo "missing M23 explicit root-context marker" >&2
	exit 1
}

echo "M23 static PASS: explicit syscall MM_data dependency"
echo "M23 PASS: $RESULT"
