# VKSO timekeeper / clock_gettime 统一重构计划

## 0. 文档定位

本文是 `vkso-timekeeper-unification` 分支的实施基线，用于指导
`linux-5.15.198-vkso` 中 timekeeper、global-time reader、
`clock_gettime/getres` 分派以及 VKSO 用户态导出路径的统一重构。

本计划首先保证每个阶段都处于可构建、可启动、可验证且可回退的状态；
在完整重构结束前，只进行正确性验证、静态性能分析和代码规模审计，不用
QEMU 或中间裸机数据推断真实性能。最终性能结论只来自同一台裸机、同一配置
和统一脚本下的 Raw/VKSO 对照实验。

PLAN 是设计基线，不是禁止修正的死清单。实现中发现此前未知的调用关系、
并发约束或编译器行为时，可以调整局部设计，但必须遵守本文的数据所有权、
ABI、正确性、验证和 Git 规则。

---

## 1. 总体决策

### 1.1 分支、基线与源码范围

- 主重构线起点为 `d89f2e5`；M00～M09 位于
  `vkso-timekeeper-unification`，M10 的直接 shared 候选位于
  `vkso-timekeeper-direct-shared`。
- 实际功能代码只修改 `test/test_gettime/linux-5.15.198-vkso`。
- `linux-5.15.198-no-vdso` 只用于确认干净结构、识别 VKSO 实际新增工作量。
- Raw Linux 5.15.198 只用于 ABI、语义、错误行为、源码归属和最终性能对照。
- wrapper、测试、构建和实验脚本只在确有需要时修改，并与内核功能改动分开统计。
- 不混入与 timekeeper/clock 模块无关的项目修改和未跟踪实验文件。

### 1.2 重构范围

本次重构覆盖：

- timekeeper 中面向普通 global-time reader 的数据组织与发布；
- `CLOCK_REALTIME`、`CLOCK_MONOTONIC`、`CLOCK_MONOTONIC_RAW`、
  `CLOCK_REALTIME_COARSE`、`CLOCK_MONOTONIC_COARSE`、
  `CLOCK_BOOTTIME`、`CLOCK_TAI` 的读取；
- 上述 clock 的 `clock_getres`；
- `time()`、`gettimeofday()` 对相同 canonical state 的复用；
- 普通 `ktime_get_*` global-time reader；
- `clock_gettime/getres` 的 global/backend 分派与 fallback 边界；
- VKSO shared text、shared data、MM context 和 environment context 的接口；
- Raw 已有 CPU、alarm、dynamic/PTP clock 后端与错误语义的完整保留。

以下内容不强行合并进共享 global-time core：

- process/thread CPU clock 的实际计时后端；
- alarm clock 的 RTC/唤醒语义；
- dynamic clock、FD clock 和 PTP 设备后端；
- NMI-safe、`tk_fast`、writer-locked、early-boot 等特殊 reader；
- `getcpu`、IA32 `__kernel_vsyscall`、x32 vDSO 和已明确关闭的非实验功能。

这些后端仍属于完整功能的一部分，但应通过统一的冷分派边界接入，不能把其
特殊语义硬塞进 global-time 算法。

只有存在用户等价功能的普通kernel reader才进入shared core。没有用户clock ID
对应项的kernel-only转换或coarse offset reader保留private唯一实现，不为形式
上的“统一”新增shared入口。

### 1.3 不可改变的外部接口

必须保持：

- syscall 号、参数、返回值、errno、NULL 和无效参数语义；
- 当前对外 `__vkso_*` 符号的名称、版本、原型和调用约定；
- `ktime_get_*` 等现有内核导出符号、原型和模块 ABI；
- 其他内核子系统现有调用方式；
- MM_data ABI v3 及其 VVAR 式 per-MM special mapping；
- 用户映射的只读、NX、生命周期和 namespace 语义。

允许改变：

- 内部 C 类型、文件组织、函数分层和非公开 helper；
- timekeeper private 数据的内部组织；
- shared-data 内部 ABI 从 v10 **统一升级一次**到 v11；
- project loader 与内部 shared core 之间的非公开契约；
- 内部 core 返回状态，只要 public ABI 语义完全不变。

内部 ABI 发生变化时，kernel producer、导出清单、libkernel.so、手写 wrapper、
ABI 测试和 benchmark 必须在同一阶段同步更新，禁止长期维护 v10/v11 双路径。

### 1.4 核心目标

1. global-time 的 seq、cycle delta、mask、mult/shift、base、namespace offset
   和归一化算法只维护一份源定义。
2. 通过项目机制导出内核构建出的共享算法；用户 wrapper 不重新实现相同公式。
3. kernel 普通 reader 与用户 reader 消费同一种 canonical read state。
4. producer 直接维护 shared 页中的 canonical state，消除
   `vkso_time_compat_prepare()` 式跨数据模型逐字段转换。
5. 不保留 private canonical staging 或第二次 payload 搬运；shared seq
   只覆盖最终字段派生和写入，实际冲突成本由并发实验验证。
6. public ABI wrapper 保持薄；已知 clock 的热路径不经过统一大 switch、
   backend、syscall 或新增间接调用。
7. 功能、可读性和可验证性优先；不为减少几行代码制造晦涩宏或隐含状态。

---

## 2. 正确性、性能与代码规模原则

### 2.1 每阶段正确性

每个阶段完成时至少满足：

- 受影响的配置可构建；
- QEMU 能启动并完成对应 ABI/语义矩阵；
- 与 Raw 对照的已有功能行不得减少，语义 diff 必须为空；
- 新增的数据竞争、seq、namespace 或 backend 风险有定向测试；
- 日志中无相关 panic、BUG、WARNING、lockup 和不可解释的时间倒退；
- 阶段报告记录改动、验证、残余风险和下一阶段入口。

阶段退出条件未满足时不得继续叠加下一阶段功能。

### 2.2 中间阶段性能处理

M01～M09 不进行裸机性能比较，也不以 QEMU cycles 作为优化依据。中间阶段只做：

- 热路径/更新路径调用图检查；
- load、store、branch、call/ret、间接调用和 barrier 数量的静态比较；
- 访问 cache line 数和发布字节数估算；
- seq 奇数区间的源代码与汇编边界检查；
- `objdump`、符号大小和 section 布局检查；
- 对可能退化的原因形成可验证假设。

这些结果写入阶段报告的“静态性能模型”，只能用于避免明显不合理的设计，
不能表述为真实性能提升。M10 完成全部功能后才构建最终镜像并执行裸机实验。

### 2.3 代码规模与开发工作量

代码量必须先由人工按语义划分，再由脚本做机械复算。分类互斥且不重不漏：

- shared global-time algorithm；
- kernel private producer/timekeeper；
- shared publisher 与内部数据 ABI；
- kernel public reader/dispatcher 接入；
- user public wrapper/fallback；
- CPU/alarm/dynamic 等必要 backend；
- MM/context、映射和项目机制；
- 构建/链接胶水；
- 测试、断言和 benchmark；
- 仅为过渡或兼容而存在、最终应删除的代码。

Raw 必须用相同功能边界重新分类，不能只统计 vDSO 文件，也不能把 x32、
IA32 或实验明确不实现的功能算入 Raw 对照。`static_assert`、测试 stub 和实验
脚本不算产品功能 SLOC，但应在测试规模中单列。脚本只负责统计已人工确认的
文件、符号或行区间，不能替代语义判断。

每阶段记录源码净增删、核心符号 `.text/.rodata/.data` 大小和过渡代码余额；
最终报告同时给出“产品功能代码”和“项目通用机制”两套口径。

---

## 3. 目标架构

### 3.1 数据所有权

