#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
VKSO_SOURCE=${VKSO_SOURCE:-$ROOT/test/test_gettime/linux-5.15.198-vkso}
RAW_SOURCE=${RAW_SOURCE:-/tmp/vkso-raw-audit-src}
RAW_TARBALL=${RAW_TARBALL:-/tmp/linux-5.15.198.tar.xz}
RAW_PACKAGE=${RAW_PACKAGE:-}
BUILD_ROOT=${BUILD_ROOT:-/tmp/vkso-baremetal-build}
RAW_BUILD=${RAW_BUILD:-$BUILD_ROOT/raw}
VKSO_BUILD=${VKSO_BUILD:-$BUILD_ROOT/vkso}
BASE_CONFIG=${BASE_CONFIG:-$HERE/base.config}
BUILD_VARIANT=${BUILD_VARIANT:-normal}
UPDATE_BENCH=${UPDATE_BENCH:-0}
VKSO_VALIDATION_TESTS=${VKSO_VALIDATION_TESTS:-0}
STAMP=${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}
OUT=${OUT:-$HERE/artifacts/prepared-$STAMP}
JOBS=${JOBS:-$(nproc)}
CC=${CC:-gcc}
BENCHMARK_CFLAGS='-O2 -std=gnu11 -Wall -Wextra -Werror'
if [[ -z "${CURRENT_LINK+x}" ]]; then
	if [[ "$UPDATE_BENCH" == 1 ]]; then
		CURRENT_LINK=current-update
	elif [[ "$BUILD_VARIANT" == normal ]]; then
		CURRENT_LINK=current
	else
		CURRENT_LINK=current-no-retpoline
	fi
fi

case "$BUILD_VARIANT" in
normal|no-retpoline)
	;;
*)
	echo "BUILD_VARIANT must be normal or no-retpoline" >&2
	exit 2
	;;
esac

case "$UPDATE_BENCH" in
0|1)
	;;
*)
	echo "UPDATE_BENCH must be 0 or 1" >&2
	exit 2
	;;
esac
case "$VKSO_VALIDATION_TESTS" in
0|1)
	;;
*)
	echo "VKSO_VALIDATION_TESTS must be 0 or 1" >&2
	exit 2
	;;
esac
if [[ "$UPDATE_BENCH" == 1 && "$BUILD_VARIANT" != normal ]]; then
	echo "update-side benchmark images currently require BUILD_VARIANT=normal" >&2
	exit 2
fi
for command in "$CC" g++ make tar python3 sha256sum nm readelf; do
	command -v "$command" >/dev/null || {
		echo "missing build dependency: $command" >&2
		exit 1
	}
done
test -s "$BASE_CONFIG" || {
	echo "missing known-bootable base config: $BASE_CONFIG" >&2
	exit 1
}
test -f "$VKSO_SOURCE/Makefile"
if [[ -e "$OUT" ]]; then
	echo "refusing to overwrite package output: $OUT" >&2
	exit 1
fi

reuse_raw=0
if [[ -n "$RAW_PACKAGE" ]]; then
	for file in raw-bzImage raw.config; do
		test -s "$RAW_PACKAGE/$file" || {
			echo "missing reusable raw artifact: $RAW_PACKAGE/$file" >&2
			exit 1
		}
	done
	reuse_raw=1
elif [[ ! -f "$RAW_SOURCE/Makefile" ]]; then
	test -s "$RAW_TARBALL" || {
		echo "missing raw Linux 5.15.198 source and tarball" >&2
		echo "set RAW_PACKAGE to reuse a previously validated raw image" >&2
		exit 1
	}
	if [[ -e "$RAW_SOURCE" ]]; then
		echo "raw source path exists but is incomplete: $RAW_SOURCE" >&2
		exit 1
	fi
	mkdir -p "$RAW_SOURCE"
	tar -xf "$RAW_TARBALL" -C "$RAW_SOURCE" --strip-components=1
fi

if [[ "$reuse_raw" == 0 ]]; then
	test "$(make -s -C "$RAW_SOURCE" kernelversion)" = 5.15.198
