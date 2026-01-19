# 第 X 章  KRG：SAFE 只读内核符号集的构建、裁剪与用户态映射

本章介绍 KRG（Kernel Read-only Graph）的核心功能与实现：从 `vmlinux` 静态抽取**函数级依赖图**（调用/跳转与重定位引用），并依据“可解释的 SAFE 语义”在构建阶段**直接裁剪**出 SAFE 子图；随后在查询阶段对 SAFE 图做闭包并输出（运行时地址、大小、类型），用于“用户态镜像执行/分析”等场景。

---

## 1. 功能概览与论文关联点

### 1.1 研究目标（面向论文可复述）

KRG 的目标不是“恢复完整 CFG”，而是构建一个**足够精确、可复现、可解释**的 SAFE 函数集，使得这些函数在“用户态镜像执行”语境下尽量不触达内核全局副作用（调度、用户态拷贝、外设映射、日志/告警等）。

### 1.2 工具功能列表（表格）

**表 1：KRG 的关键功能与论文价值点**

| 功能          | 输出/效果                                | 论文中可强调的点                        |
| ----------- | ------------------------------------ | ------------------------------- |
| 符号解析        | 解析 ELF sections/symbols，分类 code/data | 静态、可复现实验；不依赖运行时插桩               |
| 主函数区间重建     | 只用“主函数入口”重算区间，避免 `.slowpath` 切片      | 提升 owner/target 归属稳定性（核心工程点）    |
| 依赖抽取（双源）    | 重定位 + 反汇编两条路径提取边                     | 同时捕获 code→code 与 code→data，解释性强 |
| SAFE 裁剪（闭包） | 最大不动点 SAFE：严格闭包、可解释原因                | 形式化语义 + 可证明/可复述的规则              |
| KASLR 对齐    | 以 `_stext` 计算 slide，将静态 VA 平移到运行时    | “内核态→用户态映射”的关键桥梁                |
| 查询闭包        | 从根符号做可达闭包，仅输出 SAFE 子图内可达节点           | 支持实验：子系统函数族谱、依赖边界               |

（主函数区间重建、ABS MEM 间接调用识别等设计动机可直接写入“问题→方案”小节。）

---

## 2. 端到端流程（示意图）

**图 1：KRG 两阶段流水线（示意）**

```
          ┌───────────┐
          │  vmlinux   │
          └─────┬─────┘
                │ 解析 ELF（sections/symbols）
                v
      ┌──────────────────┐
      │ 主函数区间重建     │  仅“主入口”→fun_ranges_
      └─────┬────────────┘
            │
            │ 依赖抽取（两条路径）
            v
  ┌─────────────────────────┐
  │ (A) Relocs：code/data引用 │
  │ (B) Disasm：CALL/JMP识别  │
  └───────────┬─────────────┘
              │
              v
      ┌──────────────────┐
      │ SAFE 最大不动点裁剪│  drop 原因可解释
      └─────┬────────────┘
            │ 序列化 out.krg（CSR）
            v
      ┌──────────────────┐
      │     out.krg       │
      └─────┬────────────┘
            │ query(root)
            v
      ┌──────────────────┐
      │ SAFE 可达闭包输出  │ addr/size/kind/name
      └──────────────────┘
```

该设计满足“构建阶段直接裁剪、查询阶段只做闭包”的实验需求。

---

## 3. 数据模型与关键数据结构

### 3.1 节点（Node）与文件头（FileHeader）

**表 2：序列化节点与文件头字段**

| 结构           | 字段                   | 含义                         |
| ------------ | -------------------- | -------------------------- |
| `Node`       | `addr:u64`           | 符号地址（构建时可能已做 KASLR 对齐）     |
|              | `size:u32`           | 以字节计的区间大小                  |
|              | `kind:u8`            | 0=code，1=data              |
| `FileHeader` | `magic='KRG1'`       | 文件魔数                       |
|              | `version=1`          | 版本                         |
|              | `n_nodes, n_edges`   | 节点与边数量                     |
|              | `name_blob_bytes`    | 名字 blob 大小                 |
|              | `arch`               | 当前实现为 x86_64（0）            |
|              | `is_runtime_address` | 预留：是否已是运行时地址（当前写入路径未启用该标志） |

