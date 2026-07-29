# M10 源码规模与“为何增长”审计

## 1. 结论

本次统计先由人工按语义划分文件和行区间，再由脚本做去空行、去纯注释后的
算术。脚本不决定代码归属。比较范围固定为同一组 x86-64 功能：

- `clock_gettime`、`clock_getres`、`gettimeofday`、`time`、`getcpu`；
- 七种 global clock；
- CPU/alarm/dynamic/invalid fallback；
- time namespace；
- TSC、PVClock、Hyper-V 源码能力。

当前结果不是“VKSO 增加很多”。真正的同范围结果是：

| 互斥口径 | Raw SLOC | VKSO SLOC | VKSO - Raw |
|---|---:|---:|---:|
| 运行时功能 | 857 | 947 | +90 |
| 运行时机制 | 490 | 353 | -137 |
| **运行时小计** | **1,347** | **1,300** | **-47（-3.49%）** |
| 功能专属构建/链接 | 158 | 58 | -100 |
| **产品功能合计** | **1,505** | **1,358** | **-147（-9.77%）** |

因此，VKSO 的运行时源码已经少于 Raw；把各自实际需要的功能专属构建/链接代码
纳入后，VKSO 总体少147 SLOC。项目已有的通用 `make_dll`、manager 和页面替换
基础设施不计入 kernel/user 产品合计，但必须作为项目机制另行披露。

另外单列：

| 非产品主表 | Raw | VKSO | 处理 |
|---|---:|---:|---|
| 最终配置不执行的兼容桩 | 14 | 9 | 不计产品；VKSO 只剩 TIME_NS 通用桩 |
| ABI/assert/probe/内核自测 | — | 340 | 不计产品 |

专用 VKSO kernel 不再支持 `CONFIG_VKSO_TIME=n`。原来的 148 SLOC VKSO 关闭
模式、旧 global callback 和空桩已经删除；Raw/no-vDSO 由独立源码树承担。

相对本分支起点 `d89f2e5` 的 Git 物理行 churn 也解释了“看起来增加很多”的
现象：当前范围为新增805、删除761；其中测试文件
`vkso_time_test.c`单独新增 173、删除 4 行。排除该 T1 测试后，产品源码实际是
新增632、删除757，**净减少125个物理行**。Git churn 反映重写过程，不替代下文
Raw/VKSO 最终 SLOC 对照。

当前候选还包含三项彼此独立的改进：

- `16e7e55`把`ns >= 1 second`的极冷归一化外提，不增加常用TSC路径动态
  指令，并使目标reader机器码减少160 B；
- `64a08e4`让producer直接维护项目映射的shared物理页，删除160-byte私有
  staging对象和`vkso_time_publish()`第二次字段搬运。
- `6312c9b`删除用户入口从不调用、只为kernel/benchmark存在的通用
  `clock-id` core；kernel与user分别只在各自public边界保留一次分派。

前两项已有上一轮裸机证据；第三项仍须由本轮裸机read、update和并发结果决定。

## 2. 为什么功能代码仍比 Raw 多

逐类结果：

| 类别 | Raw | VKSO | 差异 |
|---|---:|---:|---:|
| U1 用户 public ABI/算法或 wrapper | 359 | 149 | -210 |
| S1 kernel/user 共享 global 算法 | — | 265 | +265 |
| K1 普通 kernel global reader | 194 | 217 | +23 |
| K2 canonical producer | 56 | 47 | -9 |
| K4 syscall/dispatcher | 132 | 191 | +59 |
| E1 cycles/environment provider | 116 | 78 | -38 |
| **运行时功能** | **857** | **947** | **+90** |

功能层仍多90行，并不是多了一份 mult/shift/base 换算公式，而是边界代码：

1. Raw 把用户算法、clock 分派、fallback 和 ABI 入口写在一个 vDSO 实现中。
   VKSO 为了让同一 core 同时被 kernel/user 调用，显式保留了 U1 wrapper、
   S1 typed core 和 K1 kernel ABI adapter。
2. 用户 wrapper 为裸机热路径直接跳到 typed reader，没有调用统一大
   dispatcher。它减少运行时比较和间接层，但源码比“一个通用 wrapper”更展开。
3. 任意 Linux clocksource 都必须保持 kernel reader 正确。用户不能接收
   `clocksource *`，因此 VKSO 为非 TSC/PV/HV mode 保留一个 33 SLOC 左右的
   kernel-only cold private helper。
