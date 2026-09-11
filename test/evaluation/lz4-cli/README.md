# LZ4 file workflow

This is group E's application experiment. It uses the complete upstream LZ4
1.9.3 command-line program to compress and decompress real Silesia files.
It retains the frame implementation, headers, content checksum, allocation,
and buffered file I/O. The tested configuration is level 1, independent
blocks, no dictionary, and 64 KiB/1 MiB block limits.

The original [`lz4frame.c`](https://github.com/lz4/lz4/blob/v1.9.3/lib/lz4frame.c)
routes this compression configuration through
`LZ4_compress_fast_extState_fastReset`; its frame decoder calls
`LZ4_decompress_safe_usingDict`. The adapter redirects these block calls to
the already-exported complete Linux LZ4 interfaces. Upstream source files are
unmodified. This is a file-application experiment, distinct from the existing
in-memory official benchmark.

## Comparisons and measurement

| Backend | CLI / selected block implementation | Purpose |
| --- | --- | --- |
| `stock-cli` | Original upstream CLI and built-in block implementation, release-style `-O3` build | Ordinary application reference |
| `upstream-dso` | Adapted CLI calling the existing upstream 1.9.3 user DSO | Separates a practical dynamically selected user implementation from the stock CLI |
| `same-source` | Adapted CLI calling the existing adapted Linux 5.15 no-SIMD user DSO | Same-source application comparison |
| `kernel-vkso` | Same adapted CLI calling the live registered kernel-backed carrier | Complete VKSO application path |

The three adapted modes use the same dispatch code. The two kernel-API modes
allocate 64 KiB of work memory per CLI process; upstream uses its frame
context. The upstream DSO uses the existing algorithm experiment's
`-O3 -march=native` build. The stock CLI uses the upstream release's ordinary
`-O3` setting. Dynamic selection, initialization, build differences and helper
bindings are part of those application comparisons, not a pure PFN ablation.

Every measured invocation processes one complete file, including process and
loader startup, frame work, allocation, file open/read/write/close, and normal
exit. Parent wall time includes the `taskset`/CLI launch; child CPU time and
fault counts are recorded separately. Inputs are pre-read before each command;
output is buffered and is not fsynced. This measures ordinary cached file
processing, not durable-storage throughput or cold-disk latency.

Compression runs each encoder on the same source file. Decompression always
uses the same stock-encoded frame for a given source and block size, so its
input work is identical across backends. Every generated compressed file is
decoded with the stock CLI and checked against the complete original input;
every measured decode is checked likewise. These checks are outside timing.
Compressed sizes are retained because different encoders can change I/O work.
Compression and decompression are separate workloads, not a summed round-trip
metric with mismatched intermediate files.

Four outer rounds per deployment rotate backend and block order, putting
each backend in every position for each input/block case. For the
12-file Silesia manifest this yields 768 measured CLI invocations per
deployment (12 files × 2 block limits × 4 backends × 2 operations × 4 rounds).
`rounds.csv` sums full CLI wall times and plain bytes across files;
`summary.md` reports matched-round ratios within that deployment. The complete
algorithm orchestrator supplies three separately registered deployments.
Neither the four inner rounds nor the individual files are independent
deployment samples.

In separate untimed invocations, the adapter counts calls and uses `dladdr`
to record the actual selected function's DSO. Both compression and
decompression must exercise their selected API. Timed invocations disable
these counters. The diagnostics identify the selected carrier; the actual
kernel/user PFN match is the separate group B observation. The adapted CLI
still links upstream code needed for its other features, so this experiment
does not establish a reduction in the application's total code footprint or
support for every CLI option.

## Execution

The source preparer reads the already-cached official release archive, checks
its recorded release identity, and extracts `lib/`, `programs/`, and licenses
into the ignored local vendor directory. It downloads that release only if
the original algorithm archive is absent. It does not replace the algorithm
experiment's vendor files. The Makefile builds stock and adapted CLIs from
the same extracted release.

After Clocktime is finished, use the complete deployment runner with the
application option:

```sh
sudo python3 test/evaluation/algorithm_deployments.py \
  --output test/evaluation/results/algorithm-deployments-with-cli-20260911 \
  --with-lz4-workflow --execute
```

Omit `--execute` to print the plan. LZ4 builds both CLIs before its measurement
phase, runs the original algorithm matrix, and then runs this workflow before
the same registration is restored. Files appear under each LZ4 deployment's
`results/cli-workflow/`; the full CLI binaries are included in its artifact
identity list. Source and adapter builds, active-carrier correctness, and
full workflow measurements still require execution after the current
Clocktime campaign. Prepared source or Python validation is not application
performance evidence.

Before execution, Python/shell syntax, dry build commands, unequal-file
aggregation fixtures, and the four-position backend rotation were checked.
These checks do not replace compiling and exercising the actual carrier.
