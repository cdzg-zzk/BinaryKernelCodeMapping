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
| `same-source` | Adapted CLI calling the adapted Linux 5.15 scalar-body DSO with libc helpers | Same-source application comparison with the same helper provider |
| `kernel-vkso` | Same adapted CLI calling the live registered kernel-backed carrier | Complete VKSO application path |

The new `same-source` target is `libkernel-userspace-libc.so`. Before any CLI
measurements, the component runner records actual baseline GOT/PLT targets and
carrier bridge providers in `helper-targets.json`; the workflow requires this
evidence with `--helper-evidence`. Algorithm flags match the REP user DSO, but
libc helpers may execute SIMD. The earlier REP-baseline application runs below
retain their own identities.

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
identity list. The CLIs now compile. Actual registered sessions have reached
the first compression call and failed because an unchanged direct relative
helper call targets an omitted mapping; see the evidence update below. Full
registered correctness and workflow measurements remain incomplete.
Prepared source or functional validation is not application performance evidence.

Before execution, Python/shell syntax, dry build commands, unequal-file
aggregation fixtures, and the four-position backend rotation were checked.
These checks do not replace compiling and exercising the actual carrier.

## Build and ordinary-DSO validation — 2026-09-12

After Clocktime stopped, `make -j2` built both complete CLIs successfully.
The existing Linux-source no-SIMD DSO target also compiled from the actual
algorithm sources. All 12 complete Silesia files passed both 64 KiB and 1 MiB
block configurations with the upstream-default user DSO and the Linux-source
no-SIMD user DSO: 48 input/block/backend cases. Each case checked nonzero
selected compress/decompress call counts and the selected function's DSO,
decoded common stock frames, and cross-decoded adapted output with stock CLI.
Every complete output matched its input. No application performance result
was taken from these functional invocations.

Records and the exact validation command are under
`test/evaluation/results/harness-validation-20260912/lz4-cli-ordinary-dsos/`
from the repository root. The built no-SIMD DSO is preserved there. This
checks both adapter API signatures through ordinary DSOs; it does not check
the live registered carrier or its physical backing.

An earlier validation command mistakenly selected `liblz4-nosimd.so` (the
upstream API) for the kernel-signature mode; the adapter rejected its missing
`vkso_LZ4_compress_default` symbol before compression. That failed command's
logs remain in the sibling `lz4-cli/` directory. The corrected validation uses
`libkernel-userspace-nosimd.so`; the earlier workflow selected that
library. No adapter or algorithm change was needed.

## Registered-carrier validation — 2026-09-12

The exact-version private guest ran the full `vkso init/exec` path, including
runtime KRG, static checks, carrier construction and registration. A separate
loader process confirmed all four declared source/user PFN matches. The
complete CLI then failed on its first `dickens`/64 KiB compression call, so
zero of the 24 registered input/block pairs completed. GDB confirmed that an
unchanged direct relative call to kernel `memset` reached an unmapped user
address; the exporter had classified that dependency as a shim import.

The [application evidence note](../lz4-application-evidence.md) preserves the
six-attempt ledger, actual call-address calculation, build identities,
mapping observations and cleanup scope. The exporter proposal remains
unapplied. This failure must be resolved before executing the complete
registered correctness matrix and the planned performance deployments.
