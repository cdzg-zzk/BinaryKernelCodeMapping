# M00 基线证据

## 1. Git 与源码身份

| 项目 | 值 |
|---|---|
| 开发分支 | `vkso-timekeeper-unification` |
| 分支设计起点 | `d89f2e5f8f9ae6fec353ead9cf4dcd77456b3ddd` |
| 起点说明 | `docs: finalize VKSO concurrent and code-size analysis` |
| 当前运行时代码锚点 | `be35a28c983f754650c2ddb3312a4e29796a2194` |
| 运行时代码说明 | `vkso: align shared clock ABI with fast paths` |
| 实际修改内核 | `test/test_gettime/linux-5.15.198-vkso` |
| 结构审计参考 | `test/test_gettime/linux-5.15.198-no-vdso` |
| Raw 语义参考 | Linux stable v5.15.198 |
| Kernel release | `5.15.198` |

`be35a28..d89f2e5` 在 VKSO kernel、functional wrapper 和 `make_dll`
范围内没有运行时代码差异。因此，`be35a28` 构建和采集的最终 reader/update
证据可以作为本分支 M00 运行时基线；后续文档提交不改变这个事实。

## 2. Reader 基线

### 2.1 原始结果

结果目录：

```text
test/test_gettime/vkso-tests/baremetal/results/
└── 20260728T090125Z-vkso-compact-read/
    ├── raw-normal/
    ├── vkso-normal/
    ├── raw-no-retpoline/
    └── vkso-no-retpoline/
```

四个 case 均有完成标记、`perf.csv`、`seq.csv` 和 76 行
`functional.matrix`。四份功能矩阵逐字节相同：

```text
61edf4f6563d0347ac75cf00dea36310de3c735dd945ede2216deff6c1a07a64
```

关键文件 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `experiment-manifest.txt` | `5bcf3fc44d6fc549ea4ab17b0bd346882b93499aba8be3308b228db25c773d1b` |
| Raw normal `perf.csv` | `1c865c93dc3e97750e50e2e7b84f8788112f36787aa16dd00691bf7b619ad148` |
| VKSO normal `perf.csv` | `2383a95484d5d60b120b196f94248475d5906de1793c5c214e080c5f4754c156` |
| Raw no-retpoline `perf.csv` | `0a2fbdcfed9e038adea44af5c82d6f73db3e9787fcce71bf0d3c662d4aa35836` |
| VKSO no-retpoline `perf.csv` | `66ee1223bac6c1bf1abfd22c358895fa645f95391f963046b5a2e583e0016544` |
| Raw normal `seq.csv` | `18b69a003e34686cf5e4476a61bebb3f0932617306fce8312b037df43fbdb6a8` |
| VKSO normal `seq.csv` | `d152c36be89287c6b7fb568c795f8982df433001ef096ed8c80d5d6bd98b0974` |
| Raw no-retpoline `seq.csv` | `e43fd6e9de1d0429c278341ce0269eb7c80ed66cb3b787e2d2009c471c655ef6` |
| VKSO no-retpoline `seq.csv` | `3b43b621257c01fa3a8813ea602ca21920eb5f328f405e75376c6f4d87717a49` |

### 2.2 构建包

| 变体 | 目录 | Raw Image SHA-256 | VKSO Image SHA-256 |
|---|---|---|---|
| normal | `vkso-tests/baremetal/artifacts/final-normal` | `78b50d6bc4ba8ebad31bf11c6964a1ca41db161c51097341b08db978e28a4129` | `0ce54bb41b06cf4c49ed2265a6eb7b5b436df280d8c2f6b40e188bb3ee5a092e` |
| no-retpoline | `vkso-tests/baremetal/artifacts/final-no-retpoline` | `602c013defca9911babedba39308565a258781729c2575a317730f5e5ac6625d` | `5673bb58f42092eb743bf95e32721bce23c57af4ce9f02f24f17c633019d1bb2` |

两个包的 `verify-packages.sh` 验证结果为：

```text
four_image_package_validation=pass
```

共同实验配置：

- `experiment.conf` SHA-256：
  `f843a7e1f59859fe00a071f5397d9c2b4d16df480b1fdee4f1d9730368797268`
- `ITERATIONS=500000`
- `REPEATS=31`
- `WARMUP=10000`
- `SEQ_ITERATIONS=100000000`
- `CPU=2`

### 2.3 已冻结结论

权威报告：

```text
test/test_gettime/vkso-tests/baremetal/VKSO_READ性能实验报告_20260728.md
SHA-256: 5eabdb7d14c7e385a0922abf6ee25f315c317dd21e63889b24a42ae24c47d94f
```

该报告只作为重构前历史基线。M01～M09 不重新解释或扩展其性能结论，M10
用完整重构后的新镜像重新采集。

## 3. Update-side 基线

### 3.1 原始结果

