# VKSO Section 6.5 后续优化任务：完整交接 Prompt

你将接手一个已经完成上一轮实现、实验和论文交付的操作系统研究项目。请先读清当前状态，再实际完成下一轮诊断、实现优化、验证、复测和正文更新。

## 1. 当前任务与用户意图

项目是 VKSO，原工作目录为 `/home/zzk/BinaryKernelCodeMapping`。研究在研究者拥有和控制的机器、Linux 内核上进行。仓库 `AGENTS.md` 的规则适用。

Section 6.5 的主问题是：复杂的原生内核实现能否通过同一份驻留机器码服务真实内核消费者和真实用户应用，同时让对象、缓存和环境服务保持各域私有？SquashFS + 实际 Apptainer/SIF 是主案例；ISO9660 是互补功能/调试证据。前面算法小节和 Clocktime 不代替本节的应用证据。

用户最新判断是：**实验规模基本够了，下一阶段应提高实现效果。扩大实际复用范围是正确方向，但不能以其他路径的性能、内存或功能明显退化为代价，不能“拆东墙补西墙”。**

本轮目标，按优先级：

1. 定位并尽量解决公共 XZ 解码导致的应用性能回退，保留真实跨域 XZ 复用。
2. 改善用户桥 inode/name 缓存随访问条目增长的问题，同时保住访问性能和对象生命周期正确性。
3. 有证据时再处理剩余适配开销；沿用已有工作负载和强基线，避免无边界增加实验场景。
4. 对最终候选实际复测，更新 Section 6.5、分析图表、成本记录、主张判断和统一状态。

注意：仓库 `STATUS.md`、`final-evidence.json`、`refinement/progress.json` 的 complete 表示**上一轮评估已完整交付**，不是这次优化目标已经完成。不能读完它们就结束，也不能只提出计划而不实现和执行。

## 2. 如何使用交接包

包根目录的 `START_HERE.md` 给出入口，`BUNDLE_MANIFEST.json` 列出打包文件，`EXTERNAL_ASSETS.json` 列出未随包提供的大型运行资产。`repo/` 下保持原仓库相对路径。包是核心源码/证据包，不是完整的可启动实验环境。

若你在原工作区，直接使用现有资产，并在新目录构建/运行。若只有压缩包，先完成源码与证据分析、诊断脚本准备；具体列出运行时缺失的资产/权限，不能假装完成硬件实验。包内没有密码或凭据；已有授权不等于新环境自动拥有 sudo 凭据。

优先阅读，不要从头遍历全部原始记录：

- `test/section65/STATUS.md`、`claim-experiment-map.md`、`claim-verdicts.json`、`backend-conditions.md`。
- `test/section65/squashfs/refinement/{PROTOCOL.md,README.md,RESULTS.md}`。
- 论文 Introduction/贡献：`paper/paper_content/Paper Draft.md`；Design：`paper/design/`；对齐记录：`paper/notes/section65-alignment.md`。
- 当前正文：`paper/paper_content/sections/06-evaluation.tex` 中的 `Filesystem Reuse in Applications`；独立预览：`paper/filesystem-section-preview.pdf`。
- 当前分析：`test/section65/build/squashfs/refined-analysis-01/{analysis.json,audit.json,summary.csv,costs.json,section65.numbers.json}` 和 `resource-ledger/resources.json`。
- 当前构建/源码冻结：`test/section65/build/squashfs/refine-xz-01`、`evaluation-refined-02/identity.json`。

`.codegraph/` 在原仓库存在，但前一代理反复遇到 CodeGraph 超时并已转用定向搜索。不要为了工具反复重试而阻塞任务；根据实际可用性及仓库规则处理。不要 reset/clean 巨大的已有工作区，不要覆盖历史结果。默认不提交、不推送。

## 3. 必须区分的两个实现版本

### 上一版：公共文件系统 + LZ4，XZ 留在域内服务

