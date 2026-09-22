# Evaluation 基础修订：按共同修改对象审阅

状态（2026-09-12）：导出器直接调用拒绝、显式私有数据 binding、LZ4 bridge 与 runner 集成已在工作树实施并完成离线构建/合成验证，修改后 LZ4 的完整 guest CLI 也已通过。逐批次完成确认与错误传播已通过 guest 验证；cooperative owner pinning 已通过 LZ4 生命周期及完整应用验证；v3 完整计划、300 页跨批次回滚、QUERY 和恢复重试已实测；槽位内替换、启动中断恢复及三算法新 runtime 已通过，manager 链接产物身份核对已通过，其余边界仍待完成。现有 Clocktime 实验、原始结果、BCH/XZ 功能与 BCH 资源观测分别保留其实际构建身份。

这次需要修改基础实现的原因是：注册部分失败没有回滚、manager 成功状态不反映内核结果、owner 未被独立 pin；LZ4 导出则遗漏了直接调用目标，完整 CLI 无法完成首个压缩操作。新增重复次数不能修复这些问题。按文件与构建依赖，将实施分为两组。

## 分析与导出工具

共同文件：`kernel_cgd/function_checker/functions_checker.py`、`make_dll/build_PIC_so.py`、`vkso` 及配置/身份记录。

| 改动 | 具体行为 | 已有可审阅材料 |
| --- | --- | --- |
| ELF 符号查询缓存 | 保持符号顺序、首匹配和判定规则，避免每次直接目标查询重新扫描整个 ELF 符号表 | [缓存补丁与等价性验证](README.md) |
| 共享 text 的 Shim 引用判定 | 对没有实际重绑定位置的直接引用准确拒绝；checker 与 exporter 使用一致口径 | [机器码案例和真实 owner/KRG 重放](export-direct-calls.md) |
| 显式私有数据绑定 | 为明确的 owner slot 验证原始初始化和私有数据位置，只将该 DSO 数据重定位绑定到指定用户 helper；透传并归档 binding contract | [LZ4 绑定契约及集成说明](lz4-helper-binding.md) |

缓存补丁、拒绝补丁和数据绑定的通用 builder/vkso 集成均已独立验证；准确拒绝或离线构建本身不算 LZ4 应用通过。

**长任务记录：** 原八例检查的中断快照和日志已保存；没有覆盖旧输出，也没有混用修改前后的 checker。修订 checker 随后在新目录完成固定八例，结果见 [revised batch](../results/applicability-revised-20260912/README.md)。

## 注册会话与 owner 构建

共同文件：`page_cache_replace/`、`vkso`、三个 owner 的注册元数据，以及 LZ4 owner、现有 shim 和对应 runner 的配置。当前 v3 将批次注册改为按完整事务提交和恢复。

| 改动 | 具体行为 | 已有可审阅材料 |
| --- | --- | --- |
| 注册完成结果 | 已实施实际 errno、完成页数、序号核对及内核/交换计时，移除固定睡眠；失败传播到 runner | [完成通知证据](../registration-completion-evidence.md) |
| Owner 引用与注册事务 | descriptor/pin、完整计划 stage/commit、跨批次回滚及恢复重试已实施并实测；槽位内替换已补齐提交资源；manager 链接产物身份核对已通过，仍需剩余边界 | [统一注册事务方案](registration-transactions.md) |
| LZ4 helper slots | 完整算法的外部 memory-helper 调用经过三个私有 slots；原 kernel 初始化仍指向本次内核 helpers，用户绑定只写自己的数据 | [已实施的 owner 修改与编译证据](lz4-helper-binding.md) |
| 用户 helper 的 ABI 入口 | 在现有 libshim 中提供唯一命名的栈对齐入口，并记录其真实 libc 目标；由上一组的数据绑定契约选择 | [bridge 设计源文件（实际集成见 shim.c）](lz4-helper-binding-user-bridge.c) |

Owner descriptor 必须作为管理页排除在用户导出之外；LZ4 helper slots 则需要保留为用户私有数据，两者不能混为一类。LZ4 候选保留全部 21 个函数，text 增加 160 字节，但选中函数体的静态覆盖由三页变四页，最终页数要从新构建重新确认。ABI bridge 也会影响 shim 的装载与 helper 调用成本。

## 实施后的证据衔接

先在私有 exact119 guest 中验证最终完整实现：注册正常/失败/恢复及 owner 引用行为，LZ4 全部 24 对文件/块配置，BCH/XZ 完整原工作负载，真实绑定与 PFN。新的注册、owner 和 shim 形成同一组明确构建后，再采集相应 B 的 setup/资源账本、C 的完整部署重复和 E 的完整 CLI 工作流。旧表保留其旧构建身份，不能给修改后的实现套用旧性能数字。

物理机正式采集沿用现有 foreground 脚本及其独立条件；本清单不包含新增或重新启用系统服务、修改 host 启动或权限设置。冻结的 Clocktime 20 次实验无需重跑。固定八例已在修订 checker 下完成 8/8 静态重检；修改后的 LZ4 guest runtime 已通过，当前 KVM 可访问；C/E 正式性能仍未采集。
