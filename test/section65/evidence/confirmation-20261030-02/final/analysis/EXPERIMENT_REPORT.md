# Section 6.5 优化与完整实验报告

本报告交付实验、分析和原始证据。按用户最新要求，不更新论文正文、不生成图片。现有论文/PDF仍是先前版本，不代表本轮结果。

## 1. 研究问题与版本

验证复杂 SquashFS 公共核心能否同时服务真实 native 与 Apptainer/SIF 用户消费者，保持私有对象/缓存，并以合理的适配、执行和部署成本实现跨域物理复用。三类对照分别回答：原生准备成本、同代码 copied/shared 的共享增量、相对 SquashFUSE/LKL 的完整应用表现。

公共核心不仅是解码器：还包含 SquashFS 的 superblock、目录、inode、block list、元数据及数据访问逻辑，以及公共 LZ4/XZ。native consumer 保留 VFS、内核 page cache、同步和 BIO 环境；用户桥提供私有对象、缓存、分配和用户 I/O，并经 FUSE helper 接入真实 Apptainer/SIF。其余 codec 由两侧服务绑定提供。这是声明的复用边界，并非把完整 VFS 或整个内核带入用户域。

选定版本为现有标量字典 word-copy XZ 核心，加 2048/4096 inode/name LRU 和 48 槽惰性数据缓存（128 KiB 块时最多请求 6 MiB 数据缓冲）。metadata/fragment 缓存仍为 8/3 槽。owner 与 native consumer 字节不变；前端/translator 的运行段内容和地址不变，重建后的 build ID 和调试信息不同。copied/shared 使用完全相同的最终前端、桥和核心指令。

16 槽候选的 Python 改善伴随 LZ4 stream 回退；按文件大小使用单个缓冲区的候选未保住 Python 收益，也未消除 LZ4 回退，因此均未采用。48 槽候选经过预先限定的 16/48 比较后选定，额外内存成本计入结果。bit-tree 解码候选仅完成诊断/构建，未进入正式版本。详见 SELECTION.md、CACHE_PROTOCOL.md 和保留的全部 pilot。

本轮关键数值（全部对照详见后续表和 summary.csv）：

- Python/XZ：VKSO 对 stock：+2.98% [+2.82%, +3.14%]。
- Python/XZ：48 槽 copied 对旧一槽 copied：-11.32% [-12.03%, -10.62%]。
- XZ 顺序任务：VKSO 对 stock：-12.87% [-14.70%, -11.00%]。
- LZ4 顺序任务：48 槽 copied 对旧一槽 copied：+1.88% [+0.37%, +3.41%]。
- LZ4 顺序任务：VKSO 对同代码 copied：-1.24% [-11.73%, +10.50%]。
- 原生 XZ fresh 顺序：word-copy 对优化前 prepared：-27.02% [-28.21%, -25.82%]。

这次优化显著缩小了 Python/XZ 的旧差距，但仍慢于 stock；LZ4 顺序任务相对旧缓存存在小幅回退，且 48 槽增加私有缓冲区容量。因此结果是有成本的优化，不支持所有任务均无回退或普遍更省内存。

## 2. 覆盖、执行和统计

完整分析为 30 个 campaign / 8,172 条观测，独立重算 541 项配对比较。2,688 条来自四个二进制及 runner 身份匹配的原生 campaign；5,484 条为本轮新观测。用户应用全部重测。被交互中断的原生组 790 条部分记录完整保留、全部排除，并使用原种子/条件重跑整组。更早 14 组 / 4,580 条缩减收尾及其中 127 条中断记录仍独立保留。未按性能筛选观测。

| 矩阵 | campaign | 观测 | 作用 |
| --- | ---: | ---: | --- |
| native-final | 3 | 3,360 | 五格式，scan/archive，fresh/warm，七种 native 条件 |
| native-stream | 3 | 672 | XZ/LZ4 大文件 archive，fresh/warm |
| application-final | 9 | 3,456 | gzip/XZ/LZ4 四任务，含 stock 单线程/translator、LKL 两配置、旧缓存 copied |
| heldout | 6 | 336 | 固定 gzip/XZ Python 编译，647 个相同产物 |
| decoder-diagnostic | 6 | 240 | XZ/LZ4 等长路径、解码器与动态依赖对照 |
| sharing-singlecpu | 3 | 108 | gzip stream 单 CPU stock/copied/shared |

