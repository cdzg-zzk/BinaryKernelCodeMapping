# UPDATE / concurrent workflow audit — 2026-09-23

Status: historical pre-migration audit. The migrated implementation and commands
are now in [RUN_STATEFUL.md](../update-bench/RUN_STATEFUL.md). Target execution
remains NOT_RUN; the findings below describe the old workflow, not the new one.
No instrumented kernel was built, installed, booted or sampled in this audit.
The existing historical experiments/results are preserved. This is an engineering
migration record, not a claim that the old data were invalid for their original scope.

## Accepted implementation checkpoint

`e39f231` records opt4, public namespace/error diagnostics and kernel reader analysis.
Direct tests: 38 PASS, 3 environmental SKIP; maintenance: 11 PASS.
Normal target supplementary execution was completed by the user and validated.
no-retpoline supplementary execution remains NOT_RUN. READ artifacts/results are
local ignored data, retained unchanged, and are not uploaded by these commits.

## Findings and required migration

| Priority | Source | Current behavior | Required before opt4 collection |
|---|---|---|---|
| Blocking | baremetal/vkso_time_bench.c:408–452, 1141–1195; update-bench/collect-update.sh:400 | Raw resolves __vdso symbols; VKSO resolves __vkso symbols; load runs function-pointer calls into these entries. The function named public_clock_gettime does not call libc/opt4. | Link Raw to libc and VKSO to the sealed opt4 public library. Bind/init outside timing. Do not describe current load as opt4. |
| Blocking | update-bench/experiment-update.sh CASES/load_state; update-experiment.conf | Four cases, one boot each; 15 loops inside a boot. No boot_id in collected metadata. | Multiple balanced blocks with boot identity/deduplication; summarize within boot before across boots. Preserve four implementation cases. |
| Blocking | update-bench/collect-update.sh:293–349 | replaced flag set only AFTER successful replace; partial failed replace can bypass restore. cleanup attempts module unload even if restore fails; EXIT/INT/TERM trap discards errors. | Mark replacement attempted before invocation; restore after partial failure; retain backing module if restore fails; fail result on cleanup error; terminate correctly on signals. |
| Blocking | update-bench/collect-update.sh:223–241 | Only completed results are refused; incomplete directories reused and files truncated. | New partial directory per attempt; preserve failed attempt separately; atomic publication only after all checks/cleanup. |
| Blocking | update-bench/collect-update.sh:set_sysfs_value | Changes governor/pstate without saving/restoring prior values; missing settings silently skipped. | Reuse controlled tuning/restore semantics from READ, including avoiding writes of unchanged no_turbo. Verify required controls and capture before/after evidence. |
| Blocking | update-bench/experiment-update.sh:145; verify-update-packages.sh:117 | Ties collection to repository HEAD/dirty patch and cross-variant build timestamp, rather than frozen independent tool revision. | Separate tools from immutable kernel/carrier/benchmark identities; adopt explicit tool snapshots; retain strict artifact/config/source validation. |
| Reporting | update-bench/compare-update.py:parse_writer and report generation | Saves raw and overhead-corrected metrics but selects mean_corrected_cycles as headline; subtracts minimum TSC-pair calibration with clipping at zero. | Primary result must retain raw ticks, with calibrated correction explicitly secondary and separately labeled. Neither is core cycles without supporting evidence. |
| Reporting | compare-update.py:parse_writer | Selects action=0 periodic updates; records other_actions but does not aggregate per CPU or boot. | Report exact action scope, writer CPU distribution, dropped/invalid samples and within-boot statistics; do not generalize to all clock adjustments or locking cost. |

The READ package builder intentionally rejects UPDATE_BENCH=1, while its selective
rebuild entry hardcodes UPDATE_BENCH=0 for VKSO rebuilds. Do not bypass this validation
to force instrumented images into a READ package. Define an explicit instrumented
package scope and bind its public library/source identity, retaining the clean READ
packages unchanged.

## Timing boundaries that can be retained

`kernel/time/timekeeping.c:timekeeping_update` timestamps immediately inside function
entry and before return, while the caller already holds timekeeper_lock. It includes
state conversion/publication, fast timekeeper updates and optional mirroring, not lock
acquisition/wait or the entire timer interrupt. `timekeeping_update_bench_finish`
takes the end timestamp before appending the record. Recording still perturbs the
system/cache after the timed region; retain that limitation in concurrent analysis.
Both sides use the same recorder/header (prepare-raw-source.sh copies and checks them).
The TSC ordering uses the kernel's rdtsc_ordered and must be audited in the actual
built x86 alternative before making stronger claims about complete store visibility.

The recorder holds 65,536 entries of 16 bytes: 1,048,576 bytes of sample storage, plus
metadata/allocation costs. This is test instrumentation, not VKSO production memory.
It records actions/CPU, rejects sample overflow in analysis, and keeps calibration.

The old load loop already keeps duration-control syscalls outside the reader batch,
warms the same path after each control syscall and checks TSC_AUX. Retain these useful
properties when replacing provider calls. Writer recording currently starts before
reader process setup/initial validation and ends after process teardown; it therefore
includes transitional intervals. Add an explicit ready/start/stop handshake if the
new claim is writer cost under steady concurrent readers. Keep startup/transition
measurements separate rather than silently including them in steady state.

## Build dependencies and scope

- Existing READ images have TIMEKEEPING_UPDATE_BENCH disabled. They cannot yield the
  requested writer samples; a first instrumented experiment needs matching Raw/VKSO
  images for both mitigation variants (four images), plus dependent modules/carrier.
- Future tool-only fixes must not trigger those kernel builds. Public reader edits
  should rebuild user artifacts; kernel/recorder changes should rebuild only affected
  kernels and dependent artifacts while preserving the other verified components.
- build-update-images.sh already selects BUILD_VARIANT and delegates to build-images.sh.
  Its RAW_PACKAGE hook can reuse an instrumented Raw image, but currently checks only
  some required files/config at entry. A future selective UPDATE path must validate
  the complete parent inventory before reuse; it must not accept a non-instrumented
  READ baseline or silently fabricate provenance.
- prepare-raw-source.sh patches its supplied source in place. Use a dedicated extracted
  source directory, never the clean Raw source used to establish READ identity.
- UPDATE and CONCURRENT may share the same verified instrumented packages. Their
  observed kernel source/config identities must be reconciled to READ while explicitly
  listing instrumentation differences. A wrapper-only opt4 change cannot be credited
  with improving a kernel writer implementation that did not change.

## Implementation order after this audit

1. Reuse the existing fixed entrypoints; repair transactional collection/cleanup,
   snapshots and boot-block accounting with mocked failure-path tests.
2. Add direct-linked sustained reader with explicit steady-window coordination and
   Raw/VKSO functional checks before timed sampling. Seq protocol remains a separate
   diagnostic, not an extra formal backend.
3. Define instrumented package identity and scoped rebuild support; test validation
   and non-kernel build paths before requesting costly kernel construction.
4. Validate aggregation on synthetic missing/corrupt/mixed-boot data; retain raw
   writer samples and boot-level summaries, including failures and control metadata.
5. Only then publish executable build/install/boot/collect commands. The old commands
   in STATEFUL.md are historical references, not a ready opt4 protocol.

Audit validation: bash -n over all update-bench shell scripts and Python AST parsing
of compare-update.py PASS. These are syntax checks, not target runtime validation.
