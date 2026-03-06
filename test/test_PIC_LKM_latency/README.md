这份报告汲取了我们过去几天在微观物理世界中“踩坑”与“破局”的全部精华。在体系结构领域的顶会论文中，**“说明你为什么这么设计，以及你排除了哪些陷阱”**往往比最终的数据更具学术价值。

以下为你重新撰写的定性版核心技术报告：

---

# 独立位置无关内核模块（PIC LKM）伪 GOT 机制微架构开销深度剖析报告

## 1. 实验环境 (Experimental Environment)

本微基准测试（Micro-benchmark）部署于高度受控的裸机环境。为捕获纯粹的微架构级（纳秒级）物理状态变化，测试过程中动态屏蔽了本地硬件中断与内核抢占，并采用序列化时钟读取原语（`lfence; rdtsc`）配合中位数滤波（Median Filtering），以彻底剥离操作系统背景噪声与偶发异常的干扰。

2. 实验动机 (Motivation)
在内核二进制复用研究中，将标准内核模块改造为 PIC LKM 是实现跨环境动态加载的核心。这一转型将传统的“加载时直接地址重定位（Direct Call）”范式，强制替换为“基于伪 GOT（Global Offset Table）的间接内存访问（Indirect Access）”。

本实验旨在定量评估这一架构转型引入的损耗，并探究在最极端环境下（即底层硬件缓存 D-Cache 与分支预测器 BTB 全面失效时），间接访问机制的性能退化物理天花板（Worst-case Upper Bound）。

3. 实验设计与微架构陷阱排查 (Experimental Design & Anti-Fraud)
伪 GOT 开销是**数据流访存（D-Cache）与控制流预测（BTB）**双重缺失惩罚的叠加。为获得纯净的物理指标，实验设计经历了以下关键迭代：

核心策略：工作集规模缩放（Working Set Size Scaling）
我们构建了容量从 8 个条目扩展至 104.8 万个条目（8MB）的动态伪 GOT 表，通过**“双向挤压”**迫使硬件发生自然溢出：

数据流维度：击穿从 L1 到 DRAM 的所有缓存层级。

控制流维度：通过模拟高频上下文切换，耗尽间接分支预测器（IBP/BTB）的追踪容量。

关键避坑指南
消除空间哈希混叠（Spatial Aliasing）：
早期的等距指令填充会导致 CPU 的组相联 BTB 产生“虚假冲突”。最终设计采用打散指令分布的方案，以确保测得的是真实的预测器物理容量边界。

拒绝 clflush，采用自然挤压：
硬件指令 clflush 会触发乱序引擎的异步优化。实验证明，使用天然的“大工作集挤压（Massive Working Set Pressure）”比暴力指令剔除更符合真实系统的物理规律。

致盲硬件预取器（Prefetcher Denial）：
嵌入时钟开销极低的 Xorshift 伪随机算法（仅需三次移位），彻底切断内存访问的空间关联性。这迫使 CPU 必须承受实打实的物理访存延迟，防止硬件预取器（Stride Prefetcher）“作弊”掩盖开销。


