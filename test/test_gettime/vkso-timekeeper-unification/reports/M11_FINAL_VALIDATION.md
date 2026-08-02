# M11 / O7 最终验证与关闭记录

> 状态：**已完成**。READ、UPDATE、CONCURRENT、正确性、源码规模和
> reader 机器码六类证据均已封存。最终仓库 tag 为
> `vkso-clock-vdso-final-20260802`。

## 1. 最终身份

- 接纳的运行时实现提交：
  `6656f97159339c4b464818e5f38ff31d31e4605e`；
- 集成分支：`master`；
- 最终仓库 tag：`vkso-clock-vdso-final-20260802`；
- Linux：`5.15.198`；编译器：GCC `11.4.0`；
- 最终自包含报告：
  `vkso-tests/VKSO_READ_UPDATE性能报告_20260801.md`。

历史 tag `vkso-o7-final-code-20260731` 冻结的是 O7 执行基线。后续
fallback 边界重构以 package 中的 `source.patch`、source-tree hash 和最终
提交 `6656f97` 三重对应。新 final tag 覆盖已接纳实现、固定后的
实验脚本、最终报告和代码量证据；旧 tag 只作历史基线，不再代表
当前最终结论。

## 2. 完整性与正确性门槛

- normal/no-retpoline 的 Raw/VKSO 四镜像 package 校验：通过；
- 生产和验证配置的 ABI/功能矩阵：通过；
- global clock、CPU/alarm/dynamic/invalid fallback：通过；
- time namespace、clocksource fallback、PVClock/Hyper-V 与只读映射契约：通过；
- early/IRQ/NMI/writer-held 特殊 reader 和 seq 协议自测：通过；
- reusable-text/ITS 构建期 fail-closed 校验：通过；
- 三个最终结果的功能矩阵、stderr、样本数和归档 SHA-256：通过。

## 3. 最终 READ

| 项目 | 值 |
|---|---|
| run ID | `20260801T164548Z-vkso-final` |
| case | normal/no-retpoline × Raw/VKSO，4/4 complete |
| 归档 SHA-256 | `0435f5ad24a5714762fe05f0da5d9f40743a369eea531c35ace6b7b04c7fffe8` |
| 主结论 | 20 个公开入口等权几何平均：Normal `+0.941%`，No-retpoline `-0.275%` |
| fallback | Normal `-0.051%`，No-retpoline `-0.886%`；原有大幅回归已消除 |

仍可见的固定小差距集中在极短 `gettimeofday` 与部分 hres/coarse
路径，绝对量主要为约 1–2 cycles。这不构成继续扩大 ABI、MM 或
wrapper 特化的理由。

## 4. 最终 UPDATE

| 项目 | 值 |
|---|---|
| run ID | `20260731T182559Z-update-side-final` |
| case | normal/no-retpoline × Raw/VKSO，4/4 complete |
| 归档 SHA-256 | `f90e1afdab60c99571b4029368b86266763fef2f35f8fe874f6900775662fc9f` |
| Mean corrected | Normal `-13.176%`，No-retpoline `-4.111%` |
| P99 | 两个变体均降低约 `32.5%` |

Median 分别高 5/4 cycles，而 Mean/P99 更好，表示 writer 分布和长尾改善，
不表示每一次 update 都更快。早期 tar 权限错误发生在原始 CSV 写完之后；
修复所有权后的归档已通过校验，计时数据未受影响。

## 5. 最终 CONCURRENT

| 项目 | 值 |
|---|---|
| run ID | `20260801T173610Z-update-concurrent-final` |
| case | normal/no-retpoline × Raw/VKSO，4/4 complete |
| 归档 SHA-256 | `c61443685106602a160f073e99417a3e32143fcb8559efd649f31d7d502fab7e` |
| reader | 公开 API 窗口与独立 READ 对齐；高精度多 `0.232–2.019 cycles/call` |
| writer | 各场景 Mean corrected 均更低：Normal `3.16%–10.73%`，No-retpoline `1.95%–12.20%` |

seq 微基准中每个成功快照约多 2 cycles，但 retry 更少。该数字只用于
解释发布协议，不等于每个公开 `clock_gettime()` 固定慢 2 cycles。

## 6. 最终代码量与机器码

| 口径 | Raw | 当前 VKSO | VKSO - Raw |
|---|---:|---:|---:|
| 运行时 SLOC | 1,347 | 1,248 | -99（-7.35%） |
| 产品 SLOC | 1,505 | 1,305 | -200（-13.29%） |
| reader closure 机器码 | 2,639 B | 2,055 B | -584 B（-22.13%） |

ITS/reusable-text 通用机制 P1 为 84 SLOC，验证 T1 为 366 SLOC，实验
工具与文档单列，均不混入 1,305 SLOC 产品主表。可复现证据：

- `M11_SOURCE_MANIFEST.tsv` 和 `M11_SOURCE_COUNTS.csv`；
- `FINAL_SOURCE_DELTA.tsv`；
- `M11_BINARY_SYMBOLS.tsv` 和 `FINAL_BINARY_SYMBOLS.tsv`。

## 7. O1–O7 最终状态

| 候选 | 状态 | 结论 |
|---|---|---|
| O1 packed/单遍 dispatch | 回退 | 裸机 reader 回归 |
| O2 namespace/offset 收紧 | 不实施 | 收益不足以承担 core 复制和分支风险 |
| O3 full-width x86 delta | 保留 | 指令/分支减少，cycles 中性 |
| O4 cold backend/tail-entry | 保留 | 成功路径改善，ITS 通用修复正确 |
| fallback 边界重构 | 保留 | native clock 在环境边界早分流，大幅 fallback 回归已消除 |
| O5/O6 | 关闭 | 不为数个 cycles 扩大 ABI/MM/加载器风险 |
| O7 最终验证 | **已完成** | 六类证据完整，统一报告已封存 |

## 8. 关闭结论与后续边界

本轮“以 VKSO 共享 kernel 机器码替代 vDSO 时间读取实现”的研究实验
已完成，当前实现值得保留。在代码和镜像未变化时，不再重复当前
READ/UPDATE/CONCURRENT 批次，也不再继续为 1–2 cycles 修改热路径。

当前尚不是未修改普通应用的系统级透明接管：用户程序仍需要显式
解析 `__vkso_*` 入口并调用 `vkso_user_wrapper_init()`。加载器自动从 auxv
绑定 MM/context 和标准 ABI 透明集成属于 final tag 之后的独立新阶段，
不是 O7 的未完成项。
