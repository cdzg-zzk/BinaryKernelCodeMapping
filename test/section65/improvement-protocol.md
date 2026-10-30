# Section 6.5 improvement round — active

The completed 34-campaign evaluation remains the baseline. The new objective
is to lower evidenced adoption costs and strengthen proof of the paper's
shared-instructions/private-state and maintenance/deployment claims. Positive
results are sought through mechanism changes, never by changing comparisons or
omitting losses. The user-supplied follow-up assessment is the scope authority.

## Required work and completion evidence

| Work | Uncertainty | Intervention/control | Required evidence |
|---|---|---|---|
| Native regression attribution | Which executed operations explain scan overhead? | Original and prepared native PMU profiles; diagnostic service counts; single-factor candidate builds | Real call/work counts, instructions/cycles, generated code; uninstrumented paired before/after costs |
| User adapter costs | Repeated readdir parsing and whole-block scatter occur in current source; actual scale unknown | Instrument unchanged bridge/frontend, then directory-handle and direct-output candidates separately | Parsed/returned directory entries, calls, decoded/scattered bytes, CPU profile; complete old workload results including adverse tasks |
| Private state during simultaneous use | Sequential checks do not fully demonstrate independently live consumers | Native image A and real Apptainer image B with conflicting same-name data, plus second user process C | Overlapping execution, own-image outputs, common PFNs, private binding/object identities, one-consumer cleanup while others continue |
| Actual update work | A common repair does not imply fewer builds than materialized copied control | Replay fixed maintenance transition in copied and shared; include a justified interface/dependency update | Source/interface and artifact deltas, unchanged binaries, build/export/register/deploy steps and version identity; no fabricated human hours |
| Resource improvement | Six shared pages do not outweigh all dedicated deployment costs | Inspect fixed module/support cost and existing codec exports; choose one evidenced route | Full incremental ledger under existing-resident and additional-deployment assumptions; actual removed duplication/dependencies, execution and integration costs |
| Final evidence and text | Improvements may invalidate earlier binaries/results | Freeze stable candidate, full required regressions and independent paired campaigns | Old/new records retained, fair copied/shared and competitive LKL/stock controls, revised claim verdicts and Section 6.5 |

## Execution and decision rules

Start with dynamic attribution. Count-only/PMU diagnostic runs are not formal
speed measurements. Profiling is compiled out of production candidates.
Investigate the existing include workload and 256 MiB task; a large-directory
fixture specifically tests request continuation and is labeled additional,
not substituted for original workloads. Preserve compression formats, lifecycle
boundaries, cache/heap/thread conditions and baseline identities.

Candidate gates: correct semantics and shared-core identity; a mechanistically
predicted reduction in calls/parsed bytes/copied bytes; then uninstrumented
paired performance and memory evidence. Retain failed and neutral candidates.
Apply user-support optimizations equally to copied and VKSO. Do not introduce a
kernel-only specialized core or claim zero-copy when request/FUSE copies remain.
No unsupported multithreading; independent single-threaded consumer processes
can overlap. Malformed images remain confined to disposable guests.

Resource route selection follows dependency/residency inventory. Reusing an
existing codec is conditional on actual native+user use of the same owner and
cost accounting; increasing exported page count alone is not success. All
explicit questions above remain open until resolved by evidence, including
negative results with reasons. No new claim of human-time savings without a
prospective matched task study.

## Baseline and current source audit

The baseline is `build/squashfs/evaluation-fixed-01/build`, repaired owner hash
`b1ae55e3f1ca3ff565939b32685d4908e57d85fdf9a6ba846e18999e3868882a`.
Final prior sources/docs are frozen in `evaluation-fixed-06`; all 34-campaign
results are in `final-analysis-02`. Existing materialized copied images retain
identical core instructions for diagnostic user runs.
Current `sq_readdir` reconstructs the entire list on every request; current
`u_decompress` decodes into a separate output then scatters into already
contiguous cache storage. These are source facts, not yet measured bottlenecks.

## Formal follow-up matrix (specified after pilots, before formal collection)

Freeze `evaluation-improved-01` contains the bounded <=16-byte metadata copy,
directory-handle list retention, contiguous direct decoder output and composed
safe LZ4 block decoder. Five-format hardware correctness passed; the repaired
malformed case is being replayed in an isolated guest before formal use.
No runtime core specialization by domain is introduced.

Native comparison: original, prepared-before, bounded-copy-only, and composed
prepared builds on all five codecs, scan/archive, fresh mount plus one warm
traversal. Three independent campaigns of 12 blocks each; module replacement
occurs outside timings and each cell uses a new mount. Randomize codec/task
cells and variant order, retain every output digest and executed order. This
adds 2,880 timed observations. A four-block runner pilot precedes these runs.
The targets are to distinguish a roughly 3–5% preparation cost and estimate
fresh-scan ratios to about two percentage points, subject to measured intervals.

