# Pseudo-GOT Microbenchmarks

One reference machine used during development:

```text
Linux intelnuczzk 5.15.0-119-generic #129-Ubuntu SMP Fri Aug 2 19:25:20 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux
```

This package implements the pseudo-GOT performance methodology:

1. Layer 1 measures the primitive cost bounds of pgot-data and pgot-func.
2. Layer 2 measures how visible func-pgot overhead changes when the same
   workload is placed before the call, inside the target, or after the call.
3. Layer 3 measures copied kernel-function closures with origin and PGOT
   variants.

The code is intentionally synthetic and controlled. The goal is not to mimic a complete kernel function, but to isolate variables that explain the later real-function benchmarks.

## Portability

The benchmarks are intended to run on another Linux x86-64 machine, but the
absolute cycle numbers are machine-dependent. When moving to a new machine,
rebuild from source and record the new environment metadata.

Required for the main cycle benchmarks:

1. Linux on x86-64 with `rdtscp` support.
2. `make`, `gcc`, `bash`, and `python3`.
3. GCC support for the retpoline flags used by the retpoline builds:
   `-mindirect-branch=thunk-inline`, `-mindirect-branch-register`, and
   `-fcf-protection=none`.

Optional:

1. `perf` is only needed when `RUN_PERF=1`.
2. `sudo` or relaxed `kernel.perf_event_paranoid` may be needed for hardware
   counters.
3. CPU isolation, fixed governor, and turbo control are not required to execute
   the code, but they are recommended for paper-quality measurements.

Quick check on a new machine:

```bash
cd pgot_benchmarks
make clean
make
./run_experiment.sh list
CPU=0 ITERATIONS=1000 REPEATS=3 OUTER_RUNS=1 ./run_experiment.sh layer1-data-independent
```

If the CPU number is not known, omit `CPU=...`; the run will be unpinned and
the output metadata will record that.

## Directory Layout

```text
pgot_benchmarks/
  common/
    bench_common.h          common timing, median, CPU pinning
    data_tables.h           direct data slots and pseudo-GOT data slots
    targets.h               target functions and pseudo-GOT function slots
    common.mk               shared compiler flags
  layer1/
    01_data_independent/    pgot-data kernel-module throughput-style loads
    02_data_dependent/      pgot-data kernel-module pointer-chasing loads
    03_func_stable/         fixed-target pgot-func kernel-module builds
    04_func_entropy/        high-entropy target trace, ret/no-ret builds
  layer2/
    01_func_placement/      pgot-func unfenced placement/workload LKM
  layer3/
    01_sha256_transform/    SHA-256 transform copied closure LKM
    02_bch_encode/          BCH encode copied closure LKM
    03_zlib_deflate/        zlib deflate copied closure LKM
    04_zstd_decompress/     zstd decompress copied closure LKM
    05_crc32_le/            CRC32_LE copied closure LKM
    06_lz4_compress_fast/   LZ4_compress_fast copied closure LKM
    07_aes_encrypt/         aes_encrypt copied closure LKM
    08_lz4_decompress_safe/ LZ4_decompress_safe copied closure LKM
    09_hex_dump_to_buffer/  hex_dump_to_buffer copied closure LKM
    10_string_escape_mem/   string_escape_mem copied closure LKM
  run_experiment.sh         select and run one experiment group
  run_all.sh                wrapper for ./run_experiment.sh all
  collect_env.sh            environment snapshot helper
  scripts/
    process_layer1_data_independent.py
                            data processing only
  results/
    layer1/<experiment>/    Layer 1 outputs grouped by experiment
    layer2/<experiment>/    Layer 2 outputs grouped by experiment
    layer3/<experiment>/    Layer 3 outputs grouped by experiment
```

## Build And Run

```bash
cd pgot_benchmarks
make
SUDO_PASSWORD='...' ITERATIONS=1000000 REPEATS=31 CPU=2 ./run_experiment.sh layer2-func-placement
```

List available experiments with:

```bash
./run_experiment.sh list
```

Run everything with:

