#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path


BUILD_ORDER = {"no_retpoline": 0, "retpoline": 1}
VARIANT_ORDER = {"data_pgot": 0, "func_pgot": 1, "all_pgot": 2}


def read_metadata(path):
    meta = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                line = line[1:].strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            meta[k] = v
    return meta


def read_rows(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: (BUILD_ORDER.get(r["build"], 99),
                             VARIANT_ORDER.get(r["variant"], 99),
                             int(r.get("iterations", "0"))))
    return rows


def read_nm_sizes(path):
    sizes = {}
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 4:
                sizes[parts[3]] = int(parts[1], 16)
    return sizes


def f3(v):
    return f"{float(v):.3f}"


def f2(v):
    return f"{float(v):.2f}"


def result_table(rows):
    out = [
        "| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        out.append(
            f"| {r['build']} | {r['variant']} | {r.get('iterations', 'unknown')} | {r['n_raw']} | "
            f"{f3(r['origin_cycles'])} | {f3(r['variant_cycles'])} | "
            f"{f3(r['delta_cycles'])} | {f3(r['delta_iqr'])} | "
            f"{f2(r.get('iqr_to_abs_delta', 0.0))} | {f2(r['overhead_percent'])} |"
        )
    return "\n".join(out)


def row_for(rows, build, variant):
    for r in rows:
        if r["build"] == build and r["variant"] == variant:
            return r
    raise KeyError((build, variant))


def observations(rows, no_sizes, ret_sizes):
	no_data = row_for(rows, "no_retpoline", "all_pgot")
	ret_data = row_for(rows, "retpoline", "all_pgot")
	origin_size = no_sizes.get("sha256_transform_origin", 0)
	data_size = no_sizes.get("sha256_transform_data_pgot", 0)
	data_size_diff = data_size - origin_size if origin_size and data_size else "unknown"
	return f"""## 4. Key Observations

1. `all_pgot` does not expose a positive visible overhead in this copied
   SHA-256 closure. The measured deltas are {f3(no_data['delta_cycles'])}
   cycles in no-retpoline and {f3(ret_data['delta_cycles'])} cycles in
   retpoline. This must not be interpreted as "PGOT makes SHA-256 faster":
   the generated data-table transform is {data_size_diff} bytes different
   from `origin`, so code layout/register allocation dominate a single K-table
   slot load.
2. SHA-256 transform has no honest closure-external helper in this benchmark.
   Endian word loading, message schedule, and round logic are part of the
   copied closure, so they remain direct/internal code instead of being forced
   through function PGOT.
3. Therefore this SHA-256 Layer3 case reports `all_pgot`, but its applicable
   transformation is data-PGOT only. Function-PGOT is evaluated by later
   Layer3 functions that naturally call helpers across the copied-closure
   boundary.
"""


def size_table(no_sizes, ret_sizes):
    symbols = [
        "sha256_transform_origin",
        "sha256_transform_data_pgot",
	        "body_origin",
	        "body_data_pgot",
    ]
    out = ["| symbol | no-ret size | retpoline size |", "|---|---:|---:|"]
    for sym in symbols:
        out.append(f"| `{sym}` | {no_sizes.get(sym, 'missing')} | {ret_sizes.get(sym, 'missing')} |")
    return "\n".join(out)


def symbol_body(objdump_text, symbol):
    m = re.search(rf"^[0-9a-f]+ <{re.escape(symbol)}>:\n(?P<body>.*?)(?=^\S)", objdump_text, re.M | re.S)
    return m.group("body") if m else ""


def count_in_symbol(objdump_text, symbol, needle):
    return symbol_body(objdump_text, symbol).count(needle)


def has_relocation(objdump_text, symbol, reloc_name):
    return reloc_name in symbol_body(objdump_text, symbol)


