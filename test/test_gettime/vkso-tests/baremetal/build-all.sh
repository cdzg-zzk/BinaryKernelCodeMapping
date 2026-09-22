#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
RAW_TARBALL=${RAW_TARBALL:-/tmp/linux-5.15.198.tar.xz}
RAW_SOURCE=${RAW_SOURCE:-/tmp/vkso-final-raw-source}
BUILD_ROOT=${BUILD_ROOT:-/tmp/vkso-final-build}
NORMAL_PACKAGE=${NORMAL_PACKAGE:-$HERE/artifacts/direct-normal}
NO_RETPOLINE_PACKAGE=${NO_RETPOLINE_PACKAGE:-$HERE/artifacts/direct-no-retpoline}
JOBS=${JOBS:-$(nproc)}
KBUILD_BUILD_TIMESTAMP=${KBUILD_BUILD_TIMESTAMP:-$(date -u '+%Y-%m-%d %H:%M:%S UTC')}
export KBUILD_BUILD_TIMESTAMP
export KBUILD_BUILD_USER=${KBUILD_BUILD_USER:-vkso-research}
export KBUILD_BUILD_HOST=${KBUILD_BUILD_HOST:-controlled-build}

mkdir -p "$BUILD_ROOT"
exec 9>"$BUILD_ROOT/.build.lock"
flock -n 9 || { echo "another build is using $BUILD_ROOT" >&2; exit 1; }
build_log=$BUILD_ROOT/build-$(date -u +%Y%m%dT%H%M%SZ)-$$.log
exec > >(tee "$build_log") 2>&1
echo "build_log=$build_log"
trap 'echo "build_failed: line=$LINENO log=$build_log (installation must not follow)" >&2' ERR

# build-images.sh archives the tracked candidate patch and complete kernel
# source identity. A research candidate need not be committed to be packaged.
for output in "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"; do
	if [[ -e "$output" ]]; then
		if [[ -s "$output/SHA256SUMS" && -s "$output/boot-manifest.txt" ]]; then
			echo "refusing to overwrite completed package: $output; use install-grub.sh for this build" >&2
			exit 1
		fi
		failed=$output.incomplete-$(date -u +%Y%m%dT%H%M%SZ)-$$
		mv "$output" "$failed"
		echo "preserved_incomplete_package=$failed"
	fi
done
normal_final=$NORMAL_PACKAGE
no_retpoline_final=$NO_RETPOLINE_PACKAGE
NORMAL_PACKAGE=$normal_final.building-$$
NO_RETPOLINE_PACKAGE=$no_retpoline_final.building-$$
# Rebuild all four images. Legacy packages are not a source/provenance substitute.
test -s "$RAW_TARBALL" || {
    echo "missing Linux 5.15.198 source archive: $RAW_TARBALL; set RAW_TARBALL" >&2
    exit 1
}
if [[ -e "$RAW_SOURCE" ]]; then
    RAW_SOURCE=$(mktemp -d "$BUILD_ROOT/raw-source.XXXXXX")
fi
mkdir -p "$RAW_SOURCE"
tar -xf "$RAW_TARBALL" -C "$RAW_SOURCE" --strip-components=1
test "$(make -s -C "$RAW_SOURCE" kernelversion)" = 5.15.198

BUILD_VARIANT=normal UPDATE_BENCH=0 \
	RAW_PACKAGE= \
	RAW_SOURCE="$RAW_SOURCE" RAW_TARBALL="$RAW_TARBALL" \
	BUILD_ROOT="$BUILD_ROOT/normal" OUT="$NORMAL_PACKAGE" \
	CURRENT_LINK= JOBS="$JOBS" "$HERE/build-images.sh"

BUILD_VARIANT=no-retpoline UPDATE_BENCH=0 \
	RAW_PACKAGE= \
	RAW_SOURCE="$RAW_SOURCE" RAW_TARBALL="$RAW_TARBALL" \
	BUILD_ROOT="$BUILD_ROOT/no-retpoline" \
	OUT="$NO_RETPOLINE_PACKAGE" CURRENT_LINK= JOBS="$JOBS" \
	"$HERE/build-images.sh"

for package in "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"; do
    python3 "$HERE/../direct-api/bundle.py" --package "$package" \
        --out "$package/direct" --cc "${CC:-gcc}"
    # The outer inventory also covers every direct API file, including build.json.
    (cd "$package" && python3 - <<'INVENTORY'
from pathlib import Path
import hashlib
with open('SHA256SUMS', 'a') as f:
    for p in sorted(Path('direct').rglob('*')):
        if p.is_file() and not p.is_symlink():
            f.write(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + str(p) + '\n')
INVENTORY
    )
done

"$HERE/verify-packages.sh" "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE" |
	tee "$BUILD_ROOT/package-audit.txt"

mv "$NORMAL_PACKAGE" "$normal_final"
mv "$NO_RETPOLINE_PACKAGE" "$no_retpoline_final"
echo "four_image_build_and_package_validation=pass"
echo "runtime_tests=not_run; use experiment.sh boot/collect CASE"
