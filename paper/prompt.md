下面我给你一套**更“可辩护/可复现/可落地”**的内存评估方法（SOSP/OSDI 风格），把你提出的三个维度（Scalability / Granularity / Metadata cost）做成一条严谨证据链，并补上审稿人最可能抓住的漏洞与“怎么实现”的细节。

我会先指出你方案里**需要修正/加强**的点，然后给出一套“实验框架 + 3 个主实验 + 2 个强力补充实验 + 可复现实验脚手架”的完整方案。

---

## 0) 先把“你要证明的内存优势”定义清楚（否则指标会被 reviewer 打穿）

你说“内存开销小”，在 OS 论文里通常至少要区分这三层：

1. **用户态实例集合的“归因物理内存”**：这才是你想强调的“随 N 扩展不增长/增长极小”。

   * 推荐主指标：**Sum(PSS)**（全实例 PSS 求和）
   * 理由：PSS 是按共享进程数对共享页分摊的比例集合大小；内核文档对 PSS 的定义就是“每页除以共享进程数再求和”。 ([Kernel.org][1])

2. **内核侧的“元数据与页表开销”**：你机制可能把成本从用户态搬到了内核。

   * 推荐：**cgroup v2 的 memory.stat / memory.current / pagetables / slab / kernel_stack** 来做归因统计。cgroup v2 文档明确给出了 memory.current 和 memory.stat 的含义与字段解释。 ([Kernel Documentation][2])

3. **文件系统/页缓存层的“共享前提”**：baseline 可能并不是你想象的 O(N)。

   * Linux page cache 是以 **address_space（通常绑定 inode）** 组织与管理的（同 inode 才天然共享）。 ([Kernel.org][3])
   * 容器里 OverlayFS 的 inode/st_dev 行为复杂，st_ino/st_dev 可能不稳定或不一致；这会影响“是否共享页缓存”的可辩护性。 ([Kernel Documentation][4])

**结论：**你论文里必须把“我们衡量的内存开销”写成一段清晰定义：

* “我们报告实例集合的归因物理内存（Sum PSS）以及同一工作负载下的 memcg kernel/page-table/slab 归因开销。”

---

## 1) 你原先想法中最需要“修正”的三点（避免审稿人一拳打回）

### 修正 1：Static Linking ≠ 必然 O(N)

如果你启动的是**同一个二进制文件 inode 的 N 个进程**，即便是静态链接，**text 段仍然是 file-backed 映射**，Linux 仍会通过 page cache 共享这些代码页；这时你的“static baseline 线性增长”就不成立，会被 reviewer 指出“你在做错误对比”。

**你要做的 baseline 应该是**：

* “**每个实例都有自己 inode 的代码副本**”（容器镜像差异、不同 overlay mount、或你人为复制出 N 份二进制/so 文件到不同 inode）
  这样才模拟真实世界里“同一代码由于文件身份不同无法共享页缓存”的场景（尤其是跨镜像版本/跨 rootfs）。

### 修正 2：dlopen 的库“映射大小”不等于“驻留物理内存”

动态库一般也是 demand paging：你 dlopen 了 2MB 的库，不等于立刻增加 2MB RSS/PSS。你必须**实际测 resident pages（mincore / PSS 的 delta）**，否则数字会被认为不可信。

mincore(2) 可以返回一个向量，指示某段虚拟地址范围内的页是否 resident。 ([man7.org][5])

### 修正 3：PSS 很好，但你必须控制 THP/KSM 等影响

内核文档明确提到：在某些配置/大页情况下 PSS 可能出现近似或语义变化。 ([Kernel.org][1])
因此严谨做法是：

* **禁用 THP** 或至少报告 THP 状态并做敏感性分析
* **禁用 KSM**（否则 baseline 可能被 KSM 额外去重，掩盖你的贡献）

---

## 2) “统一实验脚手架”：把可复现性做扎实（SOSP/OSDI 审稿人很看重）

### 2.1 实验环境控制（写进论文 Appendix / Artifact）

建议你至少控制这些开关：

