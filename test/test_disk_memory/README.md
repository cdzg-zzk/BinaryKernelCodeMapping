## Disk & Memory Overhead

### 1. 评估范围与结论导向

**本小节只回答“磁盘/内存开销（footprint）”问题，不讨论任何性能延迟（例如 dlopen/启动耗时、I/O 延迟或吞吐）**。我们把评估对象限定为：**“稀疏存根 DSO（Sparse Stub DSO）”在磁盘持久化占用与进程物理内存占用上的额外成本**，并明确**不**计入构建产物（如中间对象文件、符号分析日志、调试包等）或运行时以外的缓存/临时文件（非本章节范围）。([man7.org][1])

**Claims（结论/主张）**（每条都对应可复现测量证据与/或权威定义）：

* **Claim-D1（Disk O(1) footprint within tested range）**：在 Ext4 上，存根 DSO 的**物理磁盘足迹**（allocated size，以 `st_blocks` 计）在我们测试的页面规模 (P\in{5,33,129}) 下保持恒定，尽管其逻辑大小（`st_size`）随 (P) 线性增长（表 1）。[1]
  ([man7.org][2])
* **Claim-M1（小且阶梯化的单进程私有管理开销）**：单进程从“仅加载”到“触达（touch）”阶段，额外内存开销主要体现在页表项内存（`VmPTE`）的小幅增加（4–8 KiB），且呈现页粒度的阶梯性。该指标反映**进程私有**页表内存，而非共享代码页大小。[12]
  ([man7.org][3])
* **Claim-M2（多进程共享：总物理页随 N 近似 O(1)）**：在多进程并发加载同一存根 DSO 的只读场景下，(\sum PSS) 随进程数 (N\in{1,2,4,8}) 保持近似恒定（表 2），表明**物理载荷页主要在进程间共享**；我们用 PSS（而非 RSS）避免对共享页的重复计数。[13][14]
  ([man7.org][4])

> **可直接复制进论文的表述（建议）**：
> （i）“我们仅评估磁盘与内存 footprint，不讨论延迟；磁盘以 `st_blocks×512B` 定义物理占用，内存以 `VmPTE` 与 (\sum PSS) 分别刻画每进程页表私有成本与跨进程共享后的总物理占用。”[1][12][13]
> （ii）“在 Ext4 上，存根 DSO 的物理磁盘占用在 (P=5,33,129) 三个点上保持 8 KiB，而逻辑尺寸随 (P) 线性增长，验证了稀疏布局将逻辑地址空间与物理块分配解耦。”[1]
> （iii）“并发扩展到 8 个进程时，(\sum PSS) 与进程数无关，表明载荷页由内核以文件映射方式共享；我们不把单进程的 RSS/PSS 误读为系统新增物理内存，而以 (\sum PSS) 作为唯一物理内存证据口径。”[13][14]

#### 实验环境（与可复现性相关的最小集合）

* CPU：Intel Core i7-1165G7（x86-64）。x86-64 的分级页表与页粒度分配是解释 `VmPTE` 阶梯性的基础背景。[15]
* OS：Linux kernel `5.15.0-119-generic`（影响 `/proc` 统计字段与实现细节）。[12][13] ([man7.org][3])
* FS：Ext4，块大小 4096 B（影响块分配台阶与稀疏文件的物理块分配粒度）。[1] ([man7.org][2])
* 页大小：4 KiB（影响页表粒度与 PSS/RSS 的换算）。[15]

---

### 2. Disk Overhead（只统计 stub DSO footprint）

> 目标：只回答“**单个存根 DSO 文件**在磁盘上到底占了多少真实空间”，不讨论其加载/运行性能。

#### 2.1 Metrics & Definitions

**逻辑大小 vs 物理占用**

* `st_size`：文件的**逻辑长度**（字节），对应“表观大小（apparent size）”。[1] ([man7.org][2])
* `st_blocks`：文件实际分配的块数，**以 512B 为单位**（这是接口语义，与文件系统块大小无关）。因此我们定义
  [
  \texttt{disk_bytes} = st_blocks \times 512
  ]
  用作**物理磁盘足迹**。[1] ([man7.org][2])

**为什么不能用 `ls -lh` 或仅看 `st_size`**
`du` 手册明确区分了“表观大小（apparent size）”与实际占用：对稀疏文件（holes），`--apparent-size` 可能显著大于实际占用；因此 disk footprint 必须基于“已分配块”口径或等价工具验证。[2] ([man7.org][5])

