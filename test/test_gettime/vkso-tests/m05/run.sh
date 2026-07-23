#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd)
KERNEL="$ROOT/test/test_gettime/linux-5.15.198-vkso"
BUILD=${BUILD:-/tmp/vkso-m05-build}
WORK=${WORK:-/tmp/vkso-m05-run}
JOBS=${JOBS:-$(nproc)}
RESULT="$WORK/qemu.log"

mkdir -p "$BUILD" "$WORK"
if [ ! -f "$BUILD/.config" ]; then
	make -C "$KERNEL" O="$BUILD" no_vdso_defconfig
fi
"$KERNEL/scripts/kconfig/merge_config.sh" -m -O "$BUILD" \
	"$BUILD/.config" "$KERNEL/vkso-qemu.config"
make -C "$KERNEL" O="$BUILD" olddefconfig
make -C "$KERNEL" O="$BUILD" -j"$JOBS" bzImage

gcc -O2 -Wall -Wextra -Werror -static -o "$WORK/m05-mm-data-test" \
	"$SCRIPT_DIR/mm_data_test.c"
gcc -O2 -Wall -Wextra -Werror -static -o "$WORK/m04-kernel-smoke" \
	"$SCRIPT_DIR/../m04/kernel_smoke.c"

INITRAMFS="$WORK/initramfs"
rm -rf "$INITRAMFS"
mkdir -p "$INITRAMFS/bin" "$INITRAMFS/dev" "$INITRAMFS/proc" \
	"$INITRAMFS/sys" "$INITRAMFS/tmp"
cp /usr/bin/busybox "$INITRAMFS/bin/busybox"
cp "$SCRIPT_DIR/guest_init" "$INITRAMFS/init"
cp "$WORK/m05-mm-data-test" "$WORK/m04-kernel-smoke" "$INITRAMFS/bin/"
chmod 0755 "$INITRAMFS/init"
(
	cd "$INITRAMFS"
	find . -print0 | cpio --null -o --format=newc 2>/dev/null | \
		gzip -1 > "$WORK/initramfs.cpio.gz"
)

set +e
timeout 180 qemu-system-x86_64 \
	-accel tcg,thread=single -cpu max -m 512M -smp 1 \
	-kernel "$BUILD/arch/x86/boot/bzImage" \
	-initrd "$WORK/initramfs.cpio.gz" \
	-append "console=ttyS0 init=/init panic=-1 oops=panic" \
	-nographic -no-reboot 2>&1 | tee "$RESULT"
qemu_status=${PIPESTATUS[0]}
set -e

if [ "$qemu_status" -ne 0 ] && [ "$qemu_status" -ne 124 ]; then
	echo "QEMU failed with status $qemu_status" >&2
	exit "$qemu_status"
fi

for marker in \
	"mm_data_layout=pass" \
	"mm_data_mapping=r--/nx" \
	"per_mm_pages=pass" \
	"m05_status=pass" \
	"kernel_realtime_coarse=pass" \
	"status=0"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing QEMU marker: $marker" >&2
		exit 1
	}
done

if grep -Eq "Kernel panic|BUG:|Oops:|WARNING:" "$RESULT"; then
	echo "kernel failure marker found in $RESULT" >&2
	exit 1
fi

echo "M05 PASS: $RESULT"
