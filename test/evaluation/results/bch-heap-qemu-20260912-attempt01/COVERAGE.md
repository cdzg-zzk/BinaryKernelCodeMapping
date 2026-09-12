# Actual ELF and source coverage

The independent `test/evaluation/bch_heap_coverage.py` audit passed against
this terminal-PASS guest's actual consumed artifacts. It complements the
raw pagemap/allocation audit; it does not rerun a benchmark or execute an ELF.

```sh
python3 test/evaluation/bch_heap_coverage.py \
  test/evaluation/results/bch-heap-qemu-20260912-attempt01 \
  --report test/evaluation/results/bch-heap-qemu-20260912-attempt01/bch_heap-coverage.json
```

- All 63 loader processes were covered across three roles and N=1/4/16.
  Their 147 loaded-layout records exactly match actual native, observer,
  generated carrier and generated shim ELF PT_LOAD headers and SHF_ALLOC
  section records, using an independent bounded ELF64 parser.
- All 504 non-before probe reports have the four source hashes of the
  actually consumed benchmark, adapted BCH, public header and shim files.
  The recorded compiler macros and copied observer binary agree with those
  inputs. The consumed observer is the frozen C source
  `f9d12c973053a17c97a8d124cfebdf0e4441ce4210762fa197c2ae37d1009cf6`.
- All 2,016 reported API addresses equal the actual ELF symbol value plus
  the recorded ELF load bias. This includes all four actual carrier APIs.
- All 23 original input files copied to the fresh owner/userspace build
  match the copy ledger and original repository sources. The fresh owner,
  original BCH benchmark, native baseline and author baseline `.text`
  sections are each byte-identical to the corresponding original existing
  implementation, despite build-location/debug metadata differences.
- The actual exact119 kernel `bch.h` used by the owner is byte-identical to
  the vendor public header used by the observer and native DSO. Its SHA-256
  is `4ccd9352123676facafc59fa0ee29673be62e8e597e65a495e0bd414f3187c22`.
  The owner's `.bch_impl.o.cmd` names the original complete adapted BCH
  source and this kernel header as compiler dependencies.
- All three system snapshots containing an owner census have the actual
  owner's allocated ELF section list. Each records live state, zero init
  size, 24,576 core bytes, all six requested pages with no missing address,
  and the same six-PFN set. Core includes data/padding/support as well as
  code; transient init storage and external allocations are excluded.

`bch_heap-coverage.json` contains the file ledger, hashes, exact comparison
counts, original `.text` identities, and owner census details. Small
preparation records and the consumed kernel public header are also copied
to `coverage-inputs/` with their own source/destination ledger. Keep the
consumed `payload/helpers/bch_heap_probe_source/`, native/observer/owner
binaries, generated carrier/shim under `evidence/validation/export/`, fresh
`build-source/` inputs including the hidden `kmod/.bch_impl.o.cmd`, and build
logs when archiving these results.

For replay after extraction, use the explicit archived-input mode:

```sh
python3 bch_heap_coverage.py /path/to/extracted-attempt \
  --archived-inputs --report /path/to/new-coverage.json
```

This mode reads only files inside the extracted attempt directory. It uses
the 23 original reference source files, the four original comparison ELFs,
and the original shim source preserved under
`coverage-inputs/reference-repo/`, plus the archived exact119 public header.
`coverage-inputs/path-mapping.json` records 31 original-path to archived-file
bindings with byte sizes and hashes. In particular, the original compiler
argv's observer source and output paths map explicitly to their retained
source/binary bytes. The original argv and provenance files are unchanged;
the reader uses their copies in `observation-preparation/`.

Without `--archived-inputs`, the original external-input checks remain active.
Those read the original repository, sibling preparation paths and installed
kernel header, allowing comparison with the actual preparation environment.
Archive mode verifies every reference mapping's real bytes before applying
the same source, layout, symbol and owner checks. It refuses an unmapped
compiler path or a reference hash mismatch.

Both modes passed. A separate replay copied the 656 required files into a
new temporary extraction root, passed nonexistent repository/preparation
paths, and guarded all audit file opens to reject paths outside that root.
Replay passed; deliberately damaged reference-hash, missing compiler-path
mapping, and external-JSON-symlink cases were rejected before external reads. See
`archived-replay-validation.json`. Compare the reports' `normalized_findings`
objects: these were equal across original, archived and relocated modes.
Full JSON files contain different absolute paths and are not byte-identical.

No assertion here authenticates externally modified ledgers. Pagemap contains
neither object bytes nor allocator-slot contents, so offline coverage checks
do not independently decode those runtime values. The unchanged C observer
performed its allocator binding checks during the recorded guest execution.
