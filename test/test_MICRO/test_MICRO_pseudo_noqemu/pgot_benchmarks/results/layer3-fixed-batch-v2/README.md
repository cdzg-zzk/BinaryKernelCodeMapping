# Layer-3 PGOT revision: fixed batches and confirmatory evidence

This artifact evaluates dependency adaptation inside kernel modules for four
fixed Linux-routine workloads. The later LZ4/BCH/XZ export campaign is separate.
The paper has not been edited. Start with
[FINAL-ASSESSMENT.md](../layer3-confirmatory-v2/FINAL-ASSESSMENT.md),
[the new figure](../layer3-confirmatory-v2/figures/ablation.pdf), and
[MECHANISM-EVIDENCE.md](../layer3-confirmatory-v2/MECHANISM-EVIDENCE.md).

## Completed measurements

- Original archive: 72 routine/build/variant/batch configurations, three module
  loads per configuration, 31 paired rounds per load. All available scan data
  are reconstructed in `complete-scan.csv` and `complete-scan-outer.csv`.
- Timestamp calibration: six module loads, 1,001 samples each; three loads per
  build. The maximum load median is **39 TSC ticks**. This is a September 17
  retrospective calibration, not a measurement made with the July archive.
- Confirmation: **64 module loads, 2,400 paired records, 160 outer comparison
  estimates**. Each routine/build has eight independent module loads, each
  providing 15 rounds for each applicable comparison.
- Separate BCH diagnostics: two builds, four variants, four instrumented
  source sites, each observed once per fixed encode. No formal timing samples
  are collected from diagnostic modules.

## Selection rule and frozen configuration

The batch selection reads only Origin cost, batch size, build and outer-run
identity. For each candidate/build, it computes the Origin median batch
cost within each outer run and takes the minimum across those run medians.
The selected batch is the smallest candidate meeting **39,000 TSC ticks in
both builds**. It never reads PGOT costs, deltas, IQR, signs or significance.
Every variant and both builds use the same selected batch for a routine.

| Routine | Existing candidates | Frozen operations/batch |
|---|---|---:|
| SHA-256 transform | 4096, 8192, 16384 | 4096 |
| BCH encode | 64, 128, 256 | 64 |
| zlib deflate | 16, 32, 64 | 16 |
| Zstd decompress | 16, 32, 64, 128, 256 | 16 |

`fixed-batches.json` freezes the rule, sizes, repetition hierarchy, input raw
hashes and calibration hash. `batch-selection-evidence.csv` gives the duration
and threshold ratio for every candidate/build. The old
`select_layer3_stable_rows.py` entry point is retired; its source is preserved
under `prechange/`. It cannot silently produce new outcome-selected results.

## Workload and timing contract

| Routine | Fixed input and timed operation | Outside the timer |
|---|---|---|
| SHA-256 | 64-byte block, whole transform; state evolves within each batch | constants/input setup and state/digest verification |
| BCH | m=13, t=8, swap_bits=true; clear ECC and encode 512 bytes | bch allocation/initialization and variant-output comparisons |
| zlib | reset, input/output setup, level-3 Z_FINISH on 342 bytes | workspace allocation, stream initialization and output comparisons |
| Zstd | decompressBegin and complete decompression of a 155-byte frame | context/workspace allocation and output comparisons |

All comparisons execute in the kernel domain. SHA has only Data-PGOT; the
other routines have Data, Func and All. PGOT entries bind the selected data
addresses and memory helpers. Internal copied algorithm helpers remain as in
the existing experiment. SHA/BCH use deliberately organized benchmark C,
including compiler barriers/noinline constraints. zlib/Zstd are generated
from Linux source. These are controlled adaptation builds, not untouched
Linux distribution objects.

The host is an i7-1165G7 with SMT disabled, Linux 5.15.0-119-generic, GCC 11.4.0.
CPU 2 is pinned; preemption and local interrupts are disabled inside each
sample. The exact boot command line, CPU description and boot ID are in
`../layer3-confirmatory-v2/identity.json`.

Both builds preserve the original run.sh flags: no-retpoline uses
`-mindirect-branch=keep`; retpoline uses
`-mindirect-branch=thunk-inline -mindirect-branch-register`. Per-routine
`flags.txt` and verbose `build.log` retain every flag and Kbuild command,
including return-branch, tracing/alignment and memory-builtin controls.

A sample measures a batch using LFENCE/RDTSCP and divides by operations.
The raw field names say cycles, but the unit is **TSC ticks**. Each even round
uses Origin/Variant/Variant/Origin (ABBA), each odd round BAAB; the two batch
values for each side are averaged into one paired raw record. Logs are emitted
after sampling. Separate values for the four constituent batches were not
recorded by this benchmark. Both raw pair records and their module-load
boundaries are preserved. Builds run no-retpoline then retpoline on even
outer-run IDs, reversed on odd IDs; routine order is SHA/BCH/zlib/Zstd, and
comparison order is Data/Func/All. SHA warms up five measured batches; the
other routines warm up one fixed batch per body before comparisons.

## Estimator and uncertainty

Within a module load/comparison, take the median of its paired deltas and the
median Origin cost. Relative overhead is 100 times that paired-delta median
divided by the Origin median. Summarize these percentages with an equal-weight
median across module loads. Costs and deltas are also summarized at the
outer-run level. Medians are taken separately, so subtracting the two displayed
cost medians need not equal the displayed paired-delta median.

