#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec env BENCH_SCOPE=update-side \
	STABILIZE_SECONDS="${STABILIZE_SECONDS:-120}" \
	"$HERE/collect-update.sh" "$@"
