# Active Section 6.5 optimization (2026-10-30)

## FINAL BUDGET CLOSEOUT — supersedes all running/continue notes below

- User requested conserving quota, completing the core, then stopping. No new
  candidates, expanded studies, manuscript/PDF or automatic continuation.
- Safely stopped dispatcher PID2129032 ONLY while current child2244341 finished
  XZ02 336/336 and restored/unloaded. Then terminated dispatcher at complete
  campaign boundary. Cancelled waiting postprocessor2141744 and followup2187427
  with zero jobs started; their historical state JSONs remain untouched.
- Authoritative final record: RUNS/budget-closeout-01/stopped.json. All four
  process IDs absent, task modules unloaded. Do not restart queues automatically.
- Chronological completed prefix14/30,4580/7692 observations. Original interrupted
  127 records retained/excluded, whole replacement336 retained. No within-group
  exclusion. 423 descriptive comparisons, one/two campaigns per cell, no original
  three-campaign CI claim. Source/binary identity, pairing, PFN/mapped bytes,
  complete blocks, same boot, cleanup and independent numeric replay passed.
- CORE_RESULTS.md contains results, boundaries and paths. analysis.json,
  audit.json, resource-ledger.json and stopped.json downloaded locally.
- Key outcomes: native XZ fresh sequential -27.06% versus predecessor; ordinary
  XZ versus stock startup-43.81%,archive-19.24%,scan-54.56%,stream-3.43%.
  PythonXZ remains+16.38%stock/+7.04%matchedLKL; +0.32%copied. LZ4stream
  shared/copied+6.22% remains unresolved. No favorable selection.
- Scale16 copied bounded/unbounded PSS19886/91004KiB (~-78.1%); VKSO19899,
  stock28892,stock-single13199. Cache gain is not physical-sharing gain.
  Residual anonymous growth unlocalized; queued live-probe/candidate CANCELLED.
- Matched prepared-native business disk288/324KiB shared/copied; user-only
 228/184KiB. Shared backing9pages36KiB, not whole-machine net savings.
- Unrun local lowlevel/bittree candidate work is exploratory, NOT accepted or
  validated evidence. Preserve all data, old drafts and unrelated user files.

## Latest state (overrides older active/outstanding notes below)

- **USER DIRECTION UPDATED**: focus on sound experiments and genuine
  improvement, not merely preserving negative results. Continue hypothesis,
  diagnosis, candidate, correctness and fair-comparison cycles where justified.
  Do not assume source/physical sharing establishes total memory/disk benefit:
  separate shared code, private/cache state, kernel resident/incremental costs;
  separate carrier, duplicate code, dependencies/images/deployment disk costs.
  **PAUSE PAPER/PDF/PUBLICATION WORK.** Existing drafts remain uninstalled.
  postprocess.py now runs only numerical analysis/audit/cost/reuse/resource
  ledgers after confirmation. No automatic prose/reports/final freeze.
  Frozen current matrix is a fixed candidate comparison, not reason to stop
  investigating the Python regression or residual FUSE-memory growth.

- **FORMAL MATRIX RECOVERED AND RUNNING**: old SSH tty44063 was lost when
  local exec-server transport disconnected. Old queue PID2077515 disappeared;
  boot stayed 4d29e579-2621-4df3-97a2-8d359ed1f5ea. No task mounts/processes
  remained, but page registration/four task modules did. Exact termination
  cause is unproven. XZ app01 stopped at127 samples, all preserved.
- `recover_confirmation.py` already executed ONCE successfully; DO NOT rerun.
  RUNS/confirmation-recovery-01 records 9-page restore and four unloads,
  all return0, partial/evidence hashes, selected-queue.json and matching
  selected-registration.json (30 campaigns7692), remaining-queue.json (27).
  Three earlier complete campaigns retained unchanged. Only interrupted XZ
  campaign replaced fully with identical seed/settings and new -recovery01 name.
  Original formal-queue.json/registration and stale running results untouched.
- Detached root queue PID2129032, PPID1, SID2129032:
  RUNS/formal-recovery-queue-01. stdin /dev/null and persistent queue.log;
  independent Linux session survives SSH tool transport loss. New SSH tty16923
  has validated sudo, but does not own the queue lifetime. Do NOT compile, run
  QEMU/profilers/diagnostics or other load while formal timing runs.
  Light read-only status is okay. postprocess-01 failed before analysis because
  old PID absent; keep it. postprocess.py now targets fresh postprocess-02 and
  recovered selected queue; launched detached as ordinary user PID2141744.
  It waits, then analyzes/audits/costs/reuse/resources only, no prose or PDF.
