#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path


ORDER = {
    "none": 0,
    "work_only": 1,
    "before": 2,
    "inside": 3,
    "after": 4,
}


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
    rows.sort(key=lambda r: (
        {"no_retpoline": 0, "retpoline": 1}.get(r["build"], 99),
        ORDER.get(r["placement"], 99),
        int(r["workload"]),
    ))
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


def workloads(rows):
    return sorted({int(r["workload"]) for r in rows if r["placement"] != "none"})


def row_map(rows):
    return {(r["build"], r["placement"], int(r["workload"])): r for r in rows}


def get(rows, build, placement, workload):
    return row_map(rows)[(build, placement, workload)]


def table_for_build(rows, build):
    out = [
        "| placement | workload | direct | pgot | delta | IQR | overhead% |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        if r["build"] != build:
            continue
        out.append(
            f"| {r['placement']} | {r['workload']} | {f3(r['direct_cycles'])} | "
            f"{f3(r['pgot_cycles'])} | {f3(r['delta_cycles'])} | "
            f"{f3(r['delta_iqr'])} | {f2(r['overhead_percent'])} |"
        )
    return "\n".join(out)


def work_only_table(rows, build):
    out = [
        "| workload | work_only cycles | IQR(delta same-body) |",
        "|---:|---:|---:|",
    ]
    for w in workloads(rows):
        r = get(rows, build, "work_only", w)
        out.append(f"| {w} | {f3(r['direct_cycles'])} | {f3(r['delta_iqr'])} |")
    return "\n".join(out)


def retpoline_delta_table(rows):
    out = [
        "| workload | work_only cycles | before delta | inside delta | after delta | ordering by visible overhead |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for w in workloads(rows):
        work = get(rows, "retpoline", "work_only", w)
        vals = []
        for p in ["before", "inside", "after"]:
            vals.append((p, float(get(rows, "retpoline", p, w)["delta_cycles"])))
        ordered = " > ".join(name for name, _ in sorted(vals, key=lambda x: x[1], reverse=True))
        out.append(
            f"| {w} | {f3(work['direct_cycles'])} | {vals[0][1]:.3f} | "
            f"{vals[1][1]:.3f} | {vals[2][1]:.3f} | {ordered} |"
        )
    return "\n".join(out)


def target_size_table(sizes, wlist):
    out = ["| symbol | size bytes |", "|---|---:|"]
    for w in wlist:
        sym = f"target_work_{w}"
        out.append(f"| `{sym}` | {sizes.get(sym, 'missing')} |")
    return "\n".join(out)


def body_size_table(sizes, wlist):
    out = [
        "| workload | work_only | DIRECT before | PGOT before | DIRECT inside | PGOT inside | DIRECT after | PGOT after |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for w in wlist:
        vals = [
            sizes.get(f"body_WORK_only_{w}", "missing"),
            sizes.get(f"body_DIRECT_before_{w}", "missing"),
            sizes.get(f"body_PGOT_before_{w}", "missing"),
            sizes.get(f"body_DIRECT_inside_{w}", "missing"),
            sizes.get(f"body_PGOT_inside_{w}", "missing"),
            sizes.get(f"body_DIRECT_after_{w}", "missing"),
            sizes.get(f"body_PGOT_after_{w}", "missing"),
        ]
        out.append(f"| {w} | " + " | ".join(str(v) for v in vals) + " |")
    return "\n".join(out)


def contains_symbol_block_pattern(objdump_text, symbol, patterns):
    m = re.search(rf"^[0-9a-f]+ <{re.escape(symbol)}>:\n(?P<body>.*?)(?=^\S)", objdump_text, re.M | re.S)
    if not m:
        return False
    body = m.group("body")
    return all(p in body for p in patterns)


def first_threshold(rows, threshold=1.0):
    for w in workloads(rows):
        vals = [abs(float(get(rows, "retpoline", p, w)["delta_cycles"])) for p in ["before", "inside", "after"]]
        if all(v <= threshold for v in vals):
            return w
    return None


def emit_summary(args):
    meta = read_metadata(args.metadata)
    rows = read_rows(args.paper_table)
    sizes = read_nm_sizes(args.nm_retpoline)
    ret_objdump = Path(args.objdump_retpoline).read_text(errors="replace")
    noret_objdump = Path(args.objdump_no_retpoline).read_text(errors="replace")
    wlist = workloads(rows)

    ret_has_thunk = contains_symbol_block_pattern(
        ret_objdump,
        "body_PGOT_inside_4",
        ["mov", "%rax", "pause", "lfence", "ret"],
    )
    noret_has_indirect = contains_symbol_block_pattern(
        noret_objdump,
        "body_PGOT_inside_4",
        ["mov", "%rax", "call   *%rax"],
    )

    n_raw = get(rows, "retpoline", "none", 0)["n_raw"]
    ret_none = get(rows, "retpoline", "none", 0)
    threshold = first_threshold(rows)
    threshold_text = str(threshold) if threshold is not None else "not reached"

    content = f"""# Layer2 Func-PGOT Unfenced Placement/Workload Experiment

## 1. Experiment Goal

This kernel-module experiment measures the visible overhead of stable-target
`func-pgot` in an unfenced practical instruction stream.

It compares:

```c
// direct
x = target_work_N(x);

// pgot
bench_fn_t volatile *slot = pgot_func_table;
bench_fn_t f = slot[idx];
x = f(x);
```

The experiment now includes four workload contexts:

| placement | measured body |
|---|---|
| `work_only` | `WORK_N` only, no target call |
| `before` | `WORK_N; CALL(target_work_0)` |
| `inside` | `CALL(target_work_N)` |
| `after` | `CALL(target_work_0); WORK_N` |

`none/workload=0` is kept as the call-only baseline.

## 2. Experimental Setup

| item | value |
|---|---|
| execution mode | kernel module |
| function events | 1 call event / iteration |
| target pattern | stable target |
| fence mode | unfenced |
| builds | no-retpoline, retpoline |
| sample order | paired/interleave |
| iterations | {meta.get("iterations", "unknown")} |
| repeats | {meta.get("repeats", "unknown")} |
| outer runs | {meta.get("outer_runs", "unknown")} |
| raw samples / case | {n_raw} |
| workload grid | {meta.get("workloads", ",".join(map(str, wlist)))} |
| placements | {meta.get("placements", "none,work_only,before,inside,after")} |
| CPU | pinned CPU {meta.get("requested_cpu", meta.get("cpu", "unknown"))} |

The reported delta is paired:

```text
delta[r] = pgot_cycles[r] - direct_cycles[r]
reported_delta = median(delta[r])
```

For `work_only`, both measured sides run the same no-call body. Its `direct`
cycle column is used as the workload-only baseline; its delta should stay near
measurement noise.

## 3. Key Code

```c
#define CALL_DIRECT(work) do {{ \\
    x = target_work_##work(x); \\
}} while (0)

#define CALL_PGOT(idx) do {{ \\
    bench_fn_t volatile *slot__ = pgot_func_table; \\
    bench_fn_t f__ = slot__[idx]; \\
    x = f__(x); \\
}} while (0)
```

`slot__ = pgot_func_table` only forms the table base. The actual pgot memory
operation is the slot load `f__ = slot__[idx]`.

## 4. Dynamic Results

### 4.1 Work-Only Baseline

The retpoline build's `work_only` body has no target call and no pgot call. It
shows how large the ordinary work stream is at each workload.

{work_only_table(rows, "retpoline")}

The retpoline call-only baseline is:

```text
none/workload=0 delta = {f3(ret_none["delta_cycles"])} cycles/iteration
```

The first workload where all three retpoline placements have |delta| <= 1 cycle
in this run is:

```text
workload = {threshold_text}
```

### 4.2 no-retpoline

{table_for_build(rows, "no_retpoline")}

### 4.3 retpoline

{table_for_build(rows, "retpoline")}

### 4.4 Placement Ordering Under Retpoline

{retpoline_delta_table(rows)}

This ordering table is computed mechanically from the current data. It should
be interpreted together with repeatability checks. The stable claim is the
threshold behavior, not a universal before/inside/after ordering across every
workload.

## 5. Static Analysis Evidence

### 5.1 pgot call validation

retpoline build contains inline retpoline structure in `body_PGOT_inside_4`:

```text
pause/lfence/ret found = {ret_has_thunk}
```

no-retpoline build contains a normal indirect call in `body_PGOT_inside_4`:

```text
call *%rax found = {noret_has_indirect}
```

The important no-retpoline shape is:

```asm
mov    pgot_func_table[idx], %rax
call   *%rax
```

The important retpoline shape is:

```asm
mov    pgot_func_table[idx], %rax
call   <inline retpoline sequence>
pause
lfence
ret
```

Thus the pgot path is not optimized into a direct call.

### 5.2 Function and body sizes

Target function sizes:

{target_size_table(sizes, wlist)}

Retpoline body sizes:

{body_size_table(sizes, wlist)}

Static interpretation:

1. `work_only` contains only the expanded arithmetic work in the caller loop.
2. `inside` keeps the caller body almost fixed; workload moves into
   `target_work_N`.
3. `before` and `after` expand workload in the caller, so caller size and call
   position change with workload.
4. Therefore, before/inside/after are not just the same instructions shifted in
   time. They alter caller/callee boundary, loop layout, and retpoline context.

## 6. Interpretation

The experiment separates three questions:

1. How large is the ordinary work stream without any target call? This is
   answered by `work_only`.
2. How large is call-only retpoline func-pgot overhead? This is answered by
   `none/workload=0`.
3. How does the same workload affect visible overhead when placed before,
   inside, or after the call? This is answered by the placement table.

The correct interpretation is visible whole-loop overhead, not pure hardware
latency. The target or after-work cannot execute before retpoline completes
control transfer. The reduction in delta means the fixed retpoline disturbance
becomes less visible in the steady-state loop as ordinary work and code layout
change.

## 7. Conclusions

1. `func-pgot` adds one pgot function-slot load. Under no-retpoline this feeds
   a normal indirect call; under retpoline it feeds the inline retpoline
   sequence.
2. The `work_only` group provides the no-call workload scale and helps identify
   when ordinary work is large enough to make retpoline overhead less visible.
3. Same-workload before/inside/after can differ because the machine-code shape
   differs: caller-expanded work, callee-contained work, and post-call work
   create different front-end and loop contexts.
4. A fixed ordering should only be claimed if it survives repeatability checks.
   If a workload is in the transition region, report it as transition behavior
   rather than as a deterministic primitive cost.

## 8. Files

| file | description |
|---|---|
| `raw.csv` | paired raw direct/pgot samples |
| `processed.csv` | mean/median/IQR/stddev/min/max per case |
| `paper_table.csv` | compact table for paper figures |
| `metadata.txt` | environment and build parameters |
| `static/nm_*.txt` | symbol sizes |
| `static/objdump_*.txt` | disassembly validation |
"""
    Path(args.summary).write_text(content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--paper-table", required=True)
    ap.add_argument("--nm-retpoline", required=True)
    ap.add_argument("--objdump-retpoline", required=True)
    ap.add_argument("--objdump-no-retpoline", required=True)
    ap.add_argument("--summary", required=True)
    emit_summary(ap.parse_args())


if __name__ == "__main__":
    main()
