# Final-owner reuse refinement

This directory extends the completed composed-LZ4 evaluation. The working
owner is `../../build/squashfs/refine-xz-01`; the prior owner and all its
measurements remain unchanged. See [PROTOCOL.md](PROTOCOL.md) for the bounded
matrix and the pilot-based sampling decision. New performance results must
not inherit the preceding implementation's numbers.

## Implementation and verified evidence

- `build_xz.py` composes matching Linux XZ stream/LZMA2/BCJ bodies without
  modifying their three algorithm source files (2,604 physical lines).
  Nine environment-service pointers remain private to each domain. Native
  uses PREALLOC mode; the contiguous user block interface uses SINGLE mode.
- Five-format functional and isolated malformed-input regression passed.
  Shared execution has seven code and two readonly pages (36 KiB); copied
  pages have distinct backing. Both variants bind private XZ services.
- `squash-refine-xz-native-calls-01` records 190 native XZ entry calls during
  the xz scan and zero for gzip/lz4. The common LZ4 entry records 73 lz4 calls.
- `squash-refine-xz-execution-01` runs native A and actual SIF consumers B/C
  on conflicting xz images. A hardware breakpoint records the shared XZ
  entry, arguments and available stack; subsequent PFNs, native regression,
  restoration and unload pass. This is functional/debug evidence, not timing.
- `squash-refine-xz-bcj-02` verifies that the generated image actually contains
  an x86 BCJ + LZMA2 filter chain and passes both-domain reads and metadata.
- `hardening.py` records Kbuild commands and actual object instructions. The
  current shared core omits native canary checks and external thunks. A
  build-only PIC probe retains them when the native GS canary convention is
  explicitly selected; runnable cross-domain hardening remains unimplemented.
- `reuse_audit.py` separates unchanged algorithms, extraction, generated
  support and user integration, and retains both composition and native
  consumer patches. Native preparation now has a 68 KiB owner and 40 KiB
  consumer versus the 60 KiB normal reference. Generic platform residency
  remains outside the filesystem subtotal under the user's installed-platform
  premise. These are component costs, not a whole-machine net-memory result.

## Execution and analysis

`pilot-queue.json` completed six correctness/timing preflights. The independent
Python task produces 647 identical bytecode files across all six backends.
`decoder-pilot-queue.json` checks the two explicit decoder/dependency controls.
`formal-queue.json` fixes 30 campaigns and 6,540 timed observations across
native, real applications, held-out compilation, bounded decoder diagnostics
and the selected single-CPU sensitivity check. Execute queues serially with
`../campaign_queue.py` under root; every job creates a private mount namespace.
No builds or QEMU run alongside formal native timing.

`analyze.py` consumes the explicit job kinds and preserves campaign/block
pairing. Primary intervals use three campaign means. `baseline_audit.py`
exposes the earlier 16/64/256/512 MiB LKL pilot and records the exact stock
`squashfuse_ll` executable and its `-s` option. All tested heaps completed the
pilot tasks; 512 MiB is not a minimum memory requirement.

`scale_images.py` builds 5,866/23,464/93,856-entry trees for separate untimed
resource observations. `metadata_work.py` and `decoder_counts.c` measure
decoder work during the xz metadata scan; instrumented times are excluded
from the performance analysis.

## Preserved preflight failures

- `squash-refine-hardening-01`: the diagnostic compile succeeded, but the
  checker expected GS while GCC's small code model selected FS. The next
  build explicitly selects the native GS convention; both objects remain.
- `squash-refine-xz-bcj-01`: the image had the requested BCJ chain, but the
  checker assumed absent optional XZ block-size fields. The corrected parser
  reads variable-length sizes before filter IDs. No module was loaded in the
  failed attempt; `-02` runs the complete regression.
- A tool-server restart terminated the first formal queue after 25 complete
  campaigns and 28 observations of `squash-refine-heldout-gzip-03`. Its partial
  records and stale running status remain untouched. The interruption sidecar
  records absent processes, successful registration restore/module unload,
  and a complete same-parameter rerun named `-03-recovery-01`. The analysis
  uses complete campaigns only; it does not splice partial blocks or filter
  samples by their timing. `formal-queue-before-recovery.json` preserves the
  initial schedule; `formal-queue.json` selects the 30 complete campaigns.
  The detached remaining queue and its resource/postprocess dependents are
  recorded in `squash-refine-interruption-recovery-01/recovery.json`.

