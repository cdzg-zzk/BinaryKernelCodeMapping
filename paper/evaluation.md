下面是一份**可直接当作你论文 Evaluation 章节的“实验指导文档（Evaluation Plan）”**的总结版。它以你的系统为中心（page cache / xarray 重定向 + 用户态链接 stub + 缺页填 PTE），并显式强调：**我们只评估“与内核上下文无关（kernel-context independent）”的函数**。

---

# Evaluation Plan：用户态复用内核二进制代码页的有效性评估指南

## 0. 背景与系统简述（写在 Evaluation 开头的 3–5 行）

本工作提出一种二进制层面复用内核代码的机制：构造一个 stub 动态库，并将该文件在页缓存中对应的 `i_pages`（xarray）重定向，使其 `.text` 页映射到内核代码所在的物理页。用户进程链接 stub 后，当访问该 `.text` 页触发缺页时，内核可通过 page cache 命中并填充 PTE，最终使用户态能直接执行这些内核代码页。

**评估范围限定**：本文仅讨论并评估**与内核上下文无关**的函数，即函数语义不依赖 `current`/task、锁、调度状态、per-cpu 数据结构、特权寄存器、内核内存对象等（见第 3 节定义与筛选）。

---

## 1. 评估目标与研究问题（RQs）

建议你把 evaluation 明确组织成 4 个问题（每个问题对应一组图/表）：

* **RQ1：稳态性能（steady-state）**
  在页表已建立、代码页已驻留的情况下，你的机制执行这些函数的延迟/吞吐，相比用户态 baseline 如何？

* **RQ2：首次触达成本（cold-start / first-touch）**
  新进程第一次调用某个复用函数时的额外开销来自哪里（缺页、页表建立、符号绑定等），与常规动态库加载相比如何？

* **RQ3：内存共享与可扩展性（multi-instance scaling）**
  当 N 个进程/容器同时使用同一组函数时，你的机制能否降低“新增实例的增量物理内存”，并保持可扩展性？

* **RQ4：系统代价与干扰（overhead / interference）**
  该机制对内核路径（缺页、page cache、xarray）带来的 CPU/锁竞争/时延开销是否可控？对其他负载的干扰程度如何？

---

## 2. Baseline 设计：你提出的 baseline 是否合理？

### 2.1 主 baseline（推荐、合理、必须有）

你提出的观点是正确的：**主 baseline 应该是“用户态同等实现 + 以动态库形式正常链接调用”**。

原因：你的贡献点是“二进制层面复用/共享内核代码页、减少重复映射与加载”，而不是算法本身。用同等实现的用户态 `.so` 作为 baseline，能最大程度隔离以下混杂因素：

* kernel vs user 的执行语义差异（特权级、可抢占、调度、copy 路径）
* syscall/IPC 的额外开销（会掩盖你机制的真正成本/收益）

**结论**：把“映射出来的函数”直接和“内核态完成同功能”做性能对比，不适合作为主 baseline；可以保留为补充对照（见 2.3）。

### 2.2 主 baseline 的两种实现方式（建议都做）

* **Baseline A1（最干净）**：同一份源码/同一算法在用户态编译成 `.so`（同优化等级 `-O3 -march=native`），用户态正常调用。
  目的：证明差异来自“机制”，不是来自“实现/算法”。

* **Baseline A2（工程现实）**：主流用户态库（例如 OpenSSL / xxhash / zstd 等）
  目的：证明你不仅对比“自己编的对照组”，也对比“真实世界的成熟实现”。

### 2.3 可选补充 baseline（建议有则加分）

* **Baseline B（官方内核用户态接口）**：若该功能存在 AF_ALG / vDSO / ioctl 等官方接口，可作为“参考对照”。
  这不替代主 baseline，而是回答审稿人：“若用户想用内核实现，传统路径要付出多大代价？”

### 2.4 Ablation（强烈建议）

为了在论文里证明“你提出的 xarray 重定向 + page cache 命中”是关键因素，建议加入以下 ablation（至少 1 个）：

* **Ablation 1：stub 动态库不重定向（普通 `.so`）**
  即：同样的 stub 文件，但 `.text` 页来自文件自身，不指向内核物理页。
  → 用来拆分 “动态链接/调用开销” vs “你机制的映射与共享效益”。

