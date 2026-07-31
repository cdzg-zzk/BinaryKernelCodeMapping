# 设计决策记录

## D001：ABI v11 使用单一公共 cycle descriptor

- 状态：已决定
- 阶段：M01

证据：

- mono/raw 的 `clock` 仅在 `tk_setup_internals()` 写入同一指针；
- `mask` 仅在 setup 写入同一 `clock->mask`；
- `shift` 仅在 setup 写入同一 `clock->shift`；
- `cycle_last` 在 setup、forward、log accumulation、resume 全部成对更新为
  相同值。

决定：

```text
clock_mode + shift + cycle_last + mask + mono_mult + raw_mult
```

只发布一次公共 mode/shift/last/mask，mult 分开。删除 ABI v10 中 raw 的重复
mode/last/shift。M09 用 clocksource switch、NTP 和 suspend/resume 验证。

## D002：canonical state 嵌入 `struct timekeeper`（已被 D023 取代）

- 状态：历史决定；M10 直接 shared 实验后废止
- 阶段：M01

原因：

- periodic update 先修改 `shadow_timekeeper`，然后复制到 real timekeeper；
- settime/suspend/clock switch 直接修改 real timekeeper；
- 独立全局 canonical 对象会绕开 shadow/real 代际和锁顺序。

决定：

- `struct timekeeper` 包含 canonical `tk_read_state`；
- real/shadow 各有一个同类型实例；
- producer 在被修改的那个 timekeeper 内直接维护 canonical；
- shared 页保存同类型 published snapshot；
- real/shadow/shared 是同步协议需要的实例，不是三种数据模型。

## D003：ABI v11 恢复 `mask`

- 状态：已决定
- 阶段：M01

ABI v10 未发布 mask，只用 `cycles > cycle_last` 对 TSC 做 clamp，不能完整表达
非 64 位 clocksource 的 wrap 语义。v11 发布公共 mask，共享算法以
`clocksource_delta` 等价逻辑计算；架构特有的轻微 backward TSC 处理仍明确保留。

## D004：MM_data v3 不增加 seq

- 状态：已决定
- 阶段：M01

依据是 frozen time-namespace 生命周期、setns 单线程要求、fork稳定复制和
offset-before-mask 发布顺序。增加 seq 会让所有 namespace-aware hot reader
支付固定成本，却不保护当前设计中不存在的并发 writer。

## D005：fast/NMI、writer-locked 与 cross timestamp 保持专用

- 状态：已决定
- 阶段：M01

普通 shared seq reader 在 NMI 打断 writer 时可能自等待；hrtimer helper还具有
leap/event-seq 语义；cross timestamp需要 clocksource identity。它们保留专用
latch/private helper，不计作重复 global clock_gettime 实现。

## D006：`monotonic_to_boot` 在 M04 前删除

- 状态：已决定
- 阶段：M01

当前只有 compat adapter 读取该字段。canonical boottime base 由 producer直接
维护后，该 timespec 派生副本失去消费者，必须删除，不能以兼容为由保留。

## D007：resolution 与 timezone 是事件型字段

- 状态：已决定
- 阶段：M01

- timezone 只在 `do_sys_settimeofday64(tz)` 更新，独立发布；
- hrtimer resolution 从 LOW_RES 切换到 HIGH_RES，当前 Raw/VKSO 都可能在下一
  次 timekeeping publish 对用户可见；
- periodic publisher 不重写 timezone；
- M02/M03 记录 resolution 的 owner，M09 验证 hres 切换后的最终可见值。

## D008：共享 core 不拥有 fallback 政策

- 状态：已决定
- 阶段：M01

`context->fallback_mode` 把 syscall 和 kernel backend 政策放入算法并增加固定
依赖。M05 删除该耦合：

- shared core 返回有限内部状态；
- user wrapper 唯一执行 syscall；
- kernel generic dispatcher 唯一进入 backend；
- typed 成功路径不读取 fallback mode。

## D009：允许最小 provider 专门化，不允许算法复制

- 状态：已决定
- 阶段：M01

kernel clocksource 与用户 TSC/PV/HV 的取 cycle 环境不同。允许从同一源定义
生成最小 provider/entry 专门化，以避免热路径通用函数指针；seq、delta、
mult/shift、base、offset 和 normalize 不能在 user 目录重写。

若 M05 产生两个完整 global algorithm 机器码实例，必须视为设计失败而不是复用。

## D010：普通 kernel reader 按 typed root path 接入

- 状态：已决定
- 阶段：M01

保留所有现有 `ktime_get_*` 名称和 EXPORT，不修改大量调用者。函数体直接进入
对应 root-namespace typed reader：

