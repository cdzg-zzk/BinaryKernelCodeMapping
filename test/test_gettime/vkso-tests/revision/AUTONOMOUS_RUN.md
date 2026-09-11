# Clocktime 无人值守执行

本轮已启动，由 `vkso-clocktime-revision.service` 调用 `boot.py` 执行。
无需保持 Codex、终端或 SSH 连接；关闭这些客户端不会停止 systemd 服务。
机器需要保持通电。当前这轮不要重新执行 prepare、install 或 start。

## 查看进度

在仓库根目录运行：

```sh
python3 test/test_gettime/vkso-tests/revision/campaign.py status \
  test/test_gettime/vkso-tests/revision/results/normal-campaign
systemctl status vkso-clocktime-revision.service --no-pager
```

`remaining_steps` 包含正在执行的本次启动。例如值为 13 表示已完成 7/20。
服务处于 `active (running)` 表示控制器在运行；启动准备和稳定等待期间
可能暂时没有新的测量文件。

## 自动执行流程

脚本执行当前启动的全部测量，保存结果，然后通过 GRUB 自动重启到下一项
指定的内核。已经完成的启动不会重测。计划包含 20 次启动；每次 VKSO 启动
还会执行完整代码复制对照，不额外增加启动次数。

全部完成后，控制器自动生成以下文件，禁用实验服务并重启回原来的普通内核：

```text
test/test_gettime/vkso-tests/revision/results/normal-campaign/summary.csv
test/test_gettime/vkso-tests/revision/results/normal-campaign/campaign-complete.json
```

`step-000/` 至 `step-019/` 保留各次启动的原始记录及归一化结果。
完成标记表示控制器完成了采集和数值汇总；最终科学解释仍需查看原始数据和
诊断记录。之后直接告诉 Codex：“Clocktime 自动实验结束了，请检查
normal-campaign 的结果并分析。”

## 如果没有继续运行

```sh
journalctl -u vkso-clocktime-revision.service -n 60 --no-pager
```

采集失败时，控制器保留数据并写入 `results/normal-campaign/failed.json`，
停止自动推进。保留该文件和日志，交给 Codex 检查；不要删除失败记录后
直接重跑。同样，不要在采集期间更改被冻结的工具、内核或实验参数。

完整的新建实验命令见同目录 `README.md` 的 Formal campaign 部分。
