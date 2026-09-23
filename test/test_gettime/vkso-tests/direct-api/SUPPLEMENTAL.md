# opt4 supplementary checks and kernel READ analysis

## What was completed

Local direct tests: 41 total, 38 PASS, 3 environmental SKIP (native vDSO absent).
Threaded forced-error tests now cover all four integer public APIs, with distinct
thread errno values. Negative time values, successful errno preservation, sticky
initialization failure and single initialization remain covered. These use a mock
carrier and are not target-kernel execution evidence.

`tests/test_public_target.c` reuses functional/abi_matrix.c's namespace lifecycle
oracle without modifying it. Its selected backend calls the PUBLIC clock_gettime,
not __vkso_clock_gettime. Checks cover exec initialization, setns after initialization,
namespace offsets, frozen offsets and syscall-denied fast clocks. At each namespace
sample it additionally checks public clock_getres against syscall, time/gettimeofday
against syscall brackets, getcpu outputs, and successful clock errno preservation.
Fast syscall-denial coverage specifically concerns clock_gettime, not all those APIs.

The same executable separately measures invalid clock IDs -1 and INT_MAX for public
clock_gettime/getres, checking -1/EINVAL each call. 100,000 calls/batch, one warmup
batch, 11 saved rounds, ordered TSC and AUX migration checks. These are diagnostic
batch costs including errno reset/check overhead; not formal READ latency, per-call
P99 or independent boots. The runner executes opt2 then opt4 on one matching boot;
order is not randomized, so tiny timing differences are not a causal performance claim.
It does not force gettimeofday/getcpu errors on the actual carrier; those semantics
are covered by the mock tests, and their error timing remains outside this diagnostic.

Actual matched-package public diagnostic binaries compiled with -Werror: PASS.
Non-root execution fails before creating output: PASS. True target namespace and
invalid-clock timing: NOT_RUN. Sandbox sudo was unavailable; an outside-sandbox
`sudo -n true` also required a password. No carrier was registered, no modules loaded,
no formal measurements, packages, campaign states or old results were modified.

## Fixed diagnostic entry

From baremetal, on the existing **vkso-normal** boot:

```bash
sudo python3 -B ../direct-api/supplemental.py \
  --reference "$PWD/artifacts/direct-normal-entry-opt2" \
  --package "$PWD/artifacts/direct-normal-entry-opt4" \
  --out "$PWD/validation/opt4-public-special-normal" --execute
```

No kernel rebuild, GRUB installation, begin, or 16-boot campaign is needed. This
command builds only a diagnostic executable linked to each existing public library.
Use a new output directory on retry. For no-retpoline, use the two corresponding
no-retpoline packages on the matching vkso-no-retpoline boot; do not relabel results.

Without --execute, the same command compiles and records NOT_RUN without module or
namespace operations. The runner verifies both packages and matching kernel/carrier,
uses the collection lock, verifies target UTS/config before reversible CPU tuning,
then applies the full existing collection preflight including installed image/auxv.
It registers each package's own carrier, executes checks, restores registration and
unloads only its own module. Failed restore retains the backing module. CPU tuning
and irqbalance are restored; failures are reported as FAIL, never PASS.

Output: diagnostic.json with source/binary/package/boot identity; reference/candidate
namespace and error logs; registration/restore logs. New code is test-only and does
not change the sealed opt4 library or require rebuilding the experimental package.

## Existing kernel READ results

Extended the existing results.py with --kernel. It validates full acquisition
checksums, functional evidence, PFNs, boot identities and raw kernel sample matrix
before calculating per-boot medians and independent-boot summaries. It never modifies
source runs. Example (new output path required):

```bash
python3 -B ../direct-api/results.py --kernel \
  results/20260923T062446Z-direct-api/block-*/* \
  --out validation/kernel-opt4.json
```

All three campaigns have been analyzed in `baremetal/validation/opt4-kernel-analysis/`;
comparison.csv contains both variants' absolute costs/deltas/percentages plus changes
from opt2. Units are TSC ticks/call, even though the original CSV column is named
`total_tsc_cycles`. Each case has four independent boots, each with 31 samples/API.

Latest opt4 campaign:

| Variant | Kernel API | Raw | VKSO | VKSO - Raw | Percent |
|---|---|---:|---:|---:|---:|
| normal | monotonic | 55.704 | 55.193 | -0.512 | -0.92% |
| normal | monotonic_raw | 55.205 | 54.199 | -1.006 | -1.82% |
| normal | monotonic_coarse | 9.031 | 11.038 | +2.007 | +22.22% |
| no-retpoline | monotonic | 58.883 | 55.493 | -3.390 | -5.76% |
| no-retpoline | monotonic_raw | 54.238 | 53.187 | -1.051 | -1.94% |
| no-retpoline | monotonic_coarse | 11.039 | 9.036 | -2.003 | -18.14% |

The no-retpoline coarse VKSO/Raw bootstrap interval is approximately [0.8181, 1.0006],
so its lower point estimate is not a firm improvement claim. The normal coarse
penalty is stable across campaigns. Kernels/carriers/reader modules are byte-identical
between opt2 and opt4: none of these kernel deltas demonstrates a wrapper optimization
benefit. Raw normal monotonic_raw itself moved about -1.337 ticks between campaigns.
Only four boots per case and pointwise, uncorrected intervals: do not claim equivalence
or attribute all differences to sharing/retpoline alone. UPDATE/concurrent writer
performance and runtime RSS remain NOT_RUN in this task.

## Target execution follow-up (2026-09-23)

The user executed `validation/opt4-public-special-normal` on vkso-normal.
`diagnostic.json` status PASS. Source, diagnostic binary and package inventory
hashes match; both public namespace logs pass exec/setns/offset/frozen/fast-path
checks. Both registration restore logs report success and unload commands completed.
This supersedes NOT_RUN above for this normal-variant diagnostic only.

Each version has 44 complete samples (2 APIs x 2 invalid IDs x 11 rounds), 100,000
calls/sample, no AUX migration, and consistent raw counters. Every timed call
checked return -1 and errno EINVAL. Median diagnostic cost (TSC ticks/call):

| API / invalid ID | opt2 | opt4 | opt4 - opt2 | Percent |
|---|---:|---:|---:|---:|
| clock_gettime / -1 | 542.145 | 543.405 | +1.260 | +0.23% |
| clock_gettime / INT_MAX | 519.963 | 524.815 | +4.851 | +0.93% |
| clock_getres / -1 | 536.762 | 538.011 | +1.249 | +0.23% |
| clock_getres / INT_MAX | 521.264 | 515.258 | -6.005 | -1.15% |

No functional regression was observed in the tested scope. Error costs are mixed,
not uniformly improved; all four per-round ranges overlap. One boot, fixed version
order and diagnostic errno checking preclude equivalence or significant-regression
claims. no-retpoline supplementary execution, forced provider failure timings,
writer/concurrent and RSS measurements remain NOT_RUN in this supplementary task.
