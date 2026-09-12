# Selected terminal applicability records, 2026-09-12

Captured at **08:02:43 UTC** from the original static campaign. Six of the eight
prospective candidates had terminal records. The controller was live and its
child was checking `rhashtable_insert_slow`; `get_random_bytes` had not started.
The directory name refers to the completed candidate records, not completion
of the entire campaign.

Interpretation: [`../../applicability-semantics.md`](../../applicability-semantics.md).
`terminal-audit.json` PASS means the saved manifests, individual result files
and campaign results agree. It is not a candidate verdict or runtime result.

- `campaign-results.json` and the six `*-result.json` files preserve the
  unmodified records. Their `semantic_classification` placeholders are not
  later source-review conclusions.
- The five small `*-checker.log` files are complete raw logs, including ANSI
  formatting. The full 5,159,573-byte hex log remains at its original path;
  `hex_dump_to_buffer-selected-log-lines.txt` preserves its summary, sample
  failure/analysis-gap records and final verdict with original line numbers.
- `terminal-audit.json` identifies every consumed original log and rederives
  summary counts, exit codes, hard-failure categories and the distinction
  between unanalysable records and distinct affected functions.
- `matrix-at-capture.json` and `process-at-capture.txt` distinguish terminal,
  running and not-started candidates. These sequential observations are not an
  atomic process/filesystem snapshot.
- Effective Shim files, the frozen candidate manifest and campaign identity
  retain the original scope. `checker-verdict-source.txt` and its source
  identity record show count semantics and FAIL/INCOMPLETE/PASS precedence.

The new outcomes are hex FAIL, string escaping FAIL, and sort PASS with five
indirect sites. All eight prospective candidates still lack runtime results
in this batch. The semantic interpretation is in the linked document.

To cross-check currently available terminal records again into a fresh output
directory, without executing any checker:

```sh
python3 test/evaluation/results/applicability-terminal-20260912/capture-terminal.py \
  --output /tmp/applicability-terminal-review
```

The script reads the original campaign, which may have advanced since this
snapshot; a later capture can therefore contain additional terminal records.
It writes only to `--output`. The original logs, checker, candidates and
processes are never changed. No large log is recopied into this archive.
