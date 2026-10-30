# Section 6.5 research protocol and completion ledger

Status: the baseline matrix is complete; the subsequent improvement round is
tracked in `improvement-protocol.md` and `STATUS.md`. Per-claim judgments are in
`claim-verdicts.json`, and executable completion checks in `final-evidence.json`.
Their version identifies the evaluated implementation. The initial evidence-gap table and
dated decisions below preserve the prospective plan; their historical statuses
are not current work queues.

## Recovered paper objective

The Introduction and contributions in `paper/paper_content/Paper Draft.md`
ask which resident binary closures can be reused, how to rehost them without
copying execution bodies, and what duplication, deployment and execution costs
result. The Design text in that draft and the current
`paper/design/chapter3_general_os_design.md` and
`paper/design/chapter4_linux_state_binding.md` describes shared execution
and explicit environment dependencies. The previously referenced
`paper/paper_content/sections/04-design.tex` is absent from the current tree.
The authoritative evaluation source is
`paper/paper_content/sections/06-evaluation.tex`; at the initial audit it ended
with 6.4 and contained no Section 6.5 prose. Its filesystem scope
comes from the user's explicit research request and the paper's reuse motivation.

Sections 6.1–6.3 isolate backing, indirection and algorithm adaptation; 6.4
tests shared live time state and Nginx. Section 6.5 must test a different
boundary: a common filesystem implementation operating on domain-private
objects, with real kernel mounts and user applications. ISO9660 supplies
extension semantics, debugging and an independent maintenance example;
SquashFS supplies compressed container filesystems and actual Apptainer execution.

## Claims and completion conditions

| Claim / question | Experiment and metric | Existing evidence | Missing evidence and completion condition | Support / limitation / confound |
|---|---|---|---|---|
| Same execution body serves both domains | Original/prepared kernel and identical copied/shared FUSE; manifests, offset reads, PFNs, binding addresses, restore/unload | squash-native-guest-03; squash-export-04; squash-apptainer-shared-02 | Repeat affected checks on final fixed owner, preserving five-format semantics | Matching outputs and shared PFNs support tested semantics; mismatches refute them; ordinary copied DSO mappings do not prove kernel sharing |
| Native preparation has bounded cost | Original/prepared, five codecs, scan/archive, fresh mount/warm; absolute time, paired ratio and CI | squash-native-cost-01: one gzip image, one campaign | Execute image-set runner preflight and at least three independent campaigns; audit config and emitted instructions | Any regression remains visible; PIC, instrumentation and mitigation changes are part of total preparation, not pure service-call cost |
| Physical sharing has small incremental cost | Same core bytes, bridge, frontend and workload, copied versus shared | export-04 PFNs; final application comparison-02 | Verify identities and repeat on final version across independent campaigns | CI bounds support only observed workloads; differing cache/frontend versions invalidate isolation |
| Useful complete application performance | Real SIF/fd/offset Apptainer startup, scan and archive; stock, stock+C translator, copied, shared, competitive LKL | comparison-01 Python; comparison-02 C | Final-version multi-campaign C comparison, representative additional formats/scale, LKL memory sensitivity | Include whole lifecycle; no median subtraction; report losses as well as gains; LKL version, cache, threads and decompressor differ |
| Adaptation and maintenance reduce duplicated implementation | Account native preparation, exporter changes, first user bridge, application glue, subsequent patch separately | Initial ISO cost ledger; SquashFS 34 moved functions, bridge/frontend sources | Recompute final source accounting with consistent categories and baseline starting points | Source lines are proxy, not hours; no measured development-time advantage currently supported |
| Shared pages affect deployment memory | Unique PFN union; user RSS/PSS/USS; owner/consumer/registration allocation; deployment stages | 24 KiB SquashFS sharing and helper snapshots | Complete resident-core and additional-core ledgers, measure load/export/register/run/restore; identify unmeasured allocations | Helper RSS or code pages alone cannot prove net machine savings; ordinary DSOs already share across processes |
| One common repair reaches both consumers | Old/fixed × native/copied/shared, valid and malformed image, unchanged bridge/frontend, five-codec regression | maintenance-01 old SIGSEGV and target-function kernel panic; fixed never run | maintenance-02 adds copied control and multi-signal classification; native fixed semantics must be observed and checked against same-version unadapted patch | EIO and ENOTCONN alone are insufficient; preserve native zero-fill versus user short-copy behavior; no hot-update inference |
| User tools debug actual resident execution | Replay GDB hardware breakpoint, arguments, stack, step, pre/post PFNs and kernel regression | ISO fuse-export-01 and maintenance-oneshot-01 | Audit replay commands and binary identity; report ISO scope explicitly | Supports debugger feasibility, not measured debugging-time improvement or independent discovery of known upstream defect |