* **Ablation 2：关闭预热/批量触页（如果你做了）**
  → 用来解释 cold-start 曲线。

---

## 3. 关键限定：什么叫“与内核上下文无关”？（必须写清楚）

### 3.1 定义（可以直接写进论文）

我们定义一个函数为 **kernel-context independent**，当且仅当：

1. 其输出仅依赖输入参数（包括指向用户缓冲区的数据）与局部状态；
2. 不依赖内核线程/进程上下文（如 `current`、cred、namespace、per-cpu 等）；
3. 不需要持有内核锁/关抢占/关中断来保证语义正确；
4. 不访问内核动态内存对象或内核地址空间中的数据结构（除非这些数据页也被显式映射并作为只读常量处理）；
5. 不执行特权指令，不依赖 ring0-only 的硬件状态。

### 3.2 二进制层面的“可映射性”约束（你实操中更重要）

即便函数语义独立，它仍可能**在二进制层面引用内核全局常量/表**（例如 CRC table），导致只映射 `.text` 失败。为此建议在实验集中明确区分：

* **Type T（Text-only）**：只依赖寄存器/栈/参数指针，不读写任何外部全局地址
  → 最适合你当前“只映射 `.text`”的机制

* **Type TR（Text + Read-only）**：依赖只读常量表（`.rodata`）
  → 若你未来扩展到同时映射 rodata 页，这类可加入；否则作为限制说明

* **Type TD（Text + Writable global）**：依赖可写全局状态
  → 建议明确“不支持/不评估”，避免引入共享一致性与安全语义争议

### 3.3 筛选方法（让审稿人信服你不是“挑软柿子”）

建议你在论文里写一个可复现的筛选流程：

* 从候选目录（如 `lib/`, `crypto/`）选取若干候选符号
* 对每个候选函数进行二进制检查：

  * 是否存在对固定地址/全局符号的访存（尤其是绝对地址形式）
  * 是否调用外部函数（如有则需要闭包映射或剔除）
* 将通过检查的函数按第 4 节分类抽样，构成最终 benchmark set

---

## 4. 函数集合如何分类以保证多样性？（只选“上下文无关”仍要多样）

建议按下面 4 个维度做“分桶抽样”（每桶选 1–3 个函数）：

### 4.1 指令 footprint（与你的页粒度机制强相关）

* **Small**：< 1 页 `.text`（强调“调用/分支预测/PLT 开销”）
* **Medium**：1–4 页（强调“首次缺页 + iTLB/I$ 行为”）
* **Large**：> 8 页（强调“多页映射、指令 working set”）

### 4.2 工作负载特征

* **compute-bound**（每字节计算多）：哈希/压缩 transform、加密轮函数等
* **memory-bound**（流式搬运为主）：字节处理/简单变换
* **branch-heavy**：条件分支/数据依赖明显（对分支预测敏感）

### 4.3 调用模式（影响 cold-start 与稳态）

* **many small calls**：小输入高频调用（凸显开销差异）
* **few large calls**：大输入低频调用（凸显吞吐/带宽）

### 4.4 指令特性

* scalar-only
* SIMD-heavy（可选，解释更复杂，但更有代表性）

> 注意：这里的分类和“是否 I/O 密集”不同，因为你限定了“与内核上下文无关”，通常 I/O 密集函数本身很难满足条件。你应把“系统行为差异”聚焦在：**缺页/页表/指令缓存/共享**上，而不是块设备/网络 I/O。

---

## 5. 微基准（Microbench）实验矩阵

### 5.1 Micro-1：稳态延迟/吞吐 vs 输入规模（回答 RQ1）

对每个函数，做 input size sweep（如 64B→4MiB 指数增长）：

* **对比组**：你的机制 vs Baseline A1（同等实现 `.so`） vs Baseline A2（主流库）
* **指标**：ns/op、GB/s、p50/p99
* **解释性指标（建议）**：cycles、instructions、I$ misses、iTLB misses、branch-misses

**呈现方式**：

* 图 1：size–throughput 曲线（每个实现一条线）
* 图 2：size–latency 曲线（小 size 区域放大）

### 5.2 Micro-2：cold-start / first-touch 成本（回答 RQ2）

对每个函数测：

* **Cold**：新进程第一次调用，或刻意使映射失效后第一次调用
* **Warm**：同进程第二次调用（页表已建立）

