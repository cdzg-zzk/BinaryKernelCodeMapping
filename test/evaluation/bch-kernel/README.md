# BCH kernel API control driver

This separate GPL test module imports all four public APIs from three providers:

| CSV backend | API symbols | Role |
|---|---|---|
| `stock-kernel` | `bch_init/free/encode/decode` | Installed kernel distribution implementation |
| `matched-source-kernel` | `matched_bch_init/free/encode/decode` | Complete vendor Linux BCH source built under the separately recorded owner algorithm flags |
| `owner-kernel` | `vkso_bch_init/free/encode/decode` | Actual unchanged export owner used by VKSO |

The module contains workload and observation code, not a BCH implementation. Its
ordinary imports create module dependencies on the providers. These dependencies
belong to the test driver and do not establish owner pinning by the registration
mechanism. Each backend has its own mutable control structure, and owner helpers
retain their original kernel bindings. Dmesg prints the twelve imported API
symbol names and actual pointers for correlation inside the private guest.

Build against the same kernel headers and both separately built provider symbol
tables. This command compiles only and does not load modules:

```sh
make -C test/evaluation/bch-kernel \
  KDIR=/lib/modules/5.15.0-119-generic/build \
  OWNER_SYMVERS=/absolute/path/to/original-owner/Module.symvers \
  MATCHED_SYMVERS=/absolute/path/to/bch_matched/Module.symvers
```

The containing private-guest harness loads providers and mounts debugfs. It may
then load `bch_kernel_bench.ko` with the insmod process restricted to exactly one
CPU. The driver checks that effective affinity contains one CPU, records it, and
checks the affinity and actual CPU around each timed batch. It does not change
affinity or explicitly disable interrupts or preemption. Initialization allocates
with `GFP_KERNEL` and may sleep.

## Workload and defaults

`measure=0 correctness_vectors=128` performs complete functional validation. The
128-vector value is required; there is no reduced correctness mode. Each of
m=13/t=4 and m=13/t=8 uses a seeded 512-byte payload and its full ECC, all error
counts 0..t, 128 error-position trials per count, and both full/precomputed decode
interfaces on all three backends. Data seeds and the original benchmark's error
PRNG, bit reversal, duplicate rejection and correctness seed are retained.

Control geometry and reference parity must agree. Each trial also compares the
precomputed ECC differences between stock and each other backend. Every decode
must return exactly the expected unordered location set; the harness flips those
locations and compares the entire data+ECC codeword, then restores the corrupted
input. The output array is reset before each correctness call. A passing default
run has these observed counters:

- `decode_checks=10752`: 128 × (5+9) × 3 backends × 2 modes.
- `geometry_checks=6`: two parameter cases for each backend.
- `parity_checks=3588`: four reference-parity comparisons and 3,584 per-vector
  ECC-difference comparisons against stock.
- `unique_input_vectors=1792`, `vector_rows=10752`, `result_rows=0`.

All BCH control objects, work buffers and ECC buffers are freed before successful
module initialization returns. Only immutable observations remain for debugfs.
Failure releases partial allocations and debugfs entries and returns a negative
errno. Dmesg always receives a terminal `BCH_KERNEL_BENCH status=pass|fail` marker
with actual counters. Invalid parameters/affinity return `-EINVAL`, observed CPU
changes return `-EXDEV`, allocation/init failures return `-ENOMEM`, geometry or
coverage failures return `-EPROTO`, and decode/parity mismatches return `-EBADMSG`.

## Optional measurement interface

`measure=1 outer_runs=11 sample_ms=10 correctness_vectors=128` first completes
the same full correctness path, then calibrates and records all 1,056 rows:
11 × 3 backends × ((2+2×5) + (2+2×9)). Each parameter case includes init+free,
encode and both decode interfaces for every error count. Iteration counts are
calibrated for each backend/case/mode/error and then reused across outer rounds.
Init includes the corresponding free call. The reference payload is fixed per
parameter case; timed decode does not repair the working codeword.

The measured interval uses `ktime_get_ns`, so CSV `ns` is elapsed wall time,
including possible interrupt/preemption effects. It is not the userspace
benchmark's `CLOCK_PROCESS_CPUTIME_ID` estimator. The driver retains ordinary
kernel compilation/instrumentation, and all three providers use the same harness
dispatch. Scheduler yields occur between batches, not explicitly inside timed
loops. Setup, error injection, precomputed ECC/XOR and warmup precede each recorded
interval; initialization/free is intentionally timed in the init mode.

Both decode modes and all three backends use one shared error vector per
round/case/error. This deliberately removes the original userspace benchmark's
mode-dependent seed. Backend order rotates as
`(position + round + case_index + operation + errors) % 3`, where operation is
init=0, encode=1, precomputed=2, full=3. The standalone userspace author backend is
not part of this kernel control. Stock and matched-source answer different
comparison questions; stock is not asserted to share the owner's source and
compiler conditions. Private-guest `measure=1` validates collector coverage, not
formal paper performance.

A complete measurement run has `result_rows=1056`, `unique_input_vectors=1960`
and `vector_rows=10920`: the 1,792 correctness inputs plus 14 calibration inputs
and 154 measurement inputs. Correctness counters remain 10,752, not an inferred
count of timed operations.

## Saved interface

Successful runs expose read-only debugfs files under
`/sys/kernel/debug/bch_kernel_bench/`. The default run's `results` contains only
its header. `status` includes the terminal state, parameters, total and
per-case/backend/mode correctness counters, geometry, row counts, affinity CPU
and `timebase=ktime_get_ns_wall`.

`results` columns:

```text
round,backend,m,t,len,errors,mode,iterations,ns,timebase,cpu_start,cpu_end,seed,vector_id,errno
```

`ns/iterations` may be computed downstream. Every row identifies the actual
start/end CPU and any error. Init uses `errors=-1`; init and encode have seed=0
and vector_id=-1. No timing row is a correctness trace.

`vectors` columns:

```text
vector_id,phase,round,backend,m,t,len,errors,mode,seed,positions,found,returned_positions,locations_equal,restored_codeword_equal,ecc_equal
```

Positions are decimal integers separated by colons; a zero-error position list
is empty. Correctness phase has one row per backend/mode, six rows sharing each
vector ID. It preserves the actual returned locations and restoration/equality
checks. For calibration and measurement, each unique input appears once with
backend=`all`, mode=`both` and the five outcome fields empty; these rows describe
input vectors only. Calibration uses round=-1, while correctness uses round as
trial index 0..127. The standalone collector/auditor must verify the complete
matrix and actual records rather than accepting the terminal marker alone.
