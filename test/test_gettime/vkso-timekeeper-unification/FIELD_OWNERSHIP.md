# M01 字段所有权矩阵

## 1. 范围与符号

本矩阵审计 Linux 5.15.198 VKSO 当前实现中的：

- `struct tk_read_base`
- `struct timekeeper`
- `struct vkso_shared_data`
- `struct vkso_mm_data`
- `struct vkso_context`
- `tk_core`、`shadow_timekeeper`、`tk_fast_*`

目标归属：

| 标记 | 目标归属 |
|---|---|
| P | timekeeper private producer 状态 |
| C | shared_data 中唯一 canonical `tk_read_state` |
| M | per-MM `vkso_mm_data` |
| E | kernel/user environment context |
| F | fast/NMI/writer-locked/early-boot 专用状态 |
| X | canonical 建立后删除 |

“P→C”表示当前字段是 producer 状态，但其 reader 语义必须由 producer 直接写入
canonical 字段；不是允许两个独立 source-of-truth。

## 2. 当前同步模型

| 对象 | writer 同步 | reader 同步 | 生命周期 |
|---|---|---|---|
| `tk_core.timekeeper` | `timekeeper_lock` + `tk_core.seq` | 普通 reader 使用 `tk_core.seq` | 全局 |
| `shadow_timekeeper` | `timekeeper_lock`，seq 外复杂计算 | 无外部 reader；最终 memcpy 到 real | 全局 |
| `tk_fast_mono/raw` | `seqcount_latch_t` 双 buffer | NMI-safe latch reader | 全局 |
| `vkso_shared_page` | `timekeeper_lock` 内，直接维护 canonical state，并使用独立 shared seq | kernel/user shared seq | 全局独立页 |
| `vkso_mm_page` | exec/fork/setns 生命周期串行更新 | mask acquire 语义后读 offset | per-MM |
| `vkso_context` | 初始化/虚拟化页面注册时 `WRITE_ONCE` | cycles provider `READ_ONCE`/稳定页协议 | 每执行环境 |

`timekeeping_advance()` 的关键顺序是：

```text
在 shadow_timekeeper 上完成复杂计算
  -> begin tk_core.seq
  -> timekeeping_update(shadow)
  -> 直接派生并写入 VKSO shared canonical state
  -> memcpy shadow 到 tk_core.timekeeper
  -> end tk_core.seq
```

其他 settime、clocksource、suspend/resume 路径直接更新
`tk_core.timekeeper`，均持有 `timekeeper_lock` 和 `tk_core.seq`。

最终 canonical state 不嵌入 `struct timekeeper`。它只存在于物理独立的
`vkso_shared_page`；producer 在既有 shadow/real 更新顺序内直接维护它，
shared seq 排除用户和普通 kernel reader 观察到部分代际。real/shadow 只携带
各自原有的 private producer 状态。

## 3. `struct tk_read_base` 字段

| 当前字段 | 当前 writer | 当前 reader | 目标 | 处理 |
|---|---|---|---|---|
| `clock` | `tk_setup_internals()` | `tk_clock_read()`、snapshot、fast、clocksource 查询 | P/E/F | timekeeper private 保留唯一 clocksource 指针；shared 只发布 `clock_mode` |
| `mask` | `tk_setup_internals()`，mono/raw 同值 | delta、snapshot、fast | C/F | 公共 cycle descriptor 的 `mask`；fast snapshot 保留副本 |
| `cycle_last` | setup、forward、log accumulation、resume；mono/raw 成对 | 所有 hres reader、snapshot、fast | C/F | 公共 `cycle_last`；fast snapshot保留副本 |
| `mult` | setup；mono 被 NTP 调整，raw 保持原始值 | delta 换算、snapshot、fast | C/F | 公共 descriptor 内 `mono_mult`、`raw_mult` 两字段 |
| `shift` | `tk_setup_internals()`，mono/raw 同值 | 换算、normalize、fast | C/F | 公共 `shift` |
| `xtime_nsec` | setup shift 转换、forward、NTP accumulation/adjust | realtime/raw/coarse 及 base 生成 | C | 由 canonical realtime/raw `shifted_nsec` 取代；不保留独立 reader 版本 |
| `base` | `tk_update_ktime_data()` | monotonic/raw ktime reader、snapshot、fast | C/F | canonical monotonic/raw base；fast latch保留专用格式 |
| `base_real` | `timekeeping_update()`、suspend halt helper | realtime fast reader | F | 仅 fast/NMI 使用，不进入普通 canonical payload |

