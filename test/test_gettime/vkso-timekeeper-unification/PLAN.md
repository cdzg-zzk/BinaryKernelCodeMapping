# VKSO timekeeper 统一重构计划

## 1. 基线与工作范围

- Git 分支：`vkso-timekeeper-unification`
- 起点提交：`d89f2e5f8f9ae6fec353ead9cf4dcd77456b3ddd`
- 受保护基线：`vkso-temporary-final-20260728`
- 实际修改源码：`test/test_gettime/linux-5.15.198-vkso`
- 结构基线：`test/test_gettime/linux-5.15.198-no-vdso`
- 语义参考：Linux 5.15.198 Raw kernel

不从 Raw kernel 重新实现，避免重新引入原生 vDSO、IA32、x32 和 legacy
vsyscall。也不从 no-vDSO 目录重新实现已经验证的 VKSO 功能。所有功能修改都在
当前 VKSO kernel 中逐步完成；no-vDSO 和 Raw 只作对照。

## 2. 总体目标

1. 将基于 timekeeper 的 global-time 读取逻辑统一为一份可映射 core。
2. 将 timekeeper 明确拆分为 kernel-private producer 状态和最小 read state。
3. kernel 和 user 使用同一种 `tk_read_state` 数据类型，消除逐字段类型转换。
4. producer 在私有状态中完成复杂计算，再以最短 seq 临界区发布同类型快照。
5. global shared data 继续通过项目机制以 R--/NX 映射给用户。
6. per-MM context data 继续使用 VVAR 式只读 special mapping。
7. 普通 `ktime_get_*` 保留名称和导出 ABI，内部改为共享 core 的薄 wrapper。
8. fallback 语义保留，但集中在 ABI/dispatcher 边界，core 内不重复实现。
9. CPU、alarm、dynamic/PTP、NMI/fast reader 保留必要的专用 backend。
10. 保持所有用户 ABI、syscall ABI、time namespace 和错误语义。

## 3. 非目标

- 不把完整 `struct timekeeper` 或任何 kernel 指针映射给用户。
- 不强行让 CPU clock、alarm clock 或动态设备 clock 使用 global-time 算法。
- 不删除 `ktime_get_*_fast_ns()`、`tk_fast` 或 NMI-safe reader。
- 不修改所有现有 kernel 调用者；通过兼容 wrapper 保持原调用接口。
- 不以代码量为理由牺牲正确性、ABI、并发语义或可读性。
- 不在 QEMU 中用性能数字作最终结论；QEMU 只验证功能和稳定性。

## 4. 目标数据模型

### 4.1 Private producer state

只在 kernel 中存在，保存：

- `struct clocksource *`、clocksource 私有能力和更新状态；
- NTP interval、误差、频率和 leap-second 状态；
- suspend/resume、clocksource 切换及 producer 状态；
- timekeeping lock、内部 seq、调试和统计状态；
- 不允许暴露给用户的其他字段。

### 4.2 Canonical read state

kernel producer 和 kernel/user reader 对字段含义使用唯一结构：

- clock mode、cycle last、mask、mult、shift；
- realtime、monotonic、monotonic raw、boottime、TAI base；
- realtime coarse、monotonic coarse；
- 读取路径真正需要的 resolution/capability。

该结构必须：

- 使用固定宽度类型；
- 不包含指针、锁、内核地址或编译配置相关对象；
- 布局有编译期断言；
- 按读取热点进行 cache-line 审查；
- 只保存 reader 必需字段。

### 4.3 Global shared page

```text
seq + ABI header + canonical read state + 必要低频全局数据
```

- kernel 可写；
- user R--/NX；
- producer 先完成私有计算，再短时间发布；
- 初版优先采用固定尺寸同类型复制；
- 不为追求零复制而延长 seq 奇数窗口。

### 4.4 Per-MM context data

继续独立保存：

- ABI version；
- time namespace clock mask；
- monotonic offset；
- boottime offset。

它通过 VVAR 式 special mapping 建立，用户只读。地址仍通过当前 ABI 显式提供，
不与 global shared page 合并。

### 4.5 Environment context

