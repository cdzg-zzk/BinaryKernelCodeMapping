# 代码规模语义清单

## 1. 用途

本文件定义 Raw/VKSO clock/time 功能的人工语义统计边界。脚本只能对本清单
确认的文件、符号或行区间求和，不能自动决定代码归属。

M00 先冻结旧报告口径；M01 补齐符号级所有权；M08 删除旧实现后重新审计；
M10 生成最终源码和机器码数字。

## 2. 统计规则

### 2.1 产品运行时代码

计入：

- 对目标 clock/time ABI 的实际成功路径和 fallback；
- global-time shared algorithm；
- kernel producer/private 状态中仅为目标读取语义必需的部分；
- publisher、shared ABI、MM_data 选择和必要映射接入；
- user ABI wrapper；
- CPU/alarm/dynamic 等目标 ABI 必需 backend 边界；
- PVClock/Hyper-V 源码支持；
- 最终启用配置需要的构建/链接胶水。

不计入产品运行时代码、但单独披露：

- `static_assert`、编译期 layout 验证；
- `CONFIG=n` stub；
- benchmark、probe、QEMU/裸机脚本和报告；
- 通用 `make_dll`/manager/page-cache 项目基础设施；
- x32、IA32、legacy vsyscall 和本实验明确关闭的功能；
- 其他内核子系统仍使用、但目标 ABI 不再依赖的旧 reader；
- 过渡 compat/bridge 代码。

### 2.2 共享代码归属

VKSO core 位于 kernel tree 且由项目机制导出给用户执行，归为
“kernel/user shared”，不能同时计入 kernel 专属和 user 专属。

用户 wrapper 只计 ABI、context/environment 绑定和 syscall fallback。若用户
目录出现 seq、delta、mult/shift、base 或 normalize 的第二份实现，必须标记为
重复代码并在 M08 前删除。

### 2.3 源码与机器码

- SLOC：去除空行和纯注释后的有效源码行；
- Git churn：单独报告新增/删除物理行，不替代 SLOC；
- machine code：按目标 symbol 的真实 `st_size` 求和；
- 不用 `libkernel.so` 文件大小、整个 `.text` 或压缩 Image 大小代替目标符号；
- shared payload、MM payload、映射页和 ELF 元数据分别报告。

## 3. 互斥分类

| ID | 类别 | Raw 典型内容 | VKSO 目标内容 |
|---|---|---|---|
| U1 | user public ABI wrapper | `__vdso_*` entry/clock switch | `__vkso_*` wrapper、context 绑定、fallback |
| S1 | shared global algorithm | 无 kernel/user 共享机器码 | seq、delta、mask、mult/shift、base、offset、normalize |
| K1 | kernel public reader | `ktime_get_*` 目标依赖算法 | root-namespace typed 薄 wrapper |
| K2 | producer/private | 目标读取所需 timekeeper 更新 | canonical state 的直接维护 |
| K3 | publisher/data ABI | `update_vsyscall`/vdso_data | v11 header/state/scalar publisher |
| K4 | syscall/dispatcher | global `k_clock`/syscall 分派 | typed global path + cold backend |
| B1 | CPU/alarm/dynamic backend | Raw 必需后端边界 | 原语义后端边界 |
| C1 | MM/context/namespace | VVAR/timens | MM_data v3/VVAR special mapping |
| E1 | environment provider | vDSO TSC/PV/HV | kernel clocksource + user TSC/PV/HV |
| G1 | 功能构建/链接胶水 | vDSO linker/image/Kbuild | VKSO section/export/wrapper glue |
| P1 | 项目通用机制 | 不适用/既有 vDSO infra | make_dll/manager/page replacement |
| X1 | 过渡/兼容 | 不适用 | compat conversion、双 ABI、临时 bridge |
| T1 | 验证 | vDSO tests | assert/probe/QEMU/bare-metal/报告 |

任何有效行只能进入一个 ID。公共 include 或 helper 若服务多个类别，按直接语义
责任归入一个主类别，并在注释中列出消费者，不按消费者重复计数。

## 4. M00 旧实现锚点

权威旧清单：

- `vkso-tests/code-size/source-manifest.tsv`
- `vkso-tests/code-size/binary-symbol-manifest.tsv`
- `vkso-tests/code-size/incremental-source-manifest.tsv`
- `vkso-tests/code-size/VKSO开发工作量与代码规模评估_20260728.md`

旧实现的 60 SLOC `vkso_time_compat.h` 归入 `X1`。本次重构的结构目标是：

- `X1` 最终为零；
- Raw 的 user global algorithm 与 kernel global reader 重复维护，VKSO 由
  `S1` 单一源定义取代；
- `U1` 与 `K1` 只保留必要 ABI 适配，不把算法包装成多层转发；
- `K2 + K3` 只保留 producer 和最短发布，不引入第二套数据模型；
- `P1` 单列，既不能隐藏为零，也不能全部归给 clock/time 功能。

## 5. 后续补全点

M01 必须为每类补充：

- 精确文件和 symbol；
- 共享 header 的唯一归属；
- Raw/VKSO 功能对应关系；
- 其他 reader 保留代码为何不属于目标切片；
- 由同一源模板生成多份机器码时的实例数量和原因。

M01 已确认的 VKSO 符号/职责：

