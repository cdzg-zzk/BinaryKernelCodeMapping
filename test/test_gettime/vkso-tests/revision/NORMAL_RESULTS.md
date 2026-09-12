# Clocktime Normal campaign: completed results

The 20-boot campaign completed on 2026-09-12. The machine returned to
Linux 5.15.0-119-generic. This report covers the unchanged full Clocktime
implementation and the frozen five-boot-per-backend/per-role allocation.
Historical no-retpoline observations remain separate single-boot diagnostics.

## Evidence and estimators

All 60,195 normalized rows passed coverage and completion-identity checks.
The independent reader auditor reconstructed 43,095 values across all 20 boots;
the writer auditor reconstructed the other 17,100 values from 4,275 windows
containing 13,893,682 raw samples. There were no dropped writer records.
All 30 saved ABI logs passed their default matrix, with one allowed CPU per
ABI run. The 20 PFN observations passed, including same-boot source identity.
Sequence counts and concurrent control-window containment also passed.

The reporter reproduced all 729 comparisons and their bootstrap intervals
byte for byte from the archived measurements. Each method/role has five boots.
Within a boot, each measurement is the median over its configured rounds.
Across boots, method values are medians of those boot medians. Raw comparisons
use the ratio/difference of independently booted method medians; VKSO/Copy uses
the median of same-boot ratios/differences. These estimators need not compose
algebraically. Pointwise 95% percentile intervals use 10,000 bootstrap samples
of boots (seed 1729), preserving same-boot pairing for VKSO/Copy. They are not
simultaneous intervals or an equivalence test. Five boots give limited resolution.

Copy is the full compact-split carrier: code, wrappers, offsets and shared
state match VKSO, while user text has separate physical backing. Raw/Copy
still combines changes in snapshot, publication and entry organization.
READ disables the writer recorder. UPDATE enables it and subtracts each raw
file's recorded TSC-pair calibration. Kernels use fixed layout; user READ uses
`setarch -R`. Results describe these packaged images and this four-core machine.

## Public and ordinary kernel readers

The 20 public paths have an equal-weight geometric-mean VKSO/Raw increase of
0.922%, while the seven clock_gettime fast paths increase 3.863%. These are
descriptive interface summaries, not application-weighted effects or uniform
per-path bounds. `gettimeofday(NULL,NULL)` rises from 6.021 to 8.028 cycles,
33.33%; monotonic-raw rises from 52.184 to 54.879 cycles, 5.17%.
VKSO/Copy paired public-path point ratios range from 0.996906 to 1.003232;
19 of 20 pointwise intervals include one. This does not establish equivalence.

Ordinary `ktime_get_ts64` and `ktime_get_raw_ts64` batch costs fall by about one
cycle, while `ktime_get_coarse_ts64` rises from 9.033 to 11.039 cycles
(+2.006 cycles, 95% interval +1.004 to +4.013). The coarse cost is therefore
visible at the ordinary kernel API as well as the user entry.

Tables: [all public paths](results/normal-analysis/public.md),
[API groups](results/normal-analysis/groups.md),
[ordinary kernel APIs](results/normal-analysis/kernel.md).

## Writer variation changes the conclusion

Idle writer mean rises from 110.611 to 166.881 corrected cycles in the
across-boot point estimate: ratio 1.509 [0.727, 2.026]. P99 falls from 575.000
to 504.960 cycles, but its ratio interval is 0.235–3.638. All 19 VKSO/Raw
writer-mean intervals and all 19 P99 intervals include one. The earlier
single-boot claim of consistently lower writer mean and tails is unsupported
by this campaign.

Idle mean boot medians range from 87.823–220.906 for Raw, 80.455–195.597 for
VKSO, and 172.968–203.025 for Copy. The last VKSO boot has mean 80.455 versus
191.715 for Copy in the same boot; this observation is retained along with
all others. Method order alternates by boot, but these data do not isolate
the cause of the large writer variation. Same-boot VKSO/Copy writer-mean
ratios are 0.920–0.984; 8 of 19 pointwise intervals lie below one, while 11
include it. Report this limited paired observation without attributing the
whole Raw/VKSO change to physical code sharing.