紧凑运行时代码的 paired update 结果：

```text
test/test_gettime/vkso-tests/update-bench/results/
└── 20260728T095735Z-update-side/
```

关键文件：

| 文件 | SHA-256 |
|---|---|
| `UPDATE_SUMMARY.md` | `761d99940a030a40a6ad8a3045381acf61b28064d9241d40bcc9c3e6341791a3` |
| `update-comparison.csv` | `ae465ec2024a1c3c3f1d486b0e6552dc1eaa76efa646849feddceb9b7d1fb0d1` |

Raw/VKSO 均有完成标记，功能矩阵各 76 行且逐字节相同。

### 3.2 构建包

紧凑 update 包：

```text
test/test_gettime/vkso-tests/baremetal/artifacts/prepared-20260728T094533Z
```

其 manifest 记录：

- Git commit：`66e7b1ef9b0047fd2c7f87ff6019ba91e5ee8253`
- VKSO source tree：
  `df32187680ba910d98c58775fa8b119a1db5703e03fb9ef5c3ac6fc1422b1cb8`
- Raw source tree：
  `fdba196b751997d68e900c4c958e9a3d1181644f6cbe6041f3d32b84a66720d0`
- Raw Image：
  `e639416310ce2b105f4560893741e0fce3fd3b3cecc24331faacc5784477895c`
- VKSO Image：
  `8dccb7ac9f255b81155206ca5a9309fc8ef57a6e5d84f2a08d9e2fdb39a0cf9b`
- manifest SHA-256：
  `8a829baf52f0ec85e18943fb13c1c72fffbb16d18c06b1c85447098e9e309693`

权威解释报告仍为：

```text
test/test_gettime/vkso-tests/update-bench/VKSO_UPDATE性能实验报告_20260728.md
SHA-256: 78e4ec2a521c596d0aea7a9e3cce85fb5243b211e5c407d3bab6689488f91cc0
```

报告中的正式 Raw/VKSO 基准批次是 `20260728T031855Z-update-side`；
`095735` 用于确认紧凑运行时代码没有改变 update 结论。最终 M10 必须重新
成对构建并采集，不能混用这两个批次做单变量结论。

## 4. Read/update 并发基线

原始结果：

```text
test/test_gettime/vkso-tests/update-bench/results/
└── 20260728T102145Z-update-concurrent/
```

关键文件：

| 文件 | SHA-256 |
|---|---|
| `CONCURRENT_SUMMARY.md` | `e5702c014568a2913a4bab75724d000df18cda5a40040720a61641ba67760c7a` |
| `update-comparison.csv` | `b04557b3ee24ba77fc4410c3fcda1eaedded62fccf9eb32018234e1e9cf95479` |

Raw/VKSO 均有完成标记，功能矩阵各 76 行且逐字节相同。

权威报告：

```text
test/test_gettime/vkso-tests/update-bench/VKSO_READ_UPDATE并发性能实验报告_20260728.md
SHA-256: 062294626fac66cbb5ffa4d105d1efb855726997bbf5433302aa0c18a551a061
```

## 5. 代码规模基线

现有人工语义报告：

```text
test/test_gettime/vkso-tests/code-size/VKSO开发工作量与代码规模评估_20260728.md
SHA-256: c693441728e2a9f60b60b202b60fc878b0f69e0f67e859823105fc5aa271e32d
```

M00 冻结的旧实现结论：

| 指标 | Raw | VKSO 当前原型 | 差异 |
|---|---:|---:|---:|
| 产品功能 SLOC | 1,201 | 1,102 | -99（-8.24%） |
| user 专属 SLOC | 593 | 126 | -467（-78.75%） |
| reader 维护切片 SLOC | 718 | 593 | -125（-17.41%） |
| reader 机器码 | 2,497 B | 2,401 B | -96 B（-3.84%） |
| 发布函数机器码 | 575 B | 459 B | -116 B（-20.17%） |
| shared payload | 480 B | 184 B | -296 B |

其中 60 SLOC `timekeeper → shared_data` compat 转换是本次统一重构必须消除的
明确目标。上述数字不直接沿用为最终数字，M08/M10 将按
`CODE_SIZE_MANIFEST.md` 的同一语义边界重新人工审计和复算。

## 6. M00 验证结果

- 分支与起点：通过；
- `be35a28..d89f2e5` 运行时范围无差异：通过；
- reader 四镜像包 hash/config 校验：通过；
- reader 四 case 完整且功能矩阵相同：通过；
- update paired 结果完整且功能矩阵相同：通过；
- concurrent paired 结果完整且功能矩阵相同：通过；
- 性能、源码和机器码报告均可定位：通过；
- 后续仅修改 VKSO kernel、wrapper/测试和本计划目录：已锁定。

M00 通过后，M01 只做结构审计和文档产物，不修改运行时行为。
