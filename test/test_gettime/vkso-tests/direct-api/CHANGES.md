# 本次文件清单

相对仓库根目录；基线 `4be87be`。M=修改，A=新增，D=删除。

```text
M	.gitignore
D	test/test_gettime/macro-benchmark/.gitignore
D	test/test_gettime/macro-benchmark/PROTOCOL.md
D	test/test_gettime/macro-benchmark/README.md
D	test/test_gettime/macro-benchmark/adapter.c
D	test/test_gettime/macro-benchmark/check_adapter.c
D	test/test_gettime/macro-benchmark/redis_workload.py
D	test/test_gettime/macro-benchmark/vendor/REDIS-COPYING
D	test/test_gettime/macro-benchmark/vendor/redis-7.2.4.tar.gz
M	test/test_gettime/vkso-tests/README.md
M	test/test_gettime/vkso-tests/baremetal/.gitignore
M	test/test_gettime/vkso-tests/baremetal/README.md
M	test/test_gettime/vkso-tests/baremetal/build-all.sh
M	test/test_gettime/vkso-tests/baremetal/build-images.sh
M	test/test_gettime/vkso-tests/baremetal/collect-case.sh
M	test/test_gettime/vkso-tests/baremetal/experiment.conf
M	test/test_gettime/vkso-tests/baremetal/experiment.sh
M	test/test_gettime/vkso-tests/baremetal/install-grub.sh
M	test/test_gettime/vkso-tests/baremetal/verify-packages.sh
M	test/test_gettime/vkso-tests/direct-api/Makefile
M	test/test_gettime/vkso-tests/direct-api/README.md
M	test/test_gettime/vkso-tests/direct-api/VALIDATION.md
M	test/test_gettime/vkso-tests/direct-api/bundle.py
M	test/test_gettime/vkso-tests/direct-api/collect.py
M	test/test_gettime/vkso-tests/direct-api/example.c
M	test/test_gettime/vkso-tests/direct-api/results.py
M	test/test_gettime/vkso-tests/direct-api/tests/test_api.c
M	test/test_gettime/vkso-tests/direct-api/tests/test_direct.py
M	test/test_gettime/vkso-tests/direct-api/time_bench.c
A	test/test_gettime/README.md
A	test/test_gettime/history/.gitignore
A	test/test_gettime/history/README.md
A	test/test_gettime/vkso-tests/direct-api/STATEFUL.md
A	test/test_gettime/vkso-tests/direct-api/campaign.py
A	test/test_gettime/vkso-tests/direct-api/package_check.py
A	test/test_gettime/vkso-tests/direct-api/sharing.py
A	test/test_gettime/vkso-tests/direct-api/vkso_public.c
A	test/test_gettime/vkso-tests/direct-api/CHANGES.md
```

本地数据迁移：`test/test_gettime/macro-benchmark/results/` → `test/test_gettime/history/redis-results/`。
已检查的旧 Redis build 二进制与 Python 字节码缓存已删除；正式压缩包未修改。
未提交本任务之外的工作，也未改动根目录的旧补丁。
