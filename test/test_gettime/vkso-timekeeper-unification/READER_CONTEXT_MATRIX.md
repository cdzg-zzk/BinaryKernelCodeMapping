# M01 Reader 上下文矩阵

## 1. 分类原则

普通 shared reader 可以：

- 在 process、softirq 和 hardirq 中执行；
- 使用有限 seq retry；
- 调用当前 clocksource/provider；
- 读取已发布 canonical snapshot。

普通 shared reader不能：

- 在可能打断 writer 的 NMI 中等待同一个 seq；
- 在持有 `timekeeper_lock` 或 shared writer 正在发布时读取 shared seq；
- 在 early boot/provider 尚未初始化时假设正常 clocksource；
- 替代 hrtimer leap、cross timestamp 或 suspend 内部的特殊语义。

目标分类：

- **G**：迁移到 global shared typed reader；
- **W**：保留 public ABI/内核 ABI 薄 wrapper；
- **F**：保留 fast/NMI latch；
- **P**：保留 private/writer-locked helper；
- **B**：cold backend；
- **S**：其他特殊 reader，不强行统一。

## 2. 用户与 syscall reader

| 入口 | 当前上下文 | 当前路径 | 目标 |
|---|---|---|---|
| `__vkso_clock_gettime` 支持 global clock | user | assembly clockid 分派→typed VKSO core | W→G；ABI 不变 |
| `__vkso_clock_gettime` unsupported | user | assembly 直接 syscall | W→B；唯一 user fallback |
| `__vkso_clock_getres` | user | bitmap→typed getres 或 syscall | W→G/B；保留位图合理性 |
| `__vkso_gettimeofday` | user | shared realtime/timezone | W→G |
| `__vkso_time` | user | 单次 realtime seconds load | W→G，保持单次对齐读取 |
| `clock_gettime` syscall global | process | generic core→必要时 `k_clock` | W→G；不走旧 global k_clock |
| `clock_gettime` syscall CPU/alarm/dynamic | process | core fallback→`k_clock` | W→B |
| `clock_getres` syscall global | process | generic core | W→G |
| `clock_getres` syscall backend | process | core fallback→`k_clock` | W→B |
| `gettimeofday`/`time` syscall | process | VKSO core，失败旧 reader | W→G |

用户成功路径可以 seq retry；syscall 的 usercopy 必须继续留在 public syscall
边界，shared core 不访问用户指针。

## 3. 普通 kernel global reader

下表中的调用文件数是 M01 时排除定义文件后的静态参考，只用于说明影响面，
不等于运行次数。

| API/组 | 调用文件数 | 当前同步 | 合法上下文 | 目标 | 说明 |
|---|---:|---|---|---|---|
| `ktime_get()` 及 `*_ns` | 349 | `tk_core.seq` | process/softirq/hardirq | W→G | root monotonic typed reader |
| `ktime_get_real()` / `with_offset(REAL)` | 2个直接 helper，广泛 inline | `tk_core.seq` | process/IRQ | W→G | typed realtime，不保留 generic offset 热分派 |
| `ktime_get_boottime()` | inline | `tk_core.seq` | process/IRQ | W→G | typed boottime |
| `ktime_get_clocktai()` | inline | `tk_core.seq` | process/IRQ | W→G | typed TAI |
| `ktime_get_raw()` / raw ns | 15 | `tk_core.seq` | process/IRQ | W→G | typed raw |
| `ktime_get_real_ts64()` | 63 | `tk_core.seq` | process/IRQ | W→G | 输出 ABI 保持 |
| `ktime_get_ts64()` | 43 | `tk_core.seq` | process/IRQ | W→G | monotonic |
| `ktime_get_raw_ts64()` | 11 | `tk_core.seq` | process/IRQ | W→G | raw |
| boottime/TAI ts64 inline | 多处 | underlying seq | process/IRQ | W→G | typed base，最后格式转换 |
| `ktime_get_coarse_real_ts64()` | 15 | `tk_core.seq` | process/IRQ | W→G | coarse realtime |
| `ktime_get_coarse_ts64()` | 6 | `tk_core.seq` | process/IRQ | W→G | coarse monotonic |
| coarse offset/inline 组 | 2个直接 helper | `tk_core.seq` | process/IRQ | W→G | typed real/boot/TAI |
| `ktime_get_resolution_ns()` | 3 | `tk_core.seq` | process/IRQ | W→G | canonical resolution |
| `ktime_get_seconds()` | 44 | 单次 `unsigned long` load | process/IRQ | W→G | canonical monotonic coarse seconds |
| `ktime_get_real_seconds()` | 111 | 64位单次 load/32位 seq | process/IRQ | W→G | x86-64单次原子 load 保持 |
| `ktime_mono_to_any()` | 5 | `tk_core.seq` 读 offset | process/IRQ | S | 是任意历史 monotonic 值转换，不是“读取现在”；保留 private offset helper |

