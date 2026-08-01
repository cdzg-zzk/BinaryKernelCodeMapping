#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ARTIFACTS=$HERE/../baremetal/artifacts
NORMAL_PACKAGE=${NORMAL_PACKAGE:-$ARTIFACTS/final-update-normal}
NO_RETPOLINE_PACKAGE=${NO_RETPOLINE_PACKAGE:-$ARTIFACTS/final-update-no-retpoline}
GRUB_SCRIPT=/etc/grub.d/42_vkso_time_update
# shellcheck disable=SC1091
source "$HERE/update-experiment.conf"

if [[ $(id -u) -ne 0 ]]; then
	exec sudo --preserve-env=NORMAL_PACKAGE,NO_RETPOLINE_PACKAGE "$0" "$@"
fi

"$HERE/verify-update-packages.sh" \
	"$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"

boot_source=$(findmnt -no SOURCE -T /boot)
root_source=$(findmnt -no SOURCE -T /)
boot_uuid=$(blkid -s UUID -o value "$boot_source")
root_partuuid=$(blkid -s PARTUUID -o value "$root_source")
test -n "$boot_uuid"
test -n "$root_partuuid"

install_atomic()
{
	local mode=$1 source=$2 target=$3 temporary

	temporary=$target.new.$$
	install -m "$mode" "$source" "$temporary"
	mv "$temporary" "$target"
}

for item in \
	"raw-normal:$NORMAL_PACKAGE/raw-bzImage" \
	"vkso-normal:$NORMAL_PACKAGE/vkso-bzImage" \
	"raw-no-retpoline:$NO_RETPOLINE_PACKAGE/raw-bzImage" \
	"vkso-no-retpoline:$NO_RETPOLINE_PACKAGE/vkso-bzImage"; do
	IFS=: read -r case_name source_image <<<"$item"
	install_atomic 0644 "$source_image" \
		"/boot/vkso-update-$case_name-5.15.198.bzImage"
done

for item in \
	"raw-normal:$NORMAL_PACKAGE/raw.config" \
	"vkso-normal:$NORMAL_PACKAGE/vkso.config" \
	"raw-no-retpoline:$NO_RETPOLINE_PACKAGE/raw.config" \
	"vkso-no-retpoline:$NO_RETPOLINE_PACKAGE/vkso.config"; do
	IFS=: read -r case_name source_config <<<"$item"
	install_atomic 0644 "$source_config" \
		"/boot/config-vkso-update-$case_name-5.15.198"
done
install_atomic 0644 "$NORMAL_PACKAGE/boot-manifest.txt" \
	/boot/vkso-update-normal-manifest-5.15.198.txt
install_atomic 0644 "$NO_RETPOLINE_PACKAGE/boot-manifest.txt" \
	/boot/vkso-update-no-retpoline-manifest-5.15.198.txt

for item in \
	"raw-normal:$NORMAL_PACKAGE/raw-bzImage" \
	"vkso-normal:$NORMAL_PACKAGE/vkso-bzImage" \
	"raw-no-retpoline:$NO_RETPOLINE_PACKAGE/raw-bzImage" \
	"vkso-no-retpoline:$NO_RETPOLINE_PACKAGE/vkso-bzImage"; do
	IFS=: read -r case_name source_image <<<"$item"
	target=/boot/vkso-update-$case_name-5.15.198.bzImage
	cmp -s "$source_image" "$target"
	echo "installed_update_case=$case_name image=$target sha256=$(sha256sum "$target" | awk '{print $1}')"
done

common_args="root=PARTUUID=$root_partuuid rootwait ro nokaslr"
common_args+=" clocksource=tsc tsc=reliable nosmt"
common_args+=" isolcpus=domain,managed_irq,$CPU nohz_full=$CPU"
common_args+=" rcu_nocbs=$CPU irqaffinity=$HOUSEKEEPING_CPUS"
common_args+=" idle=poll intel_pstate=active"
common_args+=" processor.max_cstate=0 intel_idle.max_cstate=0"
common_args+=" nmi_watchdog=0 nowatchdog audit=0"

temporary=$GRUB_SCRIPT.new.$$
{
	echo '#!/bin/sh'
	echo "cat <<'EOF'"
	for case_name in raw-normal vkso-normal \
		raw-no-retpoline vkso-no-retpoline; do
		echo "menuentry 'VKSO update: $case_name' --id vkso-update-$case_name {"
		echo '  insmod part_gpt'
		echo '  insmod ext2'
		echo "  search --no-floppy --fs-uuid --set=root $boot_uuid"
		echo "  linux /vkso-update-$case_name-5.15.198.bzImage $common_args"
		echo '}'
		echo
	done
	echo 'EOF'
} >"$temporary"
chmod 0755 "$temporary"
if [[ -e "$GRUB_SCRIPT" ]]; then
	cp -a "$GRUB_SCRIPT" "$GRUB_SCRIPT.previous"
	chmod a-x "$GRUB_SCRIPT.previous"
fi
for backup in "$GRUB_SCRIPT".bak.*; do
	[[ -e "$backup" ]] && chmod a-x "$backup"
done
mv "$temporary" "$GRUB_SCRIPT"

update-grub
for case_name in raw-normal vkso-normal \
	raw-no-retpoline vkso-no-retpoline; do
	grep -Fq -- "--id vkso-update-$case_name" /boot/grub/grub.cfg
done
sync
echo "update_grub_installation=pass"
