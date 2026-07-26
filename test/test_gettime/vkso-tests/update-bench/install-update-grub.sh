#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ -s "$HERE/boot-manifest.txt" ]]; then
	PACKAGE=${PACKAGE:-$HERE}
else
	PACKAGE=${PACKAGE:-$HERE/../baremetal/artifacts/current-update}
fi
CPU=${CPU:-2}
HOUSEKEEPING_CPUS=${HOUSEKEEPING_CPUS:-0-1,3}
GRUB_SCRIPT=/etc/grub.d/42_vkso_time_update
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

if [[ $(id -u) -ne 0 ]]; then
	exec sudo --preserve-env=PACKAGE,CPU,HOUSEKEEPING_CPUS "$0" "$@"
fi

for file in raw-bzImage vkso-bzImage raw.config vkso.config \
	boot-manifest.txt SHA256SUMS; do
	test -s "$PACKAGE/$file" || {
		echo "missing update package artifact: $PACKAGE/$file" >&2
		exit 1
	}
done
(cd "$PACKAGE" && sha256sum -c SHA256SUMS)
grep -Fqx 'build_variant=normal' "$PACKAGE/boot-manifest.txt"
grep -Fqx 'update_bench=1' "$PACKAGE/boot-manifest.txt"
grep -Fqx 'CONFIG_TIMEKEEPING_UPDATE_BENCH=y' "$PACKAGE/raw.config"
grep -Fqx 'CONFIG_TIMEKEEPING_UPDATE_BENCH=y' "$PACKAGE/vkso.config"

boot_source=$(findmnt -no SOURCE /boot)
root_source=$(findmnt -no SOURCE /)
boot_uuid=$(blkid -s UUID -o value "$boot_source")
root_partuuid=$(blkid -s PARTUUID -o value "$root_source")
test -n "$boot_uuid" -a -n "$root_partuuid"

for target in \
	/boot/vkso-time-raw-update-5.15.198.bzImage \
	/boot/vkso-time-vkso-update-5.15.198.bzImage \
	/boot/config-vkso-time-raw-update-5.15.198 \
	/boot/config-vkso-time-vkso-update-5.15.198; do
	if [[ -e "$target" ]]; then
		cp -a "$target" "$target.bak.$STAMP"
	fi
done
if [[ -e "$GRUB_SCRIPT" ]]; then
	cp -a "$GRUB_SCRIPT" "$GRUB_SCRIPT.bak.$STAMP"
	chmod a-x "$GRUB_SCRIPT.bak.$STAMP"
fi
for backup in "$GRUB_SCRIPT".bak.*; do
	[[ -e "$backup" ]] && chmod a-x "$backup"
done

install -m 0644 "$PACKAGE/raw-bzImage" \
	/boot/vkso-time-raw-update-5.15.198.bzImage
install -m 0644 "$PACKAGE/vkso-bzImage" \
	/boot/vkso-time-vkso-update-5.15.198.bzImage
install -m 0644 "$PACKAGE/raw.config" \
	/boot/config-vkso-time-raw-update-5.15.198
install -m 0644 "$PACKAGE/vkso.config" \
	/boot/config-vkso-time-vkso-update-5.15.198
install -m 0644 "$PACKAGE/boot-manifest.txt" \
	/boot/vkso-time-update-manifest-5.15.198.txt

common_args="root=PARTUUID=$root_partuuid rootwait ro nokaslr"
common_args+=" clocksource=tsc tsc=reliable nosmt"
common_args+=" isolcpus=domain,managed_irq,$CPU nohz_full=$CPU"
common_args+=" rcu_nocbs=$CPU irqaffinity=$HOUSEKEEPING_CPUS"
common_args+=" idle=poll intel_pstate=active"
common_args+=" processor.max_cstate=0 intel_idle.max_cstate=0"
common_args+=" nmi_watchdog=0 nowatchdog audit=0"

{
	echo '#!/bin/sh'
	echo "cat <<'EOF'"
	echo "menuentry 'VKSO Time: raw update-bench 5.15.198' --id vkso-time-raw-update {"
	echo '	insmod part_gpt'
	echo '	insmod ext2'
	echo "	search --no-floppy --fs-uuid --set=root $boot_uuid"
	echo "	linux /vkso-time-raw-update-5.15.198.bzImage $common_args"
	echo '}'
	echo
	echo "menuentry 'VKSO Time: VKSO update-bench 5.15.198' --id vkso-time-vkso-update {"
	echo '	insmod part_gpt'
	echo '	insmod ext2'
	echo "	search --no-floppy --fs-uuid --set=root $boot_uuid"
	echo "	linux /vkso-time-vkso-update-5.15.198.bzImage $common_args"
	echo '}'
	echo 'EOF'
} >"$GRUB_SCRIPT"
chmod 0755 "$GRUB_SCRIPT"
update-grub
grep -Fq -- '--id vkso-time-raw-update' /boot/grub/grub.cfg
grep -Fq -- '--id vkso-time-vkso-update' /boot/grub/grub.cfg

echo "installed_raw_update=/boot/vkso-time-raw-update-5.15.198.bzImage"
echo "installed_vkso_update=/boot/vkso-time-vkso-update-5.15.198.bzImage"
echo "grub_entry_raw_update=vkso-time-raw-update"
echo "grub_entry_vkso_update=vkso-time-vkso-update"