## Finite matrix and sampling

1. Functional: five existing gzip/xz/zstd/lz4/lzo fixtures, original and prepared
   native, copied and shared; final fixed owner; semantic and lifecycle checks.
2. Maintenance: old/fixed × three consumers, valid/negative fixture; all faults
   in disposable TCG guests. Same-version unadapted fixed reference if native
   output differs from the user adapter. TCG never supplies performance results.
3. Native preparation: five codecs of the identical existing root tree with
   128 KiB blocks; scan and archive; fresh mount then two warm traversals.
   Preflight four blocks (current runner minimum), explicitly excluded from
   formal inference. Pilot determines precision; initial formal design is three
   campaigns of eight randomized paired blocks, with new loading/mount cycles
   and different random seeds. Record actual execution order and campaign ID.
4. Application: retain six baseline configurations, including LKL 16/64 MiB;
   pilot larger heaps before choosing a competitive principal LKL configuration.
   gzip is the historical anchor; xz and lz4 represent distinct compression
   tradeoffs. Use real SIFs for any cross-format application statement.
   Add a larger sequential-data task and retain metadata/small-file traversal.
   zstd/lzo functional and native evidence cannot establish their application
   performance; report that unmeasured scope explicitly. Three independent
   final-version campaigns are the initial design, revised before formal timing
   if pilot noise requires more precision.
5. Resources: application helper snapshots plus kernel/support and deployment
   accounting under both residency assumptions. Multiple processes are required
   only for a scaling claim; do not infer per-process exclusive DSO code copies.

Compressed-image cache warming, first filesystem access after a new mount, and
warm filesystem caches are distinct conditions. Warm traversal may bypass most
shared parsing and cannot alone establish preparation cost. Keep campaign/block
hierarchy in resampling; repetitions within a mount are not independent runs.
Report per-campaign estimates, absolute time, paired differences/ratios and CIs.
Never stop sampling because an advantage becomes significant. Failures and
excluded observations retain explicit reasons and original records.

Formal native measurement runs alone: no task-owned QEMU or compilation.
Record affinity, frequency policy, CPU, RAM, kernel/build identity and background
activity. No host boot configuration changes. Freeze final owner, bridge,
frontend, translator, exporter, source diff, build commands and image identities
before timing. Old results remain separate unless equivalence is demonstrated.

## Current execution status

- Existing `squash-maintenance-01` has stale `status=running`; console and
  extracted evidence show the old guest terminated with a target-function panic.
  Its orchestration stopped on errno 107 versus assumed 5. Do not rewrite it.
- `maintenance.py` and `maintenance_guest.py` now collect copied and shared
  outcomes, daemon survival and PFNs, preserve native read bytes, and record
  terminal orchestration failures. `squash-maintenance-02` is the new run.
- Five native images exist in `build/squashfs/native-images-01`; availability
  means built only. The image-set timing path still needs actual preflight.
- Application campaigns 01 and 02 use different translators and cannot be
  treated as independent repetitions of one final implementation.
- Final performance campaigns, resource accounting, tables, plots and 6.5
  manuscript integration remain required. No unsupported claim is removed
  merely to mark this task complete.

### Verified continuation checkpoint

- `squash-maintenance-reference-01/guest/run.json` and its extracted result are
  complete: unadapted 5.15.198 plus the same patch returns EIO on the negative
  fixture, preserves the valid payload, passes all five native format manifests,
  and unloads its module. `maintenance_reference.py` reproduces this reference.
