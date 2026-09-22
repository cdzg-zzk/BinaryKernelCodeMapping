# Kernel execution of the current export owners

The [typed registration regression](registration-typed-evidence.md#full-algorithms-with-the-typed-registration-implementation) repeats all three complete current-owner kernel/user workflows with protocol 4; all 2,739 kernel rows and the full setup/task audits pass. The earlier archives below retain their protocol-3 identity and results.

On 2026-09-12, three private exact119 guests ran the complete LZ4, BCH and
XZ workloads through both the registered user carrier and its resident owner.
Each guest built and registered one current owner image, ran the existing user
workflow, then loaded the kernel observer before releasing that registration.
All three sessions passed, including final PFNs, restoration and module unload.
These are functional and collection results; guest timings do not replace the
physical-host algorithm, kernel-cost or application measurements.

| Algorithm | Archive | Full kernel workload | Retained timing rows | Declared source pages |
| --- | --- | --- | ---: | ---: |
| LZ4 | [attempt02](results/lz4-kernel-cost-qemu-20260912-attempt02/result.json) | All 12 Silesia files, 211,938,580 B; 64 KiB and 1 MiB blocks; three backends and 11 rounds | 1,584 | 5 |
| BCH | [attempt01](results/bch-kernel-cost-qemu-20260912-attempt01/result.json) | m=13, t=4/8, 512-byte data; 128 correctness vectors per configuration, every 0..t error count, both decode modes; three backends and 11 measurement rounds | 1,056 | 4 |
| XZ | [attempt03](results/xz-kernel-cost-qemu-20260912-attempt03/result.json) | Complete bash, python3 and libc.so.6 inputs; XZ_SINGLE, CRC32 and x86 BCJ streams; three backends and 11 rounds | 99 | 4 |

The boot IDs are respectively `b80c89b5-5a0f-4b60-9523-bd947a430b4e`,
`94a266e5-f041-4098-91d0-e3d95ccfa76d` and
`06033d22-055d-49fd-9040-54532118fd32`. No host modules or services were loaded.
At most two 4 GiB guests ran concurrently. That concurrency is another reason
these durations are not physical performance evidence.

## Controls and measured work

Each observer imports the public stock kernel APIs, a separate matched-build
control, and the actual owner APIs. Recorded function addresses match the
expected symbols and module providers. LZ4/XZ controls preserve the full current
adapted implementation and all other build settings, selecting normal
compiler-visible memory/allocation helpers instead of helper slots. The same
owner-support metadata is retained. Normal helpers can change inlining and
generated instructions, so this intervention measures binding and compilation
effects together, not the isolated latency of an indirect call.

BCH reuses its [existing complete original-source control and observer](bch-kernel-evidence.md).
Actual compiler argument lists match the owner for every algorithm object after
normalizing only module/API namespaces and build directories. Stock distribution
modules remain separate controls; their instrumentation, optimization and
compiler-package conditions are not claimed to match these builds. Source
snapshots, full LZ4/XZ control patches, build logs, compiler comparisons and
observer imports are retained under each archive's `kernel-cost-build`.

LZ4 and XZ use [the same observer source](kernel-cost/observer.c). File loading,
allocation and result transfer are outside the algorithm timer. The process
writing the control file is pinned to guest CPU 1, and the module runs in that
process's context. It leaves interrupts and preemption enabled, uses
`ktime_get_raw_ns`, and yields between complete passes when another pass is
needed. After a complete warm-up and validation, each row repeats whole-file
work until at least 10 ms has elapsed. Every trial is retained; backend order
rotates across cases and rounds. These 11 rounds belong to one deployment,
not 11 independent deployments or boots.

For LZ4, each compression pass processes all blocks of one full input. Every
decoder consumes the same stock-kernel compressed blocks prepared at LOAD.
Kernel checks validate return lengths, complete decoded bytes, and output and
encoded-buffer guards. The guest independently compares every full decoded
output with the original file and cross-decodes every compressor's blocks
using the installed ordinary `liblz4.so.1`. All 792 trials pass both complete
checks. There are 3,097 timed full-file passes and 1,584 warm-up passes across
the two operations. Full output comparisons run outside the kernel timer.

XZ initializes CRC tables and allocates the decoder outside the timer. Each
pass resets and runs the full decoder, including terminal-state and consumed/
produced-length checks. Full output comparisons and guard checks bracket the
timed loop. The same three prepared compressed files are used by all kernel
backends and the original user benchmark. All 99 trials pass; each performs
one warm-up and one timed decode. The existing user matrix also passes all
882 complete decodes in the same registration.

BCH retains the original driver boundaries: init includes free; encoding,
precomputed decode and full decode are separate; decode verification and bit
restoration are outside the timer. Its 10 ms setting is a calibration target,
not a lower bound on each measured row. The current-owner run passes 10,752
correctness decode checks, 3,588 parity checks and the full 1,056-row matrix.
The archive contains 10,920 vector records covering 1,960 distinct inputs.
The existing user correctness matrix passes in the same owner registration.

## Owner identity and source changes

The manager verifies the owner GNU build ID before staging the registered
carrier. The kernel observers add ordinary module dependencies: owner refcount
is 1 before observer load, 2 while it is active and 1 after observer unload.
The manager then releases the registration, and the original guest flow
verifies fresh mappings and unloads the owner. This sequence ties kernel API
calls and user execution to the same resident owner, while retaining each
domain's own writable state and helpers.

XZ initially had global API symbols but no public module exports for these
five entrypoints. `module_meta.c` now exports init/run/reset/end/CRC-init with
`EXPORT_SYMBOL_GPL`. Its support count changes from 21 to 27 SLOC. All four
algorithm objects' executable sections are byte-identical to the preceding
owner build; [the comparison](results/xz-kernel-cost-qemu-20260912-attempt03/xz-api-export-code-comparison.json)
retains the object identities and section lengths. Algorithm adaptation counts
and the final four-page carrier structure are unchanged.

The full LZ4 six-backend component runner and four-backend CLI workflow also
pass in the fresh-build session: 36 component rows, 192 workflow calls, and
the original 24 input/block functional cases with 48 API-call traces.
Those user and application timings remain diagnostic records.

## Audit and reproduction

[The independent auditor](kernel_cost_audit.py) checks the complete input and
row matrices, backend order, output records, module references, public API
addresses, owner build ID, compiler controls, PFNs and release. Its results
are stored as `kernel-cost-audit.json` in each archive. Full byte comparisons
and independent LZ4 cross-decodes were executed in the guest; the archive
retains per-trial digests and final block tables, not every output blob.
Four mutations of real records reject a missing XZ row, a changed LZ4 input
size, an incorrect provider and a missing BCH vector. The original records
remain unchanged.

```sh
python3 test/evaluation/xz_qemu.py --output test/evaluation/results/xz-kernel-cost-NEW --kernel-cost
python3 test/evaluation/bch_qemu.py --output test/evaluation/results/bch-kernel-cost-NEW --kernel-cost
python3 test/evaluation/lz4_qemu.py --output test/evaluation/results/lz4-kernel-cost-NEW \
  --kernel /tmp/vkso-guest-kernel-119/extracted/boot/vmlinuz-5.15.0-119-generic \
  --initramfs test/evaluation/results/lz4-binding-qemu-20260912-attempt06/initramfs.cpio.gz \
  --kernel-cost
python3 test/evaluation/kernel_cost_audit.py test/evaluation/results/ALGORITHM-kernel-cost-NEW
```

`--kernel-cost` is optional. For LZ4 it selects a fresh current-source owner
build for both domains instead of the supplied prebuilt owner. Existing
launches without this option retain their prior behavior. The private guest
and corpus prerequisites are those of the existing algorithm launchers.

XZ attempt01 and LZ4 attempt01 stopped during observer compilation because
the observer lacked `linux/mm.h`. XZ attempt02 exposed the absent module API
exports at modpost. These are retained preparation failures; none launched a
guest or contributed workload rows. No failed workload was omitted from the
passing matrices.

The [updated cross-case ledger](applicability-ledger-evidence.md) imports these
results and the current source counts. D's fixed candidate, adaptation and
two-domain functional evidence is complete. C still requires physical kernel
cost, independent algorithm deployments and BCH regression diagnosis; E still
requires formal full-workflow performance, and B retains its resource and
source-page boundary work.