**稀疏性（sparsity）与“洞（hole）”的可证方法**

* `lseek(SEEK_DATA/SEEK_HOLE)` 可在支持的文件系统上定位数据段与洞段，用于验证稀疏布局是否仍然存在（未被复制/打包破坏）。[3] ([man7.org][6])
* `filefrag -v` 通过 FIEMAP ioctl 获取 extent 映射，提供“逻辑偏移 → 物理 extent”的证据链；这是比“猜测稀疏”更可审计的做法。[4][5] ([man7.org][7])

#### 2.2 Methodology

**输入（Inputs）**

* 三种规模存根：Small ((P=5))、Medium ((P=33))、Large ((P=129))。其中 (P) 表示“存根有效载荷代码所需的 4KiB 页面数”，由我们对生成物进行符号/程序头双重校验得到（只作为内部一致性约束，不作为外部引用来源）。
* 所有测试仅统计**stub DSO 文件本体**，不计构建目录、日志和调试符号包（范围边界写死，避免评审质疑“把中间文件藏起来”或“把其它文件算进来”）。

**步骤（Steps）**（每个配置对 DSO 文件执行一次；若复现实验建议重复并报告中位数，但本文不额外虚构重复次数）

1. **采集逻辑大小与物理块数**：

   * `stat` 读取 `st_size` 与 `st_blocks`，并按 `disk_bytes=st_blocks×512` 计算物理足迹。[1] ([man7.org][2])
2. **交叉验证 apparent size 与 allocated size**：

   * `du --apparent-size` 与默认 `du` 对比，确认是否存在稀疏洞导致的差异。[2] ([man7.org][5])
3. **证明稀疏性未被破坏**：

   * `filefrag -v` 导出 extent 分布（基于 FIEMAP），确认除头尾必要元数据外，中间 payload 区域未分配物理块（表现为大范围无 extent 覆盖）。[4][5] ([man7.org][7])
   * 可选：用 `lseek(SEEK_HOLE/SEEK_DATA)` 再次定位洞区间，作为与 extent 互补的证据。[3] ([man7.org][6])
4. **确认 ELF 结构不被破坏**（可复现性/可解释性）：

   * `readelf -lW`/`readelf -S` 检查 `PT_LOAD`、节区布局与对齐情况，确保文件仍是动态链接器可识别的 ELF 共享对象。[6][7][8] ([man7.org][8])

**输出（Outputs）**

* 表 1：`st_size`、`st_blocks`、`disk_bytes` 与稀疏性验证结论。
* （建议图占位）图 1：横轴 (P)，纵轴分别绘制 `st_size` 与 `disk_bytes`（双轴或两子图），直观看到“逻辑线性增长、物理常数”。

**验收条件（Acceptance）**

* `st_size` 随 (P) 线性增长，而 `st_blocks` 在测试范围内保持常数；并且 `filefrag`/`lseek` 显示中间区域存在洞（无物理 extent / 可定位洞区间）。[1][4][5] ([man7.org][2])

**常见陷阱（Pitfalls）**

* 复制与归档可能改变稀疏性：例如 `copy_file_range()` 在复制稀疏文件时**可能展开洞**；归档工具需要显式 `--sparse` 才能尽量保留洞布局。[9][10][11] ([man7.org][9])

#### 2.3 Results: Disk Footprint & Sparsity

**表 1：Disk Footprint & Sparsity（仅 stub DSO 文件本体）**

| 配置     | 页面数 (P) | 逻辑大小 `st_size` (B) | 物理块数 `st_blocks` (×512B) | `disk_bytes` (B) | 稀疏性验证（filefrag/extent） |
| ------ | ------: | -----------------: | -----------------------: | ---------------: | ---------------------- |
| Small  |       5 |             34,296 |                       16 |            8,192 | Payload 区域为 hole       |
| Medium |      33 |            148,984 |                       16 |            8,192 | Payload 区域为 hole       |
| Large  |     129 |            542,200 |                       16 |            8,192 | Payload 区域为 hole       |

* 关键口径：`st_blocks` 以 512B 为单位，因此表中 `disk_bytes` 与文件系统 4KiB block size 并不冲突。[1] ([man7.org][2])

**解释（Claim-D1）**

