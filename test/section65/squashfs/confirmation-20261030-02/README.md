# Confirmation after the budget closeout

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

After all correctness gates and resource diagnostics complete, run:

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

Use `analyze.py` with `formal-queue.json`, then `audit.py` with that queue,
`registration.json` and the resulting analysis. The independent audit checks
raw pairing, campaign intervals, expected counts, fixed identities, nine PFNs,
mapped bytes, restoration/unload and the explicitly reused native samples.
Three same-boot campaign means determine each interval; per-block samples are
not independent campaign replications. All adverse outcomes remain included.

`metadata_work.py` accepts explicit final binaries for untimed decoder counts.
`resource-queue.json` replays the original 1/4/16 metadata scales and includes
old bounded/unbounded copied controls. Resources include the private data
budget; its performance benefit is not a physical-sharing benefit. The
installed 32 KiB generic platform is separate from filesystem business costs.

`write_section.py` and its template consume audited results; no placeholder
numbers are installed into the paper. `paper/plot_filesystem_optimized.py`
renders all registered comparisons and main figures from those same data.
The prior publication was archived before changes. Historical failures and
the reduced 14-campaign closeout remain separate evidence, never relabeled as
the new complete confirmation.
