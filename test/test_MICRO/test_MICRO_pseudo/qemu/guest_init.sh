#!/bin/busybox sh
set -eu

export PATH=/bin:/sbin:/usr/bin

mount -t devtmpfs devtmpfs /dev || mount -t tmpfs tmpfs /dev
mount -t proc proc /proc
mount -t sysfs sys /sys
mkdir -p /dev/pts /run /tmp
mount -t devpts devpts /dev/pts 2>/dev/null || true

echo "@@GUEST_INIT_BEGIN@@"
uname -a || true

if ! insmod /micro_pseudo.ko; then
	echo "@@FATAL@@ insmod micro_pseudo.ko failed"
	dmesg || true
	exec sh
fi

if ! /guest_runner.sh; then
	echo "@@FATAL@@ guest_runner failed"
	dmesg || true
	exec sh
fi

echo "@@GUEST_DONE@@"
sync
poweroff -f || reboot -f || echo o > /proc/sysrq-trigger
exec sh
