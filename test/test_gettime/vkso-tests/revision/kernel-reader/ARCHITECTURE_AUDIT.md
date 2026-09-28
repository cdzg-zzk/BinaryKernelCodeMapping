# Clocktime function-level architecture audit

Scope: Linux 5.15.198 Raw and the VKSO tree derived from `d7ccc5c`. This is
the READ implementation and its required state/namespace lifecycle, not every
timekeeping function in Linux. The classification below assigns each named
function its **primary responsibility**; a callback may also perform a small
amount of conversion. Source size and runtime cost are separate questions.

## Call and state paths

```text
Raw kernel: timekeeper / tk_core.seq
  -> timekeeping_get_ns + ktime_get* normalization -> kernel caller
  -> update_vsyscall -> vvar (separate published representation)
Raw user: libc public API -> native vDSO __vdso_* -> do_hres/do_coarse
  -> vvar; unsupported provider or clock -> syscall -> kernel

VKSO writer: timekeeper -> tk_publish_read_state -> shared read-state page
VKSO kernel fixed-clock reader: ktime_get* -> root hres/coarse adapter
  -> vkso_clock_gettime_* -> vkso_read_hres_time / vkso_read_coarse
  -> shared read-state page; unsupported provider -> fixed kernel callback
  -> vkso_timekeeping_get_private -> timekeeper
VKSO kernel dynamic-clock reader: POSIX dispatcher -> classify once
  -> shared entry + current MM_data, or native k_clock
VKSO user: linked libc-compatible libvkso_time.so API -> carrier private entry
  -> classify once + inject bound MM_data/context -> same shared entry
  -> shared read-state page + namespace MM_data
  -> unsupported provider/native-only clock -> syscall
```

The three `.vkso.text` objects (time core, cold cycle providers, getcpu) are
the shared resident binary. The carrier-private entry and public library are
user-domain adapter code, not a second copy of the time calculation. The Raw
kernel reader and native vDSO `do_hres` are two distinct implementations of
similar cycle/sequence/normalization work. VKSO also changes the publisher and
state layout, so a Raw/VKSO timing delta cannot be credited solely to sharing.

## Function classification

`A` shared algorithm/protocol, `B` kernel adapter, `C` user adapter,
`D` cold fallback, `E` state/mapping/namespace support, `F` thin wrapper.
Functions in the same row have the same classification but are individually
named so none of the reviewed functions is counted by file ownership.

