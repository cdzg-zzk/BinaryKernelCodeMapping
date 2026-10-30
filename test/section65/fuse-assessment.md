# 文件系统复用可行性评估（2026-10-29）

> 历史阶段记录：本文按当时进展保留了早期判断和单轮结果，不是当前完成状态。
> 当前 SquashFS 维护矩阵已完成，正式多轮测量仍在执行；统一入口见
> [STATUS.md](STATUS.md)，主张、证据缺口和新增对照见
> [research-protocol.md](research-protocol.md)。下文不同版本的数字不混算。

**结论：选定的 Linux 文件系统读取逻辑能够通过 VKSO 在用户态执行，并通过 FUSE 提供实际挂载；普通 GDB 能在处理文件请求时调试仍与内核共享物理页的核心。此结论已有运行证据。**

这证明了用户提出的技术路径，而非仅证明一个解析函数能运行。当前实现是只读 ISO9660，包括所测的 Rock Ridge/Joliet、多段文件、路径、目录、元数据、符号链接和文件数据访问。它尚未证明比 LKL 或直接源码移植更省开发工作，也未实现 SquashFS/Apptainer；二者不能由 ISO9660 成功自动推出。

## 按“先准备内核，再评估收益”的重新评估

后续评估接受一次性内核重构这一前提。评价应分开回答：原生路径受多大影响；准备完成后增加用户态用途需要多少工作；同一驻留实现和物理页共享带来什么可观察收益。不能因为原驱动无法直接导出就否定方向，也不能把一次性准备成本藏进已有代码后只报前端行数。

原生测量包位于 `test/evaluation-local/packages/iso9660-native-20261029`，设计与使用方法见 [native/README.md](native/README.md)。它包含原始内核、编译选项诊断对照、准备后的内核，以及复制核心/VKSO 核心配同一 FUSE 前端五条路径。工作负载是发行 ISO 和 Linux include 文件树上的 GNU find 索引及 GNU tar 打包。当前公共核心改变了部分加固/插桩选项，因此准备后的整体性能不能直接当成服务间接调用的纯成本。

与 benchmark 同一个 raw-normal 5.15.198 启动镜像已在隔离 TCG 环境完成 [预检](../evaluation-local/runs/iso9660/native-kernel-guest-01/run.json)：五条路径共 35 组功能比对通过，20 条正式阶段试运行记录产生，模块卸载完成；VKSO 对照的 5 页全部共享，复制对照的 5 页全部独立。预检计时仅验证收集流程。随后已在 benchmark 本机执行原生测量，结果及原始记录见 [原生分析](native-analysis.json)。

首轮重构在 Linux include 文件树上使 tar 耗时增加 10.90%、find 增加 21.60%，不能视为影响较小。内核采样发现新增的 `memset_erms` 路径占准备后 find 样本约 5.6%，原始路径未达到 0.5% 的报告阈值。固定小尺寸内存操作原本可以内联，改成不透明服务回调会破坏这一优化。因此新增 `--inline-constant-memops`，仅对编译期已知且不超过 128 字节的 memcpy/memset 使用编译器 builtin，动态长度仍走原有服务；实际公共对象的未定义符号仍只有 `iso_support`。

这一版本在相同协议的独立原生轮次中，把相对同期原始驱动的 tar 增量降到 2.33% [1.45%, 3.81%]，find 降到 2.91% [2.16%, 3.65%]。随后添加 `--keep-private-helpers`，使 13 个原本为 static、且两侧消费者不直接调用的函数继续保持私有，避免不必要的导出妨碍编译优化。最终轮次的结果如下：

| Linux include 文件树任务 | 初版重构/同期原始内核 | 保留小内存操作优化 | 再保留私有函数 | 最终 VKSO/FUSE 相对同指令复制/FUSE |
|---|---:|---:|---:|---:|
| tar 归档 | +10.90% | +2.33% | **+0.99% [0.54%, 1.43%]** | +0.23% [0.11%, 0.34%] |
| find 索引 | +21.60% | +2.91% | **+2.47% [2.24%, 2.73%]** | +0.31% [0.09%, 0.55%] |

