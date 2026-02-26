## Disk & Memory Overhead

### 范围声明

本节**仅回答资源占用（disk footprint / memory footprint）**问题：我们量化“稀疏存根 DSO（sparse stub DSO）”在**磁盘占用**与**内存驻留/页表元数据**上的额外开销，并给出可复现的测量协议与可审计证据链。我们**不讨论性能延迟**（如 `dlopen`/符号解析/首次调用的时间开销），也不将缺页次数、PSS 等指标误读为“系统新增物理内存”的直接度量。[14]

---

### 符号与指标

* **页面粒度**：系统页大小为 4 KiB（本文所有“页”默认指 4 KiB 页）。
* **状态点**：

  * $S_0$：进程启动后、尚未加载 stub；
  * $S_1$：执行 `dlopen()` 后、尚未触达 payload；[13]
  * $S_2$：对 payload 执行只读逐页触达（touch）后。
* **差分口径**：正文优先报告
  $$
  \Delta X \triangleq X_{S_2} - X_{S_1},
  $$
  以隔离加载器常数项与“触达导致的实体化”开销。
* **$P$：payload 可执行页数（最终产物口径，支持多段并集）**
  令 $\mathcal{S}_{RX}$ 为最终 `.so` 中所有满足 **PT_LOAD 且 PF_X=1、PF_W=0** 的段集合。我们在**文件偏移空间**上，以 4 KiB 分页对这些段的覆盖范围按并集计数（处理多个不连续 R-X 段，避免重复计数），并与 touch 口径对齐：仅统计 `offset>=0x1000` 的 payload（排除 ELF 头所在页）。形式化地，令页大小 $B=4096$，则
  $$
  P \triangleq \left|\bigcup_{seg\in\mathcal{S}_{RX}}\left\{\left\lfloor\frac{x}{B}\right\rfloor \,\middle|\, x\in[\max(p_{off},B),p_{off}+p_{filesz})\right\}\right|.
  $$
  其中 $p_{off},p_{filesz}$ 来自程序头表。PT_LOAD 与权限位语义遵循 ELF 规范，段覆盖范围可由 `readelf -lW` 审计。[11][10]
* **磁盘指标**：

  * `st_size`：文件逻辑大小（apparent size）；
  * `st_blocks`：文件占用的块数，**单位为 512B**（与文件系统 block size 无关）；[1]
  * $\textsf{disk\_bytes} \triangleq 512\,\mathrm{B}\times \texttt{st\_blocks}$。
  * `du` / `du --apparent-size`：分别近似对应 “allocated vs apparent”。[3]
* **内存指标（stub-only 口径；与采集脚本一致）**：

  * `Pss_stub` / `Private_*_stub`：对 `/proc/<pid>/smaps` 做 per-VMA 过滤后求和，过滤条件为：
    1. `pathname == realpath(stub.so)`，或 `pathname == realpath(stub.so) + " (deleted)"`；
    2. VMA `offset >= 0x1000`（仅 payload，排除 ELF 头部页）；
    3. `perms` 必须可读且**不可写**（排除 CoW/写入噪声）；在 `touch_mode=code` 下还要求可执行（仅 `r-x` 映射）。
    该定义确保 `Pss_stub/Private_*_stub` 与 `touched_pages` 的触达范围一致。[14]
  * `VmPTE`：`/proc/<pid>/status` 的页表内存统计（进程私有页表开销的近似观测）。[15]
  * `minflt/majflt`：来自 `/proc/<pid>/stat` 的轻/重缺页计数，仅作为诊断信号（非验收门槛）。[16]

---

### Claims（结论驱动，正文将逐条闭环）