生产构建：`test/section65/build/squashfs/evaluation-improved-01/build`。
主要分析：`improvement-analysis-01`；另外还有 xz attribution、loader、singlecpu 三组分析。
共 39 个 campaign、11,328 条计时观测。冻结：`evaluation-improved-03`。
论文归档：`paper/build/section65-composed-publication-01`。

- 原生和 prepared native 的 XZ 由 Linux 5.15.198 的内核解码器提供。
- 用户 copied/VKSO 的 XZ 使用 liblzma；公共核心当时没有包含 XZ 解码器。
- XZ 大文件顺序任务相对默认 SquashFUSE 慢约 5.02%，不是 13.10%。
- 此版共享 7 页、28 KiB。旧版不利的布局/依赖敏感性结果保留。

### 当前版：公共文件系统 + LZ4 + XZ

生产构建：`test/section65/build/squashfs/refine-xz-01`。
测量前冻结：`evaluation-refined-01`；最终源码/正文冻结：`evaluation-refined-02`（318 文件）。
共 30 个完整 campaign、6,540 条计时观测、403 项独立复算的配对比较。

| 测试对象 | 当前 XZ 路径 |
|---|---|
| 原始 native / 优化 normal、relaxed native 参考 | Linux 5.15.198 自带内核 XZ；没有切换成 VKSO owner |
| prepared native | 调用公共 owner 的 `vkso_xz_*`；保留 `XZ_PREALLOC`，BIO 输入和分页输出 |
| copied 用户版 | 执行公共 owner 同指令内容的用户物理副本；用 `XZ_SINGLE` 处理完整压缩块和连续输出 |
| VKSO 用户版 | 与 native owner 共享代码/只读 PFN；同 copied 用户桥及 `XZ_SINGLE` 路径 |
| SquashFUSE 0.6.2 | 自身解析 + liblzma；实际 helper 是 `squashfuse_ll`，保留默认和 `-s` 单线程对照 |
| LKL Linux 6.12 | 自身用户态内核环境中的 SquashFS/XZ；不共享宿主内核 PFN；XZ 使用 PREALLOC |

XZ 来自匹配 Linux 5.15.198 的 `xz_dec_stream.c`、`xz_dec_lzma2.c`、`xz_dec_bcj.c`，2,604 行原始物理源码未改写。分配/释放、内存操作、CRC 等 9 个服务槽各域私有。当前用户桥移除了 liblzma 和 liblz4 依赖。

核心构建脚本：`squashfs/refinement/build_xz.py`；绑定定义：`refinement/xz_services.h`；用户调用：`squashfs/posix_io.c`；对象/缓存：`user_bridge.c`；FUSE：`fuse_frontend.c`。精确评估源码在构建的 `xz-user-source/`，前一版在 `evaluation-improved-01/build/codec-user-source/`。

当前 owner `.text` 为 27,828 字节，上一版为 16,695 字节；共享 7 个代码页 + 2 个只读页，共 36 KiB。不能把源码行数、机器码字节和模块驻留页混为一谈。

## 4. 已完成的数据及其正确解释

以下性能比例均有对应配对统计，具体区间以分析 JSON 为准：

- 最终 native 对同样 bounded-copy 优化的 normal native：fresh scan 点变化 −1.34% 至 +1.29%，archive −1.05% 至 −0.18%；十格最大 CI 上端为 +4.82%。大型 xz/lz4 archive 分别约 −0.14%/−0.13%，区间跨零。
- 新 owner 对上一版 owner，native xz sequential 为 −1.90% [−2.13%, −1.67%]。
- 九个普通非空应用任务的 VKSO/copied 比值 0.9901–1.0056，逐点 CI 总端点 0.9584–1.0255；equal-path xz/lz4 scan/stream 的区间更宽，不能宣称统一 1% 上界或等价。
- 对默认 SquashFUSE：scan 降低 4.42–54.58%，include archive 降低 3.30–19.46%；gzip/lz4 sequential 约快 7%，**xz sequential 慢 13.10% [11.45%,14.78%]**。
- 对单线程 stock：gzip/lz4 archive 反而慢 1.18%/0.89%，scan 点估计接近；xz scan 仍快 53.59%。不能把默认 stock 的线程成本全归成 VKSO 架构收益。
- 独立任务是在真实 gzip/xz SIF 内执行 Python 3.10 标准库 byte compilation，产生 647 个一致文件，不是“编译 XZ 源码”。对默认 stock，gzip 慢 0.68%，**xz 慢 16.18% [15.56%,16.80%]**。
- 普通十二项任务均优于匹配 positive-cache 的 LKL512；但独立 xz 编译比这个 LKL 慢 6.72%。不能说所有应用均优于 LKL。