* **Swap**：关闭（或设置 memory.swap.max=0），避免 swap 干扰 PSS 与 memcg。
* **THP**：`echo never > /sys/kernel/mm/transparent_hugepage/enabled`
* **KSM**：`echo 0 > /sys/kernel/mm/ksm/run`
* **CPU 频率**：固定 governor（避免 run-to-run 波动）
* **NUMA**：固定到单节点（`numactl --cpunodebind=0 --membind=0`）
* **Drop caches（冷启动实验用）**：`echo 3 > /proc/sys/vm/drop_caches`（注意先 sync）

### 2.2 强烈建议：用 **cgroup v2** 把被测进程“装进盒子里”

原因：

* `memory.current` 是这个盒子里任务及其后代的总内存使用；并且 memcg 追踪用户态页缓存/匿名内存、以及内核数据结构（dentry/inode 等）等多种内存。 ([Kernel Documentation][2])
* `memory.stat` 还能拆出 anon/file/pagetables/slab/kernel_stack 等：这正好对应你论文的 3 个维度（共享粒度、扩展性、元数据成本）。 ([Kernel Documentation][2])

**最简用法（示意）**：

```bash
# 挂载 cgroup2（很多发行版已默认）
mount | grep cgroup2 || sudo mount -t cgroup2 none /sys/fs/cgroup

# 创建实验 cgroup
sudo mkdir -p /sys/fs/cgroup/zkcr
# 确保 memory controller 启用（父 cgroup）
echo "+memory" | sudo tee /sys/fs/cgroup/cgroup.subtree_control

# 给实验设置 hard limit（可选）
echo $((16*1024*1024*1024)) | sudo tee /sys/fs/cgroup/zkcr/memory.max
```

启动进程后，把 pid 写进 `cgroup.procs`：

```bash
echo $PID | sudo tee /sys/fs/cgroup/zkcr/cgroup.procs
```

采样：

```bash
cat /sys/fs/cgroup/zkcr/memory.current
cat /sys/fs/cgroup/zkcr/memory.stat
cat /sys/fs/cgroup/zkcr/memory.peak
```

### 2.3 PSS 采样：用 smaps_rollup，而不是 smaps

* `/proc/PID/smaps_rollup` 是把 smaps 所有 VMA 的字段预先求和汇总成一条 `[rollup]`，更易采集、开销更低。 ([Kernel.org][6])
* 你仍然能拿到 PSS / Pss_Anon / Pss_File / Pss_Shmem 等关键信息。 ([Kernel.org][1])
* PSS 的定义（按共享进程数分摊）来自内核文档，直接引用即可。 ([Kernel.org][1])

采样方式：

```bash
cat /proc/$PID/smaps_rollup | egrep 'Pss:|Pss_Anon:|Pss_File:|Pss_Shmem:|Private_Dirty:|Private_Clean:'
```

> 论文里推荐写：我们对所有实例做 Sum(PSS)，并额外报告 Sum(Pss_File) 来单独观察可共享的 file-backed 成分。

---

## 3) 实验一：扩展性（Scalability）——把“Flat Line”做成铁证

### 3.1 你要对比的组应该至少有 4 个（避免 reviewer 说你挑软柿子）

你原先只有 Static / Dynamic / Yours。我建议补一个“Best-case dynamic sharing”，否则 reviewer 会说：

> “你这个就是把不同 inode 统一了，那我 bind-mount 同一个 so 不就行？”

所以组别建议：

1. **Baseline A: Private-code（最坏情况）**

* 每实例拥有独立 inode 的同内容二进制/so（通过复制 N 份文件或不同 overlay mount 实现）
* 目的：模拟“同内容但不共享页缓存”的真实容器/镜像差异场景

2. **Baseline B: Best-case Dynamic（最强对手）**

* 所有实例从同一 host path bind-mount 同一个共享 so（同 inode），动态链接
* 目的：证明你至少不比“理想条件下的共享库”差，并强调你的价值在于**跨镜像/跨文件身份**也能达到类似共享

3. **Baseline C: Static（可选）**

* 如果你要展示“语言生态导致共享困难”（Go/Rust 静态大包），请明确实验条件：不同服务二进制本来就不同 inode
* 注意别用“同一 binary 的 N 进程”去当 static O(N) baseline

