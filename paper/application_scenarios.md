# 应用场景与代码分层（U-App / U-Glue / K-Glue / K-Priv / S-Core）

本文档用于：在设计一个“内核/用户态二进制级复用 .text/.rodata”的 OS + 用户态体系时，**如何分层代码、如何组织调用关系、以及在哪些场景最有价值**。

---

## 0. 一句话定位

我们的机制更像是一套 **Algorithmic Core Library（算法标准件库）**：
- 复用的是“算法实现唯一性（single source of truth）”，以及“代码页零拷贝共享”；
- 不是把系统调用整体搬到用户态；
- 也不是把复杂强状态子系统（网络栈/FS/调度器）直接导出。

---

## 1. 硬约束（必须写在最前面）

用户态可执行的共享代码必须满足：

- **不能访问内核真实全局变量 / .data**
- **不能依赖中断/softirq 与内核上下文（current/task_struct 等）**
- **不能直接操作内核对象**（skb/socket/file/inode 等）
- 最适合的目标是：
  - **纯计算函数**（只依赖参数 + .rodata）
  - 或重构后只依赖显式传入 **EnvCtx** 的“决策/换算核心函数”

因此：
- 无法把 `sys_read/sys_write` 这种完整 syscall 直接映射到用户态跑；
- 无法整体导出网络栈/文件系统/调度器。

---

## 2. 五类代码分层（推荐的最终分类）

### 2.1 五类定义

1) **U-App（User Application）**
- 业务逻辑、策略编排、服务框架、DB/配置/可观测性等。
- 特点：迭代快、生态依赖重、应当崩在进程里而不是崩系统。

2) **U-Glue（User Glue / User Shim）**
- 把“用户应用世界”适配成“可调用共享核心”的形态：
  - ABI/版本协商
  - 构造 EnvCtx
  - 封装 S-Core 为易用 API
  - 对接 io_uring/线程模型/内存管理等

3) **S-Core（Shared Re-entrant Core）**
- 共享可重入核心：**算法真相**，严禁环境依赖。
- 只依赖：`(input data, EnvCtx, rodata)`；
- 禁止：内核对象、内核全局、sleep/锁/中断语义、任何特权副作用。

4) **K-Glue（Kernel Glue / Kernel Shim）**
- 从内核世界适配到 S-Core，并把结果落地到内核动作：
  - 从 skb/socket/file 等抽取字段 → 组装 EnvCtx
  - 权限/边界检查
  - 作为 commit 网关：把输出 decision/patch 交给 K-Priv 执行“真实副作用”

5) **K-Priv（Kernel Privileged & Stateful）**
- 内核特权与强状态代码：
  - 驱动/中断、调度/内存、内核对象生命周期、全局一致性维护等
- 只有它能“改内核状态、触硬件、做全局协调”。

---

### 2.2 EnvCtx（原 snapshot）到底是什么？

**EnvCtx 是“共享算法需要的环境参数块”**，而不是内核活体状态本身。
- 形态：小、只读、扁平、可版本化（version/size）
- 来源：可以由 K-Glue 构造（从内核对象抽取），也可以由 U-Glue 构造（从配置/规则生成）
- 目标：让 S-Core 的行为只由输入决定：  
  `result = S-Core(input_data, EnvCtx)`

> 如果一段逻辑必须读写内核对象/全局状态，那它就不属于 EnvCtx + S-Core 的世界。

---

## 3. 精确调用关系（必须/禁止）

### 3.1 允许的调用边（✅）

**常态：本地直调（不改内核状态）**
- 用户侧：`U-App → U-Glue → S-Core`（direct call，无 syscall）
- 内核侧：`K-Priv → K-Glue → S-Core`（in-kernel call）

**稀有：需要改内核状态（compute + commit）**
- 先算：`U-App → U-Glue → S-Core`（本地可反复试算）
- 再提交：`U-Glue -(syscall/ioctl/netlink)-> K-Glue → K-Priv`（内核最终裁决并落地）

**内核副作用落地（解释你困惑的 K-Glue → K-Priv）**
- 当 S-Core 给出 decision/patch 后：
  - K-Glue 负责把“纯输出”翻译成“对真实内核对象的动作”
  - 因此必须调用 K-Priv 来执行：丢包/重定向/更新 map/切换规则/写状态等

### 3.2 禁止的调用边（❌）

- `S-Core` 禁止反向调用 `U-Glue / K-Glue / K-Priv`
- 用户态禁止直接调用 `K-Priv`
- U-App 不建议绕过 U-Glue 直碰 S-Core 低层 ABI（为了版本/上下文统一）

---

## 4. 场景模板（你可以直接复用到论文里）

### Pattern A：纯算法复用（最稳、最容易做 demo）
**核心**：S-Core 是纯函数，EnvCtx 为空或极小。

