# M11 最终源码规模与机器码审计

> **历史快照。** 本文冻结 `adfe313`/O7 基线，保留用于复算重构前的
> 分层。`6656f97` fallback 边界重构后的当前权威数字为：Raw/VKSO
> 产品 SLOC `1505/1305`，reader closure `2639/2055 B`。最终结论见
> `vkso-tests/VKSO_READ_UPDATE性能报告_20260801.md`；增量证据见
> `FINAL_SOURCE_DELTA.tsv` 和 `FINAL_BINARY_SYMBOLS.tsv`。

## 1. 结论

本报告以不可移动标签 `vkso-o7-final-code-20260731`（peeled commit
`adfe3138e1388c34cb58051d33b2047682ac1a28`）和干净构建的
`o7-final-normal` package 为唯一输入。人工清单选择语义范围，
`count_manifest.py`只负责去空行、去纯注释和算术。

同一组 x86-64 time/getcpu 功能的最终结果是：

| 互斥口径 | Raw SLOC | VKSO SLOC | VKSO - Raw |
|---|---:|---:|---:|
| 运行时功能 | 857 | 867 | +10 |
| 运行时机制 | 490 | 359 | -131 |
| **运行时小计** | **1,347** | **1,226** | **-121（-8.98%）** |
| 功能专属构建/链接 | 158 | 57 | -101 |
| **产品功能合计** | **1,505** | **1,283** | **-222（-14.75%）** |

最终 VKSO 不仅总产品源码少于 Raw，运行时源码本身也少 121 SLOC。O4/ITS
之后曾报告的“约 1298 SLOC”是按提交变化作的临时估算；最终逐文件重审行区间、
排除空行和纯注释后为 1283 SLOC。15 行差异是计数口径校正，不是标签之后又改了
产品代码。

一次性 reusable-text 项目机制为 84 SLOC，验证代码为 360 SLOC，均不混入
1283 SLOC 产品主表。若把两者强行加入 VKSO，会把通用项目能力和测试错误归因
给每个 time ABI。

## 2. 最终分层

运行时功能：

| 类别 | Raw | VKSO | 差异 |
|---|---:|---:|---:|
| U1 用户 public ABI/算法或 wrapper | 359 | 71 | -288 |
| S1 kernel/user 共享 global 算法 | 0 | 291 | +291 |
| K1 普通 kernel global reader | 194 | 212 | +18 |
| K2 canonical producer | 56 | 47 | -9 |
| K4 syscall/cold backend | 132 | 158 | +26 |
| E1 cycles/environment provider | 116 | 88 | -28 |
| **合计** | **857** | **867** | **+10** |

运行时机制：

| 类别 | Raw | VKSO | 差异 |
|---|---:|---:|---:|
| C1 MM/context/namespace 映射 | 371 | 207 | -164 |
| C2 用户 context 启动 | 0 | 74 | +74 |
| K3 shared ABI/publisher | 119 | 78 | -41 |
| **合计** | **490** | **359** | **-131** |

功能代码只比 Raw 多 10 SLOC，剩余差异来自必须显式表达的共享 core 边界、
kernel ABI adapter 和 kernel/user 不同 cold backend。机制代码少 131 SLOC，
来自复用项目已有 ELF 导出、页面替换和加载生命周期，而不是省略功能。

C2 的 74 SLOC 是当前每个 VKSO 用户仍需携带的启动适配：libkernel 内保存
per-process MM/context 槽，测试客户端从 `AT_VKSO_MM_DATA` 读取 auxv、校验
ABI 并绑定。它不进入 read 热路径，但在通用加载器真正自动完成绑定前仍是
产品机制，不能提前删除或移到 P1。

## 3. 相对 M10 的变化

M10 的 VKSO 产品合计为 1358 SLOC；最终为 1283 SLOC，减少 75 SLOC：

| 层 | M10 | 最终 | 变化 |
|---|---:|---:|---:|
| U1 | 149 | 71 | -78 |
| S1 | 265 | 291 | +26 |
| K1 | 217 | 212 | -5 |
| K2 | 47 | 47 | 0 |
| K4 | 191 | 158 | -33 |
| E1 | 78 | 88 | +10 |
| **运行时功能** | **947** | **867** | **-80** |
| C1 | 207 | 207 | 0 |
| C2 | 68 | 74 | +6 |
| K3 | 78 | 78 | 0 |
| **运行时机制** | **353** | **359** | **+6** |
| G1 | 58 | 57 | -1 |
| **产品合计** | **1358** | **1283** | **-75** |

O3 `aa1855e` 专门化 full-width x86 cycle delta。该提交的产品文件物理 churn
为 `+11/-15`，测试为 `+8/-4`；它删除常用 hres 路径的 mask load、比较和
分支，没有新增 ABI 或映射。

O4 `f8d5d16` 的物理 churn 为 `+97/-67`，净增 30 行。它不是在每个 clock
复制 fallback，而是建立一个共享 clock-id/conversion core，加两个
environment-specific cold callback，并让用户 public wrapper tail-jump
进入共享入口。最终 U1、K4 大幅缩小，增加集中在可读的 S1/E1 契约。

从 M10 冻结审计点到最终标签，所选产品文件的 Git 物理 churn 为
`+206/-294`，净减少 88 行。该数字反映编辑过程；最终语义 SLOC 减少 75 行，
两者因空行、注释和范围归属不同而不要求相等。

## 4. ITS/reusable-text 的独立成本