fi
test "$(make -s -C "$VKSO_SOURCE" kernelversion)" = 5.15.198

uts_version_from_build()
{
	local build=$1

	sed -n 's/^#define UTS_VERSION "\(.*\)"$/\1/p' \
		"$build/include/generated/compile.h"
}

if [[ "$UPDATE_BENCH" == 1 ]]; then
	if [[ "$reuse_raw" == 0 ]]; then
		"$HERE/../update-bench/prepare-raw-source.sh" "$RAW_SOURCE"
	else
		grep -Fqx 'CONFIG_TIMEKEEPING_UPDATE_BENCH=y' \
			"$RAW_PACKAGE/raw.config" || {
			echo "reusable raw image lacks update instrumentation" >&2
			exit 1
		}
	fi
	test -f "$VKSO_SOURCE/include/linux/timekeeping_update_bench.h"
	test -f "$VKSO_SOURCE/kernel/time/timekeeping_update_bench.c"
fi
vkso_source_tree_sha256=$("$HERE/source-tree-hash.sh" "$VKSO_SOURCE")
if [[ "$reuse_raw" == 0 ]]; then
	raw_source_tree_sha256=$("$HERE/source-tree-hash.sh" "$RAW_SOURCE")
else
	raw_source_tree_sha256=$(awk -F= \
		'$1 == "raw_source_tree_sha256" {
			sub(/^[^=]*=/, ""); print; exit
		}' "$RAW_PACKAGE/boot-manifest.txt")
	: "${raw_source_tree_sha256:=reused-package}"
fi
mkdir -p "$RAW_BUILD" "$VKSO_BUILD" "$OUT"

configure_tree()
{
	local source=$1
	local build=$2
	local backend=$3

	cp "$BASE_CONFIG" "$build/.config"
	"$source/scripts/kconfig/merge_config.sh" -m -O "$build" \
		"$build/.config" "$HERE/baremetal.config"
	"$source/scripts/config" --file "$build/.config" \
		--enable MODULES \
		--enable MODULE_UNLOAD \
		--disable MODULE_SIG \
		--disable SECURITY_LOCKDOWN_LSM \
		--disable SECURITY_LOCKDOWN_LSM_EARLY \
		--disable IMA_APPRAISE_MODSIG \
		--disable IMA_APPRAISE_REQUIRE_MODULE_SIGS \
		--enable IKCONFIG \
		--enable IKCONFIG_PROC \
		--enable PERF_EVENTS \
		--enable TIME_NS \
		--enable SECCOMP \
		--enable SECCOMP_FILTER \
		--enable NO_HZ_FULL \
		--enable RCU_NOCB_CPU \
		--enable BLK_DEV_NVME \
		--enable EXT4_FS \
		--disable IA32_EMULATION \
		--disable X86_X32 \
		--disable X86_VSYSCALL_EMULATION \
		--disable DEBUG_INFO \
		--disable DEBUG_INFO_BTF \
		--disable KASAN \
		--disable KCSAN \
		--disable UBSAN \
		--disable KCOV \
		--disable GCOV_KERNEL \
		--disable PROVE_LOCKING \
		--disable LOCKDEP \
		--disable FTRACE \
		--disable FUNCTION_TRACER \
		--disable WERROR \
		--disable LOCALVERSION_AUTO \
		--set-str LOCALVERSION "" \
		--set-str SYSTEM_TRUSTED_KEYS "" \
		--set-str SYSTEM_REVOCATION_KEYS ""
	if [[ "$UPDATE_BENCH" == 1 ]]; then
		"$source/scripts/config" --file "$build/.config" \
			--enable DEBUG_FS --enable TIMEKEEPING_UPDATE_BENCH
	fi
	if [[ "$BUILD_VARIANT" == no-retpoline ]]; then
		"$source/scripts/config" --file "$build/.config" \
			--disable RETPOLINE \
			--disable RETHUNK \
			--disable CPU_UNRET_ENTRY
	fi
	if [[ "$backend" == vkso ]]; then
		"$source/scripts/kconfig/merge_config.sh" -m -O "$build" \
			"$build/.config" "$HERE/path.config"
		if [[ "$VKSO_VALIDATION_TESTS" == 1 ]]; then
			"$source/scripts/config" --file "$build/.config" \
				--enable VKSO_TIME --enable VKSO_TIME_TEST
		else
			"$source/scripts/config" --file "$build/.config" \
				--enable VKSO_TIME --disable VKSO_TIME_TEST
		fi
	fi
	make -C "$source" O="$build" olddefconfig
}