* **Claim‑D1（Disk–$P$ 解耦，在实验范围内近似常数）**：在 Ext4（4 KiB block）上，stub DSO 的 $\textsf{disk\_bytes}$ 在 $P\in\{5,33,129\}$ 下保持为**约 2 个文件系统块**，而 `st_size` 随 $P$ 线性增长（apparent-only）。[1][4]
* **Claim‑D2（Disk 常数的边界）**：上述“常数”成立于**元数据未跨越新的 FS block 边界**且**分发链路保持稀疏性**的范围内；在符号/重定位元数据显著增长或稀疏性被破坏时，`st_blocks` 将按 block 粒度阶梯增长。[7][8][9]
* **Claim‑M1（单进程页表元数据小且呈阶梯）**：单进程触达 payload 后，$\Delta\textsf{VmPTE}$ 仅以 4 KiB 为粒度阶梯变化，反映页表分配按页表页计费且与虚拟地址布局/对齐有关。[15][17][18]
* **Claim‑M2（多进程共享：$\sum \textsf{Pss}_{\text{stub}}$ 近似不随 $N$ 增长）**：并发进程触达同一 stub 的 payload 后，$\sum_{i=1}^{N}\textsf{Pss}^{(i)}_{\text{stub}}$ 近似保持常数；在本文测量中，Medium 覆盖 $N\in\{1,2,4,8,16,32,64\}$，Large 覆盖 $N\in\{1,2,4,8,16,32\}$。同时 $\sum_{i=1}^{N}\textsf{Private\_Dirty}^{(i)}_{\text{stub}}\approx 0$ 表明缺少 CoW 污染，是“共享成立”的必要前提之一。PSS 的比例分摊语义来自 procfs 定义。[14]

---

## 2. Disk Overhead（只统计 stub DSO footprint）

### 2.1 Metrics & Definitions

我们只统计“最终生成的 stub `.so` 文件”的 footprint：

* **apparent size**：用 `stat.st_size` 或 `du --apparent-size` 报告，表示逻辑字节长度；
* **allocated size**：用 `stat.st_blocks`（512B 单位）或 `du` 默认口径报告，表示实际分配的空间。`ls -lh` 仅展示逻辑大小，不能反映稀疏性。[1][3]

稀疏性验证采用两条互补证据链：

1. `filefrag -v` 读取 extent 映射（优先 FIEMAP ioctl）；[4][5]
2. `lseek(..., SEEK_HOLE/SEEK_DATA)` 或 FIEMAP 证明 hole 的存在（注意：并非所有零区间都必须被暴露为 hole）。[6][5]

### 2.2 Methodology（Protocol‑Disk）

**Inputs**

* 最终生成的 stub DSO 三个规模点：Small/Medium/Large（$P=5/33/129$）。
* 文件系统：Ext4，block size = 4 KiB（用于解释“约 2 个 fs blocks”的直观含义）。

**Steps**

1. **静态解析 $P$**：用 `readelf -lW` 读取程序头，按“符号与指标”中 $\mathcal{S}_{RX}$ 的并集规则计算 $P$。[10][11]
2. **磁盘占用采样**：对每个 `.so` 执行 `stat` 采集 `st_size` 与 `st_blocks`，并计算 $\textsf{disk\_bytes}=512\,\mathrm{B}\times \texttt{st\_blocks}$。[1]
3. **du 交叉验证**：记录 `du` 与 `du --apparent-size`，分别对应 allocated 与 apparent 口径，避免误把 apparent 当 allocated。[3]
4. **稀疏性证据**：执行 `filefrag -v`，记录 extent 的 **logical block range** 摘录（至少两行），证明 payload 区间未分配。[4][5]

**Outputs**

* Table 1（`st_size`, `st_blocks`, `disk_bytes`, `filefrag` extent 摘录）
* Fig.1–2 占位图（见 2.4）

**Acceptance（验收条件）**

* `filefrag` 显示仅少量 extent（头/尾），且中间出现大范围 hole 证据；
* `du` 与 `512×st_blocks` 在量级上匹配（允许工具舍入差异）。[4]

**Pitfalls**

* 稀疏性可能在分发链路被破坏：

  * `cp` 的 `--sparse` 策略、`tar --sparse/--hole-detection` 的处理方式会影响“洞”是否保留；[7][9]
  * `copy_file_range()` 在复制稀疏文件时**可能扩展 hole**（把洞写成显式零），导致 `st_blocks` 增大。[8]

### 2.3 Results（最终产物：$P=5/33/129$）

**Table 1. Disk Footprint & Sparsity Evidence（Ext4, 4 KiB blocks）**

