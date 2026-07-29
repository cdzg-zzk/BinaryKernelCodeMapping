# M01 clock backend 与错误语义矩阵

## 1. 分派规则

Linux 5.15.198 的 `clockid_to_kclock()` 规则：

```text
id >= 0 && id < ARRAY_SIZE(posix_clocks)
    -> posix_clocks[id]（空项为 invalid）
id < 0 && (id & CLOCKFD_MASK) == CLOCKFD
    -> dynamic/FD backend
id < 0 && 非 CLOCKFD
    -> encoded CPU-clock backend
其他
    -> invalid
```

VKSO 目标分派：

```text
public user/kernel ABI
  -> 支持的 global ID：typed shared reader
  -> 其他 ID：唯一 cold backend/fallback
```

shared core 不负责权限、fd、RTC、task lifetime 或 syscall。

## 2. `clock_gettime` clockid 矩阵

| ID | 名称 | Raw/kernel backend | VKSO 用户路径 | VKSO kernel/syscall 目标 | namespace |
|---:|---|---|---|---|---|
| 0 | `CLOCK_REALTIME` | realtime global | direct shared | direct typed shared | 无 offset |
| 1 | `CLOCK_MONOTONIC` | monotonic global | direct shared | direct typed shared | monotonic |
| 2 | `CLOCK_PROCESS_CPUTIME_ID` | `clock_process` | syscall | cold CPU backend | task CPU |
| 3 | `CLOCK_THREAD_CPUTIME_ID` | `clock_thread` | syscall | cold CPU backend | thread CPU |
| 4 | `CLOCK_MONOTONIC_RAW` | raw global | direct shared | direct typed shared | monotonic offset，保持当前 Raw 语义 |
| 5 | `CLOCK_REALTIME_COARSE` | realtime coarse | direct shared | direct typed shared | 无 offset |
| 6 | `CLOCK_MONOTONIC_COARSE` | monotonic coarse | direct shared | direct typed shared | monotonic |
| 7 | `CLOCK_BOOTTIME` | boottime global | direct shared | direct typed shared | boottime |
| 8 | `CLOCK_REALTIME_ALARM` | `alarm_clock` | syscall | cold alarm backend | alarm base |
| 9 | `CLOCK_BOOTTIME_ALARM` | `alarm_clock` | syscall | cold alarm backend | boottime |
| 10 | `CLOCK_SGI_CYCLE`/空槽 | 无 | syscall | invalid | 无 |
| 11 | `CLOCK_TAI` | TAI global | direct shared | direct typed shared | 无 offset |
| >11 | 未定义正 ID | 无 | syscall | invalid | 无 |
| negative CLOCKFD | dynamic/PTP | `clock_posix_dynamic` | syscall | cold device backend | driver |
| negative CPU encoding | process/thread CPU | `clock_posix_cpu` | syscall | cold CPU backend | task |

### 2.1 global 成功语义

- 返回 0；
- `timespec64` 已归一化；
- public syscall 在 core 成功后才 `put_timespec64()`；
- 用户地址无效时 syscall 返回 `-EFAULT`；
- 用户 shared entry 与 vDSO 一样直接写用户传入地址，非法地址由用户异常语义
  处理，不把 copy_to_user 引入共享 core；
- provider/mode 不可用时用户进入 syscall，kernel进入自身 backend/旧安全路径，
  不能返回伪时间。

## 3. `clock_getres` 矩阵

| clock 类别 | resolution 来源 | `tp == NULL` | 失败语义 |
|---|---|---|---|
| global hres：0/1/4/7/11 | `hrtimer_resolution` | 验证 clock 后成功，不写内存 | 无 |
| global coarse：5/6 | `LOW_RES_NSEC` | 验证 clock 后成功 | 无 |
| process/thread CPU | CPU backend；sched clock通常 1ns，其余约 `1/HZ` | backend仍做权限/ID验证 | 保留 backend errno |
| alarm：8/9 | `hrtimer_resolution` | 仍检查 RTC | 无 RTC 时 `-EINVAL` |
| dynamic/PTP | driver `clock_getres` op | 仍做 fd/driver 验证 | fd/权限/无 op 的原错误 |
| invalid | 无 | 仍失败 | `-EINVAL` |

