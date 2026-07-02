# BinaryKernelCodeMapping 论文前半部分大纲

## 0. Writing Position

这份大纲只覆盖可投稿论文从 `Introduction` 到 `Evaluation` 之前的正文。当前目标不是把整篇论文一次写完，而是先把前半部分的叙事骨架定稳，使读者在进入评测之前已经清楚理解四件事：

1. 我们要解决的问题到底是什么。
2. 现有方案为什么不满足这个问题。
3. 我们的机制边界在哪里，哪些代码能复用，哪些不能。
4. 系统是如何一步步把“正在运行的内核代码页”变成用户态可调用的标准 DSO 的。

本稿默认采用以下写法：

- `Motivation` 不单列章节，主要动机吸收到 `Introduction`。
- `Background` 只保留理解后文设计所需的最小背景。
- `Design` 是前半部分的主体，其中第一大节专门讲安全范围与适用边界。
- `Implementation` 不单独成章，而是融入各个设计小节，回答“为什么需要这个组件”以及“当前原型如何落地”。

全文主叙事要始终保持为：

> A generalized vDSO-like mechanism for restricted, function-level reuse of running kernel code pages in user space.

不要把论文写成 `xxh32/crc32/zlib` 的专题报告；这些只是 examples 和证据入口。真正的主题是一个更一般的函数类别：`hash / checksum / parse / compression helper / read-only compute kernel helper`。

建议正文篇幅分配：

- `Introduction`: 15%--20%
- `Background`: 10%--15%
- `Design`: 55%--65%
- `Transition to Evaluation`: 5%

---

## 1. Introduction

这一章吸收动机，不单列长篇 `Motivation`。它的任务不是把所有相关工作讲完，而是在最短篇幅内完成“问题建立、空白定位、机制预告、贡献列举”。

### 1.1 Hook and Tension

这一节应该从一类典型短路径函数开场，例如：

- `xxh32` / `crc32` 这类 checksum/hash helper；
- `zlib` 中的热点辅助函数；
- 更一般的 `parse/checksum/compression helper`。

要讲清的不是“某一个函数很快”，而是下面这个张力：

- 这类函数往往无状态、路径短、调用频繁；
- 真正昂贵的常常不是函数本身，而是跨越特权边界的通道；
- 如果为了绕开边界成本而在用户态重写同样逻辑，又会回到双份实现、补丁同步和语义漂移的问题。

这一节建议用 1 个 running example 起笔，但在第一屏内立即把它提升为一类问题，而不是停留在具体例子。

### 1.2 Problem Statement

这里要用论文语言明确问题，而不是泛泛地说“想复用内核代码”。建议写成类似下面的形式：

> Can a user process safely and efficiently reuse a restricted subset of already-loaded kernel code pages, without reimplementing the logic in a separate user-space library and without importing a whole kernel personality into user space?

然后用 2--3 句话定义问题边界：

- 复用的是一小类“只读、可重入、无内核上下文依赖”的函数；
- 复用对象是“正在运行的内核或 LKM 代码页”，不是另一份重新编译出来的用户库；
- 目标是在标准 DSO 形式下实现函数级复用，而不是子系统级迁移。

### 1.3 Why Existing Paths Are Unsatisfactory

这一节是问题定位，不是 related work 大综述。只保留三类最关键对比：

- `vDSO`：
  - 优点：它证明了“内核提供的只读代码在用户态执行”是成立的。
  - 局限：暴露范围极窄，无法推广到一般安全函数集合。
- `AF_ALG` 或类似官方内核接口：
  - 优点：能复用内核算法实现。
  - 局限：通道仍然重，不适合高频细粒度短路径。
- `LKL / rump kernel / LibOS`：
  - 优点：减少重复实现，能复用较大规模内核逻辑。
  - 局限：粒度太粗、环境太重，运行的是库化内核实例，不是共享“宿主当前正在运行的代码页”。

这一节必须让读者自然得出一个研究空白：

> 现有路径不是太窄，就是太重；缺少一种介于 `vDSO` 与 `LKL/rump` 之间、面向安全函数子集的函数级复用机制。

