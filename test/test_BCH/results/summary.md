# BCH kernel-exported vs user-space results

Times are medians of CPU-pinned outer rounds within one process and one deployment. The timing clock and random-error method follow the author's `tu_bench.c`; backend order rotates each outer run. `vkso/native` is the matched per-run latency ratio, so values above 1 mean the exported kernel code is slower than the same adapted Linux 5.15 source compiled as a user-space DSO.

## m=13, t=4, data=512 bytes

### init

| Errors | kernel-vkso ns | kernel-native ns | author-standalone ns | vkso/native | vkso/author |
| ---: | ---: | ---: | ---: | ---: | ---: |
| - | 81216.15 | 81969.39 | 102110.52 | 0.995x | 0.795x |

### encode

| Errors | kernel-vkso ns | kernel-native ns | author-standalone ns | vkso/native | vkso/author |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1073.41 | 1090.42 | 1137.16 | 0.984x | 0.944x |

### decode-precomputed

| Errors | kernel-vkso ns | kernel-native ns | author-standalone ns | vkso/native | vkso/author |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 30.96 | 33.50 | 32.47 | 0.924x | 0.951x |
| 1 | 216.64 | 224.42 | 223.06 | 0.970x | 0.970x |
| 2 | 255.29 | 263.37 | 263.72 | 0.968x | 0.972x |
| 3 | 731.09 | 737.96 | 691.96 | 0.993x | 1.048x |
| 4 | 788.99 | 776.92 | 737.88 | 1.012x | 1.072x |

### decode-full

| Errors | kernel-vkso ns | kernel-native ns | author-standalone ns | vkso/native | vkso/author |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1090.87 | 1099.77 | 1115.79 | 0.992x | 0.978x |
| 1 | 1265.44 | 1295.70 | 1351.60 | 0.979x | 0.950x |
| 2 | 1329.69 | 1363.39 | 1379.34 | 0.972x | 0.962x |
| 3 | 1813.06 | 1827.05 | 1835.11 | 0.992x | 0.987x |
| 4 | 1845.20 | 1870.59 | 1854.06 | 0.988x | 0.998x |

## m=13, t=8, data=512 bytes

### init

| Errors | kernel-vkso ns | kernel-native ns | author-standalone ns | vkso/native | vkso/author |
| ---: | ---: | ---: | ---: | ---: | ---: |
| - | 116680.47 | 116836.84 | 129860.34 | 0.998x | 0.899x |

### encode

| Errors | kernel-vkso ns | kernel-native ns | author-standalone ns | vkso/native | vkso/author |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1097.90 | 1097.07 | 1312.99 | 1.001x | 0.836x |

### decode-precomputed

| Errors | kernel-vkso ns | kernel-native ns | author-standalone ns | vkso/native | vkso/author |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 45.50 | 46.16 | 48.66 | 0.988x | 0.933x |
| 1 | 584.83 | 551.54 | 561.18 | 1.098x | 1.054x |
| 2 | 799.89 | 624.02 | 653.96 | 1.209x | 1.168x |
| 3 | 1181.21 | 1121.86 | 1137.44 | 1.055x | 1.046x |
| 4 | 1228.10 | 1169.80 | 1165.42 | 1.055x | 1.065x |
| 5 | 2004.70 | 1851.09 | 1845.60 | 1.074x | 1.084x |
| 6 | 2667.90 | 2513.67 | 2464.86 | 1.078x | 1.087x |
| 7 | 2953.63 | 2781.25 | 2694.67 | 1.065x | 1.095x |
| 8 | 3882.10 | 3620.21 | 3548.71 | 1.078x | 1.095x |

### decode-full

| Errors | kernel-vkso ns | kernel-native ns | author-standalone ns | vkso/native | vkso/author |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1115.94 | 1112.14 | 1333.31 | 1.003x | 0.837x |
| 1 | 1771.36 | 1684.50 | 1948.57 | 1.034x | 0.909x |
| 2 | 1798.25 | 1737.17 | 1978.18 | 1.039x | 0.904x |
| 3 | 2292.19 | 2259.34 | 2479.27 | 1.025x | 0.928x |
| 4 | 2352.90 | 2296.01 | 2533.19 | 1.024x | 0.927x |
| 5 | 3147.18 | 2998.13 | 3239.29 | 1.044x | 0.969x |
| 6 | 3797.26 | 3638.49 | 3851.16 | 1.050x | 0.984x |
| 7 | 4197.64 | 3966.25 | 4177.02 | 1.050x | 0.997x |
| 8 | 5006.50 | 4777.83 | 4927.11 | 1.054x | 1.014x |
