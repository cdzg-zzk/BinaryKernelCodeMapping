#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
# Collection must use the campaign's frozen config/package/tool identity.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec "$HERE/experiment-update.sh" collect "$@"