### 1.4 Main Insight

这一节只做机制预告，用 3 句话讲清楚系统的最小核心：

1. 用一个用户态 `Stub DSO` 承载标准 ABI、符号和私有可写状态。
2. 用 `page-cache grafting` 让该 DSO 的 `.text/.rodata` 最终映射到正在运行的内核或 LKM 物理页。
3. 用私有 `.data`、伪 GOT 和 `ld.so` 重建用户态必须拥有的可写绑定，而不是把内核可写状态暴露给用户。

这里不要提前把实现细节全展开；重点是让读者意识到，系统不是“直接 map 一页”那么简单，而是：

> shared machine code + private writable state + standard user-space loading semantics

### 1.5 Contributions

这一节要收敛，建议 3--4 条即可：

- 一个新的系统抽象：
  - generalized vDSO-like、restricted、function-level kernel code reuse。
- 一个二进制重建方案：
  - `Stub DSO reconstruction`，把内核/LKM 二进制包装成标准用户态入口。
- 一个运行时共享机制：
  - `page-cache grafting`，使用户态通过普通 file-backed fault 安装共享代码页。
- 一个原型与评测范围：
  - 当前原型展示 correctness、first-touch、steady-state 和应用级可用性的评测路径。

这一节不能把“性能一定更快”“冷启动一定碾压”写成贡献本体；这些都是后文需要验证的结果，不是前置定义。

### 1.6 Roadmap

用一段话预告后文即可：

- `Background` 只交代理解系统所需的最小背景；
- `Design` 先界定安全范围，再解释 `Stub DSO reconstruction`、`page-cache grafting` 与执行模型；
- `Evaluation` 将验证正确性、作用范围、first-touch 成本和应用级可用性。

---

## 2. Background

这一章的目标是“让读者刚好能理解后文设计”，而不是把所有背景材料都塞进来。凡是属于你方法本体的内容，都应留到 `Design` 去讲。

### 2.1 Privilege Boundary and vDSO Precedent

这一节只讲三件事：

- 为什么现代 OS 中用户态和内核态的边界对安全与稳定性是必要的；
- 为什么这种边界在短路径函数上会把固定成本放大成主要矛盾；
- 为什么 `vDSO` 是一个关键先例：它已经证明“内核提供的少量逻辑可作为用户态可执行代码暴露”。

需要控制篇幅，不要在这里展开各种 syscall benchmark 和历史脉络。只保留理解论文定位所需的最少证据。

### 2.2 File-Backed Mapping, Faults, and Page Cache

这一节要解释后文 grafting 为什么“在内核语义上成立”。应该讲清：

- file-backed VMA 与普通匿名映射的区别；
- 按需缺页如何将 file offset 解析到 page cache；
- `address_space` / `i_pages` / `file-backed fault` 在逻辑上如何串起来；
- 为什么改变某个 file offset 对应的 page-cache 槽位，会改变后续该 offset 的缺页解析结果。

这一节只需要把概念关系讲清，不需要进入当前实现的细节。不要在这里提前写“我们怎么做 grafting”。

### 2.3 Scope of Reusable Code

这是 `Background` 的收口节，也是 `Design` 中安全节的铺垫。这里要明确：

- 不是所有内核代码都能复用；
- 只有只读、可重入、无特权副作用、无内核上下文依赖的一小类函数才有讨论价值；
- 这一限制不是“工程上的遗憾”，而是论文问题定义本身的一部分。

本节可以用 1 个小表格或 3 句话预告后文分类：

- `allowed`
- `repairable`
- `unsupported`

但详细规则、threat model 和 checker 细节要留到 `Design 3.2`。

---

## 3. Design

这一章是前半部分的主体。写作原则是：

- 先界定边界，再讲机制；
- 每个小节同时回答两个问题：
  - 这个组件为什么在抽象上必要？
  - 当前原型是如何把它落地的？

### 3.1 Overview and Design Goals

这一节先放全文总图，图中建议包含以下流水线：

