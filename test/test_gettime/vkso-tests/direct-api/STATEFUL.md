# Clocktime 状态成本

当前命令与镜像矩阵见 [RUN_STATEFUL.md](../update-bench/RUN_STATEFUL.md)。无插桩镜像测完整公开 API READ 和普通内核 reader；UPDATE 插桩镜像测空闲 periodic writer 与三种持续用户读取下的 writer/reader。两类镜像在同一 32-boot campaign 中采集、分别汇总，所有 Raw/VKSO 差值均保留原始 TSC ticks。

UPDATE 的测量窗口在 `timekeeping_update()` 内、持有 timekeeper lock 后，不包含锁等待或完整定时器中断；持续 reader 批次覆盖包围 writer 窗口的加载区间。物理共享核验在计时前完成。旧单独 UPDATE、CONCURRENT 命令和结果只作为历史记录，不能填入当前协议表格。