方括号为按八个 block 重采样的描述性 95% 区间；每个 block 内三次新挂载取中位数。三个探索性轮次各保留全部 480 条正式观测及 35 组功能比对，未把不同轮次的绝对时间直接相除。Alpine 的最终 tar 增量为 +0.46% [-0.19%, 1.24%]，其短 find 任务波动较大（+5.37% [-0.60%, 14.99%]），不作为性能等价证据。该研究配置下的结果支持“准备后的所测原生路径增量较小”，不支持“VKSO 普遍加速”。编译加固选项差异仍是前述明确限制。

完整 FUSE 路径也有明显成本：最终 include 树 tar 的原生中位数约 216 ms，VKSO/FUSE 约 1040 ms；find 分别约 116 ms 与 408 ms。这里包括 FUSE 往返、不同缓存和用户态适配，不是共享页机制本身的差异。应将此路径定位为复用与调试的用户态用途，不能宣传比原生内核文件系统更快。

另外，已完成真实上游修复对应的双路径维护案例：旧 Joliet 实现将 300 字节文件名长度截为 44，完整名称查找失败；应用上游提交 `b8253bcf92d6365b20eea6465f5a93c9fc4aa029` 的兼容回移后，真实内核挂载、VKSO/FUSE 和复制/FUSE 都返回完整名称及 73 字节正确内容，继续使用原有桥接库及前端二进制。[完整维护运行](../evaluation-local/runs/iso9660/maintenance-oneshot-01/run.json)、[回移记录](build/maintenance/backport.json)。这是部分现有镜像工具支持的长 Joliet 扩展场景，超过标准 64 个 UTF-16 单元的范围；不能把它描述成所有普通 Joliet 镜像都会触发。六组功能回归、共享页硬件断点与单步、随后内核读取及最终解除注册也通过。此维护实验基于 Ubuntu 119 ABI 的功能构建，没有测量修复版本的原生性能或在线替换。普通共享源码库也可获得单点修复收益，这项案例支持维护路径可行，不能单独证明 VKSO 比共享库更省开发成本。

## 本次实际实现与证据

```text
内核挂载 → vkso_isofs 的 VFS 适配 ──┐
                                  ├→ vkso_iso_core 的公共指令页
应用读文件 → FUSE → 用户态适配 ────┘
```

公共代码来自 Linux 5.15.198；模块按 Ubuntu 5.15.0-119-generic ABI 编译。用户态对象、inode 缓存和读取缓冲区由进程持有，服务绑定表也是进程私有。没有让用户进程访问实际内核挂载的 inode、锁或缓存，也没有在用户态启动通用 VFS、调度器或块设备栈。仍然需要明确的服务适配层，不能描述成“完全不需要兼容工作”。

新增前端 [fuse_frontend.c](fuse_frontend.c) 把 FUSE 的 getattr、readdir、open、read、readlink 请求接到已有用户态适配 API，没有新增 ISO9660 格式解析实现。两条路径均使用经过必要准备的公共核心；这不等于零修改映射任意现有内核驱动。

主要运行：[fuse-export-01/run.json](../evaluation-local/runs/iso9660/fuse-export-01/run.json)。这是隔离的 QEMU TCG 功能实验，不能用于原生性能结论。

| 检验 | 实际结果 | 证据 |
|---|---|---|
| VKSO + FUSE 挂载读取 | 六组案例、200 个目录项，与原始内核参考结果一致 | [挂载结果](../evaluation-local/runs/iso9660/fuse-export-01/evidence/fuse-vkso/result.json) |
| 同布局复制核心 + 同一 FUSE 前端 | 同样六组案例全部一致 | [复制对照](../evaluation-local/runs/iso9660/fuse-export-01/evidence/fuse-copied/result.json) |
| 文件操作 | 145 个普通文件的完整内容，以及 870 次偏移/EOF 读取一致；六次写入均被只读挂载拒绝 | 上述两份挂载结果及各案例 manifest |
| 共享页来源 | 六个 VKSO 挂载进程分别观测到 4 个代码页、1 个常量页与内核 PFN 相同，用户映射不可写 | `evidence/fuse-vkso/pfns-0.json` 至 `pfns-5.json` |
| 普通工具使用挂载点 | 未修改的 tar 归档真实 Alpine 镜像，解包后普通文件内容、路径、链接目标一致 | 上述结果的 archive 字段及 `alpine.tar` |
| 用户态调试 | GDB 硬件断点进入 `isofs_get_blocks`，读出 inode 大小 65537、逻辑块号 0，显示源码位置和调用栈，并成功单步 | [调试结果](../evaluation-local/runs/iso9660/fuse-export-01/evidence/debug/result.json) |
| 调试期间仍共享 | 单步前后所有 5 个页的用户/内核 PFN 相同 | [单步前](../evaluation-local/runs/iso9660/fuse-export-01/evidence/debug/pfns-before-step.json)、[单步后](../evaluation-local/runs/iso9660/fuse-export-01/evidence/debug/pfns-after-step.json) |
| 调试后继续使用 | 被调试的 FUSE 读取完成，随后真实内核挂载再次通过六组案例；解除注册和模块卸载正常完成 | [内核回归](../evaluation-local/runs/iso9660/fuse-export-01/evidence/kernel-after-debug/result.json)、[最终状态](../evaluation-local/runs/iso9660/fuse-export-01/evidence/result.json) |

