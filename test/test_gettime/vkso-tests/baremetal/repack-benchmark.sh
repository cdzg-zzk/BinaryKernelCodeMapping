#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
ARTIFACTS=$HERE/artifacts
SOURCE_NORMAL=${SOURCE_NORMAL:-$ARTIFACTS/final-normal}
SOURCE_NO_RETPOLINE=${SOURCE_NO_RETPOLINE:-$ARTIFACTS/final-no-retpoline}
SOURCE_UPDATE_NORMAL=${SOURCE_UPDATE_NORMAL:-$ARTIFACTS/final-update-normal}
SOURCE_UPDATE_NO_RETPOLINE=${SOURCE_UPDATE_NO_RETPOLINE:-$ARTIFACTS/final-update-no-retpoline}
OUT_NORMAL=${OUT_NORMAL:-$ARTIFACTS/reader-load-v4-normal}
OUT_NO_RETPOLINE=${OUT_NO_RETPOLINE:-$ARTIFACTS/reader-load-v4-no-retpoline}
OUT_UPDATE_NORMAL=${OUT_UPDATE_NORMAL:-$ARTIFACTS/reader-load-v4-update-normal}
OUT_UPDATE_NO_RETPOLINE=${OUT_UPDATE_NO_RETPOLINE:-$ARTIFACTS/reader-load-v4-update-no-retpoline}
READER_WINDOW=$(sed -n \
	's/^#define READER_MEASUREMENT_WINDOW "\(.*\)"$/\1/p' \
	"$HERE/vkso_time_bench.c")
LOAD_WINDOW=$(sed -n \
	's/^#define LOAD_MEASUREMENT_WINDOW "\(.*\)"$/\1/p' \
	"$HERE/vkso_time_bench.c")
if [[ -z "$READER_WINDOW" || -z "$LOAD_WINDOW" ]]; then
	echo "benchmark measurement-window metadata is missing" >&2
	exit 1
fi

manifest_value()
{
	local manifest=$1 key=$2

	awk -F= -v key="$key" '$1 == key {
		sub(/^[^=]*=/, ""); print; exit
	}' "$manifest"
}

for directory in "$SOURCE_NORMAL" "$SOURCE_NO_RETPOLINE" \
	"$SOURCE_UPDATE_NORMAL" "$SOURCE_UPDATE_NO_RETPOLINE"; do
	test -s "$directory/boot-manifest.txt" || {
		echo "missing source package: $directory" >&2
		exit 1
	}
done
for directory in "$OUT_NORMAL" "$OUT_NO_RETPOLINE" \
	"$OUT_UPDATE_NORMAL" "$OUT_UPDATE_NO_RETPOLINE"; do
	if [[ -e "$directory" ]]; then
		echo "refusing to overwrite benchmark package: $directory" >&2
		exit 1
	fi
done

commit=$(git -C "$ROOT" rev-parse HEAD)
for package in "$SOURCE_NORMAL" "$SOURCE_NO_RETPOLINE" \
	"$SOURCE_UPDATE_NORMAL" "$SOURCE_UPDATE_NO_RETPOLINE"; do
	test "$(manifest_value "$package/boot-manifest.txt" git_commit)" = \
		"$commit"
done
expected_source=$(manifest_value \
	"$SOURCE_UPDATE_NORMAL/boot-manifest.txt" vkso_source_tree_sha256)
current_source=$("$HERE/source-tree-hash.sh" \
	"$ROOT/test/test_gettime/linux-5.15.198-vkso")
test "$current_source" = "$expected_source" || {
	echo "kernel/VKSO source changed; benchmark-only repack is unsafe" >&2
	exit 1
}

temporary=$(mktemp -d /tmp/vkso-benchmark-repack.XXXXXX)
trap 'rm -rf -- "$temporary"' EXIT INT TERM
benchmark_cflags=$(manifest_value \
	"$SOURCE_UPDATE_NORMAL/boot-manifest.txt" benchmark_cflags)