- 调用链：
  - 用户：`U-App → U-Glue → S-Core`
  - 内核：`K-Priv → K-Glue → S-Core`

- 典型算法：
  - checksum/hash（CRC32C/siphash/xxhash）
  - crypto 原语（chacha20/poly1305/AES 的子核心）
  - 纯解析/编码 helper（TLV/option header parse）

- 价值：
  - 消灭“一份内核实现 + 多份用户态重写”
  - 修 bug/优化：改一处，两边同步收益

---

### Pattern B：协议解析一致性（“甜点区”）
**核心**：kernel/user 两边都需要同一套解析/归一化规则，否则语义分叉。

- S-Core：`proto_parse_core(buf, len, EnvCtx, &meta)`
- 内核侧（粗过滤）：`K-Priv(hook) → K-Glue → S-Core → K-Glue → K-Priv(verdict)`
- 用户侧（细处理）：`U-App → U-Glue → S-Core`（后续业务逻辑在 U-App）

- 典型落地点：
  - XDP/TC/netfilter 的早期过滤 + 用户态 proxy 的完整处理
  - “内核先挡垃圾、用户再做细逻辑”，但解析规则同源

---

### Pattern C：io_uring 组合（它管数据，你管算法）
**核心**：I/O 中断与设备交互全部留在内核；用户态拿到 buffer 后本地调用 S-Core。

- 数据通路：
  - 设备 → 中断 → 驱动 → io_uring 内核部分 → CQ ring → 用户 buffer
- 算法通路：
  - `U-App → U-Glue → S-Core`（解析/校验/决策不需要 syscall）
- 状态修改（如果有）：
  - 仍通过 commit syscall：`U-Glue → K-Glue → K-Priv`

---

### Pattern D：两阶段（compute + commit），用于“安装/更新内核状态”
**核心**：compute 阶段可以反复算、做预验证；commit 阶段由内核落地。

- 适合的“commit 内容”：
  - 规则/策略的不可变镜像（policy image）
  - eBPF map 更新的批量 key/布局
  - kTLS/会话参数安装（一次启用，后续走 fast path）

- 调用链：
  1) compute：`U-App → U-Glue → S-Core`（N 次）
  2) commit：`U-Glue -(syscall)-> K-Glue → K-Priv`（1 次）

---

### Pattern E：eBPF / bpftime helper 统一（core + wrapper）
**核心**：两边都要同一 helper 行为，但强状态 helper 不强行统一。

- helper 分类：
  1) 纯算法型：统一 S-Core（最适合）
  2) 可 EnvCtx 化：部分可统一（如时间/统计换算核心）
  3) 强状态型：仍留在内核（操作 skb/socket/cred/cgroup/map 等）

- 典型写法：
  - 内核 helper wrapper：参数检查 → 调 `S-Core`
  - bpftime helper wrapper：直接调同一 `S-Core`
  - 若要改内核状态：只能走 `K-Glue → K-Priv`

---

### Pattern F：测试/仿真/验证工具（研究价值高、风险低）
**核心**：共享机器码 + 独立状态，适合 fuzz/trace replay/A-B test。

- Shadow module：
  - `.text` 共享宿主内核页
  - `.data/state` 用户态独立一份，不影响系统
- A/B testing：
  - 同一输入同时调用 `old_core()` / `new_core()` 比对输出
- “官方解释器”：
  - 用户态拿到原始统计数据 + 调用 S-Core 把数字解释成结论

---

## 5. 实践建议：优先实现什么 demo（论文最稳）

1) **纯算法导出库**
- 2–3 个 hash/checksum/parse helper
- 展示 kernel/user 共享同一份实现

2) **io_uring + 共享解析/校验**
- echo/代理 server：io_uring 负责 I/O，S-Core 负责解析/校验
- 对比“纯用户态重写解析”的代码量与行为一致性

3) **eBPF/bpftime 统一一个 helper**
- 以 checksum/hash 为例：core + wrapper
- 展示“更新/修 bug 只改内核一处”

4) （可选）两阶段 compute+commit
- 用 policy image “安装规则”做例子：本地反复 compute，最后一次 commit

---

## 6. 总结（可直接当论文段落）

我们不试图把完整 syscall 或强状态子系统映射到用户态；相反，我们将内核功能拆分为：
- S-Core：可重入、无副作用的共享算法真相（代码页零拷贝共享）
- Glue：两侧分别适配环境并处理副作用
- K-Priv：负责所有特权操作与真实内核状态更新

该分层让 kernel/user 在“同一套行为操作同一类数据”时，能共享唯一实现并避免语义分叉；同时保持内核边界清晰：凡涉及权限、对象、硬件与全局一致性，仍由内核最终裁决与执行。

