#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

case "${1:-}" in
raw)
	entry=vkso-time-raw
	;;
vkso)
	entry=vkso-time-vkso
	;;
raw-no-thunk)
	entry=vkso-time-raw-no-thunk
	;;
vkso-no-thunk)
	entry=vkso-time-vkso-no-thunk
	;;
*)
	echo "usage: $0 {raw|vkso|raw-no-thunk|vkso-no-thunk}" >&2
	exit 2
	;;
esac

if [[ $(id -u) -ne 0 ]]; then
	exec sudo "$0" "$@"
fi

test -s /boot/vkso-time-raw-5.15.198.bzImage
test -s /boot/vkso-time-vkso-5.15.198.bzImage
test -s /boot/vkso-time-raw-no-thunk-5.15.198.bzImage
test -s /boot/vkso-time-vkso-no-thunk-5.15.198.bzImage
grep -Fq -- "--id $entry" /boot/grub/grub.cfg

grub-reboot "$entry"
echo "next_boot_entry=$entry"
sync
systemctl reboot