每格三个 campaign；先在 campaign 内对配对 log ratio 求均值，再对 campaign 等权，95% 区间使用 campaign 层级 Student-t（df=2）。绝对时间为各 campaign 中位数的均值，不能直接相除代替配对比率。表中百分比为测试/对照−1，负值表示耗时降低。所有比较的 CPU 比率、逐 campaign 估计及次级重采样结果保存在 analysis.json。

同一 i7-1165G7 主机、同一次启动；原生 CPU 1，普通应用 CPU 1–2，单 CPU 对照单列。SMT/turbo 已关闭，powersave 策略保持原状。新进程/挂载/加载周期、交错配对和实际顺序均保留。压缩镜像页缓存预热；fresh-mount 不等于冷存储，warm native 可能绕过公共核心。正式计时无本任务并行编译、QEMU 或 profiler。TCG 仅用于功能。

## 3. 原生准备及公共 XZ 优化

| 场景 / 格式 / 任务 / 状态 | 对照 → 测试 | 对照秒 | 测试秒 | 配对耗时变化 [95% CI] | 配对数 / campaign 数 |
| --- | --- | ---: | ---: | ---: | ---: |
| native-final / gzip / archive / fresh-mount | native-word-normal → prepared-optimized | 0.2752 | 0.2739 | -0.41% [-0.59%, -0.24%] | 24 / 3 |
| native-final / gzip / scan / fresh-mount | native-word-normal → prepared-optimized | 0.0622 | 0.0629 | +0.78% [+0.08%, +1.49%] | 24 / 3 |
| native-final / lz4 / archive / fresh-mount | native-word-normal → prepared-optimized | 0.1375 | 0.1366 | -0.74% [-2.48%, +1.04%] | 24 / 3 |
| native-final / lz4 / scan / fresh-mount | native-word-normal → prepared-optimized | 0.0594 | 0.0594 | -0.20% [-0.98%, +0.59%] | 24 / 3 |
| native-final / lzo / archive / fresh-mount | native-word-normal → prepared-optimized | 0.1532 | 0.1523 | -1.29% [-2.49%, -0.08%] | 24 / 3 |
| native-final / lzo / scan / fresh-mount | native-word-normal → prepared-optimized | 0.0594 | 0.0597 | +0.01% [-1.41%, +1.44%] | 24 / 3 |
| native-final / xz / archive / fresh-mount | native-word-normal → prepared-optimized | 0.7624 | 0.7801 | +2.24% [+0.74%, +3.75%] | 24 / 3 |
| native-final / xz / scan / fresh-mount | native-word-normal → prepared-optimized | 0.0758 | 0.0769 | +1.11% [+0.89%, +1.33%] | 24 / 3 |
| native-final / zstd / archive / fresh-mount | native-word-normal → prepared-optimized | 0.1737 | 0.1723 | -0.89% [-1.42%, -0.37%] | 24 / 3 |
| native-final / zstd / scan / fresh-mount | native-word-normal → prepared-optimized | 0.0603 | 0.0609 | +0.78% [-10.53%, +13.52%] | 24 / 3 |
| native-stream / lz4 / archive / fresh-mount | native-word-normal → prepared-optimized | 0.2860 | 0.2858 | -0.05% [-1.26%, +1.17%] | 24 / 3 |
| native-stream / xz / archive / fresh-mount | native-word-normal → prepared-optimized | 0.4204 | 0.4231 | +0.74% [-0.93%, +2.44%] | 24 / 3 |

| 场景 / 格式 / 任务 / 状态 | 对照 → 测试 | 对照秒 | 测试秒 | 配对耗时变化 [95% CI] | 配对数 / campaign 数 |
| --- | --- | ---: | ---: | ---: | ---: |
| native-stream / xz / archive / fresh-mount | prepared-xz → prepared-optimized | 0.5794 | 0.4231 | -27.02% [-28.21%, -25.82%] | 24 / 3 |
| native-stream / xz / archive / warm | prepared-xz → prepared-optimized | 0.1331 | 0.1329 | -0.12% [-1.84%, +1.64%] | 24 / 3 |