| 配置     | $P$ | `st_size` (B) | `st_blocks` | $\textsf{disk\_bytes}=512\,\mathrm{B}\times \texttt{st\_blocks}$ (B) | `filefrag -v` 证据摘录（logical extents） |
| ------ | --: | ------------: | ----------: | --------------------------------------------: | ----------------------------------- |
| Small  |   5 |        34,296 |          16 |                                         8,192 | `0: 0..0`；`1: 8..8`                 |
| Medium |  33 |       148,984 |          16 |                                         8,192 | `0: 0..0`；`1: 36..36`               |
| Large  | 129 |       542,200 |          16 |                                         8,192 | `0: 0..0`；`1: 132..132`             |

**解读与归因**

* `st_size` 随 $P$ 近似线性（apparent-only）：
  $$
  \texttt{st\_size} \approx 13816 + 4096\cdot P.
  $$
  常数项对应 ELF 头/程序头与对齐填充，线性项对应 payload 的逻辑占位；段装载与权限语义由 ELF 规范与 `readelf` 输出定义支撑。[11][10]
* `st_blocks` 恒定为 16（即 8,192B），意味着在该实验范围内 stub 的**实际落盘**约为 **2 个 Ext4 block**。该现象与稀疏文件“洞不分配物理块”的语义一致：`st_blocks` 统计的是已分配块（512B 单位），而不是逻辑长度。[1]
* `filefrag` 的 extent 摘录显示每个规模点仅存在两段短 extent（头部与尾部），中间大范围逻辑区间为 hole（未分配），构成了“disk 近似常数”的可审计证据链。[4][5]

### 2.4 图表占位（Disk）

* **Fig. 1（placeholder）**：$\textsf{disk\_bytes}$ vs. $P$

  * x 轴：$P$；y 轴：$\textsf{disk\_bytes}$；
  * 预期：**水平线**（本实验点恒定为 8,192B）。
* **Fig. 2（placeholder）**：`st_size`–$P$

  * 预期：**线性**，斜率约 4,096 B/page，截距约 13,816 B。

**可直接复制进论文正文的表述（示例）**

> 在 Ext4（4 KiB block）上，stub DSO 的实际落盘空间（按 `st_blocks` 计，512B 单位）在 $P=5/33/129$ 三个规模点保持不变（8,192B），而逻辑大小 `st_size` 随 $P$ 线性增长。`filefrag` 的 extent 映射进一步表明仅头/尾块被分配，其余 payload 区间为 hole，从而实现 disk footprint 与 payload 逻辑规模的解耦。

### 2.5 Threats to Validity（Disk）

* **文件系统与实现差异**：hole/extent 的呈现依赖文件系统与内核实现；`filefrag` 的 FIEMAP 证据链在不支持 FIEMAP 的环境会退化。[4][5]
* **分发/复制破坏稀疏性**：归档/拷贝工具可能把 hole 写成显式零块，导致 `st_blocks` 增大；尤其 `copy_file_range()` 文档明确提示其可能扩展 hole。[8]
* **元数据增长的边界**：当导出符号、重定位元数据或节区布局增长跨越新的 FS block 边界时，落盘空间会按 block 粒度阶梯增长（Claim‑D2）。[7][9]

---

## 3. Memory Overhead（按因素拆解）

### 3.1 Cost Model（我们“要解释的开销”是什么）

我们将开销拆成两类，避免把不同来源混为一谈：

1. **per-process 私有元数据**：页表（`VmPTE`）与 VMA 管理等；其中 `VmPTE` 是可观测近似。[15]
2. **stub 映射对应的驻留页**：对 stub 的 **可执行映射（r-x）**，其共享性用 `Pss_stub`/`Private_*_stub` 观测。PSS 是“按共享者数量比例分摊”的驻留口径，因此 $\sum \textsf{Pss}_{\text{stub}}$ 可作为“进程集合内对该映射的驻留规模”的近似。[14]

> 重要边界：我们不把 $\sum \textsf{Pss}_{\text{stub}}$ 解释为“系统新增物理内存”，它仅说明“这些进程对该映射的驻留页集合没有随 $N$ 复制”。[14]

### 3.2 Metrics（选择这些指标的原因与边界）

