# Section 6.5 claim-to-experiment map

The Introduction in `paper/paper_content/Paper Draft.md` asks which resident
binary closures can be reused, how they can be rehosted without copying the
execution body, and which duplication and execution/deployment costs result.
Its contribution overview now also identifies the filesystem case as a test
of independent native/user objects and existing application backends. This
alignment does not turn filesystem-specific speedups into a prior assumption.
Current Design sources are identified in [research-protocol.md](research-protocol.md).

Sections 6.1–6.3 measure backing, dependency indirection and algorithm reuse.
Section 6.4 evaluates shared live time state. Section 6.5 evaluates common
format logic over **independent native and user objects**, including actual
application integration and repair. A filesystem exposes persistent format
semantics, object lifetimes, caches and environment services that an isolated
function call cannot test. SquashFS supplies real Apptainer SIF execution;
ISO9660 supplies complementary mounted-filesystem and debugger evidence.

The finite matrix and its coverage rationale are in
[refinement/README.md](squashfs/refinement/README.md); prospective selection
and stopping rules are in [refinement/PROTOCOL.md](squashfs/refinement/PROTOCOL.md).
[STATUS.md](STATUS.md) records the completed matrix and its limits. Final judgments
are recorded, without removing adverse results, in [claim-verdicts.json](claim-verdicts.json).

The current matrix uses the final XZ-composed owner: 30 complete campaigns,
6,540 observations and 403 independently replayed comparisons. The preceding
39-campaign publication is preserved separately. The server-interrupted partial
campaign is retained and replaced by a whole same-parameter campaign, not by
selected blocks. Detailed findings and verdicts are in `claim-verdicts.json`.

| Claim | Testable question | Experiments and controls | Metrics | Final evidence | Remaining gap / interpretation | Completion condition |
| --- | --- | --- | --- | --- | --- | --- |
| C1: one resident body, private environments | Do real native and SIF consumers execute the same body with separate state? | Five-format original/prepared/copied/shared; x86 BCJ fixture; native A and actual SIF B/C; decoder entry probes | Content/metadata/links/xattrs; 22,032 boundary/random reads per user backend; code and private-object PFNs; lifetimes | `squash-refine-xz-functional-01`, `-guest-01`, `-execution-01`, `-native-calls-01`, `-bcj-02` | Read-only scope; gzip/zstd/lzo services remain separate | Correct semantics, nine shared PFNs only with shared backing, private bindings/objects, native regression and cleanup: passed |
| C2: native preparation cost | What is the final owner's cost against matched native references? | Same-campaign original, optimized normal/relaxed native, preceding owner and final owner; five formats, scan/archive fresh/warm; xz/lz4 large archives | Absolute times, paired differences/ratios, campaign CIs, object-code hardening audit | `refined-analysis-01`, `squash-refine-hardening-02` | Native canary/thunk runtime parity is unimplemented; no pure-indirection attribution | Final owner measured directly in three campaigns per cell, matching work/output; configuration gap reported |
| C3: sharing increment | What changes with identical instructions and support but different backing? | Copied/VKSO ordinary tasks; separate equal-path xz/lz4 scan/stream and single-CPU gzip stream | Byte/PFN identity, paired time and campaign CIs | Formal application, decoder-diagnostic and sharing-singlecpu groups | Default points are close; equal-path intervals are broad, so no universal tight bound | Complete all planned conditions and retain their separate estimates; passed without equivalence claim |
| C4: useful real applications | Does the full adapter help against credible backends, including an independent task? | Stock/default, stock/single-thread, stock+translator, copied/VKSO, LKL default/matched cache; three SIF codecs/four ordinary tasks; gzip/xz Python compilation | End-to-end time, CPU observations, output oracle, 647 bytecode files | Nine ordinary and six held-out campaigns; heap pilot and decoder-work audit | Stock single-thread removes most gzip/lz4 metadata advantage; xz stream and held-out compilation lose | Report all tasks, thread/cache controls and adverse held-out result; no task replacement |
| C5: reuse and adaptation work | What original logic is retained and what preparation/support is required? | Original body/source comparisons; native patches; generator/generated support; first bridge; application glue; common repair | Functions, original lines, semantic edits, bytes, interfaces and artifact changes | `refined-analysis-01/costs.json`, `refinement-reuse-audit-03` | 2,604 unchanged XZ lines and larger executable text establish reuse, not human-hour savings | All stages and starting points accounted; no whole-project LKL comparison |
| C6: conditional resource benefit | What backing is avoided, and how do private costs grow? | PFN union, helper RSS/PSS/USS/HWM; 1/4/16 metadata ladder; native component and registration ledger; minimal owner deployment | 36 KiB shared backing; helper snapshots; 108 versus 60 KiB native components; 1,264 requested metadata bytes | `refined-analysis-01/resource-ledger`, resource-scale 01/04/16, minimal-deployment-01 | Private inode/name retention reaches 88.89 MiB PSS, exceeding SquashFUSE at largest scale | Include platform premise and scale reversal; do not infer whole-machine saving |
| C7: common repair | Does a targeted upstream fix repair both domains with unchanged adapters? | Guest-only old/fixed × native/copied/shared; patched unadapted reference; final-owner guest regression | Target panic, daemon signal/client result/survival, patches and hashes, normal regression/cleanup | `squash-maintenance-02`, retained maintenance ledger, `squash-refine-xz-guest-01` | Known defect; copied shares the repair; rebuild/redeploy required | Multi-signal old failure and successful fixed application behavior: passed |
| C8: user debugging | Can user tools inspect shared instructions without losing identity? | Real SIF XZ hardware breakpoint; retained ISO9660 breakpoint/step; subsequent native regression | Arguments, available stack, PFNs before/after, cleanup | `squash-refine-xz-execution-01`, `maintenance-oneshot-01` | Single-step evidence belongs to ISO9660; no human-time or TCG performance inference | Actual replay with identity/lifetime checks: passed |
| C9: developer/debugger time | Is a matched human-time advantage measured? | Audit available history and controlled-task evidence | Reliable hours at matched starting points | Cost/maintenance ledgers | Not supported; code size is not elapsed effort | Explicit unsupported verdict, no invented hours |
| C10: net memory / cheap cold deployment | Do all incremental costs support a system-wide benefit? | Already-resident, original-to-prepared and user-only premises; setup stages | Separate backing, native/module, requested metadata and process costs; stage times | Resource ledger and minimal deployment | Not supported as a whole-machine total; generic 32 KiB platform is excluded from business, not hidden | Report preparation/private costs and deployment range; no unqualified net-saving claim |
| C11: hot update / scaling / generality | Are these stronger extensions tested? | Audit repair lifecycle, simultaneous consumers and environment coverage | Existing-process update, throughput curve, hosts/boots | Protocol, simultaneous consumers, independent audit | New consumers, one host/boot; metadata scale is not process-count throughput | Explicit unsupported verdicts |
| C12: generally preferable to copied | Which benefit uniquely requires native physical reuse? | Same-core copied, shared PFNs, common maintenance and user-only deployment | Unique backing, complete-task intervals, owner requirements | Analysis/resource/minimal-deployment records | Copied retains algorithm/repair benefits and can run without owner; no general preference | Conditional resident-core use case and costs stated |
| C13: application motivation | Is resident native-body reuse a useful concrete application path? | Native + real SIF consumers, SquashFUSE/LKL tasks, copied attribution, maintenance and resources | Correct output, time/resource tradeoffs, original implementation reuse, private state | All final evidence groups and `refinement/RESULTS.md` | Selected tasks support usefulness; held-out xz and large-directory memory restrict generality; Rump has no timing row | Complete fair finite matrix and explain both benefits and costs: satisfied within stated scope |