| 类别 | 当前符号/文件 | M08 目标 |
|---|---|---|
| U1 | `vkso_user_entry.S` 的 `__vkso_*`、bind/fallback | 只保留 ABI/context/cold fallback |
| S1 | `vkso_time_internal.h`、`vkso_time_core.c`、`vkso_time_cycles.c` | v11 typed shared algorithm |
| K1 | `timekeeping.c` 普通 `ktime_get_*` | root typed 薄 wrapper |
| K2 | `struct timekeeper`、NTP/settime/suspend/switch writer | private + canonical直接维护 |
| K3 | `vkso_time.c` publisher、`include/vkso/time.h` | 同类型 scalar publisher |
| K4 | `posix-timers.c`、`time.c` | global direct + cold backend |
| B1 | `posix-cpu-timers.c`、`alarmtimer.c`、`posix-clock.c` | 原语义保留 |
| C1 | `arch/x86/kernel/vkso.c`、namespace/mm/auxv hooks | MM ABI v3保持 |
| E1 | kernel clocksource、`vkso_time_cycles.c` TSC/PV/HV | 最小 provider |
| G1 | Kconfig/Makefile/lds/export manifests | v11同步修改 |
| X1 | `vkso_time_compat.h`、fallback mode core耦合、重复 raw descriptor | M08 为零 |
| T1 | ABI matrix、probe、assert、QEMU/bare-metal | 独立统计 |

特殊 reader（fast/NMI、hrtimer update-offset、snapshot/crosststamp、
`ktime_mono_to_any`）属于既有 kernel 必要功能，不混入 S1，也不因物理保留而
重复计入目标 global reader。

M08 必须确认：

- `X1=0`；
- U1/S1/K1/K2/K3/K4 无重复公式；
- 没有仅靠改名隐藏的旧实现；
- 测试和 `CONFIG=n` stub 未混入产品 SLOC。

M10 才填写最终 SLOC、Git churn、symbol bytes 和 payload bytes。

## 6. M08 产品边界复核

M08 以 `CONFIG_VKSO_TIME=y` 的最终链接结果作为产品代码边界。下表中的
文件可以物理重叠，但符号职责互斥；M10 必须按符号或明确行区间统计，不能把
整个文件重复归入多类。

| ID | VKSO 产品符号/行区间 | 唯一职责 |
|---|---|---|
| U1 | `vkso_user_entry.S` 的 `__vkso_clock_gettime`、`__vkso_clock_getres`、`__vkso_gettimeofday`、`__vkso_time`、`__vkso_getcpu` 及其本地 syscall/context veneer | 用户 public ABI、context/environment 绑定和唯一 syscall fallback |
| S1 | `vkso_time_core.c` 的 typed/global readers、`vkso_time_apply_offset()`、gettimeofday/time；`vkso_time_internal.h` 的 seq/delta/normalize primitive；`vkso_time_cycles.c` 的可映射 cycles provider | kernel/user 唯一 global-time 读取公式 |
| K1 | `timekeeping.c` 中普通 `ktime_get_*`、`ktime_get_coarse_with_offset()` 的 VKSO 分支 | 保持既有内核 ABI 的 root-namespace 薄入口 |
| K2 | `timekeeping.c` 的 `vkso_timekeeper_refresh()` 及其 writer 调用点；`struct timekeeper.vkso_read` | producer 直接维护 canonical state |
| K3 | `vkso_time.c` 的 `vkso_time_publish*()`、timezone 更新；`include/vkso/time.h` 的 v11 payload 定义 | 短发布协议和 shared data ABI |
| K4 | `posix-timers.c` 的 `vkso_clock_gettime_dispatch()`、`vkso_clock_getres_dispatch()` 及三个 cold helper；`time.c` 的 gettimeofday/time syscall 接入 | syscall global 成功路径与统一冷出口 |
| B1 | `posix-cpu-timers.c`、`alarmtimer.c`、`posix-clock.c` 的原 callback；`posix-timers.c` 中非 global `k_clock` 解析 | CPU、alarm、dynamic/PTP 必需 backend |
| C1 | `arch/x86/kernel/vkso.c` 的 MM_data special mapping、auxv/context 选择；time namespace 初始化/更新 hook | per-MM namespace/context 语义 |
| E1 | `vkso_time_cycles.c` 的 kernel clocksource 与 user TSC/PVClock/Hyper-V provider 边界 | 环境相关 cycles 获取，不包含换算公式 |
| G1 | `kernel/time/Makefile`、Kconfig、VKSO section/导出 manifest、`vkso_user_entry.S` 的 DSO section 声明 | 仅为功能产物存在的构建与链接接入 |
| P1 | 通用 `make_dll`、manager、page replacement、KRG 与映射生命周期实现 | 项目通用机制，单列而不计入 clock/time 专属实现 |
| T1 | `CONFIG_VKSO_TIME_TEST` probe、layout assert、ABI matrix、benchmark、QEMU/裸机脚本和阶段报告 | 验证证据，不进入产品运行时 SLOC |

以下内容明确不进入启用 VKSO 的产品切片：

- `CONFIG_VKSO_TIME=n` stub 和该配置下的原 global `k_clock`
  gettime/getres callback；
- fast/NMI、writer-locked、early-boot、crosststamp 与 hrtimer
  update-offset 等特殊 reader；
- x32、IA32、legacy vsyscall 和本实验关闭的功能；
- 其他子系统继续需要、但目标 clock/time ABI 不调用的旧算法。

M08 链接/符号审计结果：

- `X1=0`：不存在 compat conversion、双 shared ABI、fallback mode 或临时
  bridge；
- 启用 VKSO 的 `posix-timers.o` 不含九个旧 global gettime/getres callback；
  `CONFIG_VKSO_TIME=n` 对象仍完整包含它们；
- 用户测试兼容层只保留一次性 `vkso_user_wrapper_init()`，不再导出六个无调用
  转发函数；
- `CONFIG_VKSO_TIME_TEST` probe 只进入测试配置，生产 package 明确标记
  `production_test_probe=absent`。

M10 仍需对 Raw 建立同样的精确 symbol/line-range 映射，并为每个 ID 填写
SLOC、Git churn 与 symbol bytes；本节只冻结语义归属，不提前用脚本猜测数字。
