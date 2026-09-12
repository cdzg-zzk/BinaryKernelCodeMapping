# Evaluation execution evidence

The Clocktime campaign and its full result audit are complete. The previous
[automatic follow-up](FOLLOWUP.md) stopped before algorithm deployment and is
disabled. The manual commands below describe a separate foreground collection;
they do not enable or restart a service.

This directory implements the grouped work in
[evaluation-review.md](../../ccfa-review-reports/evaluation-review.md).
The [registration evidence audit](registration-evidence.md) records group B's
call path and completed KVM functional sessions: multi-process PFN sharing,
private COW, ordinary-user file/mapping operations and ordered normal release.
The tested owner refcount remains zero throughout registration and use.
The separate partial-failure session confirms that an earlier binding remains
visible after a later page fails and that manager success does not propagate
the kernel error. Independent owner pinning, completion acknowledgement and
transactional recovery remain open, alongside real-closure setup and resource
accounting. The [registration proposal](proposals/registration-transactions.md)
is unapplied.

Group D now has a [fixed candidate set and inspection driver](applicability.md).
Group E has a [complete LZ4 CLI workflow](lz4-cli/README.md) prepared for the
same owner-registration sessions as group C. Both CLIs have compiled and passed
48 full-input ordinary-DSO functional cases. The
[registered LZ4 application](lz4-application-evidence.md) fails on its first
compression call: an unchanged direct helper call reaches an unmapped target.
The [exporter proposal](proposals/export-direct-calls.md) corrects the erroneous
acceptance but is unapplied and does not complete the binding method.
The [fresh BCH session](bch-functional-evidence.md) passes the full existing
correctness matrix and four declared source/user PFN matches. These are
functional observations; complete deployment performance remains outstanding.

## Isolated registration fixture

Run with ordinary host KVM access; all module operations occur inside a fresh
private guest using the existing packaged 5.15.198 components:

```sh
python3 test/evaluation/registration_qemu.py \
  --output test/evaluation/results/registration-qemu-new
```

The output directory must be new. The runner retains the payload, private disk,
guest console and extracted observations. The fixture exercises the full
registration mechanism with a controlled synthetic file offset; it does not
measure API performance or complete group B's setup/net-memory requirements.
The recorded cases and untested boundaries are listed in
[registration-evidence.md](registration-evidence.md#isolated-runtime-observations-2026-09-12).

To observe the current partial-registration and error-reporting behavior in
another fresh guest:

```sh
python3 test/evaluation/registration_qemu.py --case partial-failure \
  --output test/evaluation/results/registration-qemu-partial-new
```

This observation completes when both the kernel and manager outcomes are
recorded and the controlled file is restored. Completion is not a passing
atomicity result: the recorded current implementation exposes the first
registered binding even when its second page fails, and the manager reports
success despite kernel errors. See the
[partial-failure evidence](registration-evidence.md#partial-registration-and-completion-reporting).

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
  --output test/evaluation/results/algorithm-deployments-20260912 \
  --with-lz4-workflow
```

After Clocktime has completed and the machine has returned to
`5.15.0-119-generic`, execute the same plan:

```sh
sudo python3 test/evaluation/algorithm_deployments.py \
  --output test/evaluation/results/algorithm-deployments-20260912 \
  --with-lz4-workflow --execute
```

The script refuses to run while the Clocktime service is active, on another
kernel, or with an existing output directory. It does not install a service
or restart the machine. Each deployment retains its own build, workspace,
results, full runner log, owner object, boot identity, and normalized
observations. A failure stops the sequence and preserves its files; there is
no automatic retry or overwrite. Existing algorithm archives remain intact.

Run this command from the repository owner's terminal after other active
analysis/measurement jobs finish. It needs module-load/page-registration
privileges. The current Codex account has no noninteractive sudo credential;
do not send a password in the conversation. The runner now checks Git access
before creating the output directory, preserving the original Git refusal if
source capture fails. No repository trust setting is changed. The local
`git-config(1)` documentation describes how a normal sudo session retains the
invoking owner's UID for Git ownership checks; a root system service need not
have that context. The earlier service failure is consistent with this
distinction, but has not been independently reproduced under root here.

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
and every numeric Markdown table unchanged. Clocktime has since completed;
the follow-up service failed before deployment and is disabled. Full deployment
execution now uses the separate foreground command above.

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
