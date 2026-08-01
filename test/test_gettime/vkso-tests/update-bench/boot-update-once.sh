#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

case "${1:-}" in
raw-normal|vkso-normal|raw-no-retpoline|vkso-no-retpoline)
	case_name=$1
	;;
*)
	echo "usage: $0 {raw-normal|vkso-normal|raw-no-retpoline|vkso-no-retpoline}" >&2
	exit 2
	;;
esac

entry=vkso-update-$case_name
image=/boot/vkso-update-$case_name-5.15.198.bzImage

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
