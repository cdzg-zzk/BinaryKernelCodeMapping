#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ $# -gt 0 ]]; then
    exec python3 "$HERE/../direct-api/rebuild.py" --scope update "$@"
fi
BUILD_VARIANT=${BUILD_VARIANT:-normal}
RAW_SOURCE=${RAW_SOURCE:-/tmp/vkso-raw-update-source}
BUILD_ROOT=${BUILD_ROOT:-/tmp/vkso-update-$BUILD_VARIANT-build}

case "$BUILD_VARIANT" in
normal|no-retpoline)
	;;
*)
	echo "BUILD_VARIANT must be normal or no-retpoline" >&2
	exit 2
	;;
esac

OUT=${OUT:-$HERE/../baremetal/artifacts/update-$(date -u +%Y%m%dT%H%M%SZ)-$BUILD_VARIANT}
if [[ -n ${RAW_PACKAGE:-} ]]; then
    python3 "$HERE/stateful.py" verify --package "$RAW_PACKAGE"
fi
env OUT="$OUT" UPDATE_BENCH=1 BUILD_VARIANT="$BUILD_VARIANT" \
	RAW_SOURCE="$RAW_SOURCE" BUILD_ROOT="$BUILD_ROOT" \
	CURRENT_LINK="" \
	"$HERE/../baremetal/build-images.sh" "$@"

python3 "$HERE/../direct-api/bundle.py" --scope update --package "$OUT" --out "$OUT/direct" --cc "${CC:-gcc}"
python3 -B - "$HERE" "$OUT" <<'SEAL'
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from stateful import seal
seal(Path(sys.argv[2]))
SEAL
python3 -B "$HERE/stateful.py" verify --package "$OUT"

ln -sfn "$(realpath "$OUT")" "$HERE/../baremetal/artifacts/current-update-$BUILD_VARIANT"