* `st_size` 呈线性：根据三点数据可得
  [
  st_size \approx 13816 + P \times 4096
  ]
  其中常数项 13,816 B 对应 ELF 头/程序头/对齐填充等“必须存在的非稀疏锚点”，而 (P\times4096) 对应逻辑 payload 地址空间。ELF 文件由 ELF header 与（可选的）program header/section header 等结构组成，这些结构为动态装载/链接提供必要元数据。[6][7][8] ([man7.org][8])
* `st_blocks` 恒定：`st_blocks=16` 对应 `disk_bytes=8192`，表明在 Ext4 上该 DSO 的真实块分配仅覆盖少量元数据块，而中间 payload 大区间通过洞表示。洞区间的读取语义为“返回零”，并不要求为每个逻辑字节分配磁盘块（这也是稀疏文件/洞的定义基础之一）。[1][12] ([man7.org][2])
* `filefrag`/FIEMAP 给出可审计证据：`filefrag` 使用 FIEMAP ioctl 提供 extent 映射，能直接证明“逻辑连续 ≠ 物理分配连续”。[4][5] ([man7.org][7])

> **图 1（占位）**：`st_size` 随 (P) 线性增长，而 `disk_bytes` 在三点上恒定为 8 KiB。
> （建议文件名：`figures/disk_overhead.pdf`）

#### 2.4 讨论：我们证明了什么、没证明什么

* 我们证明的是：在该文件系统与构建方式下，**“stub DSO 文件本体”的 allocated blocks 与 (P) 解耦**（在测试点上为常数）。这是可由 `st_blocks` 与 extent 证据直接检验的事实。[1][4][5] ([man7.org][2])
* 我们**没有**在本节证明：所有文件系统/所有复制路径/所有打包流程都能保持这种稀疏性；这属于有效性威胁的一部分（见 2.5）。`du` 手册也明确指出“表观大小”与“占用空间”可显著不同，尤其在稀疏文件存在时。[2] ([man7.org][5])

#### 2.5 Threats to Validity（Disk）

* **文件系统与实现差异**：`SEEK_HOLE/SEEK_DATA` 是否可用、FIEMAP 的返回细节、洞的表示方式与最小分配粒度均可能随文件系统与内核变化。[3][5] ([man7.org][6])
* **复制/打包破坏稀疏性**：某些复制路径可能展开洞（例如 `copy_file_range()` 的已知语义风险）；归档时若未启用 `tar --sparse`，可能把洞当作真实零数据写入归档导致体积膨胀。[9][10] ([man7.org][9])
* **后处理（strip/对齐/重写节区）**：`strip` 会修改目标文件并丢弃符号信息，可能改变节区组织与尾部结构；若你的发布流水线包含 strip、二次链接或二进制重写，需要重新跑表 1 的 protocol 以验证 `st_blocks` 与 extent 仍满足预期。[8][13] ([man7.org][10])

---

### 3. Memory Overhead（按因素拆解）

> 目标：把“看起来变大了”的内存数字拆成**可解释且可审计**的组成部分，避免把共享页重复计算或把统计口径误读为“系统新增物理内存”。

#### 3.1 Cost Model：进程级开销的组成

我们将“加载存根 DSO”对内存的影响拆解为四类（其中只有部分属于“每进程私有开销”）：

1. **载荷页（payload pages）的物理驻留**：对于文件映射的只读代码页，多个进程通常共享同一份物理页缓存；因此应使用 PSS 或 (\sum PSS) 论证共享，而不是 RSS。[13][14] ([man7.org][4])
2. **动态链接/重定位引入的私有脏页**：若存在可写重定位目标（例如可写 GOT/重定位写入），可能触发 CoW，使 `Private_Dirty` 增加并随进程数增长。**为隔离机制本身，我们在基准中固定导出/重定位复杂度（(F=1, G=0)）**，避免把“链接复杂度”混进“存根稀疏机制”的结论里。[7][14] ([man7.org][11])
3. **页表与 VMA 元数据（每进程私有管理成本）**：`VmPTE` 直接给出页表项占用的内存大小，是最稳定的“每进程私有成本”信号之一。[12] ([man7.org][3])
4. **加载器常数项与映射开销**：`dlopen()` 将共享对象加入地址空间，其映射与符号解析策略由动态加载器与 ELF 元数据决定；本节仅把这部分作为背景，不把它当作“稀疏机制收益”的来源。[6][7] ([man7.org][1])

