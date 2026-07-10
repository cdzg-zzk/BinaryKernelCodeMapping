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


def symbol_body(objdump_text, symbol):
    m = re.search(rf"^[0-9a-f]+ <{re.escape(symbol)}>:\n(?P<body>.*?)(?=^\S)",
                  objdump_text, re.M | re.S)
    return m.group("body") if m else ""


def has_indirect_call(body):
    return "call   *" in body or re.search(r"call\s+\*%", body) is not None


def static_validation(no_objdump, ret_objdump, pgot_symbol, slot_symbol):
    no_body = symbol_body(no_objdump, pgot_symbol)
    ret_body = symbol_body(ret_objdump, pgot_symbol)
    checks = [
        (f"{pgot_symbol} references {slot_symbol}", slot_symbol in no_body),
        (f"{pgot_symbol} has no-retpoline indirect call", has_indirect_call(no_body)),
        (f"{pgot_symbol} has retpoline thunk markers",
         ("pause" in ret_body and "lfence" in ret_body and "ret" in ret_body)),
    ]
    out = ["| validation | result |", "|---|---|"]
    for name, value in checks:
        out.append(f"| {name} | {value} |")
    return "\n".join(out)


def size_table(no_sizes, ret_sizes):
    symbols = ["body_origin", "body_func_pgot", "pgot_func_table"]
    out = ["| symbol | no-ret size | retpoline size |", "|---|---:|---:|"]
    for sym in symbols:
        out.append(f"| `{sym}` | {no_sizes.get(sym, 'missing')} | {ret_sizes.get(sym, 'missing')} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--function", required=True)
    ap.add_argument("--scope-note", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--paper-table", required=True)
    ap.add_argument("--nm-no-retpoline", required=True)
    ap.add_argument("--nm-retpoline", required=True)
    ap.add_argument("--objdump-no-retpoline", required=True)
    ap.add_argument("--objdump-retpoline", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--pgot-symbol", default="body_func_pgot")
    ap.add_argument("--slot-symbol", default="pgot_func_table")
    args = ap.parse_args()

    meta = read_metadata(args.metadata)
    rows = read_rows(args.paper_table)
    no_sizes = read_nm_sizes(args.nm_no_retpoline)
    ret_sizes = read_nm_sizes(args.nm_retpoline)
    no_objdump = Path(args.objdump_no_retpoline).read_text(errors="replace")
    ret_objdump = Path(args.objdump_retpoline).read_text(errors="replace")

    content = f"""# {args.title}

## 1. Goal

This Layer3 kernel-module benchmark measures a real exported kernel function
entry:

```text
{args.function}
```

The `origin` path calls the exported function directly. The `func_pgot` path
loads the same function address from `pgot_func_table[0]` and then performs an
indirect call. Inputs, output buffers, reset/setup code, iteration count, and
sample order are identical between the two paths.

Scope note:

```text
{args.scope_note}
```

This experiment therefore evaluates function-entry PGOT overhead for a real
kernel workload. It does not claim to rewrite every internal helper of the
kernel implementation unless the corresponding benchmark source says so.

## 2. Setup

| item | value |
|---|---|
| execution mode | kernel module |
| comparison | func_pgot cycles - origin cycles |
| builds | no-retpoline, retpoline |
| sample order | paired/interleave |
| iterations | {meta.get('iterations_list', meta.get('iterations', 'unknown'))} |
| warmup | {meta.get('warmup', 'unknown')} |
| repeats | {meta.get('repeats', 'unknown')} |
| outer runs | {meta.get('outer_runs', 'unknown')} |
| variants | {meta.get('variants', 'unknown')} |
| CPU | pinned CPU {meta.get('requested_cpu', meta.get('cpu', 'unknown'))} |

The reported delta is paired:

```text
delta[r] = func_pgot_cycles[r] - origin_cycles[r]
reported_delta = median(delta[r])
```

## 3. Dynamic Results

{result_table(rows)}

## 4. Static Validation

{static_validation(no_objdump, ret_objdump, args.pgot_symbol, args.slot_symbol)}

Symbol sizes:

{size_table(no_sizes, ret_sizes)}

## 5. Interpretation

The static validation establishes that the PGOT path actually performs a slot
load plus indirect call, and that the retpoline build uses an inline retpoline
sequence for that indirect call. The dynamic table should be read as
whole-function visible overhead per call, not primitive indirect-call latency.
For large real functions, the absolute delta can be small or hidden by code
layout, cache state, and surrounding reset/setup work.

## 6. Files

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
