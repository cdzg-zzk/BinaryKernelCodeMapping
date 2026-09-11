# Clocktime experiment revision

This directory adds measurement tools around the existing complete Clocktime
implementation. The VKSO kernel, public wrapper, original READ executable and
page-registration implementation are unchanged. Work branch:
`experiment/clocktime-evaluation-revision`, based on paper commit `849ecf6`.

## Experiment groups

| Shared work | Collection | Interpretation |
| --- | --- | --- |
| Boot schedule and statistics | Five independent boots per Raw/VKSO image, separately for READ and recorder-enabled UPDATE | Median within each boot; boots are the sampling units |
| User/kernel READ | Unchanged public READ executable, 31 rounds across 7 processes; ordinary exported kernel APIs through a test module | Cost at both execution locations |
| Writer and concurrent readers | Idle and 1/2/3 processes, monotonic/raw/coarse, saturated and 1,000,000 total calls/s/reader | Reader cost, achieved throughput, fairness and writer mean/P95/P99 |
| Physical-sharing comparison | VKSO versus complete copied code using the same ELF offsets, entry/support code and shared state | Physical code backing, with algorithm/state/entry held fixed |
| Functionality and evidence | Existing ABI matrix, separate sequence diagnostic, runtime PFNs, immutable package identity | Correct method identity and explicit scope |

The primary campaign uses the archived Normal packages. Existing no-retpoline
measurements remain diagnostic; this revision does not substitute them for the
Normal comparison.

## Methods and measurement scope

`raw` is the original kernel and vDSO. `vkso` is the existing final VKSO kernel
and registered carrier. `compact-split` runs on that **same VKSO kernel**, but
materializes the entire live carrier file into ordinary user file backing and
registers only its shared-data page. Runtime text bytes, virtual offsets, public
wrapper, algorithms and state publication are preserved. It is a physical-code
copy comparison, not a stock-kernel implementation or a separate rewrite of the
time algorithms. Raw versus compact-split still includes the subsystem/entry
restructuring; it cannot attribute every difference solely to snapshot layout.

`multireader.c` includes the original benchmark to reuse its actual direct API
loops. The companion forks pinned processes, conditions each batch, and places
TSC timestamps around the same public API body. Clock syscalls, pacing and
writer controls are outside that timed body. The fixed rate includes **both**
conditioning and measured calls. It is a sequence of fixed-size bursts, not a
smooth arrival process or a per-request tail-latency measurement. Late batches
and achieved rates are retained; a rate target alone does not establish equal
achieved load. Endpoint checks supplement the existing semantic matrix and do
not claim to check every call for monotonicity.

The kernel module calls `ktime_get_ts64`, `ktime_get_raw_ts64` and
`ktime_get_coarse_ts64` directly in batches on the selected CPU. Interrupts stay
enabled. A checksum prevents result elimination; reported cycles include the
same loop/checksum work on both kernels. Its debugfs PFN query is read-only and
has no hooks in the time implementation.

The default UPDATE allocation is 15 rounds per boot. Each load lasts 15 seconds;
the writer recorder observes its 13-second interior, after every reader has
started and before any finishes. Idle writer sampling also lasts 13 seconds.
Per-update P99 is computed within each recorder window, then summarized across
boots separately from the mean. Sequence retry diagnostics are separate from
the timed public reader path. All individual paths, including regressions and
short paths, remain available. Ratios and absolute differences have boot-based
bootstrap intervals; fewer than three boots produce descriptive values only.
An interval containing equality is not an equivalence test.

All formal reader executions use the existing fixed `setarch -R` layout. The
result scope is this layout and the current machine; rebooting does not vary ELF
link layout or demonstrate cross-CPU generality.

PFN evidence counts the **declared closure**. `footprint.json` also retains actual
carrier `smaps`, including support mappings. Closure PFNs, mapping RSS/PSS,
symbol bytes and whole-system net memory are different quantities. This tool
does not claim to measure the latter or the full Raw kernel/vDSO footprint.

## Build and functional validation

```sh
bash revision/build-tools.sh baremetal/artifacts/reader-load-v4-update-normal \
    revision/build PREPARED_KERNEL_BUILD
python3 -m unittest discover -s revision -p 'test_*.py' -v
python3 revision/qemu-preflight.py baremetal/artifacts/reader-load-v4-update-normal \
    revision/build revision/results/qemu-update
python3 revision/qemu-preflight.py baremetal/artifacts/reader-load-v4-normal \
    revision/build revision/results/qemu-read
```

Commands above assume the `vkso-tests` working directory. The prepared build
must match the packaged kernel configuration. Preparation for this revision was
performed in a disposable copy under `/tmp`, not in the original kernel tree.
The archived target disables `CONFIG_MODVERSIONS` and its source tree lacks
`Module.symvers`; local module compilation used `KBUILD_MODPOST_WARN=1`.
Successful loading and execution on both actual packaged QEMU kernels is the
required check for symbol resolution, not the compiler exit code alone.

QEMU results are functional validation only, never bare-metal performance
evidence. The validation runs the unchanged ABI matrix, both reader collectors,
all 18 concurrent scenarios when the recorder exists, and PFN checks for both
VKSO methods. Intentional invalid-pointer subprocess faults belong to the ABI
matrix; kernel WARN/oops markers fail validation.