解码诊断 (`refinement/decoder_controls.py`) 使用同一 final owner：

1. `copied-library`：调用外部 liblzma/liblz4，保留两项依赖；私有服务表仍绑定。
2. `copied-retained`：调用公共解码器，但仍保留两项外部依赖。
3. `copied`：调用公共解码器并移除未使用依赖。

该诊断在 equal-length loader paths 和平衡 padding 条件下运行。xz sequential 从 1→2 增加 14.79% [13.43%,16.16%]，所记录 child CPU time 增加 14.87%；2→3 为 −0.51% [−2.45%,1.47%]。因此已定位到**解码执行选择**，没有定位到具体内循环、调用模式或编译/绑定热点，不能直接宣布“内核 XZ 天生慢”或“PGOT 导致 15%”。

三次单独的元数据工作量回放：stock 默认/单线程都解码 137 块、1,106,363 输出字节；公共 parser 使用库或公共 XZ 都为 76 块、558,231 字节。计数包含挂载启动，不用于正式时间，也不能将不同层 API 重复相加。

## 5. 缓存、成本与加固约束

- 小树 helper PSS：VKSO 7.00–7.04 MiB，默认 stock 14.16–23.95，单线程 stock 11.64–12.85，matched-cache LKL 82.57–82.85。
- 5,866 / 23,464 / 93,856 条目下 VKSO 为 7.02 / 23.43 / 88.89 MiB；最大规模默认/单线程 stock 为 28.52 / 12.91 MiB，LKL 为 500.92 MiB。
- `u_new_inode` 分配 cached inode，`sq_lookup_child` 保留 cached name，`u_inode_noop` 不释放，`sq_close` 在卸载时清理。当前缺少淘汰政策。这个实现选择会增长，不能称为固定小运行时；也不能未验证就称它为泄漏。
- 用户已经明确：通用 `page_cache_replace.ko` 的 **32 KiB 是平台一次性成本，不计入每个文件系统业务的小计**。不要再次征求该前提，也不能据此隐去业务自己的成本。
- owner 68 KiB + native consumer 40 KiB，较匹配 native module 60 KiB 增加 48 KiB。已有 prepared native 驻留时避免一份 36 KiB backing；请求注册元数据 1,264 字节。普通 copied DSO 也在用户进程之间共享，不允许按进程数重复乘代码页。
- 构造/导出/注册按每 campaign 内部阶段求和，中位数 2.698 s，范围 2.696–6.088 s；编译和装载另列。owner 重载/版本变化需重新部署；后续应用可摊销。copied 构造成本不假定为零。
- current prepared code 没有 native 的栈 canary 和外部 indirect/return thunks。PIC build-only probe 可带这些检查，但跨域 GS canary/失败路径/thunk 绑定未实现。`CONFIG_FTRACE=n`，不要声称移除了运行中的 ftrace。不要进一步放松加固来换取好成绩，也不能将 prepared/native 差异都归为间接调用成本。

## 6. 已有功能、维护、调试证据

原始 native / prepared before / copied / shared / prepared after 的五格式 25 次挂载通过；gzip/xz/zstd/lz4/lzo 的内容、目录、链接、声明范围内 xattr 和边界行为有记录。两种用户 backing 各完成 22,032 次边界/随机偏移读取。另有真实 x86 BCJ 链检查。