4. **Yours: Stub DSO + page cache redirection**

### 3.2 实验步骤（可直接变成 artifact 脚本）

**核心是：统一工作负载 + 同一时刻采样 + 排除启动期抖动。**

**工作负载建议（可控、可重复、只触达目标代码）：**

* 每个实例做三阶段：

  1. `dlopen`/链接初始化（或你的 stub attach）
  2. **调用目标函数一次**（确保代码页真的被触达并建立映射）
  3. `pause()` 或 `sleep(300)`（进入稳定态，方便采样）

**同步启动（非常重要）：**

* 用 barrier（管道/futex）让 N 个进程都“就绪后一起触发第 2 阶段调用”，避免不同实例触页时序影响共享统计。

**采样（稳定态时）：**

* 采集每个 pid 的 `smaps_rollup`，累加得到：

  * `SumPss`
  * `SumPss_File`
  * `SumPss_Anon`
* 同时采集 cgroup：

  * `memory.current`
  * `memory.stat` 中的 `anon/file/pagetables/slab/kernel_stack`

cgroup 的字段含义是内核文档明确给出的，可直接引用。 ([Kernel Documentation][2])

**画图：**

* X：N（建议 1, 2, 4, …, 1024/2048，指数级更清晰）
* Y：

  * 图 1：`SumPss`（GB）
  * 图 2（堆叠更好）：`SumPss_File + SumPss_Anon`（看共享主要发生在 file 还是 anon）
  * 图 3：`pagetables + slab + kernel_stack`（来自 memory.stat，展示元数据成本随 N 的增长）

### 3.3 你要在论文里写的“可辩护结论形式”

不仅说“flat”，而是量化“边际成本”：

* 拟合：`SumPss(N) = a + b*N`
* 报告：`b` 的均值与 95% CI（重复 5-10 次）
* 你的 claim 变成：“b≈0（与 baseline 的 b 显著不同）”

### 3.4 必做的 Sanity Check（审稿人最爱问）

1. **证明 baseline 的确“不共享”**

* 直接在论文里给出 `/proc/PID/maps` 中映射的 dev:inode/path 证据，或 `stat -c '%d:%i %n'` 列出 so/binary 的 inode 不同。
* 这是关键，因为 Linux 的页缓存共享与“是否同 inode”强相关（page cache 由 address_space 管理）。 ([Kernel.org][3])

2. **证明你的机制真的“共享 PFN/页帧”**（强证据）

* 如果你能以 root 读取 `/proc/PID/pagemap`，抽样比对相同 stub offset 的 PFN 是否一致（或用你内核模块导出的 debugfs 计数）。
* 论文里放一个小表：随机抽 100 个页，`#unique PFN` vs N。

---

## 4) 实验二：共享粒度（Granularity）——把“按需/按页付费”做成“可重复”的实验

你原先“只用 crc32 就只占 1-2 页”的叙述思路是对的，但需要更严谨的实现方式，否则 reviewer 会说“你只是拍脑袋估算”。

### 4.1 把自变量从“函数名”变成“触达的代码页数”

最严谨的做法是设计一个 microbenchmark：

* 有一个“函数集合”`F(k)`，保证它们落在尽量不同的代码页上（至少不同 4KB page）。
* 让程序只调用前 k 个函数（或只执行 k 个不同 page 的指令）。

然后报告：

* `Δ SumPss_File` 随 k 的增长
* `Δ pagetables` 随 k 的增长（因为映射更多页会增加页表开销）
* `# minor faults`（建立映射时的缺页）

### 4.2 “resident pages 计数”：用 mincore + 自己的 mapping 地址

在用户态拿到 stub 映射区间 `[addr, addr+len)` 后：

* 调用 `mincore(addr, len, vec)`，统计 vec 中 resident=1 的页数
  （mincore 文档明确：返回调用进程虚拟内存页是否 resident。 ([man7.org][5])）

这能让你把实验二写得非常像系统论文：

* X：k（调用函数数/页数）
* Y：resident pages / ΔPSS / Δfaults