#### A. timekeeper private

只保存不能暴露或普通 reader 不需要的 kernel-only 状态，例如：

- `clocksource *` 及 clocksource 切换状态；
- NTP、leap second、suspend/resume 的中间状态；
- writer 锁、调试、统计和错误恢复状态；
- producer 计算所需但不属于读取快照的临时量；
- fast/NMI 和 writer-locked 特殊路径需要的状态。

private 中不得长期保留一份与 canonical read state 含义相同、独立更新的
第二套 reader 数据。

#### B. canonical `tk_read_state`

这是 global-time reader 的唯一逻辑事实来源。producer 在持有既有
timekeeper writer 同步的条件下直接维护它；所有 derived base 也是 producer
正式职责，而不是发布前的兼容转换。

canonical state 直接位于物理独立的 shared 页。kernel 通过可写 alias 维护，
用户通过项目机制只读映射同一物理页；不再存在 kernel-private canonical
staging、real/shadow canonical 副本或第二次 payload 发布。

#### C. shared_data

- 只包含 seq、ABI header、canonical `tk_read_state` 和极少事件型全局数据；
- 使用项目机制建立 R--/NX 用户映射；
- 物理上与 timekeeper private 数据隔离，避免相邻 private 数据泄漏；
- 不含内核指针、锁、函数地址、per-MM namespace 数据或可写用户状态；
- kernel 普通 reader 和用户 reader 读取同一物理状态和同一 seq 代际。

#### D. MM_data/context_data

- 继续使用 MM_data ABI v3 和 VVAR 式 per-MM special mapping；
- 只保存 namespace mask、monotonic offset、boottime offset 等 per-MM 内容；
- fork、exec、setns、映射回收及只读权限保持现有语义；
- root namespace 可用 NULL/零偏移语义优化，但 public ABI 不增加额外模式；
- MM_data 不复制 global time state，不引入第二个 global seq。

#### E. environment context

PVClock、Hyper-V、TSC 和 kernel clocksource 的地址或 provider 状态属于执行
环境依赖，通过 kernel/user 各自的 environment context 或专用入口提供，
不得写入全局 shared 页或 MM_data。

### 3.2 ABI v11 canonical layout

M01 首先验证 monotonic 与 raw 是否在所有合法 writer 路径上共享：

- `clock_mode`；
- `shift`；
- `cycle_last`；
- `mask`。

若不变量成立，ABI v11 默认使用一个共同 cycle descriptor：

```text
clock_mode
shift
cycle_last
mask
mono_mult
raw_mult
```

并保存：

- realtime base；
- monotonic base；
- boottime base；
- TAI base；
- monotonic-raw base；
- realtime/monotonic coarse；
- clock resolution；
- timezone 等低频事件数据。

若审计发现任何可达路径允许 mono/raw 的公共字段不同，则不增加运行时猜测或
修复分支，ABI v11 直接使用两个显式 cycle descriptor。该预设决策无需暂停，
但必须在 `DECISIONS.md` 记录证据、布局变化和新增测试。

布局约束：

- 使用固定宽度、自然对齐字段，禁止 C 指针和锁；
- header、seq、常用 cycle 参数和 realtime 热数据优先位于首个 64-byte 区域；
- monotonic 常用数据至多再访问一个 cache line；
- raw 数据独立成组并对齐，避免污染 realtime/monotonic 热路径；
- `time()` 使用的 realtime seconds 必须自然对齐，并验证单次 64 位发布/读取；
- 有效 shared payload 不超过一页；
- 编译期断言覆盖总大小、关键 offset、cache-line 边界、原子字段对齐和无指针
  的显式成员约束。

cache-line 布局是静态访问模型，不预先宣称能提升 cycles；最终效果由 M10
裸机结果验证。

### 3.3 producer 与短发布

当前直接 shared producer 的顺序固定为：

1. 在既有 writer 锁/seq 保护下更新 private 状态；
2. 完成 NTP、leap、clocksource 切换等复杂 private 计算；
3. 将 shared seq 置为奇数并执行所需的写侧排序；
4. 从 private owner 直接派生并写入最终 canonical 字段；
5. 执行与 reader 协议配对的 memory barrier；
6. 将 shared seq 置为偶数。

约束：

- shared seq 为奇数期间禁止 NTP、除法和 clocksource 切换等复杂状态更新；
- 固定的加法、移位、归一化和最终 scalar store 在该区间直接完成；
- 不复制整页，不无条件重写 timezone 等事件型字段；
- 先保证协议正确，再依据汇编统计发布字段、字节数和 seq 奇数窗口；
- `time()` 的 seconds 不得发生撕裂；
- writer-locked helper 不得读取自己正在更新的 shared seq；
- memory ordering 必须同时说明 kernel reader 和用户 reader 的配对关系。

若 M10 并发证据表明直接派生造成不可接受的 retry 或 tail latency，可将
private staging + 短 scalar publisher 作为独立对照候选回退；不得同时长期
保留两套 canonical owner。

### 3.4 可导出的共享算法

共享 core 只负责：

- seq snapshot/retry；
- cycles delta 与 `mask` wrap；
- `mult/shift` 换算；
- base 合成；
- namespace offset；
- timespec/timeval 归一化；
- global clock 的 typed 读取原语。

共享 core 不得：

- 发起 syscall；
- 访问 `k_clock`；
- 处理 CPU/alarm/dynamic 设备语义；
- 访问 timekeeper private 指针或 writer 锁；
- 根据 kernel/user 身份选择大段不同算法；
- 在常用 typed reader 中执行统一大 switch。

项目机制负责从内核构建产物中导出 shared text/shared data。用户目录中不得
复制或重写相同 global-time 公式。若为消除热路径间接调用而需要 kernel/user
编译期专门化，只允许环境相关的最小 cycles provider/入口生成两个机器码实例；
算术、seq、base 和归一化仍来自同一源定义，并在代码量统计中如实单列。

### 3.5 cycles provider

- kernel provider 使用当前有效 clocksource 的既有读取语义；
- user provider 支持 TSC、PVClock 和 Hyper-V；
- 不支持或临时不可用的 mode 返回明确内部状态，由 public 边界 fallback；
- 热路径不新增通用函数指针；kernel 必需的现有动态 clocksource read 不算新增；
- provider 必须在 seq 两次检查之间取样，保证参数与 cycles 属于同一快照；
- `mask` 语义必须与 Raw clocksource delta 一致；
- PV/HV 先要求静态配置和 QEMU 功能路径正确，最终实验可只以裸机 TSC 为主。

### 3.6 reader 与 dispatcher 分层

代码层次固定为：

```text
public ABI wrapper
    -> 单次分类的紧凑 global dispatcher / 固定 ID 薄适配器
        -> shared seq/arithmetic primitive + environment provider
            -> backend/fallback（仅失败或非 global clock）
```

热路径约束：

- public `clock_gettime` 使用一份紧凑 global dispatcher，只分类一次 clock ID，
  不生成 jump table，也不同时保留“位图分类 + typed reader 二次分类”；
- 固定 ID 的 kernel API 可以保留 typed 薄适配器，但不得复制七份 seq、cycles、
  base 和归一化主体；
- user 成功路径不进入 syscall fallback，也不先调用 backend；
- 有用户等价功能的kernel普通`ktime_get_*`以root namespace typed薄wrapper
  进入共享算法，不支付MM_data NULL检查和generic dispatcher成本；
- kernel-only reader直接使用private owner，不生成没有用户消费者的shared
  typed入口；
- public wrapper 之后不得出现多层只转发参数的包装；是否 inline/tail-call 由
  汇编检查决定，目标是成功热路径最多保留一个必要的非内联算法调用；
