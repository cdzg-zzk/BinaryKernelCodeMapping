# BCH same-session resource evidence (exact119 private guest)

Actual attempt03 completed with `result.json: status=pass`, QEMU return 0, no
kernel failure, and all nine loader groups passing. The consumed guest preserves
the full owner, original `vkso init/exec/export`, checker, generated carrier/shim,
and the existing complete BCH `--correctness-only --correctness-vectors 128`
benchmark. Resource probes only dlopen and fault pages; the correctness benchmark
is a separate process in the same registered session. No performance samples are
reported. Boot ID: `d8069aa3-7c4f-4a1f-8d48-c3904c0ede8f`.

## Supported physical-page accounting

All values below count distinct observed 4 KiB PFNs, with a set union across the
simultaneously alive loader processes. Library scope includes every readable
PT_LOAD page, including writable data, RELRO and metadata. The registered rows
also include its required libshim. The owner is the newly built dedicated
`vkso_bch` module, not the independently configured original kernel BCH module.

| Controlled role / observed scope | 1 loader | 4 loaders | 16 loaders |
|---|---:|---:|---:|
| Native DSO, before dedicated owner load | 7 | 13 | 37 |
| Native DSO, dedicated owner already loaded | 7 | 13 | 37 |
| Native DSO union full dedicated-owner core | 13 | 19 | 43 |
| Registered carrier + required shim | 11 | 23 | 71 |
| Registered carrier + shim union full dedicated-owner core | 13 | 25 | 73 |
| Registered declared source + loader page union | 4 | 4 | 4 |
| Native DSO executable-page union | 3 | 3 | 3 |

The two native roles produce the same library page counts. The owner-loaded role
is a controlled conditional baseline; artificial preloading does not establish
that an original kernel workload needed the dedicated module. Compared with the
native DSO plus the same owner, the registered library/shim/owner scope is equal
at N=1 and occupies 6 and 30 additional pages at N=4 and N=16. Compared with native
before owner load, the measured difference is 6, 12 and 36 pages. These are
explicit partial-scope comparisons, not whole-system net memory measurements.

The registered three text pages and one rodata page match the declared owner PFNs
in every one of 21 registered loaders (4, 16 and 64 matching mappings in the three
groups); their kernel/user union remains four pages. The native executable PFNs
are shared across all simultaneous native loaders as ordinary file-backed code.
Consequently ordinary DSO text is not multiplied by process count.

## Support and infrastructure observations

Within the registered target/shim scope, each loader has two carrier support
pages and two shim pages whose observed PFNs are distinct between simultaneous
loaders; the shim also has three PFNs shared by the loader group. The native DSO
has five shared PFNs and two distinct PFNs per simultaneous loader. The raw
records retain permissions, ELF section overlaps, pagemap file/shared-anon and
exclusive bits, and per-PFN distinct-process counts. A private VMA/nonfile bit
alone is not used as proof of physical ownership: such flags may also describe a
shared zero page. These probes do not construct BCH control objects or workload
heaps; the full correctness process exercises them separately without resource
attribution.

The module census covers all sysfs `coresize` pages with zero missing addresses:

| Module | Resident core bytes | Unique observed core PFNs |
|---|---:|---:|
| vkso_bch | 24,576 | 6 |
| vkso_kernel_reader observer | 16,384 | 4 |
| page_cache_replace | 49,152 | 12 |

All three report `initstate=live`, `initsize=0`, and agreement between
`/proc/modules` total size and sysfs core size. Their complete recorded core PFN
sets remain unchanged from pre-registration to registered use and to the
post-restore, pre-unload observation. The six owner pages include the four
shared pages and two other core pages. ELF section annotations identify code,
read-only data/metadata and writable module data; pages without overlapping
allocated ELF sections remain unattributed core bytes (they are not automatically
called padding). The census excludes external allocations, allocator metadata,
and the already freed init extent. Exact119 debug-ELF confirmation of the module
field semantics is separately saved in `../module-layout-119-20260912/`.

The active manager is PID 289 in all three registered groups, confirmed from
`/work/repo/page_cache_replace/runtime/manager.pid` and saved process records.
Each group observes 304 resident PFNs in its VMAs; status reports VmRSS 1,216 KiB,
RssAnon 76 KiB, RssFile 1,140 KiB and VmPTE 28 KiB; smaps_rollup reports Pss 1,212
KiB. These process metrics are not added blindly to module/library page unions.
Loader VmPTE values are 88–100 KiB, with measured after-load/fault minus baseline
0 KiB in every loader. This reflects allocation granularity and the existing
Python address space, not zero page-table cost.

