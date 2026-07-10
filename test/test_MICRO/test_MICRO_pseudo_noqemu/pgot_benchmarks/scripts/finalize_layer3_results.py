#!/usr/bin/env python3
import argparse
import csv
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


EXPERIMENT_NAMES = {
    "01_sha256_transform": "sha256_transform",
    "02_bch_encode": "bch_encode",
    "03_zlib_deflate": "zlib_deflate",
    "04_zstd_decompress": "zstd_decompress",
    "05_crc32_le": "crc32_le",
    "06_lz4_compress_fast": "lz4_compress_fast",
    "07_aes_encrypt": "aes_encrypt",
    "08_lz4_decompress_safe": "lz4_decompress_safe",
    "09_hex_dump_to_buffer": "hex_dump_to_buffer",
    "10_string_escape_mem": "string_escape_mem",
}

BUILD_ORDER = {"no_retpoline": 0, "retpoline": 1}
VARIANT_ORDER = {"data_pgot": 0, "func_pgot": 1, "all_pgot": 2}


def quantile(values, q):
    ordered = sorted(values)
    if not ordered:
        return 0.0
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


def f3(v):
    return f"{v:.3f}"


def f6(v):
    return f"{v:.6f}"


def parse_float(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def read_metadata(path):
    meta = {}
    if not path.exists():
        return meta
    with path.open(errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                line = line[1:].strip()
            if "=" in line:
                k, v = line.split("=", 1)
                meta[k] = v
    return meta


def parse_bad_runs(exp_dir):
    bad = set()
    path = exp_dir / "dmesg_warnings.txt"
    if not path.exists():
        return bad
    for line in path.read_text(errors="replace").splitlines():
        log = line.split(":", 1)[0]
        name = Path(log).name
        parts = name.removesuffix(".log").split("_")
        if len(parts) < 3:
            continue
        run_id = parts[-2]
        iterations = parts[-1]
        build = "_".join(parts[:-2])
        if run_id.isdigit() and iterations.isdigit():
            bad.add((build, int(run_id), int(iterations)))
    return bad


def expected_repeats(meta, rows):
    if meta.get("repeats", "").isdigit():
        return int(meta["repeats"])
    counts = Counter((r["build"], r["variant"], r["iterations"], r["run_id"])
                     for r in rows)
    if not counts:
        return 0
    return counts.most_common(1)[0][1]


def load_experiment(exp_dir):
    raw_path = exp_dir / "raw.csv"
    if not raw_path.exists():
        return []

    meta = read_metadata(exp_dir / "metadata.txt")
    bad_runs = parse_bad_runs(exp_dir)
    rows = []
    with raw_path.open(newline="", errors="replace") as f:
        for raw in csv.DictReader(f):
            origin = parse_float(raw.get("origin_cycles"))
            variant = parse_float(raw.get("variant_cycles"))
            delta = parse_float(raw.get("delta_variant_origin"))
            build = raw.get("build", "")
            variant_name = raw.get("variant", "")
            try:
                run_id = int(raw.get("run_id", ""))
                repeat = int(raw.get("repeat", ""))
                iterations = int(raw.get("iterations", ""))
            except ValueError:
                run_id = repeat = iterations = -1

            valid = True
            reason = ""
            if origin is None or variant is None or delta is None:
                valid = False
                reason = "non_numeric"
            elif origin <= 0 or variant <= 0:
                valid = False
                reason = "non_positive_cycles"
            elif (build, run_id, iterations) in bad_runs:
                valid = False
                reason = "dmesg_warning_or_error"

            rows.append({
                "experiment": raw.get("experiment", ""),
                "function": EXPERIMENT_NAMES.get(exp_dir.name, exp_dir.name),
                "exp_dir": exp_dir.name,
                "build": build,
                "run_id": run_id,
                "variant": variant_name,
                "repeat": repeat,
                "iterations": iterations,
                "origin_cycles": origin if origin is not None else 0.0,
                "variant_cycles": variant if variant is not None else 0.0,
                "delta": delta if delta is not None else 0.0,
                "valid": valid,
                "invalid_reason": reason,
            })

    repeats = expected_repeats(meta, rows)
    counts = Counter((r["build"], r["variant"], r["iterations"], r["run_id"])
                     for r in rows)
    incomplete = {k for k, count in counts.items() if repeats and count != repeats}
    for r in rows:
        key = (r["build"], r["variant"], r["iterations"], r["run_id"])
        if r["valid"] and key in incomplete:
            r["valid"] = False
            r["invalid_reason"] = "incomplete_run"
    return rows


def stability(delta_median, delta_iqr):
    abs_delta = abs(delta_median)
    if abs_delta == 0:
        return "indistinguishable" if delta_iqr == 0 else "unstable"
    ratio = delta_iqr / abs_delta
    if ratio <= 0.25:
        return "strong"
    if ratio <= 0.50:
        return "usable"
    if ratio <= 1.00:
        return "weak"
    if abs_delta < delta_iqr:
        return "indistinguishable"
    return "unstable"


def aggregate(rows):
    grouped = defaultdict(list)
    raw_counts = Counter()
    for r in rows:
        key = (r["function"], r["build"], r["variant"], r["iterations"])
        raw_counts[key] += 1
        if r["valid"]:
            grouped[key].append(r)

    out = []
    for key in sorted(raw_counts, key=lambda k: (
        k[0], BUILD_ORDER.get(k[1], 99), VARIANT_ORDER.get(k[2], 99), k[3])):
        group = grouped.get(key, [])
        origin = [r["origin_cycles"] for r in group]
        pgot = [r["variant_cycles"] for r in group]
        delta = [r["delta"] for r in group]
        os = stats(origin)
        ps = stats(pgot)
        ds = stats(delta)
        delta_med = ds["median"]
        iqr = ds["iqr"]
        ratio = (iqr / abs(delta_med)) if delta_med else (0.0 if iqr == 0 else math.inf)
        overhead = (delta_med / os["median"] * 100.0) if os["median"] else 0.0
        out.append({
            "function": key[0],
            "build": key[1],
            "variant": key[2],
            "iterations": key[3],
            "n_raw": raw_counts[key],
            "n_valid": len(group),
            "origin_cycles": os["median"],
            "pgot_cycles": ps["median"],
            "delta_cycles": delta_med,
            "overhead_percent": overhead,
            "delta_iqr": iqr,
            "iqr_to_abs_delta": ratio,
            "stability": stability(delta_med, iqr),
        })
    return out


def select_rows(rows, variant=None):
    filtered = [r for r in rows if variant is None or r["variant"] == variant]
    by_key = defaultdict(list)
    for r in filtered:
        by_key[(r["function"], r["build"], r["variant"])].append(r)

    selected = []
    for key, group in by_key.items():
        group.sort(key=lambda r: (
            r["n_valid"] <= 0,
            r["iqr_to_abs_delta"] if math.isfinite(r["iqr_to_abs_delta"]) else 999999,
            -r["n_valid"],
            -r["iterations"],
        ))
        selected.append(group[0])
    return sorted(selected, key=lambda r: (
        r["function"], BUILD_ORDER.get(r["build"], 99),
        VARIANT_ORDER.get(r["variant"], 99)))


def write_csv(path, rows):
    fields = [
        "function", "build", "variant", "iterations", "n_raw", "n_valid",
        "origin_cycles", "pgot_cycles", "delta_cycles", "overhead_percent",
        "delta_iqr", "iqr_to_abs_delta", "stability",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            row = dict(r)
            for k in ["origin_cycles", "pgot_cycles", "delta_cycles",
                      "overhead_percent", "delta_iqr", "iqr_to_abs_delta"]:
                row[k] = f6(row[k]) if math.isfinite(row[k]) else "inf"
            writer.writerow({k: row[k] for k in fields})


def md_table(rows):
    lines = [
        "| Function | Build | Variant | Origin cycles | PGOT cycles | Δcycles | Overhead% | IQR(Δ) | IQR/|Δ| | Stability |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        ratio = f"{r['iqr_to_abs_delta']:.2f}" if math.isfinite(r["iqr_to_abs_delta"]) else "inf"
        lines.append(
            f"| {r['function']} | {r['build']} | {r['variant']} | "
            f"{f3(r['origin_cycles'])} | {f3(r['pgot_cycles'])} | "
            f"{f3(r['delta_cycles'])} | {f3(r['overhead_percent'])} | "
            f"{f3(r['delta_iqr'])} | {ratio} | {r['stability']} |"
        )
    return "\n".join(lines)


def write_summary(path, overview, ablation):
    by_function = defaultdict(list)
    for r in overview:
        by_function[r["function"]].append(r)

    lines = ["# Final Layer3 Summary", ""]
    lines.append("## Main Results")
    lines.append("")
    lines.append(md_table(overview))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    for fn in sorted(by_function):
        rows = by_function[fn]
        no = next((r for r in rows if r["build"] == "no_retpoline"), None)
        ret = next((r for r in rows if r["build"] == "retpoline"), None)
        if no and ret:
            no_stable = no["stability"] in {"strong", "usable"}
            ret_stable = ret["stability"] in {"strong", "usable"}
            amplified = (
                ret_stable
                and ret["delta_cycles"] > 0
                and (not no_stable or ret["delta_cycles"] > abs(no["delta_cycles"]))
            )
            if amplified:
                claim = "retpoline amplifies the visible all-pgot overhead."
            elif ret_stable and ret["delta_cycles"] > 0:
                claim = "retpoline shows a measurable positive all-pgot overhead, but the no-ret row prevents a clean amplification claim."
            else:
                claim = "this row should not be used as a strong retpoline amplification claim."
            lines.append(
                f"- `{fn}`: no-ret Δ={f3(no['delta_cycles'])} cycles "
                f"({no['stability']}), retpoline Δ={f3(ret['delta_cycles'])} "
                f"cycles ({ret['stability']}); {claim}"
            )
    lines.append("")
    lines.append("## Required Notes")
    lines.append("")
    lines.append("- `sha256_transform`: all-pgot is effectively data-pgot only; near-zero or negative deltas should be treated as indistinguishable/code-layout dominated, not as a speedup claim.")
    lines.append("- `bch_encode`: expected to show a small copied-closure overhead when stability is usable or better; weak rows should not be over-interpreted.")
    lines.append("- `zlib_deflate`: if rows are weak or indistinguishable, treat this function as noise/code-layout sensitive rather than a clean overhead estimate.")
    lines.append("- `zstd_decompress`: retpoline func/all rows are the key evidence for significant helper-call overhead when the stability label is strong or usable.")
    lines.append("- `aes_encrypt`: data/all rows measure AES S-box table indirection; func-pgot is intentionally a no-op for the timed encrypt path because no memcpy/memset/memmove callsite exists.")
    lines.append("- `lz4_decompress_safe`: data-pgot covers decode tables; func/all rows include many internal LZ4_memcpy/LZ4_memmove callsites and therefore represent a helper-call-heavy case.")
    lines.append("- `hex_dump_to_buffer`: data/all rows measure `hex_asc` table indirection in the groupsize=1 path; func-pgot is intentionally a no-op because no mem* callsite exists.")
    lines.append("- `string_escape_mem`: data/all rows measure the `hex_asc` table used by `escape_hex`; func-pgot is intentionally a no-op because no mem* callsite exists.")
    lines.append("- Rows labelled `indistinguishable`, `weak`, or `unstable` should not be used as strong quantitative claims.")
    lines.append("")
    lines.append("## Ablation Rows")
    lines.append("")
    lines.append(md_table(ablation))
    path.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True)
    args = ap.parse_args()

    results_dir = Path(args.results_dir)
    rows = []
    for exp_dir in sorted(p for p in results_dir.iterdir() if p.is_dir()):
        if exp_dir.name in EXPERIMENT_NAMES:
            rows.extend(load_experiment(exp_dir))

    aggregated = aggregate(rows)
    overview = select_rows(aggregated, variant="all_pgot")
    ablation = select_rows(aggregated)

    write_csv(results_dir / "final_layer3_overview.csv", overview)
    write_csv(results_dir / "final_layer3_ablation.csv", ablation)
    (results_dir / "final_layer3_table.md").write_text(md_table(overview) + "\n")
    write_summary(results_dir / "final_layer3_summary.md", overview, ablation)


if __name__ == "__main__":
    main()
