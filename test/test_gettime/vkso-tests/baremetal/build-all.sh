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
raw_normal=
raw_no_retpoline=
if [[ -s "$RAW_TARBALL" ]]; then
	if [[ -e "$RAW_SOURCE" ]]; then
		RAW_SOURCE=$(mktemp -d "$BUILD_ROOT/raw-source.XXXXXX")
	fi
	mkdir -p "$RAW_SOURCE"
	tar -xf "$RAW_TARBALL" -C "$RAW_SOURCE" --strip-components=1
	test "$(make -s -C "$RAW_SOURCE" kernelversion)" = 5.15.198
else
	# Reuse only the unchanged, verified native baselines. Both VKSO images
	# are rebuilt from the current implementation, including namespace sharing.
	raw_normal=$HERE/artifacts/reader-load-v4-normal
	raw_no_retpoline=$HERE/artifacts/reader-load-v4-no-retpoline
	"$HERE/verify-packages.sh" "$raw_normal" "$raw_no_retpoline"
	echo "raw_baseline=reused archived Linux 5.15.198 Normal/no-retpoline images"
fi

# Build the application tools once so both mitigation variants use identical
# executables. This step compiles; it does not launch Redis or a benchmark.
source "$HERE/experiment.conf"
macro_source=$ROOT/test/test_gettime/macro-benchmark
macro_build=$BUILD_ROOT/macro
if [[ ${MACRO_ENABLED:-0} == 1 ]]; then
	mkdir -p "$macro_build/source"
	tar -xzf "$macro_source/vendor/redis-7.2.4.tar.gz" \
		-C "$macro_build/source" --strip-components=1
	make -C "$macro_build/source" -j"$JOBS" \
		>"$macro_build/build.log" 2>&1
	for binary in redis-server redis-cli redis-benchmark; do
		cp "$macro_build/source/src/$binary" "$macro_build/$binary"
	done
	${CC:-gcc} -O2 -Wall -Wextra -Werror -fPIC -shared \
		-I"$ROOT/test/test_gettime/vkso-tests/functional" \
		"$macro_source/adapter.c" -ldl -o "$macro_build/adapter.so"
	cp "$macro_source/redis_workload.py" "$macro_build/"
	cp "$macro_source/adapter.c" "$macro_build/"
	cp "$macro_source/vendor/REDIS-COPYING" "$macro_build/"
fi

BUILD_VARIANT=normal UPDATE_BENCH=0 \
	RAW_PACKAGE="$raw_normal" \
	RAW_SOURCE="$RAW_SOURCE" RAW_TARBALL="$RAW_TARBALL" \
	BUILD_ROOT="$BUILD_ROOT/normal" OUT="$NORMAL_PACKAGE" \
	CURRENT_LINK= JOBS="$JOBS" "$HERE/build-images.sh"

BUILD_VARIANT=no-retpoline UPDATE_BENCH=0 \
	RAW_PACKAGE="$raw_no_retpoline" \
	RAW_SOURCE="$RAW_SOURCE" RAW_TARBALL="$RAW_TARBALL" \
	BUILD_ROOT="$BUILD_ROOT/no-retpoline" \
	OUT="$NO_RETPOLINE_PACKAGE" CURRENT_LINK= JOBS="$JOBS" \
	"$HERE/build-images.sh"

if [[ ${MACRO_ENABLED:-0} == 1 ]]; then
	for package in "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"; do
		mkdir "$package/macro"
		for file in redis-server redis-cli redis-benchmark adapter.so \
			redis_workload.py adapter.c REDIS-COPYING build.log; do
			cp "$macro_build/$file" "$package/macro/"
		done
		cp "$macro_source/vendor/redis-7.2.4.tar.gz" "$package/macro/"
		cp "$ROOT/test/test_gettime/vkso-tests/functional/vkso_abi.h" "$package/macro/"
		(cd "$package" && sha256sum macro/* >>SHA256SUMS)
	done
fi

"$HERE/verify-packages.sh" "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE" |
	tee "$BUILD_ROOT/package-audit.txt"

mv "$NORMAL_PACKAGE" "$normal_final"
mv "$NO_RETPOLINE_PACKAGE" "$no_retpoline_final"
echo "four_image_build_and_package_validation=pass"
echo "runtime_tests=not_run; use experiment.sh boot/collect CASE"
