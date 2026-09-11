# Collection observations

These notes document observed evidence and interpretation constraints. They do
not change the frozen collection or remove any samples. The campaign remains
in progress; these are not final multi-boot performance conclusions.

## Ordinary kernel reader targets

The supplied VKSO `kernel/time/timekeeping.c` routes `ktime_get_ts64()`,
`ktime_get_raw_ts64()` and `ktime_get_coarse_ts64()` through
`vkso_time_get_root()` for monotonic, raw and coarse clocks respectively. These
are the three actual exported APIs called by the new test module. The module
therefore exercises the ordinary kernel entry paths into the adapted time
implementation, including their entry/fallback logic, rather than timing a
standalone arithmetic substitute.

## First Raw and VKSO UPDATE measurements

Audited on 2026-09-11 between the VKSO measurement and its code-copy comparison:

| Check | Raw, step-002 | VKSO, step-003/vkso |
| --- | ---: | ---: |
| Writer windows | 285 | 285 |
| Recorded writer samples | 926,261 | 926,282 |
| Recorder drops | 0 | 0 |
| Header `seen` / row-count mismatches | 0 | 0 |
| Nonzero-action samples | 0 | 0 |
| Concurrent workload windows | 270 | 270 |
| Reader/writer overlap violations | 0 | 0 |
| Fixed-rate late batches | 0 | 0 |
| Achieved fixed rate, calls/s/reader | 999,997.925–1,000,003.218 | 999,997.070–1,000,002.506 |

The full CSV audit found all Raw writer samples on CPU 0. VKSO had 926,277
samples on CPU 0, four on CPU 2 and one on CPU 1. The five other-CPU records are
retained in the formal data. Their locations within `step-003/vkso/` are:

- `monotonic/readers-2/rate-0/round-00-writer.csv`
- `monotonic/readers-2/rate-0/round-02-writer.csv`
- `monotonic/readers-2/rate-0/round-12-writer.csv`
- `monotonic_raw/readers-2/rate-0/round-04-writer.csv`
- `monotonic_coarse/readers-1/rate-0/round-10-writer.csv`

CPU 0 is the intended housekeeping/timekeeper CPU, but collection configuration
does not prove every observed update ran there. The final report must use the
recorded CPU distribution, retain these samples in the main analysis, and check
their influence separately if interpreting small writer differences.

`action == 0` is the existing writer analysis filter. It does **not** uniquely
identify a periodic tick caller. In the supplied kernel's
`kernel/time/timekeeping.c`, `timekeeping_advance()` calls
`timekeeping_update(tk, clock_set)`, and both `update_wall_time()` (TK_ADV_TICK)
and frequency/tick changes through `do_adjtimex()` (TK_ADV_FREQ) can reach
`timekeeping_advance()`. The recorder has no caller-mode field. The five records'
specific origins have not been established; do not infer an NTP cause merely
from their CPUs, or describe all action-zero samples as proven tick-only
updates. No implementation or recorder change is required to report the
observed stratum accurately.

## Startup diagnostic versus runtime WARN/oops

The completed Raw boot's log includes the early message
`process: WARNING: polling idle and HT enabled, performance may degrade`.
`arch/x86/kernel/process.c:select_idle_routine()` prints it when polling idle is
selected and `smp_num_siblings > 1`; it is a `pr_warn_once`, not a WARN_ON.
The actual recorded topology is four online CPUs, four cores and one thread per
core, and runtime `smt/active` is zero. Keep the log and topology evidence;
substring matching `WARNING:` alone is insufficient to classify this as a
runtime kernel fault. The collector separately rejects the kernel's WARN/oops
taint bits. No kernel code was changed to suppress the diagnostic.
