# Section 6.3 experiment design

## Questions

1. How much does a complete exported algorithm cost compared with an ordinary
   user library built from the original Linux algorithm?
2. How does the actual exported owner perform for a kernel consumer compared
   with the distribution implementation?
3. Which differences are associated with source adaptation and which remain
   after controlling source or compiler conditions?

Keep LZ4, BCH and XZ. Section 6.2 isolates dependency mechanisms and performs
adaptation ablations in copied routines. This section executes the real export
owners through actual carriers, then invokes those same owners inside the
kernel. These are distinct experiments even when an algorithm appears in both.

## Versions and denominators

| Domain | Version | Algorithm / dependencies | Compiler conditions |
| --- | --- | --- | --- |
| User | Native DSO | Original 5.15.0-119.129 algorithm; essential Linux API portability only | GCC, O2, PIC, ordinary user optimizations |
| User | Adapted DSO | Owner algorithm rewrites and feature configuration; ordinary user dependencies | Same user options as Native |
| User | VKSO | Actual carrier and resident owner execution pages; domain-local dependencies | Actual owner kernel build |
| Kernel | Stock | Distribution implementation and dependencies | Distribution build |
| Kernel | Matched | Original source, original dependencies and features; module namespace packaging | Owner code-generation options |
| Kernel | Owner | Actual exported implementation, including source and helper adaptations | Actual owner kernel build |

Primary cost ratios: VKSO/Native and Owner/Stock. Auxiliary ratios:
VKSO/Adapted and Owner/Matched. Adapted/Native and Matched/Stock are retained
for explanation. Ratios above one mean slower execution. No cost required by
the mechanism is subtracted from the primary result.

The two intermediate versions answer different questions. User Adapted shares
the algorithm rewrites while keeping ordinary user compilation. Kernel Matched
shares the owner compiler conditions while keeping the original algorithm.
Neither auxiliary ratio isolates page grafting; section 6.1 addresses that.
Matched/Stock also includes module placement/layout and build context.
Cross-domain ratios have different denominators and are not subtracted.

### Portability and adaptations

- LZ4 Native retains original C and `lz4defs.h`; compatibility headers supply
  Linux types and APIs. Both DSOs expose renamed kernel-ABI entry points to
  the same benchmark adapter. Adapted includes export source preparation.
- BCH Native retains original C. Linux API compatibility headers supply user
  allocation and memory operations. Adapted includes the cached syndrome loop
  and relative-address table preparation. The owner additionally uses helper
  slots in its kernel build. Kernel Matched retains the original syndrome loop.
- XZ Native retains original decoder C, all original decoding modes and BCJ
  filters. Its documented user port uses the internal CRC32 fallback.
  Adapted includes the cached dictionary loop, SINGLE/x86 configuration and
  relative-address CRC table. The owner uses the internal CRC implementation
  and domain-local memory-helper slots/ABI bridges. Stock and kernel Matched
  use kernel CRC32 and the original features. The user and kernel native
  references therefore do not have identical CRC dependencies.

Native and Adapted user compilation is `-O2 -g -fPIC -std=gnu11`.
Unlike earlier controls, it does not disable SIMD or builtins. The actual
owner build retains its required kernel restrictions and helper adaptations;
these remain part of total export cost. Build commands and normalized
Owner/Matched compiler comparisons are retained per deployment.

## Workloads and operation boundaries

| Algorithm | Workloads | Timed operation |
| --- | --- | --- |
| LZ4 user | All 12 Silesia files, 211,938,580 B; 4 KiB, 64 KiB, 1 MiB blocks | Official 1.9.3 harness compression/decompression with 2 s windows |
| LZ4 kernel | Same complete corpus; 64 KiB and 1 MiB blocks | Full-file compression/decompression; corpus costs sum each round's file costs |
| BCH | m=13, t=4/8, 512 B, bit swapping disabled; every error count 0..t | Init/free, encode, full decode, precomputed decode separately |
| XZ | Complete bash, Python and libc inputs; x86 BCJ, LZMA2, 1 MiB dictionary, CRC32 | Decoder reset plus full SINGLE-mode stream decode |

