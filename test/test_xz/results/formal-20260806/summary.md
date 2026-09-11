# XZ Embedded evaluation summary

| Case | Native median MiB/s | Kernel-vkso median MiB/s | Paired kernel/native median | P10–P90 |
|---|---:|---:|---:|---:|
| bash | 30.40 | 29.94 | 0.985× | 0.984–0.986× |
| libc.so.6 | 33.23 | 32.74 | 0.985× | 0.984–0.988× |
| python3 | 33.25 | 32.64 | 0.982× | 0.980–0.983× |

Ratios are formed within the same outer run before aggregation. The two-backend execution order rotates between outer rounds within one process and one deployment.