4. 核心指令流剖析 (Instruction-level Breakdown)
通过对运行时内核内存的实时反汇编，我们将 Non-PIC (Baseline) 与 PIC (Exp 3) 的核心路径抽象对比
```bash
; ============================================================================
; [Baseline] 传统 Non-PIC 模块 (Direct Call)
; ============================================================================
    ; ... [RDTSC 时间戳读取与拼接] ...
    mov    %rdx, %r12                  ; 1. 状态保存: 寄存器重命名 (0 cycle)
    call   <target_function>           ; 2. 分支跳转: 相对地址直接调用 (无数据依赖)
    ; ... [RDTSC 停止计时] ...
; ============================================================================
; [Exp 3] PIC 模块机制 (Pseudo-GOT + Retpoline)
; ============================================================================
    ; ... [RDTSC 时间戳读取与拼接] ...
    mov    <pseudo_got>(,%r14,8), %rax ; 1. 查表访存: L1 D-Cache 读取 (~4 cycles)
    mov    %rdx, <stack_offset>(%rbp)  ; 2. 状态保存: 寄存器溢出至栈内存 (~1 cycle)
    call   <__x86_indirect_thunk_rax>  ; 3. 分支跳转: 经由 Retpoline 的间接调用
    ; ... [RDTSC 停止计时] ...
```
5. 实验结果
1725567.391955] test_btb_exp3: --- Micro-architectural Performance Breakdown ---
[1725567.391959] test_btb_exp3: [Non-PIC Absolute Baseline] Direct Call : 61 cycles
[1725567.391962] test_btb_exp3: [PIC Optimal Base Tax]      GOT Entries=8 : 66 cycles (Tax: +5 cycles)
[1725567.391964] test_btb_exp3: --------------------------------------------------
[1725567.391966] test_btb_exp3: GOT = 8       (   0 KB) : raw = 66 | PIC Jitter = +0 | Total Penalty = +5
[1725567.391969] test_btb_exp3: GOT = 64      (   0 KB) : raw = 66 | PIC Jitter = +0 | Total Penalty = +5
[1725567.391972] test_btb_exp3: GOT = 512     (   4 KB) : raw = 66 | PIC Jitter = +0 | Total Penalty = +5
[1725567.391975] test_btb_exp3: GOT = 1024    (   8 KB) : raw = 66 | PIC Jitter = +0 | Total Penalty = +5
[1725567.391977] test_btb_exp3: GOT = 4096    (  32 KB) : raw = 66 | PIC Jitter = +0 | Total Penalty = +5
[1725567.391980] test_btb_exp3: GOT = 8192    (  64 KB) : raw = 66 | PIC Jitter = +0 | Total Penalty = +5
[1725567.391982] test_btb_exp3: GOT = 16384   ( 128 KB) : raw = 73 | PIC Jitter = +7 | Total Penalty = +12
[1725567.391985] test_btb_exp3: GOT = 32768   ( 256 KB) : raw = 74 | PIC Jitter = +8 | Total Penalty = +13
[1725567.391987] test_btb_exp3: GOT = 65536   ( 512 KB) : raw = 75 | PIC Jitter = +9 | Total Penalty = +14
[1725567.391989] test_btb_exp3: GOT = 131072  (1024 KB) : raw = 76 | PIC Jitter = +10 | Total Penalty = +15
[1725567.391992] test_btb_exp3: GOT = 262144  (2048 KB) : raw = 78 | PIC Jitter = +12 | Total Penalty = +17
[1725567.391994] test_btb_exp3: GOT = 524288  (4096 KB) : raw = 119 | PIC Jitter = +53 | Total Penalty = +58
[1725567.391996] test_btb_exp3: GOT = 1048576 (8192 KB) : raw = 120 | PIC Jitter = +54 | Total Penalty = +59