完整原生表同时保留 original、相同算法优化的 normal/relaxed native，以及先前 prepared 对照。prepared 的 PIC、stack protector、indirect/return thunk 差异未消除；结果属于完整准备方案，不能解释为纯 PGOT 成本或加固等价。匹配 word-copy 的 native 模块捆绑 XZ，和调用宿主 XZ 的旧参考具有不同驻留边界。

## 4. 完整应用表现

| 场景 / 格式 / 任务 / 状态 | 对照 → 测试 | 对照秒 | 测试秒 | 配对耗时变化 [95% CI] | 配对数 / campaign 数 |
| --- | --- | ---: | ---: | ---: | ---: |
| application-final / gzip / archive / full-application | lkl-512 → vkso | 2.2252 | 0.9035 | -59.72% [-61.56%, -57.79%] | 36 / 3 |
| application-final / gzip / archive / full-application | lkl-cache-512 → vkso | 1.2997 | 0.9035 | -30.63% [-31.93%, -29.31%] | 36 / 3 |
| application-final / gzip / archive / full-application | stock → vkso | 0.9629 | 0.9035 | -5.96% [-6.82%, -5.09%] | 36 / 3 |
| application-final / gzip / archive / full-application | stock-single → vkso | 0.8982 | 0.9035 | +0.80% [-0.49%, +2.10%] | 36 / 3 |
| application-final / gzip / scan / full-application | lkl-512 → vkso | 2.0206 | 0.4524 | -77.38% [-78.03%, -76.71%] | 36 / 3 |
| application-final / gzip / scan / full-application | lkl-cache-512 → vkso | 0.6608 | 0.4524 | -31.24% [-33.87%, -28.51%] | 36 / 3 |
| application-final / gzip / scan / full-application | stock → vkso | 0.4902 | 0.4524 | -8.05% [-9.40%, -6.69%] | 36 / 3 |
| application-final / gzip / scan / full-application | stock-single → vkso | 0.4552 | 0.4524 | +0.15% [-1.62%, +1.95%] | 36 / 3 |
| application-final / gzip / startup / full-application | lkl-512 → vkso | 0.2319 | 0.1409 | -37.81% [-41.86%, -33.48%] | 36 / 3 |
| application-final / gzip / startup / full-application | lkl-cache-512 → vkso | 0.2183 | 0.1409 | -35.37% [-36.86%, -33.85%] | 36 / 3 |
| application-final / gzip / startup / full-application | stock → vkso | 0.1446 | 0.1409 | -5.13% [-13.05%, +3.51%] | 36 / 3 |
| application-final / gzip / startup / full-application | stock-single → vkso | 0.1445 | 0.1409 | -2.44% [-3.45%, -1.42%] | 36 / 3 |
| application-final / gzip / stream / full-application | lkl-512 → vkso | 0.9629 | 0.6231 | -35.25% [-37.18%, -33.27%] | 36 / 3 |
| application-final / gzip / stream / full-application | lkl-cache-512 → vkso | 0.9707 | 0.6231 | -35.64% [-37.13%, -34.11%] | 36 / 3 |
| application-final / gzip / stream / full-application | stock → vkso | 0.6659 | 0.6231 | -6.69% [-7.53%, -5.84%] | 36 / 3 |
| application-final / gzip / stream / full-application | stock-single → vkso | 0.6458 | 0.6231 | -4.06% [-5.39%, -2.72%] | 36 / 3 |
| application-final / lz4 / archive / full-application | lkl-512 → vkso | 2.0232 | 0.7996 | -60.67% [-60.85%, -60.49%] | 36 / 3 |
| application-final / lz4 / archive / full-application | lkl-cache-512 → vkso | 1.1127 | 0.7996 | -28.49% [-30.29%, -26.64%] | 36 / 3 |
| application-final / lz4 / archive / full-application | stock → vkso | 0.8135 | 0.7996 | -2.24% [-2.82%, -1.66%] | 36 / 3 |
| application-final / lz4 / archive / full-application | stock-single → vkso | 0.7783 | 0.7996 | +1.90% [-0.02%, +3.86%] | 36 / 3 |
| application-final / lz4 / scan / full-application | lkl-512 → vkso | 1.9679 | 0.4387 | -77.62% [-78.21%, -77.02%] | 36 / 3 |
| application-final / lz4 / scan / full-application | lkl-cache-512 → vkso | 0.6285 | 0.4387 | -30.50% [-32.59%, -28.35%] | 36 / 3 |
| application-final / lz4 / scan / full-application | stock → vkso | 0.4628 | 0.4387 | -5.25% [-5.56%, -4.94%] | 36 / 3 |
| application-final / lz4 / scan / full-application | stock-single → vkso | 0.4352 | 0.4387 | +1.17% [-1.75%, +4.17%] | 36 / 3 |
| application-final / lz4 / startup / full-application | lkl-512 → vkso | 0.2132 | 0.1298 | -37.03% [-40.47%, -33.40%] | 36 / 3 |
| application-final / lz4 / startup / full-application | lkl-cache-512 → vkso | 0.2067 | 0.1298 | -34.11% [-38.68%, -29.21%] | 36 / 3 |
| application-final / lz4 / startup / full-application | stock → vkso | 0.1303 | 0.1298 | +1.41% [-10.12%, +14.41%] | 36 / 3 |
| application-final / lz4 / startup / full-application | stock-single → vkso | 0.1303 | 0.1298 | -0.58% [-14.62%, +15.77%] | 36 / 3 |
| application-final / lz4 / stream / full-application | lkl-512 → vkso | 0.7943 | 0.5224 | -35.47% [-41.33%, -29.02%] | 36 / 3 |
| application-final / lz4 / stream / full-application | lkl-cache-512 → vkso | 0.8008 | 0.5224 | -35.67% [-41.64%, -29.09%] | 36 / 3 |
| application-final / lz4 / stream / full-application | stock → vkso | 0.5469 | 0.5224 | -5.59% [-14.74%, +4.54%] | 36 / 3 |
| application-final / lz4 / stream / full-application | stock-single → vkso | 0.5320 | 0.5224 | -2.76% [-12.58%, +8.16%] | 36 / 3 |
| application-final / xz / archive / full-application | lkl-512 → vkso | 2.6428 | 1.5467 | -42.78% [-44.71%, -40.78%] | 36 / 3 |
| application-final / xz / archive / full-application | lkl-cache-512 → vkso | 1.8365 | 1.5467 | -16.10% [-17.48%, -14.70%] | 36 / 3 |
| application-final / xz / archive / full-application | stock → vkso | 2.0398 | 1.5467 | -23.98% [-24.32%, -23.63%] | 36 / 3 |
| application-final / xz / archive / full-application | stock-single → vkso | 1.9841 | 1.5467 | -22.02% [-22.59%, -21.43%] | 36 / 3 |
| application-final / xz / scan / full-application | lkl-512 → vkso | 1.0706 | 0.5370 | -49.72% [-51.54%, -47.83%] | 36 / 3 |
| application-final / xz / scan / full-application | lkl-cache-512 → vkso | 0.6521 | 0.5370 | -18.10% [-22.07%, -13.92%] | 36 / 3 |
| application-final / xz / scan / full-application | stock → vkso | 1.2951 | 0.5370 | -58.33% [-59.57%, -57.05%] | 36 / 3 |
| application-final / xz / scan / full-application | stock-single → vkso | 1.2683 | 0.5370 | -57.40% [-58.53%, -56.24%] | 36 / 3 |
| application-final / xz / startup / full-application | lkl-512 → vkso | 0.3002 | 0.2066 | -29.81% [-33.28%, -26.16%] | 36 / 3 |
| application-final / xz / startup / full-application | lkl-cache-512 → vkso | 0.2851 | 0.2066 | -25.63% [-30.87%, -19.98%] | 36 / 3 |
| application-final / xz / startup / full-application | stock → vkso | 0.4534 | 0.2066 | -53.57% [-55.40%, -51.66%] | 36 / 3 |
| application-final / xz / startup / full-application | stock-single → vkso | 0.4500 | 0.2066 | -53.22% [-55.15%, -51.19%] | 36 / 3 |
| application-final / xz / stream / full-application | lkl-512 → vkso | 1.2340 | 0.8307 | -33.11% [-34.34%, -31.86%] | 36 / 3 |
| application-final / xz / stream / full-application | lkl-cache-512 → vkso | 1.2287 | 0.8307 | -32.65% [-33.45%, -31.83%] | 36 / 3 |
| application-final / xz / stream / full-application | stock → vkso | 0.9468 | 0.8307 | -12.87% [-14.70%, -11.00%] | 36 / 3 |
| application-final / xz / stream / full-application | stock-single → vkso | 0.9163 | 0.8307 | -9.73% [-12.15%, -7.23%] | 36 / 3 |
| heldout / gzip / compile / full-application | lkl-512 → vkso | 1.9825 | 1.6696 | -15.53% [-16.93%, -14.11%] | 24 / 3 |
| heldout / gzip / compile / full-application | lkl-cache-512 → vkso | 1.8179 | 1.6696 | -8.04% [-9.84%, -6.21%] | 24 / 3 |
| heldout / gzip / compile / full-application | stock → vkso | 1.7011 | 1.6696 | -1.59% [-2.84%, -0.32%] | 24 / 3 |
| heldout / gzip / compile / full-application | stock-single → vkso | 1.6913 | 1.6696 | -1.00% [-2.08%, +0.09%] | 24 / 3 |
| heldout / xz / compile / full-application | lkl-512 → vkso | 2.5171 | 2.2341 | -11.23% [-11.98%, -10.47%] | 24 / 3 |
| heldout / xz / compile / full-application | lkl-cache-512 → vkso | 2.3677 | 2.2341 | -5.68% [-6.62%, -4.73%] | 24 / 3 |
| heldout / xz / compile / full-application | stock → vkso | 2.1678 | 2.2341 | +2.98% [+2.82%, +3.14%] | 24 / 3 |
| heldout / xz / compile / full-application | stock-single → vkso | 2.1589 | 2.2341 | +3.61% [+2.38%, +4.85%] | 24 / 3 |