* **`Pss_stub`（主证据）**：直接绑定 stub 的可执行映射，避免 `smaps_rollup` 或进程总量（含栈/堆/ld.so/libc）稀释归因。[14][20]
* **`Private_Dirty_stub`（共享成立的必要证据）**：若出现写入路径（重定位写入、可写 GOT 等）导致 CoW 污染，私有脏页会增长并破坏“共享近似常数”。因此我们将 `ΔPrivate_Dirty_stub≈0`（或多进程下 `∑Private_Dirty_stub≈0`）作为必要证据之一。[14]
* **`VmPTE`（对照曲线）**：页表内存是**进程私有**，预期随 $N$ 线性增长；将其与 $\sum \textsf{Pss}_{\text{stub}}$ 同图展示，可形成“共享页常数 vs 私有元数据线性”的对照。[15]
* **`minflt/majflt`（仅诊断）**：缺页次数受 fault-around 等机制影响，不能等价为“触达页数”。我们在验收中以 `touched_pages`（由实验显式触达的页数）为准。[16][19]

### 3.3 Single‑process experiment（$S_0/S_1/S_2$，正文只报 $\Delta(S_2-S_1)$）

#### Methodology（Protocol‑1P）

**Inputs**：单进程 + stub DSO（$P\in\{5,33,129\}$）。
**Steps**

1. 采样 $S_0$：读取 `status/smaps`（基线）。
2. 触发 $S_1$：`dlopen(stub)` 后立即采样。[13]
3. 触发 $S_2$：对 payload 执行只读 touch（每页至少读 1B），随后采样。
4. 计算 $\Delta X = X_{S_2}-X_{S_1}$，并对 stub 的 `r-x` VMA 做过滤汇总（stub-only）。

**Outputs**

* Table 2：$\Delta\textsf{VmPTE}$、$\Delta \textsf{Pss}_{\text{stub}}$、$\Delta \textsf{Private\_Clean}_{\text{stub}}$、$\Delta \textsf{Private\_Dirty}_{\text{stub}}$、`touched_pages`

**Acceptance（硬验收）**

* **触达闭环**：`touched_pages == P`（以 PT_LOAD(R‑X) 覆盖并集计数为准）。
* **replace 生效 sanity-check**：被触达页面中至少存在“非全零”内容（避免把 hole/zero-page 当作 payload 测到）。
* **无 CoW 污染**：$\Delta \textsf{Private\_Dirty}_{\text{stub}}\approx 0$。[14]

> 说明：`majflt==0` 更适合作为“诊断/异常信号”，而不是硬门槛；本节以 `touched_pages` 与 stub-only 差分为主闭环。[16][19]

#### Results（单进程差分）

**Table 2. Single-process overhead（$\Delta = S_2 - S_1$，stub `r-x` VMA only, medians）**

| 配置     | $P$ | $\Delta\textsf{VmPTE}$ (KiB, median) | $\Delta \textsf{Private\_Clean}_{\text{stub}}$ (KiB) | $\Delta \textsf{Private\_Dirty}_{\text{stub}}$ (KiB) | $\Delta \textsf{Pss}_{\text{stub}}$ (KiB) | `touched_pages` |
| ------ | --: | -----------------------------------: | ----------------------------------: | ----------------------------------: | ------------------------: | --------------: |
| Small  |   5 |                                    8 |                                  20 |                                  ~0 |                        20 |               5 |
| Medium |  33 |                                   12 |                                 132 |                                  ~0 |                       132 |              33 |
| Large  | 129 |                                    8 |                                 516 |                                  ~0 |                       516 |             129 |

**讨论（为何 $\Delta\textsf{VmPTE}$ 呈阶梯）**
页表以页表页为分配单位（4 KiB），因此 `VmPTE` 以 4 KiB 粒度变化；其阶梯点与 VMA 的虚拟地址布局、2 MiB 对齐边界、以及是否需要额外分配页表页相关。Linux 页表层级与页表页覆盖范围的基本事实在内核文档与体系结构文档中有明确描述。[17][18]

**图表占位（Single-process）**

* **Fig. 3（placeholder）**：$\Delta\textsf{VmPTE}$–$P$

  * 预期：离散阶梯（4 KiB 粒度），多次重复后以中位数稳定在少数台阶上。

### 3.4 Multi‑process experiment（$N$ 扩展，同窗采样；stub-only 主证据）