The canonical Section 6.5 and 13-page standalone PDF now use the final owner.
All 30 completed campaigns (6,540 observations), 403 independently replayed
comparisons and three resource-scale runs are complete. See [RESULTS.md](RESULTS.md)
for benefits, adverse outcomes and the implementation decisions. The preceding
publication is preserved under `paper/build/section65-composed-publication-01`.

## Repeating confirmation without overwriting runs

Use the matching owned Linux 5.15.198 evaluation kernel and the recorded
compiler/configuration, prepared support modules, SIF assets and backend
binaries. The runner records their identities and checks native output against
the original driver. Do not change host boot configuration as part of this
recipe. Malformed fixtures remain confined to the guest.

From the repository root, create a fresh namespace with `clone_queue.py
--queue formal-queue.json --tag repeat-a --output /tmp/vkso-repeat-a.json`
(use repository-relative paths to both scripts and input queues). Run
`sudo python3 test/section65/squashfs/campaign_queue.py --queue
/tmp/vkso-repeat-a.json --output
test/evaluation-local/runs/iso9660/refinement-repeat-a-queue`.
Seeds, inputs and finite cell counts are preserved. No compiler, QEMU,
profiler or other test workload should run alongside confirmation.

Clone `resource-queue.json` separately and run it after confirmation. Analyze
the cloned formal queue with `analyze.py` and independently replay it with
`audit.py`; pass the cloned resource queue to `resources.py --resource-queue`.
Existing one-time deployment evidence can be retained for unchanged binaries,
or replaced using `--minimal` after a new `minimal_deployment.py` run.
Plotting uses `paper/build/section65-plot-env-02/venv/bin/python`; retain its
virtual-environment prefix rather than resolving the interpreter symlink.

To rebuild, invoke `build_xz.py --base` with the preserved composed-LZ4 build
and a new output directory, then `decoder_controls.py` with that candidate.
Run guest and host functional protocols before timing. A new build identity
needs a newly named measurement queue; do not relabel old samples.

For a completed rerun, the analysis sequence is:

```sh
paper/build/section65-plot-env-02/venv/bin/python \
  test/section65/squashfs/refinement/analyze.py \
  --queue /tmp/vkso-repeat-a.json --output /tmp/vkso-repeat-a-analysis
python3 test/section65/squashfs/refinement/audit.py \
  --queue /tmp/vkso-repeat-a.json \
  --analysis /tmp/vkso-repeat-a-analysis/analysis.json \
  --output /tmp/vkso-repeat-a-analysis/audit.json
python3 test/section65/squashfs/refinement/resources.py \
  --queue /tmp/vkso-repeat-a.json \
  --resource-queue /tmp/vkso-repeat-a-resources.json \
  --output /tmp/vkso-repeat-a-analysis/resources
paper/build/section65-plot-env-02/venv/bin/python \
  paper/plot_filesystem_refined.py \
  --analysis /tmp/vkso-repeat-a-analysis/analysis.json \
  --resources /tmp/vkso-repeat-a-analysis/resources/resources.json \
  --output /tmp/vkso-repeat-a-figures
python3 test/section65/squashfs/refinement/write_section.py \
  --analysis /tmp/vkso-repeat-a-analysis/analysis.json \
  --audit /tmp/vkso-repeat-a-analysis/audit.json \
  --resources /tmp/vkso-repeat-a-analysis/resources/resources.json \
  --output /tmp/vkso-repeat-a-analysis/section65.tex
```

The resource queue above is a separately cloned and executed queue. The plot
script also reads the preserved hardening, decoder-work and heap-pilot audits;
these are untimed evidence, not extra formal samples. Review the new estimates
before changing the canonical manuscript. The publication exporter reads that
canonical section and the selected figure/ledger directory; it does not select
a favorable campaign or change the underlying analysis.