| Function | Class | Reason |
| --- | --- | --- |
| `vkso_read_begin` | A | Start shared sequence snapshot. |
| `vkso_read_retry` | A | Reject mixed generations. |
| `vkso_cycles_read` | A | Read TSC or select cold cycle provider. |
| `vkso_cycle_delta` | A | Compute guarded cycle delta. |
| `vkso_apply_offset` | A | Normalize per-namespace offset. |
| `vkso_read_coarse` | A | Snapshot coarse value with sequence retry. |
| `vkso_shared_data` | A | Locate shared read-state page from shared text. |
| `vkso_read_pvclock_cycles` | A | Cold paravirtual cycle provider. |
| `vkso_read_hvclock_cycles` | A | Cold Hyper-V cycle provider. |
| `vkso_cycles_read_cold` | A | Provider selection; reports unsupported mode. |
| `vkso_finish_hres_cold` | A | Exceptional normalization. |
| `vkso_read_hres_time` | A | Shared cycle conversion, retry and normalization. |
| `vkso_clock_gettime_hres` | A | Select shared base, apply namespace offset, invoke domain callback on provider failure. |
| `vkso_clock_gettime_coarse` | A | Select coarse base and apply namespace offset. |
| `vkso_clock_getres_hres` | A | Shared high-resolution metadata read. |
| `vkso_clock_getres_coarse` | A | Shared coarse resolution. |
| `vkso_gettimeofday_core` | A | Shared realtime calculation and usec conversion. |
| `__vkso_time` | A | Shared realtime-seconds read. |
| `__vkso_getcpu` | A | Shared CPU/node read. |
| `vkso_clock_classify` | B | Dynamic kernel POSIX boundary classifier; user entry implements the same classification in assembly. |
| `vkso_time_get_root_hres` | B | Bind root semantics and fixed kernel callback for known hres clocks. |
| `vkso_time_get_root_coarse` | B | Bind root semantics for known coarse clocks. |
| `posix_clock_gettime_dispatch` | B | Classify dynamic ID; select shared or native `k_clock`. |
| `posix_clock_getres_dispatch` | B | Select shared resolution or native `k_clock`. |
| `vkso_current_mm_data` | B | Resolve current process's namespace page. |
| `vkso_time_get_root_resolution` | B | Read shared resolution for kernel ABI. |
| `vkso_time_get_root_monotonic_seconds` | B | Read shared coarse monotonic seconds. |
| `vkso_time_get_root_realtime_seconds` | B | Read shared realtime seconds. |
| `vkso_time_gettimeofday` | B | Translate kernel timeval pointers to shared ABI. |
| `vkso_getcpu` | B | Bind shared getcpu completion to kernel ABI. |
| `vkso_posix_clock_gettime_failure` | D | Private kernel read and one namespace offset on unsupported provider. |
| `vkso_kernel_gettimeofday_failure` | D | Private realtime read and timezone on unsupported provider. |
| `vkso_timekeeping_get_private` | D | Retained timekeeper path for unsupported provider; distinct from NMI/locked readers. |
| `vkso_user_clock_gettime_failure` | D | User syscall fallback for native ID or provider failure. |
| `vkso_user_gettimeofday_failure` | D | Carrier-private syscall fallback. |
| `vkso_public_gettimeofday_failure` | D | Public errno-preserving syscall fallback. |
| `__vkso_clock_gettime` | C | Classify once, bind MM_data/context, tail-jump to shared reader. |
| `__vkso_clock_getres` | C | Classify once, bind result and tail-jump. |
| `__vkso_gettimeofday` | C | Bind context and tail-jump. |
| `__vkso_bind_context` | C | One-time per-process context setup. |
| `__vkso_bind_gettimeofday_failure` | C | One-time public errno callback setup. |
| `__vkso_shared_data` | C | Expose shared ABI-version address to initializer. |
| `vkso_user_wrapper_init` | C | Validate shared/MM ABI, get auxv mapping, bind carrier. |
| `vkso_time_init` / `initialize` | C | One-time public initialization; precheck auxv before touching carrier. |
| `clock_gettime` / `clock_getres` / `getcpu` | C | Public signature and negative-status-to-errno conversion. |
| `gettimeofday` / `time` | C | IFUNC resolves directly to carrier entry at load time. |
| `public_result` / `public_error` | C | Public errno conversion; cold error part outlined. |
| `resolve_gettimeofday` / `resolve_time` | C | One-time direct carrier binding. |
| `tk_set_read_base` | E | Encode canonical timekeeper base into shared state. |
| `tk_publish_read_state` | E | Publish all bases/cycle metadata under sequence protocol. |
| `vkso_time_set_pvclock_page` / `vkso_time_set_hvclock_page` | E | Maintain kernel provider aliases. |
| `vkso_time_update_timezone` | E | Publish timezone metadata. |
| `vkso_mm_fault` / `vkso_mm_mremap` | E | Fault a read-only MM-data page; reject remap. |
| `vkso_namespace_page` / `vkso_install_mm_mapping` | E | Select and map namespace MM-data backing. |
| `vkso_init_context` / `vkso_dup_mmap` / `vkso_destroy_context` | E | MM-data lifetime across exec/fork/exit. |
| `vkso_time_join_namespace` | E | Switch backing page and invalidate old PTE. |
| `arch_setup_additional_pages` | E | Install MM-data mapping during exec. |
| `timens_freeze_offsets` / `timens_commit` | E | Freeze namespace offsets and switch MM backing. |
| `vkso_time_apply_offset` | F | Out-of-line shared-text bridge to the one `vkso_apply_offset` implementation for cold kernel fallback. |

