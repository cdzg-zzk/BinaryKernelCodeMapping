# test_zlib

这个目录保存 `zlib_lkm`、用户态对照库、`pigz` 适配、正确性测试和宏/微基准文档。

建议提交到 git 的内容：

- 核心源码与构建规则
  - [common_zlib_build_flags.mk](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/common_zlib_build_flags.mk)
  - [zlib_lkm/Makefile](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_lkm/Makefile)
  - [zlib_lkm/README.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_lkm/README.md)
  - [zlib_user/Makefile](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_user/Makefile)
  - [zlib_upstream_user/Makefile](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user/Makefile)
  - [zlib_upstream_user_trim/Makefile](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/Makefile)
  - [zlib_upstream_user_trim/exports.map](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/exports.map)

- 用户态库说明文档
  - [zlib_user/README.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_user/README.md)
  - [zlib_upstream_user/README.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user/README.md)
  - [zlib_upstream_user_trim/README.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/README.md)

- 测试与分析文档
  - [test_zlib_lkm/Makefile](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/test_zlib_lkm/Makefile)
  - [test_zlib_lkm/ROOT_CAUSE_ANALYSIS.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/test_zlib_lkm/ROOT_CAUSE_ANALYSIS.md)
  - [test_zlib_lkm/RUN_ERROR.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/test_zlib_lkm/RUN_ERROR.md)
  - [macro_test_content/Readme.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/macro_test_content/Readme.md)
  - [macro_test_content/Conclusion.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/macro_test_content/Conclusion.md)
  - `macro_test_content/scripts/` 下的脚本

- 需要保留的源码树
  - [zlib_lkm](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_lkm)
  - [zlib_user](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_user)
  - [zlib_upstream_user](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user)
  - [zlib_upstream_user_trim](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim)
  - [test_zlib_lkm](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/test_zlib_lkm)
  - [pigz_macro/pigz-2.8](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8)
  - [pigz_macro/zlib-1.2.11](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/zlib-1.2.11)

当前不建议提交到 git 的内容：

- `.o/.so/.ko/.mod*` 等构建中间结果
- `pigz_user`、`pigz_upstream_user`、`pigz_upstream_user_trim` 等生成出的可执行文件
- [so/](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so) 目录下的生成物
  - [deflate_types.h](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so/deflate_types.h) 可按需要单独决定是否保留
- `macro_test_content/csv/`
- `macro_test_content/correctness/`
- `macro_test_content/perf_data/`
- 各目录下 `verification/` 里的结果数据

构建和运行命令已经分别记录在各用户态库目录的 README 里：

- [zlib_user/README.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_user/README.md)
- [zlib_upstream_user/README.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user/README.md)
- [zlib_upstream_user_trim/README.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/README.md)