调试调用栈确实包含 `FUSE → iso_read → iso_read_inode_data → isofs_get_blocks`，不是直接调用一个算法函数的独立测试程序。硬件断点不改写共享指令；公共函数的 DWARF 来自实际 owner 模块，通过用户映射地址重新定位。[GDB 硬件断点说明](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Breaks.html)

另有宿主机复制版 FUSE 预检 [fuse-host-01](../evaluation-local/runs/iso9660/fuse-host-01/result.json)，它只用于前端功能检查，没有当成 VKSO 共享页结果。

## 开发成本与能支持的论点

此前核心适配的 [完整成本记录](../evaluation-local/runs/iso9660/costs-01.json) 描述初版实现：

- 28 个 isofs 函数、原始 2092 行被组织进公共核心；另有 3 个 NLS 辅助函数、122 行。四个函数有主体边界调整，机械移动与实质修改分开记录。
- 29 个服务绑定；用户态桥接 251 行；生成的内核支持、owner 元数据、类型声明、重映射和用户绑定合计 293 行；原内核函数中的 wrapper 也属于适配。
- 适配生成与用户构建脚本合计 386 行。
- 本次额外的 FUSE 前端为 169 行，`build_fuse.py` 为构建支持。检查脚本、QEMU 编排和 GDB 自动化另计，均保留在仓库中。以上行数含空行和注释，不能直接换算成开发时间。

完成 LKL 对齐和名称缓存后，当前用户桥接为 299 行（比初版增加 48 行，包含可选缓存及统计），FUSE 前端为 197 行（增加 28 行，包含文件句柄处理、选项和可选退出统计）。公共核心和 29 个服务没有因这次缓存而修改；缓存占用另见配对测量。不能沿用初版行数描述最终适配成本。

所以目前可支持的论点是：**在完成服务边界适配后，能够保留同一份核心实现，通过较薄的 FUSE 前端供应用使用，并在用户态检查这份实际驻留实现。** 不能只展示 169 行前端就宣称“整个文件系统只需 169 行适配”。