迁移原则：

- public 函数名和 EXPORT 保持；
- 已知时钟直接调用 typed reader；
- root kernel reader 不传 MM_data，不检查 namespace mask；
- 不批量修改调用者；
- shared core 失败只可能来自 provider/mode，不转入 syscall；
- 任何被发现从 NMI 调用的普通 API 必须重新分类，不靠“通常不会”合并。

## 4. fast/NMI/no-seq reader

| API | 当前数据 | 上下文/语义 | 目标 |
|---|---|---|---|
| `ktime_get_mono_fast_ns()` | `tk_fast_mono` latch | NMI/tracing；允许更新边界小幅乱序 | F，保留 |
| `ktime_get_raw_fast_ns()` | `tk_fast_raw` latch | NMI；raw slope 稳定 | F，保留 |
| `ktime_get_boot_fast_ns()` | fast mono + racy `offs_boot` | NMI；文档允许 resume 窗口偏差 | F，保留 |
| `ktime_get_real_fast_ns()` | fast mono `base_real` | NMI | F，保留 |
| `ktime_get_fast_timestamps()` | fast mono + boot offset | NMI，多 clock 同时近似 | F，保留 |
| `__ktime_get_real_seconds()` | 无 seq单次 load | writer-held、MCE/KDB/NTP 特殊上下文 | P/F，保留 |
| `random_get_entropy_fallback()` | 直接 clocksource pointer/read | early boot/suspend 容错 | P，保留 |

原因：NMI 可能中断 shared writer；若它在 seq 为奇数时自旋，writer无法恢复。
fast latch 的允许误差也是公开语义，不能用普通严格 snapshot 替换。

## 5. hrtimer、snapshot 与 cross timestamp

| API | 当前字段 | 调用上下文 | 目标 |
|---|---|---|---|
| `ktime_get_update_offsets_now()` | mono base、real/boot/TAI offset、clock-set seq、next leap | hrtimer interrupt/retrigger | S，保留专用 helper |
| `ktime_get_snapshot()` | 同一 cycles 下 real/raw、clocksource id、两事件 seq | PTP/PPS/设备同步 | S，保留 cross snapshot |
| `get_device_system_crosststamp()` | private clock pointer、历史 snapshot | 设备 callback/process/driver | S，保留 backend |
| `getboottime64()` | `offs_real-offs_boot` | RTC/系统管理 | S，可改读 private offset但不走“现在”reader |

这些函数不是普通 clock_gettime 的重复实现：

- hrtimer helper处理 leap 插入和 offset generation；
- snapshot 需要返回 clocksource identity 与 event sequence；
- cross timestamp 要校验设备 counter 与当前 clocksource；
- getboottime 返回系统启动 wall time，而不是 `CLOCK_BOOTTIME` 当前值。

M06 不能为了减少代码量把它们强行包装到 shared clock_gettime core。

## 6. writer-locked 与 producer helper

| helper/路径 | 锁状态 | 目标 |
|---|---|---|
| `tk_clock_read()` in writer | 持 `timekeeper_lock` | private provider |
| `timekeeping_forward_now()` | writer 路径 | 直接更新 canonical accumulator，不读 shared seq |
| `tk_update_ktime_data()` | writer | M03 被 canonical finalize helper 取代 |
| `timekeeping_update()` | writer | canonical finalize→短发布→fast update |
| settime/inject/clock switch | writer + `tk_core.seq` | private/canonical helper |
| periodic `shadow_timekeeper` advance | `timekeeper_lock`，复杂计算在 real seq 外 | 在 shadow canonical 上计算 |
| suspend/resume | writer + IRQ off | private/canonical + fast halt/resume |
| NTP/leap adjustment | writer | private政策状态→canonical结果 |

硬规则：上述路径不得调用任何会等待 `vkso_shared_page.seq` 的普通 reader。

## 7. backend reader

| 后端 | 上下文 | 目标 |
|---|---|---|
| process/thread CPU clock | process，task/cputime 锁和权限检查 | B |
| alarm clock | process，RTC availability + timens | B |
| dynamic/PTP clock | process，fd lookup、file/driver ops | B |
| invalid ID | process/user fallback | B/error |

这些路径功能保留但不进入 global core。详见 `BACKEND_SEMANTICS.md`。

## 8. 结论

- 普通 global reader 集合已完整归入 G/W；
- fast/NMI、writer-locked、early boot、hrtimer 和 cross timestamp 均有明确
  保留类别；
- M06 只替换第3节普通 API 的函数体，不修改其调用者；
- M06 不替换第4～7节特殊/后端函数；
- 不存在“尚未审计但先迁移”的 reader。
