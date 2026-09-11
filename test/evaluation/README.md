# Evaluation execution evidence

This directory implements the grouped work in
[evaluation-review.md](../../ccfa-review-reports/evaluation-review.md).
The current addition concerns algorithm repetition identities (group C) and
the corresponding manuscript/report corrections (group F).

## Algorithm deployments

`algorithm_deployments.py` invokes the complete existing LZ4, BCH, and XZ
runners. Each invocation builds its libraries, loads the real owner module,
resolves its current addresses, exports and registers the carrier, validates
outputs, measures all configured cases, restores the carrier, and unloads the
owner. The orchestrator checks that the owner is no longer loaded afterward;
this is a normal cleanup observation, not a concurrent lifetime test.

Print the plan without building or running anything:

```sh
python3 test/evaluation/algorithm_deployments.py \
  --output test/evaluation/results/algorithm-deployments-20260911
```

After Clocktime has completed and the machine has returned to
`5.15.0-119-generic`, execute the same plan:

```sh
sudo python3 test/evaluation/algorithm_deployments.py \
  --output test/evaluation/results/algorithm-deployments-20260911 --execute
```

The script refuses to run while the Clocktime service is active, on another
kernel, or with an existing output directory. It does not install a service
or restart the machine. Each deployment retains its own build, workspace,
results, full runner log, owner object, boot identity, and normalized
observations. A failure stops the sequence and preserves its files; there is
no automatic retry or overwrite. Existing algorithm archives remain intact.

The initial allocation is three complete deployments per algorithm, all on
the original algorithm kernel, using the archived full workload sizes:

| Algorithm | Workload within each deployment | Measurement processes |
| --- | --- | --- |
| LZ4 | Silesia, 3 block sizes, 5 backends, 7 rounds, 2-second harness windows | 105: one per round/block/backend; each measures compression and decompression |
| BCH | m13t4/m13t8, all error counts, init/encode/two decode modes, 11 rounds, 10 ms samples, 128 correctness vectors | 1, with all 3 backends loaded |
| XZ | bash/python3/libc inputs, 7 rounds, 20 complete decodes per input/backend | 1, with both backends loaded |

Algorithm order rotates across the three deployment blocks. Within each
deployment, each original runner retains its backend/workload rotation.
Reusing the complete workload allows the BCH regression and its comparison
cases to be examined together. Three deployments are a bounded initial check
of redeployment sensitivity; they do not establish cross-boot independence,
hardware generality, or statistical equivalence. Report each deployment's
paired-ratio summary and its spread before deciding whether further evidence
is needed. Do not pool inner rounds as independent deployments.

Archived metadata spans about 43 minutes in total for three repetitions of
these three runners' post-setup intervals. New builds, export preparation,
correctness work outside those intervals, and cleanup add to that estimate.
`runner_wall_seconds` records the full runner, including timed benchmark work;
it is not setup-to-first-call latency and does not complete group B.

`observations.csv` labels every row by deployment, algorithm, logical
measurement-process scope, round, backend, workload, and unit. The process
scope follows the verified runner structure; it is not an observed PID.
The validator checks the complete expected matrices (210 LZ4, 1,056 BCH,
42 XZ rows per deployment), duplicate/missing keys, and positive numeric
counters. BCH and XZ rates derive from their lossless timing counters.
Closure/correctness checks remain in the full runners. Matrix completeness
alone does not prove active PFN identity or a performance conclusion.

## Verified existing evidence

The [algorithm evidence note](algorithm-evidence.md) records the old
deployment boundaries, comparison identities, and BCH diagnostic targets.
The canonical manuscript and generated summaries now describe their existing
results as within-deployment repetitions. Their numeric result tables and raw
data were preserved.

Validation on 2026-09-11: all three archived raw matrices passed; duplicate
and missing-row mutations were rejected for each algorithm. The live-host
guard rejected collection while Clocktime was active. Regenerating the four
algorithm summaries left all five numeric aggregate/pairwise CSVs byte-identical
and every numeric Markdown table unchanged. Full deployment execution is
pending completion of the Clocktime campaign.

## Evaluation design references

The following evaluation practices guide the additional evidence; their
sample counts and reported speedups are not requirements or baselines for VKSO.

- [Orbit, OSDI 2022, §5](https://www.usenix.org/system/files/osdi22-jing.pdf)
  separates creation/invocation costs from the cost and utility of real
  auxiliary tasks. This motivates measuring VKSO setup separately from
  steady algorithm calls and retaining a real application workflow.
- [Userspace Bypass, OSDI 2023, §6](https://www.usenix.org/system/files/osdi23-zhou-zhe.pdf)
  combines microbenchmarks with Redis/Nginx and varies deployment conditions;
  its application table includes regressions. VKSO likewise retains BCH
  regressions and distinguishes controlled comparisons from application cost.
- [µFork, SOSP 2025, §5](https://owl.eu.com/papers/ufork-sosp25.pdf)
  evaluates creation, memory, applications, and meaningful alternative designs.
  VKSO's full-code-copy control addresses physical sharing, while the separate
  setup and memory ledger must account for the resources needed to obtain it.