- **Latest verified status 2026-10-30 ~04:52 UTC**: original three completed
  groups plus replacement XZ app01 and LZ4 app01 are complete (5/30).
  Python/gzip01 was running with44/48 samples. Root queue2129032 is PPID1,
  SID2129032, elapsed14m24s; analysis waiter2141744 and follow-up waiter2187427
  are PPID1 with their own SIDs. Local exec-server briefly disconnected AGAIN,
  but a fresh SSH check confirmed all three remained alive. Do not restart.
- `followup_queue.py --detach` already launched root PID2187427, output
  RUNS/followup-queue-01, status waiting/jobs[]. It waits for BOTH recovered
  formal queue and postprocess-02 success, verifies source/frozen hashes and
  absent task modules, then serially runs:
  1. component_ledger.py -> RUNS/component-ledger-01 (saved smaps + actual disk
     logical/allocated files, ELF sections, dependencies/images, deployment scenarios).
  2. fuse_memory_diagnostic.py -> RUNS/fuse-memory-diagnostic-01 (normal user,
     original3scale SIFs, production vs instrumented frontend,2tar passes each,
     exact archive hash gates, libfuse3.10.5 live table/slab ABI invariants).
  3. bittree_diagnostic.py -> RUNS/bittree-diagnostic-01 (one new common-algorithm
     diagnostic: fixed-depth3/6/8 tree unrolling, unchanged rc_bit;32768
     ASAN/UBSAN tree-state comparisons, existing244validstreams,8originalblocks
     x5conditionsx5rounds=200obs; not production or native/PFN validation).
  4. Three Python/XZ attribution campaigns (8blocks x stock/library/common-retained/
     copied/VKSO=120obs), existing final binaries and original image/oracle,
     equal loader paths, then separate analysis. No pooling with main7692.
  Protocol `FOLLOWUP_PROTOCOL.md` and `followup-queue-01/source-registration.json`.
  These files are hash-frozen while waiting; do not edit them silently. If any
  stage fails, the queue stops, logs retained; inspect before a new named retry.
- Local smaps analysis of existing large-scale VKSO snapshot completed:
  PSS19895KiB (per-VMA sum) vs rollup19899KiB; heap2348KiB, anonymous17120KiB.
  Do NOT yet attribute all anonymous bytes to FUSE: live-object probe pending.
  Carrier logical size65016B; actual allocation/deployment delta pending ledger.
  Libfuse official3.10.5 source shows separate path/node tables/slabs; no
  allocation ownership or savings claim until measured. Core PSS category
  must not be treated as proof against native/user PFN sharing.
- Additional factual checks while timing (light stat, offline saved-smaps):
  carrier and copied are both65016logicalbytes; allocated blocks are56 vs128
  in512-byte units, i.e.28KiB vs64KiB, exactly36KiB saved on that backing.
  owner.ko is80832logical/81920allocated; consumer60232logical/61440allocated.
  Thus an already-prepared native deployment saves36KiB backing here, whereas
  user-only owner+carrier is108KiB allocated vs64KiB copied before other common
  files/platform. Full ledger with dependencies/images is still pending.
  Offline scale1/4/16 smaps sums: PSS4274/7448/19895KiB; heap2344/2520/2348;
  other anonymous1520/4492/17120. Rollup differs by4-5KiB rounding. Anonymous
  growth dominates; actual FUSE object attribution remains pending probe.
- **LOCAL ONLY, not uploaded/built/run/promoted** possible memory candidate:
  `fuse_lowlevel_frontend.c`, `lowlevel_node_api.inc`,
  `build_lowlevel_candidate.py`, `validate_node_ids.py`.
  Stable immutable inode location encoded as nodeid=location+2, root1;
  bounded second location hash index in private bridge, open handles stillpin;
  no per-kernel-nlookup heap object required. Preserves DT_UNKNOWN hints to
  avoid silently adding readdir-type optimization as a second factor.
  Root is constructed via new_inode/read_inode OUTSIDE iget: prototype sets
  location=-1 and excludes root from location index, so it cannot alias ref0.
  Builder is gated on completed follow-up and measured material FUSE slab
  growth; copies a new build, only bridge/frontend changes, verifies owner/
  native/decoder/helper hashes unchanged. New API unit test reloads8192stable
  IDs3times, checks24576contents, hardlinks, parents, pins and cachebounds.
  This prototype is NOT evidence yet; it still needs build, correctness,
  realFUSElifetime, guest/PFN and original-workload timing if hypothesispasses.
