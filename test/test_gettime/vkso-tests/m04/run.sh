#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd)
KERNEL="$ROOT/test/test_gettime/linux-5.15.198-vkso"
BUILD=${BUILD:-/tmp/vkso-m04-build}
WORK=${WORK:-/tmp/vkso-m04-run}
JOBS=${JOBS:-$(nproc)}
QEMU_SMP=${QEMU_SMP:-1}
QEMU_TCG_THREAD=${QEMU_TCG_THREAD:-single}
read -r -a QEMU_EXTRA <<<"${QEMU_EXTRA_ARGS:-}"
RESULT="$WORK/qemu.log"

mkdir -p "$BUILD" "$WORK"

if [ ! -f "$BUILD/.config" ]; then
	make -C "$KERNEL" O="$BUILD" no_vdso_defconfig
fi
"$KERNEL/scripts/kconfig/merge_config.sh" -m -O "$BUILD" \
	"$BUILD/.config" "$KERNEL/vkso-qemu.config"
make -C "$KERNEL" O="$BUILD" olddefconfig
make -C "$KERNEL" O="$BUILD" -j"$JOBS" bzImage modules_prepare
cp "$BUILD/vmlinux.symvers" "$BUILD/Module.symvers"

MODULE="$WORK/module"
mkdir -p "$MODULE"
cp "$ROOT/page_cache_replace/Makefile" \
	"$ROOT/page_cache_replace/page_cache_replace.c" \
	"$ROOT/page_cache_replace/manager.cpp" "$MODULE/"
make -C "$MODULE" KDIR="$BUILD" -j"$JOBS" module manager

KRG="$WORK/vkso-m04.krg"
if [ ! -f "$KRG" ] || [ "$BUILD/vmlinux" -nt "$KRG" ]; then
	"$ROOT/kernel_cgd/src/krg" build "$BUILD/vmlinux" -o "$KRG" \
		--kallsyms "$BUILD/System.map"
fi

DSO="$WORK/dso"
mkdir -p "$DSO"
if [ ! -f "$DSO/libkernel.so" ] || [ "$KRG" -nt "$DSO/libkernel.so" ]; then
	cp "$SCRIPT_DIR/symbols.txt" "$SCRIPT_DIR/shared_data.txt" "$DSO/"
	(
		cd "$DSO"
		python3 "$ROOT/make_dll/build_PIC_so.py" \
			--symbols symbols.txt \
			--krg "$KRG" \
			--shim-list "$ROOT/make_dll/shim.txt" \
			--shared-data-list shared_data.txt \
			--vmlinux "$BUILD/vmlinux" \
			--symbol-addresses resolved_symbol_addresses.txt \
			--page-map page_mappings.txt
	)
fi

gcc -O2 -Wall -Wextra -static -o "$WORK/m04-kernel-smoke" \
	"$SCRIPT_DIR/kernel_smoke.c"
gcc -O2 -Wall -Wextra -o "$WORK/m04-user-test" \
	"$SCRIPT_DIR/user_test.c" -L"$DSO" -Wl,--no-as-needed -lkernel \
	-ldl -pthread -Wl,-rpath,/work

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
	find . -print0 | cpio --null -o --format=newc 2>/dev/null | \
		gzip -1 > "$WORK/initramfs.cpio.gz"
)

PAYLOAD="$WORK/payload"
rm -rf "$PAYLOAD"
mkdir -p "$PAYLOAD"
cp "$MODULE/page_cache_replace.ko" "$MODULE/manager" "$PAYLOAD/"
cp "$DSO/libkernel.so" "$DSO/page_mappings.txt" "$PAYLOAD/"
cp "$WORK/m04-kernel-smoke" "$WORK/m04-user-test" "$PAYLOAD/"
if [ "${GETCPU_ONLY:-0}" -eq 1 ]; then
	touch "$PAYLOAD/getcpu-only"
fi
truncate -s 32M "$WORK/payload.ext4"
mkfs.ext4 -q -F -d "$PAYLOAD" "$WORK/payload.ext4"

set +e
timeout 180 qemu-system-x86_64 \
	-accel "tcg,thread=$QEMU_TCG_THREAD" -cpu max -m 512M \
	-smp "$QEMU_SMP" \
	-kernel "$BUILD/arch/x86/boot/bzImage" \
	-initrd "$WORK/initramfs.cpio.gz" \
	-drive "file=$WORK/payload.ext4,if=virtio,format=raw" \
	-append "console=ttyS0 init=/init panic=-1 oops=panic nokaslr" \
	"${QEMU_EXTRA[@]}" -nographic -no-reboot 2>&1 | tee "$RESULT"
qemu_status=${PIPESTATUS[0]}
set -e

if [ "$qemu_status" -ne 0 ] && [ "$qemu_status" -ne 124 ]; then
	echo "QEMU failed with status $qemu_status" >&2
	exit "$qemu_status"
fi

if [ "${GETCPU_ONLY:-0}" -eq 1 ]; then
	required_markers=(
		"kernel_getcpu_cpu=pass"
		"user_getcpu_cpu=pass"
		"user_getcpu_multithread=pass"
		"status=0"
	)
else
	required_markers=(
		"kernel_realtime_coarse=pass"
		"user_realtime_coarse=pass"
		"mapping_permissions=pass"
		"rip_relative_shared_read=pass"
		"status=0"
	)
fi
for marker in "${required_markers[@]}"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing QEMU marker: $marker" >&2
		exit 1
	}
done

if grep -Eq "Kernel panic|BUG:|WARNING:" "$RESULT"; then
	echo "kernel failure marker found in $RESULT" >&2
	exit 1
fi

echo "M04 PASS: $RESULT"