**指标**：

* 首次调用 wall time
* minor faults / major faults 数量
* 建立映射的页数（触达了多少 `.text` 页）

**呈现方式**：

* 表：cold vs warm 的时间与 fault 数
* 图：随着函数 footprint 增大，cold 成本如何增长

### 5.3 Micro-3：多进程/多实例内存共享曲线（回答 RQ3）

启动 N 个进程（N=1,10,50,100,500,1000）同时调用同一组函数：

**指标（推荐写成“增量曲线”）**：

* 每新增一个实例的 ΔPSS（或 ΔRSS，但 PSS更好）
* `.text` 映射区域的 PSS
* 系统总内存变化（作为辅证）

**呈现方式**：

* 图：N–Δmemory（每个实现一条线）
  你希望你的机制曲线“接近水平”，baseline 可能更陡（尤其当 baseline 由于 inode/版本不同无法共享 page cache 时）。

### 5.4 Micro-4：并发与线程可扩展性（补充 RQ1/RQ4）

线程数：1/2/4/8/16（固定总输入量或固定每线程输入量）

* 指标：吞吐、p99、CPU 利用率
* 目的：证明你的机制不会在某个共享点（例如映射/元数据路径）引入严重锁竞争

---

## 6. 系统代价与干扰（回答 RQ4）

建议至少做一个“co-run”实验：

* 基准负载：任选你方便复现的（编译、压测服务、fio 等）
* 干扰负载：若干进程持续调用你的复用函数（高频小输入 + 大输入两种模式）
* 对比：不开启你的机制 vs 开启你的机制

**指标**：

* 基准负载吞吐/延迟变化比例
* 内核 CPU 时间、context switch、fault 相关统计
  -（可选）锁竞争/热点函数（perf top / ftrace）

---

## 7. 实验环境与方法学规范（避免被审稿人挑刺）

* CPU 亲和性：固定到同一核（或固定 NUMA 节点）
* 禁止频率波动：performance governor / 记录 turbo 状态
* 统一编译与链接：baseline 与你的机制用相同优化等级、相同调用约定
* 预热：每个点 warmup（避免首次解析/缓存噪声）
* 统计：每点重复 ≥5 次，报告均值+方差或中位数+IQR
* 输出：建议 CSV，便于画图与复现

---

## 8. 结果叙事模板（顶刊常用写法）

你可以按如下顺序写 evaluation 小节：

1. **Correctness**：三方一致性 + 边界输入
2. **Steady-state performance (RQ1)**：size sweep 曲线 + 解释（I$ / iTLB）
3. **Cold-start (RQ2)**：first-touch 时间与 faults 分解
4. **Memory scaling (RQ3)**：N–Δmemory 曲线（最能量化你的优势）
5. **Overhead (RQ4)**：co-run 干扰结果 + 内核热点分析
6. **Limitations**：例如 text-only 限制、全局表/rodata 的影响与未来扩展方向

---

## 9. 你这条路线的“最关键提醒”（一句话总结）

即使函数语义上“与内核上下文无关”，**二进制层面仍可能依赖内核全局常量/表**；因此你必须在 evaluation 中显式报告“函数筛选标准/可映射性类型”，并把实验集覆盖到不同 footprint 与不同 compute/memory 特征，才能让审稿人相信你评估的全面性与可复现性。

---

如果你愿意，我可以在这份文档基础上再给你补一个“**Evaluation Checklist（逐项打勾）**”版本，以及一个“**最小实验集（8–12 个函数）建议表**”（每个函数标注：Type T/TR、代码页数、输入规模、对应图表、预期现象）。你只要把你目前已经能稳定映射执行的候选符号名列出来即可。



你这个“全局观”非常关键：**论文的 evaluation 不是在评估 xxHash 算法，而是在评估你的“函数级复用/映射机制”**。所以一个好的 Evaluation 章节要回答的不是“XXH32 快不快”，而是这些更通用的问题：

* **(Q1) 机制能否显著减少 cold-start 成本**（尤其是 major page fault / I/O 等待）？
* **(Q2) steady-state 性能是否几乎不受影响**（call overhead、IPC、分支、cache/TLB）？
* **(Q3) 内存开销是什么形态**（页表/VMA 元数据 vs 代码页复用），多进程下是否更划算？
* **(Q4) 扩展性/边界如何**（映射的函数数量、代码 footprint、别名映射对 iTLB 的上限影响）？
* **(Q5) 能否在“公认工程/套件”里复现收益**（让读者信服你不是在做“手写 demo”）？

