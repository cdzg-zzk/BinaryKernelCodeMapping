# Complete-task setup collection

These observers measure the three lifecycle scopes in group B: current
export/deployment, registration of an already constructed carrier, and a new
process using an active registration. The full algorithm DSOs and owner
implementations are unchanged. Each C observer includes the existing benchmark
source to reuse its API loading, allocation, input and full-result validation
helpers. Unused benchmark main functions are not invoked.

| Task | Input and first valid result |
| --- | --- |
| LZ4 | All 12 Silesia files, 211,938,580 bytes, split into the existing 64 KiB blocks; complete compression, decompression and full-byte comparison |
| BCH | Original m=13, t=4/8 geometries and deterministic 512-byte payloads; initialize and encode, exercise all 0..t error counts with the full decode path, verify locations and corrected codewords, and free controls |
| XZ | All three original bash/Python/libc files; full XZ_SINGLE decode, complete input consumption/output length, full-byte comparison and output guards |

BCH uses the original trial-zero error vectors for this latency task, and
retains complete initialization and full decoding. The separate existing
128-vector, three-backend, two-decode-path functional matrix still runs; this
setup task does not replace that correctness coverage. One or three complete
tasks per process distinguish short and repeated work. For BCH and XZ each
task initializes and frees its controls; LZ4 retains the process work buffer.
The one-round results do not estimate steady-state throughput or a break-even
call count.

## Clocks and boundaries

All event timestamps use CLOCK_MONOTONIC_RAW within one boot. C observers keep
timestamps in a fixed buffer and print them after work and dlclose. They
record main entry, load, dlopen, dlsym, input preparation where applicable,
task, first valid result and unload. `dlopen(RTLD_NOW)` includes constructors
and carrier-private binding. Those costs are not independently attributed
by subtracting dlsym from load.

The Python controller records external process start/return timestamps and
retains raw stdout and the argument vector. Input I/O is inside the
load-to-first-valid interval for LZ4/XZ and is separately marked. Full result
validation is also inside the first-valid boundary. The process lifetime
includes startup and output of buffered evidence.

`VKSO_SETUP_TRACE` and `VKSO_SETUP_CLOCK` optionally enable shell stage events
in the actual `vkso` command. Ordinary executions omit this instrumentation.
The observer covers KRG construction/cache lookup, closure checking, header
construction, carrier construction, shim/build-output installation, session
preparation, manager startup/READY, application execution and cleanup. The
clock helper is an external process: its launch, timestamp output and exit
cost remain in instrumented intervals. Do not subtract a generic constant or
interpret these shell markers as precision microbenchmarks. Formal sampling
must retain an uninstrumented external comparison and measure observer cost
in the same measurement environment.

Kernel response logs already contain exchange wall time and callback,
prepare, apply and release durations. Prepare/apply are nested in COMMIT and
remain present in the later RELEASE reply; sum neither these nested intervals
nor repeated cumulative fields. Manager READY additionally includes identity
checks, durable state writes, filesystem flags and userspace scheduling.

## Execution paths

`vkso exec` runs the current build/export command and then starts the guarded
registration. `vkso exec-ready` uses existing build outputs and the same
manager/notification/cleanup functions; owner and kernel build-ID checks,
plan validation and registration are still required. Reuse of an old carrier
does not bypass the manager's deployment identity checks.

The guest first executes six processes during the full-export registration:
VKSO/one task, native/one, native/three, VKSO/three, VKSO/one and native/one.
The first VKSO process precedes the PFN observer and the original full
benchmark. After release, an exec-ready session repeats the same process
schedule. PFNs and restored mappings are checked by the existing guest
observer, and test modules unload normally.

The first process is the first application after registration, not a claim of
cold system caches: build and kernel registration have already accessed their
inputs and prepared pages. Later processes use naturally warm caches without
drop_caches. This fixed diagnostic order is not a randomized performance
comparison. The full deployment's external end includes the separate original
functional workflow; use its external start to the first task's valid result
for setup-to-first-result. Its complete wall time is not the lifetime of a
single short task.

## Reproduction

Build the observers without loading a host module:

```sh
python3 test/evaluation/setup/build.py /tmp/vkso-setup-build
```

The existing `lz4_qemu.py`, `bch_qemu.py` and `xz_qemu.py` launchers copy these
binaries and sources into new private guest runs. Preparation archives the
compiler argument vectors and the included benchmark source files, including
ignored repository inputs. `setup/collect.py` is the in-guest controller.

After a completed run, reconstruct its observations without running code:

```sh
python3 test/evaluation/setup/audit.py RESULT_DIRECTORY bch
```

The auditor checks all 12 raw process logs, both session traces, the outer
command interval, first-result boundaries, six distinct process IDs per
session, task coverage, nested intervals, and the two actual kernel
COMMIT/RELEASE sequences. It also requires full guest success, PFN evidence
and module cleanup. Failed/truncated logs and invalid event boundaries are
not accepted as observations.

These guest runs validate the collection protocol. Formal physical-machine
costs remain separate from guest evidence. The current claim-based stopping
criteria are in the evaluation review; historical group B checklists do not
automatically require more experiments.

## Matched LZ4 command comparison

`compare.py` uses the same complete LZ4 task for the ordinary same-source DSO
with libc helpers and the actual registered carrier. `active` launches new
processes while registration is held; `ready` compares an ordinary DSO command
with `vkso exec-ready`, including registration and release. The carrier is
already constructed in both phases. Offline closure analysis and carrier
construction are a separate deployment scope, not included in these totals.
The complete LZ4 CLI workflow is also measured separately: this task includes
all corpus I/O, allocation, compression, decompression and full-byte validation,
but does not implement the CLI's framing and output-file workflow.

Each phase has Native/VKSO × trace off/on × one/three complete corpus passes,
with three rounds and two full warmup commands. All 12 Silesia files remain
present (211,938,580 bytes, 64 KiB blocks). Condition order rotates and reverses
between rounds; it is deterministic. Repeated use warms input caches without
eviction. Processes inherit the selected CPU. The independent repetition unit
in a formal campaign is a complete owner deployment, not these inner rounds.

Trace-off builds compile out C event collection and omit shell tracing.
External elapsed time includes process launch, complete work and exit. Trace-on
runs additionally record first valid result and nested stages, and retain the
observer cost in their totals. Thirty separate clock-helper invocations measure
the shell observer in the same environment; no constant is subtracted.

The actual complete guest run and independent reconstruction are recorded in
[setup-comparison-evidence.md](../setup-comparison-evidence.md). Both phases
passed with 24 measured commands each. `compare_audit.py` checks raw task output,
event boundaries, condition order, calibration and all 13 added ready-carrier
registrations against the original manager log. The original two-session audit
accounts for these independently checked registrations before checking its own
two sessions; it does not ignore additional manager records.

`algorithm_deployments.py --with-lz4-setup` runs both phases within each complete
LZ4 owner deployment, alongside the optional CLI and kernel cost collectors.
No further guest repetition is needed for this unchanged path. Remaining work
is formal physical-host collection and deployment-level analysis, including
the separately reported offline export cost.