native xz/LZ4 probe 分别记录公共入口 190/73 次调用。实际 xz SIF 的硬件断点记录参数、可见调用栈，调试后仍有九个共享 PFN。native A、SIF B/C 使用冲突内容并保持私有对象和独立退出；不是吞吐扩展实验。

关键 raw run 位于 `test/evaluation-local/runs/iso9660/`：

- `squash-refine-xz-functional-01`、`squash-refine-xz-guest-01`。
- `squash-refine-xz-execution-01`、`squash-refine-xz-native-calls-01`、`squash-refine-xz-bcj-02`。
- `squash-refine-hardening-02`、`squash-refine-metadata-work-01`、`squash-refine-minimal-deployment-01`。
- `squash-maintenance-02`：已完成已知上游负偏移修复 old/fixed × native/copied/shared；保留目标内核 panic、daemon signal、client errno 等组合分类。不要再把已修正的 maintenance.py 旧故障当作当前任务。
- `maintenance-oneshot-01`：ISO9660 硬件断点、参数、栈和单步，调试前后 PFN 以及后续原生回归。单步证据属于 ISO9660，不要挪用为 XZ 单步。

异常镜像只能进入隔离客体，不能在宿主触发已知 panic。修复需要重建和重新部署；copied 同样获得公共修复，不证明热更新或开发工时下降。

## 7. 下一阶段的具体推进方式

先做有限的 XZ 诊断，使用**现有 SIF 的相同压缩块**，覆盖已有可压缩/伪随机顺序文件，以及独立 Python 任务中的代表性块。不要通过换输入消除退化。

建立可分离的路径：liblzma；普通用户环境中的同源 Linux XZ；prepared copied；prepared shared。明确每格编译选项、SINGLE/PREALLOC 模式、CRC、输入/输出方式和服务绑定，不能把四格当成天然单因素。先匹配能匹配的条件，再逐个改变因素。

观察实际热点、CPU 时间/必要计数、分配/复制/解码工作量、状态初始化与复用。必要时把两个大文件分开观察，但最终完整应用仍报告原任务。仪器化只用于诊断，正式时间使用未插桩版本。

值得检查、**尚未证实是根因**的两个代码点：

- XZ 继承了公共文件系统编译选项，包括 `-fno-jump-tables`；检查这些限制的必要性和机器码影响。
- `memcpy/memmove/memset/memcmp` 统一改为服务指针，可能丢失固定小尺寸操作的编译优化；不能因为以前类似优化有效就未经证据照搬。

若热点在适配边界，修正调用/编译/缓冲策略；若主要在共同算法，允许有机制依据的共同优化，让两域都获益。不能为了声称 2,604 行“原样复用”拒绝合理优化；若改了原始算法，必须更新语义修改和维护成本核算，不再保留“零 body edit”的旧描述。

不要用切回用户 liblzma、保留未执行的 XZ 代码来冒充问题已解决。旧库路径保留作对照；当前目标仍是实际共同执行的 XZ。也不要在用户侧单独启用内核不能合法使用的指令/配置来伪装同一核心优化。

XZ 候选先独立评估，再处理缓存。缓存先定位必要常驻状态和可淘汰状态，考虑减少对象占用、按需分配或有界缓存；维护 open handle、目录、hardlink、查找和 private-state 生命周期。不能仅通过关闭缓存把内存降低后忽略性能回退，也不能无限扩缓存换时间。

每个新增小实验说明：它回答哪项不确定性、为什么旧数据不够、什么结果支持/否定解释。针对一个假说先导验证，失败候选保留；不要不断换布局、输入、采样窗口直至有利。

## 8. 不“拆东墙补西墙”的验收