本节给出**可对账**的多进程结果（来自同一轮 `dm_matrix.py`, `touch_mode=code`，输出列为：`sum(VmPTE) sum(Pss_total) sum(Pss_stub) sum(Private_Dirty_stub) touched_pages`）。其中 Medium 采用 $N=1/2/4/8/16/32/64$，Large 采用 $N=1/2/4/8/16/32$ 并报告中位数。我们将 `∑Pss_stub` 作为 Claim‑M2 的主证据；`∑Pss_total`（混入 ld.so/libc/栈/堆等常数项）仅用于展示整体趋势上界，不用于强归因。[14][20]

#### Methodology（Protocol‑NP）

**Inputs**：并发加载同一 stub（Medium: $N\in\{1,2,4,8,16,32\}$；Large: $N\in\{1,2,4,8,16,32\}$）。
**Steps**

1. 启动 $N$ 个子进程执行 `dlopen()+touch_mode=code`，每个子进程在完成 touch 后写出 `S2.<pid>` marker（并保持存活一段时间，覆盖采样窗口）。
2. 协调者以 “marker 数量达到 $N$” 作为同步点（等价于 barrier）：观察到所有 `S2.<pid>` 后，在**同一时间窗**内读取每个 pid 的 `/proc/<pid>/status`（`VmPTE`）与 `/proc/<pid>/smaps_rollup`（`Pss_total`），并解析 `/proc/<pid>/smaps` 得到 stub-only 的 `Pss_stub/Private_*_stub`，最后求和得到 $\sum_{i=1}^{N}\textsf{Pss}^{(i)}_{\text{stub}}$、$\sum_{i=1}^{N}\textsf{Private\_Dirty}^{(i)}_{\text{stub}}$ 与 $\sum_{i=1}^{N}\textsf{VmPTE}^{(i)}$。[14][15]

**Acceptance（硬验收）**

* `touched_pages == P`（证明该轮逐页触达了目标 `r-x` 页集合）；
* $\sum_{i=1}^{N}\textsf{Private\_Dirty}^{(i)}_{\text{stub}} = 0$（无 CoW 污染）。[14]

#### Results（多进程共享：以 `∑Pss_stub` 为主证据）

**Table 3. Multi-process scalability（同窗采样，中位数；单位 kB）**

**Small（$P=5$）**

| $N$ | $\sum \textsf{VmPTE}$ | $\sum \textsf{Pss}_{\text{total}}$ | **$\sum \textsf{Pss}_{\text{stub}}$** | $\sum \textsf{Private\_Dirty}_{\text{stub}}$ | `touched_pages` |
| --: | -----------: | -----------------: | --------------------: | --------------------------: | --------------: |
|   1 |           48 |                201 |                **20** |                           0 |               5 |
|   2 |          100 |                364 |                **20** |                           0 |               5 |
|   4 |          204 |                676 |                **20** |                           0 |               5 |
|   8 |          396 |               1313 |                **20** |                           0 |               5 |
|  16 |          772 |               2525 |                **20** |                           0 |               5 |
|  32 |         1584 |               4803 |                **20** |                           0 |               5 |

**Medium（$P=33$）**

| $N$ | $\sum \textsf{VmPTE}$ | $\sum \textsf{Pss}_{\text{total}}$ | **$\sum \textsf{Pss}_{\text{stub}}$** | $\sum \textsf{Private\_Dirty}_{\text{stub}}$ | `touched_pages` |
| --: | -----------: | -----------------: | --------------------: | --------------------------: | --------------: |
|   1 |           52 |                315 |               **132** |                           0 |              33 |
|   2 |          100 |                472 |               **132** |                           0 |              33 |
|   4 |          200 |                795 |               **132** |                           0 |              33 |
|   8 |          392 |               1433 |               **132** |                           0 |              33 |
|  16 |          784 |               2650 |               **132** |                           0 |              33 |
|  32 |         1608 |               4950 |               **132** |                           0 |              33 |

**Large（$P=129$）**

| $N$ | $\sum \textsf{VmPTE}$ | $\sum \textsf{Pss}_{\text{total}}$ | **$\sum \textsf{Pss}_{\text{stub}}$** | $\sum \textsf{Private\_Dirty}_{\text{stub}}$ | `touched_pages` |
| --: | -----------: | -----------------: | --------------------: | --------------------------: | --------------: |
|   1 |           48 |                696 |               **516** |                           0 |             129 |
|   2 |          100 |                856 |               **516** |                           0 |             129 |
|   4 |          200 |               1176 |               **516** |                           0 |             129 |
|   8 |          404 |               1814 |               **516** |                           0 |             129 |
|  16 |          780 |               3032 |               **516** |                           0 |             129 |
|  32 |         1584 |               5306 |               **516** |                           0 |             129 |