cc=$(manifest_value "$SOURCE_UPDATE_NORMAL/boot-manifest.txt" cc_path)
# The flags are stored as a controlled package manifest value.
# shellcheck disable=SC2086
"$cc" $benchmark_cflags -fno-omit-frame-pointer \
	-o "$temporary/vkso-time-bench" \
	"$HERE/vkso_time_bench.c" \
	"$ROOT/test/test_gettime/vkso-tests/functional/vkso_user_wrapper.c" \
	-L"$SOURCE_UPDATE_NORMAL" -Wl,--no-as-needed -lkernel -ldl \
	-Wl,-rpath,'$ORIGIN'

git -C "$ROOT" diff --binary --no-ext-diff HEAD -- \
	>"$temporary/source.patch"
patch_sha=$(sha256sum "$temporary/source.patch" | awk '{print $1}')
if [[ -s "$temporary/source.patch" ]]; then
	dirty=1
else
	dirty=0
fi
prepared_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
experiment_config_sha=$(sha256sum "$HERE/experiment.conf" | awk '{print $1}')
update_config_sha=$(sha256sum \
	"$HERE/../update-bench/update-experiment.conf" | awk '{print $1}')
concurrent_config_sha=$(sha256sum \
	"$HERE/../update-bench/concurrent-experiment.conf" | awk '{print $1}')

update_manifest()
{
	local package=$1 update_bench=$2 temporary_manifest

	temporary_manifest=$temporary/boot-manifest.$RANDOM
	awk -F= \
		-v prepared="$prepared_utc" \
		-v dirty="$dirty" \
		-v patch_sha="$patch_sha" \
		-v source_sha="$current_source" \
		-v experiment_sha="$experiment_config_sha" \
		-v update_sha="$update_config_sha" \
		-v concurrent_sha="$concurrent_config_sha" \
		-v reader_window="$READER_WINDOW" \
		-v load_window="$LOAD_WINDOW" \
		-v update_bench="$update_bench" '
	BEGIN { reader_seen = 0; load_seen = 0 }
	$1 == "prepared_utc" { print "prepared_utc=" prepared; next }
	$1 == "git_worktree_dirty" { print "git_worktree_dirty=" dirty; next }
	$1 == "candidate_patch_sha256" {
		print "candidate_patch_sha256=" patch_sha; next
	}
	$1 == "vkso_source_tree_sha256" {
		print "vkso_source_tree_sha256=" source_sha; next
	}
	$1 == "experiment_config_sha256" {
		print "experiment_config_sha256=" experiment_sha; next
	}
	$1 == "update_experiment_config_sha256" {
		if (update_bench == 1)
			print "update_experiment_config_sha256=" update_sha
		next
	}
	$1 == "concurrent_experiment_config_sha256" {
		if (update_bench == 1)
			print "concurrent_experiment_config_sha256=" concurrent_sha
		next
	}
	$1 == "reader_measurement_window" {
		print "reader_measurement_window=" reader_window
		reader_seen = 1
		next
	}
	$1 == "load_measurement_window" {
		print "load_measurement_window=" load_window
		load_seen = 1
		next
	}
	{ print }
	END {
		if (!reader_seen)
			print "reader_measurement_window=" reader_window
		if (!load_seen)
			print "load_measurement_window=" load_window
	}' "$package/boot-manifest.txt" >"$temporary_manifest"
	install -m 0644 "$temporary_manifest" "$package/boot-manifest.txt"
}

copy_common_files()
{
	local package=$1

	install -m 0755 "$temporary/vkso-time-bench" \
		"$package/vkso-time-bench"
	install -m 0644 "$HERE/vkso_time_bench.c" \
		"$package/vkso_time_bench.c"
	install -m 0755 "$HERE/collect-case.sh" "$package/collect-case.sh"
	install -m 0755 "$HERE/experiment.sh" "$package/experiment.sh"
	install -m 0755 "$HERE/boot-once.sh" "$package/boot-once.sh"
	install -m 0755 "$HERE/install-grub.sh" "$package/install-grub.sh"
	install -m 0755 "$HERE/qemu-preflight.sh" \
		"$package/qemu-preflight.sh"
	install -m 0755 "$HERE/qemu-guest-init" "$package/qemu-guest-init"
	install -m 0755 "$HERE/verify-packages.sh" \
		"$package/verify-packages.sh"
	install -m 0755 "$HERE/source-tree-hash.sh" \
		"$package/source-tree-hash.sh"
	install -m 0644 "$HERE/experiment.conf" "$package/experiment.conf"
	install -m 0644 "$HERE/README.md" "$package/README.md"
	install -m 0644 "$temporary/source.patch" "$package/source.patch"
}