- 不为追求“单一入口”引入新的函数指针、重复 mode 判断或 call/ret；
- shared core 返回内部 `OK`、`UNSUPPORTED_MODE`、`BACKEND_REQUIRED` 等有限
  状态，但成功路径应能被编译器收敛成最少分支。

fallback 约束：

- user public wrapper 只有一个 syscall fallback 出口；
- kernel generic dispatcher 只有一个 backend 出口；
- fallback 不得重新进入已经失败的 shared core；
- CPU、alarm、dynamic/PTP 和 invalid ID 继续保持 Raw 的权限检查、错误码、
  NULL、设备和 RTC 语义；
- 如集中 fallback 可重复造成热路径额外开销，可使用 user-local 冷 trampoline，
  但不得复制 global 算法或改变 syscall ABI。

### 3.7 特殊 reader

以下路径默认不读取 shared seq，除非 M01 证明上下文安全：

- `tk_fast` 和 NMI-safe reader；
- timekeeper writer 持锁期间的 reader；
- early boot、clocksource 尚未稳定时的 reader；
- suspend/resume、clocksource switch 中的内部 helper；
- 依赖尚未发布 private 中间状态的 producer helper。

它们可读取原有 private producer state 或保留专用快照，但必须在矩阵中说明：
调用上下文、同步方式、数据来源、为何不能共用普通 reader，以及何时与
canonical state 对齐。不得用“兼容性”作为未审计重复算法的理由。

---

## 4. 预期代码组织

最终文件边界以 M01 审计结果为准，但职责必须清晰：

- **internal ABI**：v11 固定宽度结构、状态码、offset/size 断言；
- **producer/private**：NTP、settime、leap、suspend、clocksource switch；
- **canonical producer**：唯一 shared 写入口、字段派生和 memory-order 协议；
- **shared primitives**：seq、delta、mult/shift、normalize；
- **typed global readers**：realtime/monotonic/raw/coarse/boottime/TAI；
- **providers**：kernel clocksource、user TSC/PV/HV；
- **kernel adapters**：有用户等价功能的 `ktime_get_*` 薄 wrapper；
- **kernel-only readers**：只在内核存在的转换/offset功能直接使用private状态；
- **public user wrappers**：`__vkso_*` ABI、MM/environment 参数绑定和 syscall
  fallback；
- **cold dispatcher/backends**：CPU、alarm、dynamic/PTP、invalid；
- **tests**：ABI、语义、并发、权限和 benchmark，不进入产品 SLOC。

禁止：

- 同一字段在两个结构中由不同 writer 独立维护；
- public wrapper、dispatcher 和 core 各做一次相同 clock/mode 判断；
- user 目录复制 kernel 算法；
- 热路径内部大段 `#ifdef`；
- 为减少 SLOC 构造难以调试的多语句宏；
- 循环 include、循环调用或 core 反向依赖 public wrapper；
- 长期保留“新旧任选”的双实现和测试专用功能开关。

---

## 5. 阶段产物与执行规则

计划目录至少维护：

- `PLAN.md`：设计基线与阶段状态；
- `BASELINE.md`：M00 证据、commit/config/image/result hash；
- `FIELD_OWNERSHIP.md`：字段 writer/reader/同步/归属；
- `READER_CONTEXT_MATRIX.md`：reader 上下文和可迁移性；
- `BACKEND_SEMANTICS.md`：clockid、后端、错误与 fallback；
- `ABI_V11.md`：布局、offset、不变量和发布协议；
- `DECISIONS.md`：未预期问题与设计决策；
- `reports/M00.md`～`reports/M10.md`：阶段报告；
- `CODE_SIZE_MANIFEST.md`：人工分类后的统计清单；
- `FINAL_REPORT.md`：最终功能、性能和代码规模证据索引。

每个阶段：

1. 先更新本阶段清单和假设；
2. 实现最小闭环，不混入下一阶段；
3. 完成退出验证；
4. 写阶段报告；
5. 形成独立 Git commit，记录源码 hash；
6. 自动进入下一阶段。

只有发生外部 ABI 改变、MM_data ABI/映射改变、无法解释的并发语义、
特殊 reader 安全性冲突、Raw backend 功能缺失或实验范围重大变化时暂停请求
决策。已有预案（例如 mono/raw 改用双 descriptor）按计划执行并记录即可。

---

## 6. 分阶段实施

### M00：冻结证据与工作边界

任务：

- 确认分支、起点 `d89f2e5` 和工作树范围；
- 记录 temporary-final 的功能、reader、syscall/kernel read、update-side、
  read/update 并发、源码和机器码结果；
- 记录 Raw、temporary-final 的 commit、config、Image、libkernel.so 和脚本 hash；
- 验证现有 QEMU preflight、bare-metal reader、update 与 concurrent 脚本可定位；
- 建立 `BASELINE.md`、`CODE_SIZE_MANIFEST.md` 初稿；
- 明确 no-vDSO/Raw/VKSO 的目录对应关系和不参与比较的功能。

正确性验证：

- 不修改运行时代码；
- 所有基线结果路径可读，摘要可由原始 CSV/日志复算；
- 当前分支相对起点的范围清楚，无无关文件混入。

退出条件：

- 基线、配置、镜像、脚本和结果均可定位复算；
- 形成独立 M00 commit 与 `reports/M00.md`。

### M01：字段、reader 与 backend 审计

任务：

- 对 `timekeeper`、`tk_read_base`、现有 VKSO shared/context 的每个字段记录：
  writer、reader、锁/seq、更新事件和生命周期；
- 将字段唯一分类为 private、canonical shared、MM_data、environment、
  fast/NMI-only 或可删除；
- 审计 mono/raw 的 `clock_mode/cycle_last/mask/shift` 公共不变量；
- 将全部相关 `ktime_get_*` 调用按 process、IRQ、NMI、writer-locked、
  early boot、suspend/switch 分类；
- 列出 global、CPU、alarm、dynamic/PTP clock 路径、权限和错误语义；
- 标记 user/kernel 重复公式、compat 转换和多余 wrapper；
- 画出当前与目标的 producer→publish→reader 调用图；
- 产出三个矩阵和 `DECISIONS.md` 初稿。

正确性验证：

- 审计必须以实际调用关系和 writer 路径为证据；
- 每个迁移候选必须有唯一所有者和同步说明；
- 每个 public clockid 必须能落到明确 global reader、backend 或 invalid 语义。

退出条件：

- `FIELD_OWNERSHIP.md`、`READER_CONTEXT_MATRIX.md`、
  `BACKEND_SEMANTICS.md` 无未分类项；
- mono/raw descriptor 采用单份或双份的决策已经锁定；
- 未审计对象不得进入 M02/M03 迁移。

### M02：定义 ABI v11，保持算法行为不变

任务：

- 定义 canonical `tk_read_state` 和 v11 shared layout；
- 添加大小、offset、对齐、cache-line、原子字段和无指针约束断言；
- 用现有 producer/compat 数据暂时填充 v11；
- reader 改为解析 v11 布局，但保留现有算法、fallback 和数据来源行为；
- 同步 libkernel.so 导出清单、手写 wrapper、测试 ABI 和 benchmark 结构；
- 删除 v10 运行时支持，不形成双 ABI 长期路径；
- 编写 `ABI_V11.md`，包含 reader/writer memory-order 协议。

构建矩阵：

- 默认 VKSO 配置；
- `CONFIG_TIME_NS=y/n`；
- PVClock 相关配置；
- Hyper-V 相关配置；
- 与现有实验一致的 normal thunk 配置。

正确性验证：

