# Complete-task LZ4 setup comparison

This experiment measures the cost of obtaining a complete result through an
ordinary same-source DSO or VKSO, with registration either already active or
included in the command. It supplies the setup comparison missing from the
algorithm/application campaign. It does not alter the registration protocol.

## Physical-host results

All three LZ4 deployments completed on 2026-09-12, with 24 measured active and
24 measured ready-carrier commands per deployment. All 144 measured commands,
their raw internal/shell timestamps, clock calibrations and registration
records passed independent reconstruction. The same-boot deployment summaries
are in [the final tables](results/application-setup/paper-tables/tables.md),
with [commands and archive selection](kernel-cost-host.md) retained separately.

The untraced ready-carrier cost ratios are 1.717 [1.715, 1.721] for one complete
corpus pass and 1.287 [1.285, 1.287] for three. Active registration is measured
separately. Paper Tables 29–30 report full command and offline export costs;
Appendix B reports instrumented first-valid-result and nested stages. Owner
compilation/loading are outside these setup windows. No calibration constant
is subtracted, and guest timing fields are not combined with host records.

## Guest verification before formal collection

The [complete archive](results/lz4-setup-comparison-qemu-20260912-attempt01/result.json)
finished normally on Linux 5.15.0-119 in a private KVM guest, boot
`3ded0876-2ccb-4fac-bacf-d62684e49111`. The full adapted LZ4 owner, actual
exporter/manager and ordinary libc-helper baseline ran with all 12 Silesia
inputs, totaling 211,938,580 bytes. The setup task compresses and decompresses
64 KiB blocks and compares every decoded byte. One and three corpus passes
share the same process buffers.

| Scope | Measured commands | Warmups | Additional registration sessions |
| --- | ---: | ---: | ---: |
| New process, registration active | 24 | 2 | 0 |
| Complete ready-carrier command | 24 | 2 | 13 |

Each matrix contains both backends, both pass counts and trace off/on builds
in three deterministically rotated rounds. Trace-off excludes setup event
collection; trace-on retains all observer overhead. The latter also records
30 clock-helper launches in the ready phase. The observers use external and
internal CLOCK_MONOTONIC_RAW timestamps from the same boot. No calibration
constant is subtracted from a measured command.

Independent audits reconstructed [active](results/lz4-setup-comparison-qemu-20260912-attempt01/evidence/validation/setup-comparison-active/independent-audit.json)
and [ready](results/lz4-setup-comparison-qemu-20260912-attempt01/evidence/validation/setup-comparison-ready/independent-audit.json)
matrices from raw logs. All 13 additional registrations have successful
BEGIN/STAGE/COMMIT/RELEASE/FORGET records, five applied pages and zero pages
remaining after release. The [original setup audit](results/lz4-setup-comparison-qemu-20260912-attempt01/setup-audit.json)
also passed after accounting for these exact sessions, covering both original
full-export and ready-carrier observations. The [independent application audit](results/lz4-setup-comparison-qemu-20260912-attempt01/independent-audit.json)
reconstructed 432 cross-backend decode checks, 36 component rows, 192 complete
application rows and five shared PFNs. The guest restored mappings and unloaded
its test modules normally.

## Measurement scope and historical preparation

These are complete collection-path checks in a guest; their timing values do
not enter the paper's physical-host performance tables. The matched command
comparison starts with a constructed carrier. It measures registration,
process loading, complete computation and release; it does not charge offline
analysis/build to every process. The original full-export trace separately
records construction stages. The full CLI supplies the application workflow
comparison, including its framing and output-file behavior.

The completed formal campaign enabled `--with-lz4-setup`, `--with-lz4-workflow`
and `--with-kernel-cost` together, preserving three complete owner deployments
per algorithm. Analysis must report deployment summaries, separate traced and
untraced values, and distinguish ready-carrier cost from offline export cost.
No extra algorithms, failure matrices or unchanged guest reruns are required.

The host precondition check on 2026-09-12 found exact119, an inactive Clocktime
service and a failed (not running) follow-up service. Outside the sandbox,
`sudo -n true` reported that a password was required. No host module was loaded
and no formal campaign was started. A normal privileged researcher session is
the execution prerequisite, not an unresolved algorithm failure. The researcher
subsequently supplied explicit privileged authorization; the physical-host
campaign above then completed without another unchanged guest repetition.

The formal LZ4 runner also enables the existing shell stage observer around
its initial `vkso exec`. `audit_export` separately extracts construction and
registration intervals and was checked against this archive's full-export
trace. Owner compilation/loading are outside that trace; its application
interval contains the complete campaign and is not reported as setup latency.
