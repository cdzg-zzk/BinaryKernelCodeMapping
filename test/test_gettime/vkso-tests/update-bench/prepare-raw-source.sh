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

# An incremental Raw source may already contain the earlier complete-update
# recorder. Upgrade only its known hook locations, keeping the source cache.
python3 - "$SOURCE/kernel/time/Kconfig" "$SOURCE/kernel/time/timekeeping.c" <<'PY'
from pathlib import Path
import sys
config, source = map(Path, sys.argv[1:])
k = config.read_text()
if 'config TIMEKEEPING_UPDATE_STAGE_DIAG\n' not in k:
    marker = 'if GENERIC_CLOCKEVENTS\n'
    assert k.count(marker) == 1, 'unexpected Raw Kconfig layout'
    k = k.replace(marker, '''config TIMEKEEPING_UPDATE_STAGE_DIAG
\tbool "Timekeeping update stage diagnosis"
\tdepends on TIMEKEEPING_UPDATE_BENCH
\thelp
\t  Add ordered TSC timestamps between timekeeping_update() stages for
\t  standalone diagnosis. Keep this disabled in formal UPDATE kernels:
\t  the extra timestamps perturb the complete writer latency.

''' + marker)
    config.write_text(k)
k = config.read_text()
if 'config TIMEKEEPING_UPDATE_CACHE_PREP_DIAG\n' not in k:
    marker = 'if GENERIC_CLOCKEVENTS\n'
    assert k.count(marker) == 1, 'unexpected Raw Kconfig layout'
    k = k.replace(marker, '''config TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
\tbool "Timekeeping update cache-preparation diagnosis"
\tdepends on TIMEKEEPING_UPDATE_BENCH
\thelp
\t  Permit controlled cache-line preparation immediately before UPDATE
\t  timing. This is for standalone diagnosis, not formal measurements.

''' + marker)
    config.write_text(k)
k = config.read_text()
if 'config TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG\n' not in k:
    marker = 'if GENERIC_CLOCKEVENTS\n'
    assert k.count(marker) == 1, 'unexpected Raw Kconfig layout'
    k = k.replace(marker, '''config TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
\tbool "Timekeeping update per-call RFO diagnosis"
\tdepends on TIMEKEEPING_UPDATE_BENCH && PERF_EVENTS
\tdepends on !TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
\thelp
\t  Count CPU-local RFO hits and misses around each complete UPDATE
\t  without placing counter reads inside its timed body. Diagnosis only.

''' + marker)
    config.write_text(k)
s = source.read_text()
function_start = s.index('static void timekeeping_update(struct timekeeper *tk, unsigned int action)')
function_end = s.index('\n/**\n * timekeeping_forward_now', function_start)
before, body, after = s[:function_start], s[function_start:function_end], s[function_end:]
old_finish = 'timekeeping_update_bench_finish(update_bench_start, action);'
if old_finish in body:
    assert body.count(old_finish) == 1
    body = body.replace(old_finish,
        'timekeeping_update_bench_finish(update_bench_start, action, tk);')
