# Filesystem improvement experiments

The current completion state is in [../../STATUS.md](../../STATUS.md).
The prospective questions, controls and stopping rules are in
[../../improvement-protocol.md](../../improvement-protocol.md). Retained
diagnostics, failed candidates and interpretation changes are in
[decisions.md](decisions.md).

## What each comparison answers

| Matrix | Controls | Campaigns / observations | Scope |
| --- | --- | --- | --- |
| Main native | Original; previous prepared; bounded-copy prepared; composed prepared | 3 / 2,880 | Five codecs, include scan/archive, fresh and warm filesystem phases |
| Real application | Stock; old-adapter copied; complete copied/VKSO; LKL512 default/matched cache; gzip/lz4 adapter/decoder ablations; gzip stock translator | 9 / 3,600 | Three real SIF codecs, startup/scan/include archive/256 MiB archive |
| Optimized native references | Original; normal native; optimized normal/relaxed native; bounded-copy prepared | 3 / 720 | gzip/xz/lz4 fresh/warm scan; tests whether the same small-copy optimization benefits unadapted native code |
| Final native sequential | The four main native variants | 3 / 576 | gzip/xz/lz4 fresh/warm 256 MiB archive; required because composition changes the native LZ4 implementation |
| Additional xz attribution | Stock; old/directory/direct/both-library/full copied; VKSO | 3 / 672 | Same four tasks and xz SIF; explains the observed stream regression, separately from the main estimates |
| Equal-loader-path controls | Stock; old/both-library/full copied; VKSO | 9 / 1,440 | All four tasks and three SIF codecs; unchanged binary hardlinks, equal path lengths, two balanced padding levels |
| Single-CPU placement diagnostic | Same five backends and loader controls | 9 / 1,440 | Same tasks and inputs; application/helper CPU 1 affinity, separate from default two-CPU execution |

The main matrix has 18 campaigns and 7,776 observations; the targeted xz
extension adds three campaigns and 672 observations. The loader-control
matrix adds nine campaigns and 1,440 observations. The final placement
diagnostic adds nine campaigns and 1,440 observations. All 39 campaigns /
11,328 observations are complete and independently audited. The 34 campaigns
of the preceding implementation remain separate. Pilots and count/profile
experiments are not added to the formal sample count. Every formal cell has
three campaign estimates; repeated blocks are not independent campaigns.

The five-format native matrix uses the same logical tree and 128 KiB blocks.
Application SIFs use gzip/xz/lz4 and add equally sized compressible and seeded
pseudorandom payloads. gzip/lz4 ablations cover metadata-heavy and fast-codec
cases; xz retains all complete application tasks, including the previously
adverse stream task. No zstd/lzo application-performance extrapolation is made.
Random/boundary reads are correctness tests, not random-I/O performance tests.
The simultaneous A/B/C case tests private-state and lifecycle independence,
not a throughput or process-count scaling curve.

## Production implementation and diagnostics

The measured production binaries are frozen in
`../../build/squashfs/evaluation-improved-01/build`. `codec-user-source/`
contains their exact user C sources. `build_native_copy.py --small-copy`
creates the bounded-copy candidate; `build_codec.py` composes the existing
adapted safe LZ4 decoder. The native and user consumers use the same owner.
`build_user.py` enables directory-list retention and direct decoder output
equally for copied and VKSO; its default-off profiling instrumentation is
absent from production builds. `composed-controls.json` identifies the
same-owner user ablations.

`service_counter.c`, `count_native.py`, `profile_native.py` and `profile_user.py`
attribute actual work. Probe modules are removed before physical-sharing
tests. `directory_memory.py` builds separate diagnostics for requested live
directory-list storage, excluding allocator overhead. It does not modify
the measured frontend. The direct-output implementation retains its temporary
output allocation; it does not imply zero-copy I/O.

`simultaneous.py` runs native image A and actual Apptainer images B/C with
conflicting contents and metadata at identical paths. It records task
lifecycle intervals, shared PFNs and private object/binding PFNs, then ends
C, A and B in sequence. Apptainer's explicit uid/gid override is part of the
application oracle. `minimal_deployment.py` executes the real application
without the native consumer or construction observer, restores/unloads all
task modules, then executes the materialized copied DSO again.

The known malformed image is restricted to `guest_regression.py` and the
isolated maintenance guests. Do not mount it on the host. The retained repair
and final composed guest runs preserve old failure classification and fixed
native/copied/shared outcomes.

## Replay without overwriting evidence

Use the owned matching Linux 5.15.198 research host and the retained kernel,
Apptainer, stock SquashFUSE, LKL, compiler and image assets. Their identities
are in the implementation freeze and each run's `environment.json`.
`build_native_controls.py` also needs the original normal and relaxed
maintenance-reference build directories. The existing build recipes create
these assets; changing their versions creates a different experiment.
Keep compilation, QEMU and other task-owned benchmarks stopped during native
timings. Do not change host boot settings to reproduce this matrix.

Generate fresh manifests from the repository root:

```sh
python3 test/section65/squashfs/improvement/make_replay.py \
  --tag repeat-01 --output /tmp/vkso-section65-repeat-01
```

