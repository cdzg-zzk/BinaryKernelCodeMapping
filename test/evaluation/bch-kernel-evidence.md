# BCH：实际 owner 的内核端对照与采集验证

2026-09-12，两个独立的私有 `5.15.0-119-generic` guest 会话完成了三组内核端对照的完整功能验证，并验证了完整计时采集入口。三组分别调用 Ubuntu119 stock 模块、完整未适配源码的匹配编译模块，以及当前实际 `vkso_bch` owner 的公开 API。没有修改原 owner、页面注册、checker、exporter 或 shim，也没有在 host 装载模块。

## 对照与覆盖

| 后端 | 实际执行体 | 比较口径 |
| --- | --- | --- |
| `stock-kernel` | 已安装的 Ubuntu `bch.ko`，包版本 `5.15.0-119.129` | 发行构建的整体参照；包含编译条件和未排除的源版本差异 |
| `matched-source-kernel` | 完整 vendored `lib/bch.c`，四个 API 改名为 `matched_bch_*` | 与 owner 使用相同算法编译选项，用于观察已知源码适配差异 |
| `owner-kernel` | 从未修改的当前源码重新构建的 `vkso_bch.ko` | 直接执行实际 export owner 的四个公开 API |

每次构建都比较 matched 与 owner 的实际算法编译命令。除 API/module 命名和构建路径外，全部编译器参数逐 token 一致；记录在各会话的 `compiler-comparison.json`。发行模块的源码与构建边界见[基线证据](bch-kernel-baselines.md)，不能把 stock 比值解释为单独的 PGOT 或页面映射成本。

每个会话都执行 m=13、t=4/8、512-byte payload 加 parity、各 128 轮错误位置试验、全部 0..t 错误数、三个 backend 和 full/precomputed 两种 decode。每个 backend 独立创建和释放控制对象。两条路径共用同一组受损 codeword，核对 ECC、完整错误位置集合和翻转后的整个 codeword。

每个会话有 **10,752 次 decode 检查、3,588 次 parity 比较和六次几何参数检查**。1,792 个 correctness input IDs 表示参数/试验/错误数的组合，不代表 1,792 个独立 payload 或互不相同的错误向量；每种 t 使用一个固定种子的 payload。原始 `driver-vectors.txt` 保存每个 backend/mode 的注入位置、返回位置及恢复结果。

## 实际会话

| 会话 | 结果与范围 |
| --- | --- |
| attempt01 | FAIL：BusyBox `taskset` 不支持 `-c`，在装载测试 driver 之前退出；三个 provider 正常卸载，未进入算法测试 |
| attempt02，boot `0c6e1694-7934-453a-a237-5721bcb17fb2` | PASS：Python 设置 CPU 1 亲和性，`measure=0` 完整功能矩阵通过；没有计时行 |
| attempt03，boot `b7351b52-e736-4114-86c9-56479812f22c` | PASS：再次完成全部功能检查，再以 `measure=1 outer_runs=11 sample_ms=10` 验证完整 1,056 行采集矩阵 |

两个完成会话均记录 12 个实际 API 指针，并与本次 guest 的公开符号及其 `bch`、`bch_matched`、`vkso_bch` 模块归属逐项匹配。三个 provider 的 refcnt 在 driver 装载前为 0、装载后为 1、卸载 driver 后回到 0，随后 provider 全部正常卸载。该引用来自测试 driver 的普通模块依赖；本实验没有页面注册，不能作为注册机制已经独立 pin owner 的证据。

两个 guest 均正常退出，没有 kernel BUG/WARNING/panic。所有加载、卸载、原始 dmesg、模块布局、API 归属及构建记录均已保留。attempt01 的失败状态和原始输入不覆盖、不合并为成功会话。

## 计时与验收范围

完整采集覆盖每个 t 的 init（包括 free）、encode、全部错误数的 full/precomputed decode，三个 backend 按 round/case/mode/errors 轮换次序。相同 round/t/error 的两种 decode 使用相同的已记录向量。校准、准备和预热在正式间隔外，时钟是 `ktime_get_ns` 的 wall time；driver 不禁用 IRQ 或 preemption，结果保留起止 CPU、总 ns 和迭代次数。

10 ms 是校准目标，不是每行耗时下界。此次 guest 的实际总间隔为 460,908–32,653,487 ns，全部保留。它们验证采集流程和记录完整性，不加入论文中的物理机性能表，也不与用户端 `CLOCK_PROCESS_CPUTIME_ID` 的旧结果直接相减。

[独立记录审计器](bch_kernel_audit.py)在 guest 和 host 分别重放：重建全部种子/错误位置、逐 backend/mode 返回位置集合、计时矩阵、轮转顺序、CPU、迭代及跨模式输入配对。两个实际会话均通过。另有 20 个损坏测试组，覆盖缺行、保留总行数的重复、错误位置/恢复状态、错误时钟/CPU/errno、迭代和向量配对；合成测试数据不作为实验结果。

下一步是在基础实现稳定后，按 C 类计划采集隔离物理机上的完整部署重复及这组三后端对照。当前结果补齐内核端接口、功能和可用采集入口，尚未给出实际 owner 的正式内核成本，也未解释用户端 BCH 退化的指令或布局原因。

## 复现与归档

完整 guest 入口（使用已准备的私有119内核/initramfs，输出目录必须不存在）：

```sh
python3 test/evaluation/bch_kernel_qemu.py --output /tmp/bch-kernel-functional
python3 test/evaluation/bch_kernel_qemu.py --output /tmp/bch-kernel-collector --measure
```

归档在 [`results/bch-kernel-validation-20260912/`](results/bch-kernel-validation-20260912/)，包含三个原尝试的选定源码、实际模块、编译命令、原始记录与失败日志。磁盘镜像和共用 kernel/initramfs 留在本地运行目录，归档记录其来源与身份，不重复打包。解包后的目录可直接用审计器重放，具体命令见归档 README。
