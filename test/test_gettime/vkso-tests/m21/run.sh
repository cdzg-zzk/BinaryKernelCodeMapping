#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m21-build}
WORK=${WORK:-/tmp/vkso-m21-run}
RESULT="$WORK/qemu.log"

BUILD="$BUILD" WORK="$WORK" "$SCRIPT_DIR/../m20/run.sh"

grep -Fq "root_namespace_null_context=pass" "$RESULT" || {
	echo "missing M21 root-namespace fast-path marker" >&2
	exit 1
}

echo "M21 PASS: one-time ABI validation and root namespace NULL context"
echo "M21 PASS: $RESULT"