```bash
CPU=2 ITERATIONS=1000000 REPEATS=31 ./run_all.sh
```

Results are grouped by experiment. For example:

```text
results/layer2/01_func_placement/
  metadata.txt
  raw.csv
  processed.csv
  paper_table.csv
  summary.md
  static/
    nm_no_retpoline.txt
    nm_retpoline.txt
    objdump_no_retpoline.txt
    objdump_retpoline.txt

results/layer1/01_data_independent/
  metadata.txt
  raw.csv
  processed.csv
  paper_table.csv
  SUMMARY.md
```

Layer 2 pgot-func validation includes objdump output, symbol-size evidence,
and stability summaries under the same experiment directory.

Layer 3 uses copied-closure experiments:

1. `01_sha256_transform` copies a SHA-256 transform closure and reports
   `all_pgot`. For this function, all applicable PGOT is data-PGOT only,
   because the transform has no honest closure-external helper call to convert
   into func-PGOT.
2. `02_bch_encode` copies the BCH encode closure and reports `all_pgot`.
   Internal BCH helpers remain direct; the func-PGOT part covers
   closure-external `memcpy`.
3. `03_zlib_deflate` copies the zlib deflate closure from `deflate.c` and
   `deftree.c`. Data-PGOT covers configuration and tree tables; func-PGOT
   covers closure-external `memcpy` and `memset`.
4. `04_zstd_decompress` copies the zstd decompression closure from
   `decompress.c`, `huf_decompress.c`, `fse_decompress.c`,
   `entropy_common.c`, and `zstd_common.c`. Data-PGOT covers default
   decompression tables used by the benchmarked path; func-PGOT covers
   closure-external `memcpy`, `memset`, and `memmove`.
5. `05_crc32_le` copies the CRC32 little-endian table-driven computation into
   the LKM. The applicable all-PGOT transform is data-PGOT: the CRC table base
   is loaded from `pgot_crc32table_le[0]`.
6. `06_lz4_compress_fast` copies the `LZ4_compress_fast` implementation
   closure into the LKM. Data-PGOT covers actual static data references such as
   `LZ4_minLength` and `LZ4_64Klimit`; func-PGOT covers real `memcpy`,
   `memset`, and `memmove` callsites left in the copied closure.
7. `07_aes_encrypt` copies the generic AES closure. Data-PGOT covers the AES
   S-box tables reached by `aes_encrypt` and key setup; func-PGOT is a no-op
   for the timed encrypt path because there is no internal mem* callsite.
8. `08_lz4_decompress_safe` copies the LZ4 safe decompressor closure.
   Data-PGOT covers the decode helper tables `inc32table` and `dec64table`;
   func-PGOT covers closure-internal `LZ4_memcpy`, `LZ4_memmove`, and raw
   `memmove` callsites.
9. `09_hex_dump_to_buffer` copies the one-line hex dump formatter. Data-PGOT
   covers the `hex_asc` table used by `hex_asc_hi/lo`; func-PGOT is a no-op
   for the measured path because there is no internal mem* callsite.
10. `10_string_escape_mem` copies the string escaping closure. Data-PGOT
    covers the `hex_asc` table used by `escape_hex`; func-PGOT is a no-op
    because the closure has no `memcpy`, `memset`, or `memmove` callsite.

For Layer 3, the benchmark modules validate correctness before timing:
origin and PGOT variants run on the same input, and the module compares return
code, output length, and output bytes. Static validation artifacts are stored
beside each result under `results/layer3/<experiment>/static/`.

If CPU isolation is already configured on the machine, pass the isolated CPU through `CPU=...`. Otherwise omit it. The output CSV records the requested CPU, kernel command line, isolated CPU mask, governor, turbo/boost state, SMT state, Spectre v2 mitigation, CPU model, topology, and compiler.

For paper-quality runs, record and report the same settings in the paper:

```bash
cd pgot_benchmarks
SUDO_PASSWORD='...' CPU=2 ITERATIONS=1000000 REPEATS=31 ./run_experiment.sh layer2-func-placement
```

Recommended run conditions:

1. Pin to one CPU with `CPU=...`.
2. Prefer an isolated CPU, and report the `isolcpus`, `nohz_full`, and `rcu_nocbs` kernel settings if used.
3. Use a fixed frequency policy, preferably the `performance` governor.
4. Report whether turbo/boost is enabled or disabled.
5. Report the repeat count and IQR columns, not only the median.

Optional hardware-event collection is not part of the current Layer 2 LKM
entry point. Use the generated `static/objdump_*.txt` and `static/nm_*.txt`
files as the default code-generation validation evidence.

## Timing Method

The benchmark programs use:

```text
lfence; rdtscp
tested loop
rdtscp; lfence
```

Each case performs a warmup, then repeats the timed region multiple times and reports the median. This avoids relying on a single noisy run. The result fields include the iteration count and repeat count so that all measurements are reproducible.

The pseudo-GOT slot accesses use `volatile` loads in the benchmark code. This is intentional: otherwise the compiler can hoist a fixed pseudo-GOT slot out of a loop and accidentally remove the pgot event being measured.

## Layer 1: Primitive Cost Bounds

Layer 1 asks:

> What are the basic lower and upper cost bounds of pgot-data and pgot-func?

It does not try to model complete kernel functions.

### 01_data_independent

Measures direct data access versus pgot-data access when loads are independent.

Variables:

| Variable | Values |
|---|---|
| events per iteration | `1, 2, 4, 8, 16` |
| variant | `direct`, `pgot` |

Important interpretation:

Independent loads can be overlapped by out-of-order execution. Therefore, a near-zero delta is a meaningful result: it describes the lower-bound throughput case.

CSV fields:

```text
experiment,events,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,delta_cycles_per_event,direct_cycles_per_event,pgot_cycles_per_event,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter
```

### 02_data_dependent

Measures direct data access versus pgot-data access in a dependent chain.

Variables:

| Variable | Values |
|---|---|
| chain steps per iteration | `1, 2, 4, 8, 16` |
| variant | `direct`, `pgot` |

Important interpretation:

The next step depends on the previous loaded value, so the extra pgot slot load is harder to hide. This is the latency-oriented upper-bound case for pgot-data.

CSV fields:

```text
experiment,chain_steps,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,delta_cycles_per_step,direct_cycles_per_step,pgot_cycles_per_step,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter
```

### 03_func_stable

Measures fixed-target pgot-func in a kernel module while varying event count.

Module builds:

| Build | Meaning |
|---|---|
| `no_retpoline` | ordinary indirect call build |
| `retpoline` | retpoline-protected indirect call build |

Variables:

| Variable | Values |
|---|---|
| variant | `direct`, `pgot` |
| pgot events | `1, 2, 4, 8, 16` |
| target count | always `1` |
| target behavior | stable target only |

This is the common case for the current pseudo-GOT design: each transformed
callsite normally resolves to one fixed target. `pgot_events` controls how many
function-call events are repeated in one loop iteration. In the `pgot` variant,
each event reloads `slot[0]` before calling the target, so the event count is a
real Pseudo-GOT event count rather than repeated calls through a hoisted function
pointer.

CSV fields:

```text
experiment,pgot_events,target_count,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,delta_cycles_per_event,direct_cycles_per_event,pgot_cycles_per_event,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter
```

For a targeted kernel-module run:

```bash
SUDO_PASSWORD='...' CPU=2 ITERATIONS=1000000 REPEATS=31 OUTER_RUNS=10 ./layer1/03_func_stable/run.sh
BUILDS=no_retpoline SUDO_PASSWORD='...' ./layer1/03_func_stable/run.sh
```

### 04_func_entropy

Measures pgot-func under a high-entropy target trace.

Variables:

| Variable | Values |
|---|---|
| target count | `1, 2, 4, 8, 16` |
| build | no-retpoline, retpoline |
| trace length | `65536` |

This is not the normal pgot callsite behavior. It is a stress test that bounds
the unfavorable branch-target prediction case. Here `target_count` changes the
number of possible indirect-call targets; it is different from `pgot_events` in
`03_func_stable`. Simple round-robin traces are intentionally avoided because
modern predictors can learn short regular patterns.