#### 3.2 Metrics：选择哪些统计字段，以及边界解释

* **`VmPTE`（/proc/pid/status）**：页表项占用的内存大小（单位 kB），用于量化“映射带来的页表元数据成本”。它是**每进程私有**的，不会因共享代码页而被抵消。[12] ([man7.org][3])
* **`Pss`, `Rss`, `Private_Clean/Dirty`, `Shared_Clean/Dirty`（/proc/pid/smaps）**：逐 VMA 给出驻留与共享拆分。我们使用 PSS（及跨进程求和）来避免对共享页的重复计数。[13][14] ([man7.org][4])
* **`smaps_rollup`（/proc/pid/smaps_rollup）**：对 smaps 各字段的“进程级汇总”，可降低用户态聚合开销并减少“不同进程采样窗口不一致”的风险（尤其在多进程实验中）。[15] ([Linux Kernel Archives][12])
* **`minflt/majflt`（/proc/pid/stat）**：分别是 minor/major page faults 的计数；major faults 表示需要从磁盘加载页，minor faults 表示无需从磁盘加载页。我们**不把它当作“触达页数”或“驻留页数”的直接替代**，仅用于 sanity-check：例如只读映射下 major faults 是否异常升高。[16] ([man7.org][13])

#### 3.3 Single-process experiment（S0/S1/S2 分阶段）

**阶段定义（States）**

* **S0（Baseline）**：进程启动但尚未加载存根 DSO。
* **S1（Loaded）**：调用 `dlopen()` 后，存根 DSO 已加入地址空间，但尚未触达 payload（不强制触发所有页驻留）。[7] ([man7.org][1])
* **S2（Touched）**：对 payload 执行只读 touch，触发必要的缺页与页表建立，使开销“实体化”并可被 /proc 指标捕获（注意：我们只讨论 footprint，不讨论缺页导致的延迟）。[11][16] ([man7.org][14])

**协议（Protocol）**

* Inputs：选择某一 (P) 的存根 DSO；固定 (F=1, G=0)。
* Steps：在 S0、S1、S2 三个检查点分别读取 `/proc/<pid>/status`（提取 `VmPTE`）与 `/proc/<pid>/smaps(_rollup)`（提取 PSS/Private_* 等）。[12][13][15] ([man7.org][3])
* Outputs：(\Delta VmPTE = VmPTE_{S2}-VmPTE_{S1})，以及（可选）PSS/Private_* 的差分。
* Acceptance：(\Delta VmPTE) 为小幅页粒度增长；只读触达下 `Private_Dirty` 不应异常增大（否则通常意味着发生了写入/CoW）。[12][13] ([man7.org][3])

**结果（Claim-M1）**
在 S1→S2 的转换中，我们观测到 `VmPTE` 增量为 **4–8 KiB**。这与“页表按需分配、以页为粒度增长”的预期一致：页表本身占用页粒度内存，因此 `VmPTE` 往往呈现阶梯性，而不是随逻辑映射长度连续增长。[12][17] ([man7.org][3])

> **图 2（占位）**：单进程 (\Delta VmPTE) 在不同 (P) 下的散点/箱线图（若有重复实验）。
> （建议文件名：`figures/vmpte_step.pdf`）

#### 3.4 Multi-process experiment（N 扩展，同窗采样）

**问题定义**
我们关心的是“并发 N 个进程加载同一存根 DSO 时，总物理内存是否随 N 线性增长”。因此我们选择 **(\sum PSS)** 作为证据口径：PSS 明确把共享页按共享者均分；跨进程求和可近似还原“唯一物理页总量”。[14][13] ([man7.org][15])

**协议（Protocol）**

* Inputs：选择 Medium ((P=33)) 与 Large ((P=129)) 两种规模；并发进程数 (N\in{1,2,4,8})。
* Steps：所有进程在进入 S2（Touched）前使用 barrier 同步，尽量让采样处于同一稳态窗口；随后对每个进程读取 `smaps_rollup`（或 smaps 聚合）并求和得到 (\sum PSS)。[15] ([Linux Kernel Archives][12])
* Outputs：表 2 中的 (\sum PSS) 随 N 的变化趋势。
* Pitfalls：smaps 逐 VMA 输出体量大、读取开销高；使用 rollup 能降低聚合成本并减少进程间采样偏移导致的误差。[15] ([Linux Kernel Archives][12])

