下面我按“与你的项目机制最相关的多个维度”补一批**跨 FS** 的数据/论文论据素材（网络、存储、系统调用/隔离边界、密码学接口、内核扩展安全、生态维护/补丁传播等）。我会尽量给出**可量化数据**；每条后面都按你的要求**直接附上来源链接**（重复也不省略），并且我也额外加上我这边的引用标注方便你回溯。

---

## 1) 系统调用/特权边界的“硬成本”远大于函数调用（与你的机制直接同构）

你们的核心诉求之一，本质是把“原本需要进入内核才能执行的实现逻辑”，变成**用户态一次函数调用**（通过 page cache 重定向到内核 text/.rodata 对应物理页 + 缺页填 PTE），因此最关键的现象证据就是：**syscall / ioctl 的固定开销非常大**，而且在打开安全缓解（KPTI、Spectre/MDS 等）时更明显。

* 有研究在**开启默认 CPU 漏洞缓解**时测得：

  * vDSO 里“空函数调用”仅 **1.4 ns**；
  * fastcall（仍有 ring transition，但跳过传统内核 entry 序列）为 **23.9 ns**；
  * “空 system call”开销是 **354.7 ns**；
  * “空 ioctl handler”更是 **413.6 ns**。
    这意味着在该测试系统上：**syscall 比一次 vDSO 函数调用大约慢 253×**（354.7/1.4），比 fastcall 慢约 **15×**。`https://arxiv.org/pdf/2112.10106`

* 同一研究还指出：当**关闭所有 mitigations** 时，system call 延迟可以降到 **46.4 ns**，会明显接近 fastcall 的 **24.1 ns**；但在多租户/云环境里“安全缓解是刚需”，因此他们后续评估都以 fully-mitigated 系统为主。`https://arxiv.org/pdf/2112.10106`

* 这篇 fastcalls 工作还给了“更贴近真实负载”的 microbenchmark：在 array-copy 场景 fastcall 约 **×12.5 更快**，在 non-temporal-copy 场景约 **×3.4 更快**（说明即便算上主存访问延迟，syscall 的固定成本仍非常显眼）。`https://arxiv.org/pdf/2112.10106`

* 他们还量化了控制面开销：注册 fastcall 函数的延迟约 **1.4–2.6 µs**，注销约 **2.4–4.8 µs**，并强调这种控制面操作很少发生，因此总体可接受。`https://arxiv.org/pdf/2112.10106`

**你们项目如何用这组数据落地到“现象”**：

> 在现代 CPU 上（尤其开启安全缓解时），一次进入内核（syscall/ioctl）的固定开销达到数百纳秒量级，而用户态函数调用可达数纳秒量级；当某些“内核实现的基础纯函数”在用户态频繁被调用（例如 checksum/hash/小块拷贝/位运算/协议解析小片段），这种边界开销会成为主导瓶颈。`https://arxiv.org/pdf/2112.10106`

---

## 2) 学术界/工业界长期在“绕开同步 syscall”上做大幅改造（证明这是长期痛点）

除了 fastcalls，你还需要更“经典、被反复引用”的证据来说明：**同步系统调用会破坏流水线、TLB 与缓存局部性**，因此很多系统研究专门围绕“减少/重排/异步化 syscall”来做。

* FlexSC（OSDI’10）明确指出：传统同步 syscall 会显著伤害性能，原因包括 pipeline flushing 以及对关键处理器结构（TLB、数据/指令缓存等）的污染；它提出 exception-less syscall 并给出应用层收益：Apache **最高 +116%**，MySQL **最高 +40%**，BIND **最高 +105%**，且无需修改应用（通过兼容 pthread 的用户态线程包透明转换）。`https://www.usenix.org/legacy/event/osdi10/tech/full_papers/Soares.pdf`

**与你们项目的关系（可写进“背景→动机”）**：

> FlexSC/fastcalls/vDSO 这一脉络共同说明：内核/用户边界本身的架构成本（以及安全缓解带来的额外成本）在高频小操作场景里非常突出；因此，“把可安全复用的内核逻辑以用户态函数形式提供”是一条与既有研究方向一致、但覆盖面更广的路径。`https://www.usenix.org/legacy/event/osdi10/tech/full_papers/Soares.pdf` `https://arxiv.org/pdf/2112.10106`

