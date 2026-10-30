# Reproducing the Section 6.5 filesystem evaluation

The final XZ-composed implementation and serial confirmation are documented in
[squashfs/refinement/README.md](squashfs/refinement/README.md). Production binaries
are in `build/squashfs/refine-xz-01`; final sources/publication are frozen in
`build/squashfs/evaluation-refined-02`. Use the typed final queue and its analysis
scripts for current results. [STATUS.md](STATUS.md) identifies all final artifacts.

The guide below retains the earlier fixed-core baseline and common asset/build
recipes. Its campaign counts, configuration-specific figures and old timing
commands describe that version; do not pool them with the final confirmation.

This is an execution guide. Completion status is in [research-protocol.md](research-protocol.md)
and the named raw run records. Existing output directories are immutable inputs;
use new directories for every rerun. Run commands from the repository root.

## Evaluated assets

- Host: Intel Core i7-1165G7, about 15.3 GiB RAM, Linux 5.15.198. Native tasks use
  CPU 1; all application client/helper descendants share CPUs 1 and 2. The saved
  governors are `powersave`; the existing boot has SMT and turbo disabled.
  This work does not change boot or frequency configuration.
- Linux source/config/compiler commands: `build/native/linux-5.15.198`,
  `build/native/kernel/.config`, and the `.cmd`/build records in the frozen build.
  GCC is 11.4.0. The host kernel's built-in SquashFS is the primary native oracle.
- Baseline owner and native consumer: `build/squashfs/evaluation-fixed-01/build`,
  copied from `squash-maintenance-02/fixed-build`. The fix is upstream commit
  `e300eb5002925b29be803d2661af07266cfa267e`. All baseline formal campaigns use these
  same module/frontend/bridge/translator binaries. Later source freezes add
  runner and analysis changes; they do not replace those evaluated binaries.
  The formal copied control is materialized from the registered final owner at
  runtime. The retained old `libsq-copy.so` in the build directory is not that
  control and is not used in final timing.
- Native images: `build/squashfs/native-images-01/images.json`; gzip, xz, zstd,
  lz4, lzo; identical root tree, 128 KiB blocks. Build commands and hashes are
  in the manifest. `superblock-audit.json` checks format/block/inode metadata.
- Application images: `build/squashfs/application-images-01/images.json`;
  three real gzip/xz/lz4 SIFs, 128 KiB blocks, partition offset 36,864. Each
  contains the same Linux include tree and two additional 128 MiB files.
  One file repeats text; the other uses seed 650031 pseudorandom bytes.
- Apptainer: `build/squashfs/apptainer/jammy`; version 1.5.5 with bundled
  SquashFUSE 0.6.2. Acquisition records are `release.json` and `ppa-package.json`
  in its parent. Compression libraries and executed paths are visible in the
  saved helper maps and per-run environment.
- LKL: commit `d0f76a77e8c2ca68bd7d96190b8da09040eab072`, Linux 6.12,
  `build/lkl/build-squash-only/sif-frontend/lklfuse`. See [lkl/README.md](lkl/README.md)
  for verified source reconstruction, focused configuration and build records.
  The primary application heap is 512 MiB; 64 MiB is a sensitivity control.
- Registration/export tools: `test/evaluation-local/packages/iso9660-native-optimized-20261029`
  and `make_dll/build_PIC_so.py`. Owner identity is checked against the running
  kernel. The observer module is used for PFNs, separately from registration.

Paths beginning `build/` above are relative to `test/section65/`. The runtime
packages and workload assets are already present in this research workspace.
Reproduction on another machine requires matching the kernel SDK and support
module ABI; substituting another host build is a new experimental condition.

## Build and functional gates

`squashfs/prepare.py --build` generates the original prepared owner/consumer
from the retained Linux source, while `squashfs/build_user.py` builds its
bridge/frontends. The exact commands are saved in each build record. To repeat
the known upstream-fix experiment, choose a new output:

```sh
python3 test/section65/squashfs/maintenance.py \
  --build test/section65/build/squashfs/reader-adapted \
  --output test/evaluation-local/runs/iso9660/squash-maintenance-new
python3 test/section65/squashfs/maintenance_reference.py \
  --maintenance test/evaluation-local/runs/iso9660/squash-maintenance-new \
  --output test/evaluation-local/runs/iso9660/squash-maintenance-reference-new
```