### 3.1 mono/raw 公共 cycle 不变量

全树 writer 审计结果：

| 字段 | 全部写点 | 结论 |
|---|---|---|
| `clock` | `tk_setup_internals()` 同时赋同一 `clock` | 恒等 |
| `mask` | `tk_setup_internals()` 同时赋 `clock->mask` | 恒等 |
| `shift` | `tk_setup_internals()` 同时赋 `clock->shift` | 恒等 |
| `cycle_last` | setup、forward、log accumulation、resume 均成对赋相同值/加相同 interval | 恒等 |

`shadow_timekeeper` 与 real timekeeper 的整结构复制不会破坏不变量。树中没有其他
可达写点。结论：

- ABI v11 使用一份公共 `clock_mode/shift/cycle_last/mask`；
- `mono_mult/raw_mult` 显式分开；
- 不使用运行时“若相同则共用”的分支；
- M02 添加布局断言，M03 在所有 writer helper 中保持结构性成对更新；
- M09 加 clocksource switch、NTP 调频和 suspend/resume 定向测试。

## 4. `struct timekeeper` 字段

| 当前字段 | 当前职责/主要 writer | 主要 reader | 目标 | 处理 |
|---|---|---|---|---|
| `tkr_mono` | clocksource、NTP 和 monotonic/realtime 累积 | 普通、snapshot、fast | P+C+F | 按第3节拆分，不再作为普通 reader 的整块模型 |
| `tkr_raw` | raw 累积 | raw、snapshot、fast | C+F | 去掉与 mono 重复的 clock/mask/last/shift |
| `xtime_sec` | init、tick、settime、sleep、leap | realtime/coarse/seconds | C | canonical realtime seconds，原字段迁移后删除 |
| `ktime_sec` | `tk_update_ktime_data()` | `ktime_get_seconds()` | C | 使用 canonical monotonic coarse seconds，原字段删除 |
| `wall_to_monotonic` | init、settime、sleep、leap | producer、getboottime、旧 ts reader | P | 保留 settime/invariant 所需 private offset；普通 reader 不直接消费 |
| `offs_real` | `tk_set_wall_to_mono()` | offset reader、hrtimer、snapshot/fast | P+C/F | private 事件 offset；canonical 直接保存 realtime base |
| `offs_boot` | sleep injection | offset reader、hrtimer、fast boot | P+C/F | private suspend offset；canonical 直接保存 boottime base |
| `offs_tai` | wall/TAI offset 更新 | offset reader、hrtimer | P+C | private event offset；canonical 直接保存 TAI base |
| `tai_offset` | adjtimex、leap | producer | P | 保留政策状态，canonical 保存派生 TAI base |
| `clock_was_set_seq` | `timekeeping_update(TK_CLOCK_WAS_SET)` | hrtimer、snapshot/crosststamp | F | 保留 private/special，不发布给普通用户 reader |
| `cs_was_changed_seq` | `tk_setup_internals()` | snapshot/crosststamp | F | 保留 private/special |
| `next_leap_ktime` | `tk_update_leap_state()` | hrtimer update-offset helper | F | 保留 private/special |
| `raw_sec` | tick/forward/init | raw reader/base producer | C | canonical raw base seconds，原字段迁移后删除 |
| `monotonic_to_boot` | `tk_update_sleep_time()` | 仅 compat adapter | X | ABI v11 canonical boottime base 建立后删除 |
| `cycle_interval` | clocksource setup | tick accumulation/NTP | P | 保留 |
| `xtime_interval` | setup、NTP adjustment | tick accumulation/error | P | 保留 |
| `xtime_remainder` | setup | NTP adjustment/error | P | 保留 |
| `raw_interval` | setup | raw tick accumulation | P | 保留 |
| `ntp_tick` | setup、NTP adjustment | NTP adjustment/error | P | 保留 |
| `ntp_error` | setup、tick、clear | NTP adjustment | P | 保留 |
| `ntp_error_shift` | setup | NTP adjustment/error | P | 保留 |
| `ntp_err_mult` | setup、NTP adjustment | NTP adjustment | P | 保留 |
| `skip_second_overflow` | setup、NTP underflow/second accumulation | leap/NTP | P | 保留 |
| debug warning fields | debug checker | debug only | P | 配置私有，不共享 |