1. candidate selection
2. eligibility checking
3. Stub DSO reconstruction
4. page-cache grafting
5. fault-driven user execution
6. private writable state / shim boundary

然后给出 goals：

- `G1` 函数级复用，而不是子系统级迁移；
- `G2` 以标准 DSO 形式接入用户态；
- `G3` 尽量少改内核原生执行路径；
- `G4` 在安全子集内提供可解释、可审计的边界。

同时给出 non-goals：

- 不是“导出任意内核函数”；
- 不是把 syscall/网络栈/文件系统整体搬到用户态；
- 不是提供跨 kernel version 的稳定 ABI；
- 不是把所有安全问题一并解决。

这一节的目标是让读者先看见全局图，再进入细部机制。

### 3.2 Eligibility and Safety Scope

这是 `Design` 的第一核心节，必须放在所有具体机制之前。它要避免一种常见质疑：

> 你们是不是先做了一个 clever hack，再事后补一个安全解释？

本节建议拆成下面几个小块：

#### 3.2.1 Threat Model

说明攻击者能力和论文保护目标：

- 攻击者是普通用户进程，能加载 Stub DSO 并调用导出函数；
- 我们要防止 privilege escalation、任意内核状态修改、对可写内核数据的直接访问；
- 我们不声称解决所有侧信道，也不声称彻底消除 gadget 暴露。

#### 3.2.2 Function Classes

给出统一的三类函数：

- `Allowed`
  - 只依赖参数、局部状态和只读常量；
  - 无特权指令；
  - 无 `current`、per-CPU、锁、设备和异常修复依赖。
- `Repairable`
  - 逻辑本身可复用，但存在绝对地址、有限外部依赖、可收敛到伪 GOT 或 shim 的绑定。
- `Unsupported`
  - 依赖可写内核全局、上下文、调度、锁、设备对象或特权副作用的代码。

这部分最好在正文中放成一张表，列出：

- 类别
- 特征
- 代表例子
- 典型拒绝原因
- 是否纳入评测

#### 3.2.3 Static Eligibility Checker

说明当前原型如何落地这套边界。应提到：

- 闭包分析；
- privileged instruction filtering；
- absolute relocation / writable global 检查；
- unresolved dependency rejection；
- instrumentation / indirect control flow / retpoline 的处理策略。

这里要点出当前仓库已有的工具链基础，例如 `function_checker` 和闭包图分析，但不要写成“工具使用说明”。

#### 3.2.4 Runtime Rules and Residual Risks

明确运行时规则：

- 映射页只以 `RX` 暴露，坚持 `W^X`；
- 不共享可写内核 `.data`；
- 对外符号集合受控；
- 私有可写状态只放在 Stub DSO 的 `.data` 中。

同时正面承认剩余限制：

- page-granularity sharing 可能连带暴露同页其他指令；
- gadget exposure 无法完全避免；
- 侧信道风险不在本文解决范围内；
- `MPK/PKU` 最多作为 future hardening，而不是主设计依赖。

这一节结束后，读者应当能明确知道系统“能做什么、不能做什么、为什么这条边界是合理的”。

### 3.3 Stub DSO Reconstruction

这一节回答的问题是：

> 为什么我们需要一个 Stub DSO，以及它如何把内核/LKM 二进制变成标准用户态入口？

建议按以下顺序写：

#### 3.3.1 Why a Stub DSO Is Necessary

先说设计意图：

- 用户态需要一个标准 loader 能理解的对象；
- 共享代码页与私有可写状态必须在对象边界上被清晰分开；
- 复用机制必须复用现有 `ld.so` 和 DSO 语义，而不是自造整套加载器。

#### 3.3.2 Topology-Preserving Sparse Layout

说明为什么 Stub 必须保持符号与页级布局关系：

- 目标不是存放真正的代码副本，而是提供与后续 grafting 相容的地址骨架；
- 跨函数跳转、页粒度落点和后续 fault 行为都依赖这种布局兼容。

这里可以提到当前原型如何从 `.ko` 或选定符号闭包恢复 layout，但重点仍是“为什么要这样设计”。