提交 `0c1215f` 解决 secondary-mapped kernel text 经 ITS 改写后跳向仅在
kernel 地址空间可达的动态 thunk 问题。它是一次性 P1 项目能力，不是 time
reader 算法。

最终人工语义 SLOC：

| P1 子层 | SLOC |
|---|---:|
| kernel secondary-mapped-text 谓词与 ITS guard | 17 |
| 构造器解析、校验、闭包和 package 接入 | 62 |
| reusable-text 静态根清单 | 5 |
| **P1 合计** | **84** |

另有 21 SLOC reusable-text 单元测试，归 T1。Git 物理变化应按逻辑基线解释：

- kernel runtime `+29/-4`；其中精简 overlay 首次完整纳入
  `alternative.c`，相对上游真实逻辑差异只有 `+12/-3`，不能把文件的
  1889 行都算成实现；
- DSO 构造器 `+56/-5`；
- package build glue 6 行、根清单 5 行；
- 单元测试新增 24 个物理行。

内核只有一个通用“当前指令是否位于 secondary-mapped text”谓词。新目标只需
进入 `reusable_text.txt`；构造器校验 owner/函数类型、求依赖闭包并保留目标
所在整个 RX 页。它不会随着内核物理页数量在 runtime 中逐页增加特判。

此前已披露、但不加入产品主表的项目机制仍包括：

| P1 项目机制 | 统计性质 | 规模 |
|---|---|---:|
| shared_data R--/NX 支持 | Git 物理 churn | +255/-13 |
| private wrapper ET_REL/relocation/export 适配 | 人工语义 SLOC | 210 |
| private wrapper 自动依赖闭包 | Git 物理 churn | +42/-7 |
| 既有 make_dll、manager、page replacement、KRG | 复用基础设施 | 不归因给 time |

## 5. 最终机器码

机器码使用最终 normal Raw/VKSO 构建中真实 ELF `st_size`，按不重叠 symbol
body 求和。Raw reader 边界为 public vDSO、其独有 cycle helper 和普通 kernel
reader；VKSO 边界为 user wrapper、共享 core、普通 kernel reader以及
clock/private cold reader。`vkso_kernel_gettimeofday_backend` 属于 K4 syscall
路径，和 Raw K4 一样不加入 reader closure。

| reader closure | Raw | VKSO |
|---|---:|---:|
| user public/wrapper | 1,515 B | 105 B |
| user私有依赖 / shared core | 142 B | 1,184 B |
| 普通 kernel reader | 982 B | 421 B |
| kernel clock/private cold reader | 0 B | 366 B |
| **合计** | **2,639 B** | **2,076 B** |
| **VKSO - Raw** | — | **-563 B（-21.33%）** |

相对 M10 的 2829 B，最终 VKSO reader closure 减少 753 B（-26.62%）。
O4 把原来七个展开的 typed hres 函数收敛为 572 B
`vkso_clock_gettime_common`，同时通过 tail-entry 保持成功路径不为 cold
backend 增加 wrapper 往返。

C2 一次性启动另有 196 B text 和 40 B private data，不计 reader closure。
normal `libkernel.so` 为 22,848 B，no-retpoline 为 18,496 B；文件尺寸包含页
对齐和 ELF metadata，不能代替 symbol-body 统计。

## 6. Payload 与映射页

- canonical `vkso_read_state` 为 160 B；
- 含 seq/ABI header 的 `vkso_shared_data` 为 168 B，占一个 4096 B R--/NX
  shared 页；
- `vkso_mm_data` v3 为 40 B，占一个 per-MM 4096 B R--/NX 页；
- `vkso_context` 为 32 B，保存在每进程 private data。

normal DSO 复用两个 kernel RX 页：reader text 与静态 ITS/thunk
reusable-text 页；另复用一个 shared-data 页，并拥有一个 private wrapper RX
页和一个 private RW segment。no-retpoline 没有 ITS/thunk 页，因此复用一个
kernel RX 页和一个 shared-data 页，private 页布局相同。

O4 没有增加共享/MM payload或常驻映射页。ITS修复只在 normal 构建中保留本来
就承载原生 thunk/ITS 的 RX 页；它避免把该页合成为不再匹配内核运行时改写的
替代页。

## 7. 可读性和下一步

最终结构把职责限制为三层：

1. public wrapper 只注入当前地址空间的 MM/context，并 tail-jump；
2. shared core 只实现 clock-id、seq reader 和时间换算；
3. cold callback 分别承载 kernel `k_clock/private timekeeper` 与 user syscall。

该结构比为七种 clock 保留重复 typed 函数、或在内核中为每个 reusable 页追加
特判更短且更容易审计。继续压缩 reader 预计只能换取数个 cycles，并会重新扩大
ABI、MM 或加载器风险，因此最终性能验证前不再修改产品代码。

加载器从 auxv 自动绑定 MM/context 能消除每个 VKSO 用户侧的 C2 适配并降低
使用复杂度，但它属于 O7 完成后的独立通用机制工作，不属于 O7。O7 本身只对
冻结标签执行 READ、UPDATE、并发和证据封存；不得把加载器变化混入本轮结果。

## 8. 可复现文件

- 人工语义范围：`M11_SOURCE_MANIFEST.tsv`
- 机械计数：`M11_SOURCE_COUNTS.csv`
- 机器码 symbol：`M11_BINARY_SYMBOLS.tsv`
- clean reader package：`artifacts/o7-final-normal` 与
  `artifacts/o7-final-no-retpoline`
- clean update package：`artifacts/o7-final-update`
