#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SOURCE=${1:?usage: source-tree-hash.sh SOURCE_TREE}
test -f "$SOURCE/Makefile"

tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 \
	--numeric-owner --exclude=.git -cf - -C "$SOURCE" . |
	sha256sum | awk '{print $1}'
