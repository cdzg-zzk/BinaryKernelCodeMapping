# LZ4 registered application evidence — 2026-09-12

The complete LZ4 CLI reaches the selected registered carrier but fails on its
first compression operation. The failure is an unresolved direct relative
helper call in the current export path. Static checks and physical page
sharing succeed before that call; neither establishes executable closure
completeness. These guest sessions provide functional and diagnostic evidence,
with no application performance samples.

## Workload and environment

The [application plan](lz4-cli/README.md) retains the complete upstream 1.9.3
CLI, frame processing, checksums, allocation and file I/O. The registered
backend validation requires all 12 complete Silesia files, independent blocks
at 64 KiB and 1 MiB, compression and decompression: 24 input/block pairs and
48 selected-backend operations. Each pair must decode a common stock frame,
cross-decode the adapted output with the stock CLI, match the complete input,
and record calls to the selected DSO. Zero pairs completed in the registered
sessions below. The separate ordinary-DSO validation passed 48
input/block/backend pairs across its two user-space backends.

[`lz4_qemu.py`](lz4_qemu.py) prepares a private KVM guest using the exact
Ubuntu `5.15.0-119-generic=5.15.0-119.129` kernel and the existing full
[`lz4_guest.py`](lz4_guest.py) validation. The guest has no network or shared
host directory. The kernel image was extracted from the public package;
package and environment records are included with attempt 06. Modules are
loaded only in the guest. The harness invokes the actual `vkso init` and
`vkso exec` path, rebuilding runtime KRG, static checks, type header, sparse
carrier and shim for that session. No checker bypass, historical runtime
address substitution, exporter patch or replacement algorithm was used.

## Attempt ledger

All paths below are under `test/evaluation/results/`. Earlier failures remain
separate records; preparation failures are not algorithm test failures.

| Directory | Last reached stage | Outcome |
| --- | --- | --- |
| `lz4-cli-qemu-20260912-attempt01` | Launch `vkso` | Guest lacked `/usr/bin/env`; no algorithm cases started. |
| `lz4-cli-qemu-20260912-attempt02` | Preparation | Superseded before starting QEMU to add restoration observation. |
| `lz4-cli-qemu-20260912-attempt03` | Build runtime KRG | Guest lacked `/dev/fd`; Bash process substitution failed before registration. |
| `lz4-cli-qemu-20260912-attempt04` | Checks, build, registration | Buffered pagemap observer reported a missing PFN before CLI execution; cleanup could not be verified, so module unload was skipped and the private guest shut down. |
| `lz4-cli-qemu-20260912-attempt05` | Four PFN matches, first full CLI compression | `dickens`, 64 KiB, SIGSEGV; four fresh post-cleanup mappings no longer pointed to their source PFNs, then modules unloaded. |
| `lz4-cli-qemu-20260912-attempt06` | Fresh owner build, same full CLI, GDB diagnosis | Same first-operation failure; unchanged direct call predicts the exact unmapped fault address; four PFN matches and four post-cleanup source-PFN differences verified. |

Attempt 04's observer reused a buffered pagemap reader while faulting adjacent
pages one at a time. An independent [presence-bit observation](results/pagemap-freshness-20260912/README.md)
reproduced stale buffered entries. Later sessions use `os.pread` after each
fault. This change affects the new LZ4 observer; the frozen Clocktime campaign
and its measurement implementation remain unchanged.

Attempt 06 rebuilt the current owner sources with exact-version headers and
split BTF in an isolated directory. Its two selected compression functions
match the earlier owner's unrelocated function bytes. The decompressor does
not: its symbol size changes from 949 to 917 bytes. The archived
`owner-build-evidence/selected-function-comparison.json` records this
difference; this is not a claim of whole-module binary identity.

## Direct-call diagnosis

The authoritative records are in
[`lz4-cli-qemu-20260912-attempt06`](results/lz4-cli-qemu-20260912-attempt06/):