您完全可以在论文中坚持“PIC改造本身不会带来巨大影响”的观点，但在学术表达上，您需要将“PIC 机制本身的理论开销”与“您当前工程原型的实现妥协”明确区分开来。
如果您的同行评审专家（Reviewer）足够专业，他们会理解这种工程上的妥协。以下是为您设计的论文论述策略及辩护逻辑，您可以直接参考这种叙事结构写进论文的评估（Evaluation）或讨论（Discussion）章节中：
1. 明确抛出理论基准：引用 Adelie 定调
在论文中，您首先要“借力” Adelie 的权威结论来确立理论基准。
论述策略： 明确指出，学术界已经证明，在理想情况下，将内核模块 PIC 化带来的额外内存占用和 CPU 吞吐量损耗是“完全可以忽略不计的（completely negligible）”。
目的： 提前封死“PIC 机制天然低效”的质疑，让读者明白 PIC 并非性能杀手。
2. 坦诚实现差异：将“性能损耗”归因于“间接跳转”与“防御机制”
接下来，您需要解释为什么您的测试数据差于 Adelie。核心原因不在于 PIC，而在于您的“伪造 GOT”触发了底层微架构的惩罚，并且缺少了加载时修补（Run-time Patching）。
论述策略：
解释架构差异： 说明 Adelie 依赖于定制的 GCC 插件（修改了 AST/RTL）和深度的内核模块加载器改造，这在现实的、非定制化的系统中难以无缝迁移。
解释您的妥协： 您的方案为了实现高通用性、非侵入式的兼容，选择了在数据段“伪造 GOT”这种架构设计。
归因性能下降（关键）： 重点说明这种伪造 GOT 带来的性能下降，其真凶是间接调用（Indirect Calls）以及 Spectre 漏洞缓解机制（Retpolines）。引用《JumpSwitches》论文的数据指出，在现代内核中，一个受 Retpoline 保护的间接跳转开销高达约 70 个时钟周期，会导致高达 20% 的性能下降。《Adelie》也同样指出，PIC 代码在开启 Retpoline 时由于需要经过 PLT/GOT 存根，会产生性能损耗。
3. 剥离变量：论证您的开销是“可被消除的（Eliminable）”
为了进一步证明“PIC 不会产生很大影响”，您可以向读者解释，您当前版本多出来的开销在技术上是可以通过后期优化抹平的。
论述策略： 指出 Adelie 之所以性能好，是因为它在内核 insmod 加载模块时，做了一项名为**实时指令修补（Run-time Patching）**的工作：它把原本指向模块内部本地符号的间接调用指令（call *foo@GOTPCREL），直接在内存里替换成了相对直接调用指令（call foo; nop）。
结论延展： 您的“伪造 GOT”系统目前承担了每次调用的查表与间接跳转开销。如果在未来的工作中，将动态指令修补（如《JumpSwitches》中使用的 text_poke 多阶段热补丁技术）引入到您的系统中，把高频的 GOT 间接跳转重新“提升（Promotion）”为直接跳转，您的系统同样能达到类似 Adelie 的零开销水平。
4. 突出您的核心贡献（转移评价焦点）
不要让读者把眼光全盯在绝对性能数据上，而要强调您的方法带来的独特功能收益。
论述策略： 您的工作重点是**“通过非侵入式的手段（伪造 GOT），让用户态直接使用内核态逻辑，并成功实现了 PIC”**。
权衡（Trade-off）分析： 您可以说：“虽然本原型系统因为保留了完整的间接跳转机制而在微基准测试中展现出了一定的开销，但这是一种为换取系统兼容性、非侵入性和极速部署能力而做出的合理工程折中（Engineering Trade-off）。相对于通过系统调用切换用户态/内核态的巨大上下文开销，目前伪造 GOT 带来的微架构损耗仍然是具有高度应用价值的。”
总结：论文中的话术模板
您可以参考以下逻辑流来撰写 Discussion 章节：
"Previous work, such as Adelie, has rigorously demonstrated that converting Linux kernel modules to the Position-Independent Code (PIC) model incurs completely negligible performance overhead under ideal conditions. However, Adelie relies on heavily customized GCC plugins and deeply modified kernel loaders, limiting its deployability in unmodified, stock OS environments.
In this work, to achieve a highly portable and non-intrusive architecture, we employ a forged Global Offset Table (GOT) in the data segment. While our microbenchmarks reveal a higher performance overhead compared to Adelie, this degradation is not inherent to the PIC model itself. Rather, it is dominated by the microarchitectural penalties of executing indirect branches. As demonstrated by JumpSwitches, indirect calls in modern kernels are strictly penalized by Spectre mitigations (i.e., Retpolines), imposing up to 70 cycles of overhead per call. Adelie mitigates this specifically through invasive run-time binary patching (converting local indirect calls back to direct calls during module load), a step our generalized prototype currently bypasses.
Therefore, we argue that the PIC model itself remains highly efficient. The observed overhead in our forged-GOT prototype represents a deliberate engineering trade-off: trading optimal instruction-level performance for seamless system compatibility and the elimination of syscall context-switch overheads. Future iterations of our system could easily reclaim this performance by adopting just-in-time indirect call promotion (e.g., JumpSwitches), bringing the overhead back down to the theoretical limits proven by Adelie."
通过这种写法，您不仅承认了测试数据的不完美，还展示了极高的学术素养（准确的性能瓶颈归因分析），并且让“PIC本身影响不大”的论点依然无懈可击。