- 不传 MM_data；
- 不检查 namespace mask；
- 已知时钟不经过 generic dispatcher；
- `ktime_mono_to_any`、hrtimer、snapshot 等特殊 helper不强行替换。

## D011：中间阶段不做真实性能结论

- 状态：已决定
- 阶段：M00/M01

M01～M09 只做 QEMU 正确性、汇编/调用图/代码量审计。只有 M10 在裸机重新
成对构建和测量 Raw/VKSO；历史结果只作基线，不把 QEMU cycles 当性能证据。

## D012：ABI v11 布局固定为 168-byte 单 descriptor payload

- 状态：已决定并验证
- 阶段：M02

布局将 header、公共 descriptor 和 realtime base放在首个 cache line；
monotonic最多增加一条 cache line；raw base从 shared offset 128开始。
`time()` seconds位于自然对齐 offset 40。

有效 payload从 v10 的184 bytes降到168 bytes。ABI v10不保留运行时兼容分支；
wrapper init同时检查 shared v11和MM_data v3，版本错配返回`EPROTO`。
精确布局和 memory-order 协议见 `ABI_V11.md`。

## D013：boottime offset从canonical base差值保留（已被 D023 取代）

- 状态：历史决定；M10 直接 shared 实验后废止
- 阶段：M03

删除仅供发布转换使用的`monotonic_to_boot`，但不在每个tick调用
`ktime_to_timespec64(offs_boot)`：

- normal producer从旧canonical boottime与monotonic base的差恢复offset；
- rare sleeptime事件直接推进canonical boottime；
- shift变化时用旧shift恢复整数纳秒，再按新shift构造base。

这同时消除冗余字段和周期64-bit division。`offs_boot`仍为fast/snapshot等
专用kernel接口保留，不作为普通global reader数据源。

## D014：shared publisher使用显式148-byte scalar协议（已被 D023 取代）

- 状态：历史决定；M10 直接 shared 实验后废止
- 阶段：M04

publisher直接接收canonical `tk_read_state`，不构造栈上shared snapshot，也不
接收`struct timekeeper`。周期更新只在shared seq奇数区间发布21个必要字段，
共148 bytes；timezone继续按事件单独更新，reserved字段不复制。

当前编译结果的奇数窗口只有直接load/store与配对barrier，无函数调用、除法、
循环或跨模型转换。保留显式scalar发布是为了使字段和原子宽度可审计；只有
M10证据证明固定尺寸copy更优且不破坏`time()`原子字段时，才允许独立试验替换。

## D015：pure core 使用有限状态，不拥有 fallback

- 状态：已决定并验证
- 阶段：M05

shared core 只返回 `OK`、`UNSUPPORTED_MODE` 或 `BACKEND_REQUIRED`。前者表示
算法成功，后两者分别表示 environment provider 不可用和 clock 不属于
global-time 集合。

user public wrapper 唯一执行 syscall，kernel dispatcher 唯一进入 POSIX
backend。`fallback_mode`、syscall number 和 syscall asm 不得重新进入 shared
core。这样 typed 成功路径不支付策略字段读取，也不会让可映射算法依赖某一种
地址空间的执行政策。

## D016：cycle delta 同时保持 x86 clamp 与有限 mask wrap

- 状态：已决定并验证
- 阶段：M05

`mask == U64_MAX` 时保持 x86 native vDSO 的 backward-observation clamp；
finite mask 时使用 clocksource 等价的 modulo delta。该规则既保留当前 TSC
热路径语义，又让 ABI v11 的 mask 对未来合法 provider 有实际含义。

启动期测试覆盖 forward、backward clamp 和 8-bit wrap；M09 继续用
clocksource switch 与并发 seq 测试验证完整路径。

## D017：typed reader 固定为 root namespace

- 状态：已决定并验证
- 阶段：M06

clock-specific typed reader 不接收 MM_data。kernel 普通 reader直接调用该入口；
syscall generic core和user public entry只在typed读取成功后应用per-MM offset。

offset归一化仍由一份可映射的`vkso_time_apply_offset()`实现，user assembly
不复制公式。这样kernel root path不支付MM指针、mask或NULL分支，shared core
也不依赖current task。

## D018：unsupported clocksource 使用单一 private cold helper

- 状态：已决定并验证
- 阶段：M06

用户可见shared state不能包含clocksource函数指针。对于无法由TSC/PV/HV
provider表示的合法clocksource，普通kernel reader由一个
`timekeeping_get_private()` cold helper保持完整动态read语义。

该helper只处理provider failure/early mode，不是normal global-time算法的
第二source of truth；fast/NMI/writer-held reader继续使用各自专用路径。

## D019：provider failure 与非 global backend 使用不同冷出口

- 状态：已决定并验证
- 阶段：M07