if 'UPDATE_BENCH_MARK(0);' not in body:
    replacements = (
        ('u64 update_bench_start = timekeeping_update_bench_start();\n',
         '''u64 update_bench_start = timekeeping_update_bench_start();
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
\tstruct timekeeping_update_bench_stages update_bench_stages;
#define UPDATE_BENCH_MARK(part) timekeeping_update_bench_stage_mark(&update_bench_stages, part)
#define UPDATE_BENCH_STAGES (&update_bench_stages)
#else
#define UPDATE_BENCH_MARK(part) do { } while (0)
#define UPDATE_BENCH_STAGES NULL
#endif
'''),
        ('\ttk_update_leap_state(tk);\n',
         '\ttk_update_leap_state(tk);\n\tUPDATE_BENCH_MARK(0);\n'),
        ('\ttk_update_ktime_data(tk);\n',
         '\ttk_update_ktime_data(tk);\n\tUPDATE_BENCH_MARK(1);\n'),
        ('\tupdate_vsyscall(tk);\n',
         '\tupdate_vsyscall(tk);\n\tUPDATE_BENCH_MARK(2);\n'),
        ('\tupdate_pvclock_gtod(tk, action & TK_CLOCK_WAS_SET);\n',
         '\tupdate_pvclock_gtod(tk, action & TK_CLOCK_WAS_SET);\n\tUPDATE_BENCH_MARK(3);\n'),
        ('\ttk->tkr_mono.base_real = tk->tkr_mono.base + tk->offs_real;\n',
         '\ttk->tkr_mono.base_real = tk->tkr_mono.base + tk->offs_real;\n\tUPDATE_BENCH_MARK(4);\n'),
        ('\tupdate_fast_timekeeper(&tk->tkr_mono, &tk_fast_mono);\n',
         '\tupdate_fast_timekeeper(&tk->tkr_mono, &tk_fast_mono);\n\tUPDATE_BENCH_MARK(5);\n'),
        ('\tupdate_fast_timekeeper(&tk->tkr_raw,  &tk_fast_raw);\n',
         '\tupdate_fast_timekeeper(&tk->tkr_raw,  &tk_fast_raw);\n\tUPDATE_BENCH_MARK(6);\n'),
        ('timekeeping_update_bench_finish(update_bench_start, action, tk);\n',
         '''timekeeping_update_bench_finish(update_bench_start, action, tk,
\t\t\t\t\tUPDATE_BENCH_STAGES);
#undef UPDATE_BENCH_MARK
#undef UPDATE_BENCH_STAGES
'''),
    )
    for old, new in replacements:
        assert body.count(old) == 1, 'unexpected Raw UPDATE hook: '+old.strip()
        body = body.replace(old, new, 1)
if 'timekeeping_update_bench_prepare(&tk_fast_raw);' not in body:
    old = '\tu64 update_bench_start = timekeeping_update_bench_start();'
    assert body.count(old) == 1, 'unexpected Raw UPDATE start hook'
    body = body.replace(old, '''#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
\tu64 update_bench_start;
#else
\tu64 update_bench_start = timekeeping_update_bench_start();
#endif''', 1)
    marker = '\n\tif (action & TK_CLEAR_NTP) {'
    assert body.count(marker) == 1, 'unexpected Raw UPDATE body'
    body = body.replace(marker, '''
#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
	BUILD_BUG_ON(L1_CACHE_BYTES != 64);
	BUILD_BUG_ON(sizeof(tk_fast_raw) < 68);
	timekeeping_update_bench_prepare(&tk_fast_raw);
	update_bench_start = timekeeping_update_bench_start();
#endif
''' + marker, 1)
if 'timekeeping_update_bench_pmu_before(&update_bench_pmu_before);' not in body:
    old = '''#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
	u64 update_bench_start;
#else
	u64 update_bench_start = timekeeping_update_bench_start();
#endif'''
    new = '''#if defined(CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG) || \\
	defined(CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG)
	u64 update_bench_start;
#else
	u64 update_bench_start = timekeeping_update_bench_start();
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
	struct timekeeping_update_bench_pmu_snapshot update_bench_pmu_before;
#endif'''
    assert body.count(old) == 1, 'unexpected Raw diagnostic declaration'
    body = body.replace(old, new, 1)
    old = '''	timekeeping_update_bench_prepare(&tk_fast_raw);
	update_bench_start = timekeeping_update_bench_start();
#endif'''
    new = '''	timekeeping_update_bench_prepare(&tk_fast_raw);
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
	timekeeping_update_bench_pmu_before(&update_bench_pmu_before);
#endif
#if defined(CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG) || \\
	defined(CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG)
	update_bench_start = timekeeping_update_bench_start();
#endif'''
    assert body.count(old) == 1, 'unexpected Raw diagnostic start'
    body = body.replace(old, new, 1)
    old = '''	timekeeping_update_bench_finish(update_bench_start, action, tk,
					UPDATE_BENCH_STAGES);'''
    new = '''#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
	timekeeping_update_bench_pmu_finish(update_bench_start, action, tk,
					UPDATE_BENCH_STAGES,
					&update_bench_pmu_before);
#else
''' + old + '''
#endif'''
    assert body.count(old) == 1, 'unexpected Raw diagnostic finish'
    body = body.replace(old, new, 1)
