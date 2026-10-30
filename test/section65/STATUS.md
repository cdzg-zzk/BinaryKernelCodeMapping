# Section 6.5 — optimization experiments complete

Current version: **word-copy XZ + bounded inode/name caches + 48 lazy data slots**.
Completed **30 campaigns / 8,172 observations**, with three campaigns per cell.
Independent replay verified **541 comparisons**; offline archive verification
checked **7,674 files in 50 archives**, including raw wall/CPU timing and intervals.

- [Experiment report](evidence/confirmation-20261030-02/final/analysis/EXPERIMENT_REPORT.md)
- [Claim coverage](squashfs/confirmation-20261030-02/CLAIM_COVERAGE.md)
- [Reproduction and sources](squashfs/confirmation-20261030-02/README.md)
- [Analysis / raw archive manifest](evidence/confirmation-20261030-02/final/manifest.json)
- [Completion and cleanup audit](evidence/confirmation-20261030-02/final/analysis/completion-audit.json)
- [Offline verification](squashfs/confirmation-20261030-02/bundle-verification.json)

## Main measured effects

- Python/XZ: VKSO/stock **+2.98%** [95% CI +2.82%, +3.14%].
  Final copied versus old one-slot copied: **−11.32%** [−12.03%, −10.62%].
- XZ application stream: VKSO/stock **−12.87%** [−14.70%, −11.00%].
  Native fresh XZ stream word-copy versus prior prepared: **−27.02%** [−28.21%, −25.82%].
- Tradeoffs remain: LZ4 stream copied versus old one-slot copied **+1.88%**
  [+0.37%, +3.41%], and up to 6 MiB requested private data buffers.
  LZ4 shared/copied wall-time CI remains wide: **[−11.73%, +10.50%]**.
- At 16×, final copied PSS **25,968 KiB** versus old unbounded **91,014 KiB**
  (−71.47%). Shared is **25,990 KiB**, above stock-single **13,237 KiB**.
  Snapshots are not peak or net machine memory. Libfuse live-node accounting
  explains substantial remaining growth.
- Same nine physical pages / **36 KiB**; filesystem source reuse and native
  changes are itemized. Business disk allocation remains 288/324 KiB for
  shared/copied with prepared native, and 228/184 KiB for user-only deployment.
  Installed generic platform 32 KiB is separate; business preparation and
  registration remain charged. No developer-hour or net-machine saving claim.

The final bridge passed five-format/BCJ, isolated malformed-input regression,
private-adapter sanitizers, real FUSE lifetimes, simultaneous native/SIF private
objects, breakpoint/PFNs, native regression and minimal-deployment checks.
The final audit confirms **no active task runner/helper/queue and no task module**.

Four byte/runner-matched native campaigns (2,688 observations) are explicitly
reused; all 5,484 user/new-native observations are new. An interrupted native
campaign's **790 rows are retained and excluded in full**, and its whole
replacement uses the original seed/conditions. The prior reduced 14/30,
4,580-observation closeout and its 127 partial rows remain separate.
Old `running` fields are historical; recovery and completion audits prevail.

**Delivery scope:** raw data and experiment report only. Existing manuscript,
PDF and figures are unchanged; the publication below is the preserved
predecessor and does not represent these optimized results. No publication or
follow-up optimization job is queued.

Branch: `experiment/section65-filesystem-reuse`. Frozen-input checkpoint:
`ebe40754b34fbe0b5bbf316e628c4d13a61bd151`. The user will push the final local
commit; no agent push attempt is pending.

---

# Preserved common-XZ publication status

The implementation, finite confirmation matrix, independent statistical replay,
resource-scale experiments and canonical Section 6.5 are complete. The final
owner includes common filesystem, LZ4 and XZ code. The standalone PDF contains
four main-text pages and nine pages of diagnostics and complete comparison
results. This is a Section 6.5 build, not a whole-paper build.

## Main findings

- **More actual reuse:** 2,604 unchanged XZ algorithm lines join the existing
  34 filesystem functions / 2,103 original lines and LZ4 decoder. Owner text
  grows from 16,695 to 27,828 bytes; native and user execution is verified.
  Nine kernel/user pages (36 KiB) share backing with private bindings/state.
- **Final native cost:** versus equally optimized normal native, fresh scan
  point changes span −1.34% to +1.29% and archive changes −1.05% to −0.18%.
  The largest upper interval endpoint is +4.82%; no zero-cost or native
  hardening-equivalence claim is made.
- **Sharing increment:** nine ordinary nonempty VKSO/copied ratios span
  0.9901–1.0056, with interval endpoints 0.9584–1.0255. Equal-path diagnostic
  intervals are wider; a universal tight overhead bound is unproved.
- **Application effects depend on the baseline and task:** default SquashFUSE
  scans improve 4.42–54.58% and include archives 3.30–19.46%. Against its
  single-thread mode, gzip/lz4 metadata advantages mostly disappear, while
  xz scan remains 53.59% faster. gzip/lz4 sequential tasks improve about 7%;
  xz sequential time increases 13.10%.