The maintenance wrapper creates disposable QEMU TCG guests. Its malformed image
belongs exclusively in those guests. The old guest is expected to terminate
with the target-function panic; the outer classifier checks valid controls,
client result and daemon signal as well. Fixed guests must complete native and
both user regressions, PFNs, restoration and module unloading. Add `--relaxed`
to a separately named reference run for the compiler-option diagnostic.

`native_images.py --output NEW` rebuilds ordinary five-format images from the
original Apptainer preflight rootfs. `application_images.py --output NEW`
constructs the enlarged real SIF set from the same source. The rootfs is
reproducible through `apptainer_preflight.py` (no `--image` argument), which
copies busybox, GNU tar, required runtime libraries and the retained Linux
headers before invoking Apptainer build. The resulting manifests identify
exact payload versions; changing host binaries changes the workload identity.

`build_debug_types.py --build BUILD --output NEW` makes a separate DWARF
companion for private-state inspection. It verifies every allocated section
against the original object. Production targets remain unchanged.

## Hardware campaign order

Finish compilation and all QEMU jobs before measurement. Runners require root
for module/mount/PFN setup and run actual Apptainer workloads as the selected
ordinary user. Use a private mount namespace. For example:

```sh
sudo unshare --mount --propagation private python3 \
  test/section65/squashfs/native_cost.py \
  --build test/section65/build/squashfs/evaluation-fixed-01/build \
  --image-set test/section65/build/squashfs/native-images-01/images.json \
  --blocks 12 --warm-repeats 3 --seed 65201 --campaign five-codec-new \
  --output test/evaluation-local/runs/iso9660/squash-native-new
```

The original native pilot has four blocks and two warm repeats, excluded from
formal inference. Primary native sampling ultimately fixes seven independent
campaigns of twelve blocks and three warm repeats. Each block pairs original
and prepared at each codec/task/repetition. A fresh mount and warm accesses
are different phases; compressed backing images are warmed in both.

The complete application invocation and seed schedule are recorded in
`squashfs/application-formal-queue.json`: three campaigns per real SIF, eight
randomized blocks, two fresh executions per cell, six backends and four tasks.
The queue is 3,456 lifecycle observations. The later native schedule is
`squashfs/native-final-queue.json`; together with primary campaigns 01–03 it
contains 9,072 observations. It includes all five-codec primary cells,
three-format sequential archives and normal/relaxed module diagnostics.

Queue files name historical output paths. For a rerun, copy the queue, replace
output paths and campaign names consistently, set the ordinary `--user`, and
retain or explicitly change seeds. `campaign_queue.py --queue QUEUE --output NEW`
executes serially, stops on failure and saves per-job logs and process IDs.
`--after PREVIOUS/result.json` waits only while that prior queue is actually
alive. Run application and native queues sequentially, without parallel builds.
Do not treat an old `status=running` JSON as proof of a live process.

The optional final `--verify-without-observer` path in `apptainer_shared.py`
unloads the PFN observer, starts another real application, checks native output,
restores registration and unloads the remaining modules. It also records
GNU-time resource observations for deployment commands. Those instrumented
durations are separate from the nine campaigns' ordinary stage durations.

## Analysis and provenance

```sh
python3 test/section65/squashfs/audit_existing.py --output NEW-audit.json
python3 test/section65/squashfs/final_analysis.py --with-cache --output NEW-analysis
python3 paper/plot_filesystem.py --analysis NEW-analysis --output NEW-figures
```

`final_analysis.py` selects the explicitly named final matrix, rejects missing
cells, checks actual randomized order/PFNs/output records and regenerates
native/application estimates and resource accounting. Change its explicit run
list when reproducing under new names. It never includes pilots, old Python
translator results, or pre-fix owner timings in the final estimates.

Sample CSV retains campaign, block, repetition and actual order. Repeated
samples become block medians; campaign estimates receive equal weight.
Paired effects use mean log ratios and campaign-level 95% Student-t intervals.
Absolute plots use mean campaign medians with campaign-level intervals.
Detailed paired tables also retain median-of-campaign-median absolute values;
the estimator is labeled. Intervals describe this host and boot, not a
multi-machine or cross-boot population. They are pointwise, not simultaneous.

