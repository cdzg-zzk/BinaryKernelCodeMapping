#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd)
VKSO_KERNEL="$ROOT/test/test_gettime/linux-5.15.198-vkso"
VKSO_BUILD=${VKSO_BUILD:-/tmp/vkso-m27-vkso-build}
RAW_KERNEL=${RAW_KERNEL:-/tmp/vkso-raw-audit-src}
RAW_BUILD=${RAW_BUILD:-/tmp/vkso-m27-raw-build}
RAW_TARBALL=${RAW_TARBALL:-/tmp/linux-5.15.198.tar.xz}
WORK=${WORK:-/tmp/vkso-m27-run}
JOBS=${JOBS:-$(nproc)}
# Stable TSC is required to prove the high-resolution user fast path.  TCG
# marks the TSC unstable with multiple vCPUs; the multi-CPU matrix is a
# separate run and must not silently turn this path test into syscall fallback.
QEMU_SMP=${QEMU_SMP:-1}
QEMU_TCG_THREAD=${QEMU_TCG_THREAD:-single}
read -r -a QEMU_EXTRA <<<"${QEMU_EXTRA_ARGS:-}"

mkdir -p "$VKSO_BUILD" "$RAW_BUILD" "$WORK"

if [[ ! -f "$VKSO_BUILD/.config" ]]; then
	make -C "$VKSO_KERNEL" O="$VKSO_BUILD" no_vdso_defconfig
fi
"$VKSO_KERNEL/scripts/kconfig/merge_config.sh" -m -O "$VKSO_BUILD" \
	"$VKSO_BUILD/.config" "$VKSO_KERNEL/vkso-qemu.config" \
	"$SCRIPT_DIR/path.config"
"$VKSO_KERNEL/scripts/config" --file "$VKSO_BUILD/.config" \
	--disable VKSO_TIME_TEST
make -C "$VKSO_KERNEL" O="$VKSO_BUILD" olddefconfig
make -C "$VKSO_KERNEL" O="$VKSO_BUILD" -j"$JOBS" bzImage modules_prepare
cp "$VKSO_BUILD/vmlinux.symvers" "$VKSO_BUILD/Module.symvers"

if [[ ! -f "$RAW_KERNEL/Makefile" ]]; then
	[[ -f "$RAW_TARBALL" ]] || {
		echo "missing raw Linux 5.15.198 tarball: $RAW_TARBALL" >&2
		exit 1
	}
	rm -rf "$RAW_KERNEL"
	mkdir -p "$RAW_KERNEL"
	tar -xf "$RAW_TARBALL" -C "$RAW_KERNEL" --strip-components=1
fi

# Start from the already-resolved VKSO config.  Raw olddefconfig removes the
# VKSO-only symbols and restores the native x86 vDSO selects.
cp "$VKSO_BUILD/.config" "$RAW_BUILD/.config"
make -C "$RAW_KERNEL" O="$RAW_BUILD" olddefconfig
make -C "$RAW_KERNEL" O="$RAW_BUILD" -j"$JOBS" bzImage

config_symbols()
{
	grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$1" |
		grep -Ev \
		'^(CONFIG_VKSO_TIME=|# CONFIG_VKSO_TIME|CONFIG_GENERIC_GETTIMEOFDAY=|CONFIG_GENERIC_TIME_VSYSCALL=|CONFIG_GENERIC_VDSO_TIME_NS=|CONFIG_HAVE_GENERIC_VDSO=|# CONFIG_IA32_EMULATION is not set|# CONFIG_X86_X32 is not set)' |
		sort
}

if ! diff -u <(config_symbols "$RAW_BUILD/.config") \
		   <(config_symbols "$VKSO_BUILD/.config") \
		   >"$WORK/config.diff"; then
	echo "raw/VKSO configs differ outside the implementation selects" >&2
	cat "$WORK/config.diff" >&2
	exit 1
fi
grep -Fqx 'CONFIG_VKSO_TIME=y' "$VKSO_BUILD/.config"
grep -Fqx '# CONFIG_VKSO_TIME_TEST is not set' "$VKSO_BUILD/.config"
grep -Fqx 'CONFIG_GENERIC_GETTIMEOFDAY=y' "$RAW_BUILD/.config"

MODULE="$WORK/module"
mkdir -p "$MODULE"
cp "$ROOT/page_cache_replace/Makefile" \
	"$ROOT/page_cache_replace/page_cache_replace.c" \
	"$ROOT/page_cache_replace/manager.cpp" "$MODULE/"
make -C "$MODULE" KDIR="$VKSO_BUILD" -j"$JOBS" module manager

KRG="$WORK/vkso.krg"
if [[ ! -f "$KRG" || "$VKSO_BUILD/vmlinux" -nt "$KRG" ]]; then
	"$ROOT/kernel_cgd/src/krg" build "$VKSO_BUILD/vmlinux" -o "$KRG" \
		--kallsyms "$VKSO_BUILD/System.map"
fi

DSO="$WORK/dso"
mkdir -p "$DSO"
cp "$SCRIPT_DIR/symbols.txt" "$SCRIPT_DIR/shared_data.txt" "$DSO/"
(
	cd "$DSO"
	python3 "$ROOT/make_dll/build_PIC_so.py" \
		--symbols symbols.txt \
		--krg "$KRG" \
		--shim-list "$ROOT/make_dll/shim.txt" \
		--shared-data-list shared_data.txt \
		--vmlinux "$VKSO_BUILD/vmlinux" \
		--symbol-addresses resolved_symbol_addresses.txt \
		--page-map page_mappings.txt
)

