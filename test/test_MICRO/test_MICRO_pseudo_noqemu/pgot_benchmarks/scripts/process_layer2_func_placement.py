#!/usr/bin/env python3
import argparse
import csv
import math
import statistics
from collections import defaultdict


def quantile(values, q):
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def stats(values):
    ordered = sorted(values)
    q1 = quantile(ordered, 0.25)
    med = quantile(ordered, 0.50)
    q3 = quantile(ordered, 0.75)
    return {
        "mean": sum(values) / len(values) if values else 0.0,
        "median": med,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": ordered[0] if ordered else 0.0,
        "max": ordered[-1] if ordered else 0.0,
    }


def fmt(v):
    if isinstance(v, int):
        return str(v)
    return f"{v:.9f}"


def load_rows(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "experiment": r["experiment"],
                "build": r["build"],
                "fence": r["fence"],
                "run_id": int(r["run_id"]),
                "placement": r["placement"],
                "workload": int(r["workload"]),
                "repeat": int(r["repeat"]),
                "iterations": int(r["iterations"]),
                "direct_cycles": float(r["direct_cycles"]),
                "pgot_cycles": float(r["pgot_cycles"]),
                "delta_pgot_direct": float(r["delta_pgot_direct"]),
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--processed", required=True)
    ap.add_argument("--paper-table", required=True)
    args = ap.parse_args()

    rows = load_rows(args.raw)
    by_group = defaultdict(list)
    for r in rows:
        by_group[(r["build"], r["fence"], r["placement"], r["workload"])].append(r)

    processed_fields = [
        "build", "fence", "placement", "workload", "n_raw",
        "direct_mean", "direct_median", "direct_iqr",
        "pgot_mean", "pgot_median", "pgot_iqr",
        "delta_mean", "delta_median", "delta_iqr", "delta_stddev",
        "delta_min", "delta_max", "overhead_percent_median",
    ]
    processed_rows = []
    for key in sorted(by_group, key=lambda x: (
            {"no_retpoline": 0, "retpoline": 1}.get(x[0], 99),
            {"unfenced": 0, "fenced": 1}.get(x[1], 99),
            {"none": 0, "work_only": 1, "before": 2, "inside": 3, "after": 4}.get(x[2], 99),
            x[3])):
        group = by_group[key]
        direct = [r["direct_cycles"] for r in group]
        pgot = [r["pgot_cycles"] for r in group]
        delta = [r["delta_pgot_direct"] for r in group]
        ds = stats(direct)
        ps = stats(pgot)
        xs = stats(delta)
        overhead = (xs["median"] / ds["median"] * 100.0) if ds["median"] else 0.0
        processed_rows.append({
            "build": key[0],
            "fence": key[1],
            "placement": key[2],
            "workload": key[3],
            "n_raw": len(group),
            "direct_mean": ds["mean"],
            "direct_median": ds["median"],
            "direct_iqr": ds["iqr"],
            "pgot_mean": ps["mean"],
            "pgot_median": ps["median"],
            "pgot_iqr": ps["iqr"],
            "delta_mean": xs["mean"],
            "delta_median": xs["median"],
            "delta_iqr": xs["iqr"],
            "delta_stddev": xs["stddev"],
            "delta_min": xs["min"],
            "delta_max": xs["max"],
            "overhead_percent_median": overhead,
        })

    with open(args.processed, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=processed_fields)
        writer.writeheader()
        for r in processed_rows:
            writer.writerow({k: fmt(r[k]) if isinstance(r[k], float) else r[k]
                             for k in processed_fields})

    paper_fields = [
        "build", "fence", "placement", "workload", "n_raw",
        "direct_cycles", "pgot_cycles", "delta_cycles", "delta_iqr",
        "overhead_percent",
    ]
    with open(args.paper_table, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=paper_fields)
        writer.writeheader()
        for r in processed_rows:
            out = {
                "build": r["build"],
                "fence": r["fence"],
                "placement": r["placement"],
                "workload": r["workload"],
                "n_raw": r["n_raw"],
                "direct_cycles": r["direct_median"],
                "pgot_cycles": r["pgot_median"],
                "delta_cycles": r["delta_median"],
                "delta_iqr": r["delta_iqr"],
                "overhead_percent": r["overhead_percent_median"],
            }
            writer.writerow({k: fmt(out[k]) if isinstance(out[k], float) else out[k]
                             for k in paper_fields})


if __name__ == "__main__":
    main()
