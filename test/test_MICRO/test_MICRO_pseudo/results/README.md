# results

这个目录按“函数名”组织 benchmark 输出，避免不同函数的 QEMU 结果混在一起。

当前结构：

- [crc32_le](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/results/crc32_le)
  `crc32_le` 与 `crc32_le_micro` 的函数级 benchmark 结果。

建议后续统一沿用：

- `results/<function>/<timestamp>_qemu_*`
- `results/<function>/<timestamp>_host_*`

如果中间做过 `smoke` 或一次性试跑，建议在正式结果稳定后清掉，只保留可引用的结果目录和对应 `SUMMARY.md`。

这样后面继续做 `sha256_transform`、`sm4_crypt_block`、`crypto_aes_encrypt` 之类函数时，不需要再调整结果目录规则。
