# M11 / O7 fallback 性能差异根因

> **历史根因报告。** 本文定量的“syscall 后二次共享分派”已由
> `6656f97` 修复：native clock 现在环境边界直接进入 syscall/`k_clock`，
> 不再先穿过 shared core。最终 fallback 结果为 Normal `-0.051%`、
> No-retpoline `-0.886%`，见 `vkso-tests/VKSO_READ_UPDATE性能报告_20260801.md`。

## 1. 直接结论

O7 READ 中差距最大的 fallback 是 normal 配置下的
`clock_gettime_process_cpu_fallback`：

| 路径 | Raw | VKSO | VKSO - Raw |
|---|---:|---:|---:|
| wrapper 完整路径 | 877.231 cycles | 917.269 cycles | **+40.038 cycles / +4.564%** |
| direct syscall | 868.208 cycles | 902.572 cycles | **+34.365 cycles** |
| 用户态 fallback 外壳差值 | 9.023 cycles | 14.697 cycles | **+5.673 cycles** |

因此，这 40.038 cycles 中：

- **34.365 cycles（85.8%）在进入 syscall 之后产生**；
- **5.673 cycles（14.2%）来自用户态 VKSO fallback 外壳**。

最大差距的主因不是 shim、ITS 物理页导出或 O7 loader。主因是
VKSO 内核在 syscall 边界再次进入共享 reader，对不可在共享页完成的
CPU/alarm clock 经由间接 backend 回到原来的 `k_clock`。Raw 内核则从
syscall 直接进入 `k_clock`。normal 内核中对额外间接边界的
retpoline/ITS 保护又放大了这一差距。

完整路径的 PMU 中位数也一致：VKSO 每次多执行 88 instructions 和
26 branches。branch misses 反而从 Raw 的 0.132978/call 降到 VKSO 的
0.127048/call，所以最大差距不是由新的分支预测失败造成的。

## 2. 拆分方法

同一份 benchmark 对每个 API 同时测量 direct-syscall 和
Raw-vDSO/VKSO-wrapper 两条路径。两条路径使用同一个 `invoke_loop`、
iterations、warmup 和 PMU 计数方式，因此可以把差距拆成：

```text
完整差距 = VKSO wrapper - Raw vDSO
内核差距 = VKSO direct syscall - Raw direct syscall
用户态外壳差距 = 完整差距 - 内核差距
```

这个拆分不把 Raw/VKSO 两个内核的 syscall 实现假定为相同，因而比只比较
wrapper 更能定位根因。数据均为 31 次采样的逐列中位数。

## 3. 三个 fallback 的定量结果

### 3.1 normal

| API | 完整差距 | 内核差距 | 用户态外壳差距 | 内核占比 | 完整路径指令/分支差 |
|---|---:|---:|---:|---:|---:|
| `clock_gettime_process_cpu_fallback` | +40.038 | +34.365 | +5.673 | 85.8% | +88 / +26 |
| `clock_gettime_realtime_alarm_fallback` | +23.779 | +17.832 | +5.946 | 75.0% | +110 / +27 |
| `clock_getres_process_cpu_fallback` | +18.301 | +19.791 | -1.489 | 108.1% | +27 / +13 |

`clock_getres` 的内核占比超过 100% 并不矛盾：VKSO 的用户态 getres
wrapper 比 Raw vDSO 的 fallback 前置分派少约 1.49 cycles，它抵消了一小部分
内核侧差距。

### 3.2 no-retpoline

| API | 完整差距 | 内核差距 | 用户态外壳差距 | 内核占比 |
|---|---:|---:|---:|---:|
| `clock_gettime_process_cpu_fallback` | +18.614 | +11.979 | +6.635 | 64.4% |
| `clock_gettime_realtime_alarm_fallback` | +10.401 | +4.724 | +5.677 | 45.4% |
| `clock_getres_process_cpu_fallback` | +4.687 | +5.712 | -1.024 | 121.9% |

process-CPU 的完整差距从 normal 的 40.038 cycles 降到 no-retpoline
的 18.614 cycles，共减少 21.423 cycles。其中内核差距减少
22.385 cycles，用户态外壳差距反而在约 1 cycle 的反向波动内。这说明
normal 的主要 mitigation 敏感成本位于 **VKSO 内核的额外间接分派**，
不是用户态 shim。

process-CPU direct-syscall 的 PMU 进一步印证这一点：

| 配置 | 内核指令差 | 内核分支差 | 用户态外壳指令差 | 用户态外壳分支差 |
|---|---:|---:|---:|---:|
| normal | +73 | +24 | +15 | +2 |
| no-retpoline | +61 | +11 | +14 | +1 |

normal 比 no-retpoline 在内核差值上额多约 12 instructions/13 branches，
与额外的 mitigation thunk/间接分派边界一致。

## 4. 实际调用路径

`clock_gettime` fallback 在两种内核中的差异是：