`UNSUPPORTED_MODE` 表示 clock ID 属于 global 集合，但当前 clocksource 不能由
共享 provider 采样。若将其交给原 `k_clock`，global backend 会调用已经迁移的
`ktime_get_*()`，从而再次进入刚失败的 shared reader。

M07 因此将两类失败明确分开：

- `UNSUPPORTED_MODE` 直接进入 `vkso_timekeeping_get_private()`，再由共享
  `vkso_time_apply_offset()` 应用 MM namespace offset；
- `BACKEND_REQUIRED` 才通过唯一 cold helper 进入
  `clockid_to_kclock()`，保留 CPU、alarm、dynamic/PTP 与 invalid 语义。

native 和 compat syscall 共用该 dispatcher。正常 global 路径仍只调用
`vkso_clock_gettime_core()` 一次；用户 public wrapper 的 syscall fallback
边界不变。

## D020：用配置边界移除不可达的 global k_clock callback

- 状态：已决定并验证
- 阶段：M08

启用 VKSO 后，统一 dispatcher 在进入 `k_clock` 前已经处理全部七种 global
clock；合法 global provider failure 也直接进入 private helper。因此原
`clock_get_timespec`/`clock_getres` global callback 在产品中不可达，却仍占用
机器码并形成算法所有权歧义。

M08 将这些 callback 及表项放到 `CONFIG_VKSO_TIME=n` 构建边界：

- VKSO 产品对象不再编译七个 gettime 与两个 getres callback；
- `clock_get_ktime`、set/adj、sleep 和 timer operation 保留，因为 POSIX timer
  仍真实调用它们；
- VKSO 关闭配置继续得到完整 Raw 行为。

这是静态功能选择，不是运行时条件分支。默认对象减少 772 bytes，Raw
compatibility build 的 callback 符号完整，QEMU Raw/VKSO 语义矩阵保持一致。

## D021：完整验证 hook 只进入专用配置

- 状态：已决定并验证
- 阶段：M09

early-boot、IRQ、NMI、writer-held、seq/mask 和无效 mode 的 kernel selftest
由 `CONFIG_VKSO_TIME_TEST` 统一控制。构建系统同时生成：

- validation image：启用 hook，用于证明特殊上下文和并发不变量；
- production image：关闭 hook，符号审计要求所有 `__vkso_test_*` 消失。

测试 hook、动态 POSIX clock module、ABI matrix 和 QEMU orchestration 全部归
T1，不进入产品 SLOC 或性能路径。M09 不允许为了制造后端状态而向产品
alarm/CPU/dynamic 实现添加测试分支。

## D022：后端与时间事件必须走真实状态转换

- 状态：已决定并验证
- 阶段：M09

完整验证不用 mock 替代关键语义：

- dynamic/PTP 由注册 `struct posix_clock` 的外部测试 module 提供合法 FD clock；
- 无 RTC alarm 通过启动时 blacklist RTC device/driver initcall 构造，Raw/VKSO
  均实际进入原 alarm backend；
- leap 测试把 realtime 定位到 UTC 日界前，等待真实 insertion，并验证
  TAI-realtime offset 增加一秒；
- clocksource 测试实际在 TSC 与 HPET 间切换，验证 user provider fallback；
- suspend 测试实际进入 QEMU S3，由 RTC 唤醒并核对 monotonic/boottime/realtime。

因此 M09 证明的是 dispatcher、producer、发布和后端的完整运行路径，而不只是
静态编译或人为调用单个 helper。

## D023：shared 页直接作为唯一 canonical reader state

- 状态：已实现并通过 QEMU 功能验证，等待 M10 裸机性能门槛
- 阶段：M10

M03/M04 的过渡实现仍保留一份 kernel-private canonical staging，然后将同类型
payload 发布到独立 shared 页。虽然不存在跨模型转换，但仍有一个 160-byte
重复实例和一次逐字段搬运，不符合最终的单一数据所有权目标。

最终候选改为：

- 物理独立的 `vkso_shared_page.data.state` 本身就是唯一 canonical
  global-reader state；
- kernel 通过可写 alias 维护该页，用户只得到同一物理页的 R--/NX 映射；
- `struct timekeeper` 只保留 NTP、clocksource、特殊 reader 和 producer
  必需的 private 状态，不嵌入 canonical payload；
- producer 完成 NTP 等复杂 private 更新后，将 shared seq 置奇数，直接从
  private owner 派生并写入最终 canonical 字段，随后结束 seq；
- 删除 staging 对象、real/shadow canonical 副本和
  `vkso_time_publish()` 第二次 payload 搬运；
- `offs_boot` 保持权威 private offset，只额外维护一个事件型
  `timespec64` split cache，避免每个 tick 在 seq 窗口中进行 64-bit 除法。