- QEMU ABI/语义矩阵与 M00 基线一致；
- shared/MM VMA 仍为正确权限，shared 数据无指针和 private 泄漏；
- v11 layout 的 kernel、wrapper、测试所见 offset 完全一致。

退出条件：

- v11 单一启用，外部 ABI/MM v3 不变；
- 无功能变化和语义 diff；
- 形成 M02 commit 与报告。

### M03：重构 timekeeper private/read 所有权

按小组迁移，禁止一次性重写整个 `timekeeping.c`：

1. cycle descriptor、mult/shift、mask 和 cycle base；
2. realtime/monotonic bases；
3. raw、boottime、TAI 和 coarse；
4. NTP、settime、leap、timezone 事件；
5. suspend/resume 和 clocksource switch；
6. writer-locked/fast/NMI 对应的 private 读取接口。

每组任务：

- producer 直接维护 canonical 字段；
- 删除该组旧 reader 状态的独立 source-of-truth；
- 保留必要 private 中间量，但记录其不可共享原因；
- 为持锁调用提供不读取 shared seq 的 private helper；
- 检查 timekeeper update 锁顺序和 seq 嵌套；
- 构建并运行该组定向 QEMU 测试后再迁移下一组。

正确性重点：

- monotonic/raw 不倒退；
- settime 不错误影响 monotonic/raw；
- boottime 正确包含 suspend；
- TAI/leap/NTP 与 Raw 行为一致；
- clocksource switch 前后 cycle 参数与 base 属于同一代状态；
- early boot 和 writer-locked 不发生 seq 自等待。

退出条件：

- global reader 数据只有 canonical 一份逻辑来源；
- private 中不存在未说明的重复 reader state；
- 所有事件路径和特殊上下文测试通过；
- 形成 M03 commit 与报告。

### M04：实现短发布并删除转换层

任务：

- publisher 接收 canonical `tk_read_state`，不接收另一种 compat 类型；
- 将全部复杂计算移出 shared seq 奇数区间；
- 实现显式 scalar `WRITE_ONCE` publisher 和配对 barrier；
- timezone/resolution 等事件字段按事件发布；
- 删除 `vkso_time_compat.h`、`vkso_time_compat_prepare()` 及全部调用；
- 记录各更新事件发布字段、字节数和 seq 奇数窗口；
- 检查 compiler 是否把发布重排或生成非预期大复制。

正确性验证：

- 并发 reader/writer 压力下无 torn snapshot；
- `time()` seconds 原子读取；
- coarse 与高精度 base 更新关系正确；
- retry 仅由真实发布并发触发；
- publisher 期间无 private 数据泄漏。

退出条件：

- 跨数据模型转换层完全消失；
- shared 奇数区间只包含必要发布；
- 形成 M04 commit 与报告。

### M05：建立纯共享读取 core

任务：

- 分离 environment provider 与 seq/arithmetic primitives；
- 恢复并验证 Raw 一致的 `mask` wrap 语义；
- 为七种 global clock 建立 typed reader；
- 让 `time()`、`gettimeofday()`、`clock_getres()` 复用相同 canonical 原语；
- core 内部移除 syscall、`k_clock` 和 fallback-mode 耦合；
- user wrapper 只完成 ABI 参数、MM/environment 注入和失败出口；
- 确认用户路径调用的是项目导出的内核构建算法，不是用户侧复制实现；
- 检查专门化是否仅复制最小 provider/entry。

正确性验证：

- 所有 global clock、NULL 组合和 getres 语义与 Raw 一致；
- namespace root/非 root、fork/exec/setns 正确；
- invalid clock mode 能稳定进入 public fallback；
- PV/HV 静态配置和 QEMU 可达路径通过；
- seq retry 和人工构造的 mask wrap 测试通过。

退出条件：

- shared core 是纯计算/读取组件；
- user/kernel 不再维护两份 global-time 公式；
- 形成 M05 commit 与报告。

### M06：统一普通 kernel reader

任务：

- 根据 M01 矩阵，将安全的普通 `ktime_get_*` 改成 root-namespace typed 薄 wrapper；
- 保持函数名、参数、返回类型、export symbol 和模块 ABI；
- 已知 clock 的函数直接进入 typed reader，不经过 generic dispatcher；
- fast/NMI、writer-locked、early-boot 和明确专用路径继续使用 private helper；
- 不批量修改约 624 个调用者，通过原函数名兼容；
- 删除普通 reader 中已被 shared core 取代的重复算法。

正确性验证：

- process/IRQ reader 与 Raw 一致；
- NMI/fast/writer-locked 路径无锁递归、seq 自等待或未初始化访问；
- 内核 root-namespace reader 不读取 MM_data；
- 模块和其他子系统无需改调用方式。

退出条件：

- 普通 kernel reader 成为可读的薄适配层；
- 特殊 reader 的保留原因逐项可审计；
- 形成 M06 commit 与报告。

### M07：统一 clock dispatcher 与 backend 边界

任务：

- global clock 正常路径直接使用 typed shared reader；
- CPU、alarm、dynamic/PTP 只由 generic cold dispatcher 调用；
- user wrapper 集中 syscall fallback；
- kernel generic path 集中 backend fallback；
- 保持 Raw 的权限、RTC、FD、invalid ID、NULL 和 errno 语义；
- 检查成功路径的 compare、branch、call/ret、间接调用和参数搬运；
- 消除 wrapper/dispatcher/core 间重复 clock/mode 判断；
- 必要时以独立提交试验 cold trampoline，不复制核心算法。

正确性验证：

- global clocks；
- process/thread CPU clocks；
- alarm clocks 在有/无 RTC 配置；
- dynamic/PTP/FD clock；
- NULL 输出指针和无效 clockid；
- fallback 恰好执行一次且不回到 shared core。

退出条件：

- global 热路径与 backend 冷路径边界清晰；
- 全部 clock_gettime/getres 语义与 Raw 一致；
- 形成 M07 commit 与报告。

### M08：清理、可读性与静态效率重构

任务：

- 删除无调用旧 global reader 算法、compat 类型、桥接和临时测试开关；
- 合并重复声明、状态判断和只转发 wrapper；
- 固定 public wrapper→typed/dispatcher→primitive/provider 的层次；
- 将热路径 `#ifdef` 收敛到 provider 或构建边界；
- 注释只解释不变量、同步和 fallback 原因，不记录开发历史；
- 人工复核函数命名、文件职责、错误处理和 include 依赖；
- 更新 `CODE_SIZE_MANIFEST.md`，对 Raw/VKSO 重新做无重叠分类；
- 生成静态性能模型与关键汇编对照。

不得：

- 为追求 Raw 机器码一致而牺牲合理结构；
- 用宏隐藏控制流；
- 为几行 SLOC 增加动态分派；
- 在没有功能证据时删除特殊 backend；
- 在此阶段夹带未经隔离的性能补丁。

退出条件：

- 编译器/链接器无可确认的死代码；
- 无临时双路径和无意义 wrapper；
- 人工代码审查通过；
- 源码和机器码归属可复算；
- 形成 M08 commit 与报告。

### M09：完整正确性验证

构建：

- 默认配置；
- `CONFIG_TIME_NS=y/n`；
- PVClock；
- Hyper-V；
- 实验使用的 normal thunk 配置；
- 必要的静态 no-thunk 构建仅用于确认代码生成，不做性能结论。

QEMU/定向验证：

- Raw/VKSO public ABI 和语义矩阵，diff 必须为空；
- 七种 global clock、time、gettimeofday、getres；
- seq 并发、mask wrap、无效 clock mode；
- NTP、settime、TAI、leap；
- suspend/resume、clocksource switch；
- root/non-root namespace、fork/exec/setns、多线程；
- CPU、alarm、dynamic/PTP、invalid clock；
- process、IRQ、NMI、writer-locked、early boot reader；
- shared/MM VMA 权限、R--/NX、映射生命周期；
- shared 页无 private 数据和内核指针泄漏；
- fallback 次数、路径和错误语义。