Application comparison: three independent campaigns per codec, 12 blocks,
one new Apptainer execution per cell, all four established tasks. Include
stock, copied-old-adapter, copied-composed, VKSO-composed, LKL default 512 MiB
and LKL cache-matched 512 MiB for gzip/xz/lz4. For gzip and lz4 also include
directory-only, direct-output-only and combined-adapter/user-lib-LZ4 copied
controls; include stock-with-translator for gzip to recheck fixed startup
translation cost. These controls use the same composed owner, so adapter and
codec comparisons do not conflate core instructions or physical backing.
The bound LZ4 slots are initialized even in library-decoder controls; their
actual decoder remains liblz4. This is 3,600 timed observations, with all
absolute times and paired results retained. Existing broad cache-policy
comparison remains valid evidence about unchanged LKL binaries and settings.

The single-factor gzip/lz4 cells span metadata-dominated and faster-codec,
copy-sensitive cases. The xz main comparison retains all tasks, including the
previous adverse stream case; no cross-format codec-speed claim is made from
LZ4 composition. The previously completed user-only pilots retain xz ablation
measurements as diagnostics. The app precision target is a three-percentage-
point effect on nontrivial tasks; startup may remain less precise and will be
reported accordingly. Three campaigns and their block hierarchy are retained;
within-campaign repeats are not independent campaigns. No stopping rule depends
on positive significance, and no rejected candidate is pooled into final data.

Order: guest regression and native-runner pilot, native codec call-count check,
then formal native and application campaigns. Native formal timings run without
our compilation, QEMU or concurrent benchmarks. Any configuration change after
this freeze requires affected reruns; scripts/analysis fixes preserve old logs.

Resource ordering correction before formal application collection: capture
helper/process snapshots and complete smaps before any PFN or debugger read.
PFN observation deliberately touches mapped pages and must not determine the
reported post-workload resident set. Pilot resource observations retain their
older ordering and are not pooled with these formal memory snapshots. Timing
workloads and their lifecycle boundaries are unchanged.

Uncertainty convention, fixed before inspecting formal results: retain the
baseline paper's primary Student-t interval over independent campaign mean
log ratios (three campaigns, two degrees of freedom). Paired differences use
campaign means in seconds. A 10,000-draw campaign/block hierarchical bootstrap
is secondary sensitivity output, not the headline interval with only three
independent rounds. Absolute plots use mean campaign medians and campaign-level
intervals. No formal point estimates had been examined when setting this rule.

## Bounded-copy interpretation diagnostic

The completed main native comparison establishes improvement of the prepared
implementation relative to its predecessor. A new uncertainty follows from
the intervention: bounded small copies may also improve an unadapted native
driver. Therefore the stock-original comparison must not be interpreted as
having isolated or eliminated the adaptation-only cost. Apply exactly the same
bounded-copy helper to the patched unadapted module, retaining normal native
flags, and also to its existing relaxed-flags diagnostic. Compare original,
normal module, optimized normal module, optimized relaxed module and prepared
bounded-copy core on gzip/xz/lz4 fresh/warm scans: three campaigns, eight blocks,
plus one four-block runner precheck. The shared tree and copy-size distribution
are codec-independent; these three codecs span decompression costs. Archive
and all-five-format performance remain in the primary matrix.

If both native and prepared paths improve, identify this as a generally useful
micro-optimization. Any residual difference from the optimized native controls
remains an adaptation/build-context cost. This diagnostic does not change the
final application version or serve as a stopping rule for positive results.
It will run after the existing application queue, with its two builds completed
before timed collection. All timing and failed variants remain separate.

Final-version native sequential coverage: the composed LZ4 decoder changes the
native path as well as the user path, so the baseline 256 MiB native archive
results cannot represent it. Repeat the same original/prepared-before/bounded-
copy/composed comparison on the established gzip/xz/lz4 SIF stream subtree,
fresh and warm archive phases, three campaigns of eight blocks (576 samples).
The data, block size and task are already established; this is a required
version-matched rerun, not selection of a new favorable input. It follows the
bounded-copy controls without concurrent compilation or QEMU. The extended
formal matrix totals 18 campaigns and 7,776 observations when complete; earlier
baselines and pilots remain distinct.


## Targeted xz attribution extension (before its new measurements)

The completed main application matrix finds composed copied / old-adapter
copied xz stream time +3.486%, with a campaign interval [2.709%, 4.268%] and
CPU time +3.949%. All three campaign ratios exceed one. The earlier profile
records have identical raw bytes, decoder calls and decoded bytes, while direct
output removes approximately 128 MiB of scatter. These facts rule out a
simple increase in logical work but do not separate directory caching, decoder
destination changes and the removed unused LZ4 dependency. The original xz
matrix contains only old/full adapters, so a causal attribution gap remains.

