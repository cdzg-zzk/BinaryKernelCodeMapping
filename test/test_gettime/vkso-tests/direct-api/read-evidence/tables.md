# READ 结果表

单位：TSC ticks/call。Raw/VKSO 为四次启动中位数的中位数；Δ = VKSO − Raw。区间为独立启动精确枚举 bootstrap 的逐项 95% 百分位区间。每个启动包含 31 个批次，每批 500,000 次调用。

## 用户 clock_gettime 快路径

| 配置 | 接口 | Raw | VKSO | Δ | Δ 95% CI | Δ% |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| Retpoline | `clock_gettime_realtime` | 54.188 | 54.211 | +0.023 | [-0.001, +0.110] | +0.042 |
| Retpoline | `clock_gettime_monotonic` | 54.188 | 54.190 | +0.002 | [+0.002, +0.003] | +0.003 |
| Retpoline | `clock_gettime_monotonic_raw` | 54.191 | 54.190 | -0.001 | [-0.002, +0.513] | -0.002 |
| Retpoline | `clock_gettime_boottime` | 54.191 | 55.024 | +0.833 | [+0.722, +0.885] | +1.537 |
| Retpoline | `clock_gettime_tai` | 54.191 | 55.192 | +1.001 | [+0.799, +1.002] | +1.847 |
| Retpoline | `clock_gettime_realtime_coarse` | 15.099 | 16.100 | +1.000 | [+1.000, +1.042] | +6.624 |
| Retpoline | `clock_gettime_monotonic_coarse` | 15.099 | 16.105 | +1.006 | [+1.006, +1.012] | +6.662 |
| No-retpoline | `clock_gettime_realtime` | 54.188 | 53.890 | -0.298 | [-1.002, +0.408] | -0.551 |
| No-retpoline | `clock_gettime_monotonic` | 54.188 | 53.186 | -1.002 | [-1.003, -1.002] | -1.850 |
| No-retpoline | `clock_gettime_monotonic_raw` | 54.192 | 53.186 | -1.006 | [-1.007, -1.004] | -1.856 |
| No-retpoline | `clock_gettime_boottime` | 54.191 | 53.186 | -1.005 | [-1.006, -1.005] | -1.855 |
| No-retpoline | `clock_gettime_tai` | 54.191 | 54.196 | +0.005 | [-0.001, +1.176] | +0.009 |
| No-retpoline | `clock_gettime_realtime_coarse` | 15.099 | 15.095 | -0.004 | [-0.005, -0.003] | -0.027 |
| No-retpoline | `clock_gettime_monotonic_coarse` | 15.099 | 15.098 | -0.001 | [-0.002, +0.000] | -0.004 |

## 其他公开时间快路径

| 配置 | 接口 | Raw | VKSO | Δ | Δ 95% CI | Δ% |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| Retpoline | `clock_getres_realtime` | 15.095 | 13.045 | -2.049 | [-2.050, -2.048] | -13.576 |
| Retpoline | `clock_getres_realtime_coarse` | 14.049 | 13.080 | -0.969 | [-0.969, -0.969] | -6.896 |
| Retpoline | `gettimeofday_tv` | 56.204 | 55.192 | -1.012 | [-1.012, -1.011] | -1.800 |
| Retpoline | `time_null` | 7.024 | 6.021 | -1.003 | [-1.003, -1.003] | -14.284 |
| Retpoline | `time_pointer` | 7.024 | 5.034 | -1.990 | [-1.990, -1.990] | -28.332 |
| No-retpoline | `clock_getres_realtime` | 15.095 | 13.045 | -2.050 | [-2.050, -2.050] | -13.580 |
| No-retpoline | `clock_getres_realtime_coarse` | 14.049 | 13.080 | -0.969 | [-0.969, -0.969] | -6.896 |
| No-retpoline | `gettimeofday_tv` | 56.204 | 55.201 | -1.002 | [-1.003, -1.002] | -1.784 |
| No-retpoline | `time_null` | 7.024 | 6.021 | -1.003 | [-1.003, -1.003] | -14.284 |
| No-retpoline | `time_pointer` | 7.024 | 5.034 | -1.991 | [-1.991, -1.991] | -28.342 |

## getcpu

| 配置 | 接口 | Raw | VKSO | Δ | Δ 95% CI | Δ% |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| Retpoline | `getcpu_both` | 14.049 | 13.045 | -1.004 | [-2.007, -1.003] | -7.144 |
| No-retpoline | `getcpu_both` | 14.049 | 13.045 | -1.004 | [-1.652, -1.003] | -7.144 |

## 用户 fallback

| 配置 | 接口 | Raw | VKSO | Δ | Δ 95% CI | Δ% |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| Retpoline | `clock_gettime_process_cpu_fallback` | 869.619 | 867.344 | -2.276 | [-8.176, -0.316] | -0.262 |
| Retpoline | `clock_getres_process_cpu_fallback` | 591.499 | 589.761 | -1.738 | [-3.302, -0.580] | -0.294 |
| Retpoline | `clock_gettime_realtime_alarm_fallback` | 682.872 | 673.651 | -9.221 | [-11.169, -7.137] | -1.350 |
| No-retpoline | `clock_gettime_process_cpu_fallback` | 843.650 | 841.226 | -2.424 | [-43.209, +2.522] | -0.287 |
| No-retpoline | `clock_getres_process_cpu_fallback` | 574.723 | 571.913 | -2.810 | [-6.349, -0.908] | -0.489 |
| No-retpoline | `clock_gettime_realtime_alarm_fallback` | 669.544 | 664.353 | -5.191 | [-10.477, -2.907] | -0.775 |

## 普通内核 READ

| 配置 | 接口 | Raw | VKSO | Δ | Δ 95% CI | Δ% |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| Retpoline | `monotonic` | 55.197 | 56.195 | +0.998 | [-0.107, +1.000] | +1.809 |
| Retpoline | `monotonic_raw` | 55.704 | 54.189 | -1.516 | [-2.403, -1.011] | -2.721 |
| Retpoline | `monotonic_coarse` | 9.031 | 9.032 | +0.001 | [+0.000, +1.004] | +0.013 |
| No-retpoline | `monotonic` | 58.603 | 55.875 | -2.728 | [-2.961, -0.493] | -4.656 |
| No-retpoline | `monotonic_raw` | 54.195 | 55.282 | +1.087 | [+0.494, +1.397] | +2.006 |
| No-retpoline | `monotonic_coarse` | 11.039 | 9.032 | -2.007 | [-2.009, +0.000] | -18.185 |

