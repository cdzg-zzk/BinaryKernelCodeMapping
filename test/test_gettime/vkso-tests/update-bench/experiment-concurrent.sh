#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# Compatibility entry: concurrent load is a phase of the full campaign.
exec "$HERE/experiment-update.sh" "$@"
