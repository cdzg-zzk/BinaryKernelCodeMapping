#!/usr/bin/env python3
import argparse
import csv
import sys


ORDER = [
    ("native", "hot"),
    ("stub", "hot"),
    ("native", "pte-cold"),
    ("stub", "pte-cold"),
    ("native", "post-drop"),
    ("stub", "post-drop"),
]


def read_by_key(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return {(row["Target"], row["Condition"]): row for row in rows}


def main():
    parser = argparse.ArgumentParser(
        description="Merge latency and PMU CSVs into the paper table."
    )
    parser.add_argument(
        "--latency", default="first_touch_results.csv", help="latency CSV"
    )
    parser.add_argument("--pmu", default="pmc_results.csv", help="PMU CSV")
    parser.add_argument(
        "-o",
        "--output",
        default="first_touch_pmu_combined.csv",
        help="merged output CSV",
    )
    args = parser.parse_args()

    latency = read_by_key(args.latency)
    pmu = read_by_key(args.pmu)

    fields = [
        "Target",
        "Condition",
        "Latency_Median_Cycles",
        "Latency_Mean_Cycles",
        "Latency_StdDev",
        "Latency_P25",
        "Latency_P75",
        "Latency_P95",
        "Latency_Minor_Flt",
        "Latency_Major_Flt",
        "PMU_Median_TSC_Cycles",
        "PMU_Mean_TSC_Cycles",
        "PMU_StdDev_TSC",
        "PMU_Minor_Flt",
        "PMU_Major_Flt",
        "PMU_Expected_Fault_Runs",
        "PMU_Valid_Runs",
        "PMU_Fault_Mismatches",
        "Mean_Perf_Cycles",
        "Mean_Instructions",
        "Mean_L1I_Misses",
        "Mean_L1D_Misses",
        "Mean_LLC_Misses",
        "Mean_iTLB_Misses",
    ]

    missing = []
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for key in ORDER:
            lrow = latency.get(key)
            prow = pmu.get(key)
            if lrow is None or prow is None:
                missing.append(key)
                continue
            writer.writerow(
                {
                    "Target": key[0],
                    "Condition": key[1],
                    "Latency_Median_Cycles": lrow["Grand_Median"],
                    "Latency_Mean_Cycles": lrow["Grand_Mean"],
                    "Latency_StdDev": lrow["Avg_StdDev"],
                    "Latency_P25": lrow["Avg_P25"],
                    "Latency_P75": lrow["Avg_P75"],
                    "Latency_P95": lrow["Avg_P95"],
                    "Latency_Minor_Flt": lrow["Avg_Minor_Flt"],
                    "Latency_Major_Flt": lrow["Avg_Major_Flt"],
                    "PMU_Median_TSC_Cycles": prow["Median_TSC_Cycles"],
                    "PMU_Mean_TSC_Cycles": prow["Mean_TSC_Cycles"],
                    "PMU_StdDev_TSC": prow["StdDev_TSC"],
                    "PMU_Minor_Flt": prow["Avg_Minor_Flt"],
                    "PMU_Major_Flt": prow["Avg_Major_Flt"],
                    "PMU_Expected_Fault_Runs": prow["Expected_Fault_Runs"],
                    "PMU_Valid_Runs": prow["Valid_Runs"],
                    "PMU_Fault_Mismatches": prow["Fault_Mismatches"],
                    "Mean_Perf_Cycles": prow["Mean_Perf_Cycles"],
                    "Mean_Instructions": prow["Mean_Instructions"],
                    "Mean_L1I_Misses": prow["Mean_L1I_Misses"],
                    "Mean_L1D_Misses": prow["Mean_L1D_Misses"],
                    "Mean_LLC_Misses": prow["Mean_LLC_Misses"],
                    "Mean_iTLB_Misses": prow["Mean_iTLB_Misses"],
                }
            )

    if missing:
        print("missing rows:", ", ".join(f"{t}/{c}" for t, c in missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
