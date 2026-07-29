# VKSO time shared ABI v11

## 1. 目的与边界

ABI v11 只统一 shared global-time 数据布局，不在 M02 改变时间算法、producer
数据来源、fallback 政策、外部 `__vkso_*` ABI 或 MM_data ABI。

本版的结构目标是：

- mono/raw 共用经 M01 证明始终一致的 cycle descriptor；
- mono/raw 只分别保留真正不同的 multiplier 和 base；
- 恢复非全宽 clocksource 正确换算所需的 `mask`；
- realtime 热路径的 seq、cycle descriptor 和 base 位于第一个 cache line；
- monotonic 最多额外访问第二个 cache line；
- monotonic raw base 从 shared offset 128 开始；
- 共享有效 payload 小于一页，不含指针、锁或 kernel-private 状态。

## 2. 精确布局

所有字段采用固定宽度类型，x86-64 kernel、libkernel.so wrapper 和测试镜像均用
编译期断言验证下表。

### 2.1 `vkso_cycle_data`

| Offset | Size | Field | 说明 |
|---:|---:|---|---|
| 0 | 4 | `clock_mode` | TSC/PVClock/Hyper-V/unsupported |
| 4 | 4 | `shift` | 两种 multiplier 共用 |
| 8 | 8 | `cycle_last` | 公共采样基准 |
| 16 | 8 | `mask` | clocksource wrap mask |
| 24 | 4 | `mono_mult` | realtime/mono/boot/TAI |
| 28 | 4 | `raw_mult` | monotonic raw |

结构大小为 32 bytes。

### 2.2 `vkso_read_state`

| Shared offset | State offset | Size | Field |
|---:|---:|---:|---|
| 8 | 0 | 32 | `cycles` |
| 40 | 32 | 16 | `realtime_base` |
| 56 | 48 | 16 | `monotonic_base` |
| 72 | 64 | 16 | `boottime_base` |
| 88 | 80 | 16 | `tai_base` |
| 104 | 96 | 16 | `realtime_coarse` |
| 120 | 112 | 4 | `hrtimer_resolution` |
| 124 | 116 | 4 | `reserved` |
| 128 | 120 | 16 | `monotonic_raw_base` |
| 144 | 136 | 16 | `monotonic_coarse` |
| 160 | 152 | 8 | `timezone` |

`vkso_read_state` 为 160 bytes，`vkso_shared_data` 为 168 bytes：

```text
shared + 0    u32 seq
shared + 4    u32 abi_version
shared + 8    struct vkso_read_state state
```

ABI v10 的有效结构为 184 bytes。v11 在新增 8-byte `mask` 的同时删除第二份
raw `clock_mode/cycle_last/shift` 和相应 padding，净减少 16 bytes。实际映射仍
是一张 4096-byte R--/NX 页，余下空间不承载 private 数据。

## 3. Cache-line 与原子字段约束

以 64-byte cache line 为基准：

- shared 0～63：header、公共 cycle descriptor、完整 realtime base，以及
  monotonic base 的前半部分；
- shared 64～127：monotonic 后半、boottime、TAI、realtime coarse 和
  resolution；
- shared 128～191：raw base、monotonic coarse 和 timezone。

`time()` 使用的 `state.realtime_base.sec` 位于 shared offset 40，是自然对齐的
单次 64-bit load/store。M02 publisher 继续显式 `WRITE_ONCE` 每个字段，不用
可能撕裂该字段的非受控整页复制。

所有 shared 字段均为整数或整数聚合：

- 无 C pointer；
- 无 function pointer；
- 无 lock/seqcount 对象；
- 无 `clocksource *`；
- 无 NTP、leap、suspend 或调试 private 状态。

## 4. 发布与读取协议

M02 继续使用既有标量协议，M04 再把同类型 canonical producer 接入：

### Writer

1. 在 private/local `next` 中完成全部派生计算；
2. `WRITE_ONCE(seq, old + 1)`，将 seq 置奇数；
3. `smp_wmb()`；
4. 逐字段 `WRITE_ONCE` 发布 payload；
5. `smp_wmb()`；
6. `WRITE_ONCE(seq, old + 2)`，将 seq 置偶数。

timezone 是独立事件型字段，只有 timezone 事件更新，不随 periodic tick 重写。

### Reader

1. `READ_ONCE(seq)`，奇数则 `cpu_relax()` 后重试；
2. `smp_rmb()`；
3. `READ_ONCE` 所需 descriptor/base；
4. 读取 cycles 并完成现有换算；
5. `smp_rmb()`；
6. 再次 `READ_ONCE(seq)`，不同则整体重试。

`time()` 与 Raw vDSO 相同，不使用 seq；它只读取上述自然对齐、单 store 发布的
realtime seconds。MM_data v3 保持独立 per-MM 映射和原生命周期协议，不加入
shared seq。

## 5. 单一版本与消费者

ABI v11 的唯一产品定义位于
`linux-5.15.198-vkso/include/vkso/time.h`。同步消费者为：

- kernel compat producer 和 scalar publisher；
- 共享 reader core；
- test-only concurrent sample；
- libkernel.so 手写 wrapper 的 ABI version gate；
- functional ABI matrix；
- bare-metal seq observer。

不保留 v10 结构、兼容 reader 或运行时版本分派。kernel 与 libkernel.so
版本不一致时，wrapper init 以 `EPROTO` 拒绝执行，而不是按错误 offset 读取。

## 6. M02 验证证据

- normal kernel、libkernel.so 和所有用户测试以 `-Werror` 构建通过；
- `CONFIG_TIME_NS=y/n` 静态构建通过；
- `CONFIG_PARAVIRT_CLOCK=y` 的 PVClock 路径构建通过；
- `CONFIG_HYPERV=y`、`CONFIG_HYPERV_TIMER=y` 路径构建通过；
- QEMU Raw/VKSO 各 76 行功能矩阵完全相同；
- `abi_matrix_status=pass`、`guest_status=0`；
- libkernel.so shared segment 是独立 `R` LOAD，未带 `W`/`E`；
- shared page symbol size仍为 4096，v11 有效 payload 为 168 bytes。

验证产物：

- package：`vkso-tests/baremetal/artifacts/unification-m02-abi11`
- QEMU：`vkso-tests/baremetal/artifacts/validation/unification-m02-abi11-rerun`
