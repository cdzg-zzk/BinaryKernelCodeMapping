#!/usr/bin/env python3
"""Generate four separate delta bar charts for microbenchmarks.

Outputs:
  microbench_delta_cycles.svg
  microbench_delta_instructions.svg
  microbench_delta_branches.svg
  microbench_delta_cpi.svg

Each chart shows Adapted - Native, except cycles/call which is shown as percent
delta relative to Native.
"""

from __future__ import annotations

import csv
import html
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE / "microbench_data.csv"

TEXT = "#1f2933"
MUTED = "#607083"
GRID = "#d9dee7"
AXIS = "#2d3748"
BAR = "#2a7fb8"
BG = "#ffffff"

LABELS = {
    "sha256_transform": "sha256",
    "crc32_le": "crc32",
    "errname": "errname",
    "strscpy_pad": "strscpy",
    "string_get_size": "size",
    "strlcat": "strlcat",
    "strlcpy": "strlcpy",
    "hex_dump_to_buffer": "hex_dump",
}


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
            row = {"function": raw["function"], "label": LABELS[raw["function"]]}
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


def fmt_label(value, kind):
    if kind == "cycles":
        return f"{value:+.2f}%"
    if kind == "instr":
        return f"{value:+.1f}"
    if kind == "branches":
        if abs(value) < 0.0005:
            return "+0"
        if abs(value) < 0.01:
            return f"{value:+.3f}"
        if abs(value) < 0.1:
            return f"{value:+.2f}"
        return f"{value:+.1f}"
    return f"{value:+.3f}"


def fmt_axis(value, kind):
    if kind == "cpi":
        return f"{value:.3f}"
    if kind == "branches":
        return f"{value:.1f}"
    if kind == "cycles":
        return f"{value:.1f}"
    return f"{value:.0f}"


def nice_ticks(ymin, ymax, count=5):
    step = (ymax - ymin) / (count - 1)
    return [ymin + i * step for i in range(count)]


def draw_chart(rows, value_key, kind, title, ylabel, outfile, ymin=None, ymax=None):
    values = [row[value_key] for row in rows]
    if ymin is None:
        ymin = min(values)
    if ymax is None:
        ymax = max(values)
    pad = max((ymax - ymin) * 0.12, 0.01)
    ymin = min(ymin - pad, 0)
    ymax = max(ymax + pad, 0)

    width, height = 1060, 430
    left, right, top, bottom = 82, 30, 52, 96
    plot_w = width - left - right
    plot_h = height - top - bottom

    body = [
        rect(0, 0, width, height, BG),
        text(width / 2, 26, title, size=17, weight="700"),
    ]

    for tick in nice_ticks(ymin, ymax):
        yy = ymap(tick, ymin, ymax, top, plot_h)
        body.append(line(left, yy, width - right, yy, GRID, 1.0, "4 4" if abs(tick) > 1e-12 else ""))
        body.append(text(left - 10, yy + 4, fmt_axis(tick, kind), size=11, anchor="end"))

    zero_y = ymap(0, ymin, ymax, top, plot_h)
    body.append(line(left, zero_y, width - right, zero_y, "#2a7fb8", 1.4))
    body.append(line(left, top, left, top + plot_h, AXIS, 1.1))
    body.append(line(left, top + plot_h, width - right, top + plot_h, AXIS, 1.1))
    body.append(text(24, top + plot_h / 2, ylabel, size=12, rotate=-90))
    body.append(text(width / 2, height - 16, "Function", size=12))

    group_w = plot_w / len(rows)
    bar_w = min(58, group_w * 0.62)
    for i, row in enumerate(rows):
        value = row[value_key]
        cx = left + group_w * (i + 0.5)
        yy = ymap(value, ymin, ymax, top, plot_h)
        by = min(yy, zero_y)
        bh = max(1.0, abs(zero_y - yy))
        body.append(rect(cx - bar_w / 2, by, bar_w, bh, BAR))
        label_y = by - 7 if value >= 0 else by + bh + 14
        label_y = min(max(label_y, top + 10), top + plot_h - 5)
        body.append(text(cx, label_y, fmt_label(value, kind), size=10, fill=TEXT))
        body.append(text(cx, height - 54, row["label"], size=11, rotate=-33, anchor="end"))

    svg = "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        *body,
        "</svg>",
        "",
    ])
    (HERE / outfile).write_text(svg, encoding="utf-8")
    print(HERE / outfile)


def main():
    rows = read_rows()
    draw_chart(
        rows,
        "delta_cycles_pct",
        "cycles",
        "Steady-state overhead relative to Native",
        "Delta cycles/call (%)",
        "microbench_delta_cycles.svg",
        ymin=-1.8,
        ymax=1.4,
    )
    draw_chart(
        rows,
        "delta_instr",
        "instr",
        "PMU delta: retired instructions",
        "Delta retired instructions/call",
        "microbench_delta_instructions.svg",
        ymin=-4,
        ymax=22,
    )
    draw_chart(
        rows,
        "delta_branches",
        "branches",
        "PMU delta: retired branches",
        "Delta retired branches/call",
        "microbench_delta_branches.svg",
        ymin=-1.2,
        ymax=0.2,
    )
    draw_chart(
        rows,
        "delta_cpi",
        "cpi",
        "PMU delta: CPI",
        "Delta CPI",
        "microbench_delta_cpi.svg",
        ymin=-0.009,
        ymax=0.009,
    )


if __name__ == "__main__":
    main()