阻塞失败：

- panic、BUG、WARNING、lockup；
- 不可解释的时间倒退或跨 clock 关系错误；
- ABI 矩阵行减少或 Raw/VKSO semantic diff 非空；
- seq 死循环、明显 torn snapshot、NMI/锁递归；
- public ABI、MM v3 或映射生命周期发生未批准改变。

退出条件：

- 所有必需配置、功能和安全属性通过；
- 生成一个只包含完整正确功能的 pre-performance tag；
- 形成 M09 commit、报告和最终测试清单。

### M10：最终裸机性能、代码量与证据

M10 是唯一进行正式性能结论的阶段。

#### A. user/kernel read

- normal Raw；
- normal VKSO；
- no-thunk Raw；
- no-thunk VKSO；
- 分别记录 user read、syscall/kernel read、cycles、百分比、retry 和 fallback；
- no-thunk 只用于解释 return thunk/retpoline 影响，normal 是主要结论。

#### B. update-side

- Raw/VKSO 使用相同 update workload、CPU 绑定和配置；
- 测量完整 update、关键 phase、发布字节和 seq 奇数窗口；
- 区分 private 复杂计算、canonical 维护、shared publish 和兼容工作；
- 禁止把仅 VKSO 执行的测试 instrumentation 算作产品 update 成本。

#### C. read/update 并发

- 同时记录 reader latency、tail、throughput、retry 与 writer update 成本；
- Raw/VKSO 使用同一频率、CPU 拓扑和隔离策略；
- 解释 retry 变化与固定路径成本，不能只用 retry 推断总体性能。

#### D. 代码规模

- 按 `CODE_SIZE_MANIFEST.md` 人工分类复算 Raw/VKSO SLOC；
- 分别报告 user 专属、kernel 专属、shared core、backend、ABI/publisher、
  MM/项目机制和测试；
- 报告源码增删、净变化和必要转换/兼容代码；
- 用符号和 section 报告 `.text/.rodata/.data` 机器码变化；
- 保存关键函数汇编、调用图、config 和构建工具版本。

#### E. 优化规则

- 先用最终结果定位明确热点，再做一个假设一个提交；
- 每个优化同时重跑相关功能和对应性能测试；
- 不以减少某个单项 cycles 为由恶化总体语义、update 或并发；
- 性能候选失败则回到 M09 pre-performance tag，不叠加补丁掩盖；
- 可接受的最终退化必须有稳定复现、汇编/路径证据和结构收益说明。

退出条件：

- Raw/VKSO 性能结果在同一实验协议下可复算；
- 显著变化均有路径或代码生成证据；
- 代码统计人工分类明确、脚本复算一致且不重不漏；
- 保存 source/config/Image/libkernel/result hash；
- `FINAL_REPORT.md` 独立可读，形成最终 commit/tag。

---

## 7. 未预期问题处理

### 7.1 当前阶段内可直接解决

不改变外部 ABI、核心不变量、MM 映射和阶段范围的局部问题，可在当前阶段
修正并继续。阶段报告必须记录：

- 现象、根因和影响面；
- 至少两个可行候选或“不修改”的对照；
- 选择理由；
- 新增验证；
- 对热路径、update 和代码规模的静态预期。

### 7.2 必须更新决策记录

以下情况先写入 `DECISIONS.md`，再实现：

- 字段无法获得唯一所有权；
- mono/raw 公共 cycle 不变量不成立；
- shared 发布需要改变 memory-order 协议；
- 普通 reader 被发现可在 NMI/writer-locked 上下文调用；
- backend 语义无法通过现有冷分派保持；
- 编译期专门化产生超出 provider 的算法复制；
- shared payload 超过一页或发生 private 数据暴露风险。

本文已规定的备选方案可记录后自动执行；超出既定外部 ABI、MM v3、
功能范围或实验可比性的重大变化才暂停请求确认。

### 7.3 回退与试验

- 任一阶段退出条件失败，回到上一阶段通过的 commit，先修正设计；
- 不用兼容补丁长期并存来掩盖所有权或并发问题；
- 性能布局、整块复制、inline、cold trampoline 等候选必须独立 commit；
- 失败候选保留在可定位分支或 commit 中，不进入主实施线；
- 回退不得删除基线证据和失败原因记录。

---

## 8. 风险清单与对应控制

| 风险 | 主要控制 |
|---|---|
| shared seq 与 timekeeper writer 锁嵌套 | M01 reader-context 审计；writer-locked 使用 private helper |
| canonical/private 双 source-of-truth | shared 页是唯一 canonical；private 只保留生产/特殊 reader 状态 |
| mono/raw cycle 参数并非恒等 | M01 全 writer 审计；不成立则 v11 双 descriptor |
| 64 位字段撕裂或发布重排 | 自然对齐、`WRITE_ONCE`、配对 barrier、并发测试与汇编检查 |
| shared 暴露 private 指针/相邻数据 | 独立物理页、无指针断言、VMA/内容检查 |
| namespace 语义退化 | MM v3 不变；root/non-root、fork/exec/setns 测试 |
| NTP/leap/settime/TAI 关系错误 | 事件级迁移与 Raw 定向对照 |
| suspend/clocksource switch 快照混代 | cycle descriptor 与 bases 同次 canonical 更新/发布 |
| NMI/early boot seq 自等待 | 特殊 reader 不强并入普通 shared reader |
| CPU/alarm/dynamic 功能被过度统一 | 保留后端，只统一 cold dispatcher |
| fallback 重入或执行两次 | user/kernel 各唯一 cold 出口，路径计数测试 |
| 共享算法在用户态被重新实现 | 导出清单和符号审计；user SLOC 分类检查 |
| 过度 wrapper 抵消复用收益 | 固定三层结构，汇编检查 call/ret 与参数搬运 |
| 为代码量牺牲可读性 | 禁止晦涩宏；人工审查先于脚本统计 |
| QEMU 性能误导设计 | M01～M09 不作 cycles 结论；M10 统一裸机测量 |
| 配置差异破坏对照 | 保存 config/image hash；Raw/VKSO 仅功能相关差异 |

---

## 9. 阶段报告模板

每个 `reports/Mxx.md` 至少包含：

1. 阶段目标与实际范围；
2. 关键设计决定和不变量；
3. 修改文件与符号；
4. 数据所有权/调用图变化；
5. 构建配置与命令；
6. QEMU/定向测试结果；
7. Raw 语义对照结果；
8. 静态性能模型：
   - 热路径分支、call/ret、间接调用；
   - cache-line 访问估算；
   - update store/bytes/barrier 和 seq 窗口；
9. 源码与机器码规模变化；
10. 残余风险、未决项和下一阶段入口；
11. commit hash 与相关证据路径。

M01～M09 的“静态性能模型”不得写成裸机性能结论。

---

## 10. 最终验收标准

### 功能与 ABI

- syscall、`__vkso_*`、`ktime_get_*` 和其他子系统接口保持不变；
- MM_data ABI v3 与 VVAR 式映射保持；
- shared 内部 ABI 只升级为 v11，不保留运行时双版本；
- global、CPU、alarm、dynamic/PTP、invalid 的功能和错误语义不低于 Raw；
- QEMU Raw/VKSO semantic diff 为空。

### 数据与并发

- private、canonical shared、MM_data、environment 和 special-reader 状态边界明确；
- 每个 reader 字段只有一个逻辑 owner；
- shared 页最小、R--/NX、无指针/锁/private 泄漏；
- NTP、除法和clocksource切换等复杂更新位于shared seq奇数区间之外；最终固定
  字段派生与写入由并发实验验证；