- `squash-maintenance-02` old guest has been classified successfully. Fixed
  guest is still running; preliminary guest records show copied/shared EIO with
  surviving daemons and successful shared format regressions. Only extracted
  final records may close the maintenance requirement.
- `native_cost.py` now accepts campaign/seed/pilot labels, records actual sample
  order and environment/module identities, and rejects image hash mismatch.
  Syntax checking passed; actual image-set preflight remains pending until
  task-owned QEMU exits.
- `native-images-01/superblock-audit.json` records all five superblocks: 128 KiB
  blocks, 6,156 inodes, 274 fragments each. This does not substitute for content
  or timed-output equivalence checks.

### Maintenance gate completed

The extracted final `squash-maintenance-02/result.json` is complete. Fixed native,
copied and shared reads all return EIO; both user daemons survive. Both user
backends pass six full regressions with PFN checks; native five-format regression,
restore and unload pass. Same-version unadapted fixed reference agrees. The
source/owner snapshot is `build/squashfs/evaluation-fixed-01`; the original
reader-adapted build is retained. Five-codec native pilot 01 is executing against
the fixed build, with no task-owned QEMU or compiler processes running.

### Native pilot and prospectively fixed sample size

Five-codec pilot 01 completed 240 samples and 120 complete pairs; outputs agree
across formats/variants. `squashfs-native-pilot-audit.json` records a rerun of the
summary and pair audit. Fresh scan differences range from approximately +3%
to +5%; warm scans show substantial short-task variation. Before formal data,
fix three campaigns × 12 blocks, with three warm traversals per new mount,
seeds 65201/65202/65203. Target descriptive resolution is about 2 percentage
points for fresh tasks and 5 for warm tasks; unresolved cells retain their
intervals rather than being described as equivalent. No significance-based
stopping or selective campaign exclusion. This replaces the initial 8-block
proposal based on actual pilot variation. Campaigns reload modules and mount
new filesystems. They support this host/boot only. Larger sequential-data
coverage and application campaigns remain additional requirements.

### Application coverage implementation

`application_images.py` prepares real gzip/xz/lz4 SIFs from the same root,
retaining the include tree and adding two 128 MiB sequential files: repeated
text and seeded pseudorandom bytes. This separates small-file/metadata work
from larger, differently compressible content. These three codecs cover
compression tradeoffs; zstd/lzo application performance remains unmeasured.
The script is implemented, not yet executed. `apptainer_bench.py` now supports
startup, include-tree scan/archive and sequential-data archive, campaign seeds
and configurable LKL heaps. `apptainer_shared.py` forwards these parameters
and records stage timings and resident module sizes. Actual preflight is
required before treating any new path as evidence.

### Formal native campaign 01 complete

`squash-native-five-formal-01` contains 960 observations, 480 paired keys,
12 complete blocks and successful unload. `squashfs-native-formal-01-audit.json`
verifies output equality, ordering and exact summary regeneration. Two further
independent campaigns remain. `application-images-01` is currently building
the enlarged real SIFs. Native runner gained optional subtree/workload selection
for separate sequential-data measurements; default include-tree behavior is
unchanged. Application image generation and audit run only after formal timing
ended. No application timing from the new runner exists yet.

### Application pilot selection (before formal application sampling)

Expanded gzip pilot 01 passes 32 observations; gzip pilot 02 passes 128
observations in four paired blocks. All eight backends pass correctness.
Increasing LKL from 256 to 512 MiB improves include archive time by about
3.88% in paired geometric mean; it has mixed/small effects on the other tasks.
The formal primary LKL setting will therefore be **512 MiB**, with 64 MiB
retained as memory sensitivity. 16 and 256 MiB remain visible pilot diagnostics.
512 MiB exceeds the whole 256 MiB sequential payload plus the include tree
and runtime working set; choose this competitive configuration rather than
the slower historical 16 MiB baseline.