| Observation | Evidence |
| --- | --- |
| Checker reports `PASS`, treating calls to `memset` and `memcpy` as shim boundaries | `evidence/validation/export/vkso/metadata/checks/vkso_LZ4_compress_default.log` |
| Builder emits `memset`, `memcpy`, `memmove` as undefined imports | `carrier-elf.txt` and `evidence/validation/export/vkso/metadata/resolved_symbol_addresses.txt` |
| Carrier has three module text pages and one module rodata page | `evidence/validation/export/vkso/metadata/page_mappings.txt` |
| ELF has nine `R_X86_64_64` data relocations and no rebinding of this executable direct call | `carrier-elf.txt` |
| First full CLI compression faults inside the selected carrier's call chain | `evidence/validation/cli-validation.json` and `full-cli-gdb-diagnostic.log` in the same directory |

In the diagnostic guest, the call instruction in
`LZ4_compress_fast_extState` is at `0xffffffffc0009e78` and its kernel
`memset` target is `0xffffffff816bb8a0`. The signed displacement is
`target − (call + 5) = −1049945565`. In the GDB process, the same shared
instruction is at `0x7ffff7d87e78`, so its unchanged displacement produces:

```text
0x7ffff7d87e78 + 5 - 1049945565 = 0x7fffb94398a0
```

GDB reports exactly `RIP=0x7fffb94398a0`, outside every mapped range, and a
return address of `0x7ffff7d87e7d`. Registers contain `rsi=0` and `rdx=16416`,
matching the work-memory initialization. The backtrace reaches
`vkso_LZ4_compress_default` through the full frame/CLI path. The observed
failure occurs before entering a shim or libc helper; it does not establish
a libc calling-convention failure. GDB's rerun diagnoses the same full input
and operation and is not counted as a passing case.

[`verify-diagnosis.py`](results/lz4-cli-qemu-20260912-attempt06/verify-diagnosis.py)
recomputes the displacement from the raw checker/resolved-symbol records,
compares GDB's decoded target and RIP against all 32 recorded mapping ranges,
and checks the PFN and unload records. Its
[`evidence-audit.json`](results/lz4-cli-qemu-20260912-attempt06/evidence-audit.json)
passes as an evidence-consistency check while retaining the failed application
status. The [archive selection](results/lz4-cli-qemu-20260912-attempt06/archive-selection.json)
lists the preserved records and consumed components; large guest disks,
initramfs trees, corpus copies and debug kernel image remain in the local
attempt directories outside Git.

Declaring an undefined dynamic symbol does not retarget an unchanged direct
branch in a shared executable page. The observed exporter output omitted
the native destination while treating it as a shim import. The next change
therefore concerns binding and closure construction, not LZ4 timing or the
number of repetitions. The separately prepared exporter proposal is unapplied.

## Mapping and cleanup observations

Before CLI execution, a separate loader process loads the same registered
DSO, faults each declared page, and compares fresh user pagemap entries with
the kernel PFN probe. All four declared pages match: three are RX and one
is R. This checks physical backing in that loader process; it does not
directly measure each CLI process's PFNs or a whole-system net memory saving.
The GDB record also contains an executable process stack, so the carrier
permissions do not imply process-wide W^X.

After `vkso exec` returns, the observer opens fresh mappings of the four
file offsets. Their PFNs differ from the registered source PFNs. The manager
log records its restore-and-exit path, each module unload command returns
zero, and the final module list contains none of the three test modules.
This establishes the observed fresh mappings and ordered unload; it does not
verify original carrier bytes, original PFN identity, surviving old mappings,
transactional rollback or owner pinning.

The next complete application result still requires resolving the direct-call
binding, then passing the full 24-pair registered validation and collecting
the three-deployment application matrix defined by the plan. A successful
rejection of an unsupported export would improve error reporting but would
not complete that application experiment.