The trace is generated once before each case from a fixed seed and then reused. It is long enough to avoid a tiny repeating pattern, while still being reproducible.

CSV fields:

```text
experiment,variant,target_count,iterations,repeats,trace_len,cycles_per_call,iqr_cycles_per_call
```

For per-target perf collection:

```bash
PGOT_TARGET_COUNT=8 ./layer1/04_func_entropy/bench_noret
```

## Layer 2: Func Placement And Workload

Layer 2 asks:

> In an unfenced practical code stream, does the same amount of ordinary work
> hide or dilute retpoline func-pgot overhead differently when it appears before
> the call, inside the target, or after the call?

### 01_func_placement

Keeps function-event density fixed at one call per iteration and changes the
position of the same workload. It also includes a no-call `work_only` baseline
to measure the ordinary work stream by itself.

Variables:

| Variable | Values |
|---|---|
| event count | fixed `1` |
| placement | `none`, `work_only`, `before`, `inside`, `after` |
| workload | `0, 1, 2, 3, 4, 5, 6, 8, 16, 32, 64` |
| target pattern | stable target |
| build | no-retpoline, retpoline |
| fence mode | unfenced |

Run:

```bash
SUDO_PASSWORD='...' CPU=2 ITERATIONS=1000000 REPEATS=31 OUTER_RUNS=10 \
  ./run_experiment.sh layer2-func-placement
```

Retpoline fence diagnostics:

```bash
SUDO_PASSWORD='...' CPU=2 ITERATIONS=100000 REPEATS=15 OUTER_RUNS=3 \
  ./run_experiment.sh layer2-func-fence-diagnostics
```

This auxiliary run writes
`results/layer2/01_func_placement/diagnostics/fence_modes/` and refreshes the
fence-diagnostics section in `results/layer2/01_func_placement/summary.md`.

Output fields:

```text
build,fence,placement,workload,n_raw,direct_cycles,pgot_cycles,delta_cycles,delta_iqr,overhead_percent
```

Interpretation:

| Metric | Meaning |
|---|---|
| `direct_cycles` | median cycles/iteration for direct call |
| `pgot_cycles` | median cycles/iteration for slot-load + function-pointer call |
| `delta_cycles` | median paired delta, `pgot - direct` |
| `delta_iqr` | IQR of the paired delta samples |
| `overhead_percent` | `delta_cycles / direct_cycles * 100` |

For `work_only`, both measured sides run the same no-call body. Use its
`direct_cycles` column as the workload-only baseline; its delta is expected to
stay near measurement noise.

## Layer 3: Kernel-Function Benchmarks

### 01_sha256_transform

This experiment copies a SHA-256 block-transform closure into a kernel module
and compares the original implementation against a data-PGOT transformed
variant. It intentionally does not report func-PGOT for SHA-256, because the
message-word loading, message schedule, and round logic are part of the copied
closure rather than honest closure-external helpers.

| variant | meaning |
|---|---|
| `all_pgot` | SHA-256 K table address is loaded through a data slot |

Run:

```bash
SUDO_PASSWORD='...' CPU=2 ITERATIONS=100000 REPEATS=31 OUTER_RUNS=3 \
  ./run_experiment.sh layer3-sha256-transform
```

Results are written to `results/layer3/01_sha256_transform/`.

### 02_bch_encode

This experiment copies the BCH encode closure into the LKM. Internal helpers
such as `swap_bits`, `load_ecc8`, `store_ecc8`, and
`bch_encode_unaligned` are copied as part of the closure and remain direct
calls.

| variant | meaning |
|---|---|
| `origin` | copied encode closure, direct `swap_bits_table`, direct `memcpy` |
| `all_pgot` | `data_pgot + func_pgot` |

The module validates that all PGOT variants produce the same ECC bytes as
`origin` before collecting performance samples.

Run:

```bash
SUDO_PASSWORD='...' CPU=2 ./run_experiment.sh layer3-bch-encode
```

