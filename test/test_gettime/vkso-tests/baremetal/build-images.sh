#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
VKSO_SOURCE=${VKSO_SOURCE:-$ROOT/test/test_gettime/linux-5.15.198-vkso}
RAW_SOURCE=${RAW_SOURCE:-/tmp/vkso-raw-audit-src}
RAW_TARBALL=${RAW_TARBALL:-/tmp/linux-5.15.198.tar.xz}
BUILD_ROOT=${BUILD_ROOT:-/tmp/vkso-baremetal-build}
RAW_BUILD=${RAW_BUILD:-$BUILD_ROOT/raw}
VKSO_BUILD=${VKSO_BUILD:-$BUILD_ROOT/vkso}
BASE_CONFIG=${BASE_CONFIG:-/boot/config-vkso-time-raw-5.15.198}
STAMP=${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}
OUT=${OUT:-$HERE/artifacts/prepared-$STAMP}
JOBS=${JOBS:-$(nproc)}

for command in gcc g++ make tar python3 sha256sum nm readelf; do
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

if [[ ! -f "$RAW_SOURCE/Makefile" ]]; then
	test -s "$RAW_TARBALL" || {
		echo "missing raw Linux 5.15.198 source and tarball" >&2
		exit 1
	}
	if [[ -e "$RAW_SOURCE" ]]; then
		echo "raw source path exists but is incomplete: $RAW_SOURCE" >&2
		exit 1
	fi
	mkdir -p "$RAW_SOURCE"
	tar -xf "$RAW_TARBALL" -C "$RAW_SOURCE" --strip-components=1
fi

test "$(make -s -C "$RAW_SOURCE" kernelversion)" = 5.15.198
test "$(make -s -C "$VKSO_SOURCE" kernelversion)" = 5.15.198
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
	if [[ "$backend" == vkso ]]; then
		"$source/scripts/kconfig/merge_config.sh" -m -O "$build" \
			"$build/.config" "$HERE/path.config"
		"$source/scripts/config" --file "$build/.config" \
			--enable VKSO_TIME --disable VKSO_TIME_TEST
	fi
	make -C "$source" O="$build" olddefconfig
}

configure_tree "$RAW_SOURCE" "$RAW_BUILD" raw
configure_tree "$VKSO_SOURCE" "$VKSO_BUILD" vkso

