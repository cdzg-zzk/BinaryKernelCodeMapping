#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
SOURCE=${1:?usage: prepare-raw-source.sh RAW_KERNEL_SOURCE}
CANONICAL=$ROOT/test/test_gettime/linux-5.15.198-vkso

test -f "$SOURCE/Makefile"
test "$(make -s -C "$SOURCE" kernelversion)" = 5.15.198

if ! grep -q '^config TIMEKEEPING_UPDATE_BENCH$' \
	"$SOURCE/kernel/time/Kconfig"; then
	patch -d "$SOURCE" -p1 <"$HERE/raw-integration.patch"
fi

# An incremental Raw source may already contain the previous two-argument
# hook. Upgrade that exact call without reapplying the integration patch.
python3 - "$SOURCE/kernel/time/timekeeping.c" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
old = 'timekeeping_update_bench_finish(update_bench_start, action);'
new = 'timekeeping_update_bench_finish(update_bench_start, action, tk);'
if old in s:
    p.write_text(s.replace(old, new))
elif new not in s:
    raise SystemExit('missing Raw UPDATE finish hook')
PY

install -m 0644 "$CANONICAL/include/linux/timekeeping_update_bench.h" \
	"$SOURCE/include/linux/timekeeping_update_bench.h"
install -m 0644 "$CANONICAL/kernel/time/timekeeping_update_bench.c" \
	"$SOURCE/kernel/time/timekeeping_update_bench.c"
cmp -s "$CANONICAL/include/linux/timekeeping_update_bench.h" \
	"$SOURCE/include/linux/timekeeping_update_bench.h"
cmp -s "$CANONICAL/kernel/time/timekeeping_update_bench.c" \
	"$SOURCE/kernel/time/timekeeping_update_bench.c"

grep -Fq 'timekeeping_update_bench_start()' \
	"$SOURCE/kernel/time/timekeeping.c"
grep -Fq 'timekeeping_update_bench.o' "$SOURCE/kernel/time/Makefile"
grep -Fq 'config TIMEKEEPING_UPDATE_BENCH' "$SOURCE/kernel/time/Kconfig"
