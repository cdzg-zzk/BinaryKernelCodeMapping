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