PVClock/Hyper-V 页面地址和 fallback mode 属于地址空间相关依赖，不写入全局
shared data。kernel wrapper 和 user wrapper 分别提供在自身地址空间有效的地址。

## 5. 目标读取架构

```text
kernel cycles provider ----\
                            +--> shared global-time algorithm
user TSC/PV/HV provider ---/            |
                                         +--> user VKSO ABI
                                         +--> clock_gettime syscall
                                         +--> ktime_get_* wrapper
```

算法负责：

- seq begin/retry；
- cycles delta；
- mult/shift 换算；
- base、coarse 和 namespace offset；
- timespec 归一化。

cycles provider 负责环境相关的计数器读取。热路径不能引入不必要的间接调用；
REALTIME、MONOTONIC 等常用 clock 保留编译期专门化入口。

## 6. Dispatcher 与 backend

统一 dispatcher 按功能分类：

- global clocks：共享 core；
- process/thread CPU clocks：CPU backend；
- realtime/boottime alarm clocks：alarm backend；
- dynamic/FD/PTP clocks：设备 backend；
- 无效 ID：保持 Raw kernel 错误语义。

共享 core 只返回统一状态，不直接决定 user syscall 或 kernel backend：

- `OK`
- `UNSUPPORTED`
- `BACKEND_REQUIRED`

user wrapper 只有一个 syscall fallback 出口；kernel dispatcher 只有一个 backend
出口。global clock 正常路径不得再次调用旧 `ktime_get_*` 算法。

## 7. ABI 与并发不变量

任何阶段都必须保持：

1. syscall 和标准用户 ABI 不变；
2. `ktime_get_*` 名称、类型、导出符号和 root namespace 语义不变；
3. time namespace 只在明确的 per-MM 路径应用；
4. seq 奇数表示正在发布，payload 读取必须位于两次 seq 检查之间；
5. NMI/IRQ/writer-locked reader 不得等待被自己打断的 writer；
6. shared page 不泄漏 kernel 指针或 private 数据；
7. user 映射始终 R--/NX；
8. unsupported clock、alarm、CPU clock 和无效 ID 与 Raw 语义一致；
9. early boot、suspend/resume 和 clocksource 切换有有效路径；
10. ABI layout 变化必须提升内部 ABI version，并同步 wrapper 与测试。

## 8. 分阶段实施

### M00：保护基线和建立证据

- [x] 创建独立 Git 分支。
- [x] 记录起点提交和受保护 tag。
- [ ] 保存当前功能、read、update 和并发结果索引。
- [ ] 确认工作目录只修改 `linux-5.15.198-vkso` 和本计划目录。

退出条件：基线可重复定位，工作树无来源不明修改。

### M01：字段和调用上下文审计

- [ ] 建立现有 `struct timekeeper` 字段读写者矩阵。
- [ ] 将字段分类为 private、canonical read、MM data 或无需保留。
- [ ] 建立 reader 上下文矩阵：process、IRQ、NMI、writer-locked、early boot。
- [ ] 标记普通 `ktime_get_*`、fast/NMI reader 和内部 producer reader。
- [ ] 列出 Raw `k_clock` 的 global、CPU、alarm、dynamic backend。

退出条件：每个迁移字段和 reader 都有明确归属，不凭名称批量替换。

### M02：引入 canonical read state，保持行为不变

- [ ] 定义最小 `tk_read_state`。
- [ ] 添加布局、大小、cache-line 和 ABI 断言。
- [ ] 让现有 VKSO shared data 临时适配新类型。
- [ ] 暂不切换 producer、reader 或 syscall。

退出条件：多配置静态编译和现有 QEMU 功能矩阵通过。

### M03：重构 timekeeper private/read 组织

- [ ] 将 reader 必需状态迁入 canonical read state。
- [ ] 将 clocksource 指针、NTP 和 producer-only 字段留在 private。
- [ ] 修改 NTP、settime、TAI、suspend/resume、clocksource switch 更新路径。
- [ ] 保留 writer-locked 私有访问路径，避免 seq 自等待。

退出条件：Raw 对照语义、启动、时间单调性和更新压力测试通过。

### M04：同类型短发布

