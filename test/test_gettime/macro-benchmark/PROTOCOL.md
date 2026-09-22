# Clocktime 四种内核 macrobench 协议

唯一对外采集入口为 `vkso-tests/baremetal/experiment.sh`，保留已有 `begin [RUN_ID]`、`begin-normal [RUN_ID]`、`boot [CASE]`、`collect [CASE]`、`status` 接口。内部 Python 文件是工作负载模块，不负责重启或实验调度。

## 比较对象

固定四个 case：`raw-normal`、`vkso-normal`、`raw-no-retpoline`、`vkso-no-retpoline`。`raw` 表示原生 vDSO；`normal` 使用原有 mitigation 配置，`no-retpoline` 沿用项目既有 retpoline/rethunk 等配置组关闭的定义。

每次 collect 先执行既有 ABI、READ 和 seq 采集，再执行 Redis。Raw 内核分别记录原生 libc（native）和同层 vDSO bridge（vdso）；VKSO 内核记录 VKSO bridge（vkso）。native/VKSO 比较包含实际应用接入成本，vdso/VKSO 比较使用同一 bridge。两种 mitigation 配置分别分析，不混合平均。

本次按用户要求使用手动 boot/collect，不启动此前拟议的 20-boot 自动控制器，也不自动加入 Copy 或 writer 实验。原有 revision 和 update-bench 框架及历史数据保留。

## 构建与版本

通过原有 `build-all.sh` 构建两个配对包，包含四个镜像及逐字节相同的 Redis/bridge 工具。VKSO 两个镜像均来自当前修改后的源码。没有原始 Linux tarball 时，复用已归档且验证身份的 5.15.198 原生 vDSO 镜像，只重建两个 VKSO 镜像；有 tarball 时照常构建四个镜像。配置差异由原有 verify-packages 检查。

Redis 固定为未修改的 7.2.4 发布包，使用默认构建选项及 bundled jemalloc。源包保存在 vendor，构建日志与工具放进每个实验包的 macro 目录。build-all 只构建及核对包，不自动启动 KVM 或性能测试。

## 负载与计时

- 单实例 Redis，loopback TCP，10,000 个 key、64 B value；无周期 RDB 保存、无 AOF，其他服务设置沿用默认值。
- GET、SET 各使用 pipeline 1、16，共四种负载；50 clients、2 个 benchmark 线程。
- 每种负载每轮暖机 200,000 请求，再测 nominal 3,000,000 请求；每种方法 7 轮，轮间旋转负载顺序。GET 必须无 miss。
- 服务端 CPU 1，客户端 CPU 2/3，控制进程及 IRQ 使用 CPU 0。隔离 CPUs 1–3，关闭 SMT/turbo，固定 performance 范围与 setarch -R 布局。
- VKSO 和同层 vDSO 服务端使用同一 libc bridge，只有初始化 provider 不同；native 服务端不预加载 bridge。
- 所有 redis-benchmark 客户端统一使用 bridge 的 syscall 模式。VKSO 内核没有原生 vDSO，因此不能让 Raw 客户端走 vDSO、VKSO 客户端走 syscall 而不加区分。
- 正式 bridge 不编译诊断计数器，不开启 seccomp。启动、注册和暖机不计入 Redis 报告的稳态吞吐。

保存 rps、平均/P50/P95/P99/min/max 延迟，以及每轮客户端和服务端 CPU 时间、子进程墙钟时间。CPU 时间用于判断负载生成器限制；墙钟时间包含客户端进程启动，不代替 Redis 自身的吞吐测量。redis-benchmark 为闭环客户端，pipeline 延迟采用其批次测量语义。

## 输出与解释

一轮四个 case 共 168 条应用记录：2 个 Raw case × 2 种方法 × 7 轮 × 4 负载，加 2 个 VKSO case × 1 种方法 × 7 轮 × 4 负载。每个方法保存原始 CSV、warmup、server log、INFO、maps/smaps、CPU 记录与 complete.json；缺失或失败不推进 case。

每次完成四个 case 后自动归档。再次从 `boot raw-normal` 开始会生成新 run，旧结果不覆盖。要估计跨启动变动，可独立重复完整四-case 轮次；一轮中的 7 次重复不应冒充 7 次独立启动。固定 case 顺序是已有接口的行为，分析时应保留这一顺序限制。

页共享证据单列，不能用 smaps 或重复映射 RSS 相加代替整机物理内存比较。

## 验证状态

之前的 results/preflight 是旧接入版本的 KVM 功能证据。此次统一入口、客户端 syscall 计时及四-case 集成版本按用户要求尚未运行，也未启动性能采集；它的运行验收将由用户执行以下 README 中的固定命令完成。不能把旧 preflight 表述为此次修改后的整套脚本已经运行通过。
