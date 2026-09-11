# Linux XZ Embedded vkso evaluation

This evaluation compares two executions of the same Linux 5.15 XZ Embedded
single-call decoder:

- `kernel-vkso`: machine code from a freshly loaded owner LKM, exposed through
  the normal sparse-DSO/page-replacement workflow;
- `native`: the same four decoder C files compiled as an ordinary user-space
  DSO with `-O2 -fPIC`.

It measures complete `.xz` stream decoding with LZMA2, the x86 BCJ filter, and
CRC32 validation. Unlike a raw memory-function microbenchmark, this exercises a
stateful format parser, range decoder, dictionary, filter, and integrity check.

## Prerequisites

The running kernel needs matching headers and `/sys/kernel/btf/vmlinux`.
Required tools are GCC, GNU make, binutils, Python 3, `xz`, `pahole`, `taskset`,
and sudo permission to load `vkso_xz` and the project's page-replacement
module.

## Run

Quick end-to-end check:

```sh
INPUTS=/bin/bash CPU=2 REPEATS=2 OUTER_RUNS=1 test/test_xz/run.sh
```

Default run (bash, Python, and libc when present):

```sh
CPU=2 REPEATS=20 OUTER_RUNS=7 test/test_xz/run.sh
```

Custom whitespace-separated input files may be supplied with `INPUTS`.
Compression is preparation only and is never timed. Every file is encoded with
one thread, CRC32, x86 BCJ, and a 1 MiB LZMA2 dictionary.

Do not set `VKSO_SKIP_CHECK=1` for reported results.

## Measurement and correctness

Decoder allocation and CRC-table initialization occur outside timing. Each
timed iteration executes `xz_dec_reset()` and one `xz_dec_run()` in documented
single-call mode. Before timing and after every timed batch, the harness checks
the return code, consumed and produced byte counts, byte-for-byte output, and
64-byte guard regions.

All outer rounds run in one process and one owner-module/page-registration
session. Backend order rotates between outer rounds. `summary.md` forms kernel/native
ratios within the same outer run before reporting their median and P10–P90.
The summarizer recomputes throughput from the lossless byte, repeat, and
elapsed-nanosecond fields; the rounded throughput column is display-only.

## Outputs

`results/` contains:

- `raw.csv`, `aggregate.csv`, and `summary.md`;
- `kernel-dso-audit.md`, which requires five exports, `DT_NEEDED:
  libshim.so`, four helper relocations, and a bounded reusable-page closure;
- generated DSO dynamic, relocation, symbol, page-map, resolved-symbol, and
  module-dependency evidence;
- source/build/runtime metadata and SHA-256 hashes of measured artifacts.

See [ADAPTATIONS.md](ADAPTATIONS.md) for the exact functionality boundary.
