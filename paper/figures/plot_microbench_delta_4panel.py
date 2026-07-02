#!/usr/bin/env python3
"""Generate one SVG containing four delta bar-chart panels."""

from __future__ import annotations

import csv
import html
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE / "microbench_data.csv"
OUT = HERE / "microbench_delta_4panel.svg"

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


def draw_panel(body, rows, x, y, w, h, value_key, kind, title, ylabel, ymin, ymax):
    body.append(text(x, y - 16, title, size=15, anchor="start", weight="700"))

    for tick in nice_ticks(ymin, ymax):
        yy = ymap(tick, ymin, ymax, y, h)
        body.append(line(x, yy, x + w, yy, GRID, 1.0, "4 4" if abs(tick) > 1e-12 else ""))
        body.append(text(x - 8, yy + 4, fmt_axis(tick, kind), size=9.5, anchor="end"))

    zero_y = ymap(0, ymin, ymax, y, h)
    body.append(line(x, zero_y, x + w, zero_y, "#2a7fb8", 1.4))
    body.append(line(x, y, x, y + h, AXIS, 1.1))
    body.append(line(x, y + h, x + w, y + h, AXIS, 1.1))
    body.append(text(x - 58, y + h / 2, ylabel, size=11, rotate=-90))

    group_w = w / len(rows)
    bar_w = min(48, group_w * 0.60)
    for i, row in enumerate(rows):
        value = row[value_key]
        cx = x + group_w * (i + 0.5)
        yy = ymap(value, ymin, ymax, y, h)
        by = min(yy, zero_y)
        bh = max(1.0, abs(zero_y - yy))
        body.append(rect(cx - bar_w / 2, by, bar_w, bh, BAR))
        label_y = by - 6 if value >= 0 else by + bh + 13
        label_y = min(max(label_y, y + 10), y + h - 5)
        body.append(text(cx, label_y, fmt_label(value, kind), size=9.5, fill=TEXT))
        body.append(text(cx, y + h + 40, row["label"], size=10, rotate=-32, anchor="end"))


def main():
    rows = read_rows()
    width, height = 1500, 900
    body = [
        rect(0, 0, width, height, BG),
        text(width / 2, 30, "Steady-state Microbenchmark Deltas", size=19, weight="700"),
        text(width / 2, 54, "All bars report Adapted - Native; cycles/call is shown as percent delta", size=12, fill=MUTED),
    ]

    left, top = 112, 104
    panel_w, panel_h = 560, 235
    gap_x, gap_y = 152, 146

    draw_panel(
        body,
        rows,
        left,
        top,
        panel_w,
        panel_h,
        "delta_cycles_pct",
        "cycles",
        "A. Steady-state overhead",
        "Delta cycles/call (%)",
        -1.8,
        1.4,
    )
    draw_panel(
        body,
        rows,
        left + panel_w + gap_x,
        top,
        panel_w,
        panel_h,
        "delta_instr",
        "instr",
        "B. Retired instructions",
        "Delta instructions/call",
        -4,
        22,
    )
    draw_panel(
        body,
        rows,
        left,
        top + panel_h + gap_y,
        panel_w,
        panel_h,
        "delta_branches",
        "branches",
        "C. Retired branches",
        "Delta branches/call",
        -1.2,
        0.2,
    )
    draw_panel(
        body,
        rows,
        left + panel_w + gap_x,
        top + panel_h + gap_y,
        panel_w,
        panel_h,
        "delta_cpi",
        "cpi",
        "D. CPI",
        "Delta CPI",
        -0.009,
        0.009,
    )

    body.append(text(width / 2, height - 18, "Function", size=12))

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
