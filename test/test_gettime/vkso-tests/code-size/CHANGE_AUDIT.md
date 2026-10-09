# Clocktime source modification audit

## 2026-10-09：适配精简与计数边界

本节描述当前工作区的ABI/初始化精简；下文改动账保持性能实验版本 `cf9dc817` 的统计。性能实验文件与其源码、二进制证据未覆盖。当前源码比较采用同一清单并完整计入列明的保留读取/分派：Raw 1,578、原VKSO 1,771、精简VKSO 1,708行。精简净减63行，不把源码行数换算为开发工时。

| 审查对象 | 决定与实际修改 | 保留语义/验证 |
| --- | --- | --- |
| 用户/内核9个ABI结构及版本定义 | 合并到 `include/vkso/time_abi.h`；用户通过符号链接引用，导出包复制头文件内容 | 9个结构、45项布局记录与旧用户ABI一致；真实内核编译通过 |
| 两层初始化的auxv查询 | 检查集中到 `vkso_user_wrapper_init`，并移到carrier访问之前；外层保留 `pthread_once` | 成功和失败路径均只查询一次；错误保留、失败粘滞、并发初始化通过 |
| 公开库与载体入口 | 保留 | 分别负责errno/API语义与地址/上下文绑定；两个对象逐字节不变 |
| 内核入口与动态POSIX分派 | 保留 | root/current视图、返回类型与原生时钟分类各有职责 |
| 私有读取与provider回退 | 保留并纳入成本总量 | 56行必需回退计入保留项；原始主表1,487/1,624不能代表含回退总量 |
| libc与内部布局检查 | 保留接口边界检查 | 编译期检查不进入读取指令；本次不通过删除检查压低行数 |

逐文件净变化：内核原头文件−66，新共用ABI头文件+71，用户ABI头文件−62，一次性初始化−6；wrapper重排与Makefile依赖更新不改变行数。共用头文件定义只计一次，符号链接不形成第二份维护源。初始化查询位置由两处变为一处，9个跨域结构由两份定义变为一份。测试、导出脚本和审计工具不并入原案例源码清单。

验证结果与重现入口：

- [结构化审查、计数与编译比较](adapter-evidence/report.json)
- [布局记录](adapter-evidence/abi-layout.txt)、[公开接口测试](adapter-evidence/public-api.log)、[内核契约测试](adapter-evidence/kernel-contract.log)
- `python3 test/test_gettime/vkso-tests/code-size/audit_adapter_refactor.py`：需要配置好的本地内核对象编译命令，复算同范围增量，重新比较代码并运行接口/契约检查；不启动内核或性能采集。
- `python3 test/test_gettime/vkso-tests/code-size/audit_current.py --check --historical`：核对性能实验版本的存量证据。默认不加 `--historical` 时仍要求源码与实验版本完全一致，防止将新源码误标成旧实验对象。

本地GCC 11.4.0下，公开读取入口和carrier对象逐字节一致；7个真实内核编译单元的可执行节及重定位目标一致。共享算法、MM/namespace代码和发布代码未改动。初始化是本次唯一改变的运行逻辑，其错误及线程行为通过主机测试。现有READ/UPDATE数值仍绑定原实验版本，不将编译一致性描述为新一轮性能测量。


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

- Audited tracked sources: Git `cf9dc817f29f9c8d6f88dde0c58c4ccb75347aeb`.
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

| Category | Added | Deleted | Net | Content |
| --- | ---: | ---: | ---: | --- |
| Shared computation and ABI | 494 | 0 | +494 | `vkso_time_core.c`, cycles/internal helpers, shared ABI, shared getcpu |
| Kernel readers and syscall boundaries | 221 | 182 | +39 | Ordinary readers, dispatch, output conversion, native failure paths |
| State publication | 102 | 14 | +88 | Canonical shared state, sequence publication, timezone, boot offset |
| Per-MM and time namespace | 173 | 57 | +116 | Mapping lifetime, offsets, fork/join and MM hooks |
| Clock providers | 10 | 22 | −12 | TSC/PVClock/Hyper-V declarations and provider hookup |
| User ABI and initialization | 393 | 0 | +393 | Private carrier entry, public library, initialization and headers |
| Build, linking and platform integration | 84 | 65 | +19 | Shared sections, build flags, auxv, alternative thunk placement, configuration |
| **Total** | **1,477** | **340** | **+1,137** | Case-specific source changes |