Formal application matrix: gzip/xz/lz4 × startup/include archive/include scan/
sequential archive × stock/stock+C translator/copied/VKSO/LKL64/LKL512;
three independent campaigns per image, eight randomized blocks and two fresh
container executions per cell. This is 384 observations per campaign, 3456
overall. Per-image phase and output oracles stay explicit. Fresh processes,
mounts and registrations distinguish campaigns. Pilot data are excluded.
Target approximately 2% resolution for full tasks; startup may remain less
precise, in which case retain that uncertainty. The finite matrix does not
claim zstd/lzo application performance, random-I/O performance, concurrent
scaling, net machine memory savings or measured developer-time improvement.
These claims remain separately assessed, not silently deleted.

Build audit 02 preserves actual original and prepared disassembly. Original
read-inode/readdir/read-data contain stack-check failure references; original
readdir/read-data contain indirect thunks, and all six inspected functions
contain return thunks. Prepared core lacks them. Audit 01 included objdump's
preceding-section relocation records; audit 02 filters relocations to symbol
extents and supersedes those relocation counts. Raw instruction evidence
remains available. Compilation-option and modularity diagnostics are still
required before interpreting preparation effects.

### Cost and resource instrumentation

`squashfs-cost-ledger.json` records raw source categories and final moved-body
comparison: 34 functions/2103 original lines, 46 services/10 operation tables,
and three changed bodies after the upstream repair. ELF allocated bytes, disk
size and actual module residency are kept distinct. No hours are inferred.
`private_state_gdb.py` adds an optional read-only DWARF walk of user image,
inode/name caches, filesystem caches and output buffers in an untimed paused
helper. The reported requested-byte subtotal excludes allocator, codec and
other explicitly named allocations; it must be interpreted with process
RSS/PSS/USS, not as a complete private-memory total. This optional path still
requires execution validation. It does not modify the evaluated binaries.

### Three-campaign analysis and fixed precision extension

The initial native set is complete: 2880 observations, 1440 paired keys,
three independent load cycles, 12 blocks each. `native-five-analysis-01`
contains raw CSV and campaign/block estimates. Inference uses a 95% Student
t interval across campaign mean log ratios (df=2), retaining block medians;
an independent geometric-mean cross-check passed. First-archive changes range
from +0.09% to +1.43%; first-scan changes from +3.06% to +4.59%. Some scan
intervals exceed the prospective precision targets (e.g. lz4 fresh scan
−0.58% to +10.03%, gzip warm scan −5.41% to +10.40%).

Before further observations, extend the complete five-codec matrix to a fixed
**seven campaigns** (add four, all cells, same 12 blocks/three warm repeats).
Retain every earlier campaign and report all estimates, including wide or
negative intervals. Stop at seven irrespective of significance; unresolved
precision is reported. Place added campaigns at later times after the main
application queue, providing additional time variation on this same boot.
This extension addresses observed campaign variation rather than selecting
formats or rounds with favorable performance.

### Private-state tool correction and successful validation

Private-state pilot 01 failed because the production bridge lacks DWARF types.
`build_debug_types.py` generated a separate companion; all allocated sections
match the original user_bridge.o. Pilot 02 timed out while repeatedly parsing
the same type sizes in GDB. Memoizing sizeof queries fixes the observation
script without changing target binaries. Pilot 03 completes, including
post-observation PFNs, application output, restore and unload. Both failed
runs and their queue failures remain. The directly accounted live allocation
subtotal is 5,456,958 bytes, including 4,452,480 inode-object bytes, 262,350 name
bytes and 592,920 cache bytes; excluded allocations are explicitly listed.
This is a requested-byte subtotal, not RSS or whole-machine net savings.
The relaxed same-version native reference also passes its guest regression.

### Remaining native finite matrix fixed after pilot

The 256 MiB stream pilot completes 48 observations over gzip/xz/lz4. The
normal-module and relaxed-module references each complete 160 observations
over all five codecs. Fresh-scan differences persist in both controls; some
archive intervals remain noisy. Formal diagnostics are fixed at three
campaigns × eight blocks × one warm repeat, all five codecs and both tasks
for each reference. Stream formal sampling uses three campaigns × eight
blocks × two warm repeats, archive only over the three real SIFs. The separate
baseline labels prevent normal/relaxed modules from being pooled. These
diagnostics do not create an additive decomposition of hardening, PIC and
service indirection. `native-final-queue.json` interleaves these with primary
five-codec campaigns 04–07 after the nine formal application campaigns.