BCH precomputed supplies the XOR of corrupted-data ECC and received ECC.
ECC preparation is outside timing; the syndrome argument is NULL, so syndrome
calculation and root finding remain timed. Decode returns error locations;
applying corrections and checking restored codewords occur outside timing.
The same codewords, bit positions and ECC differences are used across all six
versions. Eleven rounds provide eleven error patterns per parameter/error
count. `BCH_CONST_PARAMS` is not enabled in these builds.

Allocation of contexts/workspaces is outside encode/decode timing. Algorithm
reset and necessary per-operation work remain inside. Loading DSOs, registering
carriers, resolving entry points, preparing inputs and checking outputs are
outside algorithm timing. Mandatory helper bridges remain in the measured path.
The registered owner is unchanged between user and kernel phases.

LZ4 user output is the official harness's fastest complete-loop throughput
within each window. Convert it to cost before computing ratios. BCH user uses
process CPU time; kernel collectors time kernel batches and exclude the user
triggering syscall. XZ user samples include twenty complete decodes.

## Repetition and analysis

LZ4/XZ each have three full load/export/register/measure/restore/unload
deployments; BCH has twelve (the original three plus nine fixed follow-up
repetitions), all in one boot on CPU 2. Algorithm deployment order rotates. Backend order
rotates within rounds. User LZ4/XZ use seven rounds; BCH and every kernel
comparison use eleven. BCH and kernel batches target 10 ms.

Pair matching backend measurements within a workload and round. Take the
median ratio within each deployment, then the equal-weight median of the available
deployment medians. Report their minimum–maximum range, not a confidence
interval. Retain raw counters, round ratios and deployment ratios; do not
exclude slow but valid loads or pool iterations as independent deployments.

Completion requires all eighteen deployments, all expected workload cells, correct
outputs, equal BCH inputs, actual owner/API identity, completed registration
and release, and original-source Matched controls. Entry-symbol ranges are
checked against the exported owner mapping. Separate PFN studies retain their
own provenance; an entry-range check is not a per-timing-process PFN sample.

## Analysis stopping rule

Investigate material effects with bounded diagnostics tied to a concrete
hypothesis, using separate runs. Retain unfavorable results. Changes to the
production algorithm need a separate decision; diagnostic variants do not
replace formal measurements. The deliverable is an explained full matrix and
paper evidence, not zero overhead for every workload.

### Bounded diagnostic hypotheses

The first completed BCH and XZ deployments motivate two additional controls,
collected only after the main campaign, with three loads and eleven rounds:

1. **BCH loop:** original Matched versus that same source with only
   `compute_syndromes` replaced by the already adopted cached loop, alongside
   the unchanged Owner. This tests whether the loop rewrite explains the
   precomputed-decode difference under the same kernel compiler conditions.
   The two controls retain direct helpers and original initialization.
2. **XZ CRC:** unchanged Owner versus a kernel-only copy with the CRC body
   delegating to `crc32_le`, alongside Stock. Decoder code, features, helper
   slots and compiler conditions remain the Owner's. This tests the compact
   internal CRC dependency as a source of full-stream overhead. The diagnostic
   variant is not a proposed user export or a replacement primary baseline.

Both reuse full workloads and correctness checks. Their results are stored in
`results/diagnostics/`, separately from formal observations. Each hypothesis receives one three-load diagnostic. The loop control left a
material BCH residual, so one additional helper-slot intervention was collected: cached
original source with direct helpers versus the same source with four helper slots,
alongside Owner. It did not reproduce the residual gain. Collection stops here;
the remaining difference is reported without further optimization experiments.

## Repetition and PMU follow-up

The [fixed follow-up plan](repetition-plan.md) adds nine unchanged-binary BCH
deployments and reports original/additional cohorts separately. The same
within-round pairing and equal-weight load estimator now uses twelve BCH loads.
All original samples remain included. Independent kernel PMU/context crossover
uses three loads and three phases per load; independent user PMU uses three
actual carrier registrations. They execute the complete workload and correctness
matrix, verify event running time, and remain outside the formal time samples.
The report explains material two-error/eight-error differences and retains the
zero-error range without claiming a uniquely identified microarchitectural cause.