### 4.1 不允许删除的 private 语义

下列字段即使不属于普通 global reader，也不能因代码量目标删除：

- `wall_to_monotonic`：settimeofday 合法性及 real/mono 关系；
- `offs_real/boot/tai`：hrtimer、转换 API 和特殊 reader；
- `clock_was_set_seq/next_leap_ktime`：hrtimer 中断语义；
- NTP interval/error 系列：producer 正确性；
- `clocksource *`：kernel 环境动态 provider 和切换；
- fast latch 所需 `base_real`/clock pointer。

它们属于必要 private/backend，不计作重复用户 reader 算法。

## 5. 当前 `vkso_shared_data` 字段

| 字段 | 当前来源 | 当前 reader | v11 目标 |
|---|---|---|---|
| `seq` | `tk_publish_read_state()` | 全部 shared reader | 保留，唯一全局 canonical seq |
| `abi_version` | 静态初始化 | loader/test | 升级为 11 |
| `hres.cycles.clock_mode` | `tkr_mono.clock->vdso_clock_mode` | cycles provider | 移入公共 descriptor |
| `hres.cycles.cycle_last` | `tkr_mono.cycle_last` | hres reader | 公共 descriptor |
| `hres.cycles.mult` | `tkr_mono.mult` | mono/realtime reader | 改名 `mono_mult` |
| `hres.cycles.shift` | `tkr_mono.shift` | hres reader | 公共 descriptor |
| `hres.*_base` | compat 逐字段派生 | global hres readers | canonical producer 直接维护 |
| realtime/monotonic coarse | compat 派生 | coarse readers | canonical producer 直接维护 |
| `raw.cycles.clock_mode` | mono clock 重复发布 | raw cycles provider | 删除重复 |
| `raw.cycles.cycle_last` | `tkr_raw.cycle_last`，恒等 | raw reader | 删除重复 |
| `raw.cycles.mult` | `tkr_raw.mult` | raw reader | 公共 descriptor 的 `raw_mult` |
| `raw.cycles.shift` | `tkr_raw.shift`，恒等 | raw reader | 删除重复 |
| raw base | compat 派生 | raw reader | canonical producer 直接维护 |
| `hrtimer_resolution` | 每次 publish 读取全局变量 | getres | canonical/event 字段 |
| `timezone` | `do_sys_settimeofday64()` 事件写 | gettimeofday | 保留事件字段，不随每 tick 重写 |

ABI v10 当前没有 `mask`，reader 用 `cycles > cycle_last` 模拟 TSC clamp。
ABI v11 必须发布公共 `mask`，共享算法使用与 Raw clocksource 相同的 masked
delta 语义；TSC 轻微倒退的架构规则在 provider/typed reader 层明确处理。

## 6. MM_data 与 environment 字段

### 6.1 `vkso_mm_data`

| 字段 | writer | reader | 同步/目标 |
|---|---|---|---|
| `abi_version` | exec 分配初始化 | wrapper init | MM ABI v3 保持 |
| `clock_mask` | exec/setns 最后发布 | typed namespace reader | mask 是发布标志 |
| `monotonic_offset` | exec/setns 先写 | mono/raw/mono-coarse | M，保持 |
| `boottime_offset` | exec/setns 先写 | boottime | M，保持 |