#### 3.3.3 Private Writable State

说明共享 `.text/.rodata`、私有 `.data` 的设计原则：

- 共享机器码不等于共享所有状态；
- 用户态仍需拥有自己的可写槽位、导入绑定和局部状态；
- 这一步是隔离内核可写状态和用户可写状态的关键。

#### 3.3.4 Pseudo GOT and `.rela.dyn` Rebuild

这一小节讲 repairable 函数为何成立：

- 从 `.ko` 的可写数据重定位中收集需要在用户态重新绑定的槽位；
- 把这些槽位重建为标准 ELF 可理解的 `.rela.dyn`；
- 让 `ld.so` 回填，而不是让用户态重演内核模块加载器。

这里要强调：伪 GOT 是行为语义，不是简单“复制一个 `.got` 节”。

#### 3.3.5 Shim Boundary

解释为什么需要 shim：

- 某些有限环境依赖必须被截断，否则依赖闭包会失控；
- shim 既是依赖剪枝边界，也是运行期导入边界；
- 其目标不是模拟整个内核 API，而是收拢最小必要的用户态替代实现。

这一节里要顺带讲当前原型的 `libshim.so` 在系统中的位置，但不展开到工程细枝末节。

#### 3.3.6 File-Backed Segment Forcing

讲为什么需要让相关 `PT_LOAD` 段保持 file-backed：

- 如果 loader 把相关区域变成匿名映射，后续 page-cache grafting 将失去物理载体；
- 因此需要把对象 shaping 成能触发 file-backed fault 的形式。

语言上统一使用：

- `file-backed segment shaping`
- `loader-compatible segment forcing`

避免 `欺骗`、`伪装` 这类偏 exploit 的词。

这一整节结束后，读者应能回答：

> 为什么这个系统不是“直接 map 一个 page”，而是需要一个完整的用户态承载对象。

### 3.4 Runtime Page-Cache Grafting

这一节回答的问题是：

> Stub DSO 准备好之后，用户态是如何最终执行到“正在运行的内核代码页”的？

建议按以下顺序写：

#### 3.4.1 Why Page-Cache Grafting

先讲设计理由：

- 我们不想在用户态复制另一份代码页；
- 我们也不想构造一条完全脱离现有 fault 机制的新执行通路；
- 最自然的切入点是 file-backed mapping 的 page-cache 解析路径。

#### 3.4.2 Grafting the Target Pages

说明机制本身：

- 对目标 Stub DSO 的 `address_space/i_pages` 进行受控 grafting；
- 将特定 offset 的页缓存槽位指向运行中的内核/LKM `.text/.rodata` 物理页；
- grafting 发生在 inode/page-cache 层，而不是每进程私有层。

这里可以顺带指出当前原型的 `page_cache_replace` 模块和 manager 承担了什么角色。

#### 3.4.3 Fault-Driven Installation

讲用户态首次触达时发生什么：

- 触发普通 file-backed fault；
- fault 路径在页缓存中命中 grafted page；
- 内核按常规路径安装相应 PTE；
- 用户态最终看到的是“正常 DSO 调用”，而不是专用 trap 或 RPC 通道。

这一节必须把“标准路径参与”讲清楚，这是系统论文可信度的关键。

#### 3.4.4 Cross-Process Sharing

说明为什么这个机制天然具备系统级共享意义：

- grafting 发生在 page-cache 层，因此多个进程加载同一个 Stub DSO 时，会自然收敛到同一组底层共享页；
- 这也是后续 memory scaling 实验的机制解释基础。

#### 3.4.5 Invalidate and Restore

这小节不应被夸大。只需要交代：

- 为什么需要失效旧映射；
- 当前 restore/invalidate 的适用前提；
- 当前原型是否支持完全通用回滚，若不支持，要明确收口。

### 3.5 Execution Model and State Isolation

前两节分别解释了“承载体”和“共享页映射”，这一节要把调用语义、状态边界和 loader 参与方式集中讲透。

这一节建议讲清：