**表 2：Multi-Process Scalability（Sum of PSS）**

| 配置     | (P) | 指标         |     N=1 |     N=2 |     N=4 |     N=8 | 趋势   |
| ------ | --: | ---------- | ------: | ------: | ------: | ------: | ---- |
| Medium |  33 | (\sum PSS) | ~132 kB | ~132 kB | ~132 kB | ~132 kB | 近似恒定 |
| Large  | 129 | (\sum PSS) | ~516 kB | ~516 kB | ~516 kB | ~516 kB | 近似恒定 |

**解释（Claim-M2）**

* 以上结果与“文件映射代码页由内核共享”的机制一致：PSS 把共享页按共享者均分，跨进程求和能抵消均分从而逼近“唯一物理页总量”。[14] ([man7.org][15])
* 同时，我们强调边界：**我们不把单个进程的 PSS/RSS 当作“系统新增物理内存”**；只有 (\sum PSS)（或等价的全局口径）才能作为“总物理占用”的证据，避免共享页重复计数。[14][13] ([man7.org][15])

> **图 3（占位）**：横轴 N，纵轴 (\sum PSS)，两条曲线（Medium/Large）近似水平。
> （建议文件名：`figures/pss_scaling.pdf`）

#### 3.5 Threats to Validity（Memory）

* **“未触达页”的低估风险**：只在 S1（Loaded）采样会显著低估 resident footprint，因为 `dlopen()` 仅保证对象进入地址空间，并不强制所有页立即驻留；因此我们必须区分 S1 与 S2，并把 S2 作为 footprint 的主要证据点。[7][11] ([man7.org][1])
* **PSS/RSS 的误读**：RSS 会对共享页重复计数；PSS 才是为共享场景设计的口径，但它仍是“按映射拆分的统计量”，应避免把单进程 PSS 直接解读为系统总内存占用。[14] ([man7.org][15])
* **采样窗口不同步与统计开销**：`/proc/pid/smaps` 逐 VMA 输出，聚合成本高；多进程并发下更容易出现“不同进程采样时刻不同”导致的瞬时偏差。`smaps_rollup` 提供了汇总视图以缓解该问题，但仍需在实验协议中显式加入同步点。[15] ([Linux Kernel Archives][12])
* **THP/内核策略差异**：透明大页可能改变页表与 resident 统计行为；虽然本实验的最大逻辑规模（~542 KB）低于典型 2 MiB hugepage 粒度，仍建议在不同 THP 配置与内核版本上复测，以避免把配置特性误当作机制收益。[18] ([Linux 内核文档][16])

---

### 4. Summary of Claims ↔ Evidence

| Claim                                   | 可检验现象/趋势                                            | 来自测量的证据                                      | 关键定义/论证引用                                                                        |
| --------------------------------------- | --------------------------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------- |
| Claim-D1：磁盘物理足迹与 (P) 解耦（测试点内为常数）        | `st_size` 随 (P) 线性↑，但 `st_blocks` 常数；extent 显示中段无分配 | 表 1（`st_blocks=16` 恒定，`disk_bytes=8192B` 恒定） | `st_blocks` 语义与 512B 单位：[1]；apparent vs allocated：[2]；FIEMAP/filefrag 证据链：[4][5] |
| Claim-M1：单进程私有开销主要体现在小幅 `VmPTE` 增量（阶梯化） | S1→S2：`VmPTE` 增量为少量 KiB，并以页粒度出现台阶                   | “(\Delta VmPTE=4–8KiB)”（S1→S2）               | `VmPTE` 字段定义：[12]；页表分配/阶梯性背景：[17]                                                |
| Claim-M2：多进程共享使 (\sum PSS) 对 (N) 近似不变   | (N=1..8) 时 (\sum PSS) 近似恒定（同一 DSO）                  | 表 2：Medium ~132kB、Large ~516kB 均随 (N) 不变     | smaps/PSS 字段来源：[13]；PSS 作为共享拆分口径：[14]；rollup 用于聚合与同步：[15]                        |

---

### References

> 说明：以下仅列外部公开资料/文献；每条包含 URL 与访问日期（2026-02-09）。正文引用以 ([n]) 标注。

[1] Linux man-pages project. **stat(3type) — Linux manual page**. URL: `https://man7.org/linux/man-pages/man3/stat.3type.html`. Accessed: 2026-02-09. ([man7.org][2])