copy_update_files()
{
	local package=$1 file

	for file in collect-update.sh collect-update-side.sh \
		collect-update-concurrent.sh compare-update.py \
		boot-raw-update.sh boot-vkso-update.sh boot-update-once.sh \
		experiment-update.sh experiment-concurrent.sh \
		install-update-grub.sh verify-update-packages.sh; do
		install -m 0755 "$HERE/../update-bench/$file" "$package/$file"
	done
	for file in update-experiment.conf concurrent-experiment.conf; do
		install -m 0644 "$HERE/../update-bench/$file" "$package/$file"
	done
}

write_hashes()
{
	local package=$1 update_bench=$2
	local -a files=(
		raw-bzImage vkso-bzImage raw.config vkso.config
		raw.image.config vkso.image.config boot-manifest.txt
		libkernel.so page_mappings.txt page_cache_replace.ko
		vkso_m09_clock.ko manager raw-abi-matrix vkso-abi-matrix
		vkso-time-bench vkso_time_bench.c collect-case.sh experiment.sh
		boot-once.sh install-grub.sh qemu-preflight.sh qemu-guest-init
		verify-packages.sh source-tree-hash.sh experiment.conf source.patch
	)

	if [[ "$update_bench" == 1 ]]; then
		files+=(
			collect-update.sh collect-update-side.sh
			collect-update-concurrent.sh compare-update.py
			boot-raw-update.sh boot-vkso-update.sh boot-update-once.sh
			experiment-update.sh experiment-concurrent.sh
			install-update-grub.sh verify-update-packages.sh
			update-experiment.conf concurrent-experiment.conf
		)
	fi
	(
		cd "$package"
		sha256sum "${files[@]}" >SHA256SUMS
	)
}

prepare_package()
{
	local source=$1 output=$2 update_bench=$3

	mkdir "$output"
	cp -a "$source/." "$output/"
	copy_common_files "$output"
	if [[ "$update_bench" == 1 ]]; then
		copy_update_files "$output"
	fi
	update_manifest "$output" "$update_bench"
	write_hashes "$output" "$update_bench"
}

prepare_package "$SOURCE_NORMAL" "$OUT_NORMAL" 0
prepare_package "$SOURCE_NO_RETPOLINE" "$OUT_NO_RETPOLINE" 0
prepare_package "$SOURCE_UPDATE_NORMAL" "$OUT_UPDATE_NORMAL" 1
prepare_package "$SOURCE_UPDATE_NO_RETPOLINE" \
	"$OUT_UPDATE_NO_RETPOLINE" 1

"$HERE/verify-packages.sh" "$OUT_NORMAL" "$OUT_NO_RETPOLINE"
"$HERE/../update-bench/verify-update-packages.sh" \
	"$OUT_UPDATE_NORMAL" "$OUT_UPDATE_NO_RETPOLINE"

for pair in \
	"$SOURCE_NORMAL:$OUT_NORMAL" \
	"$SOURCE_NO_RETPOLINE:$OUT_NO_RETPOLINE" \
	"$SOURCE_UPDATE_NORMAL:$OUT_UPDATE_NORMAL" \
	"$SOURCE_UPDATE_NO_RETPOLINE:$OUT_UPDATE_NO_RETPOLINE"; do
	IFS=: read -r source output <<<"$pair"
	for image in raw-bzImage vkso-bzImage; do
		cmp -s "$source/$image" "$output/$image"
	done
done

echo "benchmark_repack=pass"
echo "reader_measurement_window=$READER_WINDOW"
echo "load_measurement_window=$LOAD_WINDOW"
echo "normal_package=$OUT_NORMAL"
echo "no_retpoline_package=$OUT_NO_RETPOLINE"
echo "update_normal_package=$OUT_UPDATE_NORMAL"
echo "update_no_retpoline_package=$OUT_UPDATE_NO_RETPOLINE"
