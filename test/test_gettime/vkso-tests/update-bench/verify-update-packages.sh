#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ARTIFACTS=$HERE/../baremetal/artifacts
NORMAL_PACKAGE=${1:-$ARTIFACTS/final-update-normal}
NO_RETPOLINE_PACKAGE=${2:-$ARTIFACTS/final-update-no-retpoline}

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
		page_mappings.txt page_cache_replace.ko vkso_m09_clock.ko raw-m09-clock.ko \
		manager collect-update.sh collect-update-side.sh \
		collect-update-concurrent.sh \
		boot-update-once.sh experiment-update.sh experiment-concurrent.sh \
		install-update-grub.sh verify-update-packages.sh \
		update-experiment.conf; do
		test -s "$package/$file" || {
			echo "missing update package artifact: $package/$file" >&2
			exit 1
		}
	done
	test -e "$package/source.patch" || {
		echo "missing update package artifact: $package/source.patch" >&2
		exit 1
	}
	(cd "$package" && sha256sum -c SHA256SUMS >/dev/null)
	test "$(manifest_value "$package" build_variant)" = "$variant"
	test "$(manifest_value "$package" update_bench)" = 1
	grep -Fqx 'CONFIG_TIMEKEEPING_UPDATE_BENCH=y' "$package/raw.config"
	grep -Fqx 'CONFIG_TIMEKEEPING_UPDATE_BENCH=y' "$package/vkso.config"
	grep -Fqx 'BENCH_SCOPE=all' "$package/update-experiment.conf"
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
		'^(CONFIG_VKSO_TIME=|# CONFIG_VKSO_TIME|CONFIG_GENERIC_TIME_VSYSCALL=|# CONFIG_GENERIC_TIME_VSYSCALL|CONFIG_HAVE_GENERIC_VDSO=|# CONFIG_HAVE_GENERIC_VDSO|CONFIG_GENERIC_GETTIMEOFDAY=|# CONFIG_GENERIC_GETTIMEOFDAY|CONFIG_GENERIC_VDSO_TIME_NS=|# CONFIG_GENERIC_VDSO_TIME_NS|CONFIG_IA32_EMULATION=|# CONFIG_IA32_EMULATION|CONFIG_X86_X32=|# CONFIG_X86_X32|CONFIG_X86_VSYSCALL_EMULATION=|# CONFIG_X86_VSYSCALL_EMULATION)' |
		sort
}

config_without_retpoline_family()
{
	grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$1" |
		grep -Ev \
		'^(CONFIG_RETPOLINE=|# CONFIG_RETPOLINE|CONFIG_RETHUNK=|# CONFIG_RETHUNK|CONFIG_CPU_UNRET_ENTRY=|# CONFIG_CPU_UNRET_ENTRY|CONFIG_CPU_SRSO=|# CONFIG_CPU_SRSO|CONFIG_MITIGATION_ITS=|# CONFIG_MITIGATION_ITS)' |
		sort
}

python3 "$HERE/stateful.py" verify --package "$NORMAL_PACKAGE"
python3 "$HERE/stateful.py" verify --package "$NO_RETPOLINE_PACKAGE"

validate_package "$NORMAL_PACKAGE" normal
validate_package "$NO_RETPOLINE_PACKAGE" no-retpoline

for package in "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"; do
	diff -u <(config_without_implementation "$package/raw.config") \
		<(config_without_implementation "$package/vkso.config") >/dev/null
done

for backend in raw vkso; do
	diff -u \
		<(config_without_retpoline_family \
			"$NORMAL_PACKAGE/$backend.config") \
		<(config_without_retpoline_family \
			"$NO_RETPOLINE_PACKAGE/$backend.config") >/dev/null
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
		echo "no-retpoline update package enables a mitigation option: $config" >&2
		exit 1
	fi
done

# Compare implementation/toolchain identity, not collection scripts or build time.
for key in vkso_source_tree_sha256 raw_source_tree_sha256 cc_version \
    update_bench_header_sha256 update_bench_recorder_sha256; do
    normal_value=$(manifest_value "$NORMAL_PACKAGE" "$key")
    no_retpoline_value=$(manifest_value "$NO_RETPOLINE_PACKAGE" "$key")
    if [[ -z "$normal_value" || "$normal_value" != "$no_retpoline_value" ]]; then
        echo "update package manifest mismatch for $key" >&2; exit 1
    fi
done

echo "kernel_update_package_validation=pass"
echo "normal_package=$NORMAL_PACKAGE"
echo "no_retpoline_package=$NO_RETPOLINE_PACKAGE"

python3 - "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE" <<'CHECK'
import json,sys
from pathlib import Path
p,q=map(Path,sys.argv[1:])
a,b=[json.loads((x/'direct/build.json').read_text()) for x in (p,q)]
for key in ('source_fingerprint','compiler_version','base_cflags'):
    if a[key]!=b[key]: sys.exit('public build mismatch: '+key)
for name in ('native-load','vkso-load','libvkso_time.so'):
    if (p/'direct'/name).read_bytes()!=(q/'direct'/name).read_bytes():
        sys.exit('public binary mismatch: '+name)
CHECK

echo "four_image_update_package_validation=pass"