- Prototype frontend also preserves actual helper options verified in trace:
  allow_other,ro,uid=1000,gid=1000. It parses/removes uid/gid and optional
  entry/attr timeout controls before low-level session creation, applies the
  same ownership override, and preserves 1s defaults. No new permission policy.
  C compilation has NOT run yet; Python syntax checks only passed locally.
- Also LOCAL ONLY pending scripts: `audit_python_attribution.py` (independent
  120obs/cells/PFN/identities/campaign-CI replay after followup analysis) and
  `backend_disk_ledger.py` (evaluated full backend file manifests incl stock/
  LKL, debug sections and inode-deduplicated dynamic dependency unions;
  preserves installed-native vs user-only and common-image/platform boundaries).
  Upload/run after primary timing/follow-up gates. Do not confuse preparation
  with completed evidence. Main snapshot currently12complete then gzip02
  nearcompletion; next compact read reported13complete and XZ02 at31/336.
- Attempt to send a status via multi_agent.send_input to parent cloud-thread
  ID failed "agent ... not found"; these are different runtimes. No subagent
  was spawned or unrelated agent changed. Parent needs commentary/final/log
  status, but current assignment says persist until actual experiment/attribution
  delivered. Do not end just because queues were launched.
- audit.py now strictly verifies recovery derivative against original
  registration, same settings/identities/boot, all127 partials preserved and
  excluded only as an interrupted campaign. All completed observations remain.
  write_section/reports/final_evidence explicitly disclose this interruption.
- RUNS is /var/tmp/vkso-section65-optimization-20261030-hBcg9Y, with repo
  entry test/section65/build/squashfs/optimization-runs-01. The registration
  `confirmation-registration.json` freezes 30 campaigns / 7692 observations:
  native tree3360, native stream672, ordinary apps3024, Python288,
  decoder240, singleCPU108. Three campaigns/group, original counts/seeds/inputs.
  The native matrix has 7 conditions (incl old and new references).
- Production candidate is frozen staged builds/optimization-cache-01.
  No more algorithm/cache-budget/flags changes. Native references bundle the
  identical edited XZ without VKSO; disclose this module packaging boundary.
  Decoder library/retained controls staged byte-identically on RUNS filesystem
  for equal-loader hardlinks. Registration hashes production and exact runners.
  Do not modify registered files (including PROTOCOL.md, C/inc sources/builders).
- All 7 validation queue jobs completed: original metadata scales1/4/16;
  shared-decoder-01 (160 observations, SINGLE/PREALLOC, copied/shared PFNs,
  held FUSE handles/cursors, restored/unloaded); native-calls-01 (XZ190,LZ473);
  minimal-deployment-01 (owner-only and copied after unload); hardening-01.
  Core remains no-SIMD and inherited SSP/thunk gap is explicitly unresolved.
- Original scale VKSO retained PSS4279/7452/19899 KiB; same-core unbounded
  copied7183/23964/91004 KiB; at largest stock28892/single13199/LKL513981 KiB.
  Traversal counts include root:5867/23465/93857; paper entries exclude root.
  Substantial reduction but not constant process memory, nor below single stock.
- cache-scale-direct-01: each original image scanned3times; retained counts
  2048/4096 throughout, direct harness PSS2376..2436KiB, allocator trim only
  saves16..40KiB (diagnostic-only, no production allocator changes). FUSE
  process growth is not explained as continued unbounded inode/name retention;
  precise remaining component attribution is unmeasured. Do not subtract these
  different-process snapshots as calibrated libfuse cost. C compiled with one
  cosmetic misleading-indentation warning; executable and source unchanged.
- metadata-work-01 reran current binaries: stock137blocks/1106363decodedbytes,
  copied/common and copied/library76/558231; three replays agree. Old counts
  happened to repeat, but this is fresh final-version evidence.
- perf-range-comparison-01 complete: word3.085Bbranches/362.86Mmisses,
 25.384Binstructions,6.0352s; branchless2.627B/245.24M,36.158B,6.2960s.
  Fewer misses but ~42% more instructions and ~4.3% longer. Rejected,
  not claimed to resolve Python application loss.
