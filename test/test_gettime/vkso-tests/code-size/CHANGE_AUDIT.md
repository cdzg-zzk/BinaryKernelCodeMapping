# Clocktime source modification audit

This is the current source-change ledger for the direct-linked Raw/VKSO experiment.
The older `source-manifest.tsv` and `incremental-source-manifest.tsv` describe earlier
implementations and are retained as historical evidence, not used for current paper totals.

## Scope and reproduction

```bash
python3 test/test_gettime/vkso-tests/code-size/audit_changes.py --check
python3 -m unittest discover -s test/test_gettime/vkso-tests/code-size -p 'test_audit_changes.py'
```

The default baseline is the cached upstream `linux-5.15.198.tar.xz` in
`baremetal/artifacts/source-cache/`; use `--tarball PATH` to select another copy of
that release. Omitting `--check` regenerates `change-counts.json` and
`change-lines.csv`. No kernel rebuild, boot, or performance collection is needed.

- Audited tracked sources: Git `ff79171885356e05800c6c488679befb03db7f68`.
- Baseline: upstream Linux 5.15.198, not an empty directory and not the first
  repository import of a full kernel file.
- `change-manifest.json` assigns case-specific files and reviewed physical-line
  ranges to categories. Its kernel list covers all 41 kernel files tracked at
  the audited revision, including unchanged files and the experiment defconfig.
- A full on-disk comparison against the release found 57 modified and 53 absent
  upstream files. Some pre-existing no-vDSO edits are outside Git tracking.
  `platform-baseline.json` preserves their 88 file edits as zero-based,
  half-open replacements against the upstream archive. The auditor reconstructs
  them without depending on the mutable ignored source tree.
- `change-lines.csv` records every counted addition/deletion, its source line,
  and category. `change-counts.json` gives file and category totals.

The metric is physical nonblank, noncomment source lines. It includes declarations,
preprocessor directives, braces, assembly labels/directives, and compile-time ABI
assertions. Comments, Kconfig help prose, and formatting-only whitespace changes
are excluded; macros are not expanded. Replacements count as one deletion and
one addition. Counts use Python `SequenceMatcher(autojunk=False)` after explicitly
removing test-only source ranges from the production comparison. These ranges are
counted separately as diagnostic additions. Each file's net count is checked
against the independently counted old/new source lengths.

Build/configuration lines are reported separately from runtime categories. Source
lines measure adaptation size, not engineering hours or instructions executed.
New files can contain refactored Linux algorithms; “added” does not mean invented
from scratch.

## Classified case-specific changes

| Category | Added | Deleted | Content |
| --- | ---: | ---: | --- |
| Shared computation and ABI | 494 | 0 | `vkso_time_core.c`, cycles/internal helpers, shared ABI, shared getcpu |
| Kernel readers and syscall boundaries | 238 | 182 | Ordinary readers, dispatch, output conversion, native failure paths |
| State publication | 102 | 14 | Canonical shared state, sequence publication, timezone, boot offset |
| Per-MM and time namespace | 173 | 57 | Mapping lifetime, offsets, fork/join and MM hooks |
| Clock providers | 10 | 22 | TSC/PVClock/Hyper-V declarations and provider hookup |
| Build, linking and platform integration | 84 | 65 | Shared sections, build flags, auxv, alternative thunk placement, configuration |
| User ABI and initialization | 393 | 0 | Private carrier entry, public library, initialization and headers |
| **Total** | **1,494** | **340** | **Net +1,154 source lines within these categories** |

The shared computation is maintained once and executes from the kernel-resident
pages in both domains. This is a consolidation of execution and maintenance, with
additional adaptation code. The table does not establish a reduction in the total
source size of the feature.

## User-side implementation

All seven source/header files consumed by the current user library/carrier are
included, even though some live under `functional/` and were previously labelled
as tests. The user's application links `libvkso_time.so` and initializes it before
calling the conventional APIs. It does not implement cycle conversion, sequence
snapshot arithmetic, normalization, or namespace offset calculation itself.

