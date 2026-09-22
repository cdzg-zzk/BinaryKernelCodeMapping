# Clocktime / VKSO

本项目让 Linux 5.15.198/x86-64 的普通内核时间 reader 与用户路径复用驻留时间计算代码。
当前正式实验是四组 **Raw/VKSO × Normal/no-retpoline** 的完整公开时间 API READ。

从 [执行说明](vkso-tests/direct-api/README.md) 开始；固定入口在 `vkso-tests/baremetal/`。

| 路径 | 用途 |
|---|---|
| `linux-5.15.198-vkso/kernel/time/vkso_time*.c` | 共享时间计算与内核入口 |
| `linux-5.15.198-vkso/arch/x86/kernel/vkso.c` | 用户映射与生命周期 |
| `linux-5.15.198-vkso/kernel/time/namespace.c` | namespace 数据页共享 |
| `vkso-tests/functional/` | carrier 私有入口、context、ABI 验证 |
| `vkso-tests/direct-api/` | 公开 API 库、READ 程序、验证与统计 |
| `vkso-tests/baremetal/` | 构建、安装、启动、收集；结果保留在 results |
| `namespace-sharing/`、`optimization-audit/` | 页共享验证及其依赖的旧基线证据 |
| `vkso-tests/update-bench/` | 独立 UPDATE/读写交互插桩与采集 |
| `vkso-tests/revision/`、`vkso-timekeeper-unification/` | 既有验证工具和历史设计/结果 |
| `history/` | 已停用 Redis 的结果说明；旧源代码在 Git 历史中 |

Raw 使用正常 libc/vDSO；VKSO 应用在启动时初始化并链接公开 API 库，再经 carrier 私有入口进入 grafted 内核页。没有 LD_PRELOAD 或多 provider 桥。历史三方法、Redis 和旧 sidecar 结果不能并入 direct-api-v2。

共享减少了按进程重复的 namespace 元数据页；它不自动证明 API 更快或整机内存低于 vDSO。新实验保留原始样本与每次独立启动身份，据此判断完整部署路径成本。