下面我给你一套“Evaluation 章节可以直接照着写”的实验体系：**微基准解释机制 + 敏感性实验给上限 + 宏基准用公认套件背书**。整个体系仍然是“函数级”的，不会脱离你的实现。

---

## 1) 工作负载怎么选：别纠结“必须大程序”，你要的是“代表性轴”

你可以把函数（workload）按三个轴选，做到“既真实、又能覆盖 iTLB/iCache、内存开销”：

### 轴 A：函数代码 footprint（iTLB/iCache 的关键）

* **1 页以内**：最贴近你现在的典型用法（1～2 个函数页）
* **多页（4KB～64KB）**：用来观察 iTLB/iCache 的拐点
* **更大（>64KB）**：作为压力上限（敏感性/边界分析）

### 轴 B：使用场景（你机制的价值点）

* **cold-start / 短命进程**：你的机制最容易赢（避免 major fault / I/O）
* **长跑热态**：你的机制应该“几乎不输”（证明无副作用）

### 轴 C：函数类别（证明普适性，不是只对 hash）

推荐你至少选 2～4 类（每类 1 个函数即可）：

1. **校验/哈希类**（你已经有 xxHash，保留即可）
2. **安全/内核常用 PRF 类**：例如 SipHash（内核有专门文档与实现，属于常见基础组件）。([Kernel Documentation][1])
3. **压缩/解压类（大 footprint，最适合 iCache/iTLB 观察）**：内核里有 LZ4 解压实现（`lib/lz4/lz4_decompress.c`）。([CodeBrowser][2])
4. **CRC 类（常见、可硬件加速、内核有模块/crypto 路径）**：libcrc32c 在内核配置里是明确存在的库模块。([KernelConfig][3])

> 这四类的共同点：都容易做成“纯函数/无特权访问”的接口，符合你把它们导出到用户态执行的前提。

---

## 2) baseline 怎么选：让读者信服你评估的是“机制差异”

你至少需要这 3 个对照（每个都很自然）：

1. **User-DynLib（普通动态库）**

   * 代表“传统做法”：从文件系统读入 + page cache + relocation（容易出现 major fault）

2. **User-Static（静态链接或内置实现）**

   * 代表“没有 dlopen/动态加载”的理想上限（但会把代码带进每个二进制/镜像里）

3. **Your-Reuse（你的机制）**

   * 你主张的方案：避免读取库文件页，降低 cold fault；多进程无需把同一份库文件引入 page cache

> 如果你觉得静态链接不方便做，也可以用 “User-Preload/Warmup（提前 dlopen + madvise WILLNEED）” 当作第三个 baseline；但静态链接在论文里通常更有说服力，因为它是“最佳情况上限”。

---

## 3) Evaluation 章节结构建议（可以直接用作小节标题）

### 5.1 Experimental Setup（实验设置）

写清楚：CPU 隔离（你现在的 CPU3 很好）、pin、重复次数、统计方法（median/p95/CI）、内核版本、perf 事件。

### 5.2 Correctness（正确性）

对每个导出函数：随机输入 + 边界输入 + 与 baseline 输出逐字节一致；跑 1e6 组也不夸张。

### 5.3 Cold-start latency & page faults（冷启动与缺页）

**核心要点：用“major/minor fault + time breakdown”证明机制价值**

* 指标：

  * cold first-call latency（你已做）
  * `major-faults / minor-faults`（你已用 ftrace 很漂亮）
  * 可再加：`read_bytes`（如果你能从 cgroup 或 /proc 拿到 I/O 统计）

* 场景：

  * **drop cache** 后第一次调用（把“major”稳定触发出来）
  * 内存压力下的第一次调用（reclaim 以后更真实）

### 5.4 Steady-state performance（热态吞吐/开销）

证明“你机制不是靠偷懒赢的”，热态不应该引入额外 overhead：

* 指标（perf）：

  * cycles / instructions（IPC）
  * branches / branch-misses
  * cache-misses（作为背景）
  * iTLB / iCache 相关事件（见后面 5.6）