| File | Source lines | Role |
| --- | ---: | --- |
| `functional/vkso_user_entry.S` | 112 | Clock classification, syscall failure entry, context binding and tail transfer |
| `functional/vkso_user_wrapper.c` | 61 | ABI assertions and auxv/context initialization |
| `direct-api/vkso_public.c` | 47 | Conventional names, errno conversion and load-time IFUNC resolution |
| `direct-api/vkso_time_init.c` | 35 | One-time initialization |
| `functional/vkso_user_wrapper.h` | 4 | Initialization declaration |
| `functional/vkso_abi.h` | 79 | User-side type and carrier declarations |
| `direct-api/vkso_time.h` | 55 | Public header, assertions and optional explicit-name adapters |
| **Total** | **393** | **255 implementation lines + 138 header lines** |

For context, the original x86-64 vDSO executable implementation slice contains
406 lines: generic time reader 240, x86 cycle/fallback shim 121, time entrypoints
33 and getcpu entry 12. Its exact ranges are in the manifest. This slice excludes
32-bit branches and does not include the separate vDSO state/layout headers,
publisher, or mapping code. The VKSO 393-line inventory includes its user headers
and initialization. **Do not turn 406 versus 393 into a same-scope reduction
percentage.** The directly supported claim is elimination of a separate user
computation body, with the complete current user adaptation cost disclosed.
Common Linux mathematical/provider helpers and the general VKSO exporter,
page-grafting manager and module are shared infrastructure, outside this
case-specific source table. They remain deployment prerequisites.

## Platform and experimental changes kept separate

| Category | Added | Deleted | Interpretation |
| --- | ---: | ---: | --- |
| Additional native-vDSO withdrawal | 21 | 1,418 | Retired native mappings, entries, headers and build machinery |
| Compatibility/platform cleanup | 4 | 1,734 | Includes 32-bit, UML and SGX-related support/selftests |
| Kernel validation and UPDATE diagnosis | 1,213 | 0 | Recorder, probes, synthetic tests and conditional hooks |
| Experiment defconfig | 19 | 0 | Noncomment config settings |

The first two rows are the captured platform edits outside the tracked integration
files. Some corresponding removal hooks inside tracked files belong to their
functional categories above. They are not independent measurements of algorithm
savings. Documentation, ignore patterns and non-source fixture material are listed
but not counted. User tests, collectors, build campaigns, archived data and this
auditor are excluded from feature implementation counts.

The broad no-vDSO platform removes capabilities beyond the five time/getcpu APIs.
Consequently its source deletion total cannot be described as equal-function code
reduction, nor can it support compatibility claims for 32-bit, UML or SGX users.

## Correspondence to the measured implementation

The seven audited user files exactly match reconstruction from the measured
`clocktime-auto-781e311945f1-clean-normal` package's `git_commit=b2408e1` plus its
`source.patch`. The shared production core files and `vkso_time.c` are unchanged
between that base commit and the audit revision; `tk_publish_read_state()` is also
unchanged within `timekeeping.c`. The four later changed tracked
kernel files are the recorder/header, diagnostic Kconfig and diagnostic hooks in
`timekeeping.c`; the added diagnostic ranges are excluded from functional totals.

Performance evidence remains the 32-boot `20260924T065535Z-clocktime-full` campaign.
It supports preserved tested API behavior and mixed performance effects, not a
blanket no-slowdown claim. In normal builds the kernel monotonic/raw readers cost
0.674/1.401 fewer TSC ticks, while the kernel coarse reader costs 2.007 more; the
idle publisher costs 3.05 more ticks/update. Public non-fallback paths have a
4.99% lower equal-weight geometric mean cost, while the seven clock_gettime paths
have a 2.40% higher mean ratio. Public compatibility requires explicit linking,
initialization and successful carrier registration; it is not drop-in deployment
on an arbitrary kernel. Existing formal correctness records provide functional
evidence; this audit does not create new runtime test results.