Every recorded sample has action zero, which is not a unique caller label.
CPU counts are 13,893,551 on CPU 0, 58 on CPU 1, 49 on CPU 2 and 24 on CPU 3.
Main estimates retain all 131 non-CPU0 records. A separate CPU0-only sensitivity
reconstructs the 40 affected windows (160 normalized values); the maximum
change in any writer point ratio is 0.001861, or 0.1861 percentage points.
These rare records do not account for the large boot variation.

Tables: [idle](results/normal-analysis/idle.md),
[all writer statistics and comparisons](results/normal-analysis/writer_all.md),
[boot medians](results/normal-analysis/boot-medians.csv),
[CPU0-only sensitivity](results/normal-analysis/cpu0-writer-summary.csv).

## Concurrent readers and diagnostics

The matrix covers monotonic/raw/coarse, one to three readers on CPUs 1–3,
and saturated or one-million-calls/s-per-reader batch-paced load. Each
15-second reader window contains the writer control envelope around its
nominal 13-second collection. Control timestamps do not identify the exact
first and last recorded update. Calls/s includes conditioning calls.

VKSO saturated total-throughput ratios are 0.989–0.990 for monotonic,
0.957658–0.957998 for raw, and 0.929–0.932 for coarse across the reader counts.
Achieved paced per-reader rate/target ranges from 0.9999968368 to 1.0000032182,
with zero late batches. This is batch-paced demand, not a per-request latency
distribution. Jain fairness is near one in boot summaries, but the minimum
individual-window fairness is 0.922232 (VKSO, two saturated coarse readers,
step 003); this observation is retained in the per-scenario range table.

Sequence diagnostics are separate 100-million-snapshot runs on each image.
VKSO/Copy successful snapshots cost about 45.158 cycles versus Raw's 43.151.
Hres retry medians decrease, while raw-protocol retry medians increase for
VKSO in both image roles. Retry behavior is not uniformly improved and does
not substitute for full public-API timing.

Tables: [total throughput](results/normal-analysis/concurrent.md),
[each reader's cycles](results/normal-analysis/reader_all.md),
[fairness with observed minima](results/normal-analysis/fairness.md),
[concurrent writer](results/normal-analysis/writer.md),
[sequence diagnostics](results/normal-analysis/sequence.md).
The campaign [summary CSV](results/normal-campaign/summary.csv) additionally
contains all individual achieved-rate and late-batch comparisons, along with
absolute differences and intervals for every metric.

## Physical pages and scope

Every VKSO observation has two shared text pages and one shared state page:
three unique source/user PFNs. Copy uses the same three kernel source pages,
two separate user text pages, and the shared state page: five union PFNs.
Loader text/state permissions are RX/R--. This establishes backing relations
within the declared closure. Carrier metadata, private support, page tables,
mapping infrastructure and other kernel memory are outside that union;
whole-system net memory belongs to the separate registration/resource study.
Historical product SLOC and symbol-byte results retain their original scopes.

## Reproduction and remaining work

Audit reports are in `results/record-audit-full-20260912T030118Z/` and
`test/evaluation/results/post-clocktime-20260911/clocktime-{coverage,writer-*}.log`
(the latter path is relative to the repository root). Reporting reads these
completed records; it does not launch a benchmark or modify the collector.
From the repository root, choose a fresh output directory:

```bash
python3 test/test_gettime/vkso-tests/revision/report_results.py \
  test/test_gettime/vkso-tests/revision/results/normal-campaign \
  test/test_gettime/vkso-tests/revision/results/record-audit-full-20260912T030118Z \
  test/evaluation/results/post-clocktime-20260911 \
  /tmp/clocktime-normal-report
```

The campaign supports a full three-method report, including costs and uncertain
writer effects; it does not require extra repetitions to seek favorable ratios.
Explaining writer boot variation would need a separately specified diagnostic,
not exclusion of observed boots. B's resource/lifetime study, C's algorithm
deployments/diagnosis, D's applicability runs and E's application remain separate
unfinished work. The automatic follow-up stopped before algorithm deployment:
its initial Git source-diff capture failed, and the service is now disabled.