- 保留实际公共 XZ 执行、同核心 copied 对照、PFN 身份及用户私有服务/状态。
- 同时看 native/copied/shared，不把原生变慢转移为用户收益。
- 检查 xz 元数据、顺序和独立编译，也检查 gzip/lz4 等未执行 XZ 的任务，避免链接布局带来的新退化。
- 同时记录执行时间、CPU、代码/驻留规模、私有内存和部署成本。
- 对通用算法优化，必要时让原生参考也获得同样优化，继续区分一般优化收益与 VKSO 增量。
- 明确工程上可接受的变化和测量精度，再固定确认协议；不把不显著等同于无回退。
- 诊断完成不等于优化完成。继续实现有证据支持的候选并验证；若目标确实不能兼得，给出已执行的候选、原因、可复现取舍和明确需要用户决定的设计问题，不能提前用“这是算法特性”结束。

## 9. 测量与运行纪律

已有 matrix 在 `refinement/formal-queue.json`：native-final 3/2400、native-stream 3/480、application-final 9/3024、heldout 6/288、decoder-diagnostic 6/240、singlecpu 3/108（campaign/观测）。三档资源另行测量。主推断基于三个 campaign 的均值，保存 block 配对与顺序，不把访问次数当独立环境重复。

开发阶段只跑诊断所需小对照；候选稳定后重跑受影响的既有正式矩阵。owner/bridge 变化不能默默复用旧版性能；特别注意未调用新解码器的任务也可能受代码/装载布局影响。无需机械增加新格式、新应用或新机器。

硬件环境为研究者的 Linux 5.15.198 / i7-1165G7；既有 SMT/turbo 关闭、powersave，普通应用 CPU 1–2、native CPU 1，另有 CPU 1 诊断。先确认当前环境，不擅自改变宿主启动配置。正式计时期间不并行编译、QEMU 或其他本任务负载；TCG 仅作功能验证。保留实际配置、二进制、输入和统计版本。

每个 build/run/analysis 用新名称，保留本次 handoff 基线。`campaign_queue.py` 可串行运行；`clone_queue.py` 可复制队列并更换 campaign/output 名称，注意新候选还需修改 build/control 路径。不要直接重跑指向既有输出的队列。

上一轮曾服务重启：前 25 个 campaign 完成，`squash-refine-heldout-gzip-03` 中断留下 28 条样本。已恢复注册、卸载模块，并以同参数完整重跑 `-03-recovery-01`。正式分析只使用完整 campaign；部分记录保留。`formal-queue-01` 的旧 running 不代表活进程。`recover_interrupted.py` 是已执行的一次性恢复脚本，**不要把它当新任务启动脚本再运行**。

## 10. 最终交付与沟通

交付可复现的诊断、修改、构建、功能/维护/PFN 回归、正式结果和成本比较；明确每项变化解决了什么、仍有什么限制。更新 canonical Section 6.5（保留 6.1–6.4），重新生成图表和 PDF、逐项主张判断、README/STATUS 及新版本冻结。旧版 PDF、数据、失败候选不得覆盖。

当前图表脚本 `paper/plot_filesystem_refined.py`，正文生成 `refinement/write_section.py` + `section65-template.tex`，导出 `paper/build_filesystem_section.py`。绘图环境 `paper/build/section65-plot-env-02/venv/bin/python`，PDF 构建 `make -C paper filesystem-section TECTONIC=build/tools/tectonic`。新版本分析脚本/校验器中存在旧计数、页数和版本断言，必要时按新协议明确更新，不要为了通过而关闭校验。

沿用用户要求：源码复用、完整后端效率和物理页共享的独有收益分开解释；没有工时数据不宣称节省工时，没有整机总账不宣称净内存收益。核心维护和优化也惠及 copied 是合理结果，不需要人为让 copied 更差。

请先简短说明你核对出的版本状态、优先诊断假说和第一批有限对照，随后直接推进已授权且可执行的工作。只在方向实质歧义、必要资产缺失或真实权限阻塞时具体询问；不要重复征求已明确的研究范围和平台成本口径。更新简短、讲结果和下一步，不用长篇计划代替执行。
