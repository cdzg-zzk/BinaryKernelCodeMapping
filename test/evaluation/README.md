# Evaluation execution evidence

Section 6.3 has one [current experiment entry](../section63/README.md),
[design](../section63/methods.md), and [complete report](../section63/results/report.md).
All three algorithms use new user Native/Adapted/VKSO and kernel
Stock/original-source-Matched/Owner controls. The old mixed campaign is retired.
Application/setup measurements remain [separate](results/application-setup/README.md).

LZ4 [application and setup results](results/application-setup/README.md) are
separate and retain their original measurements. Clocktime, applicability and
physical-memory evidence retain their respective directories. Current scope
and status are recorded in
[evaluation-review.md](../../ccfa-review-reports/evaluation-review.md).

## Historical execution checkpoints

The entries below preserve the order of implementation and guest validation.
Their then-pending formal collection items are superseded by the completed
campaign above. Full allocator accounting, broader platform/application
matrices and generic runtime-rewriting certification are outside the current
paper scope; they are not silently treated as implemented.

[Typed source admission](registration-typed-evidence.md) now passes the full
transaction and 96-session scale matrices. The kernel receives page kinds and
checks actual mapping permissions before replacement. Identical LZ4 binaries
under normal and `rodata=off` guest boots verify rejection of writable source
text/rodata. Protocol 4 bindings request 64 B per page; built-in publicness and
later runtime rewriting remain open.

Current registration update: [full-plan transactions and recovery](registration-transaction-evidence.md)
pass a 300-page, two-chunk failure matrix and the full registered LZ4 CLI.
The manager confirms COMMIT before ready, queries a lost ACK, and persists the
transaction ID for recovery. Owner pins, reverse rollback and idempotent release
are implemented. Occupied-slot replacement removes commit-time xarray reallocation, five
manager interruption points recover, and all three cooperative algorithm
owners pass their full runtime workflows. The manager now verifies owner and
vmlinux GNU build IDs after pinning and before staging; same-source different
builds are rejected. [FIFO completion and ordinary file/VMA checks](registration-notification-evidence.md)
now pass with root and real sudo launchers; the application retains its UID,
and competing or stale sessions preserve their recovery state. All three full
algorithm workflows pass with this wrapper. Runtime rewriting, source-page
publicness and formal setup/resource measurements remain open.
Earlier v1/v2 observations retain their original implementation identity.

[Completed transaction retirement](registration-retirement-evidence.md) now
uses FORGET after confirmed RELEASE, including recovery when the FORGET reply
is lost or the manager stops before local cleanup. The full matrix passes;
17 manager transaction IDs are absent at the end. The repeated scale matrix
passes all 96 sessions, with no terminal record after the 48 manager DONE
events. This removes completed-object accumulation; it does not establish
physical slab-page reclamation or resolve source-page admission.

[Setup collection](setup-evidence.md) now covers full export, prebuilt-carrier
registration and new-process complete tasks for all three algorithms. Six
guarded sessions and 36 task processes pass raw timestamp and release audits.
Instrumented guest durations validate collection; formal setup comparisons,
observer calibration, scaling and complete resource measurements remain open.

[The 1..32-page scan](registration-scale-evidence.md) now covers 96 registrations
with measured target-file cache state, per-page PFNs and release. It also
records transaction allocation requests, retained terminal records, manager
smaps/FDs and same-guest clock-helper calibration. These remain scoped resource
and virtualized observations; full physical accounting remains.