4. 普通 `ktime_get_*` 外部 ABI 不允许删除。它们已经是 shared core 的薄入口，
   但函数名、返回类型、WARN 和 export symbol 仍必须存在。
5. kernel 与 user 的 fallback 目标不同：kernel进入 `k_clock`/private
   timekeeper，user执行syscall。clock-id策略只能在两个public边界各保留一次，
   不能把访问`current`和执行syscall的代码放进可共享core。

本轮审计删除了一个不满足上述原则的边界：旧
`vkso_clock_gettime_core()`/`vkso_clock_getres_core()`既不被用户public
wrapper调用，又被作为动态ABI导出，只服务kernel和benchmark。删除后：

- S1从337降至265 SLOC；
- kernel唯一分派回到syscall边界，K4从135增至191 SLOC；
- K1头文件删除无用generic adapter，从231降至217 SLOC；
- 功能代码净减少30 SLOC，且用户typed热路径源码和机器码均不变。

另有68 SLOC的用户context启动代码不再混入U1功能算法，而在机制表C2中单列。
其中包括libkernel内的bind/data槽，以及当前测试客户端读取
`AT_VKSO_MM_DATA`并执行一次绑定的真实代码；它不是测试断言，也不能隐去。

审计同时纠正了“所有普通kernel reader都必须强行进入shared core”的过度统一：
`ktime_get_coarse_with_offset()`提供的是kernel-only的REAL/BOOT/TAI offset
reader，并不存在对应用户clock ID。旧实现为它新增两个shared入口和一套base
差值算法，既没有复用对象，也增加调用和读取。当前已恢复为Raw等价的private
offset读取；这不是算法复制，而是让单侧功能留在单侧。

这说明“共享 core”消除了算法维护的第二份源定义，但不会让 ABI wrapper、
environment binding 和 kernel export symbol 自动消失。

## 3. Producer/publisher 已合并为直接shared维护

把生产和发布作为一个完整职责比较：

| 生产/发布职责 | Raw | VKSO |
|---|---:|---:|
| K2 canonical producer | 56 | 47 |
| K3 payload ABI + publisher | 119 | 78 |
| **合计** | **175** | **125** |

VKSO 在同一职责上少50 SLOC。这里同时修正了旧统计的不对称：Raw
`update_vsyscall()`中的base/cycle派生现在也归K2，seq/VVAR/架构同步归K3；
VKSO采用完全相同的功能/机制划分。

当前 VKSO 的数据所有权是：

- `struct timekeeper`继续保存 NTP、clocksource、suspend、fast/NMI 等
  kernel-private 状态；
- 物理独立的shared页本身就是唯一160-byte canonical global-reader state；
- kernel通过可写alias直接维护，用户只看到同一物理页的R--/NX映射；
- 不再存在private canonical snapshot、real/shadow canonical副本或第二次
  payload搬运；
- `offs_boot`仍是权威值，只有一份16-byte split cache在罕见suspend事件更新，
  避免周期路径64-bit除法；该cache不进入real/shadow复制。

这次审计发现并修复了 M03 遗留的真实冗余：此前 real/shadow timekeeper 各自
携带 160-byte `vkso_read_state`，并随 mirror memcpy。随后直接shared候选又
删除了过渡期的全局160-byte staging和real/shadow中的
`monotonic_to_boot`副本。相对`16e7e55`：

- `timekeeping.o` BSS从928降到784 bytes（-144 B）；
- `timekeeping.o + vkso_time.o`主`.text`从10,975降到10,735 bytes
  （-240 B）；
- `timekeeping_update + vkso_time_publish`从两个函数、合计882 B，变为单一
  650 B的`timekeeping_update`（-232 B）；
- user reader及shared core对象逐字节不变。

直接维护使seq奇数窗口包含canonical派生，因而比短scalar publisher更长；
这是删除staging/copy后的唯一实质代价。Raw VVAR同样在seq奇数期间派生并写入
状态。最终必须用裸机read/update并发实验比较retry，而不能只凭对象大小接受。

## 4. 机制代码为什么显著减少

| 机制类别 | Raw | VKSO | 差异 |
|---|---:|---:|---:|
| C1 MM/context/namespace 映射 | 371 | 207 | -164 |
| C2 用户context启动 | 0 | 68 | +68 |
| K3 shared ABI/publisher | 119 | 78 | -41 |
| **运行时机制** | **490** | **353** | **-137** |
| G1 功能构建/链接 | 158 | 58 | -100 |

