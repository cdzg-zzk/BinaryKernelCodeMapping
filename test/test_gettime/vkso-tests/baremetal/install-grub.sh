#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PACKAGE=${PACKAGE:-$HERE/artifacts/current}
NO_THUNK_PACKAGE=${NO_THUNK_PACKAGE:-$HERE/artifacts/current-no-thunk}
CPU=${CPU:-2}
HOUSEKEEPING_CPUS=${HOUSEKEEPING_CPUS:-0-1,3}
GRUB_SCRIPT=/etc/grub.d/41_vkso_time
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

if [[ $(id -u) -ne 0 ]]; then
	exec sudo --preserve-env=PACKAGE,NO_THUNK_PACKAGE,CPU,HOUSEKEEPING_CPUS \
		"$0" "$@"
fi

validate_package()
{
	local package=$1
	local variant=$2
	local file

	for file in raw-bzImage vkso-bzImage raw.config vkso.config \
		boot-manifest.txt SHA256SUMS; do
		test -s "$package/$file" || {
			echo "missing package artifact: $package/$file" >&2
			exit 1
		}
	done
	(cd "$package" && sha256sum -c SHA256SUMS)
	grep -Fqx "build_variant=$variant" "$package/boot-manifest.txt"
}

validate_package "$PACKAGE" normal
validate_package "$NO_THUNK_PACKAGE" no-thunk

boot_source=$(findmnt -no SOURCE /boot)
root_source=$(findmnt -no SOURCE /)
boot_uuid=$(blkid -s UUID -o value "$boot_source")
root_partuuid=$(blkid -s PARTUUID -o value "$root_source")
test -n "$boot_uuid" -a -n "$root_partuuid"

for target in \
	/boot/vkso-time-raw-5.15.198.bzImage \
	/boot/vkso-time-vkso-5.15.198.bzImage \
	/boot/vkso-time-raw-no-thunk-5.15.198.bzImage \
	/boot/vkso-time-vkso-no-thunk-5.15.198.bzImage \
	/boot/config-vkso-time-raw-5.15.198 \
	/boot/config-vkso-time-vkso-5.15.198 \
	/boot/config-vkso-time-raw-no-thunk-5.15.198 \
	/boot/config-vkso-time-vkso-no-thunk-5.15.198; do
	if [[ -e "$target" ]]; then
		cp -a "$target" "$target.bak.$STAMP"
	fi
done
if [[ -e "$GRUB_SCRIPT" ]]; then
	grub_backup=$GRUB_SCRIPT.bak.$STAMP
	cp -a "$GRUB_SCRIPT" "$grub_backup"
	chmod a-x "$grub_backup"
fi
# update-grub executes every executable file in /etc/grub.d, including an old
# backup with an otherwise harmless suffix.  Keep all backups as data only.
for grub_backup in "$GRUB_SCRIPT".bak.*; do
	[[ -e "$grub_backup" ]] && chmod a-x "$grub_backup"
done

install -m 0644 "$PACKAGE/raw-bzImage" \
	/boot/vkso-time-raw-5.15.198.bzImage
install -m 0644 "$PACKAGE/vkso-bzImage" \
	/boot/vkso-time-vkso-5.15.198.bzImage
install -m 0644 "$PACKAGE/raw.config" \
	/boot/config-vkso-time-raw-5.15.198
install -m 0644 "$PACKAGE/vkso.config" \
	/boot/config-vkso-time-vkso-5.15.198
install -m 0644 "$NO_THUNK_PACKAGE/raw-bzImage" \
	/boot/vkso-time-raw-no-thunk-5.15.198.bzImage
install -m 0644 "$NO_THUNK_PACKAGE/vkso-bzImage" \
	/boot/vkso-time-vkso-no-thunk-5.15.198.bzImage
install -m 0644 "$NO_THUNK_PACKAGE/raw.config" \
	/boot/config-vkso-time-raw-no-thunk-5.15.198
install -m 0644 "$NO_THUNK_PACKAGE/vkso.config" \
	/boot/config-vkso-time-vkso-no-thunk-5.15.198
install -m 0644 "$PACKAGE/boot-manifest.txt" \
	/boot/vkso-time-manifest-5.15.198.txt
install -m 0644 "$NO_THUNK_PACKAGE/boot-manifest.txt" \
	/boot/vkso-time-manifest-no-thunk-5.15.198.txt

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
	echo "menuentry 'VKSO Time: raw 5.15.198' --id vkso-time-raw {"
	echo '	insmod part_gpt'
	echo '	insmod ext2'
	echo "	search --no-floppy --fs-uuid --set=root $boot_uuid"
	echo "	linux /vkso-time-raw-5.15.198.bzImage $common_args"
	echo '}'
	echo
	echo "menuentry 'VKSO Time: VKSO 5.15.198' --id vkso-time-vkso {"
	echo '	insmod part_gpt'
	echo '	insmod ext2'
	echo "	search --no-floppy --fs-uuid --set=root $boot_uuid"
	echo "	linux /vkso-time-vkso-5.15.198.bzImage $common_args"
	echo '}'
	echo
	echo "menuentry 'VKSO Time: raw 5.15.198 (no retpoline/rethunk)' --id vkso-time-raw-no-thunk {"
	echo '	insmod part_gpt'
	echo '	insmod ext2'
	echo "	search --no-floppy --fs-uuid --set=root $boot_uuid"
	echo "	linux /vkso-time-raw-no-thunk-5.15.198.bzImage $common_args"
	echo '}'
	echo
	echo "menuentry 'VKSO Time: VKSO 5.15.198 (no retpoline/rethunk)' --id vkso-time-vkso-no-thunk {"
	echo '	insmod part_gpt'
	echo '	insmod ext2'
	echo "	search --no-floppy --fs-uuid --set=root $boot_uuid"
	echo "	linux /vkso-time-vkso-no-thunk-5.15.198.bzImage $common_args"
	echo '}'
	echo 'EOF'
} >"$GRUB_SCRIPT"
chmod 0755 "$GRUB_SCRIPT"

update-grub
grep -Fq -- '--id vkso-time-raw' /boot/grub/grub.cfg
grep -Fq -- '--id vkso-time-vkso' /boot/grub/grub.cfg
grep -Fq -- '--id vkso-time-raw-no-thunk' /boot/grub/grub.cfg
grep -Fq -- '--id vkso-time-vkso-no-thunk' /boot/grub/grub.cfg
grep -Fq 'nokaslr' /boot/grub/grub.cfg

echo "installed_raw=/boot/vkso-time-raw-5.15.198.bzImage"
echo "installed_vkso=/boot/vkso-time-vkso-5.15.198.bzImage"
echo "installed_raw_no_thunk=/boot/vkso-time-raw-no-thunk-5.15.198.bzImage"
echo "installed_vkso_no_thunk=/boot/vkso-time-vkso-no-thunk-5.15.198.bzImage"
echo "grub_entry_raw=vkso-time-raw"
echo "grub_entry_vkso=vkso-time-vkso"
echo "grub_entry_raw_no_thunk=vkso-time-raw-no-thunk"
echo "grub_entry_vkso_no_thunk=vkso-time-vkso-no-thunk"
echo "backup_stamp=$STAMP"
