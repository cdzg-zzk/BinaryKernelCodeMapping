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

- 开发分支固定为 `vkso-timekeeper-unification`，起点为 `d89f2e5`。
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
4. producer 直接维护 canonical state，消除
   `vkso_time_compat_prepare()` 式跨数据模型逐字段转换。
5. private 复杂更新与 shared 短发布分离，缩短 shared seq 为奇数的窗口。
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

canonical state 是 kernel-private 的当前完整状态。用户可见 shared 页保存
同类型的已发布快照；二者可以是两个物理实例，但必须使用相同字段语义，
只能存在“发布”，不能存在“模型转换”。

#### C. shared_data

- 只包含 seq、ABI header、已发布的 `tk_read_state` 和极少事件型全局数据；
- 使用项目机制建立 R--/NX 用户映射；
- 物理上与 timekeeper private 数据隔离，避免相邻 private 数据泄漏；
- 不含内核指针、锁、函数地址、per-MM namespace 数据或可写用户状态；
- kernel 普通 reader 和用户 reader 读取同一发布语义。

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

producer 的顺序固定为：

1. 在既有 writer 锁/seq 保护下更新 private 状态；
2. 完成 NTP、leap、offset、coarse、cycle base 和 derived base 的复杂计算；
3. 直接得到完整 canonical `tk_read_state`；
4. 进入 shared 短发布；
5. 将 shared seq 置为奇数并执行所需的写侧排序；
6. 用显式、可审计的 `WRITE_ONCE` 字段发布本次变化的 canonical payload；
7. 执行与 reader 协议配对的 memory barrier；
8. 将 shared seq 置为偶数。

约束：

- shared seq 为奇数期间禁止 NTP、除法、clocksource 切换判断等复杂计算；
- 初版不复制整页，不无条件重写 timezone 等事件型字段；
- 先保证协议正确，再依据汇编统计发布字段、字节数和 seq 奇数窗口；
- `time()` 的 seconds 不得发生撕裂；
- writer-locked helper 不得读取自己正在更新的 shared seq；
- memory ordering 必须同时说明 kernel reader 和用户 reader 的配对关系。

只有 M09 功能稳定后，固定尺寸复制才可作为独立性能候选提交；必须证明不会
扩大 seq 窗口、不会破坏原子字段，并在 M10 与 scalar publisher 直接比较。
失败候选不得与正确性重构混合保留。

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
    -> typed global reader 或 generic cold dispatcher
        -> shared seq/arithmetic primitive + environment provider
            -> backend/fallback（仅失败或非 global clock）
```

热路径约束：

- 已知 global clock 使用 typed 入口，不经过 generic clockid 大 switch；
- user 成功路径不进入 syscall fallback，也不先调用 backend；
- kernel 普通 `ktime_get_*` 以 root namespace typed 薄 wrapper 进入共享算法，
  不支付 MM_data NULL 检查和 generic dispatcher 成本；
- public wrapper 之后不得出现多层只转发参数的包装；是否 inline/tail-call 由
  汇编检查决定，目标是成功热路径最多保留一个必要的非内联算法调用；
- 不为追求“单一入口”引入新的函数指针、重复 mode 判断或 call/ret；
- shared core 返回内部 `OK`、`UNSUPPORTED_MODE`、`BACKEND_REQUIRED` 等有限
  状态，但 typed 成功路径应能被编译器收敛成最少分支。

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

它们可读取 private canonical state 或保留专用快照，但必须在矩阵中说明：
调用上下文、同步方式、数据来源、为何不能共用普通 reader，以及何时与
canonical state 对齐。不得用“兼容性”作为未审计重复算法的理由。

---

## 4. 预期代码组织

最终文件边界以 M01 审计结果为准，但职责必须清晰：

- **internal ABI**：v11 固定宽度结构、状态码、offset/size 断言；
- **producer/private**：NTP、settime、leap、suspend、clocksource switch；
- **publisher**：唯一 shared 写入口和 memory-order 协议；
- **shared primitives**：seq、delta、mult/shift、normalize；
- **typed global readers**：realtime/monotonic/raw/coarse/boottime/TAI；
- **providers**：kernel clocksource、user TSC/PV/HV；
- **kernel adapters**：现有 `ktime_get_*` 薄 wrapper；
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
| canonical/private 双 source-of-truth | 字段唯一所有权；按字段组迁移后立即删除旧 owner |
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
- complex update 位于 shared seq 奇数区间之外；
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
| M06 普通 kernel reader 统一 | 进行中 | shared core 功能完整 |
| M07 dispatcher/backend 重构 | 待开始 | 普通 reader 稳定 |
| M08 清理与静态审计 | 待开始 | 完整分派通过 |
| M09 完整正确性验证 | 待开始 | 无临时/双重路径 |
| M10 裸机性能与最终证据 | 待开始 | M09 pre-performance tag |

M00～M05 已通过；下一步执行 M06，只将普通上下文安全的 `ktime_get_*`
迁入 root-namespace typed shared-core 路径，继续隔离 fast/NMI、
writer-locked、early-boot 与 cross-timestamp reader。