Add a finite explanatory matrix on the same xz SIF and all four existing
application tasks: stock, old-adapter copied, directory-only copied,
direct-only copied, both-adapters/library-LZ4 copied, complete copied and VKSO.
Use the already-built same-core controls, with no production-code changes and
no new input selection. A two-block pilot checks this variant set, then three
campaigns of eight randomized paired blocks (seeds 66401–66403), totaling
672 formal observations. They execute after all existing native timing and
resource queues. Campaign intervals retain the same primary convention.

This extension is reported separately from the original 18 campaigns/7,776
observations. Its purpose is to locate the observed xz regression, including
the possibility that the controlled repeat disagrees. It is not pooled into
main results or used to select favorable runs. A change is justified only if
these controls identify an implementation issue or a general mechanism with
an actionable correction; otherwise the observed format/task tradeoff remains
a reported limit. No universal benefit is inferred from reduced copy counters.

## Same-binary pathname diagnostic

The completed xz attribution campaigns locate the stream slowdown in the
complete copied configuration relative to the both-adapter/library control
(+4.148%, interval [3.416%, 4.886%]); direct output alone does not reproduce
the slowdown. However, unchanged VKSO binaries now run about 4.7% faster than
copied, whereas the primary campaigns were close to equal. This context
sensitivity prevents attributing either difference to physical sharing.
Changing output-directory spelling changes loader inputs and may change
private allocation layout. This is a hypothesis, not an established cause.

First run a bounded diagnostic: five pathname padding lengths (0, 8, 16, 24,
32 bytes), eight randomized paired blocks, identical hardlinked frontend,
bridge and materialized core inodes. Each cell starts a fresh FUSE mount and
archives the same 256 MiB xz SIF subtree with image backing warmed. Record
elapsed time, helper CPU ticks, output identity, and private addresses read
after timing. No kernel module is required. This isolates pathname spelling
with identical code and backing; it is not an Apptainer lifecycle estimate.
One block checks the runner before the eight-block diagnostic. Any subsequent
layout-controlled application matrix will be specified separately; earlier
campaigns remain visible and are not pooled or discarded.

The completed same-inode diagnostic changes private allocation offsets and
shows less than 1% spread in median mounted-task time. It does not reproduce
the 4--5% full-application difference or establish its cause. The earlier
application snapshots nevertheless show unequal copied/shared heap offsets.
Add equal-loader-path controls to test the physical-backing claim directly:
hardlink each reader's unchanged frontend, bridge and core under equal-length
paths; verify inode and byte identities. Copied/shared use the same frontend
and bridge inodes and different core backing. Use two predetermined padding
lengths, 0 and 16, balanced four blocks each per campaign. All variants in a
block receive the same padding; padding and task/variant order are randomized
and recorded. Path lengths are not selected for favorable timing.

Run three independent campaigns for each gzip/xz/lz4 SIF, eight blocks, all
four established tasks and five backends: stock, old-adapter copied,
both-adapter/library copied, complete copied and VKSO (1,440 observations).
A two-block xz pilot exercises both padding levels before formal collection.
Keep the original and xz-attribution estimates separate; these controls test
robustness to loader inputs rather than replace unfavorable observations.
Primary intervals retain three campaign means, with separate padding-stratum
estimates. If the controlled difference remains inconsistent or imprecise,
report the observed conditions and uncertainty instead of claiming universal
equivalence. No production source or measured binary is changed.

## CPU-placement sensitivity control

All nine equal-loader-path campaigns completed. Their balanced xz VKSO/copied
stream ratio is 1.0021 [0.9905, 1.0138], but gzip scan/stream intervals remain
too broad for the three-percentage-point precision target. In gzip campaign
2, one copied stream uses 0.569 CPU seconds in 0.456 elapsed seconds, while
the paired VKSO invocation uses 0.565 CPU seconds in 0.621 elapsed seconds.
Both have the same two-CPU affinity. Campaign 1 also contains delayed scan
samples with similar CPU work. This is consistent with placement/parallelism
variability, not evidence of a computational-work increase or a valid reason
to discard samples. The common-LZ4 stream improvement also does not reproduce
under every original/normalized-path context.

Run one finite placement diagnostic using the same five backends, three SIF
codecs, four tasks, equal-loader paths and balanced padding 0/16. Restrict all
application/helper descendants to CPU 1, leaving the host configuration
unchanged. Use three campaigns of eight paired blocks per codec (1,440
observations), with a two-block xz runner precheck. Record live process
affinities in untimed resource observations. This changes the task CPU budget
and therefore answers a conditional mechanism/adapter question; it does not
replace the default two-CPU application comparison. No LKL superiority claim
will be inferred from this separate diagnostic.

The fixed extension tests whether backing and adaptation differences persist
without cross-CPU placement variability. Report its intervals even if they
remain wide or adverse; do not extend again merely to obtain a favorable
bound. The original 30 campaigns remain separate, and the complete improvement
record will contain 39 campaigns / 11,328 observations. There is no production
binary change and no deletion of prior samples.