### Formal application and deployment audit checkpoint

The first xz and gzip formal campaigns complete with 384 observations each;
the remaining campaigns continue in the unchanged finite matrix. The independent
`audit_application.py` verifies every block/workload/backend/repetition key,
seeded order, summary point estimates, saved native manifests, six PFNs before
and after private-state observation, and restoration/unload. Raw runner assertions
check every application output before recording timing; per-sample output
manifests are transient, with native/preflight manifests retained.

Registration accounting uses the actual packaged module's DWARF: transaction
688 bytes plus six 64-byte binding records = 1072 requested bytes, excluding
slab rounding, sockets, file objects and page tables. The packaged module matches
the retained build byte-for-byte. Successful registration drops references to
the displaced ordinary pages; it does not retain a full backup copy. One-shot
registration exits before application sampling. The observer-free deployment
check is queued after native timing. It also records GNU time resource reports
for each deployment command; those instrumented stages stay separate from
uninstrumented campaign stage samples. Outer wrappers now save their own source
and hash; the benchmark runner and evaluated binaries are unchanged.

### Identified FUSE cache-policy confound and diagnostic extension

The evaluated LKL frontend explicitly sets entry/attribute/negative timeouts to
zero (`tools/lkl/lklfuse.c`, init callback). The SquashFS VKSO frontend leaves
libfuse 3.10.5 entry/attribute defaults at one second (negative zero), while
retaining private inode/name caches. The official release source confirms those
defaults: https://raw.githubusercontent.com/libfuse/libfuse/fuse-3.10.5/lib/fuse.c
(lines 4620–4622). This is a concrete attribution gap for metadata workloads,
not evidence that sharing itself accelerates metadata operations.

Preserve all default-profile formal campaigns. `lkl/cache_frontend.py` builds
a separate SIF frontend changing only entry/attribute assignments from 0 to 1;
it keeps the same LKL library, 512 MiB heap, single FUSE request thread and
compiler options. The distinct output binary, patch, commands and hashes remain.
The benchmark gained optional diagnostic-backend/subset/group arguments; their
defaults leave the existing six-backend workload and seeded order unchanged.
The diagnostic is labeled `application-cache` and cannot pool with default runs.

A build plus three one-block pilots (gzip/xz/lz4, all four tasks, stock/copied/
VKSO/LKL512/LKL512-cache1) is queued after all original formal timing and
analysis. It verifies the new frontend and all application outputs before
further sampling. Initial diagnostic design is three campaigns per format,
eight randomized blocks, one fresh execution per cell (1440 observations).
Its purpose is to resolve material cache-policy effects, with a target of about
5 percentage points rather than tiny sharing equivalence. Review pilot behavior
before launching formal diagnostic campaigns; retain all signs of the effect.
The paper cannot close its competitive-LKL interpretation before this gate.

### Mutable-binding identity strengthened and executed

The PFN observer now also locates the native owner's `sq_support` table in
module kallsyms and observes its physical backing. In actual
`squash-application-lz4-formal-02` preflight/resource observations, copied and
shared user tables both have PFNs distinct from the kernel table. All six
shared code/readonly PFNs still match. This is an untimed evidence-only change;
backend instructions, callbacks and formal workload order are unchanged.
Earlier snapshots retain their original schema and are not retroactively
represented as having this extra check.

### Evidence refinements during the serial campaign queue

The untimed PFN observer now also records hashes of the six mapped read-only
pages. Later campaigns and the matched-cache diagnostic can therefore compare
actual copied/shared mapped bytes directly, in addition to the existing
materialization-from-registered-owner construction and PFN evidence. Earlier
campaigns retain their original records; absent byte hashes are not backfilled.
This changes observation only, not evaluated binaries or timed workload code.

The source ledger now includes the actual generated shared_types/shared_remap
headers (359 lines of native support including metadata and kernel bindings),
the common-owner source separately (2,238 lines including reused bodies), the
364-line preparation generator, and raw generated-consumer diffs across 16
changed files (57 added/2,099 removed). Those deltas include mechanical moves
and are not semantic-work counts. The 45-line owner runtime header is inherited.
The LKL cache diagnostic is separate from its 30-line SIF integration.