这会让 shared seq 奇数窗口包含最终的固定字段派生，因此不再满足 D014
“奇数区间只做复制”的旧目标。代价必须通过 read/update 并发实验衡量；若
retry 或 tail latency 显著恶化，则回退 D023，而不是重新引入第三种数据模型。

## D024：只共享kernel/user真正重合的reader

- 状态：已实现并通过normal/no-retpoline QEMU，等待裸机门槛
- 阶段：M10

`ktime_get_coarse_with_offset()`支持kernel-only的REAL/BOOT/TAI offset读取；
Linux没有对应的`CLOCK_BOOTTIME_COARSE`或`CLOCK_TAI_COARSE`用户clock ID。
将其强行统一到shared core曾需要两个额外typed入口和一套从hres base恢复offset
的算法，但没有消除任何用户侧重复。

当前决定：

- realtime/monotonic coarse继续使用shared core，因为它们有对应用户ABI；
- kernel-only BOOT/TAI coarse直接读取timekeeper private base与offset，保持
  Raw的seq和返回语义；
- 删除`vkso_clock_gettime_boottime_coarse()`、
  `vkso_clock_gettime_tai_coarse()`及其通用base差值helper；
- 该例外不允许扩展到已有用户等价实现的hres/global reader。

相对D023直接shared基线，功能源码减少58 SLOC，目标对象`.text`减少292 B；
读取路径还减少一次shared函数调用和多组base load，因此没有以性能换代码量。

## D025：clock-id分派只存在于kernel/user public边界

- 状态：已实现并通过多配置静态构建与normal QEMU，等待裸机门槛
- 阶段：M10

旧`vkso_clock_gettime_core()`和`vkso_clock_getres_core()`并非真正共享边界：
用户public汇编为性能直接调用typed reader，只有kernel syscall和benchmark调用
generic core；它们却被列为libkernel.so动态导出，形成第三份clock-id策略和
benchmark-only ABI。

当前决定：

- shared core只保留seq/cycles/base/offset/normalize及typed reader；
- user public wrapper保留一次用户clock-id分派和唯一syscall fallback；
- kernel syscall边界保留一次kernel clock-id分派和private/`k_clock` cold exit；
- 删除`BACKEND_REQUIRED`伪状态、两个generic core及其kernel adapter；
- `make_dll`从private wrapper relocation自动求dependency roots，typed reader
  保持内部符号，不再写入功能export清单；
- benchmark不再直接调用内部core，只测真实public ABI。

相对D024候选，生产功能源码净减少30 SLOC，两条kernel syscall目标机器码净减
52 B，`libkernel.so`文件减少256 B；用户typed reader和public wrapper机器码
不变。动态导出从10个降到7个，其中五个是时间public ABI，两个是当前C2
context启动机制。

## D026：成功路径 tail-enter shared reader，fallback 进入显式冷 backend

- 状态：已决定并通过 normal 裸机验证
- 阶段：M11

用户 public wrapper 加载 context 后 tail-jump 到 shared reader；shared reader
成功时直接返回原调用者，只有 `UNSUPPORTED_MODE/BACKEND_REQUIRED` 才
tail-jump 到有类型的冷 backend。kernel/user 两个 context 分别绑定可信的
kernel backend 和用户 syscall trampoline，共享 core 不包含 syscall 号或
`k_clock` 策略。

提交 `f8d5d16` 的两次独立 normal 裸机结果显示：hres 每次减少 7 条指令和
2 个分支且 cycles 中性；coarse、gettimeofday 和 getres 明显改善；cold
fallback 约退化 0.5%～0.7%。因此保留 O4，不继续为剩余亚 cycle 差异引入 O5。

## D027：secondary-mapped ITS 使用显式 reusable-text 静态目标

- 状态：已决定并验证
- 阶段：M11

x86 ITS 默认可把间接分支改写到启动期动态分配的 thunk。该地址只在 kernel
映射中有效；若源指令位于被二次映射的 VKSO text，同一条相对分支不能在
libkernel.so 地址处到达动态 thunk。

提交 `0c1215f` 采用两层通用约束：

- `alternative.c` 只对 secondary-mapped text 保留静态 ITS thunk，其他内核
  文本继续使用原动态 ITS 行为；
- `reusable_text.txt` 将静态 thunk 声明为非导出的原生依赖根，构造器校验
  owner/函数类型、求 KRG 闭包并保留目标所在整页。

清单缺失、为空或条目不合法时构建直接失败。新增目标只增加一个符号根，不在
内核中累积页地址特例。最终通用方案与早期静态候选的 wrapper 页、关键符号
布局和 hot-path PMU 指令完全相同，因此修复没有 read 运行时开销。