stock 为实际 squashfuse_ll 0.6.2；默认和 -s 使用同一可执行体，编译时 data/fragment 容量均为 48。LKL 使用 Linux 6.12、512 MiB heap，并保留默认和匹配 positive timeout 的配置；512 MiB 是偏性能的选择，不是完成任务的最低内存。不同核心/缓存/FUSE API/线程/库的完整方案差异不等于物理共享效果。Python 已参与本次优化，不能再称为未见过的 holdout。

## 5. 共享增量与缓存优化归因

| 场景 / 格式 / 任务 / 状态 | 对照 → 测试 | 对照秒 | 测试秒 | 配对耗时变化 [95% CI] | 配对数 / campaign 数 |
| --- | --- | ---: | ---: | ---: | ---: |
| application-final / gzip / archive / full-application | copied → vkso | 0.9050 | 0.9035 | -0.19% [-1.75%, +1.40%] | 36 / 3 |
| application-final / gzip / scan / full-application | copied → vkso | 0.4510 | 0.4524 | +0.72% [-2.01%, +3.51%] | 36 / 3 |
| application-final / gzip / startup / full-application | copied → vkso | 0.1419 | 0.1409 | -2.83% [-5.43%, -0.16%] | 36 / 3 |
| application-final / gzip / stream / full-application | copied → vkso | 0.6243 | 0.6231 | -0.62% [-2.59%, +1.39%] | 36 / 3 |
| application-final / lz4 / archive / full-application | copied → vkso | 0.7987 | 0.7996 | -0.00% [-0.43%, +0.43%] | 36 / 3 |
| application-final / lz4 / scan / full-application | copied → vkso | 0.4408 | 0.4387 | -0.63% [-2.02%, +0.79%] | 36 / 3 |
| application-final / lz4 / startup / full-application | copied → vkso | 0.1287 | 0.1298 | +1.97% [-8.07%, +13.11%] | 36 / 3 |
| application-final / lz4 / stream / full-application | copied → vkso | 0.5239 | 0.5224 | -1.24% [-11.73%, +10.50%] | 36 / 3 |
| application-final / xz / archive / full-application | copied → vkso | 1.5495 | 1.5467 | -0.14% [-0.88%, +0.60%] | 36 / 3 |
| application-final / xz / scan / full-application | copied → vkso | 0.5370 | 0.5370 | -0.16% [-2.24%, +1.96%] | 36 / 3 |
| application-final / xz / startup / full-application | copied → vkso | 0.2051 | 0.2066 | +1.30% [-1.44%, +4.12%] | 36 / 3 |
| application-final / xz / stream / full-application | copied → vkso | 0.8330 | 0.8307 | -0.65% [-1.65%, +0.37%] | 36 / 3 |
| decoder-diagnostic / lz4 / scan / full-application | copied → vkso | 0.4414 | 0.4382 | -0.77% [-4.33%, +2.91%] | 12 / 3 |
| decoder-diagnostic / lz4 / stream / full-application | copied → vkso | 0.5171 | 0.5190 | +1.02% [+0.17%, +1.87%] | 12 / 3 |
| decoder-diagnostic / xz / scan / full-application | copied → vkso | 0.5382 | 0.5411 | +0.47% [+0.36%, +0.58%] | 12 / 3 |
| decoder-diagnostic / xz / stream / full-application | copied → vkso | 0.8202 | 0.8208 | -0.17% [-0.92%, +0.59%] | 12 / 3 |
| heldout / gzip / compile / full-application | copied → vkso | 1.6696 | 1.6696 | +0.13% [-1.03%, +1.32%] | 24 / 3 |
| heldout / xz / compile / full-application | copied → vkso | 2.2339 | 2.2341 | +0.18% [-0.88%, +1.25%] | 24 / 3 |
| sharing-singlecpu / gzip / stream / full-application | copied → vkso | 0.6065 | 0.6058 | -0.11% [-1.77%, +1.58%] | 36 / 3 |

