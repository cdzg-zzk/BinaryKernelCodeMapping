#!/usr/bin/env python3
"""Generate a 4-panel raw-value preview figure for selected microbenchmarks.

Each panel shows Native and Adapted bars using the raw metric values.  The
Adapted bar is annotated with the Adapted-vs-Native delta.
"""

from __future__ import annotations

import csv
import html
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE / "microbench_data.csv"
OUT = HERE / "microbench_4panel_raw_preview.svg"

SELECTED = [
    "sha256_transform",
    "crc32_le",
    "strlcat",
    "strlcpy",
    "hex_dump_to_buffer",
]

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
    rows = {}
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
            rows[row["function"]] = row
    return [rows[name] for name in SELECTED]


def ymap(value, ymin, ymax, top, height):
    return top + (ymax - value) / (ymax - ymin) * height


def nice_ticks(ymax, count=4):
    if ymax <= 0:
        return [0]
    step = ymax / (count - 1)
    return [i * step for i in range(count)]


def fmt_value(value, kind):
    if kind in {"cycles", "instr", "branches"}:
        if value >= 1000:
            return f"{value:.0f}"
        return f"{value:.1f}"
    return f"{value:.3f}"


def fmt_delta(value, kind):
    if kind == "cycles":
        return f"{value:+.2f}%"
    if kind in {"instr", "branches"}:
        return f"{value:+.1f}"
    return f"{value:+.3f}"


def draw_panel(body, rows, x, y, w, h, title, native_key, micro_key, delta_key, kind, unit):
    body.append(text(x, y - 16, title, size=15, anchor="start", weight="700"))
    body.append(text(x + w, y - 16, unit, size=10, anchor="end", fill=MUTED))
    body.append(line(x, y + h, x + w, y + h, AXIS, 1.1))
    body.append(line(x, y, x, y + h, AXIS, 1.1))

    max_value = max(max(row[native_key], row[micro_key]) for row in rows)
    ymax = max_value * 1.18
    if kind == "cpi":
        ymax = max_value * 1.25

    for tick in nice_ticks(ymax, 4):
        yy = ymap(tick, 0, ymax, y, h)
        body.append(line(x, yy, x + w, yy, GRID, 1.0, "4 4" if tick else ""))
        body.append(text(x - 8, yy + 4, fmt_value(tick, kind), size=10, anchor="end"))

    group_w = w / len(rows)
    bar_w = min(26, group_w * 0.28)
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
        body.append(text(cx + 3 + bar_w / 2, mtop - 6, fmt_delta(delta, kind), size=9, weight="700", fill=color))
        body.append(text(cx, y + h + 38, row["function"], size=10, rotate=-30, anchor="end"))


def main():
    rows = read_rows()
    width, height = 1300, 820
    body = [
        rect(0, 0, width, height, BG),
        text(width / 2, 28, "Microbenchmark Preview: Raw Native vs Adapted Metrics", size=19, weight="700"),
        text(width / 2, 50, "Selected functions; Adapted bars are annotated with delta vs Native", size=12, fill=MUTED),
    ]

    left, top = 92, 96
    panel_w, panel_h = 500, 210
    gap_x, gap_y = 120, 128

    draw_panel(body, rows, left, top, panel_w, panel_h,
               "A. cycles/call", "native_cycles", "micro_cycles", "delta_cycles_pct", "cycles", "raw cycles/call")
    draw_panel(body, rows, left + panel_w + gap_x, top, panel_w, panel_h,
               "B. instructions/call", "native_instr", "micro_instr", "delta_instr", "instr", "raw instructions/call")
    draw_panel(body, rows, left, top + panel_h + gap_y, panel_w, panel_h,
               "C. branches/call", "native_branches", "micro_branches", "delta_branches", "branches", "raw branches/call")
    draw_panel(body, rows, left + panel_w + gap_x, top + panel_h + gap_y, panel_w, panel_h,
               "D. CPI", "native_cpi", "micro_cpi", "delta_cpi", "cpi", "raw CPI")

    body.append(rect(width - 228, height - 32, 18, 11, NATIVE))
    body.append(text(width - 204, height - 23, "Native", size=11, anchor="start"))
    body.append(rect(width - 132, height - 32, 18, 11, ADAPTED))
    body.append(text(width - 108, height - 23, "Adapted", size=11, anchor="start"))

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
