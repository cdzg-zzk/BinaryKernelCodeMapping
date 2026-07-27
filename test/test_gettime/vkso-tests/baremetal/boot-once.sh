#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

case "${1:-}" in
raw-normal)
	entry=vkso-final-raw-normal
	image=/boot/vkso-final-raw-normal-5.15.198.bzImage
	;;
vkso-normal)
	entry=vkso-final-vkso-normal
	image=/boot/vkso-final-vkso-normal-5.15.198.bzImage
	;;
raw-no-retpoline)
	entry=vkso-final-raw-no-retpoline
	image=/boot/vkso-final-raw-no-retpoline-5.15.198.bzImage
	;;
vkso-no-retpoline)
	entry=vkso-final-vkso-no-retpoline
	image=/boot/vkso-final-vkso-no-retpoline-5.15.198.bzImage
	;;
raw-update)
	entry=vkso-time-raw-update
	image=/boot/vkso-time-raw-update-5.15.198.bzImage
	;;
vkso-update)
	entry=vkso-time-vkso-update
	image=/boot/vkso-time-vkso-update-5.15.198.bzImage
	;;
*)
	echo "usage: $0 {raw-normal|vkso-normal|raw-no-retpoline|vkso-no-retpoline|raw-update|vkso-update}" >&2
	exit 2
	;;
esac

if [[ $(id -u) -ne 0 ]]; then
	exec sudo "$0" "$@"
fi

test -s "$image"
grep -Fq -- "--id $entry" /boot/grub/grub.cfg
grub-reboot "$entry"
next_entry=$(grub-editenv /boot/grub/grubenv list |
	awk -F= '$1 == "next_entry" { print $2; exit }')
test "$next_entry" = "$entry" || {
	echo "failed to arm GRUB next_entry: expected $entry, got ${next_entry:-empty}" >&2
	exit 1
}
echo "next_boot_entry=$entry"
sync
systemctl reboot
