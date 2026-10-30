# Word-copy XZ and bounded private metadata: reproduction

This is a new implementation version, not a rename of `refine-xz-01`.
Start with `PROTOCOL.md`, `confirmation-registration.json`, `RESULTS.md`, and
`../../STATUS.md`. The task-owned run namespace is the repository symlink
`test/section65/build/squashfs/optimization-runs-01`, resolving to
`/var/tmp/vkso-section65-optimization-20261030-hBcg9Y`. Historical data was not
deleted to make space. All commands below run from the repository root.

## Exact implementation and finite selection

`build_candidate.py --bounded-cache --output NEW` starts from the retained
common-XZ baseline, changes only the `dict_repeat` algorithm body and installs
the private LRU/handle-lifetime bridge and frontend. Native/user execution uses
the same scalar word-copy algorithm. Baseline compiler/ISA/hardening policy is
unchanged; the inherited native SSP/thunk gap remains explicitly unresolved.
The generator produces fresh owner/consumer and both copied/bridge builds.
`optimization.json` supersedes inherited build metadata and zero-edit claims.

The chosen binary is `optimization-runs-01/builds/optimization-cache-01`.
It is byte-identical to the home build `optimization-cache-01`; staging is
necessary for equal-loader hardlinks on the same filesystem as new outputs.
`build_native_controls.py` gives normal/relaxed native references the identical
XZ algorithm without VKSO. Their module bundles XZ rather than changing the
host kernel; report both this 72 KiB reference and the prior 60 KiB host-XZ
reference, not a calibrated whole-kernel replacement cost.

The original real-SIF block diagnostic uses fixed inputs/hashes, five paired
rounds and correctness checks. Random payloads may be stored uncompressed and
do not invoke a decoder; cache hits are not counted as new decode events.
Jump-table, small-service, O3 and scalar-mask range-decoder hypotheses were
not selected. Word repetition improves the intended compressible block path;
Python application loss remains a separate measured issue. Do not continue
searching code/layout/input variants until a favorable answer appears.

Private cache budgets are 2048 inodes / 4096 positive names. Stable image-local
IDs and locations survive eviction. Root and open handles pin inodes;
release callbacks restore retention bounds. Live pins, open-directory lists
and other runtime state are outside those bounds. Total FUSE-process PSS is
not constant and is not uniformly below single-thread stock.

## Correctness and diagnostic gates

Completed outputs are individually preserved under the new run/build namespaces:

- `optimization-xz-valid-01`: 65,536 dictionary states, sanitizers, 244 valid
  SINGLE/PREALLOC/BCJ streams.
- `optimization-cache-valid-01`, `optimization-cache-sanitize-01`, and
  `optimization-cache-fuse-01`: randomized eviction, >budget held handles,
  hardlinks/xattrs/long names, private-adapter sanitizers and FUSE cursors.
- `optimization-cache-guest-01`: repaired malformed input exclusively inside
  an isolated guest; EIO and daemon survival, normal five-format regressions,
  restoration/unload. Never mount these malformed fixtures on the host.
- `optimization-runs-01/functional-01`, `simultaneous-01`: final-binary
  native/copied/shared content, BCJ, actual SIF B/C, private objects, shared
  PFNs, hardware breakpoint, independent exits and native regression.
- `validation-queue-01`: original three memory scales, 160 contiguous-buffer
  copied/shared SINGLE/PREALLOC decoder observations, held FUSE descriptors,
  native decoder counts, owner-only/copied-minimal deployment and hardening.
- `metadata-work-01`: three current-version mount/scan decoder-count replays;
  instrumentation is not used for formal timing.
- `cache-scale-direct-01`: three traversals of each original scale, cache
  counters and process/allocator snapshots. Diagnostic `malloc_trim` is never
  installed in production. These non-FUSE processes are not subtracted from
  actual helper PSS as a calibrated component attribution.

Eight four-block pilots contain 1,136 observations, separate from confirmation.
Cache-only comparisons use the same owner instructions. Adverse startup/Python
and warm native points are retained. Promotion records their review rather
than claiming equivalence from nonsignificance or small point estimates.

## Registered confirmation and safe reruns

`formal-queue.json` and `confirmation-registration.json` fix 30 campaigns:

| Group | Campaigns | Observations |
| --- | ---: | ---: |
| Five-codec native tree, seven native conditions | 3 | 3,360 |
| XZ/LZ4 native sequential, fresh/warm | 3 | 672 |
| Three-codec ordinary application tasks | 9 | 3,024 |
| Fixed gzip/XZ Python compilation | 6 | 288 |
| Equal-loader decoder/dependency controls | 6 | 240 |
| Selected single-CPU gzip stream | 3 | 108 |
| Total | 30 | 7,692 |

Original SIFs, task commands, seeds and block counts are retained. Native and
Python use eight blocks; ordinary applications twelve; decoder controls four;
single-CPU twelve. No QEMU/compiler/profiler/parallel task load during timing.
Do not change governor, turbo, SMT or boot. Each runner owns its mounts/modules,
restores registrations and unloads its modules. Stop and diagnose failure;
do not delete a partial run or count it as complete.

For a rerun on this same host with the exact frozen binaries/runners:

```sh
python3 test/section65/squashfs/optimization-20261030-01/clone_confirmation.py \
  --tag repeat01 --output /var/tmp/vkso-section65-confirmation-repeat01
sudo python3 test/section65/squashfs/campaign_queue.py \
  --queue /var/tmp/vkso-section65-confirmation-repeat01/queue.json \
  --output /var/tmp/vkso-section65-confirmation-repeat01/queue-log
```

This creates fresh names and a corresponding registration, not new samples
under existing names. It verifies registered identities before cloning. A new
host/build requires explicit path/ABI/environment validation and a new version;
do not evade the identity checks. Credentials are entered only at a verified
interactive sudo prompt and are never placed in scripts or output records.

## Analysis, accounting and publication

```sh
python3 test/section65/squashfs/optimization-20261030-01/analyze.py \
  --queue NEW/queue.json --output NEW/analysis
python3 test/section65/squashfs/optimization-20261030-01/audit.py \
  --queue NEW/queue.json --registration NEW/registration.json \
  --analysis NEW/analysis/analysis.json --output NEW/analysis/audit.json
```

The independent audit replays all raw pairs/campaign intervals, fixed cells,
counts, identities, output/PFN/restoration records and one-boot scope. Primary
ratios use three equal-weight campaign mean log paired ratios; pointwise
Student-t intervals have two degrees of freedom. Absolute times are means of
campaign medians, not operands of paired ratios. Secondary resampling is
separate. Pilots and all prior versions are excluded.

The current final analysis directory is `optimization-runs-01/analysis-final-01`.
`analysis-01` holds preliminary source costs and is not the formal analysis.
Regenerate `cost_ledger.py`, `reuse_audit.py`, and `resources.py` after source
changes stop. Source inventory hashes every accounted file; XZ original hashes
are verified, the exact one-body diff is retained, and no zero-body-edit claim
survives. Platform, business/module, requested metadata, process snapshots and
deployment stages are separate ledgers, not a net machine-memory total.

`write_section.py` fills the local Section 6.5 template only from audited
analysis/resources/costs. `write_reports.py` prepares current findings and all
13 claim judgments without silently dropping C9-C12's unsupported stronger
claims. Python's raw group remains named `heldout` for provenance but was
consulted in this optimization; publication calls it a fixed separate task.

Before installing manuscript outputs, `archive_publication.py` saves the exact
previous publication, figures, PDFs and scoped documents. Its canonical-prefix
hash protects Sections 6.1-6.4. `paper/plot_filesystem_optimized.py` derives all
figures/full tables with data provenance; `paper/build_filesystem_section.py`
exports current canonical Section 6.5, using its optimization dataset marker.
Build using the existing Tectonic environment and visually inspect rendered
PDF pages. Freeze to `evaluation-optimized-01` only after numerical/visual QA.
`final_evidence.py` checks identities, all tests, statistics, source edits,
archived history, untouched earlier sections, figure inputs, PDF and claims.

No whole-paper build, human-time savings, native hardening parity, hot update,
concurrent throughput, cross-boot/host generality, universal compactness or
general adoption preference over copied is established. Rump remains related
work without a measured timing row. No commit/push/reboot is required.