The first new-copy preflight exposed a dirty-file-page warning in the existing
registration module. Registration now fsyncs the freshly written test carrier
before replacing its clean page-cache pages. This is preparation outside all
performance windows. No registration code was changed. Files must not be written
while registered. Failed validation logs are retained under `results/`.

## Formal campaign

```sh
python3 revision/campaign.py prepare revision/results/normal-campaign \
    --read-package baremetal/artifacts/reader-load-v4-normal \
    --update-package baremetal/artifacts/reader-load-v4-update-normal --boots 5
python3 revision/boot.py stage revision/results/normal-campaign \
    --multireader revision/build/vkso-multireader \
    --kernel-module revision/build/kernel-reader/vkso_kernel_reader.ko
sudo python3 revision/boot.py install revision/results/normal-campaign
sudo python3 revision/boot.py start revision/results/normal-campaign
```

`stage` writes reviewable GRUB/service files into the campaign directory.
`install` adds separate entries and enables a service gated by the campaign's
`armed` file. **`start` reboots the research machine** and arms automatic
collection across all 20 planned boots. Existing boot entries and the default
entry remain intact. READ and UPDATE each have five Raw boots and five VKSO
boots. The two VKSO methods run within the same VKSO boot with alternating
order. The default complete run takes approximately 19 hours plus machine boot
time, primarily 15 rounds × 19 UPDATE scenarios × 15 method-boot collections.

The controller reserves CPU 0, isolates CPUs 1–3, disables turbo, fixes the
performance range, and stops irqbalance during collection. Every collector
checks the actual kernel/backend/configuration, package, CPU isolation and
frequency settings. Parameters and executed tools are frozen on the first boot;
changing them requires a new campaign. Each completed step is linked to a unique
boot ID, the frozen plan/protocol and its measurements. Kernel oops/WARN states
fail collection. An interrupted/failed step keeps its files and stops automatic
progress; it is not silently retried or included as complete.

```sh
python3 revision/campaign.py status revision/results/normal-campaign
systemctl status vkso-clocktime-revision.service
journalctl -u vkso-clocktime-revision.service
```

Live service/process state determines whether collection is running. An `armed`
file alone is not evidence of a live job. Per-boot output is in `step-NNN/`, and
controller logs are `step-NNN.log`. Once all boots complete, the controller
writes `summary.csv` and `campaign-complete.json`, disables its service and
returns to the original ordinary kernel. `summary.csv` is the numeric analysis;
the final experiment report still needs to inspect individual regressions,
achieved fixed rates, writer CPU records, diagnostic output and footprint scope.

After timed collection ends, run the independent coverage audit, the reader
and support-record audits for every completed step, and the raw writer audit
for every UPDATE method directory, for example:

```sh
python3 revision/audit_coverage.py revision/results/normal-campaign
python3 revision/audit_reader_records.py revision/results/normal-campaign/step-001
python3 revision/audit_reader_records.py revision/results/normal-campaign/step-003
python3 revision/audit_support_records.py revision/results/normal-campaign/step-001
python3 revision/audit_writer_records.py revision/results/normal-campaign/step-003/compact-split
```

The coverage audit returns exit code 2 when the completed prefix passes but the
campaign is still incomplete. The writer audit checks raw-file coverage against
normalized observations, recorder counts, dropped samples, sample numbering,
and recomputed statistics against both per-window JSON and normalized CSV.
It reports actual CPU/action distributions and retains all action=0 observations
in the main statistics. For windows containing other CPUs it also emits CPU0-only
statistics as a sensitivity diagnostic; action=0 does not identify a unique
caller. These postprocessing tools do not change the frozen collector.

The reader audit requires a completed step and verifies its completion identity
and full normalized coverage. It reconstructs public READ round numbering,
kernel cycles/call, concurrent call rates, total throughput and Jain fairness
from the original CSVs. It checks reader IDs/CPUs, batch accounting, shared
timestamps and containment of the writer interval within every reader window.
It also checks sequence diagnostic counter identities. User cycle averages
are compared as recorded; their underlying TSC totals were not saved in these
CSVs. Output includes achieved-rate ranges, late batches and window margins,
without filtering observations for rate deviations or lateness. Writer
timestamps bracket control requests, so their span need not be exactly the
nominal 13-second recording interval. Exit code 0 certifies only the specified
step's audited records, not the entire campaign or a performance conclusion.
The support-record auditor checks every expected default ABI status and
fast/fallback path, including both namespace fast-path checks. It reports the
actual thread count: a `multicpu_threads=pass` record with `threads=1` is not
multi-CPU evidence. It checks recorded PFNs against the declared page plan,
recomputes unique-page totals, verifies shared/copy relationships and ordinary
loader permissions, and compares source PFNs between methods within the same
boot. PROT_NONE reservations are excluded when locating readable pages.
The resulting counts describe the declared closure, not whole-system memory;
saved mapping permissions do not establish general VM or module-lifetime
behavior. These two auditors have not been added to the automatic follow-up
service while its disposition awaits the user's answer.

To stop an active campaign, remove its `armed` file and stop the service before
any next reboot. Retain partial output and inspect `failed.json`; do not convert
an interrupted run into a completed sample. If completion requires a change to
the project's foundational functionality, stop and report the reason to the
researcher before making that change.
