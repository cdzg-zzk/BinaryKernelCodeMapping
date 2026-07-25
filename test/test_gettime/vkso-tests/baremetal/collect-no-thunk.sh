#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

export PACKAGE=${PACKAGE:-$HERE/artifacts/current-no-thunk}
export CONTROL_DIR=${CONTROL_DIR:-$HERE}
export STATE_FILE=${STATE_FILE:-$HERE/.active-run-id-no-thunk}
exec "$HERE/collect.sh" "$@"