这正是项目机制复用产生的收益：VKSO kernel 只实现 time 专属 shared/MM
语义和链接边界，通用 ELF 导出、DSO 形成、页面替换与回收由项目基础设施
承担。论文中应把这 237 SLOC 的机制/build减少作为机制复用结果，同时另表
披露项目基础设施，不能假装它不存在。

C2是当前实现尚未由通用加载器吸收的每个VKSO用户侧适配。若未来加载器能够
从auxv自动把per-MM地址写入private wrapper data，则这68 SLOC可移入一次性P1
项目机制，五个时间ABI不必各自携带；在该能力真正实现前，本报告仍把它计入
VKSO产品。

项目 P1 不加入上面的 kernel/user 合计。已有人工审计可单独披露为：

| P1 项目机制 | 统计性质 | 规模 |
|---|---|---:|
| shared_data R--/NX 支持 | Git 物理行 churn | +255 / -13 |
| private wrapper ET_REL/relocation/export 适配 | 人工语义 SLOC | 210 |
| private wrapper自动依赖闭包 | 本轮Git物理行churn | +42 / -7，另有通用单测 |
| 既有 `make_dll`、manager、page replacement、KRG | 复用基础设施 | 不归因给本次 time 功能 |

前两项是把项目能力扩展成可复用机制的投入，不是每增加一个 VKSO 接口都要重写
的 user/kernel 算法；因此论文应列为“一次性项目机制扩展”，不能混进 time
产品 SLOC，也不能隐去。

## 5. 本轮只保留的安全精简

- 删除 real/shadow timekeeper 中重复的 canonical payload；
- `coarse`、clocksource resolution 和 seconds 直接读取 canonical shared
  字段，删除永远不可能触发的 provider-failure 分支；
- 用原 `reserved` 位置发布 `clocksource_resolution`，保持 ABI v11 大小和
  offset 不变，同时恢复 `ktime_get_resolution_ns()`的 Raw 语义；
- 用一个可读汇编宏生成四个相同 hres veneer，生成的 wrapper 机器码逐字节
  不变；
- 删除专用 VKSO kernel 中无需求的 `CONFIG_VKSO_TIME=n` 兼容实现。
- 删除没有用户ABI对应项的boottime/TAI coarse shared入口，让
  `ktime_get_coarse_with_offset()`直接使用唯一private offset；
- `time()`共享seconds读取不会失败，删除永远返回OK的状态wrapper和不可达
  kernel fallback。
- 删除benchmark-only generic clock core及`BACKEND_REQUIRED`伪状态；
- `make_dll`从private wrapper relocation自动求内部dependency roots，功能
  清单不再把typed reader伪装成public导出；
- 删除`--include-core`、`core_supported`和`vkso_core_st_value`等旧实验接口，
  benchmark只测真实public ABI。

没有把 public wrapper 改成统一 generic-core call。该generic core实际上会
形成第三份clock-id分派，并增加用户热路径的参数准备、比较和call/ret；本轮
选择直接删除，而不是为了压低局部SLOC保留一个错误抽象。

## 6. 当前机器码结果

源码复用不等于编译器只生成一份机器码。当前 VKSO 为七种常用 global clock
保留 typed hres 入口，以减少用户热路径的 clock-id 比较和通用分派；这些入口
共享同一组源级原语，但会被编译成多份专门化函数体。

本轮重新构建Raw目标对象后，纠正了旧表遗漏的两个依赖：

- Raw public vDSO五个入口之外还有独立的142 B
  `__arch_get_hw_counter.constprop.0`；
- VKSO普通kernel reader在不支持的clocksource上需要227 B
  `vkso_timekeeping_get_private()`，不能因其为cold而隐去。

按不重叠的真实symbol body统计：

| 同功能reader机器码 | Raw | VKSO |
|---|---:|---:|
| user public入口/私有wrapper | 1,515 B | 414 B |
| user reader依赖 / kernel-user shared core | 142 B | 1,807 B |
| 普通kernel reader入口 | 982 B | 381 B |
| kernel cold private reader | 0 B | 227 B |
| **reader合计** | **2,639 B** | **2,829 B** |
| **VKSO - Raw** | — | **+190 B（+7.20%）** |