### 5.5 Memory footprint（内存占用）

这节不是看“函数占多少 KB”，而是看“机制带来的额外内存形态”：

* 单进程差分：`PageTables`、`VmPTE`、`maps 行数(VMA数量)`
* 多进程：PSS/RSS 随进程数增长曲线（N=1,2,4,8,16,32,64…）

这能把你的优势讲清楚：

* 传统动态库：会把“库文件页”引入 page cache（系统层面的文件页占用），并且每进程也有一部分私有映射/元数据
* 你的机制：复用内核常驻 text 的物理页，不需要把用户态库文件页读入（尤其 cold-start / 容器冷机时）

### 5.6 iTLB/iCache analysis（微架构一致性/边界）

你担心“iTLB/iCache 属于宏基准”——其实不是。**它非常适合用 microbench/敏感性实验做**，业界也有专门用 microbench 压 microarchitecture 的套件，比如 uarch-bench。([GitHub][4])

这节建议分成两部分（这样写最不尴尬）：

**(A) Typical-case（真实用法：只映射 1～2 个函数）**
目标：证明“几乎没有副作用”。
预期：iTLB/iCache miss 很低、Your-Reuse 与 user baseline 无显著差异（这是合理结论）。

**(B) Sensitivity / Worst-case（上限：人为放大信号）**
目标：回答审稿人会问的“那如果映射很多函数/很多别名呢？”
你可以做两个 sweep（非常契合函数级机制）：

* **Alias sweep（iTLB 压力）**：同一物理代码页映射到 K 个不同虚拟地址，轮询调用，观察 iTLB misses 随 K 增长
* **Footprint sweep（iCache 压力）**：构造 4KB/16KB/64KB/256KB 的导出函数（或导出一组对齐页的函数），观察 L1I miss / IPC 的拐点

> 这两种都不需要“大程序”，但能把 iTLB/iCache 的结论写得很硬。

### 5.7 Case Studies with public benchmarks（用公认套件做案例）

这是你想要的“最有说服力”部分：让别人能复跑。

我建议你用 **Phoronix Test Suite (PTS)** 做这节的框架，因为它提供自动化下载/安装/执行/汇总结果，且强调可复现性。([Phoronix Test Suite][5])

PTS 里有直接相关的测试：

* **compress-lz4**：测 LZ4 对 silesia 数据集的压缩/解压时间（可用于把你导出的 LZ4 解压函数接进来，或做“冷启动多次运行”的对比）。([OpenBenchmarking][6])
* **compress-zstd**：测 zstd 对样例数据的压缩/解压（如果你未来导出 zstd 解压/校验相关函数）。([OpenBenchmarking][7])
* **smhasher（PTS profile）**：hash 测试与速度评估的公认套件入口，PTS 已经封装好。([OpenBenchmarking][8])

另外，如果你还想保留你最初 xxhash 的权威性，也可以用：

* **xxhsum benchmark 模式**（`-b`、`-i`、`-B` 等）当作“官方提供的基准入口”。([Chromium Git Repositories][9])

> 这样写出来，读者会看到：你的 microbench 解释机制；PTS case study 证明“放到公认套件里也能复现”。

（可选）如果你有 SPEC CPU2017 许可，也可以提一句它是 industry-standard 的 CPU-intensive 套件，但它对你这种“函数级机制”不一定最敏感，而且是商业授权。([SPEC][10])
更实际的还是 PTS + 你自己的可控实验。

---

## 4) 你“自己写测试程序”是否正规？怎么写才显得正规？

**正规与否不取决于“是不是别人写的 benchmark”，而取决于你是否做到：可复现、可解释、可对照、可统计。**

你可以用两种方式让它“论文级正规”：

### 方式 1：用成熟 microbenchmark 框架包住你的函数

例如 Google Benchmark 是专门做 microbench 的库，写法标准化、统计规范。([GitHub][11])
它甚至支持集成性能计数器（依赖 libpfm 等）。([Google GitHub][12])

### 方式 2：你继续用自己写的 harness，但要补齐“规范要素”

在论文里明确写：

* 固定 CPU（你 CPU3 隔离已经很加分）
* 每个点测 N 次（比如 30～100），报告 median + p95 + 置信区间
* cold 的定义（drop caches / 内存压力 / 首次触达）
* warm/hot 的定义（预热次数/时间）
* 采集指标：time + faults + perf counters + memory stats

