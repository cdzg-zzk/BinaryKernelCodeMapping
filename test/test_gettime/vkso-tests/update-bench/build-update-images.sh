#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BUILD_VARIANT=${BUILD_VARIANT:-normal}
RAW_SOURCE=${RAW_SOURCE:-/tmp/vkso-raw-update-source}
BUILD_ROOT=${BUILD_ROOT:-/tmp/vkso-update-$BUILD_VARIANT-build}

case "$BUILD_VARIANT" in
normal|no-retpoline)
	;;
*)
	echo "BUILD_VARIANT must be normal or no-retpoline" >&2
	exit 2
	;;
esac

exec env UPDATE_BENCH=1 BUILD_VARIANT="$BUILD_VARIANT" \
	RAW_SOURCE="$RAW_SOURCE" BUILD_ROOT="$BUILD_ROOT" \
	CURRENT_LINK="current-update-$BUILD_VARIANT" \
	"$HERE/../baremetal/build-images.sh" "$@"