该190 B是静态代码体积，不等于动态多执行190 B。常用TSC路径只执行一个typed
reader；PV/HV cold provider、其他clocksource private reader和其余clock函数
不会同时执行。C2一次性context启动另有168 B text和24 B private data，单列为
机制，不加入reader合计。

对象级候选实验已经排除了“把所有 hres 换算合成一个大 helper”：

- 全部合并可使 `vkso_time_core.o` `.text` 从 2,744 B 降至 1,624 B；
- 仅合并 mono-mult clocks 可降至 1,816 B；
- 但两者分别在每次常用读取中增加约 10 条和 6 条动态指令，来源是参数准备、
  额外 callee-saved register 和 tail jump。

当前保留的reader候选仍只有极冷归一化外提：常用`ns < 1 second`路径动态
指令不增加，`gettimeofday`函数体逐指令保持不变，目标reader机器码净减160 B。
direct-shared候选不修改任何reader机器码，只改变update-side。

随后删除kernel-only coarse伪共享边界，使`vkso_time_core.o`从2572降到
2344 B（-228 B），`timekeeping.o`从12968降到12904 B（-64 B）；按主表目标
symbol求和减少273 B。`time()`状态wrapper原先已被编译器内联消除，因此该项
只减少源码，不改变热机器码。

本轮删除generic dispatcher后，相对上一候选的同配置vmlinux：

- `vkso_clock_gettime_core` 267 B和`vkso_clock_getres_core` 42 B完全消失；
- kernel clock_gettime/getres public边界因吸收唯一分派增加257 B；
- 两条完整kernel syscall目标路径净减少52 B；
- `libkernel.so`从23,328 B降至23,072 B（-256 B），动态导出从10个降至7个；
- 三个被删除的导出均为内部core，五个时间public ABI保持不变；
- text/shared映射页数不变，用户typed reader及public wrapper机器码不变。

## 7. 构建与功能验证

- 全量 x86-64 kernel、模块、manager、libkernel.so 和实验包构建通过；
- `4d34fc1` 已验证基线包：
  `vkso-tests/baremetal/artifacts/unification-m10-source-compact`；
- `64a08e4`直接shared validation包：
  `vkso-tests/baremetal/artifacts/direct-shared-validation`；
- `9755724`最终候选normal/no-retpoline生产包：
  `artifacts/direct-shared-final-normal`和
  `artifacts/direct-shared-final-no-retpoline`；
- 两个最终包的commit、source hash、测试二进制和除thunk族外配置一致性校验
  通过；
- normal与no-retpoline的QEMU Raw/VKSO各112行ABI矩阵均通过；
- 两种构建下Raw/VKSO no-RTC fallback均通过；
- validation 配置的 early、cycle-delta、NMI、IRQ、writer-context 和普通
  kernel reader 自测全部通过；
- 最终QEMU结果目录：
  `artifacts/validation/normal-direct-shared-final-r2`和
  `artifacts/validation/no-retpoline-direct-shared-final`；
- `b059b67`边界精简后的TIME_NS=n和Hyper-V目标对象构建通过，normal/no-ret
  全量镜像构建通过。
- `2e8d782` dispatcher-compact production包：
  `artifacts/dispatch-compact-qemu-2e8d782-r2`；
- 当前分支的default、`TIME_NS=n`、Hyper-V和no-thunk目标构建通过；
- 当前QEMU Raw/VKSO各112行ABI矩阵通过，no-RTC fallback均通过，证据位于
  `artifacts/validation/dispatch-compact-qemu-2e8d782-r2`。

这只证明精简未改变功能，不替代 M10 裸机性能测量。

## 8. 可复算证据

- 人工语义范围：`M10_SOURCE_MANIFEST.tsv`
- 逐行统计结果：`M10_SOURCE_COUNTS.csv`
- 人工机器码symbol范围：`M10_BINARY_SYMBOLS.tsv`
- 算术工具：`vkso-tests/code-size/count_manifest.py`
- Raw：Linux 5.15.198 官方 tarball，SHA256
  `5d4c0994580dd3bbd5ffc5fcb81c22dd305b844c9d8c7b176cc41b28f7e29743`

分类范围通过同一 view/system/file 内的行区间重叠检查；每个有效产品行只进入
一个 U1/S1/K1/K2/K3/K4/C1/C2/E1/G1 类别。