## Raw records and checks

`evidence/validation/bch_resources/` contains the three named roles. Each n01,
n04 and n16 group retains per-PID records before load, after dlopen, and after
faulting all target/shim PT_LOAD pages: maps, smaps, smaps_rollup, status and raw
pagemap binaries. JSON indices identify every recorded VMA, address, file offset,
binary byte offset and short/error read. Pagemap uses fresh os.pread after faults
and only mapped VMA ranges; x86 vsyscall is retained as an unread range. The
processes wait at phase barriers while their observations are taken. Snapshots
are sequential, not an atomic system snapshot. General Python/runtime and
observer allocations remain visible and are not attributed to BCH automatically.

`bch_resource-audit.json` reconstructs the PFN unions from those raw binaries,
checks all 63 distinct loader PIDs and one boot identity, all four declared-page
matches, complete/stable module core coverage, manager records and full existing
correctness result. Reproduce with:

```sh
python3 test/evaluation/bch_resource_audit.py test/evaluation/results/bch_resource-qemu-20260912-attempt03
```

`bch_resource_coverage.py` independently reconstructs target coverage from the
archived ELF program headers and VMA/file-offset relationships, then checks
all 63 loaders and 189 raw snapshots. It verifies library sets, complete
PT_LOAD page sets, sparse load bias, PFN/category unions and infrastructure
observations; `bch_resource-coverage.json` retains its PASS result. This
supplements the main auditor, which uses recorded target lists and categories.

The full correctness log has the actual PASS markers for m=13/t=4 and m=13/t=8,
128 error-vector trials, all errors 0..t, all three backends and both decode modes.
The 10,752 decode checks (3,584 registered) are derived from the unchanged loops,
not separately counted markers. Each parameter uses one seeded 512-byte data
payload with parity appended to form the codeword. Each of 128 trials sweeps
errors 0..t; the trials do not provide 128 different data buffers or guarantee
distinct error vectors. Fresh file-offset mappings were
verified to differ from the registered PFNs before the ordinary ordered module
unload. Restoration does not establish byte equality or old-mapping teardown.

## Preserved preparation failures and remaining scope

Attempt01 failed in the test loader before any owner load because it assumed the
native library used the registered symbol prefix. Attempt02 completed all six
native groups but rejected the first registered observation because dladdr's
first mapped address was mistaken for the sparse carrier's ELF load bias. Its
saved pagemap independently confirms the four correct source matches after
reconstructing the correct bias (`../bch_resource-qemu-20260912-attempt02/bch_resource-offset-diagnostic.json`).
Attempt02 remains a failed campaign; its restore gate skipped module unload when
no normal registered-pfns record existed, and the private guest powered off.
Attempt03 uses VMA/file-offset-derived load bias and explicitly checks offsets.
Both failed guest outputs and consumed sources are retained.

`bch_resource-failed-preparations.tar.gz` preserves the two failure outcomes,
logs, consumed guest scripts and the first registered observation's raw
snapshots. Its paths are relative to `test/evaluation/results/`. Complete
failed guest disks and preparation trees remain in their local attempt
directories.

The compact `bch_resource-evidence.tar.gz` contains the selected raw records,
consumed source/binary inputs and their original directory layout. To reproduce
the audit from the archive alone without writing over an attempt:

```sh
bch_replay_dir=$(mktemp -d /tmp/vkso-bch-resource-replay.XXXXXX)
tar -xzf test/evaluation/results/bch_resource-qemu-20260912-attempt03/bch_resource-evidence.tar.gz -C "$bch_replay_dir"
python3 test/evaluation/bch_resource_audit.py "$bch_replay_dir"
python3 test/evaluation/bch_resource_coverage.py "$bch_replay_dir"
```

The archive-only replay reproduces `bch_resource-audit.json` byte for byte.
`bch_resource-archive-selection.json` lists its files and excluded large guest
artifacts. The original failed attempt directories remain separate locally.

The result closes this BCH loader-sharing/core-census observation only. It does
not establish whole-system net savings, demand for an already resident dedicated
owner, BCH live control/heap costs, complete allocator/slab/infrastructure
attribution, formal deployment/performance distributions, owner-module pinning,
acknowledged registration or transactional rollback. Those B requirements remain.