普通源码移植也能避免重写算法，LKL 已提供 [lklfuse](https://github.com/lkl/linux/blob/master/tools/lkl/lklfuse.c)，[Bento](https://www.usenix.org/conference/fast21/presentation/miller) 也支持文件系统用户态调试。因此“可调试”和“避免重写”本身不是 VKSO 独有优势。LKL 的完整任务比较现已执行，见下节；未运行 Bento 性能对照，也未测量人的调试效率。

当前仅共享 20 KiB 指令/常量页，不能把它说成整个部署的净内存节省。此前已观察到模块拆分、注册和管理进程的额外成本，见 [原成本评估](assessment.md)。FUSE 请求、缓存、用户态适配也有成本；与 LKL 的实际速度差异取决于任务，不能宣称普遍加速。

后续 raw-normal 镜像预检进一步区分了资源口径：原始驱动的模块报告大小为 48 KiB，初版准备后的 owner 与内核驱动合计 68 KiB，注册模块另占 32 KiB；20 KiB 去重本身不足以抵消这些增量。PFN reader 是测量工具，单列而不算作应用依赖。`--hold` 管理进程在该次预检中 RSS 为 1748 KiB，但它不是必需的常驻服务：维护运行已验证 `replace` 完成后退出，期间没有存活的 manager 进程，共享读取、两个并发进程的独立状态、FUSE 和调试均正常；最后由新进程执行 `restore`，页恢复及模块卸载成功。该模式取消了可选管理进程的常驻成本，仍不等于整个部署已经节省内存。详细数值与证据路径在 [重新评估记录](reassessment-evidence.json)。

## 与 LKL 的完整任务比较

LKL 的自然对照是现成的 `lklfuse`：让相同镜像经 FUSE 挂载，再执行同一套目录索引、文件读取与 GNU tar 任务。它已经提供用户态 Linux 文件系统路径，所以不能把“无须重写 ISO 算法”或“FUSE 前端代码较少”写成 VKSO 独有的优势，也不能用支持写入、xattr 等更多功能的整个前端行数与本只读前端直接比较。[锁定版本的 lklfuse 源码](https://github.com/lkl/linux/blob/d0f76a77e8c2ca68bd7d96190b8da09040eab072/tools/lkl/lklfuse.c)

源码核对发现三个必须处理的差异。该版本基于 Linux 6.12，ISO 原型基于 5.15.198；跨版本结果应解释为完整方案的比较，不能替代已有同指令复制对照。其默认配置未启用 ISO9660，运行前必须显式加入对应文件系统与 Joliet/zisofs 选项。其 FUSE 初始化把 entry、attribute 和 negative cache timeout 设为零，而当前 ISO 前端保留 libfuse 默认值；对比前应对齐缓存、inode 呈现与请求路径策略，并重新核对功能。LKL 的默认 `mb=64` 是可调整的内存配置，不是已测得的 RSS，也不是不可降低的固有开销。既需报告默认配置，也应寻找通过完整任务的较小配置，按实际驻留资源比较。[默认内核配置](https://github.com/lkl/linux/blob/d0f76a77e8c2ca68bd7d96190b8da09040eab072/arch/lkl/configs/defconfig)、[内核版本](https://github.com/lkl/linux/blob/d0f76a77e8c2ca68bd7d96190b8da09040eab072/Makefile)

固定版本源码现已通过官方 Linux 6.12 归档和跨仓库差异重建，并核对 Git tree。未用于本机 POSIX 构建的外平台工具二进制及 fuzz 种子单列为缺失，不影响所用构建输入。构建过程没有修改 LKL 的文件系统实现或 lklfuse 程序。[源码与构建记录](lkl/README.md)。

### LKL 同任务实测：名称缓存优化前

[正式运行](../evaluation-local/runs/iso9660/lkl-comparison-native-01/result.json) 完成七条路径、49 组正确性比对和 672 条正式观测。[审计后的数据](lkl-analysis.json) 保留所有配对比值、区间、耗时与进程资源记录。除了原生内核、复制/FUSE、VKSO/FUSE，还包括 LKL 默认构建的 64 MiB 配置，以及精简构建的 64、16、8 MiB 配置。精简版移除了不需要的文件系统、IP 协议栈和 NLS 表，保留原宿主库链接所需的 socket ABI；8 MiB 通过完整任务，4 MiB 在 LKL 进程内启动时发生 OOM，未进入正式计时。这里的 8 MiB 是已测试且通过的设置，不是证明了所有 LKL 配置的理论最小值。

本轮两侧均使用单线程 FUSE、真实 inode 号、零 entry/attribute/negative timeout，以及打开后的 inode/file handle。ISO 前端因此由初版 169 行变为 190 行；历史原生测量包保留旧前端，没有把两套配置混算。下表为正式观测的任务耗时中位数，启动时间单列：

| 任务 | 原生内核 | VKSO/FUSE | LKL 默认构建、64 MiB | LKL 精简构建、8 MiB |
|---|---:|---:|---:|---:|
| Alpine tar | 47.17 ms | 112.92 ms | 132.17 ms | 152.11 ms |
| Alpine find | 3.84 ms | 6.68 ms | 5.85 ms | 5.91 ms |
| include 树 tar | 214.46 ms | 1924.02 ms | 1039.98 ms | 1063.06 ms |
| include 树 find | 116.43 ms | 721.01 ms | 281.77 ms | 288.38 ms |

VKSO 的挂载就绪中位数约 7–8 ms；精简 LKL 约 98–101 ms，默认 LKL 约 141 ms。就绪定义包含一次完成的根目录 getattr，避免把 LKL 创建 FUSE 挂载点但尚未启动内部内核的时刻误算为可用。

任务完成后的进程 RSS 来自 `smaps_rollup`：Alpine tar 的 VKSO 为 2.40 MiB，精简 LKL/8 MiB 为 16.02 MiB，默认 LKL/64 MiB 为 70.64 MiB；include 树 tar 分别为 7.14、17.06、69.75 MiB。这些是用户态服务进程的快照，既不是配置参数，也不是整个系统的净内存差。`VmHWM` 的异步计数与精确 RSS 快照出现差异，单列记录而不当成精确峰值。

这轮实测支持较低的服务进程驻留量和较短的挂载启动时间，同时暴露大量小文件任务上的明显速度代价。复制核心/FUSE 与 VKSO/FUSE 在 include 树任务上基本一致，不能把这一退化归给共享页机制。随后用同轮消融验证了名称缓存的影响，见下节；优化前记录保留。LKL 使用现成前端且无需改动 ISO 解析代码，因此本次并未证明 VKSO 比 LKL 更省首次开发工作。

### 名称缓存与最终同任务对照

[缓存消融运行](../evaluation-local/runs/iso9660/lkl-namecache-native-01/result.json) 完成八条路径、56 组正确性比对和 768 条正式观测，并恢复共享页、卸载所有测试模块。[审计数据](lkl-namecache-analysis.json) 单列本轮结果。公共核心、LKL 二进制和前述 FUSE 设置不变；复制/FUSE 与 VKSO/FUSE 使用相同缓存桥接，同时增加 VKSO 无缓存路径作为配对对照。

缓存按每个只读 image handle 保存成功的 `(父 inode, 原始名称字节)` 查找，未命中仍调用原来的 `isofs_lookup`。这避免反复扫描相同路径组件，不重写 ISO 目录格式。它仅适用于当前不可变镜像、单线程句柄，随句柄关闭释放；没有实现通用回收策略。

| 任务 | 原生内核 | VKSO 无名称缓存 | VKSO 名称缓存 | LKL 默认、64 MiB | LKL 精简、8 MiB |
|---|---:|---:|---:|---:|---:|
| Alpine tar | 47.24 ms | 113.75 ms | 110.60 ms | 132.64 ms | 150.60 ms |
| Alpine find | 3.75 ms | 6.72 ms | 5.54 ms | 5.85 ms | 5.81 ms |
| include 树 tar | 215.67 ms | 1925.88 ms | 616.38 ms | 1040.29 ms | 1068.01 ms |
| include 树 find | 116.39 ms | 723.13 ms | 336.50 ms | 280.26 ms | 286.95 ms |

表格是任务耗时中位数；结论使用八个随机区组内的配对比值。缓存使 include 归档耗时降低 67.93%（95% 描述性 bootstrap 区间 67.85%–68.00%），扫描降低 53.58%（53.26%–53.92%）。归档的 94,199 次路径组件查找中有 88,334 次命中，缓存 5,865 项。归档后的 RSS 从无缓存的 7.14 MiB 增至 7.34 MiB，约增加 0.20 MiB；这项额外适配和状态成本应计入方案。

与精简 LKL/8 MiB 相比，VKSO include 归档耗时降低 **42.23%**（41.57%–42.82%），扫描耗时仍增加 **16.83%**（16.03%–17.70%）。默认 LKL/64 MiB 的对应差异为归档降低 40.64%、扫描增加 19.75%；精简 16/64 MiB 的完整结果也保留，不能只选最有利设置。挂载就绪约 7 ms 对约 100 ms；include 归档后服务进程 RSS 为 7.34 MiB 对 17.11 MiB。

与同代码复制/FUSE 比较，VKSO include 归档的配对耗时差为 +0.02%（−0.28%–+0.30%），扫描为 +1.03%（+0.39%–+1.68%）。因此可支持的论点是：**准备后的同一内核核心可以通过较小的用户运行环境完成完整任务，保持接近复制实现的执行成本，并在本组任务中较 LKL 更快启动、占用较少进程内存；任务速度有得有失。** 名称缓存、对 LKL 的归档加速均不是共享页机制独有的收益；原生内核仍明显更快。首次开发成本优势、整机净内存节省和实际容器收益仍需分别验证。

## 适用边界

- 当前前端强制单线程，因为一个 image handle 的 inode 缓存没有跨线程同步。多个进程有独立状态，但尚未验证多线程 FUSE 服务。GDB 日志提示缺少匹配的 libthread_db，也不能据此宣称线程调试已验证。
- 所测只读配置不含用户态 zisofs 解压、写入、设备文件操作、完整挂载选项和通用缓存回收。inode 身份、xattr 等未测语义不包含在本次完整性结论中。
- 用户态调试覆盖公共解析/映射逻辑；VFS 集成、内核锁竞争、块 I/O 等仍须在内核路径测试。
- 当前已验证硬件断点、参数、回溯和指令单步，没有验证任意软件断点、ASan 插桩或不停机替换公共核心。
- 已完成已知上游缺陷的复现、修复回移和双路径回归；GDB 另行验证正常读取时的共享代码调试。没有计量开发者定位该缺陷的时间，也不能写成用 GDB 独立发现了这个已知问题。

## SquashFS 与实际容器应用：有具体接入点，但需要进一步实现

选定的实际候选是 Apptainer 的 SIF/SquashFS 镜像挂载。已检查 [Apptainer v1.5.5 的镜像驱动](https://github.com/apptainer/apptainer/blob/v1.5.5/internal/pkg/image/driver/imagedriver.go)：它会选择 `squashfuse_ll`/`squashfuse`，并向后端传递源文件/文件描述符、目标挂载点、只读选项、UID/GID，以及 SIF 内部文件系统分区的 offset。这是现有业务接入点，不是为 VKSO 虚构的新调用需求。

由此得到明确的应用要求：后端要支持容器实际镜像中的压缩、fragment、稀疏块、目录和链接；支持分区偏移及文件描述符输入；满足挂载生命周期和身份语义；最后实际启动镜像里的程序。只运行一段解压算法或只读元数据不满足这个应用目标。

对本机 Linux 5.15.198 的 `fs/squashfs` 进行了源码边界检查，结论如下。后续已实现公共核心、原生消费者和用户态 VKSO/FUSE，并完成下述功能与共享页验证；Apptainer 执行与首轮原生性能测量也已完成，应用性能对比也已完成，维护验证仍待完成。

| 边界 | 当前源码中的依赖 | 可行的改造方向 | 必须确认的代价 |
|---|---|---|---|
| 初始化与 inode | `super.c:squashfs_fill_super`、`inode.c:squashfs_read_inode` 混合格式处理、VFS 对象和操作表安装 | 公共格式处理，两侧分别创建对象并安装操作 | 所需 inode 类型、配置和错误语义是否完整保留 |
| 目录与查找 | `namei.c:squashfs_lookup`、`dir.c:squashfs_readdir` 使用元数据读取、iget/dentry、dir_context | 保留公共目录解析，显式绑定 inode 查找与目录输出服务 | 适配层不能重新实现目录格式 |
| 元数据/数据读取 | `block.c:squashfs_read_data` 直接操作 bio、页和块设备；部分错误路径使用内核 panic 策略 | 将字节 I/O、输入片段访问和外层错误策略与格式核心分开 | 不能靠额外线性拷贝把成本转移到原生内核路径 |
| 缓存与同步 | `cache.c` 使用 spinlock/waitqueue；元数据索引及解压流也有 mutex | 缓存按域持有，以服务接口提供查找、持有和释放 | 只读文件系统仍有可变执行状态，不能删除同步后宣称支持并发 |
| 文件内容 | `file.c:read_blocklist` 与 `squashfs_readpage`、页缓存和输出页组织相连 | 公共块定位/fragment 处理，两侧提供输出缓冲区或页接口 | 完整数据路径和原生 page-cache 行为必须回归 |
| 解压 | wrapper 同时依赖解压实现、bio 输入及 page_actor 输出 | 复用解压核心，显式绑定输入/输出和私有 workspace | 与仅替换解压库区分，核算所有包装和缓冲区开销 |

这些依赖可以描述为有限的服务边界，源码中尚未发现必须在用户态启动整个 Linux 调度器/VFS 才能完成选定读取任务的要求。**原生服务接口已实现，但用户态绑定、完整运行闭包和性能仍未验证，不能把这个判断写成“SquashFS 已低成本导出”。** 尤其不能将“镜像只读”误解为“不需要处理 kernel state”。

进一步检查实际 native SDK 编译产物：当前配置的 22 个 SquashFS 对象合计仍有 97 个来自子系统外部的未定义符号，包括 `current_task`、`pv_ops`、`vmemmap_base`、bio、页缓存、锁和调度服务，而非只有解压函数。[对象依赖记录](build/scenario-audit/squashfs-dependencies.json)。这个数字是整个已编译驱动的外部符号集合，不是最终公共核心需要的服务数，也不包含所有内联状态访问。它说明下一步应先划分 I/O、缓存、inode 安装及解压 workspace 的域边界，不能直接照搬 ISO 的导出列表。

目前已完成这一边界的第一版实现：[SquashFS 准备代码与记录](squashfs/README.md)。34 个函数、原始 2103 行进入公共核心，通过 46 个服务和 10 个操作表字段绑定原生环境；两处函数主体直接调整，其他依赖通过重映射处理，全部都需计入适配成本。编译后的公共对象仅剩 `sq_support` 这一未定义符号。原生消费者仍使用原 BIO、解压器、缓存锁和页缓存，已在 [功能运行](../evaluation-local/runs/iso9660/squash-native-guest-03/run.json) 中与原始内核完成 gzip/xz/zstd/lz4/lzo 五种格式的十次实际挂载、完整文件与元数据比对，硬链接、xattr、UID/GID 也一致；测试模块成功卸载。用户适配另包含 369 行 bridge、87 行字节 I/O/解压库适配和 221 行 FUSE 前端；这还不包含生成器、构建脚本和内核侧改造，不能仅凭公共函数的两处主体修改宣称开发成本很低。

[共享功能运行](../evaluation-local/runs/iso9660/squash-export-04/run.json) 已通过：VKSO 与相同指令的复制对照各完成六次挂载、22032 次边界/随机读取，包括五种压缩格式与文件描述符加非零分区偏移。每种压缩格式均验证 6 页、24 KiB 的 text/rodata 与内核物理页相同；复制对照不共享这些页。共享前后各五次原生挂载结果一致，退出注册进程后仍可运行，最后恢复载体并卸载全部测试模块。这一轮只提供功能证据；后续容器执行与原生开销见下文。普通解压库并非共享的内核算法；共用的是文件系统格式、块定位、元数据及选项解析。

目标内核配置为 `CONFIG_SQUASHFS=y`。已构建的 `vksosquash` 原生消费者调用准备后的公共核心；这一路径已实际挂载读取，owner 并非仅加载后闲置。管理员准备/注册导出也是部署成本，不能把已有 FUSE 的普通用户安装便利直接归给 VKSO。

建议继续的候选是 SquashFS/Apptainer，但进入正式论文实验前应完成：

1. 实现包含目录、文件定位和完整压缩读取的公共核心与两侧适配，保留真实内核消费者；记下全部改造，若服务适配已接近移植整个运行环境，应重新判断投入价值。
2. 在同一完整任务上比较原生内核、现有 SquashFUSE、LKL FUSE，以及同一重构核心的复制版/VKSO 版。SquashFUSE 是应用现状，LKL 是合理的整体复用方案，复制版用于分离重构与物理共享的影响。
3. 完成一个实际格式变化或真实缺陷的两侧维护案例，并运行 Apptainer 的真实容器任务；再决定开发工作证据和应用性能是否足以补充 evaluation。

**本轮评估决定：继续保留文件系统方向，技术可行性已获实际支持；不要把现有 ISO/FUSE 结果直接包装成容器收益或开发效率优势。SquashFS 已完成公共核心导出、两侧读取和真实 Apptainer 执行，首轮原生开销较小但存在目录扫描成本；与既有后端的应用性能比较已有结果，维护案例仍待执行。**

## SquashFS/Apptainer 实际接入与首轮原生代价

[实际共享应用运行](../evaluation-local/runs/iso9660/squash-apptainer-shared-02/result.json) 已完成。未修改 Apptainer 1.5.5 和 GNU tar，通过其现有 helper 边界使用 VKSO/FUSE 挂载真实 SIF。输入为 `/proc/self/fd/3`，分区偏移为 36864；容器内归档 Linux include 树的 5866 个条目，与原有 SquashFUSE 0.6.2 逐项内容和元数据相同。应用挂载期间六页、24 KiB 的共享身份得到核验，结束后恢复载体并卸载模块。原始内核和准备后消费者也读取了同一 SIF 的 6182 个根文件系统条目，结果一致。首次接入采用 Python 参数转换 helper；下面的对照实验确认其启动开销后，当前版本改为 96 行 C 转换程序，全部启动成本均计入端到端时间。

[原生开销运行](../evaluation-local/runs/iso9660/squash-native-cost-01/result.json) 在真实硬件上完成八个随机顺序配对块、96 次输出一致的测量。对同一个 gzip SIF，准备后归档耗时的配对变化为首次挂载后 +0.29%（95% 块 bootstrap 区间 +0.02% 至 +0.61%）、热缓存 +0.89%（+0.17% 至 +2.14%）；目录扫描首次为 +4.28%（+2.60% 至 +5.89%），热缓存 +0.80%（−3.49% 至 +6.87%）。首次扫描有可见开销；热扫描数据还不能分辨较小差异。这是单次启动、单种压缩镜像和两种文件系统任务，不能扩展成所有配置的性能结论，也不是 VKSO 与 SquashFUSE 的应用性能比较。

实际应用闭环和原生改造代价已有证据。完整启动/执行/内存对比也已完成，见下文；真实维护案例仍需执行。“能够接入 Apptainer”本身不能证明低开发成本或性能优势。

## SquashFS 应用对比结果

[第二轮完整运行](../evaluation-local/runs/iso9660/squash-apptainer-comparison-02/result.json) 包含六个后端、八个配对块、192 次测量。使用同一 gzip SIF，归档 5866 个条目；每次都重新启动容器，并验证归档内容。VKSO 总归档耗时中位数为 914.66 ms，原有 SquashFUSE 0.6.2 为 961.93 ms，LKL/16 MiB 为 3450.88 ms，LKL/64 MiB 为 2388.55 ms。配对块计算的变化分别为 −4.80%、−73.15%、−61.90%。空任务完整启动相对 SquashFUSE 为 +2.91%，并非所有指标都占优。

归档后单次 helper 进程 RSS 快照为 VKSO 9.16 MiB、SquashFUSE 16.10 MiB、LKL/16 为 25.09 MiB、LKL/64 为 62.12 MiB。这不是整机净内存或精确峰值；准备后的内核模块和注册成本需另算。复制版归档为 919.83 ms，与共享版配对差为 −0.54%；因此不能把相对 LKL 的主要收益解释为物理共享本身的加速。

[第一轮运行](../evaluation-local/runs/iso9660/squash-apptainer-comparison-01/result.json) 保留 Python 转换层：VKSO 比原有 SquashFUSE 慢 7.38%，但仅把 SquashFUSE 包进同一转换层就会慢 12.12%。第二轮将转换层改为 C，仍保留相同转换层的 SquashFUSE 对照，其结果与原有后端接近。两轮共 384 次测量及其配对区间见 [核验汇总](squashfs-application-analysis.json)。计时包括共同的 runuser/taskset 启动器、容器启动、任务执行和清理；内存另行采样。

LKL 使用相同的完整 SIF 任务。它的内核/文件系统源码保持不变，另编译的前端增加 30 行 offset 支持，通过既有 POSIX 磁盘回调处理 SIF 分区。VKSO 当前用户 bridge、字节 I/O、FUSE 前端及 C 转换器共 773 行，另有内核准备和生成器；现有证据不支持首次适配比 LKL 更省代码或人工。较有力的结果是：准备后的内核格式核心能直接支撑真实应用，用户运行环境更小、完整任务性能有竞争力，且实际物理共享开销接近复制实现。

## 复现

前置条件是 [README](README.md) 中的 ISO 核心、参考结果、内核和 initrd。本次另使用 libfuse3 3.10.5、GDB 12.1，以及从 `libfuse3-dev_3.10.5-1build1_amd64.deb` 解出的头文件，头文件目录为 `build/fuse-deps/usr/include/fuse3`。开发包仅下载解压到项目，没有系统安装。

```sh
python3 test/section65/build_fuse.py
python3 test/section65/reference_qemu.py --export --fuse-debug --timeout 1200 \
  --output test/evaluation-local/runs/iso9660/fuse-export-new
```

输出路径必须是新目录。整个特权流程在私有 QEMU 客体中执行，完成后解除注册、卸载测试模块并关闭客体。宿主机复制版预检的 FUSE 挂载也已卸载。
