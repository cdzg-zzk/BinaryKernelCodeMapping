# LZ4 userspace vs vkso kernel benchmark

Medians combine outer rounds within one deployment. Each round/block/backend starts a new official-harness process; the owner module and page registration remain active across rounds.
Measurements use the unmodified LZ4 1.9.3 `programs/bench.c` timing core through a thin DSO adapter.
The official harness loads input and allocates state/output buffers before timing, adapts loop counts to approximately one second, and reports the fastest completed loop.
`speedup` is throughput divided by `user-default` throughput, so values above 1 favor the selected backend.

## compress

| Block | Backend | Runs | Median MB/s | Median MiB/s | P10–P90 MiB/s | Ratio | Speedup |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4,096 | kernel-userspace-native | 7 | 434.17 | 414.06 | 413.76–414.26 | 1.7267 | 0.9890x |
| 4,096 | kernel-userspace-nosimd | 7 | 444.37 | 423.78 | 423.35–423.95 | 1.7267 | 1.0122x |
| 4,096 | kernel-vkso | 7 | 454.62 | 433.56 | 433.25–434.07 | 1.7267 | 1.0356x |
| 4,096 | user-default | 7 | 439.01 | 418.67 | 418.33–418.91 | 1.7267 | 1.0000x |
| 4,096 | user-nosimd | 7 | 456.40 | 435.26 | 435.01–435.87 | 1.7267 | 1.0396x |
| 65,536 | kernel-userspace-native | 7 | 410.96 | 391.92 | 391.37–392.15 | 2.0688 | 0.9728x |
| 65,536 | kernel-userspace-nosimd | 7 | 418.19 | 398.82 | 398.47–398.96 | 2.0688 | 0.9899x |
| 65,536 | kernel-vkso | 7 | 426.30 | 406.55 | 406.31–406.74 | 2.0688 | 1.0091x |
| 65,536 | user-default | 7 | 422.46 | 402.89 | 402.50–403.10 | 2.0688 | 1.0000x |
| 65,536 | user-nosimd | 7 | 436.66 | 416.43 | 416.25–416.86 | 2.0688 | 1.0336x |
| 1,048,576 | kernel-userspace-native | 7 | 427.94 | 408.12 | 407.79–408.54 | 2.0972 | 0.9624x |
| 1,048,576 | kernel-userspace-nosimd | 7 | 446.58 | 425.89 | 425.54–426.24 | 2.0972 | 1.0043x |
| 1,048,576 | kernel-vkso | 7 | 448.36 | 427.59 | 427.26–427.97 | 2.0972 | 1.0083x |
| 1,048,576 | user-default | 7 | 444.65 | 424.05 | 421.61–425.25 | 2.0972 | 1.0000x |
| 1,048,576 | user-nosimd | 7 | 464.55 | 443.03 | 441.93–443.24 | 2.0972 | 1.0448x |

## decompress

| Block | Backend | Runs | Median MB/s | Median MiB/s | P10–P90 MiB/s | Ratio | Speedup |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4,096 | kernel-userspace-native | 7 | 2026.60 | 1932.72 | 1931.08–1937.73 | 1.7267 | 0.9247x |
| 4,096 | kernel-userspace-nosimd | 7 | 2136.30 | 2037.33 | 2028.85–2043.13 | 1.7267 | 0.9747x |
| 4,096 | kernel-vkso | 7 | 2106.60 | 2009.01 | 2004.13–2012.65 | 1.7267 | 0.9612x |
| 4,096 | user-default | 7 | 2191.70 | 2090.17 | 2086.30–2093.60 | 1.7267 | 1.0000x |
| 4,096 | user-nosimd | 7 | 2221.30 | 2118.40 | 2116.37–2124.92 | 1.7267 | 1.0135x |
| 65,536 | kernel-userspace-native | 7 | 2075.50 | 1979.35 | 1977.41–1984.35 | 2.0688 | 0.9552x |
| 65,536 | kernel-userspace-nosimd | 7 | 2152.00 | 2052.31 | 2050.61–2053.43 | 2.0688 | 0.9904x |
| 65,536 | kernel-vkso | 7 | 2112.80 | 2014.92 | 2008.59–2017.73 | 2.0688 | 0.9723x |
| 65,536 | user-default | 7 | 2172.90 | 2072.24 | 2069.24–2074.09 | 2.0688 | 1.0000x |
| 65,536 | user-nosimd | 7 | 2213.60 | 2111.05 | 2107.81–2115.00 | 2.0688 | 1.0187x |
| 1,048,576 | kernel-userspace-native | 7 | 2400.20 | 2289.01 | 2283.31–2291.76 | 2.0972 | 0.8954x |
| 1,048,576 | kernel-userspace-nosimd | 7 | 2509.80 | 2393.53 | 2388.19–2397.73 | 2.0972 | 0.9363x |
| 1,048,576 | kernel-vkso | 7 | 2473.50 | 2358.91 | 2354.37–2362.02 | 2.0972 | 0.9228x |
| 1,048,576 | user-default | 7 | 2680.50 | 2556.32 | 2551.65–2559.22 | 2.0972 | 1.0000x |
| 1,048,576 | user-nosimd | 7 | 2698.10 | 2573.11 | 2570.44–2574.21 | 2.0972 | 1.0066x |

## Overall

- `kernel-userspace-native` geometric-mean speedup vs user-default: 0.9494x
- `kernel-userspace-nosimd` geometric-mean speedup vs user-default: 0.9843x
- `kernel-vkso` geometric-mean speedup vs user-default: 0.9842x
- `user-default` geometric-mean speedup vs user-default: 1.0000x
- `user-nosimd` geometric-mean speedup vs user-default: 1.0260x