### 4.3 对比组怎么选才公平

* **Std shared lib**：同样做 k 个函数调用，但函数来自用户态库（你可以把同一份源码编成 userland so）
* **Library OS (LKL/Rump)**：运行同样功能所需的最小实例，报告其 `memory.current` 与 `kernel`/`slab`/`pagetables` 的底噪（footprint floor）

你原先写的“libcrypto 2MB+”要改成**测出来是多少写多少**。正确姿势是：

* 报告 `dlopen + call` 之后的 `ΔPss_File/ΔPss_Anon`
* 报告 `mincore` 的 resident page 数
  这样 reviewer 很难反驳。

---

## 5) 实验三：内核元数据成本（Metadata Cost）——用 memcg + slab 双证据防守

你原先担心 reviewer 会问“你是不是把成本搬到内核里”，这个担心非常准确。做法建议如下：

### 5.1 第一层证据：cgroup v2 的 memory.stat（强烈推荐作为论文主图/主表）

在同一个 cgroup 下跑 N 个实例，采样：

* `memory.current`（总量）([Kernel Documentation][2])
* `memory.stat` 里至少这些字段：

  * `pagetables`（页表开销）([Kernel Documentation][2])
  * `kernel_stack`（每线程/进程内核栈）([Kernel Documentation][2])
  * `slab`（内核对象分配，如 VMA 等）([Kernel Documentation][2])
  * `file` / `file_mapped`（文件页缓存 & mmap 相关）([Kernel Documentation][2])
  * `anon`（匿名页）([Kernel Documentation][2])

**输出形式：**

* 图：`pagetables/slab/kernel_stack` vs N（通常会线性增长，但斜率很小）
* 表：每新增一个实例带来的 `Δpagetables`、`Δslab`（bytes/instance）

cgroup v2 文档对这些字段有标准定义，你引用它就能把“统计口径”钉死。 ([Kernel Documentation][2])

### 5.2 第二层证据：/proc/slabinfo（定位“增长来自哪里”）

做差分：

* 记录空载时的 `/proc/slabinfo`
* 运行 N 个实例后再记录
* 关注增长显著的 cache：

  * `vm_area_struct`
  * `mm_struct`
  * `anon_vma` / `anon_vma_chain`
  * `dentry` / `inode_cache`（如果你的机制引入额外文件对象或 xattr/overlay 行为）

你在论文里可以写成：

* “绝大多数增长来自 Linux 既有的 per-process 元数据（VMA/mm/page tables），没有出现新的按实例线性增长的大型自定义结构。”

### 5.3 最强防守（建议你做）：在你的内核实现里加 debugfs 计数器

这是很多顶会系统论文的“杀手锏”：让 reviewer 没法争论“你到底分配了什么”。

建议你导出：

* `nr_redirected_pages`
* `nr_xarray_nodes_allocated`
* `nr_faults_handled`
* `nr_stub_inodes`
* （可选）累计分配字节数：`bytes_metadata = nodes*sizeof(node)+...`

这样实验三就能做到：

* **“内核内真实新增分配”**（debugfs 精确计数）
* **“外部观测一致性”**（memcg/slabinfo 侧验证）

---

## 6) 两个我强烈建议加到论文里的“加分实验”（会显著提高说服力）

### 加分实验 A：跨镜像/跨路径的共享（证明你不是在做“重复发明共享库”）

你机制如果核心价值在“不同 inode、不同路径、甚至不同镜像版本也能共享”，那你必须做一个“容器现实场景”的实验：

* 两个容器镜像 A/B，内容相同的库文件但路径/层不同（导致文件身份不同，页缓存不共享）。
* 你机制：所有实例共享同一 kernel code pages。
* baseline：动态库在不同镜像下会各自占一份 page cache（除非底层 FS 支持内容去重共享页缓存）。

OverlayFS 的 inode/st_dev 行为在文档里就提示了“不稳定/不一致”的可能性，这为你的“现实必要性”提供背景。 ([Kernel Documentation][4])