- Preliminary costs and reuse audit COMPLETE in RUNS/analysis-01; this
  directory already exists. **Use RUNS/analysis-final-01 for final analyze.py
  output**, then regenerate costs/reuse there AFTER scripts are final, because
  cost ledger hashes all source/harness files. Do not overwrite preliminary
  costs or old-version analyses. Current owner .text28052 vs prior27828;
  XZ original2604 ->2637physical lines, only dict_repeat body edited;
  diff35added/2removed (block replacement5->38). Bridge524/POSIX154/frontend314.
- Local adapted scripts: analyze.py/audit.py (7692, registration identities,
  strict cells/oneboot); resources.py (new fair native residency+oldboundary);
  cost_ledger/reuse_audit truthful edits; final_evidence.py updated but NOT RUN;
  freeze.py includes optimization/incs/newplot; archive_publication.py prepared
  but NOT RUN; write_section.py/template, plot_filesystem_optimized.py and
  build_filesystem_section.py adapted locally, NOT yet uploaded or executed.
- PDF skill fully read. Required artifact marker successfully ran ONCE with
  edit/1/pdf at local plugin path. Do not rerun. Final PDF must render + inspect.
  Charts widget skill inspected but not used: repository scientific figures
  stay in existing Matplotlib reproducible pipeline. Library previously read;
  attachments unavailable, user resolved task through server files.
- Canonical paper/documents remain UNCHANGED. Local docs/ contains copies of
  STATUS, README, backend-conditions, claim-map, reproduce, alignment, canonical
  06-evaluation.tex. For Chinese reads use [Console]::OutputEncoding =
  [System.Text.UTF8Encoding]::new() plus Get-Content -Encoding UTF8; previous
  garbling was output encoding, not source corruption. Preserve user dirty files.
- Before publication run archive_publication.py after timing. It snapshots
  exact scoped old paper/PDF/figures/docs to paper/build/section65-preoptimization-publication-01
  and hashes canonical prefix before6.5. Then update only6.5 and its docs.
  Final evidence asserts prefix unchanged and prior archive intact.
- Important prose correction: Python workload was a historical holdout but
  consulted in THIS optimization; call it fixed separate distribution task,
  NOT unseen holdout. All adverse startup/Python/native cells and uncertainty
  must remain. C9-C12 stronger claims stay unsupported.


This is an active task, not a completion report. User explicitly confirmed
`test/section65/handoff/20261030-01/HANDOFF_PROMPT.md` as the task, then supplied
additional review appended to `HANDOFF_PROMPT.txt` (read in full as a diff).
Priority: actual common XZ optimization, then bounded private metadata growth,
then final existing matrices, native/copied/shared regressions and Section 6.5
publication update. Do not stop at diagnosis or reuse old completion status.

Host: `zzk@10.177.21.196:50145`, root repo `/home/zzk/BinaryKernelCodeMapping`.
Linux 5.15.198, powersave, SMT off, no_turbo=1. Home initially 4.2 GiB available.
User has authorized sudo and an interactive SSH sudo session is established.
No credentials belong in this file or any script/log. Existing unrelated
worktree changes and user processes must be preserved. Never reuse old outputs.
Malformed images run only in isolated guests; no host reboot or setting changes.

Source written locally in this directory, uploaded to remote
`test/section65/squashfs/optimization-20261030-01/`. Baseline untouched:
`test/section65/build/squashfs/refine-xz-01` and `evaluation-refined-02`.

## Completed new work

- `optimization-xz-diagnostic-01`: failed build (missing profile header path),
  retained. Fixed include path in `diagnose.py`.
- `optimization-xz-diagnostic-02`: 280 observations, 8 fixed real XZ blocks,
  7 conditions, 5 randomized blocks. Inputs captured through actual copied
  filesystem reader from unchanged SIFs, checked against image hashes,
  rootfs reads and Python liblzma. Random stream samples are stored uncompressed
  and do not invoke XZ. Instrumentation never used for timing.
- Jump tables / small fixed memory helpers did not consistently improve this
  diagnostic. Ordinary reference used internal software CRC, so its slowdown
  was explicitly NOT attributed to preparation. Matching CRC added next.
- perf wrapper lacks custom kernel package; existing usable binary is
  `/usr/lib/linux-tools-5.15.0-119/perf`. Do not install anything.
- `diagnostic-02/perf-compressible.data` + `.txt`: 2102 samples, dict_repeat
  53.85%, libz crc32_little 39.42%. `perf-python.data` + `.txt`: 2484 samples,
  lzma_main 68.71%, lzma_len 15.03%, dict_repeat 10.14%, CRC 5.46%.
