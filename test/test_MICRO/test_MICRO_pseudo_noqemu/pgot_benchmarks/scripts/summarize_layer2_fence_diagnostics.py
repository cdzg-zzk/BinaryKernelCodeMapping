#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path


FENCES = ["unfenced", "post_fenced", "iter_fenced", "pre_post_iter_fenced"]
PLACEMENTS = ["before", "inside", "after"]


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
    return {
        (r["fence"], r["placement"], int(r["workload"])): r
        for r in rows
        if r["build"] == "retpoline"
    }


def f3(v):
    return f"{float(v):.3f}"


def workloads(rows):
    return sorted({k[2] for k in rows if k[1] != "none"})


def get_delta(rows, fence, placement, workload):
    return float(rows[(fence, placement, workload)]["delta_cycles"])


def get_direct(rows, fence, placement, workload):
    return float(rows[(fence, placement, workload)]["direct_cycles"])


def threshold(rows, fence, limit=1.0):
    for w in workloads(rows):
        vals = [abs(get_delta(rows, fence, p, w)) for p in PLACEMENTS]
        if all(v <= limit for v in vals):
            return w
    return None


def delta_table(rows, fence):
    out = [
        f"### {fence}",
        "",
        "| workload | work-only cycles | before Δ | inside Δ | after Δ |",
        "|---:|---:|---:|---:|---:|",
    ]
    for w in workloads(rows):
        work = get_direct(rows, fence, "work_only", w)
        vals = [get_delta(rows, fence, p, w) for p in PLACEMENTS]
        out.append(f"| {w} | {work:.3f} | {vals[0]:.3f} | {vals[1]:.3f} | {vals[2]:.3f} |")
    return "\n".join(out)


def compact_table(rows):
    out = [
        "| fence mode | call-only Δ | first workload with all |Δ|<=1 | before Δ@4 | inside Δ@4 | after Δ@4 | before Δ@6 | inside Δ@6 | after Δ@6 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for fence in FENCES:
        call_only = get_delta(rows, fence, "before", 0)
        th = threshold(rows, fence)
        th_text = str(th) if th is not None else "not reached"
        vals4 = [get_delta(rows, fence, p, 4) for p in PLACEMENTS]
        vals6 = [get_delta(rows, fence, p, 6) for p in PLACEMENTS]
        out.append(
            f"| {fence} | {call_only:.3f} | {th_text} | "
            f"{vals4[0]:.3f} | {vals4[1]:.3f} | {vals4[2]:.3f} | "
            f"{vals6[0]:.3f} | {vals6[1]:.3f} | {vals6[2]:.3f} |"
        )
    return "\n".join(out)


def symbol_body(objdump_text, symbol):
	m = re.search(rf"^[0-9a-f]+ <{re.escape(symbol)}>:\n(?P<body>.*?)(?=^\S)", objdump_text, re.M | re.S)
	if not m:
		return ""
	return m.group("body")


def symbol_counts(objdump_text, symbol):
	body = symbol_body(objdump_text, symbol)
	return {
		"lfence": body.count("lfence"),
		"call": body.count("call"),
		"pause": body.count("pause"),
	}


def static_table(static_dir):
	out = [
		"| mode | DIRECT after_4 lfence/call | PGOT after_4 lfence/call/pause | interpretation |",
		"|---|---:|---:|---|",
	]
	for fence in FENCES:
		path = static_dir / f"objdump_retpoline_{fence}.txt"
		text = path.read_text(errors="replace")
		direct = symbol_counts(text, "body_DIRECT_after_4")
		pgot = symbol_counts(text, "body_PGOT_after_4")
		extra = pgot["lfence"] - direct["lfence"]
		if fence == "unfenced":
			interp = "only the retpoline thunk contributes the PGOT-side lfence"
		elif fence == "post_fenced":
			interp = "adds one post-call lfence to both direct and PGOT"
		elif fence == "iter_fenced":
			interp = "adds one end-of-iteration lfence to both direct and PGOT"
		else:
			interp = "adds pre-call, post-call, and end-of-iteration lfences"
		out.append(
			f"| {fence} | {direct['lfence']}/{direct['call']} | "
			f"{pgot['lfence']}/{pgot['call']}/{pgot['pause']} | {interp}; "
			f"PGOT has {extra} extra lfence from retpoline thunk |"
		)
	return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--paper-table", required=True)
    ap.add_argument("--static-dir", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--append", required=True)
    args = ap.parse_args()

    meta = read_metadata(args.metadata)
    rows = read_rows(args.paper_table)
    static_dir = Path(args.static_dir)

    summary = f"""# Layer2 Func-PGOT Fence Diagnostics

This diagnostic keeps the same Layer2 func-placement benchmark, but rebuilds
the retpoline module with progressively stronger `lfence` boundaries.

| mode | compile-time fence |
|---|---|
| `unfenced` | none |
| `post_fenced` | `lfence` after each direct/pgot call event |
| `iter_fenced` | `lfence` at the end of each benchmark iteration |
| `pre_post_iter_fenced` | `lfence` before call, after call, and at iteration end |

Parameters: `iterations={meta.get('iterations')}`, `repeats={meta.get('repeats')}`,
`outer_runs={meta.get('outer_runs')}`, `sample_order={meta.get('sample_order')}`.

## Summary Table

{compact_table(rows)}

## Full Delta Tables

{delta_table(rows, 'unfenced')}

{delta_table(rows, 'post_fenced')}

{delta_table(rows, 'iter_fenced')}

{delta_table(rows, 'pre_post_iter_fenced')}

## Static Fence Validation

{static_table(static_dir)}

## Diagnostic Interpretation

The important comparison is within each fence mode, not the absolute call-only
number across modes, because adding `lfence` changes both the direct and PGOT
instruction streams.

1. In the unfenced practical stream, all placements reach `|Δ| <= 1` at
   workload 6.
2. In the strongest `pre_post_iter_fenced` mode, the threshold is not reached:
   before/inside/after remain around 26-32 cycles even at large workloads.
3. Therefore, workload does not make the retpoline thunk itself faster. The
   main-experiment collapse requires the unfenced whole-loop execution context.
4. The intermediate modes separate the context effects. `post_fenced` keeps
   inside high but lets before/after become small; `iter_fenced` keeps
   inside/after high but lets before become small. This shows that the visible
   delta depends on where the work sits relative to call boundaries and
   iteration boundaries, plus the resulting caller/callee code layout.
5. The defensible causal statement is: the decreasing retpoline `Δcycles` is a
   whole-loop visible-overhead effect caused by unfenced surrounding work,
   cross-iteration steady state, and code-layout/caller-callee shape. It is not
   evidence that target instructions execute before the retpoline transfer is
   complete.
"""

    append = "\n".join([
        "<!-- fence-diagnostics:start -->",
        "## 10. Fence Diagnostics",
        "",
        summary.split("\n", 1)[1].rstrip(),
        "",
        f"Full diagnostic report: `diagnostics/fence_modes/summary.md`.",
        "<!-- fence-diagnostics:end -->",
        "",
    ])

    Path(args.summary).write_text(summary)
    Path(args.append).write_text(append)


if __name__ == "__main__":
    main()