gcc -O2 -Wall -Wextra -Werror -pthread \
	-o "$WORK/raw-abi-matrix" "$SCRIPT_DIR/abi_matrix.c" -ldl
gcc -DVKSO_BACKEND -O2 -Wall -Wextra -Werror -pthread \
	-o "$WORK/vkso-abi-matrix" \
	"$SCRIPT_DIR/abi_matrix.c" "$SCRIPT_DIR/vkso_user_wrapper.c" \
	-L"$DSO" -Wl,--no-as-needed -lkernel -ldl -Wl,-rpath,/work

INITRAMFS="$WORK/initramfs"
rm -rf "$INITRAMFS"
mkdir -p "$INITRAMFS/bin" "$INITRAMFS/dev" "$INITRAMFS/proc" \
	"$INITRAMFS/sys" "$INITRAMFS/tmp" "$INITRAMFS/work" \
	"$INITRAMFS/lib/x86_64-linux-gnu" "$INITRAMFS/lib64"
cp /usr/bin/busybox "$INITRAMFS/bin/busybox"
cp "$SCRIPT_DIR/guest_init" "$INITRAMFS/init"
cp /lib/x86_64-linux-gnu/libc.so.6 \
	"$INITRAMFS/lib/x86_64-linux-gnu/libc.so.6"
cp -L /lib64/ld-linux-x86-64.so.2 \
	"$INITRAMFS/lib64/ld-linux-x86-64.so.2"
chmod 0755 "$INITRAMFS/init"
(
	cd "$INITRAMFS"
	find . -print0 | cpio --null -o --format=newc 2>/dev/null |
		gzip -1 >"$WORK/initramfs.cpio.gz"
)

make_payload()
{
	local kind=$1
	local label=${2:-$kind}
	local mode=${3:-full}
	local payload="$WORK/payload-$label"
	local image="$WORK/payload-$label.ext4"

	rm -rf "$payload"
	mkdir -p "$payload"
	printf '%s\n' "$kind" >"$payload/backend"
	cp "$WORK/$kind-abi-matrix" "$payload/abi-matrix"
	if [[ "$mode" == multicpu ]]; then
		touch "$payload/multicpu-only"
	fi
	if [[ "$kind" == vkso ]]; then
		cp "$MODULE/page_cache_replace.ko" "$MODULE/manager" "$payload/"
		cp "$DSO/libkernel.so" "$DSO/page_mappings.txt" "$payload/"
	fi
	truncate -s 32M "$image"
	mkfs.ext4 -q -F -d "$payload" "$image"
}

run_qemu()
{
	local label=$1
	local build=$2
	local smp=${3:-$QEMU_SMP}
	local success_marker=${4:-abi_matrix_status=pass}
	local log="$WORK/$label.log"
	local qemu_status

	set +e
	timeout 180 qemu-system-x86_64 \
		-accel "tcg,thread=$QEMU_TCG_THREAD" -cpu max -m 768M \
		-smp "$smp" \
		-kernel "$build/arch/x86/boot/bzImage" \
		-initrd "$WORK/initramfs.cpio.gz" \
		-drive "file=$WORK/payload-$label.ext4,if=virtio,format=raw" \
		-append "console=ttyS0 init=/init panic=-1 oops=panic nokaslr" \
		"${QEMU_EXTRA[@]}" -nographic -no-reboot 2>&1 | tee "$log"
	qemu_status=${PIPESTATUS[0]}
	set -e
	if [[ "$qemu_status" -ne 0 && "$qemu_status" -ne 124 ]]; then
		echo "$label QEMU failed with status $qemu_status" >&2
		exit "$qemu_status"
	fi
	grep -Fq "$success_marker" "$log"
	grep -Fq 'guest_status=0' "$log"
	if grep -Eq 'Kernel panic|BUG:|WARNING:' "$log"; then
		echo "kernel failure marker in $log" >&2
		exit 1
	fi
	grep -E '^(semantics|path)\.' "$log" >"$WORK/$label.matrix"
}

make_payload raw
make_payload vkso
run_qemu raw "$RAW_BUILD"
run_qemu vkso "$VKSO_BUILD"

if ! diff -u "$WORK/raw.matrix" "$WORK/vkso.matrix" \
		   >"$WORK/raw-vkso-matrix.diff"; then
	echo "raw vDSO and VKSO semantic/path matrices differ" >&2
	cat "$WORK/raw-vkso-matrix.diff" >&2
	exit 1
fi

make_payload raw raw-multicpu multicpu
make_payload vkso vkso-multicpu multicpu
run_qemu raw-multicpu "$RAW_BUILD" 4 multicpu_matrix_status=pass
run_qemu vkso-multicpu "$VKSO_BUILD" 4 multicpu_matrix_status=pass

if ! diff -u "$WORK/raw-multicpu.matrix" \
		   "$WORK/vkso-multicpu.matrix" \
		   >"$WORK/raw-vkso-multicpu-matrix.diff"; then
	echo "raw vDSO and VKSO multi-CPU matrices differ" >&2
	cat "$WORK/raw-vkso-multicpu-matrix.diff" >&2
	exit 1
fi

grep -Fq 'semantics.multicpu_threads=pass threads=4' \
	"$WORK/raw-multicpu.matrix"

echo "M27 PASS: raw and VKSO semantic/path/multi-CPU matrices are identical"
echo "raw_result=$WORK/raw.log"
echo "vkso_result=$WORK/vkso.log"
echo "matrix=$WORK/raw.matrix"
