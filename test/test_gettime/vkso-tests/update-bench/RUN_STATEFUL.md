# Clocktime 全量实验（当前协议）

入口固定为 `../baremetal/experiment.sh`。一次 campaign 包含四种实现/编译组合，每种分别在无插桩 READ 内核和带 UPDATE 插桩内核上启动：每块 8 次启动，默认 4 块、共 32 次独立启动。每次启动只采集当前镜像能可靠提供的证据；不能把同一次启动中的多轮当作独立样本。

| 镜像 | 同次 `collect` 获取的证据 |
| --- | --- |
| clean Raw/VKSO | 公共时间 API 全矩阵 READ、普通内核 reader、1/8/32 进程的用户时间映射驻留 PFN 清点、ABI/错误与回退行为；VKSO 另核验共享物理页、权限与 restore |
| UPDATE Raw/VKSO | ABI/错误与回退、fast-path 无 time syscall；空闲 periodic writer UPDATE，以及 monotonic、monotonic_raw、monotonic_coarse 三种持续用户读取负载下的 writer/reader；VKSO 另核验共享物理页与 restore |

Raw 的公开入口由 libc 调用原生 vDSO；VKSO 程序在链接时绑定 `libvkso_time.so`，经 carrier-private 入口到内核驻留共享代码。测试不使用 Redis、`adapter.so`、`LD_PRELOAD` 或逐次动态查找。READ 与 UPDATE 是不同内核构建，不能把两者的计数直接解释为同一个运行环境的数值。计数单位是 **TSC ticks**，不是已校准的 core cycles；READ 与并发 reader 报告完整调用批次的 ticks/call，UPDATE 报告插桩窗口中的 ticks/update。

PFN 清点由独立 Python worker 在计时前一次性定位公开函数并预触碰映射；它只产生资源证据，不进入 READ/UPDATE 计时路径。

## 构建与安装

以下命令在实验机、仓库分支的最终源码上执行。要求 GCC 11.4.0、Linux 5.15.198 原始源码压缩包，及可用的 `/boot`/GRUB。使用全新的输出路径；脚本拒绝覆盖旧包。构建和启动会占用很长时间，助手没有代替研究者执行。

```bash
cd /home/zzk/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export RAW_TARBALL=/tmp/linux-5.15.198.tar.xz
if [ ! -s "$RAW_TARBALL" ]; then
  curl -fL --retry 3 https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.15.198.tar.xz -o "$RAW_TARBALL"
fi
test -s "$RAW_TARBALL"
export NORMAL_PACKAGE="$PWD/artifacts/clocktime-full-v1-clean-normal"
export NO_RETPOLINE_PACKAGE="$PWD/artifacts/clocktime-full-v1-clean-no-retpoline"
JOBS=4 ./build-all.sh
./verify-packages.sh "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"

cd ../update-bench
export UPDATE_NORMAL_PACKAGE="$PWD/../baremetal/artifacts/clocktime-full-v1-update-normal"
export UPDATE_NO_RETPOLINE_PACKAGE="$PWD/../baremetal/artifacts/clocktime-full-v1-update-no-retpoline"
export RAW_SOURCE=/tmp/clocktime-full-v1-raw-update-source
JOBS=4 CC=gcc BUILD_VARIANT=normal OUT="$UPDATE_NORMAL_PACKAGE" ./build-update-images.sh
JOBS=4 CC=gcc BUILD_VARIANT=no-retpoline OUT="$UPDATE_NO_RETPOLINE_PACKAGE" ./build-update-images.sh
./verify-update-packages.sh "$UPDATE_NORMAL_PACKAGE" "$UPDATE_NO_RETPOLINE_PACKAGE"

cd ../baremetal
sudo env NORMAL_PACKAGE="$NORMAL_PACKAGE" NO_RETPOLINE_PACKAGE="$NO_RETPOLINE_PACKAGE" ./install-grub.sh
sudo env NORMAL_PACKAGE="$UPDATE_NORMAL_PACKAGE" NO_RETPOLINE_PACKAGE="$UPDATE_NO_RETPOLINE_PACKAGE" ../update-bench/install-update-grub.sh
```