`clock_getres(NULL)` 不是“不执行任何路径”：它只是不复制结果，clockid 和 backend
仍必须验证。VKSO direct global 可以不写 output，但 unsupported ID 必须 fallback。

## 4. backend 细节

### 4.1 CPU clocks

保留：

- encoded PID/TID 与 `CPUCLOCK_WHICH` 校验；
- task 查找和 lifetime；
- 跨进程/线程权限；
- PROF/VIRT/SCHED 不同采样；
- `-EINVAL`、`-ESRCH`、权限错误等现有返回；
- process/thread 固定 ID 到 encoded clock 的转换。

不能将 CPU time 放入 global shared_data：它不是全局状态，且每 task/thread
变化，更新频率和权限模型完全不同。

### 4.2 alarm clocks

保留：

- `alarmtimer_get_rtcdev()` 可用性检查；
- 无 RTC 返回 `-EINVAL`；
- realtime/boottime alarm base 的 namespace 语义；
- timer/nanosleep/wakeup 相关 `k_clock` 操作。

即使 `CLOCK_REALTIME_ALARM` 的“当前时间”与 realtime 接近，也不能绕过 RTC
存在性检查直接从 shared realtime 返回。

### 4.3 dynamic/PTP

保留：

- clockid→fd 解码；
- fd lookup 和 `posix_clock` lifetime；
- file mode/权限；
- driver `clock_gettime/getres` op；
- `-EBADF`、`-EACCES`、`-EOPNOTSUPP` 和 driver error。

该路径天然是 cold 间接调用，不属于 global reader 优化目标。

### 4.4 invalid

- 正 ID 越界或 `posix_clocks[]` 空槽：`-EINVAL`；
- 用户 VKSO 必须通过 syscall 获得完全一致的错误；
- kernel generic dispatcher 可直接返回相同错误，但不能让位移、位图或数组索引
  对负数/大数产生 UB；
- 位图使用前必须先做无符号范围检查。

## 5. `time()` 与 `gettimeofday()`

### `time()`

- 用户 `time(NULL)` 和 `time(&value)` 从 naturally aligned realtime seconds
  单次读取；
- syscall 保持 `put_user`/`-EFAULT` 和
  `force_successful_syscall_return()`；
- 不因 high-resolution provider 不可用而 fallback，因为 seconds/coarse 状态
  始终可读。

### `gettimeofday()`

四种参数组合都保留：

| `tv` | `tz` | 行为 |
|---|---|---|
| non-NULL | non-NULL | realtime hres + timezone |
| non-NULL | NULL | realtime hres |
| NULL | non-NULL | timezone |
| NULL | NULL | 成功返回0，不要求 cycles provider |

timezone 是事件型全局数据，不属于 time namespace；设置范围校验和首次 warp
语义仍在 syscall producer 侧。

## 6. 当前重复与 M07 目标

当前存在两层 fallback 政策：

- assembly public wrapper 对 unsupported clock 直接 syscall；
- shared C core 还通过 `context->fallback_mode` 决定 syscall 或返回 fallback；
- kernel syscall 对 fallback 再调用 `clockid_to_kclock()`。

目标：

- M05 纯 core 不执行 syscall、不读取 fallback mode；
- user public wrapper 是唯一 syscall fallback；
- kernel global typed path不走 `k_clock`；
- kernel generic dispatcher 对 CPU/alarm/dynamic 进入唯一 backend；
- backend 不重新调用 shared global core。

位图适合 `clock_getres` 这种“范围检查后按类别选择常量结果”的路径；七个
`clock_gettime` 的常用 typed entry 继续直接跳转，不用位图制造额外间接分派。

## 7. 验证矩阵

M02～M09 的功能矩阵必须至少覆盖：

- 七个 global clock；
- process/thread CPU 固定 ID；
- encoded self/other CPU clock；
- realtime/boottime alarm 有 RTC 与无 RTC；
- 合法 dynamic clock、无效 fd、无对应 op；
- ID 10、12、`INT_MAX`、`-1` 和构造的非法 negative ID；
- `clock_getres` output non-NULL/NULL；
- `clock_gettime` output invalid address；
- provider unsupported/invalid mode；
- `gettimeofday` 四种 NULL 组合；
- `time(NULL)`、`time(&value)`、无效地址 syscall；
- root/non-root time namespace。

任何 errno 或 fallback 次数差异都视为语义失败，而不是性能优化。
