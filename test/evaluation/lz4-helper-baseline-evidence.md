# LZ4: shared libc helper policy and complete runner validation

The current registered carrier calls libc through its explicit private slots
and stack-alignment bridges. The earlier same-source no-SIMD DSO uses local
REP helpers. A new `kernel-userspace-libc` DSO preserves the latter's algorithm
sources and compiler flags while resolving its external memory calls to libc.
The REP baseline remains a separate backend. This removes a helper-provider
mismatch from the primary application comparison while preserving the
Kbuild/user-compilation distinction.

## Actual comparison conditions

| Backend | Algorithm compilation | Out-of-line memory helpers |
| --- | --- | --- |
| `kernel-userspace-nosimd` | Linux-source compatibility build, -O3/PIC, vectorization and compiler SIMD disabled | Linked test-local REP implementations |
| `kernel-userspace-libc` | Same translation units and algorithm flags as the REP DSO | Normal libc GOT/PLT imports; helpers may use SIMD |
| `kernel-vkso` | Actual -O2 Kbuild owner, kernel ABI, with its recorded stack-protector/UBSAN flags; fentry omitted and indirect/return thunks disabled for these objects | Private slots → stack-alignment bridges → libc |
| `kernel-userspace-native` | Linux-source compatibility build, -O3/PIC/-march=native | Compiler-selected inline operations and libc |
| `user-default` / `user-nosimd` | Existing upstream 1.9.3 builds | Existing native/libc or scalar/REP policies |

The two scalar-body user variants have identical algorithm compilation flags;
the link inputs differ by `scalar_mem.c`, output path and SONAME. The build log
and independent audit retain the exact commands. The new DSO has no SIMD/MMX
instructions in its disassembly and imports memcpy, memmove and memset. This
says nothing about SIMD inside libc. The actual Kbuild commands are saved
separately; compiler options and runtime ABI are not claimed to match the
ordinary DSO. The comparison therefore measures the complete exported
implementation, not an isolated PGOT or physical-sharing ablation.

## Complete guest evidence

[Attempt 02](results/lz4-libc-baseline-qemu-20260912-attempt02/result.json),
boot `1ced9611-ddc5-4b54-957e-029319c698f3`, passes on exact119 KVM with the
unchanged current owner, registration module and manager. The ordinary DSOs
and official benchmark driver are freshly built from an isolated source
snapshot. The actual `run_under_replacement.sh` runs inside the active full
registration, using all twelve Silesia files and all three component block
sizes. This run validates collection; its timings do not enter formal host
performance tables.

| Check | Observed coverage |
| --- | --- |
| Original full registered CLI validation | 24 input/block pairs, 48 traced operations, stock cross-decoding |
| Six-backend cross-correctness | 6 compressors × 6 decompressors × 12 boundary sizes; 432 decode checks |
| Official component runner | 18 processes: 6 backends × 3 block sizes × 1 round; 36 raw rows |
| Full file workflow | 12 files × 2 block limits × 4 backends × 2 operations × 1 round; 192 complete CLI invocations |
| Actual helper targets | All three baseline GOT/PLT targets equal the carrier bridges' libc targets in one process |
| Negative helper-policy check | The actual old REP DSO is rejected as a libc-matched baseline |
| Page and owner lifetime | Four text pages and one RO page share kernel PFNs; owner reference 1; fresh mappings after release use different PFNs; all test modules unload |

For the file workflow, `same-source` now selects
`libkernel-userspace-libc.so`. The complete CLI still performs frame work,
checksums, allocation and buffered I/O. Every compression output is decoded
by stock CLI; every decoded complete output is compared with the source
hash during execution. Inputs and per-command records are archived. Separate
untimed traces confirm the selected APIs; timed calls disable counters.
The [independent audit](results/lz4-libc-baseline-qemu-20260912-attempt02/independent-audit.json)
checks the full row keys, parses all 18 original component logs, checks each
CLI invocation and verification log, actual helper records, compilation
commands, PFN changes and module release. It does not recreate deleted CLI
output files: their full-output checks were performed by the executing runner.

Attempt 01 passed the original CLI, helper-target audit and six-backend
cross-correctness, then stopped because the old parser expected five
backends. No application timing workflow ran in that attempt. Its logs,
failed terminal record and successful cleanup are retained. The parser now
requires the sixth backend explicitly when `--with-libc` is supplied; the
actual runner uses that option. Attempt 02 repeats the complete flow.

## Formal collection and retained results

The formal algorithm plan now requires 252 LZ4 rows per deployment:
7 rounds × 6 backends × 3 block sizes × 2 operations. Its CLI configuration
remains four rounds and 768 complete invocations per deployment. These are
within-deployment processes and rounds, not independent boots. The historical
210-row five-backend record remains accessible through explicit legacy mode.
The earlier pairwise CSV regenerates byte-for-byte unchanged.

[Collector checks](results/lz4-libc-baseline-qemu-20260912-attempt02/collector-validation.json)
reject a missing libc backend, a duplicated process log and a duplicated
summary row. Summary prose now reports computed ranges instead of fixed
claims about which paths are faster. New-source collection copies actual
files, including Git-ignored owner sources and untracked additions, alongside
the tracked diff. Each formal deployment also preserves its owner Kbuild
command records. The source-capture check verified 265 files (6,827,138 bytes)
at that point in the worktree; this is a source archive size, not memory cost.

The pending C/E work remains three complete physical-host deployments,
analysis across deployments and the BCH kernel-cost/diagnostic work. This
functional guest run supplies none of those performance conclusions.
