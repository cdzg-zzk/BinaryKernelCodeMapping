# BCH evaluation

本目录比较三种 BCH 实现：

1. `kernel-vkso`：由实际加载的 owner LKM 生成 sparse DSO，并在运行时映射
   LKM resident pages；这是论文需要评估的 exported-kernel 版本。
2. `kernel-native`：把同一份、同样适配过的 Linux 5.15 `lib/bch.c` 普通编译成
   用户态 DSO；它用于分离“算法/源代码差异”和“内核页面复用机制”的影响。
3. `author-standalone`：BCH 作者仓库提供的 standalone 用户态实现，按其 Makefile
   风格使用 `-O3 -mtune=native` 编译。

## Benchmark 依据

BCH 没有类似 SPEC 的统一标准 benchmark。这里采用作者仓库自带的
[`Documentation/bch/tu_bench.c`](vendor/parrot-bch/Documentation/bch/tu_bench.c)
作为权威参考，并保留其关键测试定义：

- `m=13,t=4`，以及作者脚本支持的 `m=13,t=8`；
- 数据长度 `(1 << (m - 1)) / 8`，两组均为 512 bytes；
- `CLOCK_PROCESS_CPUTIME_ID` 计时；
- 在 data+ECC codeword 中随机注入 0 到 `t` 个错误；
- 分别测量 encode、使用预计算 ECC difference 的 decode，以及在计时内编码
  受损 payload 并与接收 ECC 异或的完整 decode；两条 decode 路径在 difference
  非零时都继续计算 syndromes、构造错误定位多项式并求根；
- 每个计时样本自适应到至少约 10 ms。

在性能计时前，测试还会验证三种实现生成的 ECC byte-for-byte 相同，并对每个
错误数、两条 decode 路径执行 128 组随机向量，检查返回位置且据此恢复完整
codeword。与原 `tu_bench.c` 相比，这是为了让跨实现性能比较同时具备严格的
功能等价性证据。

性能轮次中，同一路径的三个 backend 使用相同错误向量；full 与 precomputed
路径的种子不同，两条路径的时间差不能作为配对的阶段成本。Decode 计时只到
返回错误位置，位翻转及完整 codeword 恢复检查在计时外。详见
[计时边界与两错误路径核对](../evaluation/bch-decode-path-evidence.md)。

## 前置条件

- 当前运行内核的 headers、debug `vmlinux` 和 `/sys/kernel/btf/vmlinux`；
- GCC、make、pahole、binutils、Python 3、taskset；
- 可使用 sudo 加载/卸载本目录 owner LKM 与项目的 `page_cache_replace`；
- 项目根目录的 `vkso` 工作流可正常执行。

vendored Linux 5.15 与作者 standalone 源码已放在 `vendor/`，正常复现实验不需要
网络下载。

## 执行

正式测试：

```bash
SUDO_PASSWORD='<password>' CPU=2 OUTER_RUNS=11 SAMPLE_MS=10 \
CORRECTNESS_VECTORS=128 ./test/test_BCH/run.sh
```

快速验证：

```bash
SUDO_PASSWORD='<password>' CPU=2 OUTER_RUNS=2 SAMPLE_MS=1 \
CORRECTNESS_VECTORS=16 ./test/test_BCH/run.sh
```

脚本会重新编译 owner LKM、添加 BTF、加载模块、按规范 `vkso exec` 流程构造并
运行 DSO，最后恢复页面并卸载 owner LKM。输出位于 `results/`：

- `summary.md`：中位延迟和 matched-run 比值；
- `raw.csv`、`aggregate.csv`、`paired.csv`：原始、聚合和配对数据；
- `correctness-and-progress.log`：功能正确性结果；
- `kernel-dso-audit.md`：导出接口、shim、重定位和页面映射审计；
- `metadata.txt`：参数、版本、CPU 与源码哈希；
- `kernel-source-adaptation.diff`：内核源文件的完整适配差异。

`kernel-hash-views.txt` 同时保存页面替换生效时的 DSO 视图哈希，以及页面恢复后
sparse 文件视图的哈希；两者不同是 sparse page replacement 的预期语义。

## 结果解释

`vkso/native` 使用同一 outer round 的配对样本计算；大于 1 表示导出版本更慢。
所有 outer rounds 在同一进程、同一次 owner 装载和页面注册中完成；
轮次分布不估计重新部署或重新启动的变化。
正式结果及结论见 [`RESULTS.md`](RESULTS.md)，所有逐项数值见
[`results/summary.md`](results/summary.md)。适配边界见
[`ADAPTATIONS.md`](ADAPTATIONS.md)。