## What supports or limits the claims

| Claims | Supporting outcome | Limiting or contradicting outcome | Confounds controlled or retained |
| --- | --- | --- | --- |
| C1, C7, C8 | Matching application-visible semantics; identity and lifecycle checks pass; the targeted repaired failure disappears | Wrong content/metadata, shared mutable state, different backing, unrelated crash accepted as reproduction, failed native regression | Original native oracle; copied negative PFN control; actual application execution; failure signals plus target location; guest-only malformed input |
| C2, C3 | Paired cost and uncertainty are small in the stated tasks; improvement survives appropriate diagnostic controls | Positive overhead, broad intervals, differing logical work, context-sensitive effects | Same inputs and final binaries; paired random order; campaign hierarchy; equally optimized native references; explicit loader controls; retained build differences |
| C4 | Faster or competitive complete tasks with correct output against credible baselines | Slower tasks, favorable cache/heap mismatch, omitted startup or setup cost | Real SIF tasks, stock translator diagnostic, LKL heap sensitivity and matched positive caches, whole lifecycle timing; remaining backend differences disclosed |
| C5, C9 | Original logic and repair are actually reused with an explicit support-code ledger | Adapter/generator work omitted; smaller glue inferred to mean fewer human hours | Same starting point and supported scope; physical lines are proxies; no fabricated historical effort |
| C6, C10 | Unique shared pages observed and the relevant residency premise stated | Registration/private/resident costs outweigh backing avoided, or snapshots are mistaken for system totals | Pre-observer process snapshots; separate requested allocations/module costs; ordinary DSO sharing; copied runtime after unload |
| C11 | Only a dedicated experiment could support each extension | Present evidence does not establish it | Simultaneous task lifetimes, fresh-process repair and one-boot timing are not substituted for stronger tests |
| C12 | A use case already needing the owner/support can reuse the observed native backing | Dedicated deployment adds costs while copied retains performance/repair benefits | Distinguish common implementation reuse from the additional physical-backing property; no general preference is inferred |

C13 is supported by correct real SIF execution, selected competitive task times,
smaller small-tree helper snapshots and common-core identity/repair. The held-out
xz loss, single-thread stock results and large-tree memory reversal limit the
claim. None of these comparisons is a human-time study or a whole-machine total.

No trial stops on favorable significance. Failed development runs, the slower
forced-inline candidate, xz regressions, loader-context changes and imprecise
intervals remain in the record. New experiments resolve named uncertainties;
the selected matrix does not exhaust every compression/data/concurrency case.

## Installed-platform business accounting

The user selected an installed VKSO platform as the application premise.
`page_cache_replace` (32 KiB) is charged once at platform scope, not to every
filesystem or process. `refined-analysis-01/resource-ledger/resources.json` retains native preparation
(108 versus 60 KiB), registration metadata (1,264 requested bytes), and private
helper state. An already prepared resident native service avoids one 36 KiB
copied backing when adding a user consumer. This scope change does not modify
any sample or imply a whole-machine total. Related-work roles and measured
versus conceptual comparisons are in `related-work-comparison.md`.
