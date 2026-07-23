#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ -s "$HERE/libkernel.so" ]]; then
	PACKAGE=${PACKAGE:-$HERE}
	CONTROL_DIR=${CONTROL_DIR:-$HERE}
else
	PACKAGE=${PACKAGE:-$HERE/artifacts/current}
	CONTROL_DIR=${CONTROL_DIR:-$HERE}
fi
STAMP=${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}
WORK=${WORK:-$CONTROL_DIR/results/qemu-preflight-$STAMP}

for command in qemu-system-x86_64 busybox cpio gzip mkfs.ext4 timeout; do
	command -v "$command" >/dev/null || {
		echo "missing QEMU preflight dependency: $command" >&2
		exit 1
	}
done
for file in raw-bzImage vkso-bzImage raw.config vkso.config \
	raw-abi-matrix vkso-abi-matrix vkso-time-bench libkernel.so \
	page_mappings.txt page_cache_replace.ko manager SHA256SUMS; do
	test -s "$PACKAGE/$file" || {
		echo "missing package artifact: $PACKAGE/$file" >&2
		exit 1
	}
done
(cd "$PACKAGE" && sha256sum -c SHA256SUMS)

mkdir -p "$WORK/initramfs/bin" "$WORK/initramfs/dev" \
	"$WORK/initramfs/proc" "$WORK/initramfs/sys" \
	"$WORK/initramfs/tmp" "$WORK/initramfs/work" \
	"$WORK/initramfs/lib/x86_64-linux-gnu" "$WORK/initramfs/lib64"
cp /usr/bin/busybox "$WORK/initramfs/bin/busybox"
cp "$HERE/qemu-guest-init" "$WORK/initramfs/init"
cp /lib/x86_64-linux-gnu/libc.so.6 \
	"$WORK/initramfs/lib/x86_64-linux-gnu/libc.so.6"
cp -L /lib64/ld-linux-x86-64.so.2 \
	"$WORK/initramfs/lib64/ld-linux-x86-64.so.2"
chmod 0755 "$WORK/initramfs/init"
(
	cd "$WORK/initramfs"
	find . -print0 | cpio --null -o --format=newc 2>/dev/null |
		gzip -1 >"$WORK/initramfs.cpio.gz"
)

make_payload()
{
	local backend=$1
	local payload=$WORK/payload-$backend
	local image=$WORK/payload-$backend.ext4

	mkdir -p "$payload"
	printf '%s\n' "$backend" >"$payload/backend"
	cp "$PACKAGE/$backend.config" "$payload/$backend.config"
	cp "$PACKAGE/$backend-abi-matrix" "$payload/abi-matrix"
	cp "$PACKAGE/vkso-time-bench" "$PACKAGE/libkernel.so" "$payload/"
	if [[ "$backend" == vkso ]]; then
		cp "$PACKAGE/page_cache_replace.ko" "$PACKAGE/manager" \
			"$PACKAGE/page_mappings.txt" "$payload/"
	fi
	truncate -s 32M "$image"
	mkfs.ext4 -q -F -d "$payload" "$image"
}

run_backend()
{
	local backend=$1
	local log=$WORK/$backend.log
	local qemu_status

	set +e
	timeout 180 qemu-system-x86_64 \
		-accel tcg,thread=single -cpu max -m 768M -smp 1 \
		-kernel "$PACKAGE/$backend-bzImage" \
		-initrd "$WORK/initramfs.cpio.gz" \
		-drive "file=$WORK/payload-$backend.ext4,if=ide,format=raw" \
		-append "console=ttyS0 init=/init panic=-1 oops=panic nokaslr clocksource=tsc tsc=reliable" \
		-nographic -no-reboot >"$log" 2>&1
	qemu_status=$?
	set -e
	if [[ "$qemu_status" -ne 0 && "$qemu_status" -ne 124 ]]; then
		echo "$backend QEMU failed with status $qemu_status" >&2
		exit "$qemu_status"
	fi
	grep -Fq 'abi_matrix_status=pass' "$log"
	grep -Fq 'guest_status=0' "$log"
	if grep -Eq 'Kernel panic|BUG:|WARNING:' "$log"; then
		echo "kernel failure marker in $log" >&2
		exit 1
	fi
	grep -E '^(semantics|path|namespace)\.' "$log" \
		>"$WORK/$backend.matrix"
	echo "qemu_backend=$backend status=pass matrix_rows=$(wc -l <"$WORK/$backend.matrix")"
}

make_payload raw
make_payload vkso
run_backend raw
run_backend vkso
diff -u "$WORK/raw.matrix" "$WORK/vkso.matrix" \
	>"$WORK/raw-vkso-matrix.diff"

echo "qemu_preflight=pass"
echo "result_dir=$WORK"