if [[ "$reuse_raw" == 1 ]]; then
	cp "$RAW_PACKAGE/raw.config" "$RAW_BUILD/.config"
else
	configure_tree "$RAW_SOURCE" "$RAW_BUILD" raw
fi
configure_tree "$VKSO_SOURCE" "$VKSO_BUILD" vkso

config_symbols()
{
	grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$1" |
		grep -Ev \
		'^(CONFIG_CC_VERSION_TEXT=|CONFIG_VKSO_TIME=|CONFIG_VKSO_TIME_TEST=|# CONFIG_VKSO_TIME|CONFIG_GENERIC_GETTIMEOFDAY=|CONFIG_GENERIC_TIME_VSYSCALL=|CONFIG_GENERIC_VDSO_TIME_NS=|CONFIG_HAVE_GENERIC_VDSO=|# CONFIG_IA32_EMULATION is not set|# CONFIG_X86_X32 is not set)' |
		grep -Ev '^# CONFIG_TIMEKEEPING_UPDATE_BENCH is not set' |
		sort
}

if ! diff -u <(config_symbols "$RAW_BUILD/.config") \
		   <(config_symbols "$VKSO_BUILD/.config") \
		   >"$OUT/config.diff"; then
	echo "raw/VKSO configs differ outside implementation selects" >&2
	cat "$OUT/config.diff" >&2
	exit 1
fi
grep -Fqx 'CONFIG_MODULES=y' "$RAW_BUILD/.config"
grep -Fqx 'CONFIG_MODULES=y' "$VKSO_BUILD/.config"
grep -Fqx 'CONFIG_VKSO_TIME=y' "$VKSO_BUILD/.config"
if [[ "$VKSO_VALIDATION_TESTS" == 1 ]]; then
	grep -Fqx 'CONFIG_VKSO_TIME_TEST=y' "$VKSO_BUILD/.config"
else
	grep -Fqx '# CONFIG_VKSO_TIME_TEST is not set' "$VKSO_BUILD/.config"
fi
if [[ "$UPDATE_BENCH" == 1 ]]; then
	grep -Fqx 'CONFIG_TIMEKEEPING_UPDATE_BENCH=y' "$RAW_BUILD/.config"
	grep -Fqx 'CONFIG_TIMEKEEPING_UPDATE_BENCH=y' "$VKSO_BUILD/.config"
else
	if grep -Eq '^CONFIG_TIMEKEEPING_UPDATE_BENCH=y' \
		"$RAW_BUILD/.config" "$VKSO_BUILD/.config"; then
		echo "normal reader image unexpectedly enables update benchmark" >&2
		exit 1
	fi
fi
if grep -q '^CONFIG_VKSO_TIME=' "$RAW_BUILD/.config"; then
	echo "raw config unexpectedly enables VKSO" >&2
	exit 1
fi
if [[ "$BUILD_VARIANT" == normal ]]; then
	for config in "$RAW_BUILD/.config" "$VKSO_BUILD/.config"; do
		grep -Fqx 'CONFIG_RETPOLINE=y' "$config"
		grep -Fqx 'CONFIG_RETHUNK=y' "$config"
	done
else
	for config in "$RAW_BUILD/.config" "$VKSO_BUILD/.config"; do
		grep -Fqx '# CONFIG_RETPOLINE is not set' "$config"
		if grep -Eq \
			'^(CONFIG_RETPOLINE|CONFIG_RETHUNK|CONFIG_CPU_UNRET_ENTRY)=y' \
			"$config"; then
			echo "no-retpoline config still enables a related option: $config" >&2
			exit 1
		fi
	done
