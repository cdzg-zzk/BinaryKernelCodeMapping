# Clocktime 固定执行入口

正式协议为 **Raw/VKSO × Normal/no-retpoline × clean/UPDATE**，共八镜像、四个启动块。

完整构建、安装、32 次独立启动、采集和汇总命令见 [RUN_STATEFUL.md](../update-bench/RUN_STATEFUL.md)。

- `build-all.sh`：重新构建四镜像与 coherent 包，默认 `artifacts/direct-{normal,no-retpoline}`。
- `verify-packages.sh`：严格验证配置、身份、carrier 和 direct API 文件。
- `install-grub.sh`：安装四镜像；不自动采样。
- `experiment.sh begin|status|boot [MODE:CASE]|collect [MODE:CASE]|aggregate|refresh-tools|stop [REASON]`：唯一正式流程。
- `experiment.conf`：构建前配置；默认四个独立启动块。

`boot` 会立即重启。新流程使用 `.clocktime-full-state.json`，不读取旧性能数据。旧 QEMU、revision、单独 UPDATE 报告是历史记录，不是本次采集入口。

脚本修复使用 `./experiment.sh refresh-tools`，不重建内核；选择性构建用 `./build-all.sh CASE --out NEW_PACKAGE`，详见上方执行说明。