MM_data 不需要 seq，理由不是“永远不更新”，而是：

1. time namespace offset 在任务进入前被冻结；
2. exec 初始化时尚未执行用户 reader；
3. setns 要求单线程，当前任务仍在 syscall 内；
4. fork 复制稳定整页；
5. writer 先写 offset，`smp_wmb()` 后最后发布 mask。

若未来允许同一 MM 中并发修改 offset，则上述前提失效，必须重新设计；本次范围
不改变 namespace 生命周期，因此不增加 MM seq。

### 6.2 `vkso_context`

| 字段 | 归属 | 目标 |
|---|---|---|
| `pvclock_page` | E | 用户/kernel 各自地址空间的 PVClock provider |
| `hvclock_page` | E | 用户/kernel 各自地址空间的 Hyper-V provider |
| `fallback_mode` | 当前 core/user-kernel 复用的模式开关 | M05 从纯 core 删除；fallback 只在 public 边界 |
| `reserved` | ABI padding | 内部 ABI 重排时删除或保留显式 padding |

`fallback_mode` 不是时间数据，且让共享 core 承担 syscall/kernel 两种政策。
M05 将其从算法依赖中删除；environment 只提供 cycles 所需状态。

## 7. writer 事件矩阵

| 事件 | 入口 | 变化的逻辑状态 | 当前 publish | v11 要求 |
|---|---|---|---|---|
| periodic tick | `timekeeping_advance(TK_ADV_TICK)` | cycle last、bases、NTP mult、raw | 每次 | private更新后直接维护shared canonical |
| frequency/NTP | `do_adjtimex()` / `TK_ADV_FREQ` | mono mult、xtime、TAI 可能变化 | 每次 | mult/base 同一代发布 |
| settimeofday | `do_settimeofday64()` | realtime、wall/real/tai offsets | 每次 | real/mono/tai bases 同次发布 |
| inject offset/warp | `timekeeping_inject_offset()` | realtime、wall offset | 每次 | 同 settimeofday |
| clocksource switch | `change_clocksource()` | clock/mode/mask/last/mult/shift | 每次 | descriptor+bases 原子代际发布 |
| initialization | `timekeeping_init()` | 全部初始状态 | 一次 | v11 header/state 初始化 |
| sleep injection | `timekeeping_inject_sleeptime64()` | realtime、boot/mono 关系 | 每次 | real/boot/mono 同次发布 |
| resume | `timekeeping_resume()` | cycle last、sleep、bases | 每次 | 恢复后同次发布 |
| suspend | `timekeeping_suspend()` | forward 后冻结状态 | 每次 | 发布冻结快照；fast 单独 halt |
| leap second | `accumulate_nsecs_to_secs()` | realtime、wall offset、TAI | tick publish | 事件同一代 |
| timezone | `do_sys_settimeofday64(tz)` | `sys_tz` | 独立无 seq | 事件型独立发布 |
| hrtimer hres enable | `hrtimer_switch_to_hres()` | `hrtimer_resolution` | 下次 tick 间接发布 | 保持 Raw 等价；M09 验证最终值 |
| namespace exec/setns/fork | arch setup / `timens_commit()` / dup | MM offsets/mask | per-MM | 不进入 global seq |

## 8. M01 结论

- 每个当前字段均有目标归属，没有未分类字段；
- mono/raw 公共 descriptor 不变量成立；
- canonical state 只存在于独立 shared 页，不进入 real/shadow；
- kernel可写alias与用户R--/NX映射指向同一物理状态；
- `monotonic_to_boot` 和重复 raw cycle metadata 是明确可删除项；
- private NTP、event offset、cross-timestamp 和 fast 状态必须保留；
- MM_data 无需 seq，environment 不进入 global shared 页；
- M02 可以定义单 descriptor ABI v11。
