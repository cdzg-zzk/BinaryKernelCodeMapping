# public-direct-v1 验证记录

本次变更基于 43c60fc68a6ec6bed5b8131927f7c17100b2f20c。验证对象是公开用户入口、基准程序、构建/采集/汇总逻辑与失败清理保护，不是完整内核验收。

## 已实际执行

同一份最终源码分别使用 GCC 14.2.0 和 Clang 17.0.0 编译并执行 tests/test_public.py。两次结果相同：26 项 unittest，25 项通过，1 项明确 SKIP。SKIP 的原因是当前宿主 CLOCK_REALTIME_ALARM 返回 EINVAL；没有把它从正式目标矩阵删除。

原始命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B test/test_gettime/vkso-tests/public-api/tests/test_public.py
CC=clang PYTHONDONTWRITEBYTECODE=1 python3 -B test/test_gettime/vkso-tests/public-api/tests/test_public.py
```

覆盖范围包含：原生 libc/vDSO 的 16 条受支持路径本地 smoke、快路径拒绝时间 syscall 的诊断（带强制 syscall 正向控制）、ELF 链接/符号检查、原始 CSV 完整性、四组 boot 级汇总、平衡次序、打包流程和清理错误分支。

原有真实 vkso_user_entry.S 与测试替身 core 组合执行了 37 项 C 断言，覆盖初始化失败、ABI、errno、负时间值、上下文和 syscall 失败出口。测试替身不是内核共享代码；模拟 manager 命令也没有操作实际模块。打包 admission 模拟只验证编译/归档管线，不产生可部署内核包。

本地宿主为 Linux 6.18.44，Python 3.11.8、GNU Binutils 2.44。编译所需基线依赖使用与仓库对象匹配的文件；没有完整 Linux 内核 checkout/构建。下载交付包中的 validation/gcc-tests.log、clang-tests.log、environment.json 和 tested-source-blobs.json 保留详细记录。

## 未执行，不能标为 PASS

| 项目 | 状态 |
|---|---|
| GCC 11.4.0 下四镜像和新公开程序的完整目标构建 | NOT_RUN |
| Linux 5.15.198 中真实 grafted VKSO 的公开 API 执行 | NOT_RUN |
| 新版目标包的物理代码页身份、namespace/fork/exec 生命周期 | NOT_RUN |
| 原物理机四配置、多个独立启动的正式性能采集 | NOT_RUN |
| 内核 reader/publisher 的两端成本 | NOT_RUN，本次没有重写其原有流程 |
| Redis 新性能 | NOT_RUN，Redis 已退出本轮主流程 |

没有加载实验模块、安装内核、修改 GRUB 或重启目标机。目标 collector 保留原内核身份/配置/clocksource/ABI matrix 检查；正式 17 路径中任何失败都会拒绝完成，不把局部 smoke 结果作为完整实验。

本地通过只支撑上述范围。合并为正式实验版本前，仍应在目标工具链和受控内核启动下完成 README 中的验收。