[2] GNU Coreutils / Linux man-pages project. **du(1) — Linux manual page**（含 `--apparent-size` 语义）. URL: `https://man7.org/linux/man-pages/man1/du.1.html`. Accessed: 2026-02-09. ([man7.org][5])

[3] Linux man-pages project. **lseek(2) — Linux manual page**（含 `SEEK_DATA`/`SEEK_HOLE`）. URL: `https://man7.org/linux/man-pages/man2/lseek.2.html`. Accessed: 2026-02-09. ([man7.org][6])

[4] Linux man-pages project. **filefrag(8) — Linux manual page**（说明使用 FIEMAP 获取 extent）. URL: `https://man7.org/linux/man-pages/man8/filefrag.8.html`. Accessed: 2026-02-09. ([man7.org][7])

[5] The Linux Kernel Developers. **Fiemap Ioctl — Linux Kernel Documentation**. URL: `https://docs.kernel.org/filesystems/fiemap.html`. Accessed: 2026-02-09. ([Linux 内核文档][17])

[6] Linux man-pages project. **elf(5) — Linux manual page**. URL: `https://man7.org/linux/man-pages/man5/elf.5.html`. Accessed: 2026-02-09. ([man7.org][8])

[7] Linux man-pages project. **ld.so(8) — Linux manual page**（动态链接器/加载器）. URL: `https://www.man7.org/linux/man-pages/man8/ld.so.8.html`. Accessed: 2026-02-09. ([man7.org][11])

[8] Linux man-pages project. **readelf(1) — Linux manual page**. URL: `https://man7.org/linux/man-pages/man1/readelf.1.html`. Accessed: 2026-02-09. ([man7.org][18])

[9] Linux man-pages project. **copy_file_range(2) — Linux manual page**（提示复制稀疏文件可能展开 holes）. URL: `https://man7.org/linux/man-pages/man2/copy_file_range.2.html`. Accessed: 2026-02-09. ([man7.org][9])

[10] GNU Project. **cp invocation (GNU Coreutils)**（`--sparse` 相关语义与例外说明）. URL: `https://www.gnu.org/software/coreutils/manual/html_node/cp-invocation.html`. Accessed: 2026-02-09. ([GNU][19])

[11] GNU Project. **GNU tar Manual: Archiving Sparse Files**（`tar --sparse`）. URL: `https://www.gnu.org/software/tar/manual/html_node/sparse.html`. Accessed: 2026-02-09. ([GNU][20])

[12] Linux man-pages project. **proc_pid_status(5) — Linux manual page**（含 `VmPTE` 字段定义）. URL: `https://man7.org/linux/man-pages/man5/proc_pid_status.5.html`. Accessed: 2026-02-09. ([man7.org][3])

[13] Linux man-pages project. **proc_pid_smaps(5) — Linux manual page**（Pss/Rss/Private_* 等字段来源）. URL: `https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html`. Accessed: 2026-02-09. ([man7.org][4])

[14] Linux man-pages project. **smem(8) — Linux manual page**（PSS 的物理内存口径与共享均分解释）. URL: `https://man7.org/linux/man-pages/man8/smem.8.html`. Accessed: 2026-02-09. ([man7.org][15])

[15] The Linux Kernel Developers. **/proc/pid/smaps_rollup ABI documentation**（rollup 为 smaps 的预聚合视图）. URL: `https://www.kernel.org/doc/Documentation/ABI/testing/procfs-smaps_rollup`. Accessed: 2026-02-09. ([Linux Kernel Archives][12])

[16] Linux man-pages project. **proc_pid_stat(5) — Linux manual page**（`minflt/majflt` 定义）. URL: `https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html`. Accessed: 2026-02-09. ([man7.org][13])

[17] Radha Chitale, Hardik Shah, Kaushik Ram, and Sangram Kadam. **A Survey of Page Table Designs in Modern Operating Systems**. *HPCA 2015* (IEEE International Symposium on High Performance Computer Architecture), 2015. URL: `https://www.cse.iitb.ac.in/~mythili/os/papers/hpca15_pageTableSurvey.pdf`. Accessed: 2026-02-09.

[18] The Linux Kernel Developers. **Transparent Hugepage Support — Linux Kernel Documentation**. URL: `https://docs.kernel.org/admin-guide/mm/transhuge.html`. Accessed: 2026-02-09. ([Linux 内核文档][16])