- `optimization-xz-diagnostic-03`: 400 observations, adds dictionary-word
  candidate, PREALLOC version, ordinary-user same-libz CRC. Matching-CRC
  ordinary is approximately tied with prepared; no PGOT-total-cost claim.
- Word-copy candidate: scalar 8-byte forward repetition with distance >=8,
  wrapped-source boundary handling; distance=1 uses scalar repeated byte;
  original byte loop remains for small distances/remainders. No SIMD and no
  further hardening relaxation. This IS an upstream algorithm body edit and
  must change the former zero-body-edit cost claim if accepted.
- Three compressible sequential blocks: candidate CPU ratios 0.546, 0.536,
  0.537 against prepared. Python representative blocks approximately tied;
  tiny mount block noisy / one apparent regression. Not end-to-end results.
- `optimization-xz-valid-01`: 65,536 randomized dictionary-state comparisons
  under ASAN/UBSAN passed; 244 valid stream checks (SINGLE/PREALLOC, boundary
  sizes, repeats, random, BCJ) passed. Not native/PFN/guest regression yet.

## Additional progress after diagnostic-03

- `optimization-xz-diagnostic-04`: 200 observations, fixed eight blocks and
  five conditions. O3 has no consistent Python-data benefit and is rejected.
  Word-copy is retained as the single algorithm candidate, baseline flags kept.
- `optimization-word-01`: independent complete owner/consumer/user build.
  One XZ body edit (5 lines replaced by 38); baseline filesystem small-copy
  and maintenance edits also still exist. User decoder dependencies remain
  removed. `optimization.json` explicitly supersedes inherited old metadata.
- `optimization-word-guest-01`: COMPLETE. Five formats in native/copied/shared,
  valid/negative maintenance checks passed; EIO in all three repaired negative
  paths, user daemons alive, restored and unloaded. TCG takes about 5 minutes;
  console silent during construction, not evidence of a mount hang.
- `optimization-cache-01`: complete separate build with word optimization plus
  private inode/name cache. Budgets 2048/4096; LRU contains only valid unpinned
  inodes, root pinned, explicit open file/directory pin/release. Names retain
  image-local inode number + disk location, not freed pointers. Borrowed API
  lookup values valid until next allocating lookup; parent pinned within lookup.
  Extra live pinned handles / per-open-directory listings are outside budget.
  Only task-owned source copies modified; canonical source not promoted yet.
- `optimization-cache-valid-01`: 8192 files, 3 random scans, 828 content checks,
  hardlinks/xattr/symlink/255-byte name/directory retention, 26081 inode evictions,
  20710 name evictions. 2400 simultaneously pinned files remain readable;
  retained inode count returns from 2407 to 2048 after release. All passed.
- `optimization-cache-sanitize-01`: same valid fixture/tests with ASAN+UBSAN
  in private bridge objects; all passed. Core uninstrumented, Python leak scan
  disabled, not a whole-process leak proof. Symlinks reuse valid-01 fixture.
- `optimization-cache-guest-01`: COMPLETE, all three repaired negative paths
  EIO, daemons survive, five-format native/copied/shared complete, restored and
  unloaded. SSH session 80113 finished 0.
- `optimization-cache-fuse-01`: COMPLETE ordinary-user FUSE with valid churn
  fixture, 64 retained file descriptors, 3 directory seek/tell roundtrips,
  561 contents checks. After-pass PSS 4426/4423/4427KiB (only this functional
  fixture, not the original resource ladder); normal daemon exit/unmount.
- `optimization-decoder-controls-01`: built copied-library/copied-retained for
  cache candidate via existing refinement/decoder_controls.py; same owner.
- `optimization-native-controls-01`: built native-word-normal / relaxed from
  original native-small controls. Links matching original XZ with identical
  dict_repeat edit, ordinary native services, no VKSO bindings. New references
  are guest-validated (10 valid mounts), not host-timed yet.
- Home has ~3GiB remaining. New run data uses task-owned root-filesystem path
  `/var/tmp/vkso-section65-optimization-20261030-hBcg9Y` (161GiB available), with
  symlink `test/section65/build/squashfs/optimization-runs-01`. No data deleted
  or moved. Builds staged byte-identically under new runroot `builds/` so
  equal-loader hardlinks can stay on one filesystem. Source originals stay home.
