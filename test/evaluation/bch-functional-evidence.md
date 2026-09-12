# BCH: complete export and functional validation

On 2026-09-12, a private KVM guest running the exact Ubuntu
`5.15.0-119-generic` kernel completed the existing BCH correctness-only path
after a full `vkso init` / `vkso exec` deployment. The owner, benchmark, and two
ordinary DSO baselines were freshly built from unchanged project sources in
an isolated output directory. No host module was loaded and no API
performance samples were collected.

The authoritative result is [attempt01/result.json](results/bch-qemu-20260912-attempt01/result.json).
Its guest boot ID is `0678fa45-6ef4-45f1-85ed-ce7f093a989e`. The public kernel
package identity is retained in
[kernel-package-evidence.json](results/bch-qemu-20260912-attempt01/kernel-package-evidence.json);
[components.json](results/bch-qemu-20260912-attempt01/components.json) records the
consumed sources, binaries, prepared initramfs identity, and host build
commands. The inherited initramfs prints `lz4_guest_status`; the BCH launcher
also requires the BCH-specific pass marker and guest status record.

## Full implementation and correctness coverage

The unchanged [BCH benchmark](../test_BCH/src/bch_bench.c) already provides
`--correctness-only`. The guest invokes it with `--correctness-vectors 128`
and the actual registered `libvkso_bch.so`, same-source ordinary
`libbch-kernel-native.so`, and author `libbch-author-standalone.so`.
All four requested exports (`vkso_bch_init/free/encode/decode`) pass the
unmodified closure checker during `vkso exec`; no skip-check option is used.

The [actual correctness log](results/bch-qemu-20260912-attempt01/evidence/validation/bch-correctness.log)
contains both parameter-case PASS lines and the successful completion line.
The following detailed counts are derived from the consumed benchmark's
`run_correctness()` loops, not separate runtime counters:

| Parameters | Error counts | Seeded trials per error count | Backends | Decode modes | Derived decode checks |
| --- | --- | --- | --- | --- | --- |
| m=13, t=4 | 0–4 | 128 | 3 | precomputed, full | 3,840 |
| m=13, t=8 | 0–8 | 128 | 3 | precomputed, full | 6,912 |
| Total | Both cases | — | — | — | 10,752 |

Each parameter case uses its existing seeded 512-byte data codeword. The 128
trials vary error-vector generation within each error count; they are not 128
independently generated data buffers. All three backends share the generated
error vectors. Existing checks compare BCH geometry and encoded parity,
require exact returned error locations, and verify that correction restores
the codeword. The registered backend accounts for 3,584 of the loop-derived
decode checks. The
[guest validation record](results/bch-qemu-20260912-attempt01/evidence/validation/bch-validation.json)
preserves the exercised arguments and coverage interpretation.

These are the project's complete adapted BCH APIs. Their existing
namespacing, scalar build options, table addressing and domain-private helper
slots are unchanged; this experiment does not replace them with the
distribution's original BCH binary or redirect original kernel callers.
The [owner build log](results/bch-qemu-20260912-attempt01/owner-build.log)
retains the GCC package-revision difference and existing objtool warnings
associated with the declared no-thunk adaptation. The actual guest emitted
no kernel `BUG`, `WARNING`, or panic.

## Declared physical backing

The [page plan](results/bch-qemu-20260912-attempt01/evidence/validation/export/vkso/metadata/page_mappings.txt)
contains three text pages and one rodata page. A Python loader process
loads the actual registered DSO, faults each declared page, and uses fresh
`os.pread()` pagemap reads after each fault. The kernel PFN observer resolves
the corresponding source addresses in the same guest.

| File offset | Kind | Loader permission | Source and loader PFN |
| --- | --- | --- | --- |
| 0x1000 | text | r-xp | 1,136,691 |
| 0x2000 | text | r-xp | 1,136,692 |
| 0x3000 | text | r-xp | 1,136,694 |
| 0x4000 | rodata | r--p | 1,137,193 |

The [PFN record](results/bch-qemu-20260912-attempt01/evidence/validation/registered-pfns.json),
[kernel observations](results/bch-qemu-20260912-attempt01/evidence/validation/source-pages.csv),
and [loader maps](results/bch-qemu-20260912-attempt01/evidence/validation/carrier-process-maps.txt)
support all four matches. This is one loader process's declared-page
observation. The correctness benchmark is a separate process using the same
registered DSO pathname; its individual PTEs were not sampled. The record
does not establish multi-process scaling, private-support accounting or net
system-memory savings.

## Ordered cleanup and its scope

The [manager log](results/bch-qemu-20260912-attempt01/evidence/validation/export/vkso/metadata/page_replace.log)
confirms `/work/repo/page_cache_replace/runtime/manager.state`, followed by
normal restore and manager exit. After `vkso exec` returns, each declared
file offset is freshly mapped and faulted again. All four
[post-restore PFNs](results/bch-qemu-20260912-attempt01/evidence/validation/restored-pfns.json)
differ from their corresponding source PFNs: 1,260,106; 1,161,031;
1,228,736; and 1,228,738. Only after these checks does the guest unload the
page manager, observer and BCH owner. Their commands return zero and the
[final guest record](results/bch-qemu-20260912-attempt01/evidence/validation/status.json)
shows that these modules are absent.

This cleanup check establishes fresh-file-mapping backing removal in the
normal ordered session. It does not compare restored bytes with a saved
pre-registration carrier, retain an old mapping across restore, or test
concurrent owner unload. The sampled owner refcount during registration is
still zero; no module-pinning or registration-protocol repair is implied.

## Archive and remaining work

[archive-selection.json](results/bch-qemu-20260912-attempt01/archive-selection.json)
lists the selected small records and binaries. It includes the consumed
guest/launcher/helper scripts, source snapshots, actual owner and baselines,
build logs, closure logs, page plan, PFN observations and cleanup records.
Large disposable disk, initramfs, vmlinux and full dependency-graph outputs
remain outside the selected Git archive.

This closes one exact119 functional deployment and declared-PFN observation
for BCH. Group C still needs the planned full deployment repetitions and
unmodified performance collection, relevant PMU/owner-kernel diagnostics and
cross-algorithm synthesis. Group B still needs full setup/first-call and
resource accounting, multi-process and page-count scaling, private-page
classification, owner-lifetime and partial-failure contract work, and the
remaining mapping/file boundary cases. A passing guest correctness run does
not discharge those requirements.