其中 `is_runtime_address` 在实现中存在但写入时被注释，查询阶段直接认为“构建已固化地址”。  

### 3.2 “主函数入口”与区间（避免 `.slowpath` 切片）

KRG 用 `Primary`（主函数入口）来稳定定义函数区间：主入口满足“code 且名字不以 `.` 开头”，并在每个 section 内按地址排序，用“下一个主入口/节末”重算区间。 

**公式 1：主函数区间重建（可用于论文形式化）**
对每个可执行节 (s)，取其主入口集合 $P_s={f_1,\dots,f_k}$ 并按地址升序排列。设节末地址为 $\mathrm{end}(s)$。则：

$$\mathrm{start}(f_i)=\mathrm{addr}(f_i),\quad\mathrm{end}(f_i)= \begin{cases} \mathrm{addr}(f_{i+1}), & i<k \\ \mathrm{end}(s), & i=k & \end{cases} \\ \mathrm{size}(f_i)=\max\{1,\min(2^{31}-1,\mathrm{end}(f_i)-\mathrm{start}(f_i))\}$$
实现中以该区间表 `fun_ranges_` 做 owner/target 的全局二分命中。


**图 2：`.slowpath` 切片问题与区间合并（示意）**

```
原始符号（被切片）：
  foo()      [0x1000,0x1100)
  .slowpath  [0x1100,0x1180)   ← 真实 call 在这里

KRG 主入口重算后：
  foo_primary [0x1000,0x1180)  ← 将 .slowpath 合并进 foo
```

---

## 4. 依赖图构建：Reloc + Disasm 的双源融合

令图的节点集合为符号集 $V$，并区分 $V_\text{code}$、$V_\text{data}$。边分两类：

* 代码调用边：$E \subseteq V_\text{code}\times V_\text{code}$
* 数据引用边：$R \subseteq V_\text{code}\times V_\text{data}$（用于只读判定）

### 4.1 重定位路径（Relocs）：稳健捕获 code/data 引用

重定位遍历 `SHT_REL/SHT_RELA`，把 relocation site 地址映射到 owner 函数 (u)，再根据被引用符号类型写入：

* code：加入 $E$（或触发黑名单规则）
* data：加入 $R$（记录 code→data）

> 论文要点：Reloc 天然能发现 code→data 依赖，因此是 SAFE 规则中“只读数据”判定的关键证据源。

### 4.2 反汇编路径（Disasm）：精确识别 CALL/JMP

KRG 用 Capstone 在 x86-64 可执行节上滚动反汇编，识别三类关键控制流：

**(1) `CALL IMM`：ABS→REL 双尝试**
$$
t_\text{abs}=\mathrm{imm},\qquad
t_\text{rel}=\mathrm{pc}+\mathrm{len}+\mathrm{imm}
$$
优先尝试 $t_\text{abs}$，失败再尝试 $t_\text{rel}$，并将目标映射为主函数区间中的节点。

**(2) `CALL/JMP [RIP+disp]` / `CALL/JMP [ABS]`：从镜像表读指针**
这一步是“内核镜像中函数指针表”解析的核心，特别是 `CALL [ABS]`（绝对地址内存操作数）路径。

可形式化为：
$$\begin{aligned}
 & \mathrm{ptr_va}=
\begin{cases}
\mathrm{pc}+\mathrm{len}+\mathrm{disp}, & \text{RIP-relative} \\
\mathrm{disp}, & \mathrm{ABS~MEM} & 
\end{cases} \\
 & \mathrm{tgt_va}=\mathrm{Load}64(\mathrm{ptr_va}),\quad v=\mathrm{Owner}(\mathrm{tgt_va})
\end{aligned}$$
其中 $\mathrm{Load64}$ 仅在 `SHF_ALLOC` 节区间内读取（通过 `alloc_secs_` 二分定位）。 

**(3) `JMP IMM`：仅保留跨函数跳转**
若 (v=u) 视为函数内部跳转（intra）忽略；仅保留跨函数 `JMP` 作为“尾调用/跨函数依赖”的信号。

### 4.3 名单机制（硬黑名单 + 软忽略）