[Registered first-touch raw collection](first-touch-evidence.md#registered-raw-protocol-run--2026-09-12)
now completes all six Native/Stub conditions, preserving 38 batches and 3,800
calls. Empty expected-fault classes no longer stop the matrix, and the
functional validator exits before cache eviction. Executed bytes, independent
XXH32 vectors, PFNs and complete release are verified; formal physical-host
repetitions remain open.

[The registered pressure scenario](first-touch-evidence.md#reclaim-pressure-scenario--2026-09-12)
now retains 60 calls across baseline, reclaim pressure and recovery. All ten
pressure windows show actual reclaim; both Native and Stub code pages remain
resident, so this workload does not reproduce the native major faults seen
after explicit cache dropping. All hashes, 30 per-call Stub PFNs and complete
release pass. The pressure run is a guest residency diagnostic; it adds no
physical-host latency estimate or net-memory claim.

[The cross-case adaptation ledger](applicability-ledger-evidence.md) now covers all six deployed cases, preserving the eight prospective outcomes. It joins actual carrier structure and bindings with current algorithm support and independently reconstructed Clocktime source scopes. All 44 compared files replay from their archived patches. [Current-owner kernel workloads](kernel-cost-evidence.md) pass in the same three registrations as the complete user workloads: 2,739 kernel timing rows, full output checks, 13 declared PFNs and release. D's functional/source deliverables are complete; C/E physical performance and BCH regression diagnosis remain open.

The Clocktime campaign and its full result audit are complete. The previous
[automatic follow-up](FOLLOWUP.md) stopped before algorithm deployment and is
disabled. The manual commands below describe a separate foreground collection;
they do not enable or restart a service.

This directory implements the grouped work in
[evaluation-review.md](../../ccfa-review-reports/evaluation-review.md).
The [registration evidence audit](registration-evidence.md) records group B's
call path and completed KVM functional sessions: multi-process PFN sharing,
private COW, ordinary-user file/mapping operations and ordered normal release.
In that original implementation, the tested owner refcount remains zero throughout registration and use.
The separate partial-failure session confirms that an earlier binding remains
visible after a later page fails and that manager success does not propagate
the kernel error. Later v3 evidence supplies owner pinning, completion acknowledgement and
transactional recovery. Real-closure setup and resource accounting remain open;
the [registration proposal](proposals/registration-transactions.md) tracks the
implemented and remaining requirements.

The [BCH resource session](results/bch_resource-qemu-20260912-attempt03/README.md)
adds raw PFN unions across 1/4/16 simultaneous loaders, full dedicated-owner
core coverage and separate manager/page-table observations. Its measured
library/shim/owner scope is equal to the owner-loaded native comparison for
one loader and larger for four or sixteen. Shared target pages alone therefore
do not establish net savings. Control/workload heaps and full allocator costs
remain outside this measurement.

Group D now has a [fixed candidate set and inspection driver](applicability.md).
The revised checker batch completed all eight fixed cases: xxh32 and sort
passed, while crc32_le, sha256, hex_dump_to_buffer, string_escape_mem,
rhashtable_insert_slow and get_random_bytes failed static checks. xxh32 and
sort additionally have registered PFN and typed functional evidence; the six
static failures have no carrier/runtime result.
Group E has a [complete LZ4 CLI workflow](lz4-cli/README.md) prepared for the
same owner-registration sessions as group C. Both CLIs have compiled and passed
48 full-input ordinary-DSO functional cases. The
[registered LZ4 application](lz4-application-evidence.md) previously failed on
its first compression call because an unchanged direct helper call reached an
unmapped target. The exporter now rejects that direct Shim reference and
supports an explicit private-data binding contract for the helper bridge.
The rebuilt guest passes all 24 registered input/block pairs and records
five source/user PFN matches. KVM access is available after removal of the
execution-environment restriction. Formal application performance is pending.
The [fresh BCH session](bch-functional-evidence.md) passes the full existing
correctness matrix and four declared source/user PFN matches. The
[fresh XZ session](xz-functional-evidence.md) also passes all three complete
inputs with the original benchmark and four PFN matches before and after the
workload. These are functional observations; complete deployment performance
remains outstanding.

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

To reproduce the archived original partial-registration and error-reporting behavior in
another fresh guest:

```sh
python3 test/evaluation/registration_qemu.py --case partial-failure \
  --output test/evaluation/results/registration-qemu-partial-new
```

This observation completes when both the kernel and manager outcomes are
recorded and the controlled file is restored. Completion is not a passing
atomicity result: the recorded original implementation exposes the first
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
  --with-lz4-workflow --with-kernel-cost --with-lz4-setup
```

The registered LZ4 functional matrix and matched libc baseline pass, as does
the complete setup comparison. The kernel-side host hooks are prepared;
their complete registered host execution remains to be measured.
With the machine on `5.15.0-119-generic`,
the prepared deployment command is:

```sh
sudo python3 test/evaluation/algorithm_deployments.py \
  --output test/evaluation/results/algorithm-deployments-20260912 \
  --with-lz4-workflow --with-kernel-cost --with-lz4-setup --execute
```

The script refuses to run while the Clocktime service is active, on another
kernel, or with an existing output directory. It does not install a service
or restart the machine. Each deployment retains its own build, workspace,
results, full runner log, owner object, boot identity, and normalized
observations. A failure stops the sequence and preserves its files; there is
no automatic retry or overwrite. Existing algorithm archives remain intact.

Run this command from the repository owner's terminal after other active
analysis/measurement jobs finish. It needs module-load/page-registration
privileges. The researcher has explicitly authorized privileged execution;
credentials are not stored in experiment files. The runner checks Git access
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
| LZ4 | Silesia, 3 block sizes, 6 backends, 7 rounds, 2-second harness windows | 126: one per round/block/backend; each measures compression and decompression |
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
The new LZ4 matrix retains the five earlier backends and adds
`kernel-userspace-libc`; the CLI uses that same-source baseline. The original
210-row archive remains valid only through the explicit historical mode.
Actual ignored owner sources and new files are captured in `source-files/`,
with owner Kbuild command records saved per deployment.

The validator checks the complete expected matrices (252 LZ4, 1,056 BCH,
42 XZ rows per deployment), duplicate/missing keys, and positive numeric
counters. BCH and XZ rates derive from their lossless timing counters.
Closure/correctness checks remain in the full runners. Matrix completeness
alone does not prove active PFN identity or a performance conclusion.

## Verified existing evidence

The [BCH kernel-side comparison](bch-kernel-evidence.md) adds a separate driver
that directly imports the stock, matched-source and actual owner APIs. The
matched-source control uses the complete unadapted source and the owner's
algorithm compiler arguments. Private exact119 guests pass all 10,752 decode
checks and the full 1,056-row collection path. Guest timings remain diagnostic;
formal kernel-side costs still require the planned bare-metal measurements.
The original owner and registration/export implementation are unchanged.

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

The [prospective applicability result](applicability-evidence.md) adds actual
built-in xxh32/sort exports with independent kernel/user functional checks.
Following the task/adaptation evidence in Orbit, it tests complete typed APIs
and domain-local callbacks. Following the separation of mechanism, memory and
application results in µFork and Userspace Bypass, it counts sort's generated
thunk page separately and leaves performance and full-application conclusions
to their corresponding experiments. These three original Evaluation sections
were rechecked on 2026-09-12 for this update.

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
