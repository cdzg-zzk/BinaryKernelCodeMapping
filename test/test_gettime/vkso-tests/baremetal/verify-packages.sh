#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
NORMAL_PACKAGE=${1:-$HERE/artifacts/final-normal}
NO_RETPOLINE_PACKAGE=${2:-$HERE/artifacts/final-no-retpoline}

manifest_value()
{
	local package=$1 key=$2

	awk -F= -v key="$key" '$1 == key {
		sub(/^[^=]*=/, ""); print; exit
	}' "$package/boot-manifest.txt"
}

validate_package()
{
	local package=$1 variant=$2 file dirty patch_sha

	for file in raw-bzImage vkso-bzImage raw.config vkso.config \
		raw.image.config vkso.image.config boot-manifest.txt SHA256SUMS \
		raw-abi-matrix vkso-abi-matrix vkso-time-bench \
		vkso_time_bench.c libkernel.so \
		page_mappings.txt page_cache_replace.ko vkso_m09_clock.ko \
		manager; do
		test -s "$package/$file" || {
			echo "missing package artifact: $package/$file" >&2
			exit 1
		}
	done
	test -e "$package/source.patch" || {
		echo "missing package artifact: $package/source.patch" >&2
		exit 1
	}
	(cd "$package" && sha256sum -c SHA256SUMS >/dev/null)
	test "$(manifest_value "$package" build_variant)" = "$variant"
	test "$(manifest_value "$package" update_bench)" = 0
	dirty=$(manifest_value "$package" git_worktree_dirty)
	patch_sha=$(manifest_value "$package" candidate_patch_sha256)
	case "$dirty" in
	0)
		test ! -s "$package/source.patch"
		;;
	1)
		test -s "$package/source.patch"
		;;
	*)
		echo "invalid git_worktree_dirty value: $dirty" >&2
		exit 1
		;;
	esac
	test "$patch_sha" = \
		"$(sha256sum "$package/source.patch" | awk '{print $1}')"
	cmp -s "$package/raw.config" "$package/raw.image.config"
	cmp -s "$package/vkso.config" "$package/vkso.image.config"
}

config_without_implementation()
{
	grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$1" |
		grep -Ev \
		'^(CONFIG_VKSO_TIME=|# CONFIG_VKSO_TIME|CONFIG_GENERIC_TIME_VSYSCALL=|# CONFIG_GENERIC_TIME_VSYSCALL|CONFIG_HAVE_GENERIC_VDSO=|# CONFIG_HAVE_GENERIC_VDSO|CONFIG_GENERIC_GETTIMEOFDAY=|# CONFIG_GENERIC_GETTIMEOFDAY|CONFIG_GENERIC_VDSO_TIME_NS=|# CONFIG_GENERIC_VDSO_TIME_NS|CONFIG_IA32_EMULATION=|# CONFIG_IA32_EMULATION|CONFIG_X86_X32=|# CONFIG_X86_X32|CONFIG_X86_VSYSCALL_EMULATION=|# CONFIG_X86_VSYSCALL_EMULATION|CONFIG_TIMEKEEPING_UPDATE_BENCH=|# CONFIG_TIMEKEEPING_UPDATE_BENCH)' |
		sort
}

config_without_retpoline_family()
{
	grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$1" |
		grep -Ev \
		'^(CONFIG_RETPOLINE=|# CONFIG_RETPOLINE|CONFIG_RETHUNK=|# CONFIG_RETHUNK|CONFIG_CPU_UNRET_ENTRY=|# CONFIG_CPU_UNRET_ENTRY|CONFIG_CPU_SRSO=|# CONFIG_CPU_SRSO|CONFIG_MITIGATION_ITS=|# CONFIG_MITIGATION_ITS)' |
		sort
}

validate_package "$NORMAL_PACKAGE" normal
validate_package "$NO_RETPOLINE_PACKAGE" no-retpoline

for package in "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"; do
	diff -u <(config_without_implementation "$package/raw.config") \
		<(config_without_implementation "$package/vkso.config") \
		>/dev/null
done

for backend in raw vkso; do
	diff -u \
		<(config_without_retpoline_family \
			"$NORMAL_PACKAGE/$backend.config") \
		<(config_without_retpoline_family \
			"$NO_RETPOLINE_PACKAGE/$backend.config") \
		>/dev/null
done

for config in "$NORMAL_PACKAGE"/{raw,vkso}.config; do
	grep -Fqx 'CONFIG_RETPOLINE=y' "$config"
	grep -Fqx 'CONFIG_RETHUNK=y' "$config"
	grep -Fqx 'CONFIG_CPU_UNRET_ENTRY=y' "$config"
done
for config in "$NO_RETPOLINE_PACKAGE"/{raw,vkso}.config; do
	grep -Fqx '# CONFIG_RETPOLINE is not set' "$config"
	if grep -Eq \
		'^(CONFIG_RETPOLINE|CONFIG_RETHUNK|CONFIG_CPU_UNRET_ENTRY|CONFIG_CPU_SRSO|CONFIG_MITIGATION_ITS)=y' \
		"$config"; then
		echo "no-retpoline package still enables a related option: $config" >&2
		exit 1
	fi
done

for key in git_commit git_worktree_dirty candidate_patch_sha256 \
	vkso_source_tree_sha256 raw_source_tree_sha256 \
	cc_path cc_version benchmark_cflags experiment_config_sha256 \
	reader_measurement_window load_measurement_window \
	kbuild_build_timestamp kbuild_build_user kbuild_build_host; do
	normal_value=$(manifest_value "$NORMAL_PACKAGE" "$key")
	no_retpoline_value=$(manifest_value "$NO_RETPOLINE_PACKAGE" "$key")
	if [[ -z "$normal_value" || "$normal_value" != "$no_retpoline_value" ]]; then
		echo "package manifest mismatch for $key" >&2
		echo "normal=$normal_value" >&2
		echo "no-retpoline=$no_retpoline_value" >&2
		exit 1
	fi
done

for file in raw-abi-matrix vkso-abi-matrix vkso-time-bench \
	vkso_time_bench.c; do
	cmp -s "$NORMAL_PACKAGE/$file" "$NO_RETPOLINE_PACKAGE/$file" || {
		echo "test executable differs across build variants: $file" >&2
		exit 1
	}
done

if [[ -d "$NORMAL_PACKAGE/macro" || -d "$NO_RETPOLINE_PACKAGE/macro" ]]; then
	for file in redis-server redis-cli redis-benchmark adapter.so redis_workload.py \
		adapter.c vkso_abi.h redis-7.2.4.tar.gz; do
		cmp -s "$NORMAL_PACKAGE/macro/$file" "$NO_RETPOLINE_PACKAGE/macro/$file" || {
			echo "macrobench tool missing or differs across variants: $file" >&2
			exit 1
		}
	done
fi

echo "four_image_package_validation=pass"
echo "normal_package=$NORMAL_PACKAGE"
echo "no_retpoline_package=$NO_RETPOLINE_PACKAGE"