- 共享的是 `.text/.rodata`，私有的是 `.data`；
- 用户态调用遵循标准 ABI 和动态库语义；
- `ld.so` 在系统中扮演了什么角色；
- 为什么共享代码页不会自动把内核状态带到用户态；
- 为什么“标准 DSO 形式”对部署和接入很重要。

这一节的最终目标是让读者复述出下面这句话：

> The system shares machine code pages, not kernel execution context; user-visible compatibility comes from a standard DSO shell with private writable state.

### 3.6 Prototype Boundary

这是一个短节，用来防止后文过度外推。需要写清：

- 当前原型已经支持的能力；
- 当前明确不支持的能力；
- 哪些观察是机制直接属性；
- 哪些现象只是 `current Linux fault path` 下的 measured effects。

这里要明确降级这些表述：

- `zero-accounting`
- `I/O immunity`
- `dynamic flexible reuse`

它们可以作为实验观察出现，但不应作为设计公理出现在机制定义里。

---

## 4. Transition to Evaluation

在 `Design` 末尾加一个短小节或一段桥接文字，任务只有一个：告诉读者后文 `Evaluation` 将验证什么，而不是提前展开实验设计。

建议写成三个问题：

1. `Correctness and scope`
   - 系统导出的函数是否与基线语义一致？
   - 作用范围是否被 checker 和规则清晰界定？
2. `First-touch and steady-state cost`
   - 共享代码页是否改变首次触达成本？
   - 稳态是否接近原生用户态基线？
3. `Applicability`
   - 机制是否能支撑真实应用级工作负载，而不仅是手写 toy demo？

这一节的目标是完成“问题-边界-机制”到 `Evaluation` 的过渡，不在这里提前写 figure、RQ 编号或实验细节。

---

## 5. Writing Rules

这部分不是正文内容，而是写作约束，用于后续扩写时保持风格统一。

### 5.1 What to Keep

- `Introduction` 中只保留 2--3 个最硬的动机证据。
- `Background` 只讲读者必须知道的机制背景。
- `Design` 必须占前半正文的大头。
- examples 只作为入口，要不断提升为一般类别。

### 5.2 What to Avoid

- 不单列大篇幅 `Motivation` 章。
- 不把 `xxh32/crc32/zlib` 写成论文主题本身。
- 不把 `ext4/btrfs/OVS` 写成全文 running example。
- 不用 `hijack`、`欺骗`、`伪装` 这类 exploit 叙事词。
- 不把 `MPK/PKU` 写成主设计依赖。
- 不在 Design 里偷跑评测结论。

### 5.3 Keywords to Standardize

- `safe function subset`
- `generalized vDSO-like reuse`
- `Stub DSO reconstruction`
- `page-cache grafting`
- `fault-driven installation`
- `private writable state`
- `controlled exposure`
- `measured effects under current Linux paths`

---

## 6. Acceptance Checklist

在扩写这份大纲时，前半部分应满足以下标准：

- 读者看完 `Introduction`，能准确回答：
  - 问题是什么？
  - 现有路径差在哪？
  - 本文核心 insight 是什么？
- 读者看完 `Background`，刚好具备理解机制的最小背景，不会觉得前戏过长。
- 读者看完 `Design 3.2`，能说清系统能做什么、不能做什么、为什么安全边界合理。
- 读者看完 `Design 3.3` 到 `3.5`，能复述机制链路：
  - Stub DSO 如何构造；
  - page cache 如何 graft；
  - 用户态为什么最终能正常 `call`。
- 到 `Evaluation` 开始前，论文已经形成完整的“问题-边界-机制”闭环，而不是依赖评测章节补定义。

---

## 7. Current Decision Summary

为了避免后续再摇摆，这一版大纲明确采用以下决策：

- `Motivation` 吸收进 `Introduction`。
- `Background` 和 `Motivation` 不分章。
- `Implementation` 不单独成章，默认融入 `Design` 各节。
- 安全范围放在 `Design` 中的第一核心节详细讲，而不是独立大章。
- 当前轮次主交付只覆盖 `Introduction` 到 `Evaluation` 之前的内容，不展开 `Related Work`。
