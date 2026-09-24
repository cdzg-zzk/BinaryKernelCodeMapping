#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ $# -gt 0 ]]; then
    exec python3 "$HERE/../direct-api/rebuild.py" --scope update "$@"
fi
BUILD_VARIANT=${BUILD_VARIANT:-normal}
SOURCE_CACHE=$HERE/../baremetal/artifacts/source-cache
RAW_SOURCE=${RAW_SOURCE:-$SOURCE_CACHE/raw-5.15.198-update}
RAW_TARBALL=${RAW_TARBALL:-$SOURCE_CACHE/linux-5.15.198.tar.xz}
BUILD_ROOT=${BUILD_ROOT:-/tmp/vkso-update-$BUILD_VARIANT-build}
RAW_TARBALL_SHA256=5d4c0994580dd3bbd5ffc5fcb81c22dd305b844c9d8c7b176cc41b28f7e29743

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
elif [[ ! -f "$RAW_SOURCE/Makefile" ]]; then
    if [[ -e "$RAW_SOURCE" ]]; then
        echo "incomplete Raw source directory: $RAW_SOURCE" >&2
        echo 'inspect it before choosing a different RAW_SOURCE; no files were removed' >&2
        exit 1
    fi
    if [[ ! -s "$RAW_TARBALL" ]]; then
        command -v curl >/dev/null || {
            echo 'curl is required to fetch the official Linux 5.15.198 source' >&2
            exit 1
        }
        mkdir -p "$(dirname "$RAW_TARBALL")"
        download_tmp=$(mktemp "$RAW_TARBALL.part.XXXXXXXX")
        trap 'rm -f -- "$download_tmp"' EXIT
        curl --fail --location --retry 3 --retry-delay 2 --connect-timeout 15 \
            --output "$download_tmp" \
            'https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.15.198.tar.xz'
        printf '%s  %s\n' "$RAW_TARBALL_SHA256" "$download_tmp" | sha256sum -c -
        mv -- "$download_tmp" "$RAW_TARBALL"
        trap - EXIT
    fi
    printf '%s  %s\n' "$RAW_TARBALL_SHA256" "$RAW_TARBALL" | sha256sum -c -
    mkdir -p "$(dirname "$RAW_SOURCE")"
    source_tmp=$(mktemp -d "$RAW_SOURCE.part.XXXXXXXX")
    trap 'rm -rf -- "$source_tmp"' EXIT
    tar -xf "$RAW_TARBALL" -C "$source_tmp" --strip-components=1
    [[ $(make -s -C "$source_tmp" kernelversion) == 5.15.198 ]] || {
        echo 'downloaded Raw source is not Linux 5.15.198' >&2
        exit 1
    }
    mv -T -- "$source_tmp" "$RAW_SOURCE"
    trap - EXIT
fi
env OUT="$OUT" UPDATE_BENCH=1 BUILD_VARIANT="$BUILD_VARIANT" \
	RAW_SOURCE="$RAW_SOURCE" RAW_TARBALL="$RAW_TARBALL" BUILD_ROOT="$BUILD_ROOT" \
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