The normal/relaxed module instruction audit is now executed in
`build/squashfs/reference-build-audit-01`: normal read-inode/readdir/read-data
retain stack-check references, normal readdir/read-data retain indirect thunks,
and all six inspected normal functions retain return thunks. The corresponding
relaxed functions contain none of these references. No inspected function in
either module contains an fentry reference; compiler settings alone were not
used to assert that such instrumentation executed. Module hashes and compile
commands are retained.

The maintenance artifact audit now covers all 126 regular files in the retained
old/fixed build directories. Of 54 changed files, the sole changed extracted
or handwritten C/header source is `shared_core.c`; rebuilt compiler metadata
and module identities account for other changes. The consumer's relocatable
`.text` bytes are unchanged; its differing read-only strings are old/fixed
build-directory paths. The owner changes its text and build metadata. Actual
guest-package owner/consumer/bridge/frontend binaries match those audited
builds, and all user executable/bridge products remain unchanged.
`maintenance-artifact-audit-02.json` preserves every hash and ELF section delta.

The native/user boundary audit also distinguishes the ten VFS operation-table
fields from the 46 callable services. Native bindings populate those fields;
the user initializer leaves them null because FUSE callbacks expose the
operations. The upcoming cache pilots record these actual values and explicit
user addresses for filesystem, stream and cache-buffer objects. This adds
untimed observation only. Source counts and manuscript descriptions now make
this boundary explicit instead of implying ten user VFS implementations.

## Consolidated finite matrix (completion is checked by final_analysis.py)

| Evidence group | Formats | Independent campaigns | Within-campaign design | Formal observations | Question |
|---|---|---:|---|---:|---|
| Native primary | gzip/xz/zstd/lz4/lzo | 7 | 12 blocks; original/prepared; scan/archive; fresh + 3 warm | 6,720 | Total preparation cost on a common tree |
| Native larger archive | gzip/xz/lz4 SIF partitions | 3 | 8 blocks; original/prepared; fresh + 2 warm | 432 | Preparation with 256 MiB sequential content |
| Native normal module | All five | 3 | 8 blocks; reference/prepared; scan/archive; fresh + warm | 960 | Same-version patched module control |
| Native relaxed module | All five | 3 | Same as normal-module control | 960 | Selected compiler-setting diagnostic |
| Default application | gzip/xz/lz4 SIF | 3 per format (9 total) | 8 blocks; 6 backends; 4 tasks; 2 fresh executions | 3,456 | Full lifecycle and identical-core backing effects |
| Matched-cache application | gzip/xz/lz4 SIF | 3 per format (9 total) | 8 blocks; 5 backends; 4 tasks; 1 fresh execution | 1,440 | Concrete FUSE cache-policy confound |

The total is 34 campaigns and 13,968 timed observations when every gate passes.
Pilot samples are separate. The three application formats cover a common
container format (gzip), a stronger compression mode (xz), and a fast decoder
(lz4); all use 128 KiB blocks and the same logical payload. The larger task
contains both repeated text and seeded pseudorandom data, so its result is for
the specified mixture, not an isolated compressibility effect. Native five-codec
measurements cover the preparation question for zstd/lzo without pretending to
measure their Apptainer lifecycles. Block-size effects, random-I/O performance,
concurrent scaling, cold-storage latency and cross-machine/boot performance
remain outside measured scope. Functional boundary/random reads are separately
verified. These omitted combinations therefore limit extrapolation rather than
removing any failed measured cell.

The complete default application observations also resolve the sharing question
unevenly: all nine non-empty task point estimates are close to one, while the
lz4 empty-command interval is much wider. The final claim judgment must retain
that startup uncertainty; it cannot describe all application paths as equivalent.
The fixed matrix does not stop or extend sampling based on achieving an advantage.

### Cache-policy preflight passed; formal diagnostic released

All three cache pilots complete 20 correctly keyed real application samples
each, native-before/after equality, copied/shared byte and PFN checks, user
state inspection, restoration and unloading. The ten user VFS operation-table
fields are observed null; filesystem, stream and cache buffers are in user
addresses. The positive-cache change affects metadata-heavy LKL tasks in the
preflight, confirming the relevance of this diagnostic. These 60 observations
are excluded from formal estimates.