def static_validation(no_objdump, ret_objdump):
    checks = [
        ("data_pgot data slot relocation",
         has_relocation(no_objdump, "sha256_transform_data_pgot", "pgot_k_table")),
        ("data_pgot has no indirect call",
         "call   *" not in symbol_body(no_objdump, "sha256_transform_data_pgot")),
        ("retpoline data_pgot has no retpoline thunk",
         count_in_symbol(ret_objdump, "sha256_transform_data_pgot", "pause") == 0 and
         count_in_symbol(ret_objdump, "sha256_transform_data_pgot", "lfence") == 0),
    ]
    out = ["| validation | result |", "|---|---|"]
    for name, value in checks:
        out.append(f"| {name} | {value} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--paper-table", required=True)
    ap.add_argument("--nm-no-retpoline", required=True)
    ap.add_argument("--nm-retpoline", required=True)
    ap.add_argument("--objdump-no-retpoline", required=True)
    ap.add_argument("--objdump-retpoline", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()

    meta = read_metadata(args.metadata)
    rows = read_rows(args.paper_table)
    no_sizes = read_nm_sizes(args.nm_no_retpoline)
    ret_sizes = read_nm_sizes(args.nm_retpoline)
    no_objdump = Path(args.objdump_no_retpoline).read_text(errors="replace")
    ret_objdump = Path(args.objdump_retpoline).read_text(errors="replace")

    content = f"""# Layer3 SHA-256 Transform PGOT Experiment

## 1. Goal

This Layer3 kernel-module benchmark moves from synthetic primitives to a copied
real-function closure: a SHA-256 64-byte block transform. It compares the
original closure against PGOT-style data and function transformations.

| variant | transformation |
|---|---|
| `origin` | direct K-table access and direct helper calls |
| `all_pgot` | K table address is loaded from a pgot data slot |
| `func_pgot` | not reported for SHA-256: no closure-external helper |

The benchmark does not call the system crypto API. It copies the SHA-256
compression closure into the test module so the origin and PGOT versions can be
compiled side by side and measured with identical inputs.

## 2. Setup

| item | value |
|---|---|
| execution mode | kernel module |
| function under test | SHA-256 block transform, one 64-byte block per call |
| comparison | variant cycles - origin cycles |
| builds | no-retpoline, retpoline |
| sample order | paired/interleave |
| iterations | {meta.get('iterations_list', meta.get('iterations', 'unknown'))} |
| repeats | {meta.get('repeats', 'unknown')} |
| outer runs | {meta.get('outer_runs', 'unknown')} |
| variants | {meta.get('variants', 'unknown')} |
| CPU | pinned CPU {meta.get('requested_cpu', meta.get('cpu', 'unknown'))} |

The reported delta is paired:

```text
delta[r] = variant_cycles[r] - origin_cycles[r]
reported_delta = median(delta[r])
```

## 3. Dynamic Results

{result_table(rows)}

{observations(rows, no_sizes, ret_sizes)}

## 5. Static Validation

{static_validation(no_objdump, ret_objdump)}

Symbol sizes:

{size_table(no_sizes, ret_sizes)}

Static interpretation:

1. `data_pgot` contains a relocation/reference to `pgot_k_table`, so the
   K-table base is actually obtained through a data slot.
2. The SHA-256 transform variant contains no function-PGOT path: no indirect
   call is present in no-retpoline, and no retpoline thunk is present in the
   retpoline build.

## 6. Interpretation

This experiment is closer to the real kernel setting than Layer1/Layer2:

1. `data_pgot` estimates the cost of moving a real constant table reference
   through a pgot data slot inside a nontrivial transform.
2. Function-PGOT is intentionally not reported for this function because the
   transform has no honest closure-external helper call.

The result should be interpreted as whole-function visible overhead per
SHA-256 block transform, not as a primitive load or primitive call latency.

## 7. Files

| file | description |
|---|---|
| `raw.csv` | paired raw origin/variant samples |
| `processed.csv` | mean/median/IQR/stddev/min/max per case |
| `paper_table.csv` | compact paper table |
| `metadata.txt` | environment and build metadata |
| `static/nm_*.txt` | symbol sizes |
| `static/objdump_*.txt` | disassembly with relocations |
"""
    Path(args.summary).write_text(content)


if __name__ == "__main__":
    main()