The generated `replay.json` contains the exact command for the serial queue.
This preparation command does not execute experiments. The queue requires
root for the owned kernel/mount experiments; it stops at the first failure
and preserves that run. It starts with the isolated repaired-input regression
and native-runner pilot, then runs all campaigns and dependent diagnostics,
analysis, independent statistical validation and resource accounting. The
targeted xz pilot, three campaigns and their separate analysis follow last.
The loader-path pilot, nine campaigns and their separate analysis follow the
xz attribution. The shared carrier aliases are created before registration,
which makes that inode immutable. Both pathname paddings remain in every
campaign, with separate stratum estimates in the analysis.
The single-CPU pilot, campaigns and analysis then follow serially. The common
outer `runuser` launcher precedes `taskset`; actual application/helper affinity
is observed separately. This diagnostic does not replace the two-CPU defaults.
Analysis uses the retained `paper/build/section65-plot-env-02/venv` environment,
which supplies NumPy independently of root's Python user packages.
Use a new tag after a failed attempt; never overwrite its output directory.
The queued application campaigns load and unload modules themselves and
must not overlap another module experiment.

## Analysis and publication artifacts

`analyze.py` checks complete pairs and binary identities, retains absolute
times, campaign ratios, paired differences and CPU times, and computes the
primary pointwise Student-t intervals over three campaign means. Its secondary
hierarchical bootstrap is a sensitivity analysis. `validate_analysis.py`
reconstructs all primary estimates independently with the standard library,
checks exact finite-matrix counts, block order and copied/shared instructions.

`resource_ledger.py` separates RSS/PSS/USS and liblz4 mappings, requested
private allocations, unique shared PFNs, module residency, registration
metadata, setup stages and copied execution after unload. The ledger never
sums process PSS and module bytes into a whole-machine saving.
`maintenance_ledger.py` records actual source and allocated-section changes;
both copied and shared reuse one compiled owner. `../cost_ledger.py` separately
accounts source reuse, generators, generated support, first integration and
application-specific glue without converting source lines into human hours.

`paper/plot_filesystem_improved.py` renders the complete analyzed matrix and
resource table. `paper/build_filesystem_section.py` exports the canonical
Section 6.5 and refuses unfinished result placeholders. The final evidence
checker additionally verifies the rendered PDF, source freeze, claim verdicts,
functional/maintenance runs and actual SIF descriptor/offset traces. See the
status entry for the current artifacts; generated manifests or successful
builds alone do not constitute executed evidence.

The publication pipeline, after the named analyses complete, is:

```sh
paper/build/section65-plot-env-02/venv/bin/python paper/plot_filesystem_improved.py \
  --analysis test/section65/build/squashfs/improvement-analysis-01/analysis.json \
  --resources test/section65/build/squashfs/improvement-analysis-01/resources.json \
  --xz-attribution test/section65/build/squashfs/improvement-xz-attribution-analysis-01/analysis.json \
  --loader-control test/section65/build/squashfs/improvement-loader-analysis-01/analysis.json \
  --single-cpu test/section65/build/squashfs/improvement-singlecpu-analysis-01/analysis.json \
  --output paper/build/section65-improved-figures-new
python3 test/section65/squashfs/improvement/business_costs.py \
  --resources test/section65/build/squashfs/improvement-analysis-01/resources.json \
  --output test/section65/build/squashfs/improvement-analysis-01/business-costs.json \
  --table paper/tables/filesystem-business.tex
python3 paper/build_filesystem_section.py --figures paper/build/section65-improved-figures-new \
  --business-costs test/section65/build/squashfs/improvement-analysis-01/business-costs.json
make -C paper filesystem-section TECTONIC=build/tools/tectonic
```

Use a fresh output directory. The builder exports the canonical subsection
and copies traceable figures/data/tables; it rejects unresolved result slots.
The PDF includes complete comparison tables and both padding strata. Its
render QA is tied to the actual PDF digest, so inspect a regenerated PDF
before treating the previous visual-review record as applicable.
`audit_manuscript_numbers.py` checks selected hand-written timing/resource
numbers against the analyzed results. `freeze.py` captures the exact production
build, scripts, protocols, manuscript and supporting paper sources.

The optional same-inode path diagnostic is reproducible with
`path_layout.py --blocks 8 --output <fresh-directory>` on the owned host. It
uses the retained materialized core from the minimal-deployment run, requires
root for post-timing debugger reads, and loads no task module. Its mounted-task
timings are kept separate from every complete-application campaign.

## Business-specific accounting

The current paper assumes VKSO platform support is installed. `business_costs.py`
derives a separate ledger from the unchanged resource observations: generic
page_cache_replace residency (32 KiB) is not charged to this business. Native
preparation, requested registration metadata, required user runtime and
private buffers remain included. Core construction/export/registration times
are summed within each of the nine campaigns before taking medians/ranges;
no medians of independent samples are subtracted. Full platform/deployment
records remain in `resources.json`. This presentation change needs no new
performance run because all binaries, inputs, commands and raw samples remain
unchanged.
