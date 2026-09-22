# 内核状态成本：与无插桩公开 READ 分开

新 collect 每次都会用同包构建的 kernel-reader 模块测量普通内核
`ktime_get_ts64`、`ktime_get_raw_ts64`、`ktime_get_coarse_ts64`，保存原始轮次。
这是同一 Raw/VKSO 实现的附加指标，不是另一种后端。

publisher/update 插桩与持续 readers + periodic update 代码继续保留在 `../update-bench/`。
其构建使用 `UPDATE_BENCH=1`，READ 包严格要求为 0，因此必须分开镜像、运行和结果。
这些流程本次没有在目标内核执行，状态为 NOT_RUN；旧包或历史结果不能冒充当前源码的新测量。

在 `vkso-tests/update-bench/` 下，现有入口为：

```bash
export NORMAL_PACKAGE="$PWD/../baremetal/artifacts/direct-update-normal"
export NO_RETPOLINE_PACKAGE="$PWD/../baremetal/artifacts/direct-update-no-retpoline"
BUILD_VARIANT=normal OUT="$NORMAL_PACKAGE" JOBS=4 ./build-update-images.sh
BUILD_VARIANT=no-retpoline OUT="$NO_RETPOLINE_PACKAGE" JOBS=4 ./build-update-images.sh
./verify-update-packages.sh "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"
sudo env NORMAL_PACKAGE="$NORMAL_PACKAGE" NO_RETPOLINE_PACKAGE="$NO_RETPOLINE_PACKAGE" ./install-update-grub.sh
./experiment-update.sh begin
./experiment-update.sh boot
# 每次重启后
./experiment-update.sh collect
# 按 status 完成四组。另一个 campaign 收集持续读写交互：
./experiment-concurrent.sh begin
./experiment-concurrent.sh boot
# 每次重启后
./experiment-concurrent.sh collect
```

构建时 build-images.sh 会调用原有 raw-integration.patch/prepare-raw-source.sh 准备原版源码，
配置、版本及 package verifier 不应绕过。上述是保留工具的执行入口，不是已经重验过的 v2 READ 采集。
先完成直接 API READ，再审计/运行这条插桩协议；不要把 publisher 成本混入 API 批量计时。