config_symbols()
{
	grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$1" |
		grep -Ev \
		'^(CONFIG_VKSO_TIME=|# CONFIG_VKSO_TIME|CONFIG_GENERIC_GETTIMEOFDAY=|CONFIG_GENERIC_TIME_VSYSCALL=|CONFIG_GENERIC_VDSO_TIME_NS=|CONFIG_HAVE_GENERIC_VDSO=|# CONFIG_IA32_EMULATION is not set|# CONFIG_X86_X32 is not set)' |
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
grep -Fqx '# CONFIG_VKSO_TIME_TEST is not set' "$VKSO_BUILD/.config"
if grep -q '^CONFIG_VKSO_TIME=' "$RAW_BUILD/.config"; then
	echo "raw config unexpectedly enables VKSO" >&2
	exit 1
fi

make -C "$RAW_SOURCE" O="$RAW_BUILD" -j"$JOBS" bzImage modules_prepare
make -C "$VKSO_SOURCE" O="$VKSO_BUILD" -j"$JOBS" bzImage modules_prepare
cp "$VKSO_BUILD/vmlinux.symvers" "$VKSO_BUILD/Module.symvers"

for artifact in \
	"$RAW_BUILD/arch/x86/boot/bzImage" \
	"$RAW_BUILD/vmlinux" \
	"$RAW_BUILD/arch/x86/entry/vdso/vdso64.so.dbg" \
	"$VKSO_BUILD/arch/x86/boot/bzImage" \
	"$VKSO_BUILD/vmlinux"; do
	test -s "$artifact" || {
		echo "missing build artifact: $artifact" >&2
		exit 1
	}
done

# The 5.15 extract-ikconfig helper cannot always locate IKCONFIG through a
# ZSTD-compressed x86 bzImage.  kernel/config_data is the exact payload linked
# into vmlinux and exposed as /proc/config.gz at runtime.
cmp -s "$RAW_BUILD/.config" "$RAW_BUILD/kernel/config_data"
cmp -s "$VKSO_BUILD/.config" "$VKSO_BUILD/kernel/config_data"
cp "$RAW_BUILD/kernel/config_data" "$OUT/raw.image.config"
cp "$VKSO_BUILD/kernel/config_data" "$OUT/vkso.image.config"

MODULE_BUILD="$BUILD_ROOT/page-cache-replace"
mkdir -p "$MODULE_BUILD"
cp "$ROOT/page_cache_replace/Makefile" \
	"$ROOT/page_cache_replace/page_cache_replace.c" \
	"$ROOT/page_cache_replace/manager.cpp" "$MODULE_BUILD/"
make -C "$MODULE_BUILD" KDIR="$VKSO_BUILD" -j"$JOBS" module manager

KRG="$BUILD_ROOT/vkso.krg"
"$ROOT/kernel_cgd/src/krg" build "$VKSO_BUILD/vmlinux" -o "$KRG" \
	--kallsyms "$VKSO_BUILD/System.map"

DSO_BUILD="$BUILD_ROOT/dso"
mkdir -p "$DSO_BUILD"
cp "$HERE/symbols.txt" "$HERE/shared_data.txt" "$DSO_BUILD/"
(
	cd "$DSO_BUILD"
	python3 "$ROOT/make_dll/build_PIC_so.py" \
		--symbols symbols.txt \
		--krg "$KRG" \
		--shim-list "$ROOT/make_dll/shim.txt" \
		--shared-data-list shared_data.txt \
		--vmlinux "$VKSO_BUILD/vmlinux" \
		--symbol-addresses resolved_symbol_addresses.txt \
		--page-map page_mappings.txt
)

shared_value=$(nm -a "$DSO_BUILD/libkernel.so" |
	awk '$3 == "vkso_shared_page" && !value { value = "0x" $1 }
	     END { if (value) print value }')
test -n "$shared_value"
printf '%s\n' "$shared_value" >"$OUT/vkso-shared-st-value.txt"

gcc -O2 -std=gnu11 -Wall -Wextra -Werror -pthread \
	-o "$OUT/raw-abi-matrix" \
	"$ROOT/test/test_gettime/vkso-tests/m27/abi_matrix.c" -ldl
gcc -DVKSO_BACKEND -O2 -std=gnu11 -Wall -Wextra -Werror -pthread \
	-o "$OUT/vkso-abi-matrix" \
	"$ROOT/test/test_gettime/vkso-tests/m27/abi_matrix.c" \
	"$ROOT/test/test_gettime/vkso-tests/m27/vkso_user_wrapper.c" \
	-L"$DSO_BUILD" -Wl,--no-as-needed -lkernel -ldl \
	-Wl,-rpath,'$ORIGIN'
gcc -O2 -std=gnu11 -Wall -Wextra -Werror -fno-omit-frame-pointer \
	-DVKSO_SHARED_ST_VALUE="$shared_value" \
	-o "$OUT/vkso-time-bench" \
	"$HERE/vkso_time_bench.c" \
	"$ROOT/test/test_gettime/vkso-tests/m27/vkso_user_wrapper.c" \
	-L"$DSO_BUILD" -Wl,--no-as-needed -lkernel -ldl \
	-Wl,-rpath,'$ORIGIN'

install -m 0644 "$RAW_BUILD/arch/x86/boot/bzImage" "$OUT/raw-bzImage"
install -m 0644 "$VKSO_BUILD/arch/x86/boot/bzImage" "$OUT/vkso-bzImage"
install -m 0644 "$RAW_BUILD/.config" "$OUT/raw.config"
install -m 0644 "$VKSO_BUILD/.config" "$OUT/vkso.config"
install -m 0644 "$DSO_BUILD/libkernel.so" "$OUT/libkernel.so"
install -m 0644 "$DSO_BUILD/page_mappings.txt" "$OUT/page_mappings.txt"
install -m 0644 "$DSO_BUILD/resolved_symbol_addresses.txt" \
	"$OUT/resolved_symbol_addresses.txt"
install -m 0644 "$MODULE_BUILD/page_cache_replace.ko" \
	"$OUT/page_cache_replace.ko"
install -m 0755 "$MODULE_BUILD/manager" "$OUT/manager"

for script in collect.sh compare.py boot-once.sh boot-raw.sh boot-vkso.sh \
	install-grub.sh qemu-preflight.sh qemu-guest-init; do
	install -m 0755 "$HERE/$script" "$OUT/$script"
done
install -m 0644 "$HERE/README.md" "$OUT/README.md"
install -m 0644 "$HERE/vkso_time_bench.c" "$OUT/vkso_time_bench.c"

(
	cd "$OUT"
	sha256sum raw-bzImage vkso-bzImage raw.config vkso.config \
		libkernel.so page_mappings.txt page_cache_replace.ko manager \
		raw-abi-matrix vkso-abi-matrix vkso-time-bench \
		>SHA256SUMS
)

{
	date -u '+prepared_utc=%Y-%m-%dT%H:%M:%SZ'
	printf 'git_commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD)"
	printf 'raw_source=%s\n' "$RAW_SOURCE"
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
	printf 'vkso_shared_st_value=%s\n' "$shared_value"
	printf 'production_test_probe=absent\n'
	printf 'raw_native_vdso=present\n'
	printf 'vkso_native_vdso=absent\n'
	printf 'config_difference=implementation_selects_only\n'
} >"$OUT/boot-manifest.txt"

if nm "$VKSO_BUILD/vmlinux" |
	awk '$3 ~ /^__vkso_test_/ { found = 1 } END { exit !found }'; then
	echo "production VKSO image contains test probe" >&2
	exit 1
fi
if nm "$RAW_BUILD/vmlinux" |
	awk '$3 == "vkso_clock_gettime_core" { found = 1 }
	     END { exit !found }'; then
	echo "raw image contains VKSO time core" >&2
	exit 1
fi
nm "$VKSO_BUILD/vmlinux" |
	awk '$3 == "vkso_clock_gettime_core" { found = 1 }
	     END { exit !found }'

ln -sfn "$(basename "$OUT")" "$HERE/artifacts/current"
echo "baremetal_package=$OUT"
echo "current_package=$HERE/artifacts/current"
cat "$OUT/boot-manifest.txt"
