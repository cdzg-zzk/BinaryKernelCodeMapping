# 当前工作树的验证范围

基线：`4be87be575fa74848574dc419b56769c0440a90e`。
本次修改来自实际 checkout，没有应用仓库根目录的旧 `direct-api-host-probe-fix-v2.patch`。
内核时间实现与 carrier 私有 ABI 未改写；修改的是公开库、打包/收集与实验内容。

| 检查 | 状态 | 证据范围 |
|---|---|---|
| `python3 .../direct-api/tests/test_direct.py` | PASS：30 项中 27 通过、3 SKIP | GCC 11.4.0；同名动态 API 的 errno、线程初始化、失败语义、反汇编、清单与数据检查、campaign 冻结/失败保留/推进/归档 |
| Native 快路径功能、无 syscall 诊断、短批次 smoke | SKIP：上述 3 项 | 当前宿主 native_vdso=0、vkso_mm_auxv=1；不能当成 Raw 测试 |
| 两个现有真实 carrier 的新公开库/两类 benchmark 编译与 ELF 检查 | PASS | namespace-sharing-normal 与 namespace-sharing-no-retpoline；只编译链接，不注册/执行共享核心 |
| 两种 carrier 下规范化路径后的用户二进制一致性 | PASS | native-bench、vkso-bench、libvkso_time.so 逐字节相同 |
| 改动的 Python AST、baremetal shell 语法、git diff --check | PASS | 静态检查 |
| 两个旧 namespace-sharing 包送入新 verifier | PASS：明确拒绝 | 缺 direct/ 和按 backend 构建的 reader 模块，不会把旧包当新包 |
| 四个新镜像与 coherent 包全量构建 | NOT_RUN | 本地没有原版 Linux 5.15.198 tarball；本轮交付构建入口，由操作者执行 |
| 新库在正确四种目标启动上的 ABI、seccomp、PFN、权限与恢复 | NOT_RUN | 需要新包构建、安装、启动后的 collect；源码 mock 不能替代 |
| 多 boot 正式性能与普通内核 reader 数据 | NOT_RUN | 按用户要求由操作者采集；没有生成论文性能结果 |
| Publisher/update 与持续读写交互 | NOT_RUN | 保留独立插桩协议，见 STATEFUL.md；没有复用历史数据冒充新结果 |

源码测试使用带 TEST ONLY 标记的 mock carrier 和合成 CSV，不能证明真实内核共享执行。
真实 carrier 链接检查仅证明当前 ABI 能构建链接，不代表新内核功能已通过。

历史正式 Redis 压缩包保持原位与原内容；旧 Redis preflight/build-repair 结果移到
`test/test_gettime/history/redis-results/`。旧协议代码和生成缓存/二进制已清理，Git 中可恢复。

## 2026-09-23 采集恢复与分层构建修复

- `test_direct.py`：39 项通过（当前 Raw 宿主上的本地 API smoke 也实际运行）；不是正式性能采集。
- `test_maintenance.py`：10 项通过，包含无需写回未修改 sysfs、真实恢复失败退出非零、
  脚本修复保留旧快照/包身份、C 或参数变化拒绝 refresh、六种选择性构建计划不执行编译。
- 实际执行 `build-all.sh bench-normal --out /tmp/direct-bench-repair-validation`：PASS，
  新用户态程序构建并通过包验证，原两份内核及 carrier 哈希保持不变。没有加载模块或采集正式性能。
- 现有 normal/no-retpoline 两包严格验证：PASS；Python/Shell 语法、diff 检查：PASS。
- 修复当时 campaign 已执行 refresh-tools，原始 campaign.json、raw-normal/run.json、samples.csv
  及两包 SHA256SUMS 保持逐字节不变；当时完成 1 boot，下一项 vkso-normal。
- 单个 Raw/VKSO 内核的实际编译与启动：NOT_RUN。选择性路径已接入构建工具并验证计划，
  运行功能仍须由新包所在目标内核的 collect 验证。

既有局部修复（Raw Module.symvers、结果证据审计与其测试）在此修复前已经存在，已保留。

## 2026-09-23 提交前复核

- 当前 VKSO 宿主：`test_direct.py` 39 项中 36 PASS、3 SKIP（需要原生 vDSO 的 Raw smoke）；
  `test_maintenance.py` 10 PASS。未重新运行正式性能测试或内核构建。
- baremetal Shell 语法检查及 `git diff --check`：PASS。
- `20260922T185408Z-direct-api` 已完成 4 blocks / 16 个独立 boot；原始数据审计与
  summary 重算一致，共 7,936 条用户 API 批次样本。归档 SHA-256 和 416 个逐 boot 文件一致。
  此为已有数据复核，不是新增采集；publisher/update interaction 仍为 NOT_RUN。
- 归档保留原始数据；后生成的 `summary.json` 需单独备份。首次 boot 早于工具快照机制，
  其余 15 个 boot 带工具版本。旧样本和归档均未修改。
- 本地 artifacts/results/validation、实验状态与 Python 缓存已有忽略规则；
  不将它们当作源码提交，也不删除实验结果和构建包。
