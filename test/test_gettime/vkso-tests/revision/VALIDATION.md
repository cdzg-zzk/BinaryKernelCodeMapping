# Validation record — 2026-09-11

Implementation commit: `e9096c3` on
`experiment/clocktime-evaluation-revision` (paper baseline `849ecf6`). The diff
from the paper branch contains only this new `revision/` directory. The original
Clocktime implementation, reader executable/wrapper sources and foundational
registration functionality were not changed.

## Completed checks

- Eight analysis/campaign tests passed: boot weighting, paired covariance,
  incomplete/duplicate samples, insufficient boot counts, absolute differences
  for zero metrics, mixed protocol rejection and changed-result rejection.
- The multi-reader companion compiled with GCC warnings treated as errors.
- The ordinary kernel reader/PFN module loaded and ran on the actual packaged
  Raw and VKSO 5.15.198 kernels in QEMU.
- `results/qemu-read-final/`: Raw, VKSO and compact-split passed the ABI matrix
  and user/kernel READ collection. Each method produced the expected 69
  normalized records for this functional allocation (20 user APIs × 3 rounds
  plus 3 kernel APIs × 3 rounds).
- `results/qemu-update-final/`: all three methods passed the 18 concurrent
  scenarios (three clocks × three reader counts × two rates), writer interior
  window checks and ABI/PFN checks. Each produced 289 normalized records for the
  short functional allocation. No kernel WARN/oops occurred.
- `results/qemu-copy-events/`: the full compact-split comparison also passed
  settime, TAI update, NTP frequency, leap schedule/transition, provider fallback
  after clocksource switching, restored-provider lifecycle and suspend/resume.
- Actual PFNs showed 3 source/user union pages for VKSO's declared closure and
  5 for compact-split: the latter uses distinct user text PFNs for both text
  pages, while both methods share the state page.
- The four staged GRUB entries match existing packaged image hashes and isolate
  CPUs 1–3. The service definition passed `systemd-analyze verify`; unrelated
  pre-existing system-unit warnings were printed. The entries and gated service
  are installed, with the default boot entry retained.

QEMU measurements are **functional evidence only**. No performance ratios from
them are used as formal Clocktime results. The physical page result describes
the declared closure, not whole-system net memory.

## Issues resolved in the measurement tools

The initial guest image lacked `setarch`; it is now included. The first PFN
observer selected an overlapping PROT_NONE loader reservation instead of a
readable PT_LOAD mapping; it now selects actual readable mappings. Newly copied
test files initially caused a dirty-page warning in the unchanged registration
module; fsync before registration resolved it, and the subsequent complete
validation had no kernel warning. Earlier failed logs remain under `results/`.

These changes are in test preparation/observation, outside the timed API body.
They did not require a change to project foundational functionality.

The first bare-metal startup stopped during frequency setup, before the
collector or any performance sample ran. This machine's BIOS disables turbo;
the Intel driver reports `no_turbo=1` but rejects even an identical write with
`EPERM`. Commit `528f4a8` skips already satisfied settings and records only
settings actually changed for restoration. The original failure is retained in
`results/normal-campaign/incomplete-initialization/`. The resumed controller
reached `min_perf_pct=100`, `no_turbo=1`, and the `performance` governor. The
sample allocation and Clocktime implementation are unchanged.

## Formal collection still required

The prepared campaign is `results/normal-campaign/plan.json`: five independent
boots per backend for each of READ and UPDATE, 20 boots in total, with complete
VKSO/copy comparisons paired within each VKSO boot. Expected runtime is about
19 hours plus boot time with the frozen default allocation.

Use the live `vkso-clocktime-revision.service` state and the campaign's
`step-NNN/complete.json`, `failed.json`, and `campaign-complete.json` to determine
current progress. This validation record does not assert that formal collection
has finished. Completion also requires inspection of the resulting individual
path regressions, achieved rates, writer CPU/sample records and boot-level
intervals, followed by an updated experiment report.

## Reader-record auditor validation — 2026-09-11

The new `audit_reader_records.py` was checked against the first completed
physical block, steps 000–003, using CPU 0 for the short file-only check.
This covered Raw, VKSO and compact-split for READ and UPDATE: 713 normalized
reader values per READ method and 2,160 per UPDATE method, 8,619 in total.
All reconstructed values matched. READ coverage included both saved syscall
and public paths plus the ordinary kernel reader; concurrent coverage included
270 CSV windows and 540 reader observations per method. Sequence diagnostic
counts were also consistent for all six method/role records.

For this block, all writer control intervals were inside every associated
reader load window. Across the three methods, the achieved fixed-rate/target
ratio ranged from 0.9999970703898143 to 1.0000032182188345; all concurrent
observations recorded zero late batches. These are within-block audit facts,
not full-campaign results or evidence of a particular performance benefit.

Five unit tests passed. Independent arithmetic fixtures retain unequal reader
rates and nonzero lateness, check known total throughput and fairness, and
accept a control envelope longer than the nominal recording interval.
Mutations of reader identity, CPU, counts, timestamps, protocol, finite values
and normalized values are rejected; a missing reader or normalized row is
also rejected. The fixtures are synthetic verification inputs, not experimental
measurements. ABI/PFN verification and the remaining physical blocks are
outside this check. No collector, foundational code or service was changed.

## ABI and PFN record validation — 2026-09-11

`audit_support_records.py` passed on physical steps 000–003. Each of the six
method/role ABI logs contains the expected 51 pass records and 49 fast/fallback
path records; `namespace.fast_paths` occurs twice for its two lifecycle paths.
The raw ABI executable identifies itself as `raw-vdso`, whereas the performance
CSV uses `raw`; the auditor preserves this distinction. Its initial name
mismatch was a postprocessing issue, not a failed experiment.

In both the READ and UPDATE VKSO boots, the saved PFNs reconstruct three unique
source/user pages for VKSO and five for compact-split. All three VKSO pages
match their kernel backing; compact-split shares the state page and has two
distinct copied text pages. The two methods have the same source PFNs within
each boot. Saved readable loader mappings are RX for text and R-- for state.
These observations apply to the declared closure and normal loader mappings.

Six tests passed, covering ABI case omission/duplication/failure, path-status
changes, backend names, actual thread scope, wrong PFNs/counts, writable text,
executable state, wrong carrier identity, and differing same-boot sources.
Synthetic PFN fixtures also exercise overlapping PROT_NONE reservations.
The auditor was not added to the automatic follow-up service.

The current ABI logs report `semantics.multicpu_threads=pass threads=1`:
`collect.py` pins control work to CPU 0 before launching the ABI executable,
and `check_multicpu_threads()` creates one thread per allowed CPU. This is
single-CPU evidence for that check. Historical four-CPU evidence remains in
`baremetal/results/20260801T164548Z-vkso-final/`, under `raw-normal`,
`vkso-normal`, `raw-no-retpoline` and `vkso-no-retpoline`: each completed case's
`functional.matrix` records `threads=4` and has no fail/skip records. Its
`environment.txt` identifies the corresponding Raw/VKSO 5.15.198 image.
Those historical runs do not include compact-split; their coverage is retained
under their original build identity. No new multi-CPU test was launched.
