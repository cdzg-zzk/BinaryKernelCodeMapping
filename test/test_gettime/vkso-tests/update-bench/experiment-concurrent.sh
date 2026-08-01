#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec env EXPERIMENT_SCOPE=concurrent \
	EXPERIMENT_COMMAND=./experiment-concurrent.sh \
	"$HERE/experiment-update.sh" "$@"