if 'const struct tk_read_base *first_tkr' not in body:
    old = '''#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
\tstruct timekeeping_update_bench_stages update_bench_stages;'''
    new = '''#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
\tconst struct tk_read_base *first_tkr = &tk->tkr_mono;
\tconst struct tk_read_base *second_tkr = &tk->tkr_raw;
\tstruct tk_fast *first_fast = &tk_fast_mono;
\tstruct tk_fast *second_fast = &tk_fast_raw;
#endif
''' + old
    assert body.count(old) == 1, 'unexpected Raw order declaration anchor'
    body = body.replace(old, new, 1)
    old = '''\ttimekeeping_update_bench_prepare(&tk_fast_raw);
#endif'''
    new = '''\ttimekeeping_update_bench_prepare(&tk_fast_raw);
\tif (static_branch_unlikely(&timekeeping_update_bench_order_swap_key)) {
\t\tfirst_tkr = &tk->tkr_raw;
\t\tsecond_tkr = &tk->tkr_mono;
\t\tfirst_fast = &tk_fast_raw;
\t\tsecond_fast = &tk_fast_mono;
\t}
#endif'''
    assert body.count(old) == 1, 'unexpected Raw order setup anchor'
    body = body.replace(old, new, 1)
    old_order = '''#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
\tif (static_branch_unlikely(&timekeeping_update_bench_order_swap_key)) {
\t\tupdate_fast_timekeeper(&tk->tkr_raw, &tk_fast_raw);
\t\tUPDATE_BENCH_MARK(5);
\t\tupdate_fast_timekeeper(&tk->tkr_mono, &tk_fast_mono);
\t} else
#endif
\t{
\t\tupdate_fast_timekeeper(&tk->tkr_mono, &tk_fast_mono);
\t\tUPDATE_BENCH_MARK(5);
\t\tupdate_fast_timekeeper(&tk->tkr_raw,  &tk_fast_raw);
\t}
\tUPDATE_BENCH_MARK(6);'''
    old_normal = '''\tupdate_fast_timekeeper(&tk->tkr_mono, &tk_fast_mono);
\tUPDATE_BENCH_MARK(5);
\tupdate_fast_timekeeper(&tk->tkr_raw,  &tk_fast_raw);
\tUPDATE_BENCH_MARK(6);'''
    new = '''#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
\tupdate_fast_timekeeper(first_tkr, first_fast);
\tUPDATE_BENCH_MARK(5);
\tupdate_fast_timekeeper(second_tkr, second_fast);
#else
\tupdate_fast_timekeeper(&tk->tkr_mono, &tk_fast_mono);
\tUPDATE_BENCH_MARK(5);
\tupdate_fast_timekeeper(&tk->tkr_raw, &tk_fast_raw);
#endif
\tUPDATE_BENCH_MARK(6);'''
    old = old_order if old_order in body else old_normal
    assert body.count(old) == 1, 'unexpected Raw fast-publisher pair'
    body = body.replace(old, new, 1)
updated = before + body + after
if updated != s:
    source.write_text(updated)
assert body.count('UPDATE_BENCH_MARK(') == 10, 'incomplete Raw stage hooks'
assert 'timekeeping_update_bench_finish(update_bench_start, action, tk,\n' in body
PY

for item in include/linux/timekeeping_update_bench.h \
		kernel/time/timekeeping_update_bench.c; do
	if ! cmp -s "$CANONICAL/$item" "$SOURCE/$item"; then
		install -m 0644 "$CANONICAL/$item" "$SOURCE/$item"
	fi
done
cmp -s "$CANONICAL/include/linux/timekeeping_update_bench.h" \
	"$SOURCE/include/linux/timekeeping_update_bench.h"
cmp -s "$CANONICAL/kernel/time/timekeeping_update_bench.c" \
	"$SOURCE/kernel/time/timekeeping_update_bench.c"

grep -Fq 'timekeeping_update_bench_start()' \
	"$SOURCE/kernel/time/timekeeping.c"
grep -Fq 'timekeeping_update_bench.o' "$SOURCE/kernel/time/Makefile"
grep -Fq 'config TIMEKEEPING_UPDATE_BENCH' "$SOURCE/kernel/time/Kconfig"