| 场景 / 格式 / 任务 / 状态 | 对照 → 测试 | 对照秒 | 测试秒 | 配对耗时变化 [95% CI] | 配对数 / campaign 数 |
| --- | --- | ---: | ---: | ---: | ---: |
| application-final / gzip / archive / full-application | copied-small → copied | 0.9168 | 0.9050 | -1.35% [-1.84%, -0.85%] | 36 / 3 |
| application-final / gzip / scan / full-application | copied-small → copied | 0.4580 | 0.4510 | -2.05% [-3.77%, -0.31%] | 36 / 3 |
| application-final / gzip / startup / full-application | copied-small → copied | 0.1505 | 0.1419 | -3.91% [-12.72%, +5.80%] | 36 / 3 |
| application-final / gzip / stream / full-application | copied-small → copied | 0.6356 | 0.6243 | -1.81% [-4.27%, +0.71%] | 36 / 3 |
| application-final / lz4 / archive / full-application | copied-small → copied | 0.7940 | 0.7987 | +0.20% [-1.46%, +1.89%] | 36 / 3 |
| application-final / lz4 / scan / full-application | copied-small → copied | 0.4387 | 0.4408 | +1.10% [-1.64%, +3.93%] | 36 / 3 |
| application-final / lz4 / startup / full-application | copied-small → copied | 0.1294 | 0.1287 | +0.54% [-4.99%, +6.39%] | 36 / 3 |
| application-final / lz4 / stream / full-application | copied-small → copied | 0.5112 | 0.5239 | +1.88% [+0.37%, +3.41%] | 36 / 3 |
| application-final / xz / archive / full-application | copied-small → copied | 1.6481 | 1.5495 | -5.82% [-6.47%, -5.17%] | 36 / 3 |
| application-final / xz / scan / full-application | copied-small → copied | 0.5884 | 0.5370 | -8.49% [-10.85%, -6.07%] | 36 / 3 |
| application-final / xz / startup / full-application | copied-small → copied | 0.2548 | 0.2051 | -18.93% [-19.99%, -17.85%] | 36 / 3 |
| application-final / xz / stream / full-application | copied-small → copied | 0.9234 | 0.8330 | -10.04% [-10.80%, -9.28%] | 36 / 3 |
| heldout / gzip / compile / full-application | copied-small → copied | 1.7160 | 1.6696 | -2.63% [-2.97%, -2.28%] | 24 / 3 |
| heldout / xz / compile / full-application | copied-small → copied | 2.5182 | 2.2339 | -11.32% [-12.03%, -10.62%] | 24 / 3 |

