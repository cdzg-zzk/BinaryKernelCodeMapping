# Section 6.3 — Exported Kernel Algorithms

Status: complete. All eighteen formal deployments and three loads of each bounded
diagnostic passed their recorded correctness and identity checks. This is the
sole current section 6.3 campaign.

- [Complete findings and analysis](results/report.md), [repetition and PMU findings](results/repeat-bch/findings.md).
- [All results](results/paper-material/tables.md), [raw replay audit](results/analysis/audit.json).
- [English LaTeX](results/paper-material/section63.tex), [figure PDF](results/paper-material/exported_algorithms.pdf).
- [Experiment design](methods.md): questions, version definitions, workload and timing boundaries.
- `scripts/build.py`: Native and Adapted user DSOs with common ordinary user flags.
- `scripts/campaign.py`: all builds followed by nine initial owner deployments, followed by nine BCH repetitions.
- `scripts/collect_user.py`: three user backends and the registered owner's kernel comparison.
- `scripts/analyze.py`: raw-data replay, correctness/binding audits, paired ratios and load ranges.
- `source/linux-5.15.0-119.129/`: original Ubuntu algorithm sources and provenance.
- `results/`: complete raw deployments, binaries, source snapshots, corpus, and generated analysis.

From the repository root, use a new output directory:

```sh
python3 test/section63/scripts/campaign.py prepare --output /path/to/new-results
sudo python3 test/section63/scripts/campaign.py collect --output /path/to/new-results
python3 test/section63/scripts/repeat_bch.py prepare /path/to/new-results
sudo python3 test/section63/scripts/repeat_bch.py collect /path/to/new-results
# Merge the completed follow-up with repeat_bch.py merge, then replay:
python3 test/section63/scripts/repeat_bch.py merge /path/to/new-results
python3 test/section63/scripts/analyze.py /path/to/new-results
```

`collect` requires the research host running `5.15.0-119-generic` with CPU 2
available. Preparation builds the full matrix before measurements begin.
Collection does not change algorithm sources or choose configurations based on
observed speed. Repeated deployments mean owner unload/reload and new carrier
registration within one boot, not independent machines or reboots.

The owners and portability headers remain shared implementation components in
`../test_lz4/`, `../test_BCH/`, and `../test_xz/`. Their historical `run.sh`
interfaces are not the protocol for this new section. Application/setup results
remain separate in `../evaluation/results/application-setup/`.

Rebuild statistics, tables and prose from retained measurements:

```sh
python3 test/section63/scripts/analyze.py test/section63/results
python3 test/section63/scripts/tables.py test/section63/results
python3 test/section63/scripts/write_paper.py test/section63/results
```

Figure generation uses the versions in `scripts/plot-requirements.txt`. Install
these in a project Python environment, then run:

```sh
python3 test/section63/scripts/plot.py test/section63/results
```

Diagnostic collectors are `scripts/diagnose.py` and
`scripts/bch_helper_diagnostic.py`; their sources, commands and raw data are
retained under `results/diagnostics/`. They do not alter the actual owners.

Final checks are recorded in [completion.json](results/validation/completion.json).
To reproduce the completion check, first replay the independent application
records into a temporary directory, then pass that directory to the checker:

```sh
python3 test/evaluation/formal_results.py test/evaluation/results/application-setup/raw --applications-only --output /tmp/vkso-app-replay/analysis
python3 test/evaluation/formal_paper_tables.py /tmp/vkso-app-replay/analysis --applications-only --output /tmp/vkso-app-replay/paper-tables
python3 test/section63/scripts/complete.py test/section63/results --application-replay /tmp/vkso-app-replay
```

`results/source-files/` is the collection-time snapshot. Final analysis and
reproduction tools, including the corrected idempotent helper-summary replay,
are separately archived in `results/reproduction-tools/`; source snapshots are
not overwritten with post-collection edits.

Current main counts are BCH twelve loads, LZ4/XZ three each. The initial
three-load statistics are retained under `results/repeat-bch/original-three-load/`.
The additional diagnostic entry points are `scripts/bch_pmu.py` (same allocated
contexts across three kernel phases per load) and `scripts/bch_user_pmu.py`
(user-only events through actual carriers). Their preparation/collection commands
use `prepare`/`collect` followed by the campaign directory. After collection:

```sh
python3 test/section63/scripts/repeat_summary.py repetitions test/section63/results
python3 test/section63/scripts/repeat_summary.py pmu test/section63/results
python3 test/section63/scripts/repeat_summary.py user_pmu test/section63/results
python3 test/section63/scripts/repeat_report.py test/section63/results
```

Generate the PMU report before `write_paper.py`, which reads its measured facts.