- `time()` 原子、mask wrap、namespace、NTP、suspend 和 clock switch 正确；
- NMI/writer-locked/early-boot 路径无 seq 自等待。

### 复用与结构

- global-time 算法在 kernel/user 只维护一份源定义；
- 用户通过项目机制使用内核构建的共享算法，不重新实现相同公式；
- 普通 kernel reader 是 root-namespace typed 薄 wrapper；
- 特殊 reader 和必要 backend 明确保留；
- 不存在 `vkso_time_compat_prepare()` 式跨模型转换；
- public wrapper、dispatcher、core 和 provider 职责清楚，无循环依赖；
- 热成功路径无统一大 switch、无 syscall/backend、无新增通用间接调用；
- 代码可读、可审计，不靠晦涩宏压缩行数。

### 证据

- 每个阶段均有通过状态、独立 commit 和报告；
- M01～M09 的正确性证据完整，未用 QEMU cycles 代替性能结论；
- M10 在裸机完整测量 read、syscall/kernel read、update 和 read/update 并发；
- 性能变化有调用路径、汇编或发布协议证据；
- Raw/VKSO 源码和机器码按同一语义边界统计，不重不漏；
- source、config、Image、libkernel.so、脚本和结果 hash 可复算。

---

## 11. 当前里程碑状态

| 阶段 | 状态 | 进入条件 |
|---|---|---|
| M00 冻结证据 | 已完成 | 分支与起点确认 |
| M01 字段/reader/backend 审计 | 已完成 | M00 通过 |
| M02 ABI v11 | 已完成 | M01 无未分类项 |
| M03 timekeeper 所有权重构 | 已完成 | v11 行为等价 |
| M04 短发布/删除转换层 | 已完成 | canonical producer 完整 |
| M05 纯共享读取 core | 已完成 | 发布协议通过 |
| M06 普通 kernel reader 统一 | 已完成 | shared core 功能完整 |
| M07 dispatcher/backend 重构 | 已完成 | 普通 reader 稳定 |
| M08 清理与静态审计 | 已完成 | 完整分派通过 |
| M09 完整正确性验证 | 已完成 | 无临时/双重路径 |
| M10 裸机性能与最终证据 | 等待用户介入 | M09 pre-performance tag |

M00～M09 已通过。M09 的 validation 与 production 配置均完成 Raw/VKSO
完整 QEMU 对照；正常 RTC 与无 RTC 四种启动、真实 leap insertion、
clocksource switch、S3 suspend/resume、动态 clock、特殊 reader、seq、
namespace、fallback 次数和映射权限均通过。两套 Raw/VKSO 最终语义矩阵各
113 行且 diff 为空。下一阶段是需要用户介入的 M10 裸机性能和最终代码量证据，
不得用 M09 的 QEMU cycles 代替。

---

## 12. M11：裸机证据驱动的 reader 收敛优化

### 12.1 定位、基线与适用优先级

M11 是 M10 reader 实验之后的独立优化阶段，不重新设计 timekeeper owner、
shared publisher 或 MM_data 映射。目标是在保持现有功能、复用关系和可读性的
前提下，减少用户成功路径稳定执行的指令、分支、参数搬运和 call/ret。

冻结优化基线：

- commit：`238c7771eb80fa5807e629ec046df03f2eb0cb74`；
- result root：
  `test/test_gettime/vkso-tests/baremetal/results/20260730T053229Z-vkso-final`；
- case：normal Raw、normal VKSO、no-retpoline Raw、no-retpoline VKSO；
- 每个 case 包含 20 个 API、2 条路径、31 次重复，共 1240 条性能记录；
- 每个 case 的功能矩阵均为 44 pass / 0 fail；
- normal 是生产结论，no-retpoline 只用于分离 thunk/retpoline 影响。

基线证据：

| 路径 | Raw cycles | VKSO cycles | VKSO 额外指令 | VKSO 额外分支 |
|---|---:|---:|---:|---:|
| realtime | 56.263 | 57.199 | 24 | 6 |
| monotonic | 56.196 | 58.204 | 33 | 9 |
| monotonic raw | 58.303 | 59.212 | 30 | 7 |
| boottime | 56.258 | 59.208 | 38 | 11 |
| TAI | 56.199 | 58.204 | 30 | 9 |
| realtime coarse | 17.061 | 21.166 | 19 | 5 |
| monotonic coarse | 17.060 | 23.108 | 27 | 6 |
| gettimeofday(tv) | 64.222 | 67.484 | 25 | 5 |

解释边界：

- PMU 显示 cache miss 和 branch miss 接近零，当前重点不是 cache-line 重排或
  分支预测失败，而是成功路径无条件执行了更多工作；
- 关闭 retpoline/return thunk 后，高精度 `clock_gettime` 的 Raw/VKSO 绝对
  cycles 和差距基本不变，因此 thunk 不是本轮 reader 优化目标；
- VKSO hres/raw retry 分别约为 31/46 次每百万读取，Raw 约为 144/97 次，
  retry 优势真实存在但摊销远小于 0.01 cycle，不能抵消每次固定的 1～6 cycles；
- coarse/NULL 路径的百分比退化较大，但绝对差距仍为 4～6 cycles，评价时必须
  同时报告绝对 cycles 和百分比。

本阶段按下列顺序串行推进：

1. O1：单遍 clock-ID 分派；
2. O2：namespace/offset 路径收紧；
3. O3：x86 成功 provider 的 cycle-delta 专门化；
4. O4：冷 backend shim 与 tail-entry 原型；
5. O5：`gettimeofday`/NULL 等剩余短路径定向收敛；
6. O6：仅在前述优化仍不足时评估 root-MM 或 shared layout 备选；
7. O7：最终全量功能、read、update、并发和代码规模验证。

O1～O3 是首选低风险优化；O4 必须独立原型和独立决策；O5/O6 是有证据才进入
的条件项，不因计划列出就默认实施。

### 12.2 通用执行与保留规则

每个优化项必须：

1. 从上一项“已保留”的 commit 开始；
2. 先记录待删除的动态指令/分支和预期受益 API；
3. 一个假设对应一个 commit，不把两个候选混在同一镜像；
4. 构建 normal 配置并检查关键符号、`.text` 大小和汇编；
5. 运行完整 QEMU 语义矩阵、namespace、fallback 和 provider 定向测试；
6. QEMU 通过后才安装裸机镜像；
7. 开发期先测 normal VKSO，并与本节冻结的同协议基线比较；
8. 保留候选后再进入下一项；失败候选留在可定位 commit/分支，不继续叠补丁。

性能保留标准：

- 目标 API 的动态指令/分支必须按假设减少；若编译器生成相反结果，先停止；
- cycles 改善必须大于本轮重复分布噪声；小于 1 cycle 的结论至少在两个独立
  boot 中方向一致；
- 任一常用非目标 API 不得出现稳定大于 `max(0.5 cycle, 1%)` 的退化；
- O1～O3 原则上同时减少或不增加机器码；如机器码增加，必须有稳定性能收益和
  明确可读性理由；
- 代码量下降而 cycles 中性可以保留，但不得增加分支、破坏可读性或功能边界；
- 功能、ABI、namespace、PV/HV、fallback 或 update/concurrent 任一退化时
  直接回退，不以其他接口的收益抵消正确性。

统计规则：

- 开发期可复用冻结的 Raw 数据定位方向，但不得把跨版本拼接结果作为论文最终
  对照；
