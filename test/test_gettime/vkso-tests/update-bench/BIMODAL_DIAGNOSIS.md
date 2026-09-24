# UPDATE 双峰诊断

这是独立的诊断运行，不属于 32 次正式 Clocktime campaign。它只使用 normal
配置的 Raw/VKSO UPDATE 内核。`start` 仍导出原来的四列正式样本；诊断命令
`diagnose` 在**计时结束后、timekeeper 锁释放前**补记状态，并单独导出当前
writer CPU 上的 4096 个空 `rdtsc_ordered` 计时对。诊断内核和正式内核的绝对
UPDATE 耗时不可直接合并。

在 `test/test_gettime/vkso-tests/baremetal/` 执行一次构建和安装。输出路径必须
尚不存在；如果 `/tmp/vkso-raw-update-source` 不在，需要提供未修改的 Linux
5.15.198 源码目录作为 `RAW_SOURCE`，或提供 tarball 作为 `RAW_TARBALL`。

```bash
cd test/test_gettime/vkso-tests/baremetal
export DIAG_PACKAGE="$PWD/artifacts/update-bimodal-normal-v1"
JOBS=4 OUT="$DIAG_PACKAGE" BUILD_VARIANT=normal ../update-bench/build-update-images.sh
python3 ../update-bench/stateful.py verify --package "$DIAG_PACKAGE"
sudo env NORMAL_PACKAGE="$DIAG_PACKAGE" ../update-bench/install-update-grub.sh --normal-only
```

`--normal-only` 复用已安装的两个 normal UPDATE GRUB 条目，并只替换其镜像与
配置；旧 no-retpoline 条目不变。必须先有正式实验安装过的 GRUB 条目。
正式结果目录和旧包不会被修改。

Raw 启动（这条命令会重启）：

```bash
../update-bench/boot-update-once.sh raw-normal
```

重启后重新设置包路径，再采集。输出目录必须尚不存在。

```bash
cd test/test_gettime/vkso-tests/baremetal
export DIAG_PACKAGE="$PWD/artifacts/update-bimodal-normal-v1"
./experiment.sh diagnose --package "$DIAG_PACKAGE" --case raw-normal \
  --out "$PWD/results/update-bimodal-raw-normal-boot1"
../update-bench/boot-update-once.sh vkso-normal
```

第二次重启后：

```bash
cd test/test_gettime/vkso-tests/baremetal
export DIAG_PACKAGE="$PWD/artifacts/update-bimodal-normal-v1"
./experiment.sh diagnose --package "$DIAG_PACKAGE" --case vkso-normal \
  --out "$PWD/results/update-bimodal-vkso-normal-boot1"
```

建议再各启动一次，分别用 `boot2` 输出目录。每次采集是 4 个场景 × 3 轮 ×
10 秒 writer 窗口，另有稳定期和功能核验。`diagnose` 会验证实际运行的镜像、
config、boot cmdline、auxv、包、ABI、公开 API 与 VKSO 物理页；错误内核会
在计时前失败，不会把失败记录标为 COMPLETE。

全部采集后汇总；缺少某次运行时从 `--runs` 列表去掉即可。

```bash
./experiment.sh diagnose-report \
  --runs "$PWD/results/update-bimodal-raw-normal-boot1" \
         "$PWD/results/update-bimodal-vkso-normal-boot1" \
         "$PWD/results/update-bimodal-raw-normal-boot2" \
         "$PWD/results/update-bimodal-vkso-normal-boot2" \
  --out "$PWD/results/update-bimodal-report.json"
```

报告按**启动**保留每个场景的模式占比、两个模式的中位 TSC ticks、空计时对
分布、状态标记条件下的高峰比例、以及秒内相位分桶。模式边界沿用先前正式
normal 结果的谷值：Raw 120、VKSO 110 TSC ticks；这是描述性分组，不能
单凭数值边界认定 Raw/VKSO 的高低峰属于相同内部状态。若某标记在各次启动
都稳定预测高峰，下一步再做独立的分段计时诊断，验证对应阶段的耗时来源。
