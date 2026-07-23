#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec "$HERE/boot-once.sh" vkso