- O7 必须重新成对采集 Raw/VKSO；
- 每项同时记录源码净增删、核心符号大小、retired instructions、branches、
  branch misses、cycles 和 retry；
- 百分比必须和 cycles 绝对值同时报告。

### 12.3 O1：单遍 clock-ID 分派（优先级 1）

问题：

当前 `vkso_clock_gettime_common()` 先执行：

1. clock ID 上界检查；
2. `1U << clock_id`；
3. HRES/COARSE 位图分类；
4. 第二组 clock-ID 比较以选择 base、multiplier 和 offset。

Raw 使用位图分类后可通过稀疏 `basetime[clock]` 直接索引，而 VKSO named
layout 又进行第二次分类，形成重复工作。

实现方向：

- 删除 HRES/COARSE 双 mask 和后续 named-field ID 链；
- 使用每个 clock 一个 8-bit descriptor，一次确定：
  - shared payload 的 `u64` 索引；
  - hres/coarse 类型；
  - mono/raw multiplier；
  - 是否需要 namespace offset；
- descriptor 以两个编译期打包立即数保存，不增加普通 `.rodata`、shared ABI 或
  DSO 映射页；零 descriptor 统一表示 CPU、alarm、dynamic 和无效 ID；
- descriptor 提取只执行一次变量移位；仅 namespace-capable clock 在读取完成后
  使用 clock ID 检查 MM_data mask；
- 不启用 jump table，不在 wrapper 复制 clock 分类；
- 所有 clock 仍进入同一份 hres/coarse 计算主体，不恢复七份 typed 核心。

静态退出条件：

- 成功路径汇编中不再出现 HRES/COARSE 类别 mask 和第二组 clock-ID 比较；
- realtime、monotonic、coarse 的比较/分支数下降；
- `vkso_clock_gettime_common` 及关联 wrapper 总机器码不增加；
- invalid/negative/CPU/alarm clock 的 fallback 只执行一次。

验证重点：

- 七种 global clock；
- 负 clock ID、`CLOCK_TAI + 1`、CPU、alarm 和 dynamic clock；
- 输出指针错误与 syscall errno；
- normal PMU instructions/branches/cycles；
- coarse 路径必须单独报告绝对 cycles。

实施记录（2026-07-30）：

- 显式浅层树和 C `switch` 候选分别将 common core 从实际 586 B 增至约
  660 B 和 686 B，均在进入 QEMU 前回退；
- 普通 `.rodata` descriptor 表可将 text 降至约 512 B，但当前 KRG 闭包不会
  自动携带该只读对象；为避免扩大加载器机制和新增映射页，该候选回退；
- 最终采用两个指令立即数承载 12 个 8-bit descriptor：
  - 源码为 48 行新增、48 行删除，净变化 0 SLOC；
  - common core 实际尺寸 586 B → 537 B（−49 B）；
  - `libkernel.so` 对齐符号尺寸 592 B → 544 B（−48 B）；
  - `__vkso_clock_gettime` wrapper 保持 63 B；
  - 未增加 `.rodata`、shared-data 或其他 DSO 映射页；
- validation package：
  `vkso-tests/baremetal/artifacts/o1-packed-validation`；
- QEMU 结果：
  `vkso-tests/baremetal/artifacts/validation/normal-20260730T104146Z`；
  Raw/VKSO 各 112 行矩阵、正常 RTC 与无 RTC 四种启动全部通过。
- normal 裸机结果：
  `vkso-tests/baremetal/results/20260730T110954Z-vkso-final`；
  同批次 Raw 镜像、配置和测试程序与冻结基线一致，Raw 用户路径20项中位变化
  `+0.001%`，足以排除主要环境漂移；
- packed descriptor 相对修改前 VKSO：
  - realtime、monotonic、TAI 各退化约 `1.00 cycle`；
  - realtime 动态指令 `+6`、分支 `+1`，monotonic 指令 `+2`，
    TAI 指令 `+5`；
  - monotonic-raw、boottime 基本不变；两个 coarse 一快一慢；
  - syscall 路径只有不足 `0.6%` 的混合小变化，不能抵消用户热路径退化；
- 最终决策：O1 未满足动态指令下降、常用接口不退化和可读性要求。候选保留在
  `54c99ee` 供复算，运行时代码由 `e3290c8` 精确恢复到修改前基线；normal-only
  实验脚本和证据保留。O1 不进入最终实现。

### 12.4 O2：namespace/offset 路径收紧（优先级 2）

问题：

当前 common reader 先形成通用 `offset` 指针，读取结束后再统一执行
`offset != NULL`、MM_data mask 和 offset 应用判断。realtime、TAI 和
realtime-coarse 本不需要 namespace offset，也支付了通用收尾控制流；
monotonic/raw/boottime 则存在 MM_data 指针与 mask 的分散判断。

实现方向：

- realtime、TAI、realtime-coarse 成功后直接完成，不经过通用 offset 收尾；
- monotonic、raw、boottime、monotonic-coarse 才进入一个可读的
  namespace-offset helper；
- helper 将 MM_data 有效性、clock mask 和具体 offset 的选择组织在一处；
- root namespace 保持当前 NULL/零 mask 语义；
- 不在一次性 init 中缓存“永远是 root”的假设，不削弱 fork/exec/setns；
- 不把 MM_data 内容复制到 shared_data，不引入第二个 seq。

静态退出条件：

- 不支持 namespace offset 的 clock 不再读取 MM_data mask；
- namespace-capable clock 的 MM_data/mask 判断只出现一处；
- 不增加 user/kernel 两份 offset 算法；
- root kernel reader 与 user namespace reader 的调用契约仍明确。

验证重点：

- root 与非 root namespace；
- monotonic/raw/boottime/coarse offset；
- fork、exec、setns、多线程；
- realtime/TAI 不受 offset 影响；
- PMU 重点检查 realtime、monotonic、boottime 和两个 coarse clock。

### 12.5 O3：x86 cycle-delta 专门化（优先级 3）

问题：

当前成功路径读取 `mask`，先判断 `mask == U64_MAX`，再执行
`cycles > cycle_last` 和 delta。Raw x86 对用户可读的 TSC/PVClock/Hyper-V
成功路径使用 full-width counter，不支付有限 mask 的通用检查。

实施前审计：

- 列出 TSC、PVClock、Hyper-V 所有可成功返回的 mode；
- 证明它们发布到 shared state 的 mask 恒为 `U64_MAX`；
- 证明任何 finite-mask 或不支持 mode 在使用 delta 前进入 fallback；
- 检查普通 kernel reader 是否可能用同一入口消费 finite-mask clocksource。

仅在上述不变量成立时实施：

- x86 成功 provider 使用 full-width delta：
  `cycles > cycle_last ? cycles - cycle_last : 0`；
- shared ABI 中可暂时保留 mask 作为诊断/兼容字段，但成功热路径不读取它；
- finite-mask 语义不得被静默错误计算；不能证明时放弃 O3，而不是增加猜测分支；
- 不改变 PV/HV 功能与 fallback 条件。

静态退出条件：

- TSC/PV/HV 成功路径减少一次 mask load、比较和分支；
- 不支持 mode 仍在写输出前失败；
- kernel 普通 reader 没有被错误限制为 TSC；
- 代码量不因保留两个热 delta 主体而增加。

验证重点：

- TSC 裸机正常路径；
- PVClock/Hyper-V 静态构建和 QEMU 可达路径；
- 人工 backward-cycle 保护；
- unsupported mode fallback；
- 原 finite-mask 单元测试改为验证“有限 mask 不进入该成功入口”，不能简单删除。

### 12.6 O4：冷 backend shim 与 tail-entry（优先级 4，独立原型）

问题：

当前用户 wrapper 为了在 core 返回失败后执行 syscall，会无条件：

