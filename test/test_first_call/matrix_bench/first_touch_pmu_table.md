# First-Touch Latency and PMU Results

| Target | Condition | Faults (min/maj) | Lat. median cyc | Lat. P25-P75 | Lat. P95 | PMU TSC median cyc | Perf cycles | Instr. | L1I miss | L1D miss | LLC miss | iTLB miss |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| native | hot | 0 / 0 | 71 | 69-71 | 73 | 69 | 4249.52 | 3918.00 | 37.38 | 0.10 | 0.00 | 8.21 |
| stub | hot | 0 / 0 | 71 | 69-71 | 73 | 69 | 4271.21 | 3918.00 | 37.79 | 0.04 | 0.00 | 8.07 |
| native | pte-cold | 1 / 0 | 2662 | 2658-2667 | 2674 | 2675 | 6994.33 | 5828.00 | 246.11 | 2.33 | 0.00 | 10.04 |
| stub | pte-cold | 1 / 0 | 2637 | 2633-2642 | 2648 | 2656 | 6946.04 | 5729.00 | 255.07 | 1.00 | 0.00 | 9.14 |
| native | post-drop | 0 / 1 | 701069 | 669200-708383 | 727536 | 714627 | 81006.38 | 26725.86 | 3585.52 | 774.83 | 96.97 | 24.59 |
| stub | post-drop | 1 / 0 | 13094 | 12319-13882 | 14977 | 12574 | 19711.00 | 5797.14 | 655.50 | 62.79 | 17.61 | 13.18 |

Notes:

- Latency columns come from `first_touch_results.csv`.
- PMU columns come from `pmc_results.csv`; all six groups have `Expected_Fault_Runs=30` and `Fault_Mismatches=0`.
- `Perf cycles` are hardware counted on-CPU cycles. They are not identical to elapsed TSC latency, especially for major faults where the process may wait off-CPU.