缓存对照保持公共 owner 指令不变；这项收益同样惠及 copied。默认路径、等长路径及单 CPU 条件分别报告；小点估计或包含零的区间不能证明严格等价或普遍零开销。

LZ4 stream 的 shared/copied 三轮耗时变化依次为 +0.02%, -6.07%, +2.54%；合并 CPU 时间比变化为 +0.02% [-0.78%, +0.83%]。耗时区间仍宽，不能把此前单轮 +6.22% 或本轮负点估计认定为固定共享机制成本；未删除任何一轮。

三轮完整 Python 解码器诊断在旧一槽桥上观察到：common-retained/library +2.60%，library/stock +13.01%。完整 Python 的解码次数从旧桥 352 次下降到 48 槽的 282 次；stock 为 243 次，产物一致。最终 metadata 扫描三次重放均为公共解析器 76 次 / 558,231 解压字节，stock 两种线程模式均为 137 次 / 1,106,363 字节。计数支持减少重复解压工作，但不能把所有时间差精确分配给一个原因。仪器化时间不进入正式统计。

## 6. 内存、物理页与部署

| 后端 | 1× PSS KiB | 4× | 16× |
| --- | ---: | ---: | ---: |
| stock | 17709 | 28440 | 29563 |
| stock-single | 12240 | 13429 | 13237 |
| copied | 10242 | 13430 | 25968 |
| vkso | 10235 | 13434 | 25990 |
| copied-small | 4281 | 7439 | 19888 |
| copied-unbounded | 7175 | 23980 | 91014 |
| lkl-cache-512 | 84699 | 260307 | 513097 |