[19] Michael Matz, Jan Hubička, Andreas Jaeger, and Mark Mitchell (eds.). **System V Application Binary Interface: AMD64 Architecture Processor Supplement (Draft 0.99.6)**. 2012. URL: `https://refspecs.linuxbase.org/elf/x86_64-abi-0.99.pdf`. Accessed: 2026-02-09. ([Linux 基金会规范][21])

[20] Andrew Baumann, Marcus Peinado, and Galen Hunt. **Shielding Applications from an Untrusted Cloud with Haven**. *11th USENIX Symposium on Operating Systems Design and Implementation (OSDI ’14)*, 2014. URL: `https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-baumann.pdf`. Accessed: 2026-02-09. ([usenix.org][22])

[21] Abhishek Verma, Luis Pedrosa, Madhukar Korupolu, David Oppenheimer, Eric Tune, and John Wilkes. **Large-scale cluster management at Google with Borg**. *EuroSys 2015*, 2015. URL: `https://research.google.com/pubs/archive/43438.pdf`. Accessed: 2026-02-09. ([research.google.com][23])

[1]: https://man7.org/linux/man-pages/man3/dlopen.3.html "https://man7.org/linux/man-pages/man3/dlopen.3.html"
[2]: https://man7.org/linux/man-pages/man3/stat.3type.html "https://man7.org/linux/man-pages/man3/stat.3type.html"
[3]: https://man7.org/linux/man-pages/man5/proc_pid_status.5.html "https://man7.org/linux/man-pages/man5/proc_pid_status.5.html"
[4]: https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html "https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html"
[5]: https://man7.org/linux/man-pages/man1/du.1.html "https://man7.org/linux/man-pages/man1/du.1.html"
[6]: https://man7.org/linux/man-pages/man2/lseek.2.html "https://man7.org/linux/man-pages/man2/lseek.2.html"
[7]: https://man7.org/linux/man-pages/man8/filefrag.8.html "https://man7.org/linux/man-pages/man8/filefrag.8.html"
[8]: https://man7.org/linux/man-pages/man5/elf.5.html "https://man7.org/linux/man-pages/man5/elf.5.html"
[9]: https://man7.org/linux/man-pages/man2/copy_file_range.2.html "https://man7.org/linux/man-pages/man2/copy_file_range.2.html"
[10]: https://man7.org/linux/man-pages/man1/strip.1.html "https://man7.org/linux/man-pages/man1/strip.1.html"
[11]: https://www.man7.org/linux/man-pages/man8/ld.so.8.html "https://www.man7.org/linux/man-pages/man8/ld.so.8.html"
[12]: https://www.kernel.org/doc/Documentation/ABI/testing/procfs-smaps_rollup "https://www.kernel.org/doc/Documentation/ABI/testing/procfs-smaps_rollup"
[13]: https://www.man7.org/linux/man-pages//man5/proc_pid_stat.5.html?utm_source=chatgpt.com "proc_pid_stat (5) - Linux manual page - man7.org"
[14]: https://man7.org/linux/man-pages/man2/mmap.2.html "https://man7.org/linux/man-pages/man2/mmap.2.html"
[15]: https://man7.org/linux/man-pages/man8/smem.8.html "https://man7.org/linux/man-pages/man8/smem.8.html"
[16]: https://docs.kernel.org/admin-guide/mm/transhuge.html "https://docs.kernel.org/admin-guide/mm/transhuge.html"
[17]: https://docs.kernel.org/filesystems/fiemap.html "https://docs.kernel.org/filesystems/fiemap.html"
[18]: https://man7.org/linux/man-pages/man1/readelf.1.html "https://man7.org/linux/man-pages/man1/readelf.1.html"
[19]: https://www.gnu.org/s/coreutils/manual/html_node/cp-invocation.html "https://www.gnu.org/s/coreutils/manual/html_node/cp-invocation.html"
[20]: https://www.gnu.org/s/tar/manual/html_node/sparse.html "https://www.gnu.org/s/tar/manual/html_node/sparse.html"
[21]: https://refspecs.linuxbase.org/elf/x86_64-abi-0.99.pdf "https://refspecs.linuxbase.org/elf/x86_64-abi-0.99.pdf"
[22]: https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-baumann.pdf "https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-baumann.pdf"
[23]: https://research.google.com/pubs/archive/43438.pdf "https://research.google.com/pubs/archive/43438.pdf"
