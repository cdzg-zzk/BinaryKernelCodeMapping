# Clocktime 内核 reader 契约修改与验证结果

日期：2026-09-28。分支：`codex/clocktime-reader-contract`。PR：#2。

基线是 `09b9505667f1d1c3da71ac8aaaa7d6054255bc62`；生产修改在
`0b9c66617e3c520c76b05cf99dc30eb5c19618d8`，完整验证代码在
`da35e634392b6ceba2c6d11d4bff2b7a3b7af774`。后续提交只记录文档和证据。
[CI run 36406043860](https://github.com/cdzg-zzk/BinaryKernelCodeMapping/actions/runs/36406043860)
实际测试 PR merge commit `b0e96200e0d7d6bfc687dab58cdf336b4e7d1d60`。
原 `paper-writing-revision` 分支未修改。本报告不是 NUC 正式性能结果。

## 1. 实际改动与理由

生产源码只修改 `include/linux/vkso_time.h` 和 `include/linux/vkso_getcpu.h`。
这是在两个内核适配接口处统一返回契约，不是在各个调用者中增加特殊分支。

`vkso_time_get_root()` 对共享 clock 是完成式适配器：共享读取成功，或者固定的
kernel callback 已经完成 private timekeeper 读取，都会得到有效输出。它现在
显式返回 `VKSO_TIME_OK`；native-only clock 仍返回 `VKSO_TIME_NOT_SHARED`。
不再把外部共享函数的不透明返回值传回每个普通 reader，使编译器能够消去
常量 clock 调用点的第二套 private fallback。私有读取本身没有删除。

`vkso_getcpu()` 同样显式表达共享 CPU/node reader 始终完成的契约。syscall 边界
仍然通过 `put_user()` 检查非法用户指针，不会把 EFAULT 吞掉。用户公开接口及其
失败返回值没有修改。将来若 kernel callback 引入可恢复错误，必须同时修改本契约，
不能继续假设完成成功。

共享 reader 算法、序列协议、context/状态布局、MM/namespace 生命周期、publisher、
用户 IFUNC/public wrapper、carrier builder 和 page-grafting 实现均未修改。
没有为了减少源码行数改写 TSC 热路径，也没有将 NMI/持锁专用路径强行并入普通 reader。
标量返回前的 timespec 归一化暂未改写：需要新的目标机 A/B 数据才能评判取舍。

## 2. 已完成验证

| 验证 | 环境与结果 |
| --- | --- |
| direct-api 与新契约/标量工具回归 | 本地 GCC 14.2：74 项通过；CI GCC 11.4：74 项通过 |
| UPDATE 工具回归 | 本地：45 项通过 |
| 源码审计工具单元测试 | 本地与 CI：各 5 项通过；不等于重新生成历史源码总量 |
| Linux 5.15.198 Kbuild | normal/no-retpoline，各编译基线与候选的 8 个生产对象及 reader 对象 |
| 共享机器码对象 | 三个对象 `.vkso.text` 修改前后逐字节相同，两种构建分别检查 |
| 最小候选内核启动 | 两种 mitigation 配置各 TSC/jiffies 两次 QEMU TCG 启动，共四次通过 |
| syscall ABI | 七种 clock 的 gettime/getres、NULL getres、time/gettimeofday/getcpu、EINVAL/EFAULT 检查通过 |
| 内核 reader | 每次 VM 启动均通过原三接口 9 行与新五标量接口 15 行样本完整性检查 |

Host fixture 编译实际共享计算源码，并从 Git 源码提取实际 kernel callback 和普通
调用者；只替换硬件、底层 private 输入及内存屏障环境。包含 50,000 个确定性 hres
输入、归一化与 namespace 偏移、一次 fallback、用户错误传播、generation retry。
这不是对真实 SMP 内存序或页映射权限的形式证明。

VM 检查两个在线 CPU，并在启动后等待/显式选择精确的 `tsc` 或 `jiffies`。
normal 配置的 RETPOLINE/RETHUNK/CPU_UNRET_ENTRY 均为 y；no-retpoline 均关闭；
两者都启用 CPU_MITIGATIONS 父选项，并核验解析后的配置。最终两个 bzImage 哈希不同。
完整结果和内核/模块哈希在 [validation/summary.json](validation/summary.json)。

VM 中 jiffies 用于实际进入不适合共享用户 provider 的 kernel-private 回退。
每次采集后模块成功卸载。VM 的 96 行计时字段仅用于确认执行和采集完整性，
不得混入物理机均值、bootstrap 或论文性能表。此次没有在 VM 注册真实用户 carrier，
也没有运行本版本的 PFN sharing 或完整 time-namespace 部署矩阵。

## 3. 编译结果：不是延迟数据

GCC 11.4，Linux 5.15.198，配对配置。字节为指定函数与其 `.cold` 符号之和，
不含对齐空隙。完整两构建结果在 [object-bytes.csv](validation/object-bytes.csv)。

| 函数 | Normal 基线字节 | Normal 候选字节 | 差值 |
| --- | ---: | ---: | ---: |
| ktime_get_ts64 | 68 | 36 | -32 |
| ktime_get_raw_ts64 | 54 | 22 | -32 |
| ktime_get_real_ts64 | 62 | 47 | -15 |
| ktime_get | 123 | 97 | -26 |
| ktime_get_raw | 109 | 83 | -26 |
| ktime_get_with_offset | 141 | 120 | -21 |
| __x64_sys_getcpu | 171 | 130 | -41 |

这些结果证明冗余分支确实从生成代码中消失；不证明 latency 按相同比例下降。
两个生产头文件合计增加 3 行非空非注释源码：显式完成契约换来了更小的调用端机器码。
新增测试/诊断代码不计为 Clocktime 功能实现。旧的 252/592 reader 定义清单也不能
由这里的字节数反推成全内核源码缩减率。

`.vkso.text` 对象字节相等不是最终链接地址、alternatives 后驻留字节或缓存布局完全
相同的证明。所有受影响内核/模块/载体应成套重建，不能将旧 carrier 与新内核拼接。

## 4. 新工具与实验完整性

在原 kernel-reader 中加入独立 `scalar_control`/`scalar_samples`，不修改原三 API
CSV schema 或 `experiment.sh` 入口。原 `run_batch` 的源码定义相同，但调用者改变
会影响编译器范围推断、寄存器选择和布局，不能声称旧/new probe 机器码一致。
A/B 两侧必须使用同一份新 probe 源码及各自匹配的内核构建，不能沿用旧 probe 数据。

`direct-api/scalar.py` 复用现有 package preflight、环境调优和采集锁，采集/汇总分离。
它保存原始 CSV、启动/内核/模块标识、参数和校验和；拒绝重复 boot、缺失/重复样本、
错误 CPU/iterations 以及组内混合内核。输出使用独立 scalar protocol，不会被当成
历史 formal READ 数据。未提供 `--execute` 时只检查包，不调优、不加载模块。
详细命令见 [README.md](README.md)。临时编译树/fixture 使用 TemporaryDirectory，
正常结束及 Python 异常展开时清理；保留的 logs、configs、CSV 和反汇编是正式验证证据。

## 5. 失败尝试及其处理

早期 VM 脚本在 `tsc-early` 尚未切换时检查 `tsc`，随后 word-boundary grep 又把
`tsc-early` 错当成 `tsc`。这两次启动检查均失败且未当作 PASS；现改为完整名称匹配、
有界等待及实际 current_clocksource 回读。

另一次 VM 检查通过但 tinyconfig 将 CPU_MITIGATIONS 关闭，两个配置得到相同镜像。
该次只作为共同配置的功能尝试，未列为最终两 mitigation 验证。当前强制检查 Kconfig
依赖解析结果，最终矩阵重新编译、重新启动并使用不同镜像完成。

额外本地全局 carrier-builder 检查并非全部通过：18 项中有两处环境/基线问题——
GCC 14 下原 manager.cpp 依赖传递头文件而缺少 uint32_t 定义，以及缺少 Python capstone。
这些不在本次生产改动中，没有冒充全仓库测试通过。使用本地 Linux 6.12 头文件编译
5.15 专用 reader 也因旧 no_llseek API 失败；没有为错误版本改代码，而改用真实 5.15.198
Kbuild 和 VM 完成目标版本验证。

## 6. 尚未完成的目标机验收

NUC 裸机 baseline/candidate 独立启动的 READ/UPDATE/标量延迟和 PMU：**NOT_RUN**。
新版本的完整 carrier 注册、namespace/PFN 与恢复部署验证：**NOT_RUN**。
现有 GitHub 授权不是 NUC shell 连接，不能用 CI/容器时间代替这些结果。

验收应保持相同构建变体，比较原 VKSO 内核与本候选内核，给两侧构建同一新 probe；
标量实验与原公开 READ、UPDATE 结果分开。更换内核之后新建独立数据集，不追加到历史
冻结 campaign。只有目标机功能和性能通过，才能给出“不回退”的发布结论。

当前结论：内核完成式接口的重复 fallback 已收敛，实际代码生成更小，目标版本的
对象编译与有限 VM 功能验证通过；标量算法改写和完整实机性能结论仍不属于本次已完成项。