- 保存原始参数并调整栈；
- 加载 MM/environment context；
- `call` shared core；
- 检查状态；
- 恢复栈并 `ret`，失败时再进入 syscall。

这使所有成功调用为极少发生的 fallback 支付 wrapper 往返成本。

候选设计：

- environment context 增加内部 cold backend/fallback 入口；
- user context 的入口执行相应 syscall trampoline；
- kernel context 的入口进入既有 kernel backend；
- public wrapper 加载 context 后 tail-jump 到 shared entry；
- shared core 成功时直接返回原调用者；
- 只有 `BACKEND_REQUIRED/UNSUPPORTED_MODE` 才调用 cold backend；
- core 不直接写 syscall 号、不访问 `k_clock`，仍通过明确 shim 隔离环境语义。

该候选允许改变内部 context ABI，但不得改变 `__vkso_*`、syscall 或
`ktime_get_*` 外部 ABI。

必须检查：

- compiler 是否因冷 callback 让原始参数长期存活并产生 spill；
- 成功路径是否真正删除 stack save、status test 和额外 call/ret；
- indirect callback/retpoline 只存在于 cold 路径；
- 用户可控 context 在用户态调用时不形成内核权限问题；
- kernel context 使用静态可信入口；
- fallback 输出、NULL、errno 和执行次数与 Raw 一致。

保留条件：

- clock_gettime/gettimeofday 成功路径动态指令和 call/ret 明确减少；
- fallback 前置成本下降，且 syscall backend 本身不重复执行；
- shared core 与 wrapper 总源码/机器码不增加，或增加量有稳定 cycles 收益；
- 若出现 hot-path spill、间接调用进入热路径或收益不能复现，回退整个 O4。

### 12.7 O5：剩余短路径定向收敛（优先级 5，条件项）

只有 O1～O4 保留后，以下接口仍稳定落后 Raw 才进入：

- `gettimeofday(tv)`；
- `gettimeofday(timezone)`；
- `gettimeofday(NULL, NULL)`；
- coarse clock；
- CPU/alarm fallback 前置路径。

处理规则：

- 先用 PMU 和汇编区分 wrapper、core、syscall backend 和镜像布局成本；
- 优先复用 O4 的 tail-entry/cold fallback，不单独复制 global 公式；
- NULL/timezone 路径可使用清晰的早返回，但不得生成多份 hres 主体；
- CPU/alarm 的总差距必须先减去各自镜像的直接 syscall 成本，不能把 kernel
  backend 差异全部归因于 user wrapper；
- 任何 specialized leaf 必须同时给出机器码增量和稳定 cycles 收益。

不允许：

- 为少量冷调用在 wrapper 再复制完整 clock-ID 分类；
- 只因百分比大就接受大量机器码；短路径必须看绝对 cycles；
- 用 branch miss/cache miss 优化解释当前接近零的事件。

### 12.8 O6：root-MM 与 shared layout 备选（优先级 6，默认不实施）

以下方案风险高于当前证据，只保留为后备：

1. 在加载期选择 root/non-root 专门入口；
2. 将 MM_data 绑定为无需每次 NULL 检查的稳定 context；
3. 将 named base 改成 Raw 式 `basetime[clock_id]` 稀疏数组；
4. 升级 shared ABI 以换取直接索引。

进入条件：

- O1～O5 后仍有稳定且可归因于 MM/context 或二次寻址的显著差距；
- fork/exec/setns 与 MM 生命周期已经证明允许一次性绑定；
- shared payload、cache-line、publisher bytes 和 update 性能已完成模型；
- 预期收益不能由更小的局部优化获得。

任何 O6 候选必须单独分支；涉及 shared layout 时视为新内部 ABI 决策，不能
夹入普通 reader 优化提交。

### 12.9 明确排除的伪优化

本阶段不执行：

- 关闭 retpoline/return thunk 作为 VKSO reader 优化；
- 删除 seq、减少一致性检查或故意增加 retry；
- 删除 time namespace、PVClock、Hyper-V 或 fallback 语义；
- 恢复七份 typed hres/coarse 主体；
- 在 wrapper 与 core 重复 clock-ID 判断；
- 因当前数据任意调整 cache-line；cache miss 并非已观测瓶颈；
- 为追求 Raw 汇编逐字一致而破坏共享 core 的可读性和复用；
- 在一个提交中同时修改 reader、publisher 和实验脚本。

### 12.10 O7：最终验证与证据封存

保留的优化全部完成后执行：

1. 默认、TIME_NS、PVClock、Hyper-V 静态构建；
2. 完整 QEMU Raw/VKSO 语义矩阵和 namespace/provider/fallback 定向测试；
3. normal Raw 与 normal VKSO 成对 reader 实验；
4. no-retpoline Raw/VKSO 敏感性实验；
5. update-side 实验；
6. read/update 并发实验；
7. 源码语义分类与机器码复算。

最终报告必须同时对照：

- M11 冻结基线；
- M11 最终 VKSO；
- 同批次最终 Raw。

逐接口报告 cycles、百分比、instructions、branches、retry 和 fallback；列出
每个 O1～O6 候选的保留/回退状态、commit、代码规模变化和理由。最终结论不能
只说“总体平均提高”，必须解释仍慢于 Raw 的接口及其不可消除的架构边界。

### 12.11 M11 状态表

| 项目 | 优先级 | 当前状态 | 进入下一项条件 |
|---|---:|---|---|
| 冻结四组 reader/PMU/seq 基线 | 0 | 已完成 | 结果可复算 |
| O1 单遍 clock-ID 分派 | 1 | 裸机验证后回退；`e3290c8` | 失败证据已封存 |
| O2 namespace/offset 收紧 | 2 | 保留为静态原型，不直接实施 | 非namespace路径确实减少动态工作且不复制core |
| O3 x86 cycle-delta 专门化 | 3 | 推荐下一项；full-mask源码审计已通过 | 汇编确认减少load/compare/branch |
| O4 cold backend shim/tail-entry | 4 | 保留为高风险独立原型 | 无hot spill/间接调用且成功路径call/ret下降 |
| O5 剩余短路径收敛 | 5 | 条件项；仅处理O2～O4后的残余热点 | 仍有可归因固定成本 |
| O6 root-MM/shared-layout 备选 | 6 | 暂不实施 | 局部优化不足且setns/MM语义可证明 |
| O7 最终全量验证 | 7 | 待执行 | 所有保留候选冻结 |

O1 裸机结果后的执行顺序调整：

1. 先实施 O3。TSC、KVM/Xen PVClock 和 Hyper-V 可成功导出的clocksource均声明
   `CLOCKSOURCE_MASK(64)`；NONE/缺页/不稳定provider在delta前失败。该候选可直接
   删除所有hres读取共有的mask load、比较和分支，且不需要改变dispatcher、
   wrapper、shared ABI或publisher。
2. O2 只先生成候选汇编。当前显式named-field dispatcher可读且分支高度可预测；
   若为了提前返回而复制内联hres主体、增加机器码或让namespace路径退化，则不进入
   裸机测试。
3. O4 独立于 O2/O3。它可能消除user wrapper为冷fallback支付的参数保存和额外
   call/ret，但也可能因backend callback造成spill或间接调用；必须先比较wrapper、
   core和组合成功路径汇编。
4. O5 不再覆盖已经与Raw基本一致的time、getcpu和getres，只根据新结果考虑
   gettimeofday、coarse及CPU/alarm fallback前置成本。
5. O6 保持关闭。root namespace mask可在setns后原地变化，不能缓存为永久root；
   shared layout升级和固定MM地址也不应为数个cycles扩大ABI及加载器机制。