fi

if [[ "$reuse_raw" == 0 ]]; then
	make -C "$RAW_SOURCE" O="$RAW_BUILD" CC="$CC" -j"$JOBS" \
		bzImage modules_prepare
fi
make -C "$VKSO_SOURCE" O="$VKSO_BUILD" CC="$CC" -j"$JOBS" \
	bzImage modules_prepare
cp "$VKSO_BUILD/vmlinux.symvers" "$VKSO_BUILD/Module.symvers"

test "$vkso_source_tree_sha256" = \
	"$("$HERE/source-tree-hash.sh" "$VKSO_SOURCE")" || {
	echo "VKSO source tree changed during build" >&2
	exit 1
}
if [[ "$reuse_raw" == 0 ]]; then
	test "$raw_source_tree_sha256" = \
		"$("$HERE/source-tree-hash.sh" "$RAW_SOURCE")" || {
		echo "raw source tree changed during build" >&2
		exit 1
	}
fi

vkso_uts_version=$(uts_version_from_build "$VKSO_BUILD")
test -n "$vkso_uts_version"
raw_uts_version=
if [[ "$reuse_raw" == 0 ]]; then
	raw_uts_version=$(uts_version_from_build "$RAW_BUILD")
elif [[ -s "$RAW_PACKAGE/boot-manifest.txt" ]]; then
	raw_uts_version=$(awk -F= '$1 == "raw_uts_version" {
		sub(/^[^=]*=/, ""); print; exit
	}' "$RAW_PACKAGE/boot-manifest.txt")
fi

artifacts=(
	"$VKSO_BUILD/arch/x86/boot/bzImage"
	"$VKSO_BUILD/vmlinux"
)
if [[ "$reuse_raw" == 0 ]]; then
	artifacts+=(
		"$RAW_BUILD/arch/x86/boot/bzImage"
		"$RAW_BUILD/vmlinux"
		"$RAW_BUILD/arch/x86/entry/vdso/vdso64.so.dbg"
	)
fi
for artifact in "${artifacts[@]}"; do
	test -s "$artifact" || {
		echo "missing build artifact: $artifact" >&2
		exit 1
	}
done

# The 5.15 extract-ikconfig helper cannot always locate IKCONFIG through a
# ZSTD-compressed x86 bzImage.  kernel/config_data is the exact payload linked
# into vmlinux and exposed as /proc/config.gz at runtime.
if [[ "$reuse_raw" == 0 ]]; then
	cmp -s "$RAW_BUILD/.config" "$RAW_BUILD/kernel/config_data"
	cp "$RAW_BUILD/kernel/config_data" "$OUT/raw.image.config"
elif [[ -s "$RAW_PACKAGE/raw.image.config" ]]; then
	cp "$RAW_PACKAGE/raw.image.config" "$OUT/raw.image.config"
else
	cp "$RAW_PACKAGE/raw.config" "$OUT/raw.image.config"
fi
cmp -s "$VKSO_BUILD/.config" "$VKSO_BUILD/kernel/config_data"
cp "$VKSO_BUILD/kernel/config_data" "$OUT/vkso.image.config"

MODULE_BUILD="$BUILD_ROOT/page-cache-replace"
mkdir -p "$MODULE_BUILD"
cp "$ROOT/page_cache_replace/Makefile" \
	"$ROOT/page_cache_replace/page_cache_replace.c" \
	"$ROOT/page_cache_replace/manager.cpp" "$MODULE_BUILD/"
make -C "$MODULE_BUILD" KDIR="$VKSO_BUILD" CC="$CC" -j"$JOBS" \
	module manager

M09_CLOCK_BUILD="$BUILD_ROOT/m09-posix-clock"
mkdir -p "$M09_CLOCK_BUILD"
cp "$HERE/../m09-posix-clock/Makefile" \
	"$HERE/../m09-posix-clock/vkso_m09_clock.c" "$M09_CLOCK_BUILD/"