```text
Raw
  benchmark 间接调用
    -> raw vDSO clock-id 分派
    -> inline syscall
    -> Raw clock_gettime syscall
    -> clockid_to_kclock
    -> kc->clock_get_timespec

VKSO
  benchmark 间接调用
    -> private veneer（注入 MM/context）
    -> shared vkso_clock_gettime_common
    -> context->clock_gettime_backend（间接）
    -> private syscall backend
    -> VKSO clock_gettime syscall
    -> 取 current->mm 的 VKSO data
    -> shared vkso_clock_gettime_common（第二次）
    -> vkso kernel backend（间接）
    -> clockid_to_kclock
    -> kc->clock_get_timespec
```

用户态 VKSO 的 veneer 仅执行两个地址装载后 tail-jump 到共享 core；
fallback backend 本身也只是 `syscall; ret`。它们解释了稳定的约
5.7–6.6-cycle 用户态外壳差，但解释不了总共 40 cycles 的差距。

内核侧，`posix_clock_gettime_dispatch()` 无条件调用共享 core。对
`CLOCK_PROCESS_CPUTIME_ID` 和 `CLOCK_REALTIME_ALARM`，共享 core 确认它们不属于
hres/coarse 共享时钟后，再通过 context backend 回到 `k_clock`。在原始
5.15.198 路径（仓库基线 `5b7386b`）中，syscall 则直接执行
`clockid_to_kclock()` 和 `kc->clock_get_timespec()`。

`clock_getres_process_cpu_fallback` 也支持同一结论。它的用户态 VKSO
wrapper 不经过 context callback，而是直接 syscall；但 VKSO 仍然慢
18.301 cycles。direct-syscall 测量显示内核本身慢 19.791 cycles，因为
VKSO `clock_getres` syscall 也多了 mask 分派和 cold backend，之后才回到
`k_clock`。

## 5. 为什么 process-CPU 是最大差距

三个 fallback 都显示内核侧多一层分派，但 process-CPU 的内核差距
最大：normal 为 34.365 cycles，alarm 为 17.832 cycles，getres 为
19.791 cycles。

可以确定的是：

- process-CPU 的用户态外壳差仅 5.673 cycles，与 alarm 的
  5.946 cycles 基本相同，所以最大差距不在用户态；
- process-CPU 的内核 direct-syscall 路径比 Raw 多 73 instructions/24 branches；
- 完整路径 branch misses 没有增加，不是分支误预测导致；
- no-retpoline 将该内核差距从 34.365 降到 11.979 cycles，说明
  依赖串行的间接调用保护是主要放大项。

process CPU accounting 的底层 `k_clock` 路径比 alarm 更长，额外间接调用/返回
边界与其依赖链组合后的准确微架构分摊无法仅由当前四个 PMU 事件继续
拆分。若需区分 11.979-cycle no-retpoline 余量中每个 call/return 的成本，
需要内核侧 direct-bypass A/B 或更精细的 call-graph/IBS 测量。这不影响当前
“主要差距在内核二次分派”的结论。

## 6. 这是否是 O7 新回归

不是。

- 当前 Raw process-CPU fallback 相对近期稳健历史中心为 `-0.188%`；
- 最终 VKSO 整个 fallback 组相对上一个 O4 reusable-text 批次为
  `-0.064%`；
- 相对 O3 pre-O4，最终 VKSO fallback 组只有 `+0.677%`。

因此当前 Raw/VKSO 的 fallback 差距是现有共享-dispatch 架构边界，不是
O7 auxv/MM 绑定、ITS reusable-text 或当前 READ 镜像引入的新问题。

## 7. 后续选择

如果 fallback 只是罕见的不支持 clock-id 冷路径，当前最大绝对差为
40 cycles，但相对 877-cycle Raw 路径为 4.56%；它不是 READ 热路径回归，
可以在 UPDATE/并发门槛完成后再决定是否接受。

如果目标是让 fallback 也接近 Raw，最有效的候选不是修改 shim、ITS 或
用户态 loader，而是做一个狭窄的内核 A/B：

- syscall 边界对明确不属于共享 hres/coarse 的 clock-id，直接进入原
  `k_clock` fallback；
- 只有共享可处理的全局时钟才进入 `vkso_clock_gettime_common`；
- 保留 provider failure 与 time-namespace private fallback 的现有语义。

direct-syscall 数据显示该候选针对了 40.038 cycles 中的 34.365 cycles，
而不会改变用户态 READ 热路径。在当前 O7 最终 UPDATE 和并发数据完成前，
本报告不建议立即改代码。

## 8. 证据位置

- 原始 CSV：`vkso-tests/baremetal/results/20260731-o7-final-read/*/perf.csv`
- benchmark 路径选择：`vkso-tests/baremetal/vkso_time_bench.c:518-540`
- benchmark 测量循环：`vkso-tests/baremetal/vkso_time_bench.c:700-761`
- 用户态 veneer/backend：`vkso-tests/functional/vkso_user_entry.S:36-68`
- 共享 clock-gettime core：`linux-5.15.198-vkso/kernel/time/vkso_time_core.c:122-187`
- VKSO 内核 syscall/backend：`linux-5.15.198-vkso/kernel/time/posix-timers.c:60-153,1157-1209`
- Raw vDSO fallback 分派：`linux-5.15.198-vkso/lib/vdso/gettimeofday.c:227-268`
