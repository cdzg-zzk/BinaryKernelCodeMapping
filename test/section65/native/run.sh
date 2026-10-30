#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
export PATH="$PWD/bin:$PATH"
export LD_LIBRARY_PATH="$PWD${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
if [[ $EUID -ne 0 ]]; then
    echo 'Run: sudo bash run.sh --output /absolute/path/to/new-result-directory' >&2
    exit 1
fi
exec unshare --mount --propagation private python3 ./run.py "$@"
