# Incomplete hex_dump_to_buffer checker-path evidence

Captured at 2026-09-12 06:56:34 UTC from the original live checker. This is a
read-only explanation of an observed static dependency expansion, not a
fourth-candidate result. The eight candidates, checker, Shim list and original
processes were not changed. No second checker, carrier, guest or runtime test
was started.

The interpretation is in
[`../../applicability-semantics.md`](../../applicability-semantics.md).
`verification.json` reports only evidence reconstruction; PASS does not mean
the selected candidate passed the checker or could execute after export.

- `snapshot.json` records the complete local snapshot path, prefix size,
  timestamp and content identity. The full log remains in `/tmp` and is not
  part of this archive.
- `selected-log-lines.txt` contains original ANSI-bearing raw lines with their
  original snapshot line numbers. Context around each path edge is retained.
- `observed-path.json` contains all 44 first-enqueue ancestry edges extracted
  from the complete snapshot. Its event counts describe that snapshot only.
- `excerpt-reconstructed-path.json` independently reconstructs the same path
  from the archived excerpt. Its smaller total enqueue count describes only
  the excerpt and must not replace the complete-snapshot count.
- `selected-elf-edges.json` records eight selected direct transfers in the
  exact119 ELF, with caller body identity, instruction bytes, short windows,
  printable constants and the ELF build ID. This is static image evidence.
- `checker-source-excerpt.txt` and `checker-source-identity.json` preserve the
  relevant traversal rules and confirm that the current source matches the
  campaign-start commit.
- `process-at-snapshot.txt`, `campaign-results.json`, the frozen manifest,
  campaign identity and `effective-shim.txt` preserve the observed run's scope.
  The manifest's initial placeholders are not later candidate verdicts.

To reproduce the path using only the small archived raw excerpt:

```sh
python3 test/evaluation/results/applicability-path-20260912/parse-queue-path.py \
  test/evaluation/results/applicability-path-20260912/selected-log-lines.txt \
  --numbered --output /tmp/hex-dump-path-review.json
```

Omit `--numbered` and supply the complete local snapshot to rederive its full
enqueue-event count. The parser reads text and does not import the checker.
On a machine with the same readable exact119 debug ELF and existing pyelftools
and Capstone, the selected static edges can be checked with:

```sh
python3 test/evaluation/results/applicability-path-20260912/check-selected-elf.py \
  --output /tmp/hex-dump-elf-review.json
```

Neither script loads a module, changes a process, accesses runtime kernel
addresses, or proves feasibility of the entire 44-edge chain.
