# Clocktime 实验目录梳理（当前源码）

当前维护的正式协议见 [RUN_STATEFUL.md](update-bench/RUN_STATEFUL.md)。本索引按 **代码是否进入当前采集路径** 划分，避免把历史测试或旧结果称作新证据。

| 路径 | 当前作用 | 当前协议状态 |
| --- | --- | --- |
| `functional/`、`m09-posix-clock/` | ABI matrix、私有 wrapper、动态 clock 回退验证模块 | 采集前功能核验 |
| `direct-api/time_bench.c`、`vkso_public.c`、`vkso_time_init.c` | Raw libc/vDSO 与 VKSO 直接链接公开 API | clean READ 和 UPDATE 的正确性核验 |
| `direct-api/stateful_reader.c` | 持续调用同一公共 API 的用户 reader | 仅 UPDATE 插桩镜像的并发阶段 |
| `direct-api/collect.py`、`results.py`、`sharing.py` | clean READ 采集、校验/统计、VKSO PFN/权限检查 | clean 每次启动 |
| `baremetal/build-all.sh`、`build-images.sh`、`verify-packages.sh`、`install-grub.sh` | clean 镜像和包 | 构建/安装 |
| `baremetal/experiment.sh`、`boot-once.sh`、`collect-case.sh` | 唯一公开启动/采集入口及 clean 子采集器 | 正式 |
| `update-bench/prepare-raw-source.sh`、`build-update-images.sh`、`verify-update-packages.sh`、`install-update-grub.sh` | Raw/VKSO 的 UPDATE 插桩镜像和包 | 构建/安装 |
| `update-bench/stateful.py`、`boot-update-once.sh` | 八镜像计划、身份核验、UPDATE 和持续 reader、全量汇总 | 正式 |
| `direct-api/bundle.py`、`package_check.py`、`rebuild.py` | 链接/审计/选择性重建；包内保存源码和校验和 | 正式 |
| `direct-api/tests/`、`update-bench/tests/` | 源码与模拟控制测试 | 本地校验；不能替代目标内核 |

`revision/`、`code-size/`、`namespace-sharing/` 与根目录旧报告记录之前的实现、协议和结果。`macro-benchmark/` 的 Redis/`adapter.so` 不在当前主结果里。`baremetal/vkso_time_bench.c`、旧 QEMU 脚本、`update-bench/compare-update.py` 和若干兼容 shell 名称也属于旧测试接口；当前构建仍打包一部分旧二进制以保持包/旧验证脚本兼容，但 `experiment.sh` 不执行它们，其数字不可拼接到当前 summary。旧结果目录采用各自协议名，当前入口只写入新 `clocktime-full-v1` 结果目录。

## 当前证据和缺口

- **当前采集覆盖：** 16 个公开 READ 项、三种普通内核 reader、空闲 UPDATE、三种持续用户读取下的 UPDATE/reader、ABI/错误回退、fast-path 无 time syscall、共享 PFN/权限/restore。每个模式四个独立启动块。
- **未由本协议测量：** 全系统净 RAM、当前版本的代码量对照、序列锁 retry 次数、完整中断/锁等待成本、Redis 或其他应用级吞吐。历史图表不可直接填这些空白。
- **解释限制：** UPDATE 插桩代码自身影响缓存；clean READ 与 instrumented UPDATE 是不同镜像；当前改动还涉及状态组织和入口，因此 Raw/VKSO 差异不能全部归因于物理共享。

新的代码量/RAM 实验应单独定义比较边界与进程数，再在这八镜像的同版本包上执行；不要用 `sharing.json` 的选定 PFN 数声称“总 RAM 降低”。
