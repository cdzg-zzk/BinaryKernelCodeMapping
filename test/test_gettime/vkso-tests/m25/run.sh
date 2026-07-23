#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd)
KERNEL="$ROOT/test/test_gettime/linux-5.15.198-vkso"
BUILD=${BUILD:-/tmp/vkso-m25-build}
JOBS=${JOBS:-$(nproc)}

mkdir -p "$BUILD"
if [[ ! -f "$BUILD/.config" ]]; then
	make -C "$KERNEL" O="$BUILD" no_vdso_defconfig
fi
"$KERNEL/scripts/kconfig/merge_config.sh" -m -O "$BUILD" \
	"$BUILD/.config" "$KERNEL/vkso-qemu.config"
"$KERNEL/scripts/config" --file "$BUILD/.config" \
	--disable VKSO_TIME_TEST
make -C "$KERNEL" O="$BUILD" olddefconfig
make -C "$KERNEL" O="$BUILD" -j"$JOBS" vmlinux

grep -Fqx 'CONFIG_VKSO_TIME=y' "$BUILD/.config"
grep -Fqx 'CONFIG_PARAVIRT_CLOCK=y' "$BUILD/.config"

cold=$(objdump -d --disassemble=vkso_read_pvclock_cycles "$BUILD/vmlinux")
clock_gettime=$(objdump -d --disassemble=vkso_clock_gettime_core \
	"$BUILD/vmlinux")
provider=$(objdump -d --disassemble=pvclock_set_pvti_cpu0_va \
	"$BUILD/vmlinux")

grep -Eq '[[:space:]]rdtsc(p)?[[:space:]]*$' <<<"$cold"
grep -Eq '[[:space:]]mul[q]?[[:space:]]' <<<"$cold"
if grep -Eq '[[:space:]](call|jmp)[q]?[[:space:]]+\*|[[:space:]]call[q]?[[:space:]]' \
	<<<"$cold"; then
	echo "M25 PVClock cold path contains a call/indirect branch" >&2
	exit 1
fi
grep -Fq '<vkso_read_pvclock_cycles>' <<<"$clock_gettime"
grep -Fq '<vkso_time_set_pvclock_page>' <<<"$provider"

echo "M25 static PASS: PVClock page registered; cold reader is self-contained"
