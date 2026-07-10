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
                "run_id": int(r["run_id"]),
                "variant": r["variant"],
                "repeat": int(r["repeat"]),
                "iterations": int(r["iterations"]),
                "origin_cycles": float(r["origin_cycles"]),
                "variant_cycles": float(r["variant_cycles"]),
                "delta_variant_origin": float(r["delta_variant_origin"]),
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
        by_group[(r["build"], r["variant"], r["iterations"])].append(r)

    order_build = {"no_retpoline": 0, "retpoline": 1}
    order_variant = {"data_pgot": 0, "func_pgot": 1, "all_pgot": 2}
    processed_fields = [
        "build", "variant", "iterations", "n_raw",
        "origin_mean", "origin_median", "origin_iqr",
        "variant_mean", "variant_median", "variant_iqr",
        "delta_mean", "delta_median", "delta_iqr", "delta_stddev",
        "delta_min", "delta_max", "iqr_to_abs_delta", "overhead_percent_median",
    ]
    processed_rows = []
    for key in sorted(by_group,
                      key=lambda x: (order_build.get(x[0], 99),
                                     order_variant.get(x[1], 99),
                                     x[2])):
        group = by_group[key]
        origin = [r["origin_cycles"] for r in group]
        variant = [r["variant_cycles"] for r in group]
        delta = [r["delta_variant_origin"] for r in group]
        os = stats(origin)
        vs = stats(variant)
        ds = stats(delta)
        overhead = (ds["median"] / os["median"] * 100.0) if os["median"] else 0.0
        iqr_to_abs_delta = (ds["iqr"] / abs(ds["median"])) if ds["median"] else 0.0
        processed_rows.append({
            "build": key[0],
            "variant": key[1],
            "iterations": key[2],
            "n_raw": len(group),
            "origin_mean": os["mean"],
            "origin_median": os["median"],
            "origin_iqr": os["iqr"],
            "variant_mean": vs["mean"],
            "variant_median": vs["median"],
            "variant_iqr": vs["iqr"],
            "delta_mean": ds["mean"],
            "delta_median": ds["median"],
            "delta_iqr": ds["iqr"],
            "delta_stddev": ds["stddev"],
            "delta_min": ds["min"],
            "delta_max": ds["max"],
            "iqr_to_abs_delta": iqr_to_abs_delta,
            "overhead_percent_median": overhead,
        })

    with open(args.processed, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=processed_fields)
        writer.writeheader()
        for r in processed_rows:
            writer.writerow({k: fmt(r[k]) if isinstance(r[k], float) else r[k]
                             for k in processed_fields})

    paper_fields = [
        "build", "variant", "iterations", "n_raw",
        "origin_cycles", "variant_cycles", "delta_cycles",
        "delta_iqr", "iqr_to_abs_delta", "overhead_percent",
    ]
    with open(args.paper_table, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=paper_fields)
        writer.writeheader()
        for r in processed_rows:
            out = {
                "build": r["build"],
                "variant": r["variant"],
                "iterations": r["iterations"],
                "n_raw": r["n_raw"],
                "origin_cycles": r["origin_median"],
                "variant_cycles": r["variant_median"],
                "delta_cycles": r["delta_median"],
                "delta_iqr": r["delta_iqr"],
                "iqr_to_abs_delta": r["iqr_to_abs_delta"],
                "overhead_percent": r["overhead_percent_median"],
            }
            writer.writerow({k: fmt(out[k]) if isinstance(out[k], float) else out[k]
                             for k in paper_fields})


if __name__ == "__main__":
    main()