---

## 3) 网络方向：为了极致性能，大量系统把网络栈搬到用户态（但代价是“重写与分叉维护”）

你之前的数据偏 FS，这里给你网络方向非常硬的证据：**性能驱动导致用户态重写内核功能**，而重写的工程/安全成本正好反衬你们“复用内核纯函数”的价值。

### 3.1 mTCP：Linux TCP 事务率瓶颈 & 用户态 TCP 栈的数量级提升

* mTCP 论文指出：Linux TCP 事务处理率峰值约 **0.3 million transactions/s**；而用户态 packet I/O 可以扩展到约 **100 million packets/s**；他们的用户态 TCP 栈在小消息事务上对 Linux **最高 25×**，并在多个应用上提升 **33%–320%**。`https://www.usenix.org/system/files/conference/nsdi14/nsdi14-paper-jeong.pdf` ([USENIX][1])

**与你们项目的关系**：mTCP 这类系统为了性能必须“绕开内核路径”，但一旦绕开，就不可避免地要**重写/复制**大量基础逻辑（校验、hash、各种小工具函数、协议解析等）。你们的方案提供一种“只复用无状态/可验证的基础函数”的折中：既减少重写，又不把新代码塞回内核。`https://www.usenix.org/system/files/conference/nsdi14/nsdi14-paper-jeong.pdf`

### 3.2 IX：把延迟从 24µs 拉到 5.7µs、吞吐到 8.8M msg/s 的“内核旁路”典型

* IX 论文给出非常直观的对比：中位延迟 **5.7 µs**（Linux 为 **24 µs**），吞吐 **8.8 million messages/s**（约为 mTCP 的 **1.9×**、Linux 的 **8.8×**），还能用 **3 个核**跑满 10GbE（而 mTCP 需要 8 核）。`https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-belay.pdf` ([anakli.inf.ethz.ch][2])
* 他们还报告 memcached 之类应用：吞吐最高 **3.6×** 提升，tail latency 改善 **>2×**；并在 4×10GbE 上达到 **3.8 million TCP connections/s**。`https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-belay.pdf` ([anakli.inf.ethz.ch][2])

**与你们项目的关系**：这类系统已经证明“跨内核边界的开销”会把网络系统卡死在微秒级；但它们也在论文中隐含了另一个现象：为了绕开内核，必须在用户态维护大量与内核相同的基础实现，带来长期维护成本。你们的“零拷贝复用内核代码”可以被表述为：**为 kernel-bypass 体系提供一个“避免重复实现基础纯函数”的机制补丁**。`https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-belay.pdf`

---

## 4) 存储/NVMe 方向：硬件 IOPS 已经到千万级，软件栈开销成为主导（不仅仅是 FS）

### 4.1 NVMe 论文给出“硬件能到千万 IOPS”的量级（说明软件层一丁点固定成本都很贵）

* PVLDB 的 NVMe 虚拟化研究指出：NVMe SSD 阵列可以超过 **10 million I/O operations per second**；单块 SSD 可提供 **>1 million random read IOPS** 和 **7 GB/s**；他们的系统 I/O 能力达到 **12.5 million I/O/s**，在“大部分数据 out-of-memory”的条件下还能跑到 **>1 million TPC-C transactions/s**。`https://www.vldb.org/pvldb/vol13/p1942-li.pdf` ([Department of Computer Science][3])

**与你们项目的关系**：当硬件已经把 I/O 做到千万级，软件层任何“为了进入内核/走通用路径/做抽象”带来的固定开销都会被放大。即使你们不是做 FS，NVMe 这一组数据也能支撑“通用内核路径的固定成本已经不匹配硬件速度”的现象。`https://www.vldb.org/pvldb/vol13/p1942-li.pdf`

### 4.2 CHEOPS：把 I/O API 的“微架构开销”量化到 kIOPS、核数、指令数

CHEOPS 这篇论文非常适合你们，因为它把“软件栈开销”拆得很细，并且明确对比了 io_uring、SPDK 这类用户态方案。

