# Registration scale and transaction resource observations

Current update: [typed admission](registration-typed-evidence.md) repeats all
96 sessions with protocol 4 and 64 B bindings (688+64N B live requests).
The earlier protocol-3 results below retain their 56 B layout.

Previous update: [manager retirement](registration-retirement-evidence.md)
passes the same 96-session matrix in attempt02. The 48 manager sessions now
send FORGET before DONE and retain no transaction record afterward. Direct
protocol sessions still perform their explicit final FORGET. Active object
sizes remain unchanged; the new manager smaps RSS is 1,532–1,548 KiB. The
following attempt01 observations retain their earlier manager identity.

[The scale run](results/registration-scale-qemu-20260912-attempt01/result.json)
passes in boot `ca2ae91f-316a-4030-9584-26604b165b06` on exact119 KVM.
The [independent reconstruction](results/registration-scale-qemu-20260912-attempt01/independent-audit.json)
checks all 96 sessions and writes [the raw measurement table](results/registration-scale-qemu-20260912-attempt01/scale-raw.csv).
The full current manager and page module are unchanged. The source fixture
provides distinct resident pages and never executes them as an algorithm.

## Matrix and measurement boundaries

The matrix is 1/2/4/8/16/32 pages × two target-cache conditions × two control
paths × four repetitions. A fixed seed shuffles the 24 combinations within
each repetition. The controller and its manager children are pinned to guest
CPU 1; all wall timestamps use CLOCK_MONOTONIC_RAW. Repetitions share one boot
and the same owner/module deployment.

The manager path uses the actual identity checks, durable recovery state,
file protection, complete plan, FIFO READY and release/DONE notification.
The direct path issues the real v3 BEGIN/STAGE/COMMIT/RELEASE requests to the
same kernel implementation, measuring transport and engine behavior. It does
not implement manager identity verification, immutable flags or persistence
and is not a substitute full deployment. All these sizes use one STAGE batch
and one owner. The earlier 300-page matrix supplies transport-boundary
functional coverage; this scan does not isolate batch count or owner count.

Each target file is newly created and fsynced. The prepared condition reads
all selected ordinary file pages. The evicted condition applies page-aligned
POSIX_FADV_DONTNEED to that file only. Before timing, mincore reports all
selected pages present or all absent, respectively, without faulting them.
This confirms the realized conditions rather than assuming that a successful
advice call evicts pages. Dirty-page handling and advisory semantics follow
the [Linux posix_fadvise documentation](https://man7.org/linux/man-pages/man2/posix_fadvise.2.html);
[mincore supplies a residency snapshot](https://man7.org/linux/man-pages/man2/mincore.2.html).
These are target-file cache controls, not claims of a cold machine or a
memory-pressure workload.

Each session compares every selected active user PFN with the corresponding
source PFN. After release, every page contains its original bytes and every
new user PFN differs from the source. The scan verifies 1,008 active and 1,008
restored page mappings. Source-owner references return to zero, the transport
reference returns to its recorded baseline, and all test modules unload.

Kernel prepare/apply times are read from COMMIT; release time is read from
RELEASE. Cumulative prepare/apply fields are not added again from RELEASE.
Manager wall time ends at observed READY, while release wall time ends at DONE.
The intervening PFN/process inspection is outside both intervals. Full raw
response and notification sequences remain available per session.

## Resource observations

The executed module's type layout and allocating source give these allocation
**requests**, excluding allocator metadata and unused slab capacity:

| Selected pages | Transaction object (B) | Binding array (B) | Live total requested (B) |
| ---: | ---: | ---: | ---: |
| 1 | 688 | 56 | 744 |
| 2 | 688 | 112 | 800 |
| 4 | 688 | 224 | 912 |
| 8 | 688 | 448 | 1,136 |
| 16 | 688 | 896 | 1,584 |
| 32 | 688 | 1,792 | 2,480 |

After RELEASE, QUERY still finds a RESTORED transaction with zero applied
bindings. Source inspection shows its binding array is freed while the
688-byte transaction record remains. The experiment then explicitly sends
FORGET and verifies QUERY returns ENOENT. It does this for both paths after
timing, preventing retained records from accumulating across the scan.
The manager used in attempt01 did not send FORGET, so its completed
sessions retain these records until registration-module unload. Removing the
record in this experiment is not evidence that production cleanup does so.
This footprint must be counted separately from active owner/source references.

During the 48 manager sessions, smaps_rollup reports RSS 1,540–1,560 KiB and
PSS 1,537–1,557 KiB. The simultaneously archived status VmRSS counter ranges
from 4 to 1,156 KiB and is not used as the accurate resident total. Linux
[documents this counter's inaccuracy and the smaps alternatives](https://man7.org/linux/man-pages/man5/proc_pid_statm.5.html).
Manager maps, both memory snapshots and all six open descriptor targets are
saved for each session. FIFO capacity is 65,536 bytes; capacity does not
establish that 65,536 bytes of physical pipe-buffer memory are resident.
These process, capacity and allocation-request quantities are separate scopes,
not additive physical page totals.

A 30-launch clock-helper calibration in the same guest/CPU has median external
elapsed time 435,146.5 ns. The shell helper is not invoked inside this scan's
manager or direct intervals, so this value is not subtracted from them. The
calibration describes the optional shell-stage observer used by the earlier
setup collector, with raw events and enclosing intervals retained. It does
not calibrate every observer or provide an uninstrumented algorithm total.

## Scope of the result

The full 1..32-page collection path, cache controls, PFN/release observations
and dynamic-record accounting have been exercised. Guest durations describe
these sessions and remain outside formal physical-host performance tables.
Physical slab-page accounting, file/socket/pipe infrastructure, complete
manager/owner support, matched ordinary-DSO setup totals and uninstrumented
observer comparisons remain group B work. Unfiltered first-touch and memory
pressure are separate experiments.
