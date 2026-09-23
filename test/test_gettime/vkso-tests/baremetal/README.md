# Clocktime 固定执行入口

正式协议为 **Raw/VKSO × Normal/no-retpoline 的直接公开 API READ**。

完整构建、四组启动、采集、独立启动重复和汇总命令见 [direct-api/README.md](../direct-api/README.md)。

- `build-all.sh`：重新构建四镜像与 coherent 包，默认 `artifacts/direct-{normal,no-retpoline}`。
- `verify-packages.sh`：严格验证配置、身份、carrier 和 direct API 文件。
- `install-grub.sh`：安装四镜像；不自动采样。
- `experiment.sh begin|status|boot [CASE]|collect [CASE]|aggregate|refresh-tools|stop [REASON]`：唯一正式流程。
- `experiment.conf`：构建前配置；默认四个独立启动块。

`boot` 会立即重启。旧 `.experiment-state` 和既有 `results/*.tar.gz` 保留，新流程使用 `.direct-api-state.json`，不读取旧性能数据。旧 QEMU、revision 和 UPDATE 工具保留作独立验证/历史用途，不是本次 READ 的另一个入口。

脚本修复使用 `./experiment.sh refresh-tools`，不重建内核；选择性构建用 `./build-all.sh CASE --out NEW_PACKAGE`，详见上方执行说明。
