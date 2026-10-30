# Section 6.5 optimization: finite development and confirmation

This is a new implementation version, not a relabeling of the 30-campaign
common-XZ baseline. Historical outputs, manuscripts and failures remain intact.
Current candidate: common XZ `dict_repeat` word copying, unchanged baseline
compiler/hardening policy, plus private bounded inode/name retention.

## Mechanisms and limits

The fixed original SIF blocks identify dictionary repetition as the compressible
stream hotspot, while Python data is dominated by the range-decoder main loop.
Jump tables, small constant service operations and O3 did not show consistent
benefits and are not selected. The word-copy edit is common to native and user
execution; it changes an upstream algorithm body and must be charged as such.
Matching ordinary-user CRC avoids falsely attributing software-CRC cost to
preparation. Block timings do not establish application effects.

The private cache retains 2048 inodes / 4096 positive names, with explicit root
and open-handle pinning. Names use stable image-local inode numbers and disk
locations. Bounds exclude active pinned handles and per-open-directory listings;
they are not a universal fixed-runtime-memory assertion. Eviction preserves
hardlinks, directory cursors, reads and xattrs in the valid-image tests. Those
tests do not replace full shared-PFN/application/native/resource checks.

## Development tests, fixed before application sampling

1. Independent word-copy owner: guest native/copied/shared repaired-negative
   and five-format regressions; original flags and dependencies checked.
2. Cache candidate: 8192-file valid-image API churn, 2400 pinned handles,
   ASAN/UBSAN private adapter, real FUSE retained files/directory cursors;
   then the same isolated guest regression. Completed evidence is individually
   recorded; sanitizer core instrumentation and leak-check limits are explicit.
3. Two ordinary native references receive the identical word-copy body in their
   native kernel environment. Existing normal/relaxed policies remain separate.
   Guest five-format validation precedes loading them on the host.
4. Final candidate host valid-image checks, real BCJ, PFN identity and private
   services; simultaneous native and conflicting SIF consumers plus XZ execution
   breakpoint; all task registrations restored and modules unloaded afterward.
5. Original application/SIF inputs, four pilot blocks: word-only XZ ordinary
   tasks and Python compilation first; cache candidate gzip/xz/lz4 ordinary
   tasks and gzip/xz compilation next. Stock default/single, same-core copied /
   shared and both LKL policies remain. No formal samples from these pilots.
   One four-block native pilot covers the original five-codec tree and matched
   optimized native references. Extra cache-only controls use the same owner.
6. Untimed original 1/4/16 metadata scales; compare retained/peak private memory
   and workload correctness, not merely allocation counters. No new formal
   image distribution or application substitutes the adverse tasks.

## Interpretation and confirmation gate

Any correctness/PFN/restoration failure blocks promotion. A pilot point
regression above 5% on an unchanged-path task triggers investigation, not an
automatic claim that the candidate is acceptable. Smaller/non-significant
effects are not proof of equivalence. Examine CPU, elapsed time, paired spread,
native impact and memory jointly; retain adverse cells and failed candidates.
Budgets and code are not repeatedly tuned to favorable benchmark samples.

After pilots, freeze one candidate and explicitly record the final acceptance
decision/remaining limits before confirmation. Re-run every affected original
matrix using fresh outputs and original fixed block counts: three campaigns;
native/tree and stream 8 blocks, ordinary apps 12, Python 8, decoder diagnostic
4, single-CPU 12. Primary independent units are three campaign means, with
paired within-block observations preserved. No stopping on significance.
Updated native reference conditions change counts explicitly in the new audit.
No compilation, QEMU or other task load during timing. Same host boot and
affinity/SMT/turbo/governor settings; record rather than change them.

Final reporting separates algorithm optimization, preparation cost,
copied/shared increment, external backend comparisons and physical backing.
Charge the changed code size, residency, metadata, deployment and source edits;
retain the installed-platform accounting premise. Publication is updated only
from audited new results, preserving Section 6.1–6.4 and all older freezes.

## Storage

The home partition is nearly full. New run data uses the task-owned directory
`/var/tmp/vkso-section65-optimization-20261030-hBcg9Y`, with repository entry
`test/section65/build/squashfs/optimization-runs-01`. No old data was removed.
Equal-path hardlink controls must stage their binaries on this same filesystem;
ordinary source/build identities are preserved by hashes, not assumed by name.
