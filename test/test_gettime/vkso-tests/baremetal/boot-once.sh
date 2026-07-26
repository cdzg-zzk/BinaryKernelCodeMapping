#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

case "${1:-}" in
raw)
	entry=vkso-time-raw
	image=/boot/vkso-time-raw-5.15.198.bzImage
	;;
vkso)
	entry=vkso-time-vkso
	image=/boot/vkso-time-vkso-5.15.198.bzImage
	;;
raw-no-thunk)
	entry=vkso-time-raw-no-thunk
	image=/boot/vkso-time-raw-no-thunk-5.15.198.bzImage
	;;
vkso-no-thunk)
	entry=vkso-time-vkso-no-thunk
	image=/boot/vkso-time-vkso-no-thunk-5.15.198.bzImage
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
	echo "usage: $0 {raw|vkso|raw-no-thunk|vkso-no-thunk|raw-update|vkso-update}" >&2
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
if [[ "$next_entry" != "$entry" ]]; then
	echo "failed to arm GRUB next_entry: expected $entry, got ${next_entry:-empty}" >&2
	exit 1
fi
echo "next_boot_entry=$entry"
sync
systemctl reboot