- **The independent task limits generality:** Python byte compilation produces
  647 identical files, but VKSO takes 0.68%/16.18% longer than default stock
  for gzip/xz. All twelve ordinary tasks beat matched-cache LKL; held-out xz
  compilation instead takes 6.72% longer than that LKL configuration.
- **Memory has a scale reversal:** small-tree helper PSS is 7.00–7.04 MiB,
  below both stock modes and LKL. At 93,856 entries, private metadata retention
  reaches 88.89 MiB, above default/single-thread stock's 28.52/12.91 MiB.
  This is not a generally bounded or uniformly smaller user runtime.

## Completed matrix

| Evidence group | Campaigns / observations | Scope |
| --- | --- | --- |
| Final native | 3 / 2,400 | Five formats, scan/archive, fresh/warm, five native configurations |
| Native sequential | 3 / 480 | xz/lz4, two 128 MiB files, fresh/warm, same five configurations |
| Ordinary real applications | 9 / 3,024 | gzip/xz/lz4 SIFs, four tasks, seven backends/controls |
| Independent Python task | 6 / 288 | gzip/xz SIFs, six backends, validated bytecode output |
| Decoder/dependency diagnostics | 6 / 240 | xz/lz4 scan/stream, five controls, equal loader paths |
| Selected single-CPU check | 3 / 108 | gzip stream, stock/copied/VKSO |
| Resource scale | 3 separate untimed runs | 5,866/23,464/93,856 entries, five backends |
| Functional/physical/debugging | Complete | Five formats, BCJ, guest repair regression, actual decoder calls, simultaneous native/SIF consumers, hardware breakpoint, PFNs, restore/unload |

The 30 complete campaigns contain 6,540 observations and 403 paired
comparisons. All completed-campaign samples are retained. A server restart
interrupted one campaign after 28 observations; its partial records remain
unchanged, and a complete same-parameter campaign replaces it. The original
queue's stale `running` status does not indicate a live process. See the
[interruption and cleanup record](../evaluation-local/runs/iso9660/squash-refine-interruption-recovery-01/).

## Current artifacts

- [Paper PDF](../../paper/filesystem-section-preview.pdf) and [canonical source](../../paper/paper_content/sections/06-evaluation.tex).
- [Claim-to-experiment map](claim-experiment-map.md), [claim judgments](claim-verdicts.json), and [related-work comparison](related-work-comparison.md).
- [Finite protocol](squashfs/refinement/PROTOCOL.md), [reproduction guide](squashfs/refinement/README.md), [backend conditions](backend-conditions.md), and [decisions including adverse results](squashfs/refinement/RESULTS.md).
- [Analysis and independent audit](build/squashfs/refined-analysis-01/), [resource/deployment ledger](build/squashfs/refined-analysis-01/resource-ledger/resources.json), and [code-cost ledger](build/squashfs/refined-analysis-01/costs.json).
- [Kernel-change and composition patches](build/squashfs/refinement-reuse-audit-03/), [hardening audit](../evaluation-local/runs/iso9660/squash-refine-hardening-02/), and [LKL heap pilot](build/squashfs/refinement-baseline-audit-02/heap-pilot.md).
- [Figures and input provenance](../../paper/build/section65-refined-figures-01/), [render QA](../../paper/data/section65/render-qa.json), [final source/binary freeze](build/squashfs/evaluation-refined-02/identity.json), and [completion verification](final-evidence.json).
- [Final run selection](squashfs/refinement/formal-queue.json), [first 25 completed campaigns](../evaluation-local/runs/iso9660/squash-refine-formal-queue-01/), [remaining completed queue](../evaluation-local/runs/iso9660/squash-refine-formal-recovery-01/), and [resource queue](../evaluation-local/runs/iso9660/squash-refine-resource-queue-02/).

## Accounting and interpretation

The generic 32 KiB `page_cache_replace` module is installed platform
infrastructure, excluded from the filesystem subtotal as requested. The
filesystem owner/consumer still occupy 68+40 KiB, 48 KiB above the matched
60 KiB native module. An already prepared native service avoids one 36 KiB
copied backing and requests 1,264 bytes of registration metadata. Construction,
export and registration take a median 2.698 s (range 2.696–6.088 s), reused while
that owner/registration remains installed. These separate component and process
ledgers do not establish whole-machine net savings.

Common repair and algorithm/adapter benefits also apply to copied execution.
VKSO's additional verified property is native/user physical identity. The
current core omits native canaries and external thunks; build-only PIC feasibility
does not implement cross-domain hardening. Human-time savings, hot update,
filesystem throughput scaling, cross-host/boot generality and universal
preference over copied remain explicitly unsupported. No claim is removed
merely because its stronger form lacks evidence.

## Preserved predecessors

The composed-LZ4 version's 39 campaigns / 11,328 observations, PDF, sources,
figures and judgments are preserved in the
[composed publication snapshot](../../paper/build/section65-composed-publication-01/identity.json)
and `build/squashfs/improvement-analysis-01`. Its adverse xz/layout results
remain valid for that implementation; they are not relabeled as new-owner data.
The earlier 34-campaign / 13,968-observation version remains in
`build/squashfs/final-analysis-02` and the
[baseline publication snapshot](../../paper/build/section65-baseline-publication-01/identity.json).