Proceed with the already fixed nine-campaign/1,440-observation cache matrix.
Its approximately five-percentage-point precision aim uses the completed
default experiments' variability; short startup remains a known less-precise
case. The schedule is fixed before diagnostic formal observations, retains
all tasks and all campaigns, and does not use a favorable-result stopping rule.
The final implementation/runner snapshot before these runs is
`build/squashfs/evaluation-fixed-05`; the evaluated binaries still come from
`evaluation-fixed-01/build`, with a separately identified LKL cache frontend.

### Additional xattr semantic coverage gap

A final capability-to-fixture check found that the existing mounted regressions
verify `user.*` but do not instantiate the declared `security.*` handler.
`functional_extra.py` adds valid five-codec fixtures with an empty-permission
`security.capability` value, empty user value, 2,048-byte user value and the
existing ordinary user attribute. It checks exact values/lists, size-query and
ERANGE behavior, absent ENODATA, links and boundary reads across original,
prepared-before, copied, shared and prepared-after mounts. PFNs, restored
carrier bytes and unload are also required. These are additional functional
cases, not timing samples or malformed images; image construction and execution
wait for `cache-formal-queue-01` to finish. Completion requires all 25 mount
cases on the unchanged final binaries, or an explicit failure diagnosis.
This closes a declared semantic gap instead of removing the security namespace
from the stated interface.

## Final resolution of the initial evidence gaps

All 34 formal campaigns complete, with 13,968 observations and passing independent
statistics audits. The final matrix is `build/squashfs/final-analysis-02/matrix.csv`;
per-campaign estimates retain the hierarchy. The complete fixed-version evidence
and explicit unsupported extensions are indexed in `claim-verdicts.json`.

| Initial question | Final evidence | Judgment and sufficient scope | Remaining external validity limit |
|---|---|---|---|
| Shared execution and private services/state | Fixed-owner five-format regression; 25 extra semantic mounts; copied/shared PFNs and equal mapped bytes; actual SIF output; native restore/unload | Supported for tested read-only interface; all required functional gates pass | Not arbitrary Linux VFS features or write support |
| Preparation cost | Seven five-format primary campaigns plus three each normal-module, relaxed-module and sequential controls; emitted instructions audited | Measurable archive/scan effects; zero-overhead generalization rejected | No pure PGOT attribution, other CPUs or boots |
| Sharing increment | Nine default and nine separate cache-control application campaigns, identical core and adapters | Small nonempty-task differences with reported CIs | Startup precision does not establish an equally tight bound |
| Complete application | Three real SIF codecs, four tasks, stock and translator controls, copied/VKSO, competitive LKL512 plus64, cache-matched LKL | Useful but task-dependent gains; adverse stock comparisons retained | No zstd/lzo application-performance or concurrency extrapolation |
| Adaptation work | Final stage-separated source ledger, generated versus handwritten code, two exporter changes, matched LKL application glue | Concrete reuse and cost measured; human-time advantage not supported | No invented hours or whole-LKL-size comparison |
| Resources/deployment | Process PSS/RSS/USS, private allocations, kernel residency, registration, stage timing and observer-free application | 24 KiB physical backing reuse; conditional and dedicated deployment costs stated | Net machine saving not established; no multiplication by process count |
| Common repair | Old/fixed native/copied/shared and patched unadapted controls; valid/invalid inputs in guests; exact artifact hashes | Known repair reaches both domains with unchanged user binaries; normal regressions pass | Rebuild/redeploy required; no hot-update inference |
| User debugging | Re-audited ISO9660 GDB breakpoint/arguments/stack/step and PFNs before/after plus native regression | Feasible for the demonstrated shared instruction path | No human-time study or TCG performance interpretation |

This resolves the finite Section 6.5 framework without substituting historic
single-run data for final-version measurements. Wider extensions remain explicit
unsupported claims, not silently removed success criteria. No result was excluded
for an unfavorable sign; campaign-specific failure/provenance records remain.
