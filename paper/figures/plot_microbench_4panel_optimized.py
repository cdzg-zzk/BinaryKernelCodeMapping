#!/usr/bin/env python3
"""Generate an optimized 4-panel microbenchmark figure.

Each panel uses Native-normalized paired bars:
  Native = 1.0
  Adapted = Adapted raw metric / Native raw metric

The Adapted bar is annotated with the raw delta:
  cycles/call: percent delta
  instructions/call: Adapted - Native instructions/call
  branches/call: Adapted - Native branches/call
  CPI: Adapted - Native CPI

This avoids hiding small functions behind large raw values while still showing
both Native and Adapted bars for every metric.
"""

from __future__ import annotations

import csv
import html
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE / "microbench_data.csv"
OUT = HERE / "microbench_4panel_optimized.svg"

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
            row["cycles_ratio"] = row["micro_cycles"] / row["native_cycles"]
            row["instr_ratio"] = row["micro_instr"] / row["native_instr"]
            row["branches_ratio"] = row["micro_branches"] / row["native_branches"]
            row["cpi_ratio"] = row["micro_cpi"] / row["native_cpi"]
            row["delta_cycles_pct"] = (row["cycles_ratio"] - 1.0) * 100.0
            row["delta_instr"] = row["micro_instr"] - row["native_instr"]
            row["delta_branches"] = row["micro_branches"] - row["native_branches"]
            row["delta_cpi"] = row["micro_cpi"] - row["native_cpi"]
            rows.append(row)
    return rows


def ymap(value, ymin, ymax, top, height):
    return top + (ymax - value) / (ymax - ymin) * height


def ticks_for(ymin, ymax):
    mid = 1.0
    return [ymin, (ymin + mid) / 2, mid, (mid + ymax) / 2, ymax]


def fmt_delta(value, kind):
    if kind == "cycles":
        return f"{value:+.2f}%"
    if kind == "instr":
        return f"{value:+.1f}"
    if kind == "branches":
        return f"{value:+.1f}"
    return f"{value:+.3f}"


def draw_panel(
    body,
    rows,
    x,
    y,
    w,
    h,
    title,
    ratio_key,
    delta_key,
    kind,
    ypad,
    note,
):
    ratios = [row[ratio_key] for row in rows] + [1.0]
    ymin = min(ratios) - ypad
    ymax = max(ratios) + ypad
    # Keep a sane minimum window so very tiny changes still look like paired bars.
    if ymax - ymin < 0.04:
        center = (ymin + ymax) / 2
        ymin = center - 0.02
        ymax = center + 0.02
    ymin = min(ymin, 1.0 - 0.005)
    ymax = max(ymax, 1.0 + 0.005)

    body.append(text(x, y - 17, title, size=15, anchor="start", weight="700"))
    body.append(text(x + w, y - 17, note, size=10, anchor="end", fill=MUTED))
    body.append(line(x, y + h, x + w, y + h, AXIS, 1.1))
    body.append(line(x, y, x, y + h, AXIS, 1.1))

    for tick in ticks_for(ymin, ymax):
        yy = ymap(tick, ymin, ymax, y, h)
        body.append(line(x, yy, x + w, yy, GRID, 1.0, "4 4" if abs(tick - 1.0) > 1e-9 else ""))
        body.append(text(x - 8, yy + 4, f"{tick:.3f}", size=9, anchor="end"))

    group_w = w / len(rows)
    bar_w = min(18, group_w * 0.28)
    base = ymap(ymin, ymin, ymax, y, h)
    for i, row in enumerate(rows):
        cx = x + group_w * (i + 0.5)
        native_top = ymap(1.0, ymin, ymax, y, h)
        adapted_ratio = row[ratio_key]
        adapted_top = ymap(adapted_ratio, ymin, ymax, y, h)
        delta = row[delta_key]
        color = POS if delta > 0 else NEG
        body.append(rect(cx - bar_w - 3, native_top, bar_w, base - native_top, NATIVE))
        body.append(rect(cx + 3, adapted_top, bar_w, base - adapted_top, ADAPTED))
        label_y = adapted_top - 6 if adapted_ratio >= 1.0 else adapted_top + 13
        # Prevent labels from falling below the plot when the adapted bar is near the bottom.
        label_y = min(max(label_y, y + 10), y + h - 5)
        body.append(text(cx + 3 + bar_w / 2, label_y, fmt_delta(delta, kind), size=8.5, weight="700", fill=color))
        body.append(text(cx, y + h + 43, row["function"], size=9.5, rotate=-34, anchor="end"))


def main():
    rows = read_rows()
    width, height = 1500, 900
    body = [
        rect(0, 0, width, height, BG),
        text(width / 2, 30, "Microbenchmark Metrics: Native-Normalized Bars with Raw Deltas", size=19, weight="700"),
        text(
            width / 2,
            54,
            "All panels show Native = 1.0 and Adapted = Adapted/Native; labels on Adapted bars show raw delta",
            size=12,
            fill=MUTED,
        ),
    ]

    left, top = 94, 106
    panel_w, panel_h = 570, 230
    gap_x, gap_y = 146, 142

    draw_panel(body, rows, left, top, panel_w, panel_h,
               "A. cycles/call", "cycles_ratio", "delta_cycles_pct", "cycles", 0.006,
               "label: % delta")
    draw_panel(body, rows, left + panel_w + gap_x, top, panel_w, panel_h,
               "B. instructions/call", "instr_ratio", "delta_instr", "instr", 0.006,
               "label: Adapted - Native")
    draw_panel(body, rows, left, top + panel_h + gap_y, panel_w, panel_h,
               "C. branches/call", "branches_ratio", "delta_branches", "branches", 0.008,
               "label: Adapted - Native")
    draw_panel(body, rows, left + panel_w + gap_x, top + panel_h + gap_y, panel_w, panel_h,
               "D. CPI", "cpi_ratio", "delta_cpi", "cpi", 0.008,
               "label: Adapted - Native")

    body.append(rect(width - 242, height - 34, 18, 11, NATIVE))
    body.append(text(width - 218, height - 25, "Native", size=11, anchor="start"))
    body.append(rect(width - 144, height - 34, 18, 11, ADAPTED))
    body.append(text(width - 120, height - 25, "Adapted", size=11, anchor="start"))

    geomean = math.prod(row["cycles_ratio"] for row in rows) ** (1.0 / len(rows))
    body.append(text(left, height - 24, f"cycles/call geomean delta = {(geomean - 1.0) * 100.0:+.2f}%", size=11, anchor="start", fill=MUTED))

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