- Under optimization-runs-01:
  `native-controls-guest-01`: complete normal+relaxed five-format guest suite.
  `functional-01`: complete 30 valid mounts including true x86 BCJ, native
  before/after, copied/shared PFNs and private service bindings, restored/unloaded.
  `simultaneous-01`: complete native A + two conflicting SIF B/C, private
  objects, independent exits, actual shared XZ hardware breakpoint and unchanged
  PFNs afterward, native after, restored/unloaded. Not throughput evidence.
- `PROTOCOL.md` uploaded before application samples; new finite development
  protocol and 5% pilot unchanged-path regression review flag, not an equivalence
  criterion. No final acceptance yet. Original fixed campaign counts planned.
- `prepare_pilots.py` ran once successfully. Generated `pilot-queue.json` (8
  jobs), `resource-queue.json` (3 untimed scales), `cache-control.json` (extra
  copied-unbounded build uses SAME current materialized core), `native-builds`
  and `native-references` (new optimized references + old ones distinct).
- **ACTIVE:** interactive SSH session 44063 now running sudo campaign_queue.py
  on optimization source pilot-queue.json, output runs/pilot-queue-01. Jobs:
  word ordinary XZ, word Python XZ; cache ordinary gzip/XZ/LZ4, cache Python
  gzip/XZ; native five-format pilot. Four blocks; pilot only. No QEMU is live.
  Do not compile, profile, run other benchmarks or QEMU during these timings.
  Reads, local editing/analysis preparation are okay. Poll queue/result and
  current job log; stop/diagnose actual failure, preserve failed outputs.

## Current next actions

Do not repeatedly vary layout or inputs. Need examine emitted code/cost.
Continue ACTIVE pilot queue. Then inspect paired word improvement, cache vs
same-core copied-unbounded, stock/single/LKL and native fair controls. Run
untimed 3-scale resource queue afterward. Candidate not yet promoted. Exact
guest entry is `squashfs/improvement/guest_regression.py`.
`functional_extra.py` handles valid formats/BCJ;
`improvement/simultaneous.py --trace-xz` handles native + two SIF consumers.

Cache source analysis: cached_inode includes full squashfs_inode_info, linked
all-list and 1024-bin index; cached_name retains parent/child pointers;
u_inode_noop does not release; close_image frees at unmount. High-level FUSE
stores inode pointers in open file handles and directory_handle; no file
release callback currently. A bounded cache requires explicit handle pinning,
stable name identity independent of freed inode pointers, safe hash/LRU removal,
and tests for hardlinks, open handles, directory cursors and cache churn.
Cache implementation and FUSE/native/PFN functional checks now exist. Formal
application/resource measurements are NOT done. No completion claims yet.

Outstanding: full candidate build, native/copied/shared behavior and PFNs,
actual application pilots including Python, cache implementation and resource
ladder, predeclared final protocol and affected formal matrix rerun, independent
analysis, code/resource cost ledger, canonical Section 6.5/figures/PDF/state and
freeze. Original 30 campaigns/6540 are historical, never new candidate evidence.

The preceding outstanding paragraph is the initial list; build/cache/functional
work has since been completed above. Still outstanding after pilot start:
- Await all 8 pilots, summarize via new pilot_summary.py (descriptive only).
- Resource ladder 3 runs with copied-unbounded included, stage binary hashes.
- Explicit shared-vs-copied same-block decoder diagnostic was not yet run;
  prior static block diagnostics only cover prepared copied/ordinary/library.
  Real shared SIF/XZ/PFNs have been validated but are a different granularity.
  `decoder_shared.c` + `shared_diagnostic.py` are now prepared/uploaded, NOT
  compiled/run. Run only AFTER pilot timing queue is idle, using sudo unshare
  mount namespace and staged cache build. It registers a new owner, runs valid
  FUSE churn for copied/shared with PFNs before/after via extended
  fuse_lifetime.py, then 160 samples (8 original blocks x 2 modes x 2 backings
  x 5 rounds), representative live PID PFNs per mode/backing, restore/unload.
  Starts own gcc before its diagnostic measurements, never beside formal work.
- Consider valid cache-churn fixture on materialized shared backing; the
  direct FUSE churn used libsq-copy.so while full shared small-fixture checks
  and simultaneous SIF lifetimes passed. Keep this evidence scope clear.
- Re-run native entry counts and minimal user-only deployment for final version.
- Freeze final candidate and controls, update formal queue/audit explicit
  native condition counts; baseline analyze.py hardcodes prepared-xz / old
  reference pairs, audit.py hardcodes 6540/9 pages/30campaign. Update logically,
  never disable identity or sample completeness checks. New ordinary native
  references include the same XZ body edit with normal/relaxed policies.
