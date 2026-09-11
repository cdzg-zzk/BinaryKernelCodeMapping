#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PACKAGE=${1:?usage: build-tools.sh PACKAGE OUTPUT [PREPARED_KERNEL_BUILD]}
OUT=${2:?output directory required}
mkdir -p "$OUT"
gcc -O2 -std=gnu11 -Wall -Wextra -Werror -fno-omit-frame-pointer \
    -o "$OUT/vkso-multireader" "$HERE/multireader.c" \
    "$HERE/../functional/vkso_user_wrapper.c" \
    -L"$PACKAGE" -Wl,--no-as-needed -lkernel -ldl -Wl,-rpath,'$ORIGIN'
if [[ $# -ge 3 ]]; then
    mkdir -p "$OUT/kernel-reader"
    cp "$HERE/kernel-reader/Makefile" "$HERE/kernel-reader/vkso_kernel_reader.c" \
        "$OUT/kernel-reader/"
    make -C "$3" M="$(realpath "$OUT/kernel-reader")" modules
fi