* CHEOPS 报告其硬件平台峰值约 **4.2 million IOPS**；但在他们测试的 Linux I/O API 上（非 polling），只达到 **81.1–94.6 kIOPS**；开启 polling 后提升到 **108–138.9 kIOPS（约 1.7×）**，但同时 **每次 I/O 的指令数最高可增加到 2.3×**。`https://www.cs.utexas.edu/~zhiling/cheops.pdf` ([atlarge-research.com][4])
* 在高负载（QD=128，7 个设备）下，他们指出 **io_uring 比 SPDK “超过一个数量级”更低效**；并且在相同硬件上，fio 想跑满需要很多核：SPDK-perf 用 **1 核**就能打满，而 io_uring 最好需要 **13 核**。`https://www.cs.utexas.edu/~zhiling/cheops.pdf` ([atlarge-research.com][4])
* 他们还发现：常见基准工具（fio）本身会引入 **≈5× 的指令开销**，以及 I/O scheduler 可能引入 **最高 50% 的额外开销**。`https://www.cs.utexas.edu/~zhiling/cheops.pdf` ([atlarge-research.com][4])

**与你们项目的关系**：CHEOPS 证明“把路径缩短、把内核参与降到最低”能显著减少核数消耗；但与此同时，SPDK/用户态栈往往要自己维护一整套基础实现。你们的方案可以被动机化为：**在用户态极致路径上，让开发者不必为了一个小功能（checksum/hash/压缩/小拷贝）把一整套库或内核路径拉进来**。`https://www.cs.utexas.edu/~zhiling/cheops.pdf`

---

## 5) 密码学/哈希：确实存在“想复用内核实现”的现实需求，但现有接口（socket/syscall）仍有开销

你们项目强调“只能复用只读、无状态、不依赖内核上下文的安全函数”，这与 crypto/hash 的很多内核实现非常贴近；同时，crypto 也是一个很好的“跨 FS”论据方向。

### 5.1 AF_ALG 的性能与系统调用次数/Socket API 绑定（说明：走内核接口本身有框架成本）

* Linux 内核邮件列表里有人对 AF_ALG 与 /dev/crypto（cryptodev）做过性能对比，并明确怀疑 AF_ALG 性能问题与 socket API 和系统调用次数有关；在其给出的表格里，512B chunk 时 cryptodev **15.34 MB/s**、AF_ALG **12.32 MB/s**；8192B chunk 时 cryptodev **174.08 MB/s**、AF_ALG **150.04 MB/s**；并总结“512B 时 cryptodev 约快 25%”，“32KB 时约快 9%”。`https://groups.google.com/g/linux.kernel/c/bmSiPWNoT8g`

**与你们项目的关系**：这直接支持一个现象：

> “复用内核算法”这件事并不新（AF_ALG 就是），但**通过 socket/syscall 的封装会带来不可忽略的框架/边界成本**；因此如果能把“纯函数”以内存映射/页复用方式直接暴露为用户态调用，就可能进一步压缩这部分成本。`https://groups.google.com/g/linux.kernel/c/bmSiPWNoT8g` `https://arxiv.org/pdf/2112.10106`

### 5.2 io_uring + AF_ALG 的 kdigest 实测：小文件哈希时明显更快/更方便（说明：场景真实存在）

* 有人用 io_uring + AF_ALG 做 kdigest，并对比 openssl CLI，对 1MiB 文件做 MD5：kdigest **0.0011s** vs openssl **0.0039s**；对 32MiB 文件：kdigest **0.05214s** vs openssl **0.05360s**（大文件趋近）。`https://elastocloud.org/2024/07/using-af_alg-in-openssh-with-io_uring/`

**你可以怎么用这组数据**：

> 这类对比说明“调用内核 hash/crypto”在工程上确实有人需要（省掉用户态实现/依赖），并且在小数据块/小文件场景，封装方式不同会显著影响性能；你们的方案可以被描述为：把这类需求从“io_uring/socket 调内核”进一步推进到“零拷贝地直接调用内核纯函数”。`https://elastocloud.org/2024/07/using-af_alg-in-openssh-with-io_uring/`

### 5.3 “巨型依赖”的量化：为了一个 hash/压缩，用户态常常要引入几十万到百万行代码