The shared computation is maintained once and executes from the kernel-resident
pages in both domains. This is a consolidation of execution and maintenance, with
additional adaptation code. The table does not establish a reduction in the total
source size of the feature.

For the paper, the narrow reader claim and the implementation cost should be
reported separately. The 494-line shared category includes computation, ABI
definitions, provider code, and shared getcpu; it is **not** 494 lines of pure
time arithmetic. The +39 kernel-reader net includes syscall boundaries and
private fallbacks, not merely inline adapters. The +393 user category includes
carrier/public entry code, initialization, and headers; it contains no second
cycle-conversion or sequence-retry implementation. State publication (+88) and
MM/namespace support (+116) are real implementation costs but should not be
mislabelled as algorithm duplication. The retained private timekeeper reader
serves exceptional kernel contexts and unsupported providers. Function-level
ownership and call paths are documented in
[`ARCHITECTURE_AUDIT.md`](../revision/kernel-reader/ARCHITECTURE_AUDIT.md).

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

The seven case-specific categories have net **+1,137** source lines. Adding the
native-vDSO withdrawal (net **−1,397**) produces a mechanical net **−260**
against upstream Linux 5.15.198, before the separate compatibility/platform
cleanup, test instrumentation and experiment configuration. The withdrawal
includes native mapping and build machinery serving more than the measured
time/getcpu scope. Therefore −260 describes this selected source diff, not an
equal-function code-size reduction. Conversely, +1,137 describes integration
churn, not the net size of the entire modified kernel tree.

Compared with the previous audited source revision `ff791718`, the only
production-source changes are in `include/linux/vkso_getcpu.h`,
`include/linux/vkso_time.h`, and `kernel/time/timekeeping.c`. They remove 17
noncomment lines net from the kernel-reader category by narrowing fixed-clock
adapters and removing caller-side duplicate fallback branches. The shared core,
user adapter, state publisher, and MM/namespace categories are unchanged. This
is a source-size result; object-code identity and target-machine latency are
separate measurements.

Historical reports used a different, hand-selected functional SLOC inventory
at earlier implementation revisions: the July report counted Raw 1,201 versus
VKSO 1,102 runtime SLOC (−99), while the August report counted Raw 1,505 versus
VKSO 1,305 product SLOC (−200). The July report also found 467 fewer
user-exclusive SLOC after moving calculation into the shared core. These
figures do not measure source diff against upstream, and their manifests
precede the current direct-linked public library and carrier adaptation.
They must not be substituted for a matched-scope count of the present build.

The broad no-vDSO platform removes capabilities beyond the five time/getcpu APIs.
Consequently its source deletion total cannot be described as equal-function code
reduction, nor can it support compatibility claims for 32-bit, UML or SGX users.

## Source revision and performance boundary

The seven audited user files still match the direct-linked public library and
carrier sources used by the current implementation. The three changed kernel
files are classified against the same Linux 5.15.198 baseline. Their diagnostic
ranges are excluded from functional totals. Public compatibility still requires
explicit linking, initialization and successful carrier registration. The old
32-boot campaigns measured earlier source revisions; this audit creates no new
runtime performance result for the current source revision.

## 当前同功能存量与复用证据

本文件记录集成新增/删除。当前 Raw/VKSO 功能源码存量、实际实验包二进制规模、职责图、物理共享和维护案例另见 [current-evidence/README.md](current-evidence/README.md)；两种口径分别报告。
