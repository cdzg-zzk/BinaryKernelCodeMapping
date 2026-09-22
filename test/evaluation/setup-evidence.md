# Three-algorithm setup collection evidence

The current [setup observers and protocol](setup/README.md) pass on all three
complete algorithm deployments. Each independent exact119 guest runs the
actual `vkso exec` build/registration command, the original functional workload,
and a second registration using `vkso exec-ready`. Each registration executes
six independent task processes, for six registrations and 36 processes across
the three guests. These are collection-validation sessions, not independent
physical-host performance repetitions.

| Algorithm | Boot | Raw result and reconstruction |
| --- | --- | --- |
| BCH | `197e5d7e-b270-4458-a1e3-bb64701a499f` | [Run](results/bch-setup-qemu-20260912-attempt01/result.json), [setup audit](results/bch-setup-qemu-20260912-attempt01/setup-audit.json) |
| XZ | `ead7c2fa-393f-48f7-b1e9-34e555c67caa` | [Run](results/xz-setup-qemu-20260912-attempt01/result.json), [setup audit](results/xz-setup-qemu-20260912-attempt01/setup-audit.json) |
| LZ4 | `01f22111-22e4-4d93-b284-185392ba0b04` | [Run](results/lz4-setup-qemu-20260912-attempt01/result.json), [setup audit](results/lz4-setup-qemu-20260912-attempt01/setup-audit.json), [complete helper/component/CLI audit](results/lz4-setup-qemu-20260912-attempt01/independent-audit.json) |

## What is measured

The owner, page-registration and observer modules are loaded before the timed
`vkso exec` command. Their actual load commands have separate external
intervals in `commands.jsonl`. Thus command-to-first-valid means the recorded
VKSO command with those modules resident, not the algorithm runner's entire
build/insmod lifetime. The latter remains part of formal setup integration.
Archived observer sources and the included original benchmark sources are
byte-compared with the current inputs in `setup-payload-identity.json`.

The shell records KRG, checker, header, carrier, installation, manager READY,
application and cleanup boundaries with an optional external clock helper.
The actual application process records dlopen, symbol resolution, load,
first valid complete task and unload in an in-memory event buffer. The
controller's timestamps cover process startup and return. All clocks are
CLOCK_MONOTONIC_RAW in the same boot; original raw events and argv remain
available under `evidence/validation/setup-full/` and `setup-ready/`.

The first VKSO process runs before the PFN observer or original algorithm
benchmark. Its first-valid timestamp can therefore be related to the current
full deployment's external start without a preceding algorithm warm-up by the
collector. Build and registration already touch their own inputs and pages;
this is not an empty-cache condition. `exec-ready` avoids rebuilding the
carrier while retaining manager identity and page-plan validation. It uses
the same notification and cleanup functions as `exec`.

LZ4 processes each complete all 12 Silesia files (211,938,580 bytes) with
64 KiB blocks and compare the full decoded output. XZ processes decode the
three full original files (9,534,144 bytes) with full input/output and guard
checks. BCH uses both original m=13, t=4/8 geometries, initializes/encodes
512-byte payloads, and uses the full decode path for each 0..t error count,
checking error locations and corrected codewords. These latency tasks use
one or three complete iterations. The complete algorithms are unchanged;
BCH's original 128-vector functional matrix runs separately in the same guest.

The outer full-export command also runs the original functional suite after
the setup task processes. Its total elapsed time is consequently not the
lifetime of one short application. The setup-to-first-valid interval ends at
the first process's complete validated result; per-process totals and the
second registration's release timing are recorded separately.

## Verification and interpretation

The independent reconstruction checks all 12 raw process logs per algorithm,
process IDs, exact task counts, first-valid ordering, both shell traces and
outer command bounds. It replays the two actual kernel transactions and
requires successful COMMIT and RELEASE, five LZ4 or four BCH/XZ bindings,
and zero bindings after release. It retains nested kernel prepare/apply/
release fields without double-counting their cumulative appearances.

The existing independent observer verifies all declared PFNs during the first
registration; fresh mappings are checked after both releases. The second
session's active PFNs are not separately sampled. Every test module unloads
and every guest finishes without kernel panic, BUG or WARNING. LZ4 additionally
retains 432 cross-backend decode checks, 18 component processes/36 rows and
192 complete four-backend CLI operations. BCH and XZ retain their original
10,752 decode checks and 882 complete decodes, respectively.

The shell clock helper starts an external process per marker. Its cost is
included in the observed shell intervals. A separate 30-launch host diagnostic
is archived as `host-setup-clock-calibration.json` and `.tsv`; it is not a
correction for these guest measurements. C process timestamps are buffered,
but clock reads still contribute overhead. Raw guest durations are retained
for collector diagnosis and do not replace the paper's physical-host results.
A missing or backwards timestamp is rejected; the negative parser check is
archived with the BCH run. Six existing shell cleanup tests also pass with
the optional observer disabled.

## Remaining group B delivery

The collection path and its result reconstruction now exist for all three
real closures. Formal repetitions still require a matched ordinary-DSO
command-to-result path, same-environment observer calibration and
uninstrumented external totals, defined cache/ordering conditions and recorded
CPU placement. Complete resource accounting, the 1/2/4/8/16/32-page scan,
unfiltered first-touch and pressure work remain open. No break-even point or
net performance gain is inferred from these guest sessions.
