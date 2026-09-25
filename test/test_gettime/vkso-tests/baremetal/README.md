# Clocktime 固定执行入口

正式协议为 **Raw/VKSO × Normal/no-retpoline × clean/UPDATE**，共八镜像、四个启动块。

完整构建、安装、32 次独立启动、采集和汇总命令见 [RUN_STATEFUL.md](../update-bench/RUN_STATEFUL.md)。

- `build-all.sh`：一键自动构建 clean/UPDATE × normal/no-retpoline 四个 coherent 包；按当前源码变化复用包、重制公共库/carrier，或增量构建内核。`build-all.sh full` 保留从零构建 clean 内核的旧入口。
- `verify-packages.sh`：严格验证配置、身份、carrier 和 direct API 文件。
- `install-grub.sh`：安装四镜像；不自动采样。
- `experiment.sh begin|status|boot [MODE:CASE]|collect [MODE:CASE]|aggregate|refresh-tools|stop [REASON]`：唯一正式流程。
- `experiment.conf`：构建前配置；默认四个独立启动块。

`boot` 会立即重启。新流程使用 `.clocktime-full-state.json`，不读取旧性能数据。旧 QEMU、revision、单独 UPDATE 报告是历史记录，不是本次采集入口。

脚本修复使用 `./experiment.sh refresh-tools`，不重建内核；选择性构建用 `./build-all.sh CASE --out NEW_PACKAGE`，详见上方执行说明。

直接运行 `JOBS=4 ./build-all.sh` 即可。成功后脚本写出
`artifacts/clocktime-auto-current.env`，其中是本次四个已验证包的路径；安装前
运行 `source artifacts/clocktime-auto-current.env`。任何一个包失败时，不推进
`clocktime-auto-current-*` 链接，也不覆盖旧包或结果。

选择性构建按 `read|update` 和 `normal|no-retpoline` 保留独立的
`artifacts/.kbuild-cache/`。`vkso-*` 第一次建立缓存仍需编译内核；以后 Kbuild
在同一路径增量编译受影响对象并重新链接镜像。只改公共 API/benchmark 用
`bench-*`，不编译内核。只改 `functional/vkso_user_entry.S` 等 carrier 用户入口、
且内核源码未变时，用 `carrier-*` 重制 `libkernel.so`，再用 `bench-*` 更新公共库：

```bash
./build-all.sh carrier-normal --package OLD_PACKAGE --out NEW_STAGE
./build-all.sh bench-normal --package NEW_STAGE --out NEW_PACKAGE
# UPDATE 包使用 ../update-bench/build-update-images.sh 的相同目标和参数。
```

`carrier-*` 要求相应的 Kbuild 缓存中有与父包字节相同的内核镜像、配置和
`vmlinux`；没有缓存时须先运行一次 `vkso-*` 建立缓存。每次输出仍是新包，
旧包和历史结果不覆盖。头文件、配置或内核源码改动可能使 Kbuild 重编多个
依赖对象，不能保证严格只有一个 `.o` 被编译。
