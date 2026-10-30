> This directory documents the historical ISO9660 experiment. Final Section 6.5
> SquashFS matrices and scope are indexed in [STATUS.md](../STATUS.md); these
> earlier results are retained separately and are not pooled with them.

# ISO9660 原生复用实验

目的：验证内核做必要重构后，原生文件系统任务的性能如何变化；另外测量把同一核心的复制页换成 VKSO 共享页带来的差别。它不预设 VKSO 更快。

## 已执行结果（2026-10-29）

初版、固定小尺寸内存操作优化版、再保留私有辅助函数版，均在 benchmark 原生执行完毕；每轮 35 组正确性比对、480 条正式观测、解除注册及模块卸载完成。原始轮次分别为 `native-20261029-agent-01`、`native-memops-20261029-agent-01`、`native-private-20261029-agent-01`，详见上级目录 `native-analysis.json`。

在 Linux include 文件树上，重构后的原生 tar 耗时增量依次为 10.90%、2.33%、0.99%，find 增量依次为 21.60%、2.91%、2.47%。每个数值均相对本轮同期原始驱动，未跨轮次混算。最终 VKSO/FUSE 相对同指令复制/FUSE 的增量为 tar 0.23%、find 0.31%；完整 FUSE 路径仍明显慢于原生内核路径。Alpine 的短 find 任务波动较大。完整区间及原始比值保留在分析文件中。

优化通过 `adapt.py` 或 `build_modules.py` 的 `--inline-constant-memops --keep-private-helpers` 显式启用：保留不超过 128 字节的编译期常量 memcpy/memset 优化，并保留 13 个原有内部 static 函数。动态内存操作仍经过服务表，公共对象的唯一未定义符号仍为 `iso_support`。优化没有改变工作负载或 FUSE 前端。

## 五条路径

| 名称 | 实现 | 回答的问题 |
|---|---|---|
| original | 原始 Linux 5.15.198 isofs，常规内核编译选项 | 原生基线 |
| compat | 原始算法，对齐公共核心的加固/插桩选项，保留内核编译模型 | 编译选项的诊断对照 |
| prepared | 重构后的内核 VFS 驱动和公共核心 | 重构后的原生效果 |
| copied-fuse | 同布局、同指令的物理复制核心，经过同一个 FUSE 前端 | VKSO 机制消融对照 |
| vkso-fuse | 实际共享内核代码页，经过同一个 FUSE 前端 | 页共享的额外影响 |

`original` 只改变文件系统注册名称并增加模块版本元数据，解析算法未改。三条内核路径启用相同 Joliet/zisofs 编译功能。用户路径只承诺已验证的只读功能，不支持 zisofs 解压、写入、设备操作或完整挂载选项。

**当前公共核心取消了 stack protector、外部 retpoline/rethunk 等编译机制。** `original → prepared` 是当前整个准备方案的影响，不能解释成只有服务间接调用的成本。`compat` 对照在原始驱动各编译单元对齐公共核心的加固/插桩选项，但保留访问内核专用状态所需的 kernel/non-PIE 编译模型；其改变范围也与 prepared 的公共核心范围不同，所以不能把两组差值当成严格可加的成本分解。它用于判断编译选项是否掩盖了退化。性能接近本身不证明安全属性等价；若继续推进可部署实现，需要另行处理该编译约束。

## 工作负载和采样

- Alpine 3.20.10 官方发行 ISO；来源记录在 `images/alpine-source.json`。
- 原始 Linux 5.15.198 的 `include/` 目录打成 Rock Ridge/Joliet 镜像，5,586 个源文件，约 35.7 MB 文件内容。它增加目录、路径和小文件访问，来源与具体大小见 `images/kernel-include-source.json`。
- `scan`：GNU find 遍历目录，读取文件类型、大小、权限和符号链接，生成目录索引。
- `archive`：未修改的 GNU tar 读取整棵目录及文件内容，写出真实 tar 文件。输出放在实验专用 tmpfs，避免输出磁盘性能支配结果。

默认 8 个 block，每个组合重复 3 次；每次新建挂载，FUSE 路径新建进程。背后镜像文件预读入缓存，不全局 drop_caches。这测量的是热镜像上的新挂载任务，不是冷盘吞吐，也不包含挂载/注册耗时。客户端固定 CPU 1，FUSE 服务固定 CPU 2。每个 block 内随机交错五条路径；重复挂载先取中位数，再按 block 做成对比值及 bootstrap 区间。服务进程 CPU 用 `/proc/PID/stat` 计数，分辨率受系统 clock tick 限制；很短任务的零值不代表没有 CPU 开销。

运行前，五条路径分别比对六组既有原始内核参考结果，以及较大的内核头文件树。比较包含路径、元数据、符号链接、文件内容。另行检查 VKSO 页与内核 PFN 一致、复制对照 PFN 不一致。定时阶段不做内容哈希。

## 执行

包绑定 `package.json` 中的内核 build ID。正式包对应当前 `vkso-final-raw-normal-5.15.198.bzImage`，不是虚拟机使用的 Ubuntu 119 内核。脚本不会换内核或重启。

执行所需的模块、前端、镜像和工具已预编译。`source/` 保留核心改动、原始源文件和构建命令供审查；完整重建仍需本仓库及对应内核 SDK。SDK 使用原始 Linux 5.15.198 和目标内核配置；`gcc`/`gcc-11` 是同一编译器的两个名称，仅配置中的编译器显示字符串有差别。注册使用的 ELF 从实际启动镜像提取，其 build ID 与运行内核逐次核对。

```bash
sudo bash run.sh --output /home/zzk/BinaryKernelCodeMapping/test/evaluation-local/runs/iso9660/native-01
```

每次使用新的输出目录。测试在私有挂载命名空间内操作自己的只读镜像，结束时卸载本次加载的模块；不删除或覆盖旧结果。若发现测试模块已存在会停止，以免干扰其他会话。正式运行时应暂停其他基准和构建作业。

结束后查看 `result.json` 的 `status`，以及 `summary.json`。时间比值大于 1 表示 treatment 更慢。原始观测保留在 `observations.jsonl` 和 `observations.csv`；配对比值保留在汇总中。目录旁自动生成同名 `.tar.gz`，失败时也保留诊断包。

**`--functional` 只供 QEMU 流程验证，其计时不能作为原生性能证据。** 本包尚不包含 LKL/rump 的实测对比，也不测量人的开发时间。普通共享库也能复用源代码；是否具备实际优势，应结合一次性核心重构、后续适配、真实物理共享量和完整运行成本判断。
