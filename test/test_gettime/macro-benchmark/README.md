# 四种内核的固定 macrobench 入口

使用已有 `../vkso-tests/baremetal/experiment.sh`，命令接口不变。本目录只保留 Redis 负载、libc bridge、源包和历史接入证据；不再提供独立内核切换控制器。参数集中在 [experiment.conf](../vkso-tests/baremetal/experiment.conf)，测量口径见 [PROTOCOL.md](PROTOCOL.md)。

本次按要求只整理脚本，未执行新版本采集、KVM 测试或重启。之前的 preflight 结果不代表本次整合版本已经运行通过。

## 一次性准备

已有旧镜像不包含最新 VKSO 修改，先构建新配对包。完整包不覆盖；上次失败留下的不完整目录会自动改名保留，再重新构建。

```bash
cd /home/zzk/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export NORMAL_PACKAGE="$PWD/artifacts/namespace-sharing-normal"
export NO_RETPOLINE_PACKAGE="$PWD/artifacts/namespace-sharing-no-retpoline"
export BUILD_ROOT=/tmp/clocktime-macro-build
JOBS=4 ./build-all.sh && \
sudo env NORMAL_PACKAGE="$NORMAL_PACKAGE" \
  NO_RETPOLINE_PACKAGE="$NO_RETPOLINE_PACKAGE" ./install-grub.sh
```

build-all 会构建新版 VKSO 两种 mitigation 配置、构建一次 Redis/bridge 并打入两个包，核对四镜像配置及工具一致性；不自动运行 QEMU/benchmark。当前机器缺少 `/tmp/linux-5.15.198.tar.xz`，会使用已有 `reader-load-v4-{normal,no-retpoline}` 包中的原生 vDSO 镜像。若提供该 tarball，则从原始源码重建 vDSO 镜像；RAW_SOURCE 需为尚不存在的目录。

install-grub 更新四个既有 `vkso-final-*` 启动项和对应镜像，不发起重启，也不改变普通系统的默认启动项。新配置把 CPU 1–3 留给负载，所以即使已有旧启动项，也要执行此次安装。

构建只在临时源码副本中清理旧 Kbuild 生成文件，不对维护中的内核源码执行 mrproper。两个包均完成核验后才发布到上述正式目录；失败不会留下一个看起来可安装的正式包。完整日志在 `$BUILD_ROOT/build-*.log`。构建与安装之间使用 `&&`，保证构建失败时不会继续安装。

## 四种配置按顺序采集

第一条 boot 在上面的同一终端执行，使新包路径写入实验状态；后续重启只需重新进入 baremetal 目录，包路径会从状态恢复，无须重新 export。

```bash
# 1. 原生 vDSO，retpoline/rethunk 开启；本命令立即重启。
./experiment.sh boot raw-normal
# 重启、登录后，重新 cd 到 baremetal 目录：
./experiment.sh collect raw-normal

# 2. VKSO，retpoline/rethunk 开启
./experiment.sh boot vkso-normal
# 重启后：
./experiment.sh collect vkso-normal

# 3. 原生 vDSO，retpoline/rethunk 等相关配置关闭
./experiment.sh boot raw-no-retpoline
# 重启后：
./experiment.sh collect raw-no-retpoline

# 4. VKSO，retpoline/rethunk 等相关配置关闭
./experiment.sh boot vkso-no-retpoline
# 重启后：
./experiment.sh collect vkso-no-retpoline

# 随时查看进度和结果目录；不会启动测试或重启：
./experiment.sh status
```

这些命令要逐步执行，不要整段一次粘贴。boot/collect 所需的特权操作由现有脚本调用 sudo；collect 不会自动切换到下一内核。

每次 collect 保留原有 ABI、READ 和 seq 采集，并追加 Redis GET/SET × pipeline 1/16。Raw case 内同时保留 native libc 与 vDSO bridge 对照，VKSO case 使用 VKSO bridge；客户端统一用 syscall 计时。默认 7 轮，每负载每轮 300 万请求，参数在开始新 run 前修改 experiment.conf，运行中不改。

如果在第一次 boot 前关闭了配置包路径的终端，重新执行上面的两行 export；若状态已经 active，直接按 status 提示继续，不要创建新 run。

## 结果

```text
baremetal/results/<run>/
  raw-normal/redis/{native,vdso}/measurements.csv
  vkso-normal/redis/vkso/measurements.csv
  raw-no-retpoline/redis/{native,vdso}/measurements.csv
  vkso-no-retpoline/redis/vkso/measurements.csv
```

各目录同时保存每轮原始 CSV、服务日志、INFO、maps/smaps、CPU 时间及完成记录。原有 `perf.csv`、`seq.csv` 和功能记录仍在各 case 根目录。四个 case 完成后自动生成 `results/<run>.tar.gz`，可直接交回分析。

失败时保留在 `results/<run>/incomplete/`，不推进 case。修复后在同一正确内核重新 collect 当前 case。单轮四次启动得到描述性对比；跨启动统计需要重复完整四-case 轮次，不能把同一 boot 的 7 轮当作 7 次独立启动。