The confirmation CI is the 2.5th/97.5th percentile of 10,000 resampled medians
of the eight outer percentages, using seed 17092026. Historical reconstruction
shows the range across its three loads, without implying 93 independent
trials. No observations are removed. The figures show every outer-run point;
in particular the BCH no-retpoline Data/All increase in load 6 remains visible.

`origin-and-variants.csv` has explicit backend rows. Origin is retained per
paired comparison, rather than merging baselines measured at different times.
`ablation.csv` is the concise 20-comparison table used for bars; SHA has no
invented Func/All row. Plot CSVs are byte copies of their input tables.

## Reproduce all tables and figures with one command

Run from this benchmark directory:

```bash
cd test/test_MICRO/test_MICRO_pseudo_noqemu/pgot_benchmarks
python3 scripts/reproduce_layer3_v2.py
```

The command verifies the 323 historical hashes, reconstructs the full scan,
checks frozen selection, analyzes confirmation raw records, regenerates static
inventories from actual objects, renders both figures, and writes comparison
and interpretation reports. It requires Python 3.10+, NumPy, Matplotlib,
objdump and nm. `scripts/requirements-layer3-v2.txt` records the rendering
versions. If those Python packages are not installed, a local target works:

```bash
python3 -m pip install --target /tmp/pgot-analysis-deps -r scripts/requirements-layer3-v2.txt
PYTHONPATH=/tmp/pgot-analysis-deps python3 scripts/reproduce_layer3_v2.py
```

The figure is a 7.1-by-3.3-inch vector PDF plus 300-dpi PNG. It uses grayscale,
hatches, zero baselines and all outer points. The plot source and exact bar/dot
CSV inputs are also under each `figures/` directory. The SHA omissions mean
not applicable. No raster/image-generation service is involved.

## Reproduce timing on the configured research host

The collector requires the configured 5.15.0-119 kernel, matching headers,
GCC 11.4, the local Linux 5.15 source tree used by the two generators, CPU 2,
and root access for module loading. Kernel source include locations are
recorded by generated C and Kbuild commands. Do not run another benchmark
concurrently. The collector pins CPU 2 and preserves the configured boot state;
it does not silently reconfigure the machine. It prompts for sudo if needed;
passwords are not stored.

Use a **new**, nonexistent result directory. This runs only the frozen batches:

```bash
python3 scripts/run_layer3_v2.py collect \
  --config results/layer3-fixed-batch-v2/fixed-batches.json \
  --output results/layer3-confirmatory-reproduction
python3 scripts/diagnose_layer3_v2.py \
  --campaign results/layer3-confirmatory-reproduction \
  --output results/layer3-confirmatory-reproduction/diagnostics
python3 scripts/reproduce_layer3_v2.py \
  --campaign results/layer3-confirmatory-reproduction
```

`collect --build-only` followed by `run-built --output DIR` separates build and
measurement when needed. Build/source snapshots, module/object hashes and
kernel log markers record exactly what was run. An interrupted collector is
not silently resumed or pooled with another attempt; keep that evidence and
use a new output directory.

To independently repeat the selection calibration, also use new directories:

```bash
python3 scripts/run_layer3_v2.py calibrate --output results/layer3-calibration-reproduction
python3 scripts/layer3_v2.py reanalyze \
  --archive results/layer3 \
  --calibration results/layer3-calibration-reproduction/calibration.json \
  --output results/layer3-selection-reproduction
```

A newly measured calibration belongs to a new selection version. The existing
confirmation always uses its frozen calibration/configuration; it is not
retuned after inspecting PGOT results.

## Artifact map

| Evidence | Location |
|---|---|
| Original audit and source snapshots | `AUDIT.md`, `prechange/` |
| All historical file hashes | `historical-hashes.json` |
| Timestamp measurements, KOs and identity | `calibration/` |
| Old report vs same raw at old/fixed batch | `historical-vs-fixed.csv`, `.md` |
| Old complete scan and new fixed-batch analysis | `complete-scan*.csv`, `ablation.csv`, `outer-runs.csv` |
| Confirmation identity, source, hashes, builds | `../layer3-confirmatory-v2/identity.json`, `source/`, routine/build directories |
| Formal logs, session boundaries and raw | `../layer3-confirmatory-v2/sessions.json`, routine directories |
| Full three-way comparison and interpretation | `../layer3-confirmatory-v2/historical-fixed-confirmatory.csv`, `FINAL-ASSESSMENT.md` |
| Source statements, object offsets and codegen diffs | `../layer3-confirmatory-v2/static-evidence/` |
| BCH separate dynamic helper counts | `../layer3-confirmatory-v2/diagnostics/` |
| Both standalone figures and plot inputs | `figures/`, `../layer3-confirmatory-v2/figures/` |
| Current reproduction/analysis source snapshot | `analysis-source/` |
| Requirement-by-requirement completion check | `COMPLETION-AUDIT.md`, `verification.json` |

The historical selected table lacks matching raw provenance. Its outer-run
variability cannot be reconstructed honestly from the different raw archive.
That gap is explicitly labeled in the comparison CSV. The new measurements
supply their own complete provenance. BCH's load-specific slowdown and zlib's
small negative complete-adaptation result have not been assigned a speculative
microarchitectural cause; the reports distinguish what the ablations and
compiled paths demonstrate from what remains unresolved.
