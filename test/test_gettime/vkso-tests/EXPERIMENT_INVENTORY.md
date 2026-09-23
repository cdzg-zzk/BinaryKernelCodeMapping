# Clocktime 实验目录梳理（当前源码）

当前维护的正式协议见 [RUN_STATEFUL.md](update-bench/RUN_STATEFUL.md)。本索引按 **代码是否进入当前采集路径** 划分，避免把历史测试或旧结果称作新证据。

| 路径 | 当前作用 | 当前协议状态 |
| --- | --- | --- |
| `functional/`、`m09-posix-clock/` | ABI matrix、私有 wrapper、动态 clock 回退验证模块 | 采集前功能核验 |
| `direct-api/time_bench.c`、`vkso_public.c`、`vkso_time_init.c` | Raw libc/vDSO 与 VKSO 直接链接公开 API | clean READ 和 UPDATE 的正确性核验 |
| `direct-api/stateful_reader.c` | 持续调用同一公共 API 的用户 reader | 仅 UPDATE 插桩镜像的并发阶段 |
| `direct-api/collect.py`、`results.py`、`sharing.py`、`mapping_census.py` | clean READ 采集、校验/统计、VKSO PFN/权限、活进程命名映射 PFN 清点 | clean 每次启动 |
| `baremetal/build-all.sh`、`build-images.sh`、`verify-packages.sh`、`install-grub.sh` | clean 镜像和包 | 构建/安装 |
| `baremetal/experiment.sh`、`boot-once.sh`、`collect-case.sh` | 唯一公开启动/采集入口及 clean 子采集器 | 正式 |
| `update-bench/prepare-raw-source.sh`、`build-update-images.sh`、`verify-update-packages.sh`、`install-update-grub.sh` | Raw/VKSO 的 UPDATE 插桩镜像和包 | 构建/安装 |
| `update-bench/stateful.py`、`boot-update-once.sh` | 八镜像计划、身份核验、UPDATE 和持续 reader、全量汇总 | 正式 |
| `direct-api/bundle.py`、`package_check.py`、`rebuild.py` | 链接/审计/选择性重建；包内保存源码和校验和 | 正式 |
| `direct-api/tests/`、`update-bench/tests/` | 源码与模拟控制测试 | 本地校验；不能替代目标内核 |
| `revision/kernel-reader/` | 当前普通内核 reader 测试模块源码 | 构建仍依赖；`revision/` 其余采集/分析属于历史协议 |
| `code-size/` | 旧语义范围 SLOC 清单与旧机器码分析 | 历史；新包改用当前 ELF section 证据 |
| `namespace-sharing/` | time namespace MM_data 的独立生命周期/KVM 核验 | 历史功能依据；其旧结果不并入本次统计 |
| `optimization-audit/` | 旧候选入口、代码生成和内存诊断 | 历史候选依据；不作为本次性能结果 |
| `../vkso-timekeeper-unification/`、`../history/` | 设计报告和 Redis 历史记录 | 不进入当前构建/采集 |

`revision/`、`code-size/`、`namespace-sharing/` 与根目录旧报告记录之前的实现、协议和结果。`macro-benchmark/` 的 Redis/`adapter.so` 不在当前主结果里。`baremetal/vkso_time_bench.c`、旧 QEMU 脚本、`update-bench/compare-update.py` 和若干兼容 shell 名称也属于旧测试接口；当前构建仍打包一部分旧二进制以保持包/旧验证脚本兼容，但 `experiment.sh` 不执行它们，其数字不可拼接到当前 summary。旧结果目录采用各自协议名，当前入口只写入新 `clocktime-full-v1` 结果目录。

旧 `collect-update-side.sh`、`collect-update-concurrent.sh`、`boot-raw-update.sh`、`boot-vkso-update.sh` 已明确拒绝单独执行，避免绕过统一计划；新 UPDATE 包不再包含这些入口。`experiment-update.sh` 与 `experiment-concurrent.sh` 只作为指向统一控制器的兼容别名。

本次清空了 `baremetal/results/`、`update-bench/results/` 中的旧正式采样，并移走旧 campaign 状态；`namespace-sharing/results/`、`optimization-audit/results/` 和 `history/redis-results/` 保留为上述历史文档所需的功能/候选依据。当前 `experiment.sh status` 为 `not-started`。

## 当前证据和缺口

- **当前采集覆盖：** 16 个公开 READ 项、三种普通内核 reader、空闲 UPDATE、三种持续用户读取下的 UPDATE/reader、ABI/错误回退、fast-path 无 time syscall、共享 PFN/权限/restore、1/8/32 进程命名时间映射的驻留 PFN。包另保存当前镜像/DSO 的 `.text` 字节数。每个动态模式四个独立启动块。
- **未由本协议测量：** 全系统净 RAM、序列锁 retry 次数、完整中断/锁等待成本、Redis 或其他应用级吞吐。历史图表不可直接填这些空白。
- **解释限制：** UPDATE 插桩代码自身影响缓存；clean READ 与 instrumented UPDATE 是不同镜像；当前改动还涉及状态组织和入口，因此 Raw/VKSO 差异不能全部归因于物理共享。

`.text` 与命名映射 PFN 是明确限定范围的代码/内存指标。若论文要声称“总 RAM 降低”，还需另设整机资源实验；不能由 `sharing.json` 或 `resource.json` 推断。