这条对你们动机非常有用：即使共享库可以跨进程共享页，**依赖的复杂度/攻击面/供应链维护成本**仍然是现实问题（尤其在 minimal container、unikernel、function-as-a-service 等场景）。

* OpenHub 统计：OpenSSL 代码量约 **971,120 LOC**。`https://openhub.net/p/openssl`
* OpenHub 统计：zlib 代码量约 **55,372 LOC**。`https://openhub.net/p/zlib`
* OpenHub 统计：Zstandard（zstd）代码量约 **112,533 LOC**。`https://openhub.net/p/zstd` ([openhub.net][5])

**与你们项目的关系**：

> 如果应用只是需要“某个基础纯函数能力”（例如 CRC32C/SHA256/某种 decompress），今天常见做法要么链接巨型库，要么 syscalls 调内核接口；你们的方式提供第三条路：直接把内核里经过长期审计/优化的实现，以页复用形式变成用户态可调用代码，从而降低依赖复杂度并避免 syscall 框架成本。`https://openhub.net/p/openssl` `https://arxiv.org/pdf/2112.10106`

---

## 6) 安全维度：eBPF 等“把新代码放进内核”的路线风险很高（反衬“复用既有内核代码但在用户态执行”的价值）

你们项目要强调“只能映射安全纯函数、只读、无状态”，这天然适合写成：我们不做任意内核扩展（那会有巨大安全风险），我们只做“复用既有代码”的安全子集。

* IEEE S&P 2025 的 eBPF SoK 指出：Linux v6.11 中 eBPF verifier 已经超过 **22k LOC**，是 v3.18 初始版本的 **11×**；并举例说明 verifier 复杂度持续增长（2024 加了 93 行防整数溢出、2023 加了 595 行支持 open-coded iterator loops）。`https://lightninghkm.github.io/files/eBPFSoK.pdf`
* 同一 SoK 还写到：**仅 2024 年**，eBPF 子系统发现了 **100+ 与内存错误相关的 bug**，其中 **45 个仍未解决**。`https://lightninghkm.github.io/files/eBPFSoK.pdf`
* 它还量化了 eBPF 的资源限制：程序长度限制 **4096 instructions**，最大栈 **512 bytes**（这些约束也会逼迫开发者把逻辑拆成多个程序，进一步增加验证复杂度）。`https://lightninghkm.github.io/files/eBPFSoK.pdf`

**与你们项目的关系（可直接写成动机论证）**：

> eBPF 路线代表“为了性能/可扩展性，把代码执行带入内核”的诉求确实存在，但 verifier 复杂度和漏洞数量也说明这条路线的安全代价巨大；因此我们更倾向于“复用内核既有代码、但把执行留在用户态”，并且严格限制到纯函数/只读数据，从设计上降低内核被攻击的可能性。`https://lightninghkm.github.io/files/eBPFSoK.pdf`

---

## 7) 内核 bug 的规模 & 生态补丁传播/分叉维护的现实成本（说明“重复实现/重复维护”是长期现象）

这部分不局限 FS；它直接支撑你们要解决的“工程与安全维护问题”。

### 7.1 连续模糊测试把“内核 bug 的量级”摊在台面上

* syzbot（syzkaller 的公开 dashboard）当前显示：Upstream Linux **Open 1458**，**Fixed 6842**，**Invalid 17738**（还单列 Missing Backports 227）。`https://syzkaller.appspot.com/`
* 一篇对 syzbot 的大规模回顾研究提到：7 年里 syzbot 在 Linux 内核中找到 **6700+ bugs**，平均约 **2.6 bugs/day**；并报告“平均 time-to-find 超过 405 天”等延迟现象（这类数据可以用来强调：内核 bug 的发现与修复本就很难，重复实现只会让问题扩大）。`https://ics.uci.edu/~jbursey/pdf/syzretrospector.pdf`

**与你们项目的关系**：

> 当内核 bug 本身就有如此规模，用户态再去复制一份实现（crypto/压缩/解析/小工具函数）就意味着“潜在 bug 的数量 ×2”，并且修复还要同步两边；复用同一份代码（尤其是纯函数）能减少这种复制导致的风险扩散。`https://syzkaller.appspot.com/` `https://ics.uci.edu/~jbursey/pdf/syzretrospector.pdf`

