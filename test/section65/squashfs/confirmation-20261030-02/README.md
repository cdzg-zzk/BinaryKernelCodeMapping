# Confirmation after the budget closeout

Completed delivery: **30 campaigns / 8,172 observations / 541 paired comparisons**.
[Experiment report](../../evidence/confirmation-20261030-02/final/analysis/EXPERIMENT_REPORT.md),
[archived evidence](../../evidence/confirmation-20261030-02/final/manifest.json),
[completion audit](../../evidence/confirmation-20261030-02/final/analysis/completion-audit.json),
and [offline verification](bundle-verification.json) are the current entry points.
All experiment/continuation processes have exited and task modules are unloaded.
Manuscript and figures are deferred at the user’s request; the old PDF is not
this version. The user will push the local Git commit.

The original queue was interrupted after 16 new user campaigns. Recovery
retains all 790 partial native samples and excludes the entire partial group;
`recovered-formal-queue.json` and `recovered-registration.json` replace only
its name/output, preserving seed and conditions. The recovery queue completed the
whole replacement plus the nine remaining campaigns. Original queue states
and registrations remain available; old `running` fields are historical.


`PROTOCOL.md` defines the evidence gaps; `CACHE_PROTOCOL.md` records the finite
cache candidates and `SELECTION.md` records the resulting time/memory tradeoff.
`progress.json` is the current status. The old `budget-closeout-01/stopped.json`
continues to describe the old cancelled queue, not these separately named runs.

The selected candidate uses the existing scalar-word-copy XZ owner, bounded
2048/4096 private inode/name caches, and 48 lazy data slots. The native owner
and consumer are unchanged. The frontend/helper were rebuilt from identical
sources: allocated runtime sections and addresses match apart from the build
ID; debug metadata and whole-file hashes differ. Copied and shared use exactly
the same final frontend and bridge. The tree-unrolling and large-file
single-buffer candidates are retained as diagnostics and are not selected.

The source builder is `build_data_cache.py`; its output directory is
`/var/tmp/vkso-section65-optimization-20261030-hBcg9Y/builds/data-cache-controls-02`.
The `data-48` child is the selected candidate. `build_stream_admission.py`
reproduces the rejected admission control. `stream_profile.py`,
`python_work.py`, and `fuse_memory_diagnostic.py` retain the causal diagnostics.
`summarize_pilots.py` reports every completed pilot cell without confidence
claims. No measured workload or codec was removed after looking at its result.

Original frozen launch (retained as provenance; already executed, do not replay
into these existing output directories):

```sh
python3 test/section65/squashfs/confirmation-20261030-02/prepare_confirmation.py
sudo python3 test/section65/squashfs/campaign_queue.py \
  --queue test/section65/squashfs/confirmation-20261030-02/pending-queue.json \
  --output /var/tmp/vkso-section65-optimization-20261030-hBcg9Y/data48-confirmation-queue-01
```

Preparation refuses changed predecessor inputs or incomplete correctness gates.
It writes the 30-campaign analysis queue, 26 pending campaigns, exact input
identities and expected cells. Four completed native campaigns contribute
2,688 observations with identical binaries/runners; 5,484 new observations
complete the 8,172-observation matrix. Ordinary/Python cells retain old copied
as a direct cache-policy control in addition to all previous baselines.
Run timing alone, without task-owned compilation, profiling or QEMU.
No cancelled predecessor queue is resumed.

Use `analyze.py` with `recovered-formal-queue.json`, then `audit.py` with that queue,
`recovered-registration.json` and the resulting analysis. The independent audit checks
raw pairing, campaign intervals, expected counts, fixed identities, nine PFNs,
mapped bytes, restoration/unload and the explicitly reused native samples.
Three same-boot campaign means determine each interval; per-block samples are
not independent campaign replications. All adverse outcomes remain included.

`metadata_work.py` accepts explicit final binaries for untimed decoder counts.
`resource-queue.json` replays the original 1/4/16 metadata scales and includes
old bounded/unbounded copied controls. Resources include the private data
budget; its performance benefit is not a physical-sharing benefit. The
installed 32 KiB generic platform is separate from filesystem business costs.

`postprocess.py` now runs analysis, independent audit, resource accounting and
`experiment_report.py` only. `completion_audit.py` verifies functional/source
identity evidence and cleanup without modifying the manuscript. Publication
writers and plotting scaffolds from the earlier checkpoint are not invoked.
Historical failures and the reduced 14-campaign closeout remain separate,
never relabeled as this complete confirmation.

## Current report-only workflow

[Claim coverage and completion conditions](CLAIM_COVERAGE.md) separates source
reuse, physical sharing, native preparation and whole-backend efficiency.
The frozen protocols retain their original chronology; this scope note
supersedes their old publication-delivery wording.

After the recovered queue completes, the data-only postprocessor runs:

```sh
P=test/section65/squashfs/confirmation-20261030-02
R=/var/tmp/vkso-section65-optimization-20261030-hBcg9Y
python3 "$P/analyze.py" --queue "$P/recovered-formal-queue.json" --output "$R/data48-analysis-01"
python3 "$P/audit.py" --queue "$P/recovered-formal-queue.json" \
  --registration "$P/recovered-registration.json" \
  --analysis "$R/data48-analysis-01/analysis.json" --output "$R/data48-analysis-01/audit.json"
```

`postprocess.py` contains the exact additional source/reuse/resource/report
commands. Do not rerun a completed queue or overwrite its output directory;
use fresh paths and a new registration for any new measurement. Analysis
commands above also expect a new analysis directory when rerun.

After reviewing the report and after all task runners have exited:

```sh
python3 "$P/completion_audit.py" --analysis "$R/data48-analysis-01" \
  --output "$R/data48-analysis-01/completion-audit.json"
python3 "$P/pack_evidence.py" --analysis "$R/data48-analysis-01" \
  --output test/section65/evidence/confirmation-20261030-02/final
python3 "$P/verify_bundle.py" test/section65/evidence/confirmation-20261030-02/final \
  --output "$P/bundle-verification.json"
```

The archive verifier runs without sudo, kernel modules, image assets or the
original server directories. It verifies every archived file and independently
recomputes all timing estimates and campaign-level intervals from the archived
raw rows. Archives include full per-campaign JSON/JSONL/text logs, execution
order, resource/PFN records, the 790-row interrupted group and generated/frozen
text sources. Kernel binaries, SIF/SquashFS images and large task-output tar
files remain at the original server paths with recorded identities; these are
required to rerun kernel/application experiments, not to replay the statistics.