Raw application samples are appended only after successful process exit and
oracle comparison. The runner source and logs are retained. Per-sample archive
manifests are temporary; full native manifests and application preflight
evidence are saved. GDB private-state figures are requested-allocation subsets,
alongside smaps RSS/PSS/USS, not replacements for total process or machine memory.
The resource ledger separates existing-core and additional-deployment cases.

Historical failures remain in place, including the interrupted maintenance run,
exporter failures, missing-DWARF pilot and slow-observer pilot. Selected evidence
roles and reuse limits are checked by `selected-evidence-audit.json`. No data
are removed because they fail to show a performance advantage.

## Matched-cache diagnostic

After the default matrix, build `lkl/cache_frontend.py --output NEW`, then run
small gzip/xz/lz4 pilots before `squashfs/cache-formal-queue.json`. Its nine
campaigns contain 1,440 observations: three formats, four tasks, five backends,
eight blocks and one fresh execution per cell. It retains stock, copied, VKSO,
LKL512 default and LKL512 with one-second positive FUSE caches. Its
`analysis_group=application-cache` prevents pooling with default campaigns.
The primary workload/core/frontend identities remain fixed; only the separately
named LKL frontend changes cache policy. `final_analysis.py --with-cache`
requires the completed default and diagnostic matrices.

The first native pilot and first primary native campaign preceded per-run
runner-copy instrumentation. Their contemporaneous source is retained in
`evaluation-fixed-01`; later runner versions preserve the default workload
commands while adding optional diagnostics and provenance. Subsequent native
and all formal application runs have per-run runner copies and hashes. The
audit states this provenance distinction rather than retroactively filling
missing records. `reference-build-audit-01` additionally checks actual normal
and relaxed control instructions and retains their compile commands.

## Final artifacts and supplemental semantics

The delivered final analysis is `build/squashfs/final-analysis-02`; its
`matrix.csv` lists all 34 campaigns. Each of `native`, `application`, and
`cache` contains raw observation CSV, campaign-estimate CSV, paired summaries,
absolute/CPU estimates and analysis JSON. The three independent statistics
validation records pass. Final implementation binaries are the unchanged
`evaluation-fixed-01/build` inputs; `evaluation-fixed-06` captures final
runners, configuration, build products, documentation and manuscript source.

Supplemental valid-image semantics (not timed) are reproducible with:

```sh
sudo unshare --mount --propagation private python3 test/section65/squashfs/functional_extra.py --output NEW-functional-extra
```

The completed `squash-functional-extra-01` contains all 25 five-format mounts,
security/empty/large-xattr results, linked/boundary reads, copied/shared page-byte
and PFN records, private binding checks, restoration and module unloading.
It uses the same fixed owner and unchanged user bridge/frontend as formal runs.

The plotting environment is isolated under
`paper/build/section65-plot-env-02/venv`; exact dependencies are pinned in
`paper/evaluation-requirements.txt`. Regenerate into new directories:

```sh
paper/build/section65-plot-env-02/venv/bin/python paper/plot_filesystem.py --analysis test/section65/build/squashfs/final-analysis-02 --output NEW-figures
python3 paper/build_filesystem_section.py --figures NEW-figures
make -C paper filesystem-section TECTONIC=build/tools/tectonic
```

The delivered figures are `paper/build/section65-figures-final-02` and
`paper/figures/section65`; raw-data copies and provenance are under
`paper/data/section65`. Seven figures retain defaults, matched caches, sharing,
fresh/warm native and sequential controls. The standalone PDF has the complete
section and all paired cells; it does not imply that the whole manuscript or
its older Evaluation PDF has been rebuilt. `render-qa.json` records the actual
PDF review and any compiler warnings.

`final_evidence.py` checks campaign counts, raw-data statistics validation,
extra functional results, fixed binaries, PFNs/page bytes, snapshot hashes,
figure inputs, canonical/exported prose identity, PDF and claim-review gates.
It is a delivery check, not a substitute for the measured effects or their
scope. Historical failed runs, old assessments, intermediate figures and
cancelled environment setup remain separate records.
