# 本次交付的验证范围

基线：43c60fc68a6ec6bed5b8131927f7c17100b2f20c。

实际读取了 GitHub 分支与入口/构建/采集代码。容器仍不能 git clone；本地只有修改涉及的源码上下文，不是完整 Linux checkout。`functional/vkso_abi.h`、`vkso_user_wrapper.c`、`vkso_user_wrapper.h` 已逐字重建并核对 Git blob SHA；它们没有被修改，也不在补丁里。

新增源码、头文件、Makefile 和脚本位于 direct-api/。没有修改远端分支，没有构建或安装实验内核，没有执行真实 page-cache replacement。

| 检查 | 本地状态 | 范围 |
|---|---|---|
| GCC 用户态编译与 25 项测试 | PASS | GCC 14，本地依赖与新代码 |
| Clang 用户态编译与同 25 项测试 | PASS | 本地第二编译器；不等于 GCC 11 目标验证 |
| C++ 头文件编译 | PASS | g++，公开头文件与函数声明 |
| Native 快路径功能 | PASS | 本机 libc/vDSO，13 条路径 |
| Native 禁止时间 syscall 诊断 | PASS | 本机独立 seccomp 进程 |
| 完整 Native 矩阵 | BLOCKED | 本机 CLOCK_REALTIME_ALARM 返回 EINVAL；没有替换/删除正式路径 |
| Direct-link ABI、errno、once/TLS | PASS / MOCK | 测试 DSO，不是内核共享代码 |
| 恢复失败/部分 replace 失败处理 | PASS / MOCK | 命令注入测试，没有操作内核模块 |
| CSV 校验与 boot 汇总 | PASS / SYNTHETIC | 结构与统计逻辑，不是实验性能数据 |
| GCC 11.4.0 目标 sidecar 构建 | NOT_RUN | 本地无该工具链/完整原包 |
| Linux 5.15.198 下真实 VKSO 执行 | NOT_RUN | 需要匹配的内核与 carrier |
| 新流程下的实际 PFN/namespace/lifecycle | NOT_RUN | 单独目标验收 |
| 新入口的四配置物理机性能 | NOT_RUN | 本地 smoke 不入论文数据 |
| 内核 reader/publisher 指标 | NOT_RUN | 本轮未改写现有内核测量流程 |

具体编译器版本、原始日志和宿主限制在交付包的 validation/ 下。测试中的多线程/模拟恢复只能支撑调用端和脚本行为，不能推导真实内核保护/生命周期已经通过。
