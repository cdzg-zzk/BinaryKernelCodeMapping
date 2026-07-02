#!/usr/bin/env python3
"""Generate a 4-panel preview figure for selected microbenchmarks.

Panels:
  A. normalized cycles/call, Native vs Adapted, Adapted annotated with delta
  B. delta instructions/call
  C. delta branches/call
  D. delta CPI

This is intentionally a preview figure and uses a subset of functions.
"""

from __future__ import annotations

import csv
import html
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE / "microbench_data.csv"
OUT = HERE / "microbench_4panel_preview.svg"

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
            row["ratio"] = row["micro_cycles"] / row["native_cycles"]
            row["delta_pct"] = (row["ratio"] - 1.0) * 100.0
            row["delta_instr"] = row["micro_instr"] - row["native_instr"]
            row["delta_branches"] = row["micro_branches"] - row["native_branches"]
            row["delta_cpi"] = row["micro_cpi"] - row["native_cpi"]
            rows[row["function"]] = row
    return [rows[name] for name in SELECTED]


def ymap(value, ymin, ymax, top, height):
    return top + (ymax - value) / (ymax - ymin) * height


def draw_panel_frame(body, title, x, y, w, h, ylabel=None):
    body.append(text(x, y - 16, title, size=15, anchor="start", weight="700"))
    body.append(line(x, y + h, x + w, y + h, AXIS, 1.1))
    body.append(line(x, y, x, y + h, AXIS, 1.1))
    if ylabel:
        body.append(text(x - 54, y + h / 2, ylabel, size=12, rotate=-90))


def draw_cycles_panel(body, rows, x, y, w, h):
    ymin, ymax = 0.96, 1.02
    draw_panel_frame(body, "A. Normalized cycles/call", x, y, w, h, "Native = 1.0")
    for tick in [0.96, 0.98, 1.00, 1.02]:
        yy = ymap(tick, ymin, ymax, y, h)
        body.append(line(x, yy, x + w, yy, GRID, 1.0, "4 4" if tick != 1.0 else ""))
        body.append(text(x - 8, yy + 4, f"{tick:.2f}", size=10, anchor="end"))
    group_w = w / len(rows)
    bar_w = 20
    base = ymap(ymin, ymin, ymax, y, h)
    for i, row in enumerate(rows):
        cx = x + group_w * (i + 0.5)
        native_top = ymap(1.0, ymin, ymax, y, h)
        adapted_top = ymap(row["ratio"], ymin, ymax, y, h)
        body.append(rect(cx - 23, native_top, bar_w, base - native_top, NATIVE))
        body.append(rect(cx + 3, adapted_top, bar_w, base - adapted_top, ADAPTED if row["delta_pct"] <= 0 else POS))
        label_y = adapted_top - 7 if row["delta_pct"] > 0 else adapted_top + 17
        body.append(text(cx + 13, label_y, f'{row["delta_pct"]:+.2f}%', size=10, weight="700", fill=POS if row["delta_pct"] > 0 else NEG))
        body.append(text(cx, y + h + 38, row["function"], size=10, rotate=-30, anchor="end"))
    body.append(rect(x + w - 168, y - 28, 14, 9, NATIVE))
    body.append(text(x + w - 148, y - 20, "Native", size=10, anchor="start"))
    body.append(rect(x + w - 100, y - 28, 14, 9, ADAPTED))
    body.append(text(x + w - 80, y - 20, "Adapted", size=10, anchor="start"))


def draw_delta_panel(body, rows, x, y, w, h, title, key, ymin, ymax, fmt, threshold=None):
    draw_panel_frame(body, title, x, y, w, h)
    for tick in [ymin, (ymin + ymax) / 2, ymax]:
        yy = ymap(tick, ymin, ymax, y, h)
        body.append(line(x, yy, x + w, yy, GRID, 1.0, "4 4"))
        body.append(text(x - 8, yy + 4, fmt.format(tick), size=10, anchor="end"))
    zero_y = ymap(0, ymin, ymax, y, h)
    body.append(line(x, zero_y, x + w, zero_y, AXIS, 1.3))
    group_w = w / len(rows)
    bar_w = min(34, group_w * 0.52)
    for i, row in enumerate(rows):
        value = row[key]
        cx = x + group_w * (i + 0.5)
        yy = ymap(value, ymin, ymax, y, h)
        by = min(yy, zero_y)
        bh = max(1.1, abs(zero_y - yy))
        color = POS if value > 0 else NEG
        body.append(rect(cx - bar_w / 2, by, bar_w, bh, color))
        if threshold is None or abs(value) >= threshold:
            ly = by - 5 if value > 0 else by + bh + 13
            body.append(text(cx, ly, fmt.format(value), size=9, fill=color, weight="700"))
        body.append(text(cx, y + h + 38, row["function"], size=10, rotate=-30, anchor="end"))


def main():
    rows = read_rows()
    width, height = 1300, 820
    body = [
        rect(0, 0, width, height, BG),
        text(width / 2, 28, "Microbenchmark Preview: Performance and PMU Deltas", size=19, weight="700"),
        text(width / 2, 50, "Selected functions; PMU panels show Adapted - Native", size=12, fill=MUTED),
    ]

    left, top = 92, 96
    panel_w, panel_h = 500, 210
    gap_x, gap_y = 120, 128

    draw_cycles_panel(body, rows, left, top, panel_w, panel_h)
    draw_delta_panel(body, rows, left + panel_w + gap_x, top, panel_w, panel_h,
                     "B. Delta instructions/call", "delta_instr", -4, 22, "{:+.0f}", threshold=3.5)
    draw_delta_panel(body, rows, left, top + panel_h + gap_y, panel_w, panel_h,
                     "C. Delta branches/call", "delta_branches", -1.2, 0.3, "{:+.1f}", threshold=0.15)
    draw_delta_panel(body, rows, left + panel_w + gap_x, top + panel_h + gap_y, panel_w, panel_h,
                     "D. Delta CPI", "delta_cpi", -0.009, 0.003, "{:+.3f}", threshold=0.002)

    body.append(rect(width - 246, height - 32, 18, 11, POS))
    body.append(text(width - 222, height - 23, "positive delta", size=11, anchor="start"))
    body.append(rect(width - 120, height - 32, 18, 11, NEG))
    body.append(text(width - 96, height - 23, "negative delta", size=11, anchor="start"))

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