这些是完成任务后的单次未计时 helper 快照，不是峰值、区间或整机净内存。完整三 codec × 三 campaign 的 RSS/PSS/USS/VmHWM/线程和前后快照见 resource-ledger/resources.json。48 槽比旧一槽桥多保留约 6 MiB 数据；新缓存策略在小规模也可能高于旧无界桥。libfuse 16× 活对象诊断测到 14,786,560 B node slabs 和 2,097,152 B hash arrays；第二遍节点数稳定，说明桥的缓存上限并不等于整个进程内存上限。

16× 规模最终 copied 对旧无界 copied 的 PSS 变化为 -71.47%；最终 VKSO 为 25,990 KiB，高于 stock-single 的 13,237 KiB。这是缓存策略的空间/时间折中，不是代码页共享造成的 PSS 降幅。

实际共享 9 页 / 36 KiB，逐页 PFN 和映射字节一致，copied PFN 不共享。owner/consumer 为 68/40 KiB；捆绑相同 XZ 的 normal native 参考为 72 KiB；注册请求 1,264 B。通用平台 32 KiB 按用户指定作为一次性基础设施单列，不计入业务小计。

| 业务部署情景 | 文件实际分配 KiB |
| --- | ---: |
| prepared-native-shared | 288 |
| prepared-native-copied | 324 |
| user-only-shared | 228 |
| user-only-copied | 184 |

磁盘采用未剥离文件的 st_blocks，按 inode 去重，共同依赖/镜像/平台同口径排除。已有 prepared native 与纯用户部署分别解释；普通 DSO 也可在用户进程间共享，不能按进程数乘以代码去重收益。模块驻留、helper PSS、注册请求与磁盘分配不能直接相加成整机净收益。
构造/导出/注册在 9 个应用 campaign 中的中位耗时 2.746 s，范围 [2.696, 4.000]；逐次阶段见 ledger。这个值不含编译、模块加载和验证，也不能假设 copied 构造免费。owner 重载或版本变化需要重新部署，已驻留后才可摊销到后续应用调用。