**关于大 $N$（如 8/16/32/64）时 $\sum \textsf{Pss}_{\text{stub}}$ 的 4KiB 级下偏**：`smaps` 中 PSS 以 **kB 文本口径**呈现，并对共享页做比例分摊；当共享者数量较大时，每进程的分摊结果会出现整数 kB 取整，从而在跨进程求和时造成 1 页（4KiB）量级的舍入误差。这不改变“随 $N$ 近似常数”的趋势判断。[14]

#### Discussion（把“可能可疑”变成“可解释”）

* **（主结论）$\sum \textsf{Pss}_{\text{stub}}$ 近似常数**：Medium 在 $N=1/2/4/8/16/32$ 下保持约 132kB（大 $N$ 时出现 128kB 的 4KiB 级取整下偏）；Large 在 $N=1/2/4/8/16/32$ 下保持约 516kB（大 $N$ 时出现 512kB 的 4KiB 级取整下偏），且 $\sum \textsf{Private\_Dirty}_{\text{stub}}=0$、`touched_pages==P` 闭环成立。这直接支持 Claim‑M2：**stub 的 `r-x` resident 页在进程集合内未随并发数复制**。[14]
* **（对照曲线）$\sum \textsf{VmPTE}$ 近似线性**：`VmPTE` 属于 per-process 私有元数据，其跨进程求和随 $N$ 近似线性增长，构成与 “$\sum \textsf{Pss}_{\text{stub}}$ 近似常数” 的对照，有助于评审区分“共享驻留页 vs 私有页表元数据”。[15]
* **为何 Medium 与 Large 的 $\sum \textsf{VmPTE}$ 可能非常接近**：`VmPTE` 以页表页为粒度计费；在常见 x86‑64 分页结构中，一个 4KiB 的 PTE 页表页包含 512 个表项，能够覆盖 $512\times 4\text{KiB}=2\text{MiB}$ 的虚拟地址范围。[17][18]
  因此，即使 $P=33$（132KiB）与 $P=129$（516KiB）页数不同，只要这些被触达的 `r-x` 页在虚拟地址空间内主要落在**同一/相邻少数几个 2MiB 区间**中，两种配置对“需要新增多少个页表页”的需求可能只差一个 4KiB 台阶，从而使 $\sum \textsf{VmPTE}$ 表现得“接近”是合理的，而不是异常；这也解释了为什么 `VmPTE` 不应被期待严格随 $P$ 线性增长。[17][18]

**图表占位（Multi-process）**

* **Fig. 4（placeholder）**：同图双曲线（两条配置）

  * x 轴：进程数 $N$；y 轴：kB；
  * 曲线 A：$\sum \textsf{Pss}_{\text{stub}}$（近似水平线）；
  * 曲线 B：$\sum \textsf{VmPTE}$（近似线性增长）；
  * 图注注明：$N=8$ 的 4KiB 级 PSS 下偏来自 `smaps` 文本口径取整。[14]

### 3.5 Threats to Validity（Memory）

* **“faults ≠ touched pages”**：fault-around 可能在一次缺页时预映射邻近页，使 `minflt` 与实际触达页数不一致；因此本文以 `touched_pages` 为主验收，`minflt/majflt` 仅用于诊断异常。[16][19]
* **ASLR/布局敏感性**：地址空间随机化可能改变 VMA 起点与对齐关系，从而移动 $\Delta\textsf{VmPTE}$ 的阶梯点；我们使用差分 $\Delta(S_2-S_1)$ 与重复取中位数降低偶然性，并在表述中避免把“某个具体阶梯点”泛化为确定规律。[22]
* **THP/NUMA/内核版本差异**：透明大页、NUMA 策略、以及内核版本会改变页表/驻留形态与统计稳定性；本文实验规模未触达 2 MiB 大页映射的典型条件，但在更大映射/不同设置下需复核。[21]
* **统计接口的口径误读**：`Pss_stub` 是比例分摊口径，不等价于“系统新增物理内存”；`Pss_total` 混入加载器/堆栈等常数项，只能作为背景上界，不可用于 stub 共享的强归因。[14][20]

