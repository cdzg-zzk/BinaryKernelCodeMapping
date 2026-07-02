#!/usr/bin/env python3
"""Generate a raw-value 4-panel figure for all formal microbenchmarks.

All bars use raw values:
  A. cycles/call
  B. instructions/call
  C. branches/call
  D. CPI

Each function has paired Native/Adapted bars.  The Adapted bar is annotated with
the Adapted-vs-Native delta.  This figure intentionally does not normalize
values across functions.
"""

from __future__ import annotations

import csv
import html
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE / "microbench_data.csv"
OUT = HERE / "microbench_4panel_raw_all.svg"

TEXT = "#1f2933"
MUTED = "#607083"
GRID = "#d9dee7"
AXIS = "#2d3748"
NATIVE = "#7b8494"
ADAPTED = "#3366aa"
POS = "#c85f2d"
NEG = "#2f6db5"
BG = "#ffffff"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def text(x, y, value, size=12, anchor="middle", weight="400", fill=TEXT, rotate=None):
    transform = f' transform="rotate({rotate:.1f} {x:.1f} {y:.1f})"' if rotate is not None else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}"{transform}>{esc(value)}</text>'
    )


def line(x1, y1, x2, y2, stroke=AXIS, width=1.0, dash=""):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width:.1f}"{dash_attr}/>'
    )


def rect(x, y, w, h, fill, stroke="none"):
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" stroke="{stroke}"/>'
    )


def read_rows():
    rows = []
    with DATA.open(newline="") as f:
        for raw in csv.DictReader(f):
            row = {"function": raw["function"]}
            for k, v in raw.items():
                if k in {"function", "result_dir"}:
                    row[k] = v
                else:
                    row[k] = float(v)
            row["delta_cycles_pct"] = (row["micro_cycles"] / row["native_cycles"] - 1.0) * 100.0
            row["delta_instr"] = row["micro_instr"] - row["native_instr"]
            row["delta_branches"] = row["micro_branches"] - row["native_branches"]
            row["delta_cpi"] = row["micro_cpi"] - row["native_cpi"]
            rows.append(row)
    return rows


def ymap(value, ymin, ymax, top, height):
    return top + (ymax - value) / (ymax - ymin) * height


def nice_ticks(ymax, count=4):
    step = ymax / (count - 1)
    return [i * step for i in range(count)]


def fmt_axis(value, kind):
    if kind == "cpi":
        return f"{value:.3f}"
    if value >= 1000:
        return f"{value:.0f}"
    if value >= 100:
        return f"{value:.0f}"
    return f"{value:.1f}"


def fmt_delta(value, kind):
    if kind == "cycles":
        return f"{value:+.2f}%"
    if kind == "cpi":
        return f"{value:+.3f}"
    return f"{value:+.1f}"


def draw_panel(body, rows, x, y, w, h, title, native_key, micro_key, delta_key, kind, unit):
    body.append(text(x, y - 17, title, size=15, anchor="start", weight="700"))
    body.append(text(x + w, y - 17, unit, size=10, anchor="end", fill=MUTED))
    body.append(line(x, y + h, x + w, y + h, AXIS, 1.1))
    body.append(line(x, y, x, y + h, AXIS, 1.1))

    max_value = max(max(row[native_key], row[micro_key]) for row in rows)
    ymax = max_value * 1.20
    if kind == "cpi":
        ymax = max_value * 1.25

    for tick in nice_ticks(ymax, 4):
        yy = ymap(tick, 0, ymax, y, h)
        body.append(line(x, yy, x + w, yy, GRID, 1.0, "4 4" if tick else ""))
        body.append(text(x - 8, yy + 4, fmt_axis(tick, kind), size=9.5, anchor="end"))

    group_w = w / len(rows)
    bar_w = min(20, group_w * 0.24)
    base = y + h
    for i, row in enumerate(rows):
        cx = x + group_w * (i + 0.5)
        native = row[native_key]
        micro = row[micro_key]
        delta = row[delta_key]
        ntop = ymap(native, 0, ymax, y, h)
        mtop = ymap(micro, 0, ymax, y, h)
        color = POS if delta > 0 else NEG
        body.append(rect(cx - bar_w - 3, ntop, bar_w, base - ntop, NATIVE))
        body.append(rect(cx + 3, mtop, bar_w, base - mtop, ADAPTED))
        label_y = max(y + 10, mtop - 6)
        # If a bar is very close to zero, keep the label inside the plot but
        # away from the x labels.
        label_y = min(label_y, y + h - 12)
        body.append(text(cx + 3 + bar_w / 2, label_y, fmt_delta(delta, kind), size=8.3, weight="700", fill=color))
        body.append(text(cx, y + h + 47, row["function"], size=8.8, rotate=-35, anchor="end"))


def main():
    rows = read_rows()
    width, height = 1620, 930
    body = [
        rect(0, 0, width, height, BG),
        text(width / 2, 30, "Microbenchmark Metrics: Raw Native vs Adapted Values", size=19, weight="700"),
        text(width / 2, 54, "All panels use raw metric values; Adapted bars are annotated with delta vs Native", size=12, fill=MUTED),
    ]

    left, top = 102, 108
    panel_w, panel_h = 640, 230
    gap_x, gap_y = 150, 148

    draw_panel(body, rows, left, top, panel_w, panel_h,
               "A. cycles/call", "native_cycles", "micro_cycles", "delta_cycles_pct", "cycles", "raw cycles/call")
    draw_panel(body, rows, left + panel_w + gap_x, top, panel_w, panel_h,
               "B. instructions/call", "native_instr", "micro_instr", "delta_instr", "instr", "raw instructions/call")
    draw_panel(body, rows, left, top + panel_h + gap_y, panel_w, panel_h,
               "C. branches/call", "native_branches", "micro_branches", "delta_branches", "branches", "raw branches/call")
    draw_panel(body, rows, left + panel_w + gap_x, top + panel_h + gap_y, panel_w, panel_h,
               "D. CPI", "native_cpi", "micro_cpi", "delta_cpi", "cpi", "raw CPI")

    body.append(rect(width - 248, height - 34, 18, 11, NATIVE))
    body.append(text(width - 224, height - 25, "Native", size=11, anchor="start"))
    body.append(rect(width - 148, height - 34, 18, 11, ADAPTED))
    body.append(text(width - 124, height - 25, "Adapted", size=11, anchor="start"))

    svg = "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        *body,
        "</svg>",
        "",
    ])
    OUT.write_text(svg, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