Results are written to `results/layer3/02_bch_encode/`.

### 03_zlib_deflate

This experiment copies the kernel zlib deflate closure from `deflate.c` and
`deftree.c` into the LKM. It reports `all_pgot`: selected deflate tables are
loaded through data slots, and closure-external `memcpy`/`memset` callsites are
loaded through function slots.

Run:

```bash
SUDO_PASSWORD='...' CPU=2 ./run_experiment.sh layer3-zlib-deflate
```

Results are written to `results/layer3/03_zlib_deflate/`.

### 04_zstd_decompress

This experiment copies the kernel zstd decompression closure into the LKM. It
reports `all_pgot`: selected default decompression tables are loaded through
data slots, and closure-external `memcpy`/`memset`/`memmove` callsites are
loaded through function slots.

Run:

```bash
SUDO_PASSWORD='...' CPU=2 ./run_experiment.sh layer3-zstd-decompress
```

Results are written to `results/layer3/04_zstd_decompress/`.

### 05_crc32_le

This experiment copies a CRC32 little-endian table-driven closure into the LKM
and compares direct table access with an all-PGOT variant. In this function,
all applicable PGOT means the CRC table base is loaded through a data slot; the
closure has no required helper call rewrite.

| variant | meaning |
|---|---|
| `origin` | copied CRC32_LE closure, direct CRC table reference |
| `all_pgot` | CRC table base loaded through `pgot_crc32table_le[0]` |

Run:

```bash
SUDO_PASSWORD='...' CPU=2 ./run_experiment.sh layer3-crc32-le
```

Results are written to `results/layer3/05_crc32_le/`.

### 06_lz4_compress_fast

This experiment copies the kernel `LZ4_compress_fast` implementation closure
into the LKM. The origin path calls the copied implementation directly. The
PGOT paths rewrite only closure-internal references that are visible in the
generated code: static data addresses become data-PGOT slots, and real
`memcpy`/`memset`/`memmove` callsites become func-PGOT slots. The LZ4 input
length and acceleration are runtime module parameters.

| variant | meaning |
|---|---|
| `origin` | copied `LZ4_compress_fast` closure, direct internal data and mem helpers |
| `data_pgot` | `LZ4_minLength` / `LZ4_64Klimit` loaded through data slots |
| `func_pgot` | copied closure with real mem helper calls routed through function slots |
| `all_pgot` | data-PGOT + func-PGOT |

Run:

```bash
SUDO_PASSWORD='...' CPU=2 ./run_experiment.sh layer3-lz4-compress-fast
```

Results are written to `results/layer3/06_lz4_compress_fast/`.

## Recommended Paper Figures

Use Layer 1 for primitive bounds:

1. pgot-data independent vs dependent: `cycles_per_event`.
2. pgot-func stable target: direct vs pgot, no-ret vs retpoline.
3. pgot-func high-entropy trace: `cycles_per_call` and `branch-misses` versus target count.

Use Layer 2 for practical retpoline visible-overhead sensitivity:

1. Show retpoline `delta_cycles` versus workload for `before`, `inside`, and
   `after`.
2. Show `work_only` cycles to indicate how large the ordinary work stream is
   when retpoline visible overhead becomes small.
3. Use no-retpoline as a control showing stable indirect call overhead is near
   zero.
4. Include `summary.md`, `static/nm_*.txt`, `static/objdump_*.txt`, and
   `stability/` as validation evidence.
5. Report absolute delta, relative overhead, and IQR together; they answer
   different questions.

## Notes For Integrating With The Real System

The pseudo-GOT tables in this package are synthetic:

```c
pgot_data_table[i] -> &direct_values[i]
pgot_func_table[i] -> target_i
```

When integrating with your actual transformed kernel functions, keep the same measurement format:

```text
direct_cycles_per_call
pgot_cycles_per_call
delta_cycles_per_call
overhead_percent
dynamic_pgot_data_per_call
dynamic_pgot_func_per_call
```

That lets the real-function layer reuse the same interpretation as Layer 2.