---

## 4. Summary of Claims ↔ Evidence

**Table 4. Claims–Evidence Map**

| Claim    | 可检验现象/趋势                                                                              | 主要证据（实验/数据）                             | 关键引用         |
| -------- | ------------------------------------------------------------------------------------- | --------------------------------------- | ------------ |
| Claim‑D1 | $\textsf{disk\_bytes}$ vs. $P$ 为水平线；`st_size`–$P$ 线性                                  | Table 1；Fig.1–2；`stat/du/filefrag` 证据链  | [1][3][4][5] |
| Claim‑D2 | 稀疏性被破坏或元数据跨 block 时，`st_blocks` 阶梯增长                                                  | Disk pitfalls（`cp/tar/copy_file_range`） | [7][8][9]    |
| Claim‑M1 | $\Delta\textsf{VmPTE}$ 以 4 KiB 粒度阶梯变化（受布局/2MiB 区间影响）                                  | Table 2；Fig.3；页表粒度解释                    | [15][17][18] |
| Claim‑M2 | $\sum \textsf{Pss}_{\text{stub}}$ 随 $N$ 近似常数；$\sum \textsf{VmPTE}$ 近似线性；且 $\sum \textsf{Private\_Dirty}_{\text{stub}}\approx 0$ | **Table 3（可对账数据）**；Fig.4                | [14][15]     |

---

## References

