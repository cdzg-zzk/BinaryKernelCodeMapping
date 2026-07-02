#!/usr/bin/env python3
"""Generate SVG figures for the steady-state microbenchmark section.

The script intentionally uses only the Python standard library so the paper
figures remain reproducible on the benchmark host without installing plotting
packages.
"""

from __future__ import annotations

import csv
import html
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE / "microbench_data.csv"

NATIVE = "#7b8494"
FAST = "#2f6db5"
SLOW = "#c85f2d"
GRID = "#d9dee7"
AXIS = "#2d3748"
TEXT = "#1f2933"
BG = "#ffffff"


def fmt_delta(pct: float) -> str:
    return f"{pct:+.2f}%"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def read_rows() -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    with DATA.open(newline="") as f:
        for raw in csv.DictReader(f):
            row: dict[str, float | str] = {"function": raw["function"]}
            for key, value in raw.items():
                if key in {"function", "result_dir"}:
                    row[key] = value
                else:
                    row[key] = float(value)
            row["ratio"] = row["micro_cycles"] / row["native_cycles"]  # type: ignore[operator]
            row["delta_cycles_pct"] = (row["ratio"] - 1.0) * 100.0  # type: ignore[operator]
            row["delta_instr"] = row["micro_instr"] - row["native_instr"]  # type: ignore[operator]
            row["delta_branches"] = row["micro_branches"] - row["native_branches"]  # type: ignore[operator]
            row["delta_cpi"] = row["micro_cpi"] - row["native_cpi"]  # type: ignore[operator]
            rows.append(row)
    return rows


def text(
    x: float,
    y: float,
    value: object,
    size: int = 13,
    anchor: str = "middle",
    weight: str = "400",
    rotate: float | None = None,
    fill: str = TEXT,
) -> str:
    transform = f' transform="rotate({rotate:.1f} {x:.1f} {y:.1f})"' if rotate is not None else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}"{transform}>{esc(value)}</text>'
    )


def line(x1: float, y1: float, x2: float, y2: float, stroke: str = AXIS, width: float = 1.0, dash: str = "") -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width:.1f}"{dash_attr}/>'
    )


def rect(x: float, y: float, w: float, h: float, fill: str, stroke: str = "none") -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" stroke="{stroke}"/>'
    )


def svg(width: int, height: int, body: list[str]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            rect(0, 0, width, height, BG),
            *body,
            "</svg>",
            "",
        ]
    )


def draw_normalized(rows: list[dict[str, float | str]]) -> str:
    width, height = 1240, 560
    left, right, top, bottom = 92, 40, 58, 145
    plot_w = width - left - right
    plot_h = height - top - bottom
    y_min, y_max = 0.96, 1.02

    def y(value: float) -> float:
        return top + (y_max - value) / (y_max - y_min) * plot_h

    body: list[str] = []
    body.append(text(width / 2, 28, "Normalized steady-state performance", size=18, weight="700"))
    body.append(text(width / 2, 50, "Lower is better; y-axis is centered around native = 1.0", size=12, fill="#536171"))

    for tick in [0.96, 0.98, 1.00, 1.02]:
        yy = y(tick)
        body.append(line(left, yy, width - right, yy, GRID, 1.0, "4 4" if tick != 1.0 else ""))
        body.append(text(left - 12, yy + 4, f"{tick:.2f}", size=12, anchor="end"))

    body.append(line(left, top, left, top + plot_h, AXIS, 1.2))
    body.append(line(left, top + plot_h, width - right, top + plot_h, AXIS, 1.2))
    body.append(text(22, top + plot_h / 2, "Normalized cycles/call", size=13, rotate=-90))

    group_w = plot_w / len(rows)
    bar_w = 22
    base = y(y_min)
    for i, row in enumerate(rows):
        cx = left + group_w * (i + 0.5)
        native_x = cx - bar_w - 3
        micro_x = cx + 3
        native_top = y(1.0)
        ratio = float(row["ratio"])
        micro_top = y(ratio)
        delta = float(row["delta_cycles_pct"])
        micro_color = SLOW if delta > 0 else FAST

        body.append(rect(native_x, native_top, bar_w, base - native_top, NATIVE))
        body.append(rect(micro_x, micro_top, bar_w, base - micro_top, micro_color))
        label_y = micro_top - 8 if delta >= 0 else micro_top + 18
        body.append(text(micro_x + bar_w / 2, label_y, fmt_delta(delta), size=11, fill=micro_color, weight="700"))
        body.append(text(cx, height - 78, row["function"], size=12, rotate=-35, anchor="end"))

    legend_y = height - 24
    body.append(rect(width - 288, legend_y - 12, 18, 12, NATIVE))
    body.append(text(width - 264, legend_y - 2, "native", size=12, anchor="start"))
    body.append(rect(width - 210, legend_y - 12, 18, 12, FAST))
    body.append(text(width - 186, legend_y - 2, "micro faster/equal", size=12, anchor="start"))
    body.append(rect(width - 88, legend_y - 12, 18, 12, SLOW))
    body.append(text(width - 64, legend_y - 2, "micro slower", size=12, anchor="start"))
    return svg(width, height, body)