### 7.2 “Linux 生态是 fork 的生态”：补丁移植策略不同、延迟不同、引入 bug 的风险也不同

* MSR 2024 论文研究了 Linux 生态里的补丁移植：覆盖 **21 个分支、8 个主流发行/生态（含 Android）**，并与 **23 个发行版与 LTS 维护者**沟通验证；其测量目标包含 **584K commits**。`https://arxiv.org/pdf/2402.05212`
* 该论文结论之一是：不同补丁移植策略在 patch delay、patch rate、bug inheritance ratio 三个指标上存在 trade-off——“想更快/更多 port patch，就不可避免引入更多 bug；想更稳，就会漏 patch 或延迟更大”。`https://arxiv.org/pdf/2402.05212`
* 他们还观察到：Linux LTS 分支的提交里 **99.3%** 都在 commit message 中包含 upstream commit 的引用（如 “Upstream commit <hash>”），说明生态里对“追踪 upstream 来源”的强依赖与强工程负担。`https://arxiv.org/pdf/2402.05212`

**与你们项目的关系**：

> 只要存在“同一功能的多份实现”（内核一份、用户态一份、甚至多个 fork 各一份），补丁传播就会变成持续的工程成本；你们的机制可被定位为：对一类“可安全复用的基础函数”，直接消除用户态那份实现，从源头减少 patch 移植与差异维护。`https://arxiv.org/pdf/2402.05212`

### 7.3 “多实现必然导致不一致与 bug”：网络协议解析的实证例子（跨领域但非常有说服力）

* OOPSLA 2024 的 ParDiff 工作在 **14 种网络协议**上做差分分析，检测到 **41 个 bug**，其中 **25 个被开发者确认**；其核心就是证明“同一协议的不同实现之间存在语义不一致”。`https://continuation.passing.style/static/papers/oopsla24.pdf`

**你可以怎么用这条**：

> 这可以作为一个很强的“类比证据”：当同一逻辑有多份实现（哪怕都很成熟），长期演进中也会产生细微语义差异并累积为 bug；因此减少重复实现（通过复用同一份内核纯函数）能系统性降低不一致风险。`https://continuation.passing.style/static/papers/oopsla24.pdf`

---

## 8) 这些“非 FS 数据”怎么嵌回你的最终叙述结构（现象 → 背景 → 动机）

你说得对：必须从现象入手才能明确“我们究竟要解决什么问题”。基于上面这些跨领域证据，我建议你把“现象”写成一组**可被量化验证的矛盾**（每个矛盾后都能跟一个数字/论文结论）：

### 8.1 现象（写成 3–5 条“可量化事实”）

1. **频繁小操作的系统调用/边界开销已经到了数百纳秒**，而函数调用可到数纳秒；开启安全缓解后差距更大。`https://arxiv.org/pdf/2112.10106`
2. 为了性能，网络/存储系统大量采用 kernel-bypass（mTCP、IX、SPDK），能带来 **×几倍到 ×几十倍**的吞吐/延迟收益，但随之带来“用户态重写内核逻辑”的长期维护成本。`https://www.usenix.org/system/files/conference/nsdi14/nsdi14-paper-jeong.pdf` `https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-belay.pdf` `https://www.cs.utexas.edu/~zhiling/cheops.pdf`
3. “复用内核实现”的需求在 crypto/hash 上长期存在（AF_ALG 等），但通过 socket/syscall 封装仍带来框架成本。`https://groups.google.com/g/linux.kernel/c/bmSiPWNoT8g`
4. 内核扩展机制（eBPF）为了性能把代码放进内核，但 verifier 复杂度和 bug 数量显示安全代价很高。`https://lightninghkm.github.io/files/eBPFSoK.pdf`
5. 内核 bug 规模巨大且生态分叉严重，补丁传播存在显著 trade-off；重复实现会放大维护与安全风险。`https://syzkaller.appspot.com/` `https://arxiv.org/pdf/2402.05212`

### 8.2 背景（解释“为什么会这样”）

