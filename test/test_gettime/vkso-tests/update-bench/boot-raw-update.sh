#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ -x "$HERE/boot-once.sh" ]]; then
	BOOT_ONCE=$HERE/boot-once.sh
else
	BOOT_ONCE=$HERE/../baremetal/boot-once.sh
fi
exec "$BOOT_ONCE" raw-update