- Full fresh 3-campaign matrices, independent audit, current code/hardening/
  resource/setup ledger, canonical Section 6.5 only, figures/PDF (read PDF
  skill before render/QA), claims/docs and new freeze. No commits/push.
- Required claim-experiment-map.md and claim-verdicts.json now read completely;
  remember C9–C12 stronger claims remain unsupported even if optimization helps.
- First pilot `word-application-xz-pilot-01` finished, 112 observations, all
  seven variants, complete output/memory checks and four blocks. Queue moved
  to word-python-xz-pilot-01. pilot_summary.py handles application CPU as the
  sum of user_cpu_seconds and system_cpu_seconds (not an absent cpu_seconds).
- Native call counter already exists at
  `test/section65/build/squashfs/service-counter-02/service_counter.ko`;
  use existing improvement/count_native.py after timing queue, no rebuild needed.
- Cache gzip pilot completed (128 samples). Bounded copied/unbounded copied
  ratios archive1.0124, scan.9966, startup1.0156, stream1.0082. VKSO/default
  stock startup1.0780 and VKSO/copied startup1.0477, while CPU ratio ~1.0017:
  retain this noisy/possibly adverse startup point, do not ignore it. Other
  VKSO stock ratios archive.9486, scan.9434, stream.9504. One pilot, no CI.
- Cache XZ pilot also completed (128 samples), bounded/unbounded copied wall
  ratios archive1.0113, scan1.0041, startup.9932, stream1.0030; VKSO/default
  stock stream.9751 and /single1.0133. Queue moved to cache LZ4, then two
  Python pilots, finally native. All preserve startup/unfavorable results.
- Cache LZ4 pilot completed: bounded/unbounded copied archive1.0130, scan1.0006,
  startup1.0153, stream1.0163. VKSO/stock stream.9344; /single.9644. Thus no
  >5% cache-only point regression in the three ordinary codecs so far.
  Five of eight pilots done; cache Python gzip active at latest check.
- Both cache Python pilots COMPLETE. gzip bounded/unbounded copied .9982;
  VKSO/stock1.0011, /copied1.0006. XZ bounded/unbounded .9991; VKSO/stock
  1.1588, /copied.9972, /matched-LKL1.0675. Cache does not resolve XZ compile.
  **Current queue: 7/8 complete, native-pilot-01 running (560 planned rows).**
  After it finishes, do finite range branch diagnostic (if counters support),
  then select final candidate and perform pending resource/shared probes etc.
  No compilation/QEMU/profile until native pilot and cleanup complete.
  Session44063 remains active root-queue tty; sudo auth may expire afterward.
- **All 8 pilots COMPLETE, 1136 samples total** (112+24+3*128+2*28+560),
  queue/result and pilot-summary-complete-01/02.json saved. Native warm XZ
  archive prepared/new-normal wall1.0551, CPU1.0024: triggers review; preserve
  paired observations, no outlier removal or equivalence claim. Fresh XZ
  archive1.0211, scan1.0131 vs matched new normal; non-XZ fresh mostly near1.
  Some tiny warm cells have wall/CPU mismatches; inspect actual pairs and
  confirm in fixed three-campaign matrix, do not attribute without evidence.
- sudo reauthenticated at proper prompt in session44063 after queue finished.
  `perf-python-range-01.txt` under runroot: 3 reps of current word-only decoder
  on original Python block2/data0, 3000 decodes each; ~3.085B branches,
  ~363.34M misses (11.78%), 1.49IPC. Includes harness validation, not rc_bit-only
  attribution. Finite branchless hypothesis justified to test, not established.
- **ACTIVE now:** normal SSH exec runs diagnose.py --output
  `optimization-runs-01/xz-diagnostic-05` with conditions library,
  prepared-single, dictionary-word, dictionary-word-branchless,
  ordinary-matched-crc; fixed eight blocks / five rounds / 150 repeats. User
  informed. Root tty44063 idle at repo shell. Do NOT start concurrent timing,
  compile, QEMU or resource experiments until diagnostic finishes.
- Diagnostic-05 COMPLETE (SSH2841 exit0, 200 observations). Branchless
  candidate rejected: sequential CPU/baseline ~.60-.61 vs word~.54-.55;
  Python data ~1.01/1.02/1.03 vs word~1.01/1.01/.98, Python mount1.489 vs1.001.
  No consistent Python gain; not pursued as a production build. This is one
  bounded failed hypothesis, not proof that Python loss is unavoidable.
