# BCH live-allocation evidence: exact119 private guest

Attempt01 completed with QEMU return 0, no kernel BUG/WARNING/panic, all nine
loader groups passing, and normal carrier restoration followed by module
unload. Boot ID: `15bda703-bf88-4ea1-ba26-da3afa33af3d`. No host module was loaded
and no performance sample is used for paper timing claims.

The complete unchanged BCH owner, actual vkso exporter/registration and original
benchmark were built and run. The three-backend, two-parameter, 128-trial,
all-error-count, two-decode-mode correctness matrix passed separately in the
same registration session (10,752 checks derived from the unchanged loops).
The resource observer reuses the original C helpers and instantiates one backend
per process, with both m13/t4 and m13/t8 controls/codewords and one active full
context at a time. See [protocol](../../bch-heap-protocol.md) and
[evidence interpretation](../../bch-heap-evidence.md).

## Requested object bytes

All 63 independent loaders agree on these per-process requests; totals are
identical for the native DSO and registered carrier.

| Live state | Allocations | Control/table bytes | Workload bytes | Total requested bytes |
|---|---:|---:|---:|---:|
| Both cases initialized | 30 | 91,344 | 1,044 | 92,388 |
| t4 context live | 33 | 91,344 | 1,586 | 92,930 |
| t8 context live | 33 | 91,344 | 1,614 | 92,958 |

The individual control requests are 41,448 B (t4) and 49,896 B (t8), including
all fourteen persistent allocations per control. The two codewords request
519 and 525 B. The original full-decode preparation also allocates `difference`
even though that mode does not use it. Both active cases use errors=t and the
original trial-0 vector and pass full codeword/error-location verification.

Allocator-usable bytes are separate observations: initialization totals 92,608 B
in both backends; active t4 totals 93,192 B in native and 93,176 B in registered;
active t8 totals 93,208 B in both. Neither usable nor requested totals include
all chunk/arena metadata, retained freed allocations or transient init peaks.
All live inventories are empty after release; this does not prove that the
allocator returned those physical pages to the kernel.

## Physical coverage, with overlaps deduplicated

The following table unions **library, required shim, live requested-allocation
covering pages and whole dedicated-owner core** across each simultaneous cohort.
The native-before-owner role has no owner. Values count distinct resident 4 KiB
PFNs, not object bytes divided by page size. The C observer DSO is separate.

| Controlled role | Observed state | 1 loader | 4 loaders | 16 loaders |
|---|---|---:|---:|---:|
| Native before owner load | Libraries touched; no BCH objects | 7 | 13 | 37 |
| Native before owner load | Controls and codewords initialized | 46 | 169 | 661 |
| Native before owner load | t4 full-decode context live | 47 | 173 | 677 |
| Native before owner load | t8 full-decode context live | 46 | 169 | 661 |
| Native with owner loaded | Libraries touched; no BCH objects | 13 | 19 | 43 |
| Native with owner loaded | Controls and codewords initialized | 52 | 175 | 667 |
| Native with owner loaded | t4 full-decode context live | 53 | 179 | 683 |
| Native with owner loaded | t8 full-decode context live | 52 | 175 | 667 |
| Registered carrier | Libraries touched; no BCH objects | 13 | 25 | 73 |
| Registered carrier | Controls and codewords initialized | 53 | 185 | 713 |
| Registered carrier | t4 full-decode context live | 54 | 189 | 729 |
| Registered carrier | t8 full-decode context live | 55 | 193 | 745 |

These are covering-page counts in the recorded Python/C observation processes,
not exclusive BCH charges or a general application memory difference. Allocation
position, prior allocator activity and unrelated objects sharing a page affect
them. In this cohort, live controls cover 38 PFNs per loader, none shared between
loaders. Control and workload intervals can overlap on the same physical page:
they must not be added independently. Requested heap unions per loader are
39/40/39 pages in native and 40/41/42 pages in registered at initialized/t4/t8.
The requested and usable extents also differ: native t8 usable coverage is
40 pages while requested coverage is 39. All these raw sets are retained.

The registered library/owner intersection is exactly the four declared source
pages (three text and one rodata). Every one of the 21 registered loaders
matches all four after faulting and at each later stage. The complete owner
core remains six pages/24,576 B in the three recorded owner censuses. The
additional observer DSO has 12 pages in a one-loader faulted census and 13 after
initialization; it is recorded separately, not hidden in the selected union.
Manager/process/page-table observations remain separate. Whole-process PFN sets
include generic runtime memory and allocator retention. The only unread whole
VMA range is vsyscall; nonresident pages before the explicit library fault stage
are retained. All explicit targets from faulted onward were resident and read.

## Independent reconstruction and archive

`bch-heap-audit.json` replays all 567 raw process snapshots and 81
role/count/phase groups. It independently checks allocation names and size
formulas, lifetimes, original seeded vectors, raw pagemap/direct-entry agreement,
VMA/layout coverage, overlaps, source PFNs and same-session full correctness.
`bch_heap-coverage.json` supplements it by reading the actual archived ELF and
source bytes: 147 loaded layouts, 504 source-identity reports, 2,016 API symbol
addresses, 23 original build inputs, four original implementation text sections
and three full owner censuses. See [coverage details](COVERAGE.md).

The compact `bch-heap-evidence.tar.gz` preserves the selected original output
layout, raw validation records, actual small source/binary inputs, preparation
commands, replay tools and reference inputs. The local full guest disk and
preparation tree remain intact. Large guest disk/vmlinux and redundant object
files are excluded; selection and archive identity are in
`bch-heap-archive-selection.json`.

```sh
bch_heap_replay=$(mktemp -d /tmp/bch-heap-replay.XXXXXX)
tar -xzf test/evaluation/results/bch-heap-qemu-20260912-attempt01/bch-heap-evidence.tar.gz -C "$bch_heap_replay"
python3 "$bch_heap_replay/observation-tools/bch_heap_audit.py"   "$bch_heap_replay/evidence/validation/bch_heap" --output "$bch_heap_replay/replayed-audit.json"
python3 "$bch_heap_replay/observation-tools/bch_heap_coverage.py"   "$bch_heap_replay" --archived-inputs --report "$bch_heap_replay/replayed-coverage.json"
```

The synthetic auditor corruption tests are tool validation, not experiment rows.
This result extends B's object accounting; full setup, allocator/slab attribution,
transient peaks, registration transactions and owner lifetime remain separate
unfinished requirements. Ordinary controlled owner preloading does not establish
that an original kernel workload needed this dedicated module.