The ordinary `ktime_get*` functions remain kernel public APIs. They select a
known shared clock and convert the result to their established return type;
their conversion is an ABI obligation, not a second time algorithm. Raw
`timekeeping_get_ns`/`ktime_get*` and vDSO `do_hres`/`do_coarse` are algorithm
implementations on separate sides; `update_vsyscall` publishes vvar state.

## Adapter and fallback decisions

The previous root adapter classified every fixed kernel call and returned a
status, while each caller carried a second private-fallback branch. The prior
commit made the branch dead in generated code. This revision removes that
source-level responsibility split: fixed hres/coarse callers call narrow,
completing root adapters; only dynamic POSIX and user entrypoints classify.
The private fallback is still reached exactly once from the fixed kernel
callback on provider failure. The shared cycle/sequence/normalization and
namespace algorithms, context layout, MM mapping, and carrier ABI are unchanged.

The apparent duplicate auxv lookup in `vkso_time_init` and
`vkso_user_wrapper_init` is deliberate: the first rejects a non-VKSO boot
**before touching carrier text**, while the second validates MM-data and the
shared ABI before binding. Removing either changes failure behavior. The
carrier-private assembly veneers are also necessary because shared text cannot
embed process-local addresses. `vkso_time_apply_offset` is tiny but prevents a
second namespace arithmetic implementation in the cold kernel fallback.

Splitting `vkso_read_hres_time` into additional pure-compute functions would
add calls or invite a second inlined binary, without eliminating state or
domain obligations. No such split is made. Object-size and disassembly checks
can establish code-generation effects; target READ/UPDATE/scalar comparisons
are still needed before claiming latency non-regression.

The older “252 Raw / 592 VKSO kernel reader LOC” numbers were selected source
ranges, not a function-level count of the same responsibilities. In particular,
the VKSO side included a retained private path and integration work, while
Raw's vDSO reader lived outside its kernel-reader range. Do not subtract those
two figures as algorithm LOC. The broader source-change ledger in
`../../code-size/CHANGE_AUDIT.md` separates shared computation, kernel
boundaries, publisher, namespace/mapping, user ABI, and build integration;
its pinned revision also predates this narrow adapter cleanup. A paper table
must recompute a matched-scope ledger at the final evaluated commit.

## Validation of the narrow-adapter revision

The production change is `0e6a5ab`, compared with `d7ccc5c` using GCC 11.4
and real Linux 5.15.198 Kbuild. Normal and no-retpoline configs both passed
the paired object build. All measured function symbol sizes were unchanged;
the disassembled instruction bytes of the eight ordinary hres/coarse
`ktime_get*` functions matched within each variant. Their positions in
`timekeeping.o` changed, so this is not a claim of identical whole-object
layout or physical-machine latency. The three `.vkso.text` payloads were
byte-identical to the base in both variants. Exact build/boot identities and
per-function byte counts are in
[normal](validation/minimal-adapter-normal.json) and
[no-retpoline](validation/minimal-adapter-no-retpoline.json).

The host direct-api/reader/scalar suite passed 74 tests, UPDATE tooling passed
45 tests, and source-audit utilities passed 5 tests. Two minimal QEMU TCG
boots per variant, selecting TSC and jiffies, passed syscall ABI behavior and
produced the required 9 timespec and 15 scalar diagnostic rows per boot. These
VM timings are functional evidence only. Real carrier registration, PFN
sharing, target-machine READ/UPDATE/scalar timing and a candidate package
installed on the NUC are **NOT_RUN** for this revision. The currently running
NUC image is a prior Raw UPDATE kernel; it cannot validate this candidate's
runtime performance. Formal latency non-regression therefore remains open.