KRG 用前缀匹配实现两类名单：

* **软忽略 soft-ignore**：命中则“不过边”，但不影响安全性（常见于 thunk/retpoline 等）
* **硬黑名单 hard-BL**：**仅当 CALL 命中**时，标记 caller 为不安全（并不过边）；JMP 命中仅过滤，不传播“不安全”语义

**表 3：名单前缀（论文可直接列出）**

| 类别   | 前缀（实现中的精确列表）                                                                          | 语义动机（论文解释）          |
| ---- | ------------------------------------------------------------------------------------- | ------------------- |
| 硬黑名单 | `schedule`, `preempt_`, `cond_resched`, `msleep`, `udelay`, `mdelay`                  | 调度/睡眠/延迟 → 全局效应     |
|      | `copy_to_user`, `copy_from_user`, `get_user`, `put_user`                              | 用户态拷贝 → 安全边界/副作用    |
|      | `kmalloc`, `kzalloc`, `kvalloc`, `vmalloc`, `kfree`, `vfree`                          | 内存分配/释放 → 全局状态      |
|      | `ioremap`, `iounmap`                                                                  | 设备映射 → 全局/硬件效应      |
|      | `pci_`, `net_`, `sock_`, `blk_`, `vfs_`, `fs_`, `dev_`                                | 子系统 IO 路径（经验性屏蔽）    |
|      | `printk`, `pr_`, `__warn_printk`, `__sanitizer_`, `__ubsan_`                          | 日志/告警/消毒器路径 → 全局效应  |
| 软忽略  | `__x86_return_thunk`, `__x86_indirect_thunk_`, `__retpoline_`, `__fentry__`, `mcount` | 桥接/插桩/thunk，不应污染依赖图 |

（名单与“CALL 传播、JMP 不传播”的语义在 README 中也强调为“可解释 SAFE 语义”的基础。）

**图 3：CALL/JMP 解析与过滤（示意）**

```
CALL -> target
  ├─ soft-ignore(target)  => drop edge
  ├─ hard-BL(target)      => mark caller UNSAFE; drop edge
  └─ otherwise            => add edge

JMP -> target
  ├─ intra (same func)    => ignore
  ├─ soft-ignore(target)  => drop edge
  ├─ hard-BL(target)      => drop edge (no UNSAFE mark)
  └─ otherwise            => add edge
```

---

## 5. SAFE 判定与裁剪：最大不动点形式化（核心公式）

### 5.1 形式化符号与谓词

在论文中建议用“图 + 谓词”的方式定义：

* 调用图（仅 code 节点）：$G=(V,E)$，其中 $V\subseteq V_\text{code}$
* 数据引用关系：$R \subseteq V \times V_\text{data}$

对任意函数（符号）(u\in V)，定义谓词：

* $\mathrm{Def}(u)$：符号已定义（非 `SHN_UNDEF`）
* $\mathrm{Code}(u)$：符号类型为 code（`kind=0`）
* $\mathrm{BL}(u)$：存在命中硬黑名单的 **CALL**，实现中由 `calls_blacklisted[u]=1` 表示
* $\mathrm{Writable}(d)$：数据符号 (d) 位于 `SHF_WRITE` 的节（即“可写 data”）
* $\mathrm{RO}(u)$：函数 (u) 的所有 data 引用均为只读：
  $$
  \mathrm{RO}(u)\ \triangleq\ \forall d\ \big((u,d)\in R \Rightarrow \neg \mathrm{Writable}(d)\big)
  $$

并定义后继集合（被调集合）：
$$
\mathrm{Succ}(u)\ \triangleq\ {v\in V \mid (u,v)\in E}
$$

> 注：README 的“主入口”语义可作为额外谓词 $\mathrm{Primary}(u)$；如果你的论文严格以主函数为分析域，可把 $V$ 定义为所有主入口函数集合。

### 5.2 SAFE 的“基集 + 闭包”定义（润色版）

先定义“基集”（满足局部安全约束）：
$$
B\ \triangleq\ {u\in V \mid \mathrm{Code}(u)\wedge \mathrm{Def}(u)\wedge \neg \mathrm{BL}(u)\wedge \mathrm{RO}(u)}
$$
对应实现中的“初筛：drop CALL-hardBL / writable-data，否则 ok=1”。