- [ ] producer 在 private/canonical 状态完成复杂计算。
- [ ] 以短 seq 临界区发布固定尺寸 read state。
- [ ] timezone 等事件型数据保持独立、最小更新。
- [ ] 删除 `timekeeper -> vkso_shared_data` 逐字段类型转换。
- [ ] 测量发布指令、复制字节数和 seq 奇数窗口。

退出条件：转换层删除，update 功能正确，重试率不高于可解释范围。

### M05：共享读取算法适配

- [ ] shared core 只依赖 canonical read state、MM data 和环境 context。
- [ ] cycles provider 与时间换算职责分离。
- [ ] 保留常用 clock 专门化热路径。
- [ ] 集中 core 状态返回，移除分散 fallback。
- [ ] 保持 `__vkso_*` 对外 ABI。

退出条件：七种 global clock、time/gettimeofday/getres/getcpu 功能矩阵通过。

### M06：普通 kernel reader 统一

- [ ] 将可安全迁移的普通 `ktime_get_*` 改为共享 core 薄 wrapper。
- [ ] 保持 root namespace 语义和返回类型。
- [ ] 保留 fast/NMI、writer-locked 和 early-boot 专用 reader。
- [ ] 不修改现有调用者源码，除非存在明确语义错误。

退出条件：内核启动、模块符号、IRQ/NMI审计和功能压力测试通过。

### M07：clock_gettime dispatcher/backend 重构

- [ ] global clock 直接调用共享 core。
- [ ] CPU、alarm、dynamic/PTP 继续调用专用 backend。
- [ ] 用户入口集中 syscall fallback。
- [ ] kernel 入口集中 backend dispatch。
- [ ] 验证无效 ID、NULL、alarm 无 RTC 和动态 clock 语义。

退出条件：与 Raw 的完整 clock/getres 错误及 fallback 语义一致。

### M08：清理与代码规模复核

- [ ] 删除无调用的旧 global reader 算法主体。
- [ ] 删除失效适配、重复结构和临时兼容代码。
- [ ] 保留必要 ABI wrapper、backend 和 common infrastructure。
- [ ] 人工审计源码归属，再使用脚本做算术复核。

退出条件：无死代码、无重复统计、代码结构可读。

### M09：功能与构建验证

- [ ] 默认实验配置构建。
- [ ] TIME_NS 开/关构建。
- [ ] TSC 实际功能验证。
- [ ] PVClock/Hyper-V 静态编译验证。
- [ ] QEMU ABI/功能矩阵。
- [ ] seq 并发、settime、namespace、fork/exec、多线程测试。
- [ ] 检查 shared/MM VMA 权限和页面内容。

退出条件：所有必需功能通过，warning 和失败项有明确结论。

### M10：性能与论文证据

- [ ] bare-metal user read。
- [ ] bare-metal syscall/kernel read。
- [ ] update-side。
- [ ] read/update 并发。
- [ ] retry、fallback 和代码尺寸。
- [ ] 与 Raw、temporary-final baseline 和新版本统一比较。

退出条件：功能正确，性能变化可解释，源码和机器码证据可复算。

## 9. 提交与回退规则

- 每个 M 阶段至少一个独立提交，不跨阶段混合功能。
- 类型引入、producer迁移、reader迁移、dispatcher迁移和清理分别提交。
- 每个提交说明影响的ABI、热路径、update路径和验证结果。
- 功能未通过不得进入下一阶段。
- 性能实验前创建可定位tag，不覆盖历史结果。
- 发现不可解释的性能回退时，先定位阶段提交，不在其上叠加补丁。

## 10. 成功判据

重构完成必须同时满足：

1. global-time kernel/user算法只有一份；
2. `ktime_get_*` 兼容ABI保留，普通reader成为薄wrapper；
3. timekeeper private/shared职责明确；
4. 不再存在逐字段类型转换适配层；
5. shared发布短且同步协议正确；
6. fallback集中，CPU/alarm/dynamic backend完整；
7. user功能不低于Raw vDSO，kernel语义不低于Raw kernel；
8. reader性能不出现不可解释的普遍退化；
9. update和并发性能有可复现实验结果；
10. 源码工作量统计不重不漏，并区分专属、共享、兼容和通用机制。