make -C "$M09_CLOCK_BUILD" KDIR="$VKSO_BUILD" CC="$CC" -j"$JOBS"

KRG="$BUILD_ROOT/vkso.krg"
"$ROOT/kernel_cgd/src/krg" build "$VKSO_BUILD/vmlinux" -o "$KRG" \
	--kallsyms "$VKSO_BUILD/System.map"

DSO_BUILD="$BUILD_ROOT/dso"
mkdir -p "$DSO_BUILD"
cp "$HERE/symbols.txt" "$HERE/shared_data.txt" "$DSO_BUILD/"
"$CC" -c -fPIC -o "$DSO_BUILD/vkso_user_entry.o" \
	"$ROOT/test/test_gettime/vkso-tests/functional/vkso_user_entry.S"
(
	cd "$DSO_BUILD"
	python3 "$ROOT/make_dll/build_PIC_so.py" \
		--symbols symbols.txt \
		--krg "$KRG" \
		--shim-list "$ROOT/make_dll/shim.txt" \
		--shared-data-list shared_data.txt \
		--vmlinux "$VKSO_BUILD/vmlinux" \
		--private-wrapper-object vkso_user_entry.o \
		--symbol-addresses resolved_symbol_addresses.txt \
		--page-map page_mappings.txt
)

shared_value=$(nm -a "$DSO_BUILD/libkernel.so" |
	awk '$3 == "vkso_shared_page" && !value { value = "0x" $1 }
	     END { if (value) print value }')
test -n "$shared_value"
printf '%s\n' "$shared_value" >"$OUT/vkso-shared-st-value.txt"
text_anchor_value=$(nm -a "$DSO_BUILD/libkernel.so" |
	awk '$3 == "vkso_clock_gettime_realtime" && !value { value = "0x" $1 }
	     END { if (value) print value }')
test -n "$text_anchor_value"
printf '%s\n' "$text_anchor_value" >"$OUT/vkso-text-anchor-st-value.txt"

"$CC" $BENCHMARK_CFLAGS -pthread \
	-o "$OUT/raw-abi-matrix" \
	"$ROOT/test/test_gettime/vkso-tests/functional/abi_matrix.c" -ldl
"$CC" -DVKSO_BACKEND $BENCHMARK_CFLAGS -pthread \
	-o "$OUT/vkso-abi-matrix" \
	"$ROOT/test/test_gettime/vkso-tests/functional/abi_matrix.c" \
	"$ROOT/test/test_gettime/vkso-tests/functional/vkso_user_wrapper.c" \
	-L"$DSO_BUILD" -Wl,--no-as-needed -lkernel -ldl \
	-Wl,-rpath,'$ORIGIN'
"$CC" $BENCHMARK_CFLAGS -fno-omit-frame-pointer \
	-o "$OUT/vkso-time-bench" \
	"$HERE/vkso_time_bench.c" \
	"$ROOT/test/test_gettime/vkso-tests/functional/vkso_user_wrapper.c" \
	-L"$DSO_BUILD" -Wl,--no-as-needed -lkernel -ldl \
	-Wl,-rpath,'$ORIGIN'

if [[ "$reuse_raw" == 1 ]]; then
	install -m 0644 "$RAW_PACKAGE/raw-bzImage" "$OUT/raw-bzImage"
else
	install -m 0644 "$RAW_BUILD/arch/x86/boot/bzImage" "$OUT/raw-bzImage"
fi
install -m 0644 "$VKSO_BUILD/arch/x86/boot/bzImage" "$OUT/vkso-bzImage"
install -m 0644 "$RAW_BUILD/.config" "$OUT/raw.config"
install -m 0644 "$VKSO_BUILD/.config" "$OUT/vkso.config"
install -m 0644 "$DSO_BUILD/libkernel.so" "$OUT/libkernel.so"
install -m 0644 "$DSO_BUILD/page_mappings.txt" "$OUT/page_mappings.txt"
install -m 0644 "$DSO_BUILD/resolved_symbol_addresses.txt" \
	"$OUT/resolved_symbol_addresses.txt"
install -m 0644 "$MODULE_BUILD/page_cache_replace.ko" \
	"$OUT/page_cache_replace.ko"
install -m 0644 "$M09_CLOCK_BUILD/vkso_m09_clock.ko" \
	"$OUT/vkso_m09_clock.ko"
install -m 0755 "$MODULE_BUILD/manager" "$OUT/manager"

for script in collect-case.sh experiment.sh boot-once.sh install-grub.sh \
	qemu-preflight.sh qemu-guest-init verify-packages.sh \
	source-tree-hash.sh; do
	install -m 0755 "$HERE/$script" "$OUT/$script"
done
install -m 0644 "$HERE/experiment.conf" "$OUT/experiment.conf"
if [[ -s "$HERE/README.md" ]]; then
	install -m 0644 "$HERE/README.md" "$OUT/README.md"
fi
install -m 0644 "$HERE/vkso_time_bench.c" "$OUT/vkso_time_bench.c"
if [[ "$UPDATE_BENCH" == 1 ]]; then
	for script in collect-update.sh compare-update.py \
		collect-update-side.sh collect-update-concurrent.sh \
		boot-raw-update.sh boot-vkso-update.sh install-update-grub.sh; do
		install -m 0755 "$HERE/../update-bench/$script" "$OUT/$script"
	done
fi

{
	date -u '+prepared_utc=%Y-%m-%dT%H:%M:%SZ'
	printf 'git_commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD)"
	if [[ -n $(git -C "$ROOT" status --porcelain) ]]; then
		printf 'git_worktree_dirty=1\n'
	else
		printf 'git_worktree_dirty=0\n'
	fi
	printf 'build_variant=%s\n' "$BUILD_VARIANT"
	printf 'update_bench=%s\n' "$UPDATE_BENCH"
	printf 'vkso_validation_tests=%s\n' "$VKSO_VALIDATION_TESTS"
	printf 'vkso_source_tree_sha256=%s\n' "$vkso_source_tree_sha256"
	printf 'raw_source_tree_sha256=%s\n' "$raw_source_tree_sha256"
	printf 'experiment_config_sha256=%s\n' \
		"$(sha256sum "$HERE/experiment.conf" | awk '{print $1}')"
	printf 'cc_path=%s\n' "$(command -v "$CC")"
	printf 'cc_version=%s\n' "$("$CC" -dumpfullversion -dumpversion)"
	printf 'benchmark_cflags=%s\n' "$BENCHMARK_CFLAGS"
	printf 'kbuild_build_timestamp=%s\n' \
		"${KBUILD_BUILD_TIMESTAMP:-unspecified}"
	printf 'kbuild_build_user=%s\n' \
		"${KBUILD_BUILD_USER:-unspecified}"
	printf 'kbuild_build_host=%s\n' \
		"${KBUILD_BUILD_HOST:-unspecified}"
	if [[ "$reuse_raw" == 1 ]]; then
		printf 'raw_source=reused:%s\n' "$RAW_PACKAGE"
	else
		printf 'raw_source=%s\n' "$RAW_SOURCE"
	fi
	printf 'vkso_source=%s\n' "$VKSO_SOURCE"
	printf 'raw_build=%s\n' "$RAW_BUILD"
	printf 'vkso_build=%s\n' "$VKSO_BUILD"
	printf 'base_config=%s\n' "$BASE_CONFIG"
	printf 'kernelrelease=%s\n' \
		"$(make -s -C "$VKSO_SOURCE" O="$VKSO_BUILD" kernelrelease)"
	printf 'raw_image_sha256=%s\n' \
		"$(sha256sum "$OUT/raw-bzImage" | awk '{print $1}')"
	printf 'vkso_image_sha256=%s\n' \
		"$(sha256sum "$OUT/vkso-bzImage" | awk '{print $1}')"
	if [[ -n "$raw_uts_version" ]]; then
		printf 'raw_uts_version=%s\n' "$raw_uts_version"
	fi
	printf 'vkso_uts_version=%s\n' "$vkso_uts_version"
	printf 'vkso_shared_st_value=%s\n' "$shared_value"
	printf 'vkso_text_anchor_st_value=%s\n' "$text_anchor_value"
	if [[ "$VKSO_VALIDATION_TESTS" == 1 ]]; then
		printf 'production_test_probe=validation-only\n'
	else
		printf 'production_test_probe=absent\n'
	fi
	printf 'raw_native_vdso=present\n'
	printf 'vkso_native_vdso=absent\n'
	printf 'config_difference=implementation_selects_only\n'
	if [[ "$UPDATE_BENCH" == 1 ]]; then
		printf 'update_bench_header_sha256=%s\n' \
			"$(sha256sum "$VKSO_SOURCE/include/linux/timekeeping_update_bench.h" | awk '{print $1}')"
		printf 'update_bench_recorder_sha256=%s\n' \
			"$(sha256sum "$VKSO_SOURCE/kernel/time/timekeeping_update_bench.c" | awk '{print $1}')"
	fi
} >"$OUT/boot-manifest.txt"

(
	cd "$OUT"
	sha256sum raw-bzImage vkso-bzImage raw.config vkso.config \
		raw.image.config vkso.image.config boot-manifest.txt \
		libkernel.so page_mappings.txt page_cache_replace.ko \
		vkso_m09_clock.ko manager \
		raw-abi-matrix vkso-abi-matrix vkso-time-bench \
		collect-case.sh experiment.sh boot-once.sh install-grub.sh \
		qemu-preflight.sh qemu-guest-init verify-packages.sh \
		source-tree-hash.sh experiment.conf \
		>SHA256SUMS
	if [[ "$UPDATE_BENCH" == 1 ]]; then
		sha256sum collect-update.sh collect-update-side.sh \
			collect-update-concurrent.sh compare-update.py boot-once.sh \
			boot-raw-update.sh boot-vkso-update.sh \
			install-update-grub.sh >>SHA256SUMS
	fi
)

if [[ "$VKSO_VALIDATION_TESTS" == 0 ]]; then
	if nm "$VKSO_BUILD/vmlinux" |
	awk '$3 ~ /^__vkso_test_/ { found = 1 } END { exit !found }'; then
		echo "production VKSO image contains test probe" >&2
		exit 1
	fi
else
	nm "$VKSO_BUILD/vmlinux" |
		awk '$3 ~ /^__vkso_test_/ { found = 1 } END { exit !found }'
fi
if [[ "$reuse_raw" == 0 ]]; then
	if nm "$RAW_BUILD/vmlinux" |
		awk '$3 == "vkso_clock_gettime_realtime" { found = 1 }
		     END { exit !found }'; then
		echo "raw image contains VKSO time core" >&2
		exit 1
	fi
fi
nm "$VKSO_BUILD/vmlinux" |
	awk '$3 == "vkso_clock_gettime_realtime" { found = 1 }
	     END { exit !found }'
if [[ "$UPDATE_BENCH" == 1 ]]; then
	update_bench_images=("$VKSO_BUILD/vmlinux")
	if [[ "$reuse_raw" == 0 ]]; then
		update_bench_images+=("$RAW_BUILD/vmlinux")
	fi
	for image in "${update_bench_images[@]}"; do
		nm "$image" |
			awk '$3 == "timekeeping_update_bench_record" { found = 1 }
			     END { exit !found }'
	done
fi

if [[ -n "$CURRENT_LINK" ]]; then
	ln -sfn "$(basename "$OUT")" "$HERE/artifacts/$CURRENT_LINK"
fi
echo "baremetal_package=$OUT"
if [[ -n "$CURRENT_LINK" ]]; then
	echo "current_package=$HERE/artifacts/$CURRENT_LINK"
fi
cat "$OUT/boot-manifest.txt"