再定义一个单调算子 $F(\cdot)$：
$$
F(S)\ \triangleq\ {u\in B \mid \mathrm{Succ}(u)\subseteq S}
$$
则 **SAFE 集合**定义为该算子的**最大不动点**（greatest fixed point）：
$$
\mathrm{SAFE}\ \triangleq\ \nu S.\ F(S)
$$
直观含义：SAFE 既要满足局部条件（属于 $B$），又要满足“调用闭包”——它调用到的所有函数也必须 SAFE。对应实现中的“传递剪枝：callee-unsafe”直到收敛。

### 5.3 等价的“最小不动点”表述（更利于写算法与复杂度）

在论文中常用“先定义 UNSAFE，再取补集”的方式，便于说明传播机制。

令：
$$
U_0\ \triangleq\ V\setminus B
$$
并定义传播算子：
$$
G(U)\ \triangleq\ U_0\ \cup\ {u\in V \mid \exists v\in \mathrm{Succ}(u),\ v\in U}
$$
则不安全集合为**最小不动点**：
$$
\mathrm{UNSAFE}\ \triangleq\ \mu U.\ G(U)
$$
并且：
$$
\mathrm{SAFE}\ =\ V\setminus \mathrm{UNSAFE}
$$

> 这一组公式非常适合写成“定理/引理”：$G$ 单调，因此 $\mu U$ 存在；且与 $\nu S$ 互补等价（Kleene 不动点定理语境）。

### 5.4 实现对应的迭代过程（算法框）

实现使用“重复扫一遍边直到不再变化”的方式收敛（`changed` 循环），可在论文中用不动点迭代表述：

**算法 1：SAFE 最大不动点裁剪（不动点迭代形式）**

1. 初始：$S^{(0)} \leftarrow B$
2. 迭代：
   $$
   S^{(k+1)} \leftarrow F\big(S^{(k)}\big)
   $$
3. 终止：当 $S^{(k+1)}=S^{(k)}$ 时，输出 $\mathrm{SAFE}=S^{(k)}$

**图 4：不动点收敛（示意）**

```
B = {通过初筛的节点}
S0 = B
S1 = 移除“调用到非 S0”的节点
S2 = 移除“调用到非 S1”的节点
...
Sk = Sk+1  => SAFE
```

---

## 6. “内核态 → 用户态”地址映射：KASLR 对齐模型

KRG 在构建阶段尝试把 `vmlinux` 的静态符号地址对齐到运行时（KASLR 后）地址，方法是以 `_stext` 计算全局 slide：

**公式 2：KASLR slide 与运行时地址**
$$
\Delta\ \triangleq\ \mathrm{addr}*{run}(_stext)\ -\ \mathrm{addr}*{elf}(_stext)
$$
$$
\mathrm{addr}*{out}(u)\ \triangleq\ \mathrm{addr}*{elf}(u)\ +\ \Delta
$$
实现中从 `/proc/kallsyms` 读取运行时 `_stext`，若成功则对每个输出节点执行 `addr += delta`。

**图 5：地址空间平移（示意）**

```
vmlinux 静态 VA:   [..... _stext = A .....  u = Au .....]
运行时 VA(KASLR):  [..... _stext = B .....  u = Bu .....]
Δ = B - A
Bu = Au + Δ
```

> 论文备注：文件头 `is_runtime_address` 已预留但当前写入路径未设置；查询阶段直接输出节点地址（默认认为已对齐）。 

---

## 7. 输出格式与查询闭包（CSR + 可达集合）

### 7.1 `out.krg` 的 CSR 布局（图 + 表）

SAFE 子图以 CSR（Compressed Sparse Row）形式写入，并且**只写 safe→safe 的边**。

**图 6：`out.krg` 二进制布局（示意）**

```
[FileHeader]
[Node nodes[M]]
[u32 row_ptr[M+1]]
[u32 col_idx[|E|]]
[u32 name_off[M]]
[char name_blob[... '\0' ...]]
```

**表 4：CSR 数组语义**

