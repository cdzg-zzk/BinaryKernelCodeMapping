# VKSO native x86-64 functional matrix

## Contract

The comparison scope is the native x86-64 Linux 5.15.198 vDSO configured
without IA32, x32 and SGX.  VKSO must provide all five native interfaces and
must not regress their observable semantics.  Kernel syscalls and user VKSO
use the same shared implementation where the operation permits it; adapters
may differ for address-space access and fallback.

Canonical user symbols are `__vkso_clock_gettime`, `__vkso_clock_getres`,
`__vkso_gettimeofday`, `__vkso_time` and `__vkso_getcpu`.

Status values:

- `PASS`: verified in the current QEMU baseline.
- `TODO`: mandatory QEMU verification before the implementation is complete.
- `STATIC`: compile/source verification when the required PV/HV runtime is not
  available.

## Baseline and mapping

| ID | Scenario | Required result | Oracle | Status |
|---|---|---|---|---|
| B01 | no-vDSO kernel build | clean x86-64 `bzImage` link | kernel build | PASS |
| B02 | no-vDSO boot | init process reaches userspace | QEMU console | PASS |
| B03 | removed mappings | no `[vdso]`, `[vvar]` or `[vvar_vclock]` | `/proc/self/maps` | PASS |
| B04 | basic syscall time baseline | static BusyBox reads current time successfully | QEMU smoke init | PASS |
| B05 | complete syscall baseline | all five target syscalls pass their argument matrix | direct syscall test | TODO |
| M01 | ELF auxv | no `AT_SYSINFO_EHDR`; `AT_VKSO_MM_DATA=52` is present | `/proc/self/auxv` | PASS |
| M02 | VKSO text mapping | project-mapped code is `R-X`, shared and identical to the kernel code page | maps + project page-map/replace log | PASS |
| M03 | shared-data mapping | project-mapped page is `R--/NX` and has the kernel shared-data page | maps + project page-map/replace log | PASS |
| M04 | MM-data mapping | one per-MM `R--/NX` mapping; address equals auxv value | maps + auxv | PASS |
| M05 | relative layout | text-to-shared RIP displacement equals the kernel displacement | symbol addresses + successful common-core read | PASS |
| M06 | lifecycle | repeated map, execute, restore and process exit leave no stale page mapping | project manager + QEMU | TODO |

## `clock_gettime`

For fast clocks, kernel and user paths call the same VKSO read core.  The
syscall result before/after a VKSO read brackets the VKSO result.  Unsupported
clock IDs use the existing kernel handler from kernel context and a syscall
from user context.

| ID | Clock/scenario | Kernel path | User path | Status |
|---|---|---|---|---|
| C01 | `CLOCK_REALTIME` | VKSO fast core | VKSO fast core | TODO |
| C02 | `CLOCK_MONOTONIC` | VKSO fast core | VKSO fast core | TODO |
| C03 | `CLOCK_MONOTONIC_RAW` | VKSO fast core | VKSO fast core | TODO |
| C04 | `CLOCK_BOOTTIME` | VKSO fast core | VKSO fast core | TODO |
| C05 | `CLOCK_TAI` | VKSO fast core | VKSO fast core | TODO |
| C06 | `CLOCK_REALTIME_COARSE` | VKSO coarse core, no cycle read | same core | PASS |
| C07 | `CLOCK_MONOTONIC_COARSE` | VKSO coarse core, no cycle read | same core | PASS |
| C08 | process/thread CPU clocks | existing POSIX clock handler | syscall fallback | TODO |
| C09 | alarm clocks | existing POSIX clock handler | syscall fallback | TODO |
| C10 | invalid clock ID | `-EINVAL` | syscall-equivalent failure | TODO |
| C11 | monotonicity | no backward value under repeated reads | same | TODO |

## `clock_getres`

| ID | Scenario | Required result | Status |
|---|---|---|---|
| R01 | each C01-C07 clock | matches raw syscall resolution | TODO |
| R02 | CPU/alarm clock | correct fallback result | TODO |
| R03 | invalid clock | `-EINVAL` | TODO |
| R04 | `res == NULL` | valid clock succeeds without a write | TODO |

## `gettimeofday` and `time`

| ID | Scenario | Required result | Status |
|---|---|---|---|
| G01 | `tv != NULL, tz == NULL` | timestamp bracketed by syscalls | TODO |
| G02 | `tv == NULL, tz != NULL` | timezone matches syscall/raw vDSO semantics | TODO |
| G03 | both outputs non-NULL | both values correct from one coherent read | TODO |
| G04 | both outputs NULL | succeeds without an output write | TODO |
| T01 | `time(NULL)` | returned seconds match syscall bracket | TODO |
| T02 | `time(&value)` | return value and stored value are identical | TODO |

## `getcpu`

The signature and NULL-pointer behavior follow native `__vdso_getcpu`.  The
third cache argument is accepted for ABI compatibility and ignored as in the
raw x86 implementation.

| ID | Scenario | Required result | Status |
|---|---|---|---|
| P01 | CPU and node requested | matches `getcpu` syscall on an affinity-pinned thread | TODO |
| P02 | CPU only | succeeds and reports the pinned CPU | TODO |
| P03 | node only | succeeds and matches the syscall node | TODO |
| P04 | both outputs NULL | succeeds without an output write | TODO |
| P05 | multi-vCPU migration | every sample reports a valid current CPU/node pair | TODO |
| P06 | multi-threaded calls | independent concurrent callers remain correct | TODO |

## Time namespaces and MM context

| ID | Scenario | Required result | Status |
|---|---|---|---|
| N01 | root namespace | MM flags indicate zero offsets | PASS |
| N02 | monotonic-coarse offset | `CLOCK_MONOTONIC_COARSE` includes the configured offset | PASS |
| N03 | boottime offset | boottime includes the configured offset | TODO |
| N04 | unaffected clocks | realtime, raw and TAI remain namespace-independent | TODO |
| N05 | fork into child namespace | child receives the correct MM page | PASS |
| N06 | exec in namespace | auxv and MM mapping retain namespace semantics | TODO |
| N07 | `setns`/commit | existing MM data changes to the new frozen offset without stale reads | TODO |
| N08 | frozen offsets | offsets cannot change after a task joins | TODO |

## Counter modes, publication and fallback

| ID | Scenario | Required result | Status |
|---|---|---|---|
| X01 | TSC mode | ordered TSC fast path; no callback/indirect call | TODO |
| X02 | concurrent publisher | seq retry prevents mixed snapshots and backward time | TODO |
| X03 | invalid/disabled counter | both contexts select their non-recursive fallback | TODO |
| X04 | PVClock implementation | raw-compatible reader and data mapping compile into the cold path | STATIC |
| X05 | Hyper-V implementation | raw-compatible reader and TSC page mapping compile into the cold path | STATIC |
| X06 | timezone update | shared timezone is updated coherently without rewriting unrelated MM data | TODO |
| X07 | high-resolution snapshot | mode, cycle conversion and realtime base share one seq generation | PASS |

## Completion rule

The QEMU functional milestone is complete only when every `TODO` row passes on
the clean VKSO tree.  `STATIC` rows may remain runtime-unverified only when the
available QEMU accelerator cannot expose that clock mode; this limitation must
be stated in the result.  QEMU cycle counts are never used as performance
evidence.