`NORMAL_PACKAGE`/`NO_RETPOLINE_PACKAGE` 指向 clean 包；`UPDATE_*` 指向插桩包。`experiment.sh begin` 必须能同时验证这四个包，并要求八个镜像的 VKSO 源码、候选补丁和公共 API 源码身份一致。构建期间不要改源码。新构建会给 Raw 镜像单独编译时钟模块；旧包缺少 `raw-m09-clock.ko` 会被拒绝，应重新构建，不要补造身份文件。

## 采集与汇总

```bash
cd /home/zzk/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
./experiment.sh begin
./experiment.sh status
./experiment.sh boot
# boot 选择下一项 GRUB 条目并重启；登录后：
./experiment.sh collect
./experiment.sh status
# 若 status=active，再执行 ./experiment.sh boot；重复到 completed_boots=32、status=complete
./experiment.sh aggregate
```

`status` 的 `next_mode` 和 `next_case` 是下次必须启动的镜像。`boot`/`collect` 可加 `read:raw-normal` 一类参数作断言，但不能跳过计划。若只修脚本，运行 `./experiment.sh refresh-tools`，保留已采集的结果；改内核或 benchmark 二进制必须生成新包并开始新的 campaign。选择性构建可用 `./build-all.sh raw-normal|vkso-normal|bench-normal --package OLD --out NEW`，UPDATE 包用 `../update-bench/build-update-images.sh` 的相同参数；先用 `--plan` 看改动范围。

第一块的八个 `next_mode:next_case` 依次为 `read:raw-normal`、`update:raw-normal`、`read:vkso-normal`、`update:vkso-normal`、`read:raw-no-retpoline`、`update:raw-no-retpoline`、`read:vkso-no-retpoline`、`update:vkso-no-retpoline`。后续块自动轮换四种实现的次序；每项仍需独立重启，不能在同一启动内连续调用两次 `collect`。

完成数据在 `baremetal/results/<run>/block-NN/{read,update}/<case>/`，失败尝试留在 `incomplete/`；汇总是同级 `<run>-summary.json`，原始归档是 `<run>.tar.gz`。聚合重新校验每个目录和独立 boot identity，分别输出 READ 用户、READ 内核、空闲/并发 UPDATE 的 Raw/VKSO 绝对 ticks 差和比例。脚本拒绝错误内核、镜像、config、auxv、包身份或已使用的 boot；正式执行前的功能核验不计入计时。

新包还保存 Raw/VKSO `vmlinux`、Raw vDSO、VKSO carrier 和公开库的 ELF section 清单；静态主对照只取 clean 包。汇总中的 `.text` 字节数是静态代码规模；`bzImage` 是压缩文件大小。carrier 的 grafted text 与内核 text 是同一物理页，不能把两者简单相加作为 RAM。`mapping_footprint` 只清点活跃进程的 `[vdso]`/`[vvar]` 或 MM_data/carrier/公开库等命名用户映射，报告唯一驻留 PFN；不等于整机净内存。

`refresh-tools` 只允许改采集/汇总代码和文档；修改 `direct-api` 的编译源需要重新打包。目标机上请记录 `./experiment.sh status` 与 `aggregate` 输出；安装、32 次目标启动、实际 UPDATE 数据和内核资源结果目前均为 **NOT_RUN**。

## 证据边界

当前协议直接覆盖公共 READ、普通内核 READ、空闲 UPDATE、三种持续读取下 UPDATE，以及同版本静态代码规模和活进程命名映射的 PFN 规模。`sharing.json` 与 `resource.json` 仍不能证明全系统净 RAM 差值。历史 `code-size/` 与 `namespace-sharing/` 数值对应旧实现，不作为本版本结论。序列重试次数、更多 provider 和生产负载（含 Redis）属于另行设计的扩展，不在这 32 次正式启动内。不要把无显著差异解释为等价，也不要把全部差异归因于页共享。