| 数组                         | 语义               |
| -------------------------- | ---------------- |
| `row_ptr[u]..row_ptr[u+1]` | 节点 u 的出边索引区间     |
| `col_idx[i]`               | 第 i 条边指向的 v      |
| `name_off[u]`              | u 的名字在 blob 中的偏移 |
| `name_blob`                | `\0` 分隔的字符串池     |

### 7.2 查询闭包：可达集合的最小不动点

给定根符号 (r)，查询阶段输出其在 SAFE 图中的可达闭包：

**公式 3：可达闭包（最小不动点）**
$$
\mathrm{Reach}(r)\ \triangleq\ \mu X.\ {r}\ \cup\ {v \mid \exists u\in X,\ (u,v)\in E}
$$
对应实现是一次 DFS/栈式遍历 `seen[]`，只输出 `seen=1` 的节点。

**图 7：闭包查询（示意）**

```
r
├─ a
│  ├─ c
│  └─ d
└─ b
   └─ e
输出：{r,a,b,c,d,e} 的 name/addr/size/kind
```

---

## 8. 复杂度、可解释性与实验复现要点

### 8.1 时间复杂度（论文可用表）

**表 5：核心阶段复杂度（以规模量级描述）**

| 阶段        | 主操作                   | 复杂度（量级）                 |                   |             |   |              |
| --------- | --------------------- | ----------------------- | ----------------- | ----------- | - | ------------ |
| 区间构建      | 节内排序 + 合并             | (O(N_p\log N_p))（按主入口数） |                   |             |   |              |
| Reloc 抽取  | 遍历 relocation entries | (O(R))                  |                   |             |   |              |
| Disasm 抽取 | 线性扫描指令字节流             | (O(                     | \text{exec bytes} | ))          |   |              |
| SAFE 裁剪   | 不动点迭代（实现为重复扫边）        | 最坏可写为 (O(T\cdot         | E                 | ))（T 为迭代轮数） |   |              |
| Query 闭包  | DFS/BFS               | (O(                     | V                 | +           | E | ))（SAFE 子图内） |

> 如果你希望在论文里强调“可扩展性”，可以把 §5.3 的最小不动点 UNSAFE 传播写成“反向边 + 队列”的线性算法（可作为“可选增强”说明），但要明确指出当前实现采用扫描迭代。

### 8.2 可解释性（debug 日志）

`--debug/--dbg-sym` 会打印：

* RANGE：主入口区间表
* CALL/JMP：命中/过滤/no-map（含 abs/rel 与 near=[below|above]）
* PRUNE：keep/drop 与原因 `CALL-hardBL / writable-data / callee-unsafe`

这对论文的“可复现实验/可解释裁剪”非常关键。

---

## 9. 局限与潜在增强（论文需要如实披露）

**表 6：局限点（实现级）与可能影响**

| 局限                              | 影响                 | 可能的论文表述/增强方向                          |
| ------------------------------- | ------------------ | ------------------------------------- |
| 寄存器间接调用（如 `call *%rax`）默认不解析    | 可能漏边，导致 SAFE 误判    | 加启发式回溯解析（README 提到可选开关）               |
| `JMP` 命中硬黑名单不标记 caller 不安全      | 尾调用到副作用函数可能被“漏传播”  | 强化为可选策略：JMP 也传播，或分类 non-prop 前缀       |
| 当前只序列化 SAFE code 节点（data 仅用于判定） | 用户态若要显式“只读数据映射”需扩展 | 扩展 save：把可达 RO-data 一并写出              |
| `is_runtime_address` 标志未写入      | 地址语义依赖构建环境         | 论文中说明：默认 build 侧 KASLR 对齐，query 侧直接输出 |

---

## 小结（可直接作为章节末段落）

本章给出了 KRG 的功能与实现细节：通过“主函数区间重建”稳定解决 `.slowpath` 切片，通过“重定位 + 反汇编”双源抽取函数级依赖，并以**最大不动点 SAFE**形式化定义实现可解释裁剪；同时借助 `_stext` 的全局 slide 实现运行时地址对齐，最终以 CSR 格式输出 SAFE 子图并支持闭包查询。该设计在论文层面兼具**形式化安全语义、工程可复现性与规模可扩展性**。 

