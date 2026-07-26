#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
RAW_SOURCE=${RAW_SOURCE:-/tmp/vkso-raw-update-src}
BUILD_ROOT=${BUILD_ROOT:-/tmp/vkso-update-baremetal-build}

exec env UPDATE_BENCH=1 BUILD_VARIANT=normal \
	RAW_SOURCE="$RAW_SOURCE" BUILD_ROOT="$BUILD_ROOT" \
	CURRENT_LINK=current-update \
	"$HERE/../baremetal/build-images.sh" "$@"
