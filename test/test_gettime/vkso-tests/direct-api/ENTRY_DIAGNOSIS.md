# Public-entry regression diagnosis, 2026-09-23

## Evidence and limits

Compare campaigns `20260922T185408Z-direct-api` (original public wrapper) and
`20260923T050745Z-direct-api` (entry-opt2). Both have four independent boots/case.
All costs below are TSC ticks/call, not unhalted core cycles. Existing data and
packages were not modified. No new formal timing or module loading was performed.

gettimeofday: normal VKSO 59.205605 -> 60.209196 (about +1.004 ticks, +1.70%);
no-retpoline also increases by about 1.004 ticks. Raw remains about 56.204.
Both campaigns pass the fast-path time-syscall denial check. Kernels, carrier,
page mappings and benchmark executables are identical across these revisions.
The regression is reproducible across the four boot medians; it is not evidence
of a newly introduced syscall fallback or a changed time computation.

The original public entry uses a direct CALL into a PLT indirect JMP; opt2 uses
an indirect CALL through the eager GOT. Its address also moves 0x12e0 -> 0x1230.
Both still push/pop r12 and move eax -> r12d -> eax on the successful path to
accommodate a possible errno helper call. Fewer branches do not guarantee less
latency: indirect-call prediction and instruction placement both changed.
Existing samples cannot isolate their individual contributions; PMU/controlled
layout ablations have NOT_RUN status. Do not assert a particular predictor or
cache mechanism as the proven cause, or subtract a fixed 1 tick correction.

## Candidate entry-opt4

Retain the validated time IFUNC and opt2 GOT calls. Outline negative-return errno
conversion into one cold noinline helper. All four integer-return public APIs
preserve successful raw return values without saving r12 or moving the return
value twice. The stack remains ABI-aligned; error paths still set thread-local
errno and return -1. gettimeofday still ignores obsolete timezone, and getcpu
still supplies its third private argument as NULL. No new global/TLS context,
lookup, provider dispatch, or duplicated time computation is introduced.

ELF size text: original 3282, opt2 3106, opt4 3154 bytes. opt4 is +48 bytes over
opt2, -128 versus original. data=696, bss=16 unchanged. PT_LOAD page coverage and
permissions identical. This does not prove runtime RSS equality or time savings.
Both variants preserve kernel images, carrier, page mappings and both benchmark
executables byte-for-byte relative to opt2.

40 direct tests: 37 PASS, 3 environmental SKIP on VKSO (native vDSO unavailable).
11 maintenance tests PASS. Actual bench-only builds and paired package verifier
PASS. Real-carrier candidate functional/performance/RSS validation: NOT_RUN.
No old performance sample represents this candidate.

## Other interfaces and subsystems

- time: opt2 already removes the public forwarding entry; preserve it. Negative
  timestamps, unchanged errno, pointer writes and actual function binding are tested.
- getcpu: preserve opt2's measured ~1.003 tick reduction; cold helper is a new
  candidate and may still have placement-sensitive effects. Do not bypass error ABI.
- hres clock_gettime: after opt2 most normal differences are roughly -1 to +1.3
  ticks. Clock classification/MM-context and namespace offset selection are possible
  future targets; do not clone one core per clock or omit namespace support.
- coarse: normal user difference is ~2.01 ticks. In the latest kernel-reader data,
  Raw monotonic_coarse is 9.031, VKSO 11.038 (~+2.007), also present in the prior
  campaign. This is not exclusively a public-wrapper issue. no-retpoline kernel
  values instead are Raw 11.039, VKSO 9.032, so mitigation/code-layout sensitivity
  needs examination before attributing a fixed cost to physical sharing.
- gettimeofday core: already uses a 32-bit reciprocal microsecond conversion.
  Replacing that with generic division is not a justified optimization. Its
  normalization, seq validation and provider fallback must remain correct.
- getres: realtime already wins ~1.047 ticks; preserve NULL-output semantics and
  native/invalid-clock fallback while evaluating the smaller public wrapper.
- fallback: dominated by syscalls. Cold outlining may trade cold-path instructions
  for hot-path savings; report both, not only successful fast calls.
- publisher/update/concurrent: NOT_RUN in these two READ campaigns. No conclusion
  about new writer gains or losses follows from wrapper-only changes.

## Reproduce the next candidate

The packages already exist; no kernel build/install is required. From baremetal:

```bash
export NORMAL_PACKAGE="$PWD/artifacts/direct-normal-entry-opt4"
export NO_RETPOLINE_PACKAGE="$PWD/artifacts/direct-no-retpoline-entry-opt4"
./verify-packages.sh "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"
./experiment.sh begin
./experiment.sh boot
# after reboot, return to baremetal
./experiment.sh collect
./experiment.sh status
# repeat boot/reboot/collect until complete, then:
./experiment.sh aggregate
```

Four formal cases remain unchanged. Start a new campaign; do not refresh an old
campaign to adopt changed public-library machine code. The opt3 staging builds
failed before publication due to stale parent-provenance hashes on a repeated
selective rebuild. Rebuild now binds the four updated provenance sidecars to their
final contents; opt4 exercises this real second-generation package path. Failed
staging directories remain preserved, and are not installable candidate packages.
