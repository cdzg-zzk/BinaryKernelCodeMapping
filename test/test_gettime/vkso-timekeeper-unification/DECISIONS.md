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

## D002：canonical state 嵌入 `struct timekeeper`

- 状态：已决定
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

## D013：boottime offset从canonical base差值保留

- 状态：已决定并验证
- 阶段：M03

删除仅供发布转换使用的`monotonic_to_boot`，但不在每个tick调用
`ktime_to_timespec64(offs_boot)`：

- normal producer从旧canonical boottime与monotonic base的差恢复offset；
- rare sleeptime事件直接推进canonical boottime；
- shift变化时用旧shift恢复整数纳秒，再按新shift构造base。

这同时消除冗余字段和周期64-bit division。`offs_boot`仍为fast/snapshot等
专用kernel接口保留，不作为普通global reader数据源。

## D014：shared publisher使用显式148-byte scalar协议

- 状态：已决定并验证
- 阶段：M04

publisher直接接收canonical `tk_read_state`，不构造栈上shared snapshot，也不
接收`struct timekeeper`。周期更新只在shared seq奇数区间发布21个必要字段，
共148 bytes；timezone继续按事件单独更新，reserved字段不复制。

当前编译结果的奇数窗口只有直接load/store与配对barrier，无函数调用、除法、
循环或跨模型转换。保留显式scalar发布是为了使字段和原子宽度可审计；只有
M10证据证明固定尺寸copy更优且不破坏`time()`原子字段时，才允许独立试验替换。
