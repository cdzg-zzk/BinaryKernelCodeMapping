# Evaluation and test layout

Start with the paper section, rather than a historical benchmark directory.

| Paper section | Entry | Evidence question |
| --- | --- | --- |
| 6.1 Page grafting | [section61](section61/README.md) | Hot, PTE-cold and post-drop execution with identical instructions |
| 6.2 Dependency adaptation | [section62](section62/README.md) | PGOT primitives and copied-routine ablations |
| 6.3 Exported kernel algorithms | [section63](section63/README.md) | Actual LZ4/BCH/XZ exports, user Native/Adapted/VKSO and kernel Stock/Matched/Owner |
| Stateful system case | [Clocktime](test_gettime/vkso-tests/README.md) | Reads, updates, ABI and concurrency |
| Registration / mapping / residency | [evaluation](evaluation/README.md) | Setup, lifetime, PFNs and resource evidence |
| Application integration | [application/setup results](evaluation/results/application-setup/README.md) | Complete LZ4 CLI and deployment workflow |

`test_lz4/`, `test_BCH/` and `test_xz/` hold shared algorithm implementation,
portability and harness components used by export, correctness, application and
kernel experiments. Section 6.3's authoritative experiment entry is
`section63/`; historical run scripts are not interchangeable with its protocol.
`evaluation/` holds shared collectors and older evidence. Result populations
from different protocols are not merged.

## Repository maintenance

Track source, Makefiles, configuration, test logic and concise evidence reports.
Keep generated kernel modules, object files, Python bytecode, fetched corpora,
package builds and raw campaign output local under the corresponding ignored
build/work/results directories. Ignored results are not a backup: preserve formal
archives and their checksums separately before removing any local data.

Clocktime development uses `experiment/vkso-namespace-macrobench`; split changes
into functional commits there. Create another branch/worktree only for a task
that must proceed independently. Do not use a new branch for every test run.
Existing evaluation/manuscript snapshots preserve development state; a commit
alone does not certify target-kernel validation or completed paper evidence.
