#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


BUILD_ORDER = {"no_retpoline": 0, "retpoline": 1}
VARIANT_ORDER = {"data_pgot": 0, "func_pgot": 1, "all_pgot": 2}


def f3(v):
    return f"{float(v):.3f}"


def f2(v):
    return f"{float(v):.2f}"


def read_rows(results_dir):
    rows = []
    for table in sorted(Path(results_dir).glob("*/paper_table.csv")):
        experiment = table.parent.name
        with table.open(newline="") as f:
            for row in csv.DictReader(f):
                row = dict(row)
                row["experiment"] = experiment
                row["iterations"] = int(row.get("iterations", "0"))
                row["n_raw"] = int(row["n_raw"])
                for key in ("origin_cycles", "variant_cycles", "delta_cycles",
                            "delta_iqr", "overhead_percent"):
                    row[key] = float(row.get(key, 0.0))
                if row.get("iqr_to_abs_delta", "") == "":
                    row["iqr_to_abs_delta"] = 0.0
                else:
                    row["iqr_to_abs_delta"] = float(row.get("iqr_to_abs_delta", 0.0))
                if not row["iqr_to_abs_delta"] and row["delta_cycles"]:
                    row["iqr_to_abs_delta"] = row["delta_iqr"] / abs(row["delta_cycles"])
                rows.append(row)
    return rows


def stability_label(row):
    ratio = row["iqr_to_abs_delta"]
    delta = abs(row["delta_cycles"])
    iqr = row["delta_iqr"]

    if delta < 1.0 and iqr < 5.0:
        return "near_zero"
    if delta < iqr:
        return "indistinguishable"
    if ratio <= 0.25:
        return "strong"
    if ratio <= 0.50:
        return "usable"
    if ratio <= 1.00:
        return "weak"
    return "unstable"


def select_rows(rows):
    groups = {}
    for row in rows:
        groups.setdefault((row["experiment"], row["build"], row["variant"]), []).append(row)

    selected = []
    for key, group in groups.items():
        # Prefer rows where the delta is distinguishable and IQR is small.
        # If no row is clean, choose the least unstable row and preserve the
        # label so the paper can avoid overclaiming that case.
        def score(row):
            label_rank = {
                "strong": 0,
                "usable": 1,
                "weak": 2,
                "near_zero": 3,
                "indistinguishable": 4,
                "unstable": 5,
            }[stability_label(row)]
            return (
                label_rank,
                row["iqr_to_abs_delta"] if abs(row["delta_cycles"]) >= 1.0 else row["delta_iqr"],
                -row["iterations"],
            )

        best = sorted(group, key=score)[0]
        best = dict(best)
        best["stability"] = stability_label(best)
        selected.append(best)
    selected.sort(key=lambda r: (
        r["experiment"],
        BUILD_ORDER.get(r["build"], 99),
        VARIANT_ORDER.get(r["variant"], 99),
    ))
    return selected


def write_csv(path, rows):
    fields = [
        "experiment", "build", "variant", "iterations", "n_raw",
        "origin_cycles", "variant_cycles", "delta_cycles", "delta_iqr",
        "iqr_to_abs_delta", "overhead_percent", "stability",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            for key in ("origin_cycles", "variant_cycles", "delta_cycles",
                        "delta_iqr", "iqr_to_abs_delta",
                        "overhead_percent"):
                out[key] = f"{out[key]:.9f}"
            writer.writerow({key: out[key] for key in fields})


def write_markdown(path, rows):
    lines = [
        "# Layer3 Stable Paper Rows",
        "",
        "Selection rule: group by experiment/build/variant, prefer rows with smaller `IQR/|Δ|`; keep the stability label so weak or unstable cases are not overclaimed.",
        "",
        "| experiment | build | variant | iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | stability |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['experiment']} | {row['build']} | {row['variant']} | "
            f"{row['iterations']} | {row['n_raw']} | {f3(row['origin_cycles'])} | "
            f"{f3(row['variant_cycles'])} | {f3(row['delta_cycles'])} | "
            f"{f3(row['delta_iqr'])} | {f2(row['iqr_to_abs_delta'])} | "
            f"{f2(row['overhead_percent'])} | {row['stability']} |"
        )
    path.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    rows = read_rows(args.results_dir)
    selected = select_rows(rows)
    write_csv(args.out_csv, selected)
    write_markdown(Path(args.out_md), selected)


if __name__ == "__main__":
    main()