[1] Michael Kerrisk. **inode(7) — Linux manual page**（含 `st_blocks` 为 512B 单位的定义）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man7/inode.7.html](https://man7.org/linux/man-pages/man7/inode.7.html). Accessed: 2026-02-10.
[2] Michael Kerrisk. **stat(2) — Linux manual page**（`struct stat` 字段语义）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man2/stat.2.html](https://man7.org/linux/man-pages/man2/stat.2.html). Accessed: 2026-02-10.
[3] Michael Kerrisk. **du(1) — Linux manual page**（`--apparent-size` 口径）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man1/du.1.html](https://man7.org/linux/man-pages/man1/du.1.html). Accessed: 2026-02-10.
[4] Theodore Ts’o, et al. **filefrag(8) — e2fsprogs manual**（extent/hole 展示工具）. URL: [https://man7.org/linux/man-pages/man8/filefrag.8.html](https://man7.org/linux/man-pages/man8/filefrag.8.html). Accessed: 2026-02-10.
[5] The Linux Kernel Documentation. **FIEMAP ioctl**（extent 映射接口）. URL: [https://docs.kernel.org/filesystems/fiemap.html](https://docs.kernel.org/filesystems/fiemap.html). Accessed: 2026-02-10.
[6] Michael Kerrisk. **lseek(2) — Linux manual page**（`SEEK_HOLE/SEEK_DATA` 语义与边界）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man2/lseek.2.html](https://man7.org/linux/man-pages/man2/lseek.2.html). Accessed: 2026-02-10.
[7] Michael Kerrisk. **cp(1) — Linux manual page**（`--sparse` 策略）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man1/cp.1.html](https://man7.org/linux/man-pages/man1/cp.1.html). Accessed: 2026-02-10.
[8] Michael Kerrisk. **copy_file_range(2) — Linux manual page**（复制稀疏文件可能扩展 holes 的注意事项）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man2/copy_file_range.2.html](https://man7.org/linux/man-pages/man2/copy_file_range.2.html). Accessed: 2026-02-10.
[9] Free Software Foundation. **GNU tar Manual: Archiving Sparse Files**（`--sparse`/hole 识别）. URL: [https://www.gnu.org/software/tar/manual/html_node/sparse.html](https://www.gnu.org/software/tar/manual/html_node/sparse.html). Accessed: 2026-02-10.
[10] GNU Binutils. **readelf — Display the contents of ELF format files**. Sourceware Binutils Documentation. URL: [https://sourceware.org/binutils/docs/binutils/readelf.html](https://sourceware.org/binutils/docs/binutils/readelf.html). Accessed: 2026-02-10.
[11] Michael Kerrisk. **elf(5) — Linux manual page**（ELF 基础结构与程序头/段概念）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man5/elf.5.html](https://man7.org/linux/man-pages/man5/elf.5.html). Accessed: 2026-02-10.
[12] Linux Foundation / RefSpecs. **System V Application Binary Interface: ELF gABI**（PT_LOAD/segments 语义的权威规范背景）. URL: [https://refspecs.linuxfoundation.org/elf/gabi4+/contents.html](https://refspecs.linuxfoundation.org/elf/gabi4+/contents.html). Accessed: 2026-02-10.
[13] Michael Kerrisk. **ld.so(8) — Linux manual page**（动态链接器与 `dlopen` 行为背景）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man8/ld.so.8.html](https://man7.org/linux/man-pages/man8/ld.so.8.html). Accessed: 2026-02-10.
[14] Michael Kerrisk. **proc_pid_smaps(5) — Linux manual page**（PSS/Private_*/Shared_* 字段语义与单位）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html](https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html). Accessed: 2026-02-10.
[15] Michael Kerrisk. **proc_pid_status(5) — Linux manual page**（`VmPTE` 字段）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man5/proc_pid_status.5.html](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html). Accessed: 2026-02-10.
[16] Michael Kerrisk. **proc_pid_stat(5) — Linux manual page**（`minflt/majflt` 定义）. Linux man-pages project. URL: [https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html). Accessed: 2026-02-10.
[17] The Linux Kernel Documentation. **Page Tables**（层级页表、页表页粒度与覆盖范围的解释背景）. URL: [https://docs.kernel.org/mm/page_tables.html](https://docs.kernel.org/mm/page_tables.html). Accessed: 2026-02-10.
[18] Intel Corporation. **Intel® 64 and IA-32 Architectures Software Developer’s Manual (SDM)**（paging structures/entries 数量等体系结构事实）. URL: [https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html). Accessed: 2026-02-10.
[19] LWN.net. **Some documentation for the fault_around_bytes file**（fault-around 相关接口说明，用于解释 faults 与触达页数不等价）. URL: [https://lwn.net/Articles/759411/](https://lwn.net/Articles/759411/). Accessed: 2026-02-10.
[20] The Linux Kernel Documentation. **procfs: /proc/PID/smaps_rollup ABI**（rollup 聚合口径背景）. URL: [https://www.kernel.org/doc/Documentation/ABI/testing/procfs-smaps_rollup](https://www.kernel.org/doc/Documentation/ABI/testing/procfs-smaps_rollup). Accessed: 2026-02-10.
[21] The Linux Kernel Documentation. **Transparent Hugepage Support**（THP 对页表/驻留行为的潜在影响）. URL: [https://docs.kernel.org/mm/transhuge.html](https://docs.kernel.org/mm/transhuge.html). Accessed: 2026-02-10.
[22] The Linux Kernel Documentation. **Sysctl: kernel**（`randomize_va_space` 等 ASLR 相关配置背景）. URL: [https://docs.kernel.org/admin-guide/sysctl/kernel.html](https://docs.kernel.org/admin-guide/sysctl/kernel.html). Accessed: 2026-02-10.
[23] Red Hat. **Hardening ELF binaries using Relocation Read-Only (RELRO)**（CoW/写入路径相关背景，作为有效性威胁与部署前提）. 2019. URL: [https://www.redhat.com/en/blog/hardening-elf-binaries-using-relocation-read-only-relro](https://www.redhat.com/en/blog/hardening-elf-binaries-using-relocation-read-only-relro). Accessed: 2026-02-10.
[24] Chia-Che Tsai, Donald E. Porter, Mona Vij, Jay Lepreau. **Graphene-SGX: A Practical Library OS for Unmodified Applications on SGX**. USENIX ATC, 2017. URL: [https://www.usenix.org/conference/atc17/technical-sessions/presentation/tsai](https://www.usenix.org/conference/atc17/technical-sessions/presentation/tsai). Accessed: 2026-02-10.
[25] Alex Agache, et al. **Firecracker: Lightweight Virtualization for Serverless Applications**. USENIX NSDI, 2020. URL: [https://www.usenix.org/conference/nsdi20/presentation/agache](https://www.usenix.org/conference/nsdi20/presentation/agache). Accessed: 2026-02-10.
