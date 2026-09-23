# 历史数据

`redis-results/` 保留旧 Redis 工作流的原始验证与构建记录，内容未改写。
旧桥接实现、Redis vendor 压缩包和生成二进制已退出工作树；源码可从
Git 提交 `43c60fc` 的 `test/test_gettime/macro-benchmark/` 恢复。

旧四组 Redis 的 baremetal 归档已从当前正式结果目录移出；`redis-results/`
仍保留其历史验证记录。旧数据没有重新标记成当前全量协议数据。

`../optimization-audit/` 与 `../namespace-sharing/` 仍保留，因为 namespace 页共享验证依赖它们。
`../vkso-tests/revision/` 和 `../vkso-timekeeper-unification/` 是旧协议、状态成本工具及设计证据，
不能将其中历史数值合并到新 READ 协议结果。
