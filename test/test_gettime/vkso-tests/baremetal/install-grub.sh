#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
NORMAL_PACKAGE=${NORMAL_PACKAGE:-$HERE/artifacts/final-normal}
NO_RETPOLINE_PACKAGE=${NO_RETPOLINE_PACKAGE:-$HERE/artifacts/final-no-retpoline}
GRUB_SCRIPT=/etc/grub.d/41_vkso_time
# shellcheck disable=SC1091
source "$HERE/experiment.conf"

for package in "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"; do
	for artifact in SHA256SUMS boot-manifest.txt raw-bzImage vkso-bzImage; do
		if [[ ! -s "$package/$artifact" ]]; then
			echo "build is incomplete: $package (missing $artifact)" >&2
			echo "finish ./build-all.sh successfully before installing; no boot files changed" >&2
			exit 1
		fi
	done
done

if [[ $(id -u) -ne 0 ]]; then
	exec sudo --preserve-env=NORMAL_PACKAGE,NO_RETPOLINE_PACKAGE \
		"$0" "$@"
fi

"$HERE/verify-packages.sh" \
	"$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"

boot_source=$(findmnt -no SOURCE -T /boot)
root_source=$(findmnt -no SOURCE -T /)
boot_uuid=$(blkid -s UUID -o value "$boot_source")
root_partuuid=$(blkid -s PARTUUID -o value "$root_source")
test -n "$boot_uuid"
test -n "$root_partuuid"

install_atomic()
{
	local mode=$1
	local source=$2
	local target=$3
	local temporary

	temporary=$target.new.$$

	install -m "$mode" "$source" "$temporary"
	mv "$temporary" "$target"
}

install_atomic 0644 "$NORMAL_PACKAGE/raw-bzImage" \
	/boot/vkso-final-raw-normal-5.15.198.bzImage
install_atomic 0644 "$NORMAL_PACKAGE/vkso-bzImage" \
	/boot/vkso-final-vkso-normal-5.15.198.bzImage
install_atomic 0644 "$NO_RETPOLINE_PACKAGE/raw-bzImage" \
	/boot/vkso-final-raw-no-retpoline-5.15.198.bzImage
install_atomic 0644 "$NO_RETPOLINE_PACKAGE/vkso-bzImage" \
	/boot/vkso-final-vkso-no-retpoline-5.15.198.bzImage

install_atomic 0644 "$NORMAL_PACKAGE/raw.config" \
	/boot/config-vkso-final-raw-normal-5.15.198
install_atomic 0644 "$NORMAL_PACKAGE/vkso.config" \
	/boot/config-vkso-final-vkso-normal-5.15.198
install_atomic 0644 "$NO_RETPOLINE_PACKAGE/raw.config" \
	/boot/config-vkso-final-raw-no-retpoline-5.15.198
install_atomic 0644 "$NO_RETPOLINE_PACKAGE/vkso.config" \
	/boot/config-vkso-final-vkso-no-retpoline-5.15.198
install_atomic 0644 "$NORMAL_PACKAGE/boot-manifest.txt" \
	/boot/vkso-final-normal-manifest-5.15.198.txt
install_atomic 0644 "$NO_RETPOLINE_PACKAGE/boot-manifest.txt" \
	/boot/vkso-final-no-retpoline-manifest-5.15.198.txt

for item in \
	"raw-normal:$NORMAL_PACKAGE/raw-bzImage:/boot/vkso-final-raw-normal-5.15.198.bzImage" \
	"vkso-normal:$NORMAL_PACKAGE/vkso-bzImage:/boot/vkso-final-vkso-normal-5.15.198.bzImage" \
	"raw-no-retpoline:$NO_RETPOLINE_PACKAGE/raw-bzImage:/boot/vkso-final-raw-no-retpoline-5.15.198.bzImage" \
	"vkso-no-retpoline:$NO_RETPOLINE_PACKAGE/vkso-bzImage:/boot/vkso-final-vkso-no-retpoline-5.15.198.bzImage"; do
	IFS=: read -r case_name source target <<<"$item"
	cmp -s "$source" "$target"
	echo "installed_case=$case_name image=$target sha256=$(sha256sum "$target" | awk '{print $1}')"
done

common_args="root=PARTUUID=$root_partuuid rootwait ro nokaslr"
common_args+=" clocksource=tsc tsc=reliable nosmt"
common_args+=" isolcpus=domain,managed_irq,${ISOLATED_CPUS:-$CPU} nohz_full=${ISOLATED_CPUS:-$CPU}"
common_args+=" rcu_nocbs=${ISOLATED_CPUS:-$CPU} irqaffinity=$HOUSEKEEPING_CPUS"
common_args+=" idle=poll intel_pstate=active"
common_args+=" processor.max_cstate=0 intel_idle.max_cstate=0"
common_args+=" nmi_watchdog=0 nowatchdog audit=0"

temporary=$GRUB_SCRIPT.new.$$
{
	echo '#!/bin/sh'
	echo "cat <<'EOF'"
	for item in \
		"raw normal:vkso-final-raw-normal:vkso-final-raw-normal-5.15.198.bzImage" \
		"VKSO normal:vkso-final-vkso-normal:vkso-final-vkso-normal-5.15.198.bzImage" \
		"raw no-retpoline:vkso-final-raw-no-retpoline:vkso-final-raw-no-retpoline-5.15.198.bzImage" \
		"VKSO no-retpoline:vkso-final-vkso-no-retpoline:vkso-final-vkso-no-retpoline-5.15.198.bzImage"; do
		IFS=: read -r title entry image <<<"$item"
		echo "menuentry 'VKSO final: $title' --id $entry {"
		echo '	insmod part_gpt'
		echo '	insmod ext2'
		echo "	search --no-floppy --fs-uuid --set=root $boot_uuid"
		echo "	linux /$image $common_args"
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
for entry in vkso-final-raw-normal vkso-final-vkso-normal \
	vkso-final-raw-no-retpoline vkso-final-vkso-no-retpoline; do
	grep -Fq -- "--id $entry" /boot/grub/grub.cfg
done
sync
echo "grub_installation=pass"
