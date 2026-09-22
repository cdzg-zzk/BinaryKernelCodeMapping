# XZ: complete export and functional validation

The [current-owner kernel-cost session](kernel-cost-evidence.md) adds five public
GPL module exports in owner metadata and runs the complete user and kernel
workloads in one registration. All 882 original user decodes and 99 three-backend
kernel trials pass, as do four declared PFNs and release. The four algorithm
objects' executable sections are unchanged; owner support is now 27 SLOC.

Current-build update: [identity-checked registration and complete algorithm workflows](registration-transaction-evidence.md#current-complete-algorithm-workflows)
rerun the full workload with the cooperative owner and current transaction
manager. The archived logs match owner and kernel build IDs before STAGE.
Owner refcount is 1 while active, source/user PFNs match, fresh
post-release mappings no longer use them, and all modules unload. The results
below retain their earlier build identities; formal performance for the new
build is still outstanding.


On 2026-09-12, a private KVM guest running the exact Ubuntu
`5.15.0-119-generic` kernel completed the unchanged XZ Embedded benchmark on
all three original inputs after a fresh `vkso init` / `vkso exec` deployment.
The [terminal result](results/xz-qemu-20260912-attempt01/result.json) is PASS;
the guest boot ID is `6b3c6ea2-f5c2-44bd-ae26-35001ac8e544`.
The benchmark's timing fields remain in the raw diagnostic log. They are not
formal API performance samples or evidence for baremetal speed ratios.

[functional-summary.json](results/xz-qemu-20260912-attempt01/functional-summary.json)
records the result and limits. The
[public kernel package record](results/xz-qemu-20260912-attempt01/kernel-package-evidence.json)
identifies Ubuntu package version `5.15.0-119.129`, downloaded and extracted
as the ordinary host user. The guest had no network or host sharing. The
host kernel, modules, permissions and original checker campaign were unchanged.

## Full implementation and workload

The owner, `xz-bench` and ordinary `libxz-native.so` were freshly built from
the project's unchanged XZ sources and Makefiles in the attempt directory.
The existing owner preserves its complete single-call decoder, x86 BCJ
filter, internal CRC32 implementation, namespacing, declared build flags and
private helper slots. This validation does not substitute another decoder.
[components.json](results/xz-qemu-20260912-attempt01/components.json) records
source and binary identities and actual build commands; the owner build log
retains the existing objtool warnings associated with the declared build flags.

The guest used current runtime symbols, a fresh KRG, the original function
checker and `build_PIC_so.py`, generated API headers, the original XZ DSO
audit and the actual manager registration path. The five requested exports
(`crc32_init`, `dec_init`, `dec_run`, `dec_reset`, `dec_end`, with the
`vkso_xz_` prefix) passed the checker. The
[DSO audit](results/xz-qemu-20260912-attempt01/evidence/validation/kernel-dso-audit.md)
passed its existing export, helper-relocation and page-count requirements.
No skip-check option or patched exporter was used.

The unchanged preparation script compressed the complete copied inputs using
`--threads=1 --check=crc32 --x86 --lzma2=dict=1MiB`:

| Original input | Complete input bytes | Compressed bytes |
| --- | ---: | ---: |
| `/bin/bash` | 1,396,520 | 519,536 |
| `/usr/bin/python3` | 5,917,224 | 1,920,196 |
| `/usr/lib/x86_64-linux-gnu/libc.so.6` | 2,220,400 | 726,804 |

The original benchmark ran with 20 repeats and seven outer rounds, using
both `native` and `kernel-vkso`, on guest CPU 0. It completed all **42 rows**.
The [validation record](results/xz-qemu-20260912-attempt01/evidence/validation/xz-validation.json)
and [raw diagnostic rows](results/xz-qemu-20260912-attempt01/evidence/validation/raw-diagnostic.csv)
retain the full matrix and source identities. The following counts are
derived from the unchanged benchmark's loops and its successful exit;
they are not separately instrumented runtime counters:

- 882 complete decodes: one warm-up plus 20 repeats per row; 441 use the registered backend.
- Every decode requires `XZ_STREAM_END`, consumption of the entire compressed input and production of the entire original output.
- 84 full-output `memcmp` checks: after warm-up and after the repeat loop for each row.
- 42 pairs of intact 64-byte output guards, checked after each repeat loop.

The benchmark exercises all five APIs, including reset between repeated
decodes and decoder cleanup. This is one fresh deployment with the original
workload, not seven or 20 independently rebuilt deployments.

## Declared physical backing and cleanup

All four declared pages matched their source kernel PFNs in a Python loader
process both before and after the full benchmark workload:

| File offset | Kind | Loader permission | Source and loader PFN |
| --- | --- | --- | ---: |
| 0x1000 | text | r-xp | 1,136,537 |
| 0x2000 | text | r-xp | 1,136,538 |
| 0x3000 | text | r-xp | 1,136,539 |
| 0x4000 | rodata | r--p | 1,136,540 |

The [before-workload record](results/xz-qemu-20260912-attempt01/evidence/validation/registered-pfns-before-workload.json)
and [after-workload record](results/xz-qemu-20260912-attempt01/evidence/validation/registered-pfns.json)
use fresh `os.pread()` pagemap reads after faulting each declared page.
The kernel probe resolves the source addresses in the same guest.
The benchmark is a separate process using the same registered DSO pathname;
its individual PTEs were not sampled. These records establish the loader's
declared-page aliases, not multi-process scaling or net memory savings.

After normal manager cleanup, fresh mappings of all four file offsets had
PFNs different from their corresponding source PFNs:
[restored-pfns.json](results/xz-qemu-20260912-attempt01/evidence/validation/restored-pfns.json).
Only then did the guest unload the replacement module, PFN observer and XZ
owner. Their commands returned zero, and the final module list contains only
the disk driver. QEMU exited zero without a kernel BUG, WARNING or panic.

This proves removal of source backing from fresh file mappings in this
ordered session. No old mapping was retained across restore, and restored
bytes were not compared with a saved original carrier. The observed owner
refcount during registration was still zero; `module_deps.txt` contained
only the helper summary. The harness kept the owner loaded until PFN
restoration was verified. Automatic owner pinning and partial-registration
failure behavior remain separate unresolved work.

## Selected archive

[archive-selection.json](results/xz-qemu-20260912-attempt01/archive-selection.json)
lists the selected records, consumed sources and binaries, build logs,
original checker/audit output, input archives, PFN observations and cleanup
logs. The original full inputs can be recovered from the three archived
`.xz` files; their decompressed identities are checked against the inputs
recorded by the guest. Disposable disk, initramfs, large debug kernel,
duplicate plaintext corpus and intermediate build objects are not selected.
The generated carrier is archived after cleanup, so its restored sparse code
pages are not a snapshot of the active kernel-backed bytes.

This adds one complete XZ deployment and functional result to Group C and
one declared-page observation to Group B. Formal deployment repetitions,
baremetal performance and the planned resource/lifetime checks remain
outside this result.
