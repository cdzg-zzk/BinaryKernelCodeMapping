# Layer2 Func-PGOT Placement Stability Check V2

This repeats the revised experiment with `work_only` and workload grid `0,1,2,3,4,5,6,8,16,32,64` for five independent campaigns. Each campaign uses `ITERATIONS=100000`, `REPEATS=15`, and `OUTER_RUNS=3`, so each case has 45 paired samples per campaign.

## Retpoline Stability Summary

| workload | work_only cycles | before median [min,max] | inside median [min,max] | after median [min,max] | ordering stable? | dominant ordering | all abs(delta)<=1 runs |
|---:|---:|---:|---:|---:|---|---|---:|
| 0 | 1.004 | 39.135 [39.135,39.205] | 39.135 [39.135,39.205] | 39.135 [39.135,39.136] | no | before>inside>after (3/5) | 0/5 |
| 1 | 11.115 | 30.859 [30.681,31.063] | 31.021 [30.955,33.020] | 36.457 [36.392,36.460] | no | after>inside>before (4/5) | 0/5 |
| 2 | 22.145 | 19.886 [19.884,19.949] | 22.093 [22.028,22.103] | 25.087 [25.087,25.153] | yes | after>inside>before (5/5) | 0/5 |
| 3 | 33.118 | 13.416 [13.366,18.015] | 11.943 [11.122,12.238] | 16.271 [16.195,16.568] | no | after>before>inside (4/5) | 0/5 |
| 4 | 44.163 | 0.541 [0.496,0.715] | 3.205 [3.059,3.890] | 4.054 [3.981,4.576] | yes | after>inside>before (5/5) | 0/5 |
| 5 | 55.214 | 1.687 [1.684,1.827] | -0.063 [-0.138,-0.047] | -0.085 [-0.186,-0.068] | no | before>inside>after (4/5) | 0/5 |
| 6 | 66.436 | -0.210 [-0.277,0.240] | -0.051 [-0.068,-0.043] | -0.223 [-0.229,-0.161] | no | inside>after>before (3/5) | 5/5 |
| 8 | 88.397 | -0.051 [-0.059,-0.017] | 0.021 [0.014,0.040] | -0.028 [-0.033,-0.016] | no | inside>after>before (4/5) | 5/5 |
| 16 | 176.732 | 0.259 [0.235,0.270] | 0.121 [0.117,0.130] | -0.021 [-0.042,-0.013] | yes | before>inside>after (5/5) | 5/5 |
| 32 | 353.428 | 0.114 [0.110,0.136] | 0.155 [0.148,0.167] | -0.023 [-0.075,0.013] | yes | inside>before>after (5/5) | 5/5 |
| 64 | 706.804 | 0.087 [0.080,0.101] | 0.109 [0.091,0.131] | -0.015 [-0.027,0.029] | no | inside>before>after (4/5) | 5/5 |

## Key Observations

1. The first workload where all five campaigns have all three placement deltas within +/-1 cycle is `6`.
2. Low workloads show stable large retpoline visible overhead, but the exact placement ordering is not globally constant across all workloads.
3. The refined grid shows the transition more clearly: workload 3/4/5 are the sensitive region where some placements have already become small while others can still expose overhead.
4. The stable paper claim should therefore be threshold-based, not a universal ordering such as before > inside > after for every workload.