同时你可以在 Related Work / Threats-to-validity 提一句：
Linux 社区也在推动“按内容共享页缓存（如某些 FS/镜像格式）”以减少容器场景重复页缓存（比如 EROFS 相关 patch 系列讨论）。 ([LWN.net][7])
（这句话的作用是：你显得很诚实，也更像顶会论文。）

### 加分实验 B：在固定内存预算下“能塞进多少实例”（capacity under memory.max）

这类图非常直观，审稿人也爱看：

* 设定 `memory.max = X`（比如 2GB/4GB）
* 逐步增加实例数，直到 OOM 或触发 `memory.events` 里的 `oom_kill`
* 对比 Baseline vs Yours 能支撑的最大 N
  这直接把 “边际成本≈0”翻译成“**密度/承载量提升**”。

---

## 7) 你可以直接照抄到 artifact 的“采集脚本结构”（给你一个工程化落地方案）

### 7.1 运行控制：一个 driver + 一个 worker

* `driver.py`：循环 N、循环组别，创建 cgroup，启动 N 个 worker，等待稳定，采样，写 CSV
* `worker`（同一份源码编译三种链接方式）：执行 barrier -> call target -> sleep

### 7.2 采样函数（核心就是读两个地方）

1. per-pid 的 `smaps_rollup`（PSS 统计来源） ([Kernel.org][6])
2. per-cgroup 的 `memory.current/memory.stat/memory.peak`（内核归因来源） ([Kernel Documentation][2])

你最终 CSV 的列建议至少包括：

* `variant`（baselineA/baselineB/yours/…）
* `N`
* `sum_pss_kb`
* `sum_pss_file_kb`
* `sum_pss_anon_kb`
* `cgroup_memory_current`
* `cgroup_pagetables`
* `cgroup_slab`
* `cgroup_kernel_stack`
* `faults_minor`（可选 perf/bpf）
* `run_id`

### 7.3 统计与作图（论文规范）

* 每个点重复 5~10 次，画 mean + 95% CI
* 报告 slope（线性拟合 b）
* 报告“第一实例成本”（a）与“边际成本”（b）

---

## 8) 最后给你一段“论文里可用的表述模板”（你可以按你机制命名替换）

> We report the attributed physical memory footprint of an instance set using **Sum(PSS)**, where PSS accounts shared pages proportionally across processes as defined by the Linux procfs documentation. ([Kernel.org][1])
> To rule out “hidden kernel costs”, we additionally report memcg-attributed kernel memory breakdown from **cgroup v2 memory.stat**, including page tables and slab allocations. ([Kernel Documentation][2])
> Across up to N instances, our mechanism demonstrates near-constant **Sum(PSS)** growth with negligible marginal cost, while baselines that cannot share file identity exhibit linear scaling.

---

如果你愿意把你机制的更具体实现细节（例如：stub 映射是 file-backed 还是 PFNMAP？重定向是在 fault path 还是在 VFS/pathwalk？）用 5~10 行说明一下，我还能把上面每个实验的**“采样项更对齐你的实现”**（比如到底该看 `Pss_File` 还是 `Pss_Anon`，以及 pagetable 增长应该在什么量级、怎么解释异常）。但即使你不补充，这套方法本身已经足够严谨、可落地、也更能抵御审稿攻击。

[1]: https://www.kernel.org/doc/Documentation/filesystems/proc.rst "www.kernel.org"
[2]: https://docs.kernel.org/admin-guide/cgroup-v2.html "Control Group v2 — The Linux Kernel  documentation"
[3]: https://www.kernel.org/doc/html/v6.3/filesystems/vfs.html "Overview of the Linux Virtual File System — The Linux Kernel  documentation"
[4]: https://docs.kernel.org/filesystems/overlayfs.html "Overlay Filesystem — The Linux Kernel  documentation"
[5]: https://man7.org/linux/man-pages/man2/mincore.2.html?utm_source=chatgpt.com "mincore(2) - Linux manual page"
[6]: https://www.kernel.org/doc/Documentation/ABI/testing/procfs-smaps_rollup "www.kernel.org"
[7]: https://lwn.net/Articles/1052476/ "erofs: Introduce page cache sharing feature [LWN.net]"

