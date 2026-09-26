# Clocktime 状态成本

当前命令与镜像矩阵见 [RUN_STATEFUL.md](../update-bench/RUN_STATEFUL.md)。无插桩镜像测完整公开 API READ 和普通内核 reader；UPDATE 插桩镜像测空闲 periodic writer 与三种持续用户读取下的 writer/reader。两类镜像在同一 32-boot campaign 中采集、分别汇总，所有 Raw/VKSO 差值均保留原始 TSC ticks。

UPDATE 的测量窗口在 `timekeeping_update()` 内、持有 timekeeper lock 后，不包含锁等待或完整定时器中断；持续 reader 批次覆盖包围 writer 窗口的加载区间。物理共享核验在计时前完成。旧单独 UPDATE、CONCURRENT 命令和结果只作为历史记录，不能填入当前协议表格。

## 已采集数据的分布分析

`aggregate` 保留原有统计定义和归档行为。`distribution-report` 是同一入口的
离线分析命令，不读取当前 campaign 的运行状态，不启动测试，不需要 sudo、
重编或重启；输入仍通过现有完整 campaign 校验。需要 Python numpy 和
matplotlib。输出必须是原始结果目录之外的新目录，旧结果和 summary 不修改。

```bash
cd test/test_gettime/vkso-tests/baremetal
./experiment.sh distribution-report \
  --runs "$PWD/results/20260924T065535Z-clocktime-full" \
         "$PWD/results/20260923T164954Z-clocktime-full" \
  --out "$PWD/results/clocktime-distribution-analysis"
```

每轮 campaign 单独生成报告，不合并版本。主指标是每个 boot 内全部样本的
均值，再对 boot 等权平均；差值方向为 VKSO−Raw，单位为 TSC ticks。
不把 31 个批次或大量 UPDATE 样本当作独立系统实验。报告包含同 block 的
启动均值差、少量独立 block 下的描述性 bootstrap 区间、全范围 CDF、
UPDATE 中央直方图、长尾和阈值敏感性。READ/kernel reader 的 CDF 是批次
平均成本的分布，不能当作逐次调用延迟。

UPDATE 主结果仍采用原协议的全部 `action=0` 样本。少量非 CPU0 样本在
`non_cpu0_action0_samples` 中逐条列出，不默默删除。低、高耗时区间采用
明确阈值作描述，其位置项与占比项只是均值差的代数分解，不代表已经
识别出两种业务状态。截顶/winsorized 数值仅供敏感性检查，不替换完整均值。