## 7. 正确性、适配和维护

复用 34 个文件系统函数 / 2,103 原始物理行，16 个 native 源/头文件发生准备修改，3 个文件系统函数体改变。XZ 原始算法范围 2,604 行，当前 2,637 行，仅 dict_repeat 算法体编辑；公共 LZ4 同时保留。桥/POSIX/frontend 为 535/154/314 行。生成支持、生成器、服务槽、机械移动、应用 translator、通用 exporter 修正及脚本分别核算。LKL 应用扩展 30 行只与已有平台上的应用接入比较，不能与首次内核准备混比。代码量没有转换为开发工时。

最终桥通过 25 个五格式挂载和 5 个 BCJ 挂载；客体中 copied/shared 各 22,032 次边界/随机读取。ASAN/UBSAN 检查私有适配器，覆盖 8192 文件、三轮 churn 和超过缓存预算的活跃句柄；未插桩公共核心，未证明全进程无泄漏。真实 FUSE FD/游标生命周期、native A 与真实 SIF B/C 的独立对象和退出次序、共享页及 XZ 断点、后续 native 回归、最小部署均通过。

已知上游负偏移缺陷的 old/fixed × native/copied/shared 维护记录保留。旧错误由客户端、daemon 信号及目标函数内核故障共同判断；并非将任意失败算作复现。当前最终桥客体回归三端 EIO、daemon 存活、五格式回归/restore/unload 通过。原维护实验中桥和前端保持不变；后来的字典与缓存优化单独计账。共同修复惠及 copied，仍需重建、导出/注册和重新部署，未证明热更新。

## 8. 主张判断和边界

| 主张 | 当前判断 | 对应证据/边界 |
| --- | --- | --- |
| 复杂公共核心进入真实 native/user 应用 | 在明确范围内支持 | 真实 SIF/FD/offset、功能、PFN、私有对象与生命周期 |
| 保留原生功能并量化准备成本 | 在明确范围内支持 | 五格式、直接匹配优化参考；加固差异仍存在 |
| 物理共享的增量执行成本可量化 | 在测量范围内支持 | 同代码 copied/shared；不从不显著推出等价 |
| 相对现有后端的实际效率 | 在明确任务/配置范围内支持 | 上表所有任务、stock 两线程与 LKL 两缓存配置 |
| 格式代码复用与共同维护点 | 支持 | 源范围/修改面/真实上游修复；并非全部零改动 |
| 物理资源去重 | 条件性支持 | 36 KiB identity；已有 owner 与纯用户部署不同 |
| 减少开发/调试工时 | 未证明 | 无可靠历史人时或受控人工任务 |
| 整机净内存必然下降 | 不支持该一般结论 | 组件账本不足以替代完整整机增量测量 |
| 热更新、并发吞吐扩展、跨启动/机器推广 | 未验证 | 生命周期重叠及同 boot 三轮不能替代这些实验 |
| shared 普遍优于同代码 copied | 不支持 | copied 享有核心/适配/维护收益且可独立部署 |

## 9. 复现和证据入口

本目录 analysis.json、summary.csv、audit.json、costs.json、reuse-audit/ 和 resource-ledger/ 是统一分析入口。源码协议与原/恢复注册在 test/section65/squashfs/confirmation-20261030-02/；recovered-formal-queue.json 指向最终 30 组原始记录。各目录保存 samples.jsonl、environment.json、实际顺序、阶段日志、资源和 PFN 检查。790 条部分记录由 data48-recovery-01/recovery.json 单独登记；旧 running 字段不表示仍有进程。

正式停止条件为固定矩阵完成，不以显著优势停止。未运行的 stream-resource 队列、bit-tree 构建和全部失败/拒绝候选均保留其真实状态。论文与图片另行处理，本报告不将旧 PDF 标为新结果。