* 解释边界成本来自：ring transition、流水线清空、TLB/cache 污染、安全 mitigations 的 entry 序列等（FlexSC/fastcalls 都已明确指出）。`https://www.usenix.org/legacy/event/osdi10/tech/full_papers/Soares.pdf` `https://arxiv.org/pdf/2112.10106`
* 解释为何 kernel-bypass 必然“重写”：一旦绕开内核路径，应用不得不自己承担协议栈/驱动/基础算法实现与维护（mTCP/IX/SPDK 这条线的共同代价）。`https://www.usenix.org/system/files/conference/nsdi14/nsdi14-paper-jeong.pdf` `https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-belay.pdf` `https://www.cs.utexas.edu/~zhiling/cheops.pdf`
* 解释为何不能简单把代码放进内核：eBPF SoK 展示 verifier 的复杂度与漏洞压力。`https://lightninghkm.github.io/files/eBPFSoK.pdf`

### 8.3 动机（明确“我们要解决的具体问题是什么”）

我建议你把问题定义收敛成一句话（你后面裁剪也方便）：

> **问题定义（建议）**：在 kernel-bypass/高性能用户态系统中，应用需要大量“内核中已经存在、可被视为纯函数的基础实现”（例如校验、hash、压缩/解压、小型内存/位操作、解析器的局部逻辑等）；但现有手段要么通过 syscall/socket/io_uring 等进入内核导致数百纳秒级固定开销与 cache/TLB 污染，要么在用户态重写导致实现分叉、补丁不同步与安全风险扩散。我们需要一种机制，把这类**安全可复用的内核代码页**以**零拷贝方式**映射到用户态，使其以普通函数调用形式执行，从而同时降低边界开销与重复实现成本。`https://arxiv.org/pdf/2112.10106` `https://www.usenix.org/legacy/event/osdi10/tech/full_papers/Soares.pdf` `https://www.usenix.org/system/files/conference/nsdi14/nsdi14-paper-jeong.pdf` `https://arxiv.org/pdf/2402.05212`

---

如果你愿意下一步继续“补强数据”，我建议你把上面这些证据拆成你论文里最常用的三类“可复用素材块”：

1. **边界开销**（ns/µs 量级，直接支撑“为什么要避免 syscall”）：fastcalls、FlexSC。`https://arxiv.org/pdf/2112.10106` `https://www.usenix.org/legacy/event/osdi10/tech/full_papers/Soares.pdf`
2. **现实系统为何绕开内核**（吞吐/延迟/核数）：mTCP、IX、CHEOPS、NVMe PVLDB。`https://www.usenix.org/system/files/conference/nsdi14/nsdi14-paper-jeong.pdf` `https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-belay.pdf` `https://www.cs.utexas.edu/~zhiling/cheops.pdf` `https://www.vldb.org/pvldb/vol13/p1942-li.pdf`
3. **重写/扩展的安全与维护代价**（bug 数、LOC、补丁传播 trade-off）：syzbot、SyzRetrospector、MSR24、eBPF SoK、OpenSSL LOC。`https://syzkaller.appspot.com/` `https://ics.uci.edu/~jbursey/pdf/syzretrospector.pdf` `https://arxiv.org/pdf/2402.05212` `https://lightninghkm.github.io/files/eBPFSoK.pdf` `https://openhub.net/p/openssl`

你如果接下来想把这些直接融进 motivations.md，我也可以按你既定的章节结构（现象→背景→动机）把文字“整段整段”写好，并把这些跨领域数据嵌进去。

[1]: https://www.usenix.org/system/files/conference/nsdi14/nsdi14-paper-jeong.pdf?utm_source=chatgpt.com "mTCP: a Highly Scalable User-level TCP Stack for ..."
[2]: https://anakli.inf.ethz.ch/papers/ix-osdi2014.pdf?utm_source=chatgpt.com "IX: A Protected Dataplane Operating System for High ..."
[3]: https://www.cs.fsu.edu/files/reports/TR220922.pdf?utm_source=chatgpt.com "LFUZZ: Exploiting Locality for File-system Fuzzing"
[4]: https://atlarge-research.com/pdfs/2023-cheops-iostack.pdf?utm_source=chatgpt.com "POSIX I/O, libaio, SPDK, and io_uring"
[5]: https://openhub.net/p/zstd?utm_source=chatgpt.com "The zstd Open Source Project on Open Hub"

