# BCH evaluation results

正式实验在 CPU 2 上、同一进程及一次部署内执行 11 个 outer rounds，每个计时样本目标 10 ms；测试
`m=13,t=4` 和 `m=13,t=8`，数据长度均为 512 bytes。三种实现对两组参数生成完全
相同的 ECC；每组 128 个随机向量、每个 0 到 `t` 的错误数、两条 decode 路径均
通过错误位置和完整 codeword 恢复验证。导出 DSO 的接口、shim dependencies、
helper relocations、绝对 text relocation 和 reusable page map 审计全部 PASS。

## 主要结论

- 对同源 `kernel-native`，`kernel-vkso` 的 encode 基本持平：m13t4 为 0.984x，
  m13t8 为 1.001x（matched-run latency ratio）。
- m13t4 的完整 decode 在 0～4 个错误下为 0.972x～0.992x，导出版本没有可见
  额外开销。
- m13t8 的完整 decode 在 0～8 个错误下为 1.003x～1.054x；高纠错强度下导出
  版本约慢 0.3%～5.4%。
- m13t8 的 precomputed decode 对 1～8 个错误为 1.055x～1.209x，其中 2-error
  case 的 1.209x 是最大差异；0-error fast path 为 0.988x。该路径本身很短，
  helper/布局和频率噪声更容易被放大，不能把单个 case 解读成统一算法差距。
- 相比作者 standalone，导出版本并非系统性更慢：encode 和多数 full-decode
  cases 持平或更快；高错误数的 precomputed decode 则约慢 7%～10%。作者版本
  与 Linux 5.15 并非同一份 source，且使用 `-O3 -mtune=native`，因此这组差异是
  实现对比，不是纯 vkso overhead。

总体上，这次实验说明较大的、纯标量 BCH 解析/纠错闭包可以按项目规范导出，
保持完整功能语义；与相同内核实现的普通用户态编译相比，大多数端到端路径处于
约 ±5% 范围。逐项中位数和比值见
[`results/summary.md`](results/summary.md)，原始数据见
[`results/raw.csv`](results/raw.csv)。