做到这些，审稿人一般不会因为“你自己写 harness”否定它——lmbench/uarch-bench 这类公认工具本质上也是 microbench 集合。([LMbench][13])

---

## 5) 给你一个“最小但完整”的实验组合（我建议你就按这个写 Evaluation）

### A. 微基准（机制核心）

1. **冷启动首次调用**（drop cache）：time + major/minor faults + ftrace 解释路径
2. **热态吞吐**：cycles/call、IPC、branch-miss
3. **内存差分**：PageTables/VmPTE/VMA、单进程 + 多进程扩展

### B. 敏感性（iTLB/iCache 与规模边界）

4. **alias-sweep（iTLB）**：K=1..1024（或到你机器 iTLB 容量附近出现拐点即可）
5. **footprint-sweep（iCache）**：4KB..256KB（构造导出函数或函数组）

### C. 公认套件 case study（背书）

6. **PTS compress-lz4 / smhasher / compress-zstd（至少选 1～2 个）**：展示“在公认框架下同样成立”。([OpenBenchmarking][6])

这三层合起来，你就不会被解读成“只是在跑一个 hash 函数”。

---

## 6) 最关键的一句话：你要在论文里怎么“定调”避免被误解成评估算法？

你可以在 Evaluation 开头明确写（意思类似）：

> “We evaluate the *mechanism* rather than any particular algorithm. The exported functions are selected as representative kernels of different instruction footprints and usage patterns. For each workload,用相同输入、相同实现逻辑，对比不同交付方式（dynlib/static/our mapping）。”

然后你再把函数换成 xxhash/siphash/lz4_decompress/CRC 等都只是“代表性 workload”。

---

如果你把你当前“导出函数的约束”简单列一下（比如：不能调用其它内核符号？能否导出一组函数？能否同一物理页多次映射到不同 VA？），我就能把上面这套方案进一步收敛成：

* **你论文里最终建议选的 4～6 个函数列表**（每个对应哪个 evaluation 小节）
* **每个实验的可执行脚本结构**（run → perf stat → smaps_rollup → 汇总成 CSV）
* 以及你应该画的 6～8 张图（最常见的 evaluation 图谱：CDF、bar、scaling curve、MPKI 曲线等）

[1]: https://docs.kernel.org/security/siphash.html?utm_source=chatgpt.com "SipHash - a short input PRF"
[2]: https://codebrowser.dev/linux/linux/lib/lz4/lz4_decompress.c.html?utm_source=chatgpt.com "lz4_decompress.c source code [linux/lib/lz4 ..."
[3]: https://www.kernelconfig.io/config_libcrc32c?utm_source=chatgpt.com "config_libcrc32c - kernelconfig.io"
[4]: https://github.com/travisdowns/uarch-bench?utm_source=chatgpt.com "travisdowns/uarch-bench: A benchmark for low-level CPU ..."
[5]: https://www.phoronix-test-suite.com/?utm_source=chatgpt.com "Phoronix Test Suite - Linux Testing & Benchmarking Platform ..."
[6]: https://openbenchmarking.org/test/pts/compress-lz4?utm_source=chatgpt.com "LZ4 Compression Benchmark"
[7]: https://openbenchmarking.org/test/pts/compress-zstd?utm_source=chatgpt.com "Zstd Compression Benchmark"
[8]: https://openbenchmarking.org/test/pts/smhasher?utm_source=chatgpt.com "SMHasher Benchmark"
[9]: https://chromium.googlesource.com/external/github.com/Cyan4973/xxHash/%2B/refs/tags/v0.7.2/xxhsum.1.md?utm_source=chatgpt.com "xxhsum(1) -- print or check xxHash non-cryptographic ..."
[10]: https://www.spec.org/cpu2017/?utm_source=chatgpt.com "SPEC CPU ® 2017 benchmark"
[11]: https://github.com/google/benchmark?utm_source=chatgpt.com "google/benchmark: A microbenchmark support library"
[12]: https://google.github.io/benchmark/perf_counters.html?utm_source=chatgpt.com "benchmark | A microbenchmark support library - Google"
[13]: https://lmbench.sourceforge.net/?utm_source=chatgpt.com "LMbench - Tools for Performance Analysis"