def nice_ticks(y_min: float, y_max: float, count: int = 5) -> list[float]:
    if y_min == y_max:
        return [y_min]
    step = (y_max - y_min) / (count - 1)
    return [y_min + i * step for i in range(count)]


def draw_pmu(rows: list[dict[str, float | str]]) -> str:
    width, height = 1280, 720
    left, right = 92, 42
    top = 54
    panel_h = 150
    gap = 52
    bottom = 110
    plot_w = width - left - right
    panels = [
        ("Delta instructions/call", "delta_instr", -4.0, 22.0, "{:.0f}"),
        ("Delta branches/call", "delta_branches", -1.2, 0.3, "{:.1f}"),
        ("Delta CPI", "delta_cpi", -0.009, 0.009, "{:.3f}"),
    ]

    body: list[str] = []
    body.append(text(width / 2, 28, "PMU explanation of performance deltas", size=18, weight="700"))
    body.append(text(width / 2, 50, "micro - native; positive bars add work or CPI, negative bars remove them", size=12, fill="#536171"))

    group_w = plot_w / len(rows)
    bar_w = min(46, group_w * 0.54)

    for pidx, (title, key, y_min, y_max, tick_fmt) in enumerate(panels):
        ptop = top + pidx * (panel_h + gap)
        pbottom = ptop + panel_h

        def y(value: float) -> float:
            return ptop + (y_max - value) / (y_max - y_min) * panel_h

        body.append(text(left, ptop - 11, title, size=14, anchor="start", weight="700"))
        for tick in nice_ticks(y_min, y_max, 4):
            yy = y(tick)
            body.append(line(left, yy, width - right, yy, GRID, 1.0, "4 4"))
            body.append(text(left - 10, yy + 4, tick_fmt.format(tick), size=11, anchor="end"))
        zero_y = y(0.0)
        body.append(line(left, zero_y, width - right, zero_y, AXIS, 1.3))
        body.append(line(left, ptop, left, pbottom, AXIS, 1.1))

        for i, row in enumerate(rows):
            value = float(row[key])
            cx = left + group_w * (i + 0.5)
            yy = y(value)
            bar_y = min(yy, zero_y)
            bar_h = max(1.2, abs(zero_y - yy))
            color = SLOW if value > 0 else FAST
            body.append(rect(cx - bar_w / 2, bar_y, bar_w, bar_h, color))

            if abs(value) >= {"delta_instr": 4.0, "delta_branches": 0.2, "delta_cpi": 0.004}[key]:
                label = tick_fmt.format(value)
                ly = bar_y - 5 if value > 0 else bar_y + bar_h + 13
                body.append(text(cx, ly, label, size=10, fill=color, weight="700"))

    for i, row in enumerate(rows):
        cx = left + group_w * (i + 0.5)
        body.append(text(cx, height - 46, row["function"], size=12, rotate=-35, anchor="end"))

    legend_y = height - 18
    body.append(rect(width - 272, legend_y - 12, 18, 12, SLOW))
    body.append(text(width - 248, legend_y - 2, "positive delta", size=12, anchor="start"))
    body.append(rect(width - 142, legend_y - 12, 18, 12, FAST))
    body.append(text(width - 118, legend_y - 2, "negative delta", size=12, anchor="start"))
    return svg(width, height, body)


def main() -> None:
    rows = read_rows()
    # Preserve the paper order in the CSV, but check the intended delta ordering.
    deltas = [float(r["delta_cycles_pct"]) for r in rows]
    if deltas != sorted(deltas):
        raise SystemExit("microbench_data.csv must be sorted by delta_cycles_pct")

    geomean_ratio = math.prod(float(r["ratio"]) for r in rows) ** (1.0 / len(rows))
    arithmetic_mean = sum(float(r["delta_cycles_pct"]) for r in rows) / len(rows)
    print(f"geomean_delta={((geomean_ratio - 1.0) * 100.0):+.4f}%")
    print(f"mean_delta={arithmetic_mean:+.4f}%")

    (HERE / "microbench_normalized_cycles.svg").write_text(draw_normalized(rows), encoding="utf-8")
    (HERE / "microbench_pmu_deltas.svg").write_text(draw_pmu(rows), encoding="utf-8")


if __name__ == "__main__":
    main()
