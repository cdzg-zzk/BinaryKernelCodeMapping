#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
RAW_TARBALL=${RAW_TARBALL:-/tmp/linux-5.15.198.tar.xz}
RAW_SOURCE=${RAW_SOURCE:-/tmp/vkso-final-raw-source}
BUILD_ROOT=${BUILD_ROOT:-/tmp/vkso-final-build}
NORMAL_PACKAGE=${NORMAL_PACKAGE:-$HERE/artifacts/final-normal}
NO_RETPOLINE_PACKAGE=${NO_RETPOLINE_PACKAGE:-$HERE/artifacts/final-no-retpoline}
JOBS=${JOBS:-$(nproc)}
KBUILD_BUILD_TIMESTAMP=${KBUILD_BUILD_TIMESTAMP:-$(date -u '+%Y-%m-%d %H:%M:%S UTC')}
export KBUILD_BUILD_TIMESTAMP
export KBUILD_BUILD_USER=${KBUILD_BUILD_USER:-vkso-research}
export KBUILD_BUILD_HOST=${KBUILD_BUILD_HOST:-controlled-build}

if [[ -n $(git -C "$ROOT" status --porcelain) ]]; then
	echo "refusing final build from a dirty Git worktree" >&2
	git -C "$ROOT" status --short >&2
	exit 1
fi
for output in "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"; do
	if [[ -e "$output" ]]; then
		echo "refusing to overwrite final package: $output" >&2
		exit 1
	fi
done
test -s "$RAW_TARBALL" || {
	echo "missing official Linux 5.15.198 tarball: $RAW_TARBALL" >&2
	exit 1
}
if [[ -e "$RAW_SOURCE" ]]; then
	echo "raw source path already exists; remove it before a final build: $RAW_SOURCE" >&2
	exit 1
fi
mkdir -p "$RAW_SOURCE" "$HERE/artifacts"
tar -xf "$RAW_TARBALL" -C "$RAW_SOURCE" --strip-components=1
test "$(make -s -C "$RAW_SOURCE" kernelversion)" = 5.15.198

BUILD_VARIANT=normal UPDATE_BENCH=0 \
	RAW_SOURCE="$RAW_SOURCE" RAW_TARBALL="$RAW_TARBALL" \
	BUILD_ROOT="$BUILD_ROOT/normal" OUT="$NORMAL_PACKAGE" \
	CURRENT_LINK= JOBS="$JOBS" "$HERE/build-images.sh"

BUILD_VARIANT=no-retpoline UPDATE_BENCH=0 \
	RAW_SOURCE="$RAW_SOURCE" RAW_TARBALL="$RAW_TARBALL" \
	BUILD_ROOT="$BUILD_ROOT/no-retpoline" \
	OUT="$NO_RETPOLINE_PACKAGE" CURRENT_LINK= JOBS="$JOBS" \
	"$HERE/build-images.sh"

rm -rf "$HERE/artifacts/validation"
mkdir -p "$HERE/artifacts/validation"
"$HERE/verify-packages.sh" "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE" |
	tee "$HERE/artifacts/validation/package-audit.txt"
PACKAGE="$NORMAL_PACKAGE" \
	WORK="$HERE/artifacts/validation/normal" \
	"$HERE/qemu-preflight.sh" |
	tee "$HERE/artifacts/validation/qemu-normal.txt"
PACKAGE="$NO_RETPOLINE_PACKAGE" \
	WORK="$HERE/artifacts/validation/no-retpoline" \
	"$HERE/qemu-preflight.sh" |
	tee "$HERE/artifacts/validation/qemu-no-retpoline.txt"

echo "final_build_and_qemu_validation=pass"
