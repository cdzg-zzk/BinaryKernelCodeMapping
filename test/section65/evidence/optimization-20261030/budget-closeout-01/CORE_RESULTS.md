# Section 6.5 核心结果（额度收缩收尾）

已按用户要求停止扩展，完成当前组并收尾。当前版本是 `optimization-cache-01`；未启用后续低层 FUSE 或 bit-tree 候选，未改论文正文/PDF。

## 实际改动与覆盖

- XZ 字典重复复制采用标量 8 字节复制，保留原有构建/加固设置；内核与用户态复用同一算法。未启用 SIMD 或新增加固放宽。
- 私有 inode/正向名称缓存改为有界 LRU：2048/4096。根和打开的文件/目录保留必要引用；活跃句柄与打开目录列表不计入这两个缓存上限，因此不是整个进程内存上限。
- 原计划 30 组/7692 条，按用户额度要求取按执行顺序完成的前 14 组/4580 条，未按性能结果挑选。未启动的 16 组取消；此前中断的 127 条原始记录保留但排除，完整替代组纳入。
- 覆盖原生 5 种压缩格式、原生顺序读取、普通 gzip/XZ/LZ4 应用、Python 编译、解码器对照、单 CPU 对照。每个比较单元仅 1 或 2 个 campaign，下面均为描述性配对耗时比，不声明原计划三轮置信区间或统计显著性。
- 原始配对、样本计数、重复单元、完整区组、同一启动环境、冻结二进制哈希、9 页 PFN/执行字节身份及恢复/卸载状态均已核验；423 个比较的点估计经第二种遍历计算复核。

## 性能

百分比为 `(新耗时/对照耗时 - 1)×100%`；先在 campaign 内求配对对数比均值，再给 campaign 等权。

| 工作负载 | 对照 | 本轮耗时变化 | 完整配对数 / campaign 数 |
|---|---|---:|---:|
| 原生 XZ 顺序 archive，fresh-mount | 优化前 prepared-XZ | −27.06% | 16 / 2 |
| 同一原生工作负载，warm | 优化前 prepared-XZ | −0.46% | 16 / 2 |
| 普通 XZ startup | stock | −43.81% | 24 / 2 |
| 普通 XZ archive | stock | −19.24% | 24 / 2 |
| 普通 XZ scan | stock | −54.56% | 24 / 2 |
| 普通 XZ stream | stock | −3.43% | 24 / 2 |
| Python/XZ compile | stock | **+16.38%** | 8 / 1 |
| Python/XZ compile | 匹配缓存的 LKL | **+7.04%** | 8 / 1 |
| Python/XZ compile | 同代码 copied | +0.32% | 8 / 1 |
| 普通 LZ4 stream | 同代码 copied | **+6.22%** | 12 / 1 |

普通 gzip 相对 stock：startup +1.27%，archive −4.41%，scan −6.30%，stream −5.30%。普通 LZ4 相对 stock：startup −2.32%，archive −2.62%，scan −5.35%，stream −6.37%。完整 423 项含不利结果见 `analysis.json`，没有剔除离群值。

归因边界：本轮标量复制优化在 fresh-mount 原生 XZ 顺序工作负载有效，warm 下几乎无变化，与减少重复数据解码工作一致；这是该工作负载的证据，不是所有 XZ 数据都会同样加速。普通 XZ 的 shared/copied 四个工作负载耗时差在 −0.05%～+0.65%，因此相对 stock 的大部分差异不能直接归因于物理共享。Python/XZ 的 shared/copied 接近，而二者相对 stock 都慢，进一步定位仍未完成。LZ4 stream 的 shared/copied +6.22% 保留为未解决点，不能用仅一轮数据认定为固定机制开销。原生五格式多数小幅变化，完整表也保留了 warm zstd scan 约 +4% 等回退点。

## 内存与磁盘

以下为已有未计时规模测试的 helper PSS 快照，单位 KiB，不是峰值、重复均值或整个机器总内存。

| 规模 | copied 无界缓存 | copied 有界缓存 | VKSO 有界缓存 | stock | stock-single |
|---|---:|---:|---:|---:|---:|
| 1× | 7183 | 4275 | 4279 | 16742 | 12196 |
| 4× | 23964 | 7436 | 7452 | 27183 | 13488 |
| 16× | 91004 | 19886 | 19899 | 28892 | 13199 |

16× 的有界/无界 copied 配对约下降 **78.1%**：这是私有缓存优化收益，不是代码共享收益。VKSO 仍随目录规模增长，且 16× 高于 stock-single；保存的映射显示 heap 约 2.3 MiB，而其他匿名 PSS 从约 1.5 增至 16.7 MiB。匿名分配的所有者未实测定位，不能宣称整个进程内存已变为常数。

真正共享的代码/只读页是 9 页，即 **36 KiB**，逐页 PFN 与 mapped-byte 对照成立。业务 owner 常驻 68 KiB、native consumer 40 KiB；本轮捆绑相同 XZ 的 native 参考模块为 72 KiB，原先调用宿主解码器的参考模块为 60 KiB，边界不同。平台模块 32 KiB 是单独前提；构建观察器 20 KiB 不属于最小运行部署。不能把省下的 36 KiB 直接宣布为整机净收益。

实际磁盘分配（`st_blocks`，不是逻辑文件长度）：carrier 28 KiB，materialized copied core 64 KiB。包含相同 bridge/frontend/helper 后：

- 已准备的 native 部署：shared **288 KiB**，copied **324 KiB**，少 36 KiB。
- 纯用户态业务部署：shared **228 KiB**，copied **184 KiB**，反而多 44 KiB，因为需要 owner。

以上使用实际未剥离调试信息的文件，按 inode 去重；共同平台、动态依赖和应用镜像均不在这两个业务文件小计内，也没有证明它们可删除或减少。构建树、历史结果、诊断副本属于实验存储，不等于必要部署成本。详细分解见 `resource-ledger.json`。

## 正确性与结束状态

已有候选验证包括：65536 字典状态与 244 个有效流检查；8192 文件、三轮缓存 churn、828 次内容核对及 2400 活跃句柄；私有 adapter ASAN/UBSAN；真实 FUSE 句柄/游标生命周期；30 个有效格式挂载；客体中畸形镜像 EIO 回归；共享页、私有绑定、原生/用户态并存与最小部署检查。ASAN 不覆盖未插桩共享核心，未宣称全进程无泄漏。既有 hardening/runtime 限制也未解决。

主调度器在当前 XZ 组 336/336 完成并自行恢复/卸载后停止；两个后续等待队列尚未启动任何作业即取消。未删除任何结果，没有剩余本任务实验/后续队列进程，任务模块已卸载。原队列 JSON 保留历史 running/waiting 状态；最终权威取消状态是 `stopped.json`，不能再据旧字段当作仍在运行。

服务器证据根目录：

`/var/tmp/vkso-section65-optimization-20261030-hBcg9Y/budget-closeout-01/`

主要文件：`analysis.json`、`audit.json`、`resource-ledger.json`、`correctness-and-cleanup.json`、`selected-core-queue.json`、`stopped.json`。它们保留原始样本路径/哈希、完整范围与未运行项。此轮核心工作到此结束，不自动恢复后续优化。