- `range-valid-01` passed 524544 rc_bit transitions under ASAN/UBSAN;
  `range-stream-valid-01` passed65536 dictionary states and244 valid stream
  SINGLE/PREALLOC/BCJ checks for branchless. No host module loaded for it.
- Tentative final choice remains staged optimization-cache-01 (word + bounded
  cache); pending original resource ladder and final independent checks. User
  told Python loss remains and further unbounded code/layout search stops.
- **ACTIVE now (updated):** root tty44063 executing perf_range.py on diag05,
  output runs/perf-range-comparison-01. Two 3-repeat user-mode counter controls
  on the same Python block, to explain rejected mask candidate. Do not overlap
  other workload. After finish, run resource queue and prepared
  shared_diagnostic.py (includes copied/shared FUSE churn PFNs), native counts,
  minimal deployment, final hardening/cost audit and final version selection.
  Normal SSH diagnostic2841 is complete. Root sudo was refreshed recently.
- Local Python3.12 compileall syntax check of all section65_opt scripts passed.
  This does not substitute for running newly prepared C/Python diagnostics.
- Read existing cost_ledger.py/reuse_audit.py/hardening.py/freeze.py. Necessary
  updates before final use: cost_ledger asserts unchanged XZ hashes and names
  category unchanged_xz_algorithm_sources; must explicitly compare original
  upstream hashes plus actual edits and change claims, not bypass assertion.
  Staged build is outside repo: old relative_to(ROOT) source inventory fails;
  use home candidate exact source/hash or safely label external staged path.
  reuse_audit hardcodes 2604 unchanged and old composition metadata. freeze
  omits new optimization subdirectory and .inc sources, and mislabels freshly
  built libsq-copy as unused historical. Extend freeze explicitly.
- New native control matrix has 7 variants (original, previous-XZ prepared,
  new prepared, old small-normal/relaxed, word-normal/relaxed), so unchanged
  formal block counts imply native/tree3360 + native/stream672 and total7692
  observations if the other original groups stay unchanged. Compute from queue
  rather than blindly hardcoding; old total6540 is not new-version evidence.
  Bundled native XZ references add module code to avoid changing host kernel:
  expose this residency boundary when accounting, not a calibrated whole-kernel
  replacement estimate. No new hardening relaxation.
- `pilot-summary-01.json` and `-02.json` are descriptive completed-pilot
  summaries, not formal intervals. Word-only XZ stream VKSO/default stock
  ratio .97473, /single stock 1.00719, /copied .99740. Python XZ /stock 1.1599,
  /single 1.1677, /copied 1.0005, /matched LKL 1.0666. Python loss unresolved.
  User informed without combining historical/current data as paired samples.
- Given unresolved Python and range-main hotspot, one additional bounded
  hypothesis is PREPARED but NOT RUN: scalar mask selection in rc_bit to avoid
  unpredictable conditional branches. First get perf branch/miss counters
  after queue idle; no claimed root cause yet. New range_branchless.inc and
  diagnose.py condition `dictionary-word-branchless` plus validate_range.py
  (2049 probability values x 256 states, normalization boundaries, ASAN/UBSAN)
  and validate_dictionary.py --variant support uploaded. No production change.
  If justified, run new diagnostic-05 with fixed original eight inputs and
  conditions prepared-single/library/dictionary-word/dictionary-word-branchless
  (optionally matched ordinary CRC), same five rounds. Preserve failure and
  reject if added arithmetic loses; do not search endless code/layout variants.
  A successful variant requires full valid-stream/SINGLE/PREALLOC/BCJ, new
  owner/native reference builds, guest and application pilots before selection.

## Tool transport notes (no secrets)

Local environment is Windows PowerShell workspace task-2. Use apply_patch for
local source edits; scp exact files to new remote source directory. SSH read and
normal-user commands use exec_command with require_escalated. Interactive
sudo session ID at last update: 44063, currently bash at remote
repo root `/home/zzk/BinaryKernelCodeMapping`, now executing pilot queue.
Use ONE shell line ending CR per write_stdin: multiple LF lines were mangled.
Use `perf --no-pager report` to avoid less. sudo authentication is tty-scoped;
separate SSH calls cannot reuse that timestamp. No module is currently loaded
by this task. No formal campaign is running at this update.
