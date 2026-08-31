#!/usr/bin/env python3
"""Generate paper figures directly from the checked evaluation artifacts.

The script deliberately uses only the Python standard library so that the SVG
figures remain reproducible on the evaluation machine.  All plotted values are
read from the final CSV artifacts except the clocktime aggregates, which are
transcribed from VKSO_READ_UPDATE性能报告_20260801.md and checked below.
"""

from __future__ import annotations

import csv
import html
import math
import re
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

BLUE = "#3568A8"
ORANGE = "#D97732"
TEAL = "#16877A"
PURPLE = "#7656A5"
RED = "#C84B4B"
GRAY = "#687386"
DARK = "#202938"
GRID = "#D9DEE7"
LIGHT = "#F4F6F9"
WHITE = "#FFFFFF"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def quantile(values: list[float], q: float) -> float:
    values = sorted(values)
    if not values:
        raise ValueError("quantile of empty input")
    pos = (len(values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] * (hi - pos) + values[hi] * (pos - lo)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class Svg:
    def __init__(self, width: int, height: int, title: str):
        self.width = width
        self.height = height
        self.title = title
        self.items: list[str] = []

    def rect(self, x, y, w, h, fill=WHITE, stroke="none", sw=1, rx=0, opacity=1):
        self.items.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'rx="{rx:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'opacity="{opacity}"/>'
        )

    def line(self, x1, y1, x2, y2, stroke=DARK, sw=1, dash=None, opacity=1, marker=None):
        attrs = ""
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        if marker:
            attrs += f' marker-end="url(#{marker})"'
        self.items.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"{attrs}/>'
        )

    def polyline(self, points, stroke, sw=2.2, fill="none"):
        coords = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        self.items.append(
            f'<polyline points="{coords}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>'
        )

    def circle(self, x, y, r, fill, stroke=WHITE, sw=1.2):
        self.items.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def text(self, x, y, value, size=12, anchor="middle", weight=400,
             fill=DARK, rotate=None, style=""):
        transform = "" if rotate is None else f' transform="rotate({rotate} {x:.2f} {y:.2f})"'
        self.items.append(
            f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}"{transform} '
            f'style="{style}">{esc(value)}</text>'
        )

    def errorbar(self, x, ylo, yhi, color, cap=5, sw=1.4):
        self.line(x, ylo, x, yhi, color, sw)
        self.line(x - cap, ylo, x + cap, ylo, color, sw)
        self.line(x - cap, yhi, x + cap, yhi, color, sw)

    def save(self, path: Path):
        body = "\n  ".join(self.items)
        content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}"
     viewBox="0 0 {self.width} {self.height}" role="img" aria-labelledby="title desc">
  <title id="title">{esc(self.title)}</title>
  <desc id="desc">Vector figure generated from the checked experiment artifacts.</desc>
  <defs>
    <marker id="arrow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">
      <polygon points="0 0, 9 3.5, 0 7" fill="{GRAY}"/>
    </marker>
    <style>
      text {{ font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif; }}
    </style>
  </defs>
  <rect width="100%" height="100%" fill="white"/>
  {body}
</svg>
'''
        path.write_text(content, encoding="utf-8")


def panel_title(svg: Svg, x: float, y: float, label: str, title: str):
    svg.text(x, y, label, 13, "start", 700, DARK)
    svg.text(x + (34 if label else 0), y, title, 13, "start", 600, DARK)


def linear_axis(svg: Svg, x: float, y: float, w: float, h: float,
                ymin: float, ymax: float, ticks: list[float], ylabel: str = ""):
    def sy(value: float) -> float:
        return y + h - (value - ymin) / (ymax - ymin) * h

    for tick in ticks:
        yy = sy(tick)
        svg.line(x, yy, x + w, yy, GRID, 0.8)
        svg.text(x - 8, yy + 4, f"{tick:g}", 10, "end", fill=GRAY)
    svg.line(x, y, x, y + h, DARK, 1)
    svg.line(x, y + h, x + w, y + h, DARK, 1)
    if ymin < 0 < ymax:
        svg.line(x, sy(0), x + w, sy(0), GRAY, 1.1)
    if ylabel:
        svg.text(x - 48, y + h / 2, ylabel, 11, rotate=-90, fill=GRAY)
    return sy


def legend(svg: Svg, x: float, y: float, entries, columns=1, col_width=150):
    for i, (label, color, shape) in enumerate(entries):
        col = i % columns
        row = i // columns
        xx = x + col * col_width
        yy = y + row * 20
        if shape == "line":
            svg.line(xx, yy - 4, xx + 20, yy - 4, color, 2.5)
            svg.circle(xx + 10, yy - 4, 3.2, color)
        else:
            svg.rect(xx, yy - 12, 14, 10, color, color, 0)
        svg.text(xx + 22, yy - 3, label, 10.5, "start", fill=DARK)


def architecture_figure():
    svg = Svg(1180, 600, "Constructing and rehosting a resident binary closure")
    svg.text(590, 31, "Constructing and Rehosting a Resident Binary Closure", 20, weight=700)
    svg.text(590, 53, "The contract defines what must hold; environment separation expands what can satisfy it", 11.5, fill=GRAY)

    # Challenge 1: the contract and environment separation jointly define the reuse boundary.
    svg.rect(55, 78, 1070, 292, WHITE, GRID, 1.2, 10)
    svg.text(76, 105, "Challenge 1 · Construct a rehostable binary closure", 13, "start", 700)

    svg.rect(85, 146, 210, 84, LIGHT, BLUE, 1.5, 8)
    svg.text(190, 176, "Candidate dependencies", 12.3, weight=700)
    svg.text(190, 201, "code · data · control targets", 9.8, fill=GRAY)

    svg.rect(405, 126, 370, 124, WHITE, PURPLE, 1.8, 9)
    svg.text(590, 155, "Reuse contract", 13.5, weight=700)
    svg.text(590, 182, "state · control · code-shape properties", 10.5, fill=GRAY)
    svg.text(590, 209, "defines a valid cross-domain closure", 10.5, fill=GRAY)
    svg.text(590, 232, "not a whitelist of naturally pure functions", 9.5, fill=GRAY)

    svg.rect(885, 146, 190, 84, LIGHT, TEAL, 1.5, 8)
    svg.text(980, 176, "Rehostable closure", 12.3, weight=700)
    svg.text(980, 199, "resident code/rodata", 9.7, fill=GRAY)
    svg.text(980, 217, "+ explicit environment contract", 9.3, fill=GRAY)

    svg.line(295, 188, 395, 188, GRAY, 1.6, marker="arrow")
    svg.line(775, 188, 875, 188, GRAY, 1.6, marker="arrow")

    svg.rect(405, 282, 370, 62, LIGHT, ORANGE, 1.3, 7)
    svg.text(590, 307, "Environment separation", 11.5, weight=700)
    svg.text(590, 329, "PIC-compatible shape · Shim contracts · published inputs", 9.6, fill=GRAY)
    svg.line(590, 282, 590, 260, GRAY, 1.3, marker="arrow")

    svg.text(190, 291, "Outside the reuse boundary", 10.8, weight=600, fill=RED)
    svg.text(190, 314, "privileged or semantically incompatible dependencies", 9.2, fill=GRAY)
    svg.text(980, 291, "Key invariant", 10.8, weight=600, fill=TEAL)
    svg.text(980, 314, "same computation, explicit domain boundary", 9.2, fill=GRAY)

    # Challenge 2: turn the rehostable closure into an ordinary application object.
    svg.rect(55, 398, 1070, 166, WHITE, GRID, 1.2, 10)
    svg.text(76, 425, "Challenge 2 · Rehost the closure as a standard user object", 13, "start", 700)
    runtime = [
        (85,  "Rehostable closure", "shared execution body + contract", PURPLE, 235),
        (375, "Standard carrier", "symbols · ABI · virtual layout", BLUE, 210),
        (640, "Page grafting", "logical pages → resident physical pages", TEAL, 220),
        (915, "Ordinary user call", "standard loader + first touch", ORANGE, 180),
    ]
    for x, title, subtitle, color, width in runtime:
        svg.rect(x, 458, width, 72, LIGHT, color, 1.5, 8)
        svg.text(x + width / 2, 485, title, 12.1, weight=700)
        svg.text(x + width / 2, 508, subtitle, 9.5, fill=GRAY)
    svg.line(320, 494, 365, 494, GRAY, 1.5, marker="arrow")
    svg.line(585, 494, 630, 494, GRAY, 1.5, marker="arrow")
    svg.line(860, 494, 905, 494, GRAY, 1.5, marker="arrow")
    svg.text(590, 548, "same physical execution body · ordinary shared-library call · no per-call mediation", 10.4, fill=GRAY)
    svg.save(OUT / "system_architecture.svg")


def page_grafting_figure():
    svg = Svg(1120, 480, "Fault-driven page grafting over a standard file-backed mapping")
    svg.text(560, 32, "Fault-driven Resident-page Grafting", 19, weight=700)
    svg.text(560, 53, "The loader-visible object remains ordinary; only selected backing entries change", 11.5, fill=GRAY)

    panel_title(svg, 55, 88, "(a)", "Resident kernel object")
    svg.rect(55, 110, 260, 100, LIGHT, BLUE, 1.5, 8)
    svg.text(185, 140, "Kernel/LKM virtual mapping", 12.5, weight=700)
    svg.text(185, 165, "RX / RO; already resident", 10.2, fill=GRAY)
    svg.text(185, 187, "module + page references held", 10.2, fill=GRAY)

    panel_title(svg, 395, 88, "(b)", "File-object backing")
    svg.rect(395, 110, 300, 100, WHITE, PURPLE, 1.5, 8)
    svg.text(545, 138, "Stub DSO logical slot", 12.5, weight=700)
    svg.text(545, 161, "file offset → pgoff", 10.2, fill=GRAY)
    svg.text(545, 184, "manifest: source · permissions · class", 10.2, fill=GRAY)

    panel_title(svg, 775, 88, "(c)", "Ordinary process view")
    svg.rect(775, 110, 290, 100, LIGHT, ORANGE, 1.5, 8)
    svg.text(920, 140, "ld.so file-backed VMA", 12.5, weight=700)
    svg.text(920, 165, "symbols and virtual layout unchanged", 10.2, fill=GRAY)
    svg.text(920, 187, "no eager PTE population", 10.2, fill=GRAY)

    svg.rect(365, 260, 360, 88, WHITE, PURPLE, 1.7, 8)
    svg.text(545, 289, "address_space[pgoff]", 13, weight=700)
    svg.text(545, 313, "grafting manager installs resident page reference", 10.5, fill=GRAY)
    svg.line(545, 210, 545, 250, GRAY, 1.5, marker="arrow")

    svg.rect(75, 274, 220, 62, WHITE, BLUE, 1.7, 7)
    svg.text(185, 300, "Resident physical page", 12.5, weight=700)
    svg.text(185, 321, "single PFN", 10.2, fill=GRAY)
    svg.line(315, 160, 355, 160, GRAY, 1.2)
    svg.line(355, 160, 355, 305, GRAY, 1.2)
    svg.line(355, 305, 305, 305, GRAY, 1.2, marker="arrow")
    svg.line(365, 305, 305, 305, PURPLE, 1.5, marker="arrow")

    svg.rect(795, 274, 250, 62, WHITE, ORANGE, 1.7, 7)
    svg.text(920, 299, "User PTE → same PFN", 12.5, weight=700)
    svg.text(920, 321, "installed as RX or R--", 10.2, fill=GRAY)
    svg.line(920, 210, 920, 254, GRAY, 1.3, marker="arrow")
    svg.text(934, 239, "first touch", 9.6, "start", fill=GRAY)
    svg.line(725, 305, 785, 305, GRAY, 1.5, marker="arrow")

    svg.rect(235, 388, 650, 48, LIGHT, GRID, 1, 6)
    svg.text(560, 408, "Steady state: ordinary direct call + existing PTE", 11.5, weight=700)
    svg.text(560, 426, "No syscall, runtime trampoline, symbol lookup, page copy, or writable user alias", 9.8, fill=GRAY)
    svg.save(OUT / "page_grafting.svg")


def binding_adaptation_figure():
    svg = Svg(1120, 470, "Private binding separates environment addresses from shared machine code")
    svg.text(560, 32, "Environment-specific Binding without Patching Shared Text", 19, weight=700)
    svg.text(560, 53, "Pseudo-GOT moves address ownership into domain-local slots", 11.5, fill=GRAY)

    svg.rect(390, 82, 340, 76, LIGHT, BLUE, 1.7, 8)
    svg.text(560, 112, "Shared resident .text / .rodata", 13, weight=700)
    svg.text(560, 136, "PC-relative load from a declared binding slot", 10.5, fill=GRAY)

    svg.line(500, 158, 285, 220, GRAY, 1.5, marker="arrow")
    svg.line(620, 158, 835, 220, GRAY, 1.5, marker="arrow")

    panel_title(svg, 70, 205, "(a)", "Kernel execution domain")
    svg.rect(70, 230, 430, 116, WHITE, BLUE, 1.5, 8)
    svg.rect(95, 260, 165, 56, LIGHT, PURPLE, 1.2, 6)
    svg.text(177.5, 282, ".pseudo-got slot", 11.5, weight=700)
    svg.text(177.5, 301, "module-private", 9.6, fill=GRAY)
    svg.rect(310, 260, 165, 56, LIGHT, BLUE, 1.2, 6)
    svg.text(392.5, 282, "Kernel target", 11.5, weight=700)
    svg.text(392.5, 301, "object or helper", 9.6, fill=GRAY)
    svg.line(260, 288, 300, 288, GRAY, 1.4, marker="arrow")
    svg.text(285, 335, "module loader writes kernel VA", 9.8, fill=GRAY)

    panel_title(svg, 620, 205, "(b)", "User execution domain")
    svg.rect(620, 230, 430, 116, WHITE, ORANGE, 1.5, 8)
    svg.rect(645, 260, 165, 56, LIGHT, PURPLE, 1.2, 6)
    svg.text(727.5, 282, ".pseudo-got slot", 11.5, weight=700)
    svg.text(727.5, 301, "carrier-private", 9.6, fill=GRAY)
    svg.rect(860, 260, 165, 56, LIGHT, ORANGE, 1.2, 6)
    svg.text(942.5, 282, "User target", 11.5, weight=700)
    svg.text(942.5, 301, "private object or shim", 9.6, fill=GRAY)
    svg.line(810, 288, 850, 288, GRAY, 1.4, marker="arrow")
    svg.text(835, 335, "ld.so writes user VA", 9.8, fill=GRAY)

    svg.rect(225, 385, 670, 48, LIGHT, GRID, 1, 6)
    svg.text(560, 405, "Invariant: the shared instruction bytes and read-only pages are identical in both domains", 11.2, weight=700)
    svg.text(560, 423, "Only private slots differ; unresolved or privileged targets fail closed", 9.8, fill=GRAY)
    svg.save(OUT / "binding_adaptation.svg")


def first_touch_figure():
    rows = read_csv(ROOT / "test/test_first_call/matrix_bench/first_touch_pmu_combined.csv")
    data = {(r["Target"], r["Condition"]): float(r["Latency_Median_Cycles"]) for r in rows}
    fault = {(r["Target"], r["Condition"]): (int(float(r["Latency_Minor_Flt"])), int(float(r["Latency_Major_Flt"]))) for r in rows}
    conditions = [("hot", "Hot"), ("pte-cold", "PTE cold"), ("post-drop", "Post drop-caches")]

    svg = Svg(850, 540, "First-touch latency of native and kernel-backed DSOs")
    panel_title(svg, 65, 35, "", "First-touch latency (median TSC cycles; logarithmic scale)")
    x, y, w, h = 85, 65, 710, 320
    ymin, ymax = 1, 1_000_000
    def sy(v):
        return y + h - (math.log10(v) - math.log10(ymin)) / (math.log10(ymax) - math.log10(ymin)) * h
    for tick in (1, 10, 100, 1_000, 10_000, 100_000, 1_000_000):
        yy = sy(tick)
        svg.line(x, yy, x + w, yy, GRID, 0.8)
        label = f"{int(tick/1000)}K" if 1_000 <= tick < 1_000_000 else ("1M" if tick == 1_000_000 else str(tick))
        svg.text(x - 10, yy + 4, label, 10, "end", fill=GRAY)
    svg.line(x, y, x, y + h, DARK, 1)
    svg.line(x, y + h, x + w, y + h, DARK, 1)
    group_w = w / 3
    bar_w = 54
    for i, (key, label) in enumerate(conditions):
        center = x + group_w * (i + 0.5)
        for target, offset, color in (("native", -bar_w * 0.56, BLUE), ("stub", bar_w * 0.56, ORANGE)):
            value = data[(target, key)]
            xx = center + offset - bar_w / 2
            yy = sy(value)
            svg.rect(xx, yy, bar_w, y + h - yy, color, color, 0, 2)
            shown = f"{value/1000:.1f}K" if value >= 10_000 else f"{value:.0f}"
            svg.text(xx + bar_w / 2, yy - 7, shown, 10, weight=600, fill=color)
            mn, mj = fault[(target, key)]
            svg.text(xx + bar_w / 2, y + h + 39, f"{mn}/{mj}", 9.5, fill=GRAY)
        svg.text(center, y + h + 20, label, 11, weight=600)
    svg.text(x - 55, y + h / 2, "TSC cycles", 11, rotate=-90, fill=GRAY)
    svg.text(x + w / 2, y + h + 62, "minor / major faults in the measured call", 9.5, fill=GRAY)
    legend(svg, 275, 512, [("Native DSO", BLUE, "bar"), ("Kernel-backed Stub DSO", ORANGE, "bar")], 2, 185)
    svg.save(OUT / "first_touch_latency.svg")


def pgot_cost_figure():
    base = ROOT / "test/test_MICRO/test_MICRO_pseudo_noqemu/pgot_benchmarks/results"
    independent = read_csv(base / "layer1/01_data_independent/paper_table.csv")
    dependent = read_csv(base / "layer1/02_data_dependent/paper_table.csv")
    func = read_csv(base / "layer1/03_func_stable/paper_table.csv")
    placement = read_csv(base / "layer2/01_func_placement/paper_table.csv")

    events = [1, 2, 4, 6, 8, 10]
    def scheduled(rows):
        table = {int(r["event"]): float(r["raw_median_delta_cycles_per_event"])
                 for r in rows if r["variant"] == "scheduled" and r["value_mode"] == "raw"}
        return [table[e] for e in events]
    independent_y = scheduled(independent)
    dependent_y = scheduled(dependent)
    func_delta = {}
    for row in func:
        if row["value_mode"] == "raw" and int(row["event"]) == 1:
            func_delta[row["build"]] = float(row["delta_pgot_direct_per_event"])
    placement_rows = [r for r in placement if r["build"] == "retpoline" and r["fence"] == "unfenced"
                      and r["placement"] in {"before", "inside", "after"} and int(r["workload"]) <= 8]

    svg = Svg(1260, 430, "Primitive costs of Pseudo-GOT adaptations")
    panels = [(60, 55, 345, 295), (460, 55, 305, 295), (825, 55, 370, 295)]

    # Panel a: data PGOT.
    x, y, w, h = panels[0]
    panel_title(svg, x, 30, "(a)", "Data-PGOT dependency")
    sy = linear_axis(svg, x, y, w, h, 0, 5.6, [0, 1, 2, 3, 4, 5], "extra cycles / access")
    sx = lambda e: x + (events.index(e) + 0.5) / len(events) * w
    for e in events:
        svg.text(sx(e), y + h + 19, e, 10, fill=GRAY)
    svg.text(x + w / 2, y + h + 40, "accesses per loop iteration", 10.5, fill=GRAY)
    for values, color in ((independent_y, BLUE), (dependent_y, ORANGE)):
        points = [(sx(e), sy(v)) for e, v in zip(events, values)]
        svg.polyline(points, color)
        for px, py in points:
            svg.circle(px, py, 3.6, color)
    legend(svg, x + 45, y + 30, [("independent", BLUE, "line"), ("dependent chain", ORANGE, "line")], 1)

    # Panel b: function PGOT.
    x, y, w, h = panels[1]
    panel_title(svg, x, 30, "(b)", "Stable-target Func-PGOT")
    sy = linear_axis(svg, x, y, w, h, 0, 45, [0, 10, 20, 30, 40], "extra cycles / call")
    for i, (key, label, color) in enumerate((("no_retpoline", "No retpoline", BLUE), ("retpoline", "Retpoline", ORANGE))):
        value = func_delta[key]
        xx = x + 55 + i * 140
        yy = sy(value)
        svg.rect(xx, yy, 72, y + h - yy, color, color, 0, 3)
        svg.text(xx + 36, yy - 8, f"{value:.1f}", 11, weight=700, fill=color)
        svg.text(xx + 36, y + h + 19, label, 10.5, weight=600)

    # Panel c: visible retpoline cost under useful work.
    x, y, w, h = panels[2]
    panel_title(svg, x, 30, "(c)", "Visible cost under useful work")
    sy = linear_axis(svg, x, y, w, h, -5, 42, [0, 10, 20, 30, 40], "paired delta (cycles)")
    workloads = [0, 1, 2, 3, 4, 5, 6, 8]
    sx = lambda e: x + (workloads.index(e) + 0.5) / len(workloads) * w
    by_place = {name: {} for name in ("before", "inside", "after")}
    for row in placement_rows:
        by_place[row["placement"]][int(row["workload"])] = float(row["delta_cycles"])
    for name, color in (("before", BLUE), ("inside", TEAL), ("after", ORANGE)):
        points = [(sx(e), sy(by_place[name][e])) for e in workloads]
        svg.polyline(points, color, 2)
        for px, py in points:
            svg.circle(px, py, 3.2, color)
    for e in workloads:
        svg.text(sx(e), y + h + 19, e, 10, fill=GRAY)
    svg.text(x + w / 2, y + h + 40, "work units", 10.5, fill=GRAY)
    legend(svg, x + 52, y + 28, [("before", BLUE, "line"), ("inside", TEAL, "line"), ("after", ORANGE, "line")], 3, 92)
    svg.save(OUT / "pgot_primitive_costs.svg")


def pgot_closure_figure():
    base = ROOT / "test/test_MICRO/test_MICRO_pseudo_noqemu/pgot_benchmarks/results/layer3"
    selected = read_csv(base / "paper_table_selected.csv")
    choices = {
        "01_sha256_transform": "data_pgot",
        "02_bch_encode": "all_pgot",
        "03_zlib_deflate": "all_pgot",
        "04_zstd_decompress": "all_pgot",
    }
    names = ["SHA-256", "BCH", "zlib", "Zstd"]
    experiment_ids = list(choices)
    values = {"no_retpoline": [], "retpoline": []}
    intervals = {"no_retpoline": [], "retpoline": []}
    for exp in experiment_ids:
        for build in values:
            row = next(r for r in selected if r["experiment"] == exp and r["build"] == build and r["variant"] == choices[exp])
            med = float(row["overhead_percent"])
            half_iqr = float(row["delta_iqr"]) / float(row["origin_cycles"]) * 50.0
            values[build].append(med)
            intervals[build].append((med - half_iqr, med + half_iqr))

    svg = Svg(900, 470, "Pseudo-GOT overhead in copied kernel-function closures")
    panel_title(svg, 75, 35, "", "Complete copied closures (paired median; IQR-width indicator)")
    x, y, w, h = 90, 65, 750, 315
    sy = linear_axis(svg, x, y, w, h, -3, 9, [-2, 0, 2, 4, 6, 8], "overhead vs. origin (%)")
    group_w = w / len(names)
    bar_w = 45
    for i, name in enumerate(names):
        center = x + group_w * (i + 0.5)
        for build, off, color in (("no_retpoline", -29, BLUE), ("retpoline", 29, ORANGE)):
            value = values[build][i]
            xx = center + off - bar_w / 2
            y0 = sy(0)
            yy = sy(value)
            svg.rect(xx, min(yy, y0), bar_w, abs(y0 - yy), color, color, 0, 2)
            lo, hi = intervals[build][i]
            svg.errorbar(center + off, sy(hi), sy(lo), color, 4, 1.2)
            svg.text(center + off, yy - 7 if value >= 0 else yy + 15, f"{value:+.1f}", 9.5, weight=600, fill=color)
        svg.text(center, y + h + 22, name, 11, weight=600)
    legend(svg, 275, 440, [("No retpoline", BLUE, "bar"), ("Retpoline", ORANGE, "bar")], 2, 170)
    svg.save(OUT / "pgot_real_closures.svg")


def lz4_figure():
    rows = read_csv(ROOT / "test/test_lz4/results/pairwise.csv")
    comparisons = [
        ("vkso_vs_kernel_user_nosimd", "same source + helpers", TEAL),
        ("vkso_vs_upstream_native", "upstream native", ORANGE),
    ]
    order = [(op, block) for op in ("compress", "decompress") for block in (4096, 65536, 1048576)]
    labels = ["C\n4K", "C\n64K", "C\n1M", "D\n4K", "D\n64K", "D\n1M"]
    lookup = {(r["comparison"], r["operation"], int(r["block_size"])): r for r in rows}

    svg = Svg(910, 515, "LZ4 throughput ratios for kernel-backed execution")
    panel_title(svg, 75, 35, "", "LZ4: kernel-backed throughput relative to user-space baselines")
    x, y, w, h = 90, 65, 760, 315
    sy = linear_axis(svg, x, y, w, h, -10, 6, [-10, -5, 0, 5], "throughput difference (%)")
    group_w = w / len(order)
    offsets = [-14, 14]
    for j, (comp, title, color) in enumerate(comparisons):
        points = []
        for i, key in enumerate(order):
            row = lookup[(comp, key[0], key[1])]
            value = (float(row["median_ratio"]) - 1) * 100
            lo = (float(row["p10_ratio"]) - 1) * 100
            hi = (float(row["p90_ratio"]) - 1) * 100
            xx = x + group_w * (i + 0.5) + offsets[j]
            points.append((xx, sy(value)))
            svg.errorbar(xx, sy(hi), sy(lo), color, 4, 1.2)
            svg.circle(xx, sy(value), 4.2, color)
        svg.polyline(points, color, 2)
    for i, label in enumerate(labels):
        xx = x + group_w * (i + 0.5)
        op, block = label.split("\n")
        svg.text(xx, y + h + 19, op, 10.5, weight=700)
        svg.text(xx, y + h + 35, block, 9.5, fill=GRAY)
    svg.text(x + w / 2, y + h + 60, "C = compression; D = decompression; bars show P10–P90", 9.5, fill=GRAY)
    legend(svg, 245, 488, [("vs. same-source no-SIMD", TEAL, "line"), ("vs. upstream native", ORANGE, "line")], 2, 215)
    svg.save(OUT / "lz4_component_results.svg")


def bch_figure():
    rows = read_csv(ROOT / "test/test_BCH/results/paired.csv")
    svg = Svg(1000, 470, "BCH decode overhead of kernel-backed execution")
    for panel, t in enumerate((4, 8)):
        x, y, w, h = 70 + panel * 490, 65, 420, 310
        panel_title(svg, x, 35, f"({chr(ord('a') + panel)})", f"BCH m=13, t={t}")
        ymax = 30 if t == 8 else 6
        ymin = -10 if t == 4 else -3
        ticks = [-10, -5, 0, 5] if t == 4 else [0, 5, 10, 15, 20, 25, 30]
        sy = linear_axis(svg, x, y, w, h, ymin, ymax, ticks, "VKSO vs. same source (%)")
        errors = list(range(t + 1))
        sx = lambda e: x + (e + 0.5) / len(errors) * w
        for operation, label, color in (("decode-full", "full decode", TEAL), ("decode-precomputed", "precomputed", ORANGE)):
            selected = {int(r["errors"]): r for r in rows if int(r["t"]) == t and r["operation"] == operation}
            points = []
            for e in errors:
                row = selected[e]
                value = (float(row["median_vkso_over_kernel_native"]) - 1) * 100
                lo = (float(row["p10_vkso_over_kernel_native"]) - 1) * 100
                hi = (float(row["p90_vkso_over_kernel_native"]) - 1) * 100
                xx = sx(e)
                points.append((xx, sy(value)))
                svg.errorbar(xx, sy(hi), sy(lo), color, 3.5, 1.0)
                svg.circle(xx, sy(value), 3.7, color)
            svg.polyline(points, color, 2)
        for e in errors:
            svg.text(sx(e), y + h + 19, e, 10, fill=GRAY)
        svg.text(x + w / 2, y + h + 40, "injected errors", 10.5, fill=GRAY)
    legend(svg, 350, 445, [("Full decode", TEAL, "line"), ("Precomputed decode", ORANGE, "line")], 2, 165)
    svg.save(OUT / "bch_component_results.svg")


def xz_figure():
    rows = read_csv(ROOT / "test/test_xz/results/formal-20260806/raw.csv")
    paired: dict[tuple[str, int], dict[str, float]] = {}
    for row in rows:
        key = (row["case"], int(row["outer_run"]))
        paired.setdefault(key, {})[row["backend"]] = (
            int(row["bytes"]) * int(row["repeats"]) / (1024.0 * 1024.0)
        ) / (
            int(row["elapsed_ns"]) / 1.0e9
        )

    cases = ["bash", "libc.so.6", "python3"]
    ratios: dict[str, list[float]] = {case: [] for case in cases}
    for (case, _run), values in paired.items():
        if set(values) != {"native", "kernel-vkso"}:
            raise RuntimeError(f"incomplete XZ backend pair for {case}")
        ratios[case].append(values["kernel-vkso"] / values["native"])
    if any(len(ratios[case]) != 7 for case in cases):
        raise RuntimeError("XZ formal artifact must contain seven pairs per input")

    medians = [median(ratios[case]) for case in cases]
    geometric_mean = math.exp(
        sum(math.log(value) for value in medians) / len(medians)
    )

    svg = Svg(820, 455, "XZ Embedded throughput of kernel-backed execution")
    panel_title(
        svg, 75, 35, "",
        "XZ Embedded: kernel-backed throughput relative to same-source DSO",
    )
    x, y, w, h = 100, 70, 650, 290
    sy = linear_axis(
        svg, x, y, w, h, -2.5, 0.25,
        [-2.5, -2.0, -1.5, -1.0, -0.5, 0],
        "throughput difference (%)",
    )
    group_w = w / len(cases)
    for index, case in enumerate(cases):
        values = ratios[case]
        value = (median(values) - 1) * 100
        lo = (quantile(values, 0.10) - 1) * 100
        hi = (quantile(values, 0.90) - 1) * 100
        center = x + group_w * (index + 0.5)
        y0 = sy(0)
        yy = sy(value)
        svg.rect(center - 29, min(yy, y0), 58, abs(y0 - yy), TEAL, TEAL, 0, 3)
        svg.errorbar(center, sy(hi), sy(lo), DARK, 6, 1.3)
        svg.text(center, yy - 10, f"{median(values):.3f}×", 10.5, weight=700, fill=WHITE)
        svg.text(center, y + h + 23, case, 11, weight=600)

    gm_delta = (geometric_mean - 1) * 100
    svg.line(x, sy(gm_delta), x + w, sy(gm_delta), PURPLE, 1.3, "6,4")
    svg.text(
        x + w, y - 12,
        f"dashed: geomean {geometric_mean:.4f}×", 10, "end", 600, PURPLE,
    )
    svg.text(
        x + w / 2, 425,
        "Matched medians; whiskers show P10–P90 across seven outer runs",
        10.2, fill=GRAY,
    )
    svg.save(OUT / "xz_component_results.svg")


def clocktime_figure():
    # Final values from VKSO_READ_UPDATE性能报告_20260801.md (tag
    # vkso-clock-vdso-final-20260802).  The assertions catch accidental drift
    # in the authoritative report before figures are regenerated.
    report = (ROOT / "test/test_gettime/vkso-tests/VKSO_READ_UPDATE性能报告_20260801.md").read_text(encoding="utf-8")
    for token in ("+0.941%", "-0.275%", "-13.176%", "-4.111%", "2,639 B", "2,055 B"):
        if token not in report:
            raise RuntimeError(f"clocktime report no longer contains {token}")

    read_names = ["All 20", "Non-fallback", "Fallback", "clock_gettime", "gettimeofday", "getres", "time", "getcpu"]
    read_normal = [0.941, 1.117, -0.051, 3.726, 12.168, -6.041, -18.204, 0.000]
    read_noret = [-0.275, -0.167, -0.886, 1.027, 9.330, -6.693, -18.339, 4.446]
    update_names = ["Mean", "Median", "P95", "P99"]
    update_normal = [-13.176, 5.952, -16.026, -32.473]
    update_noret = [-4.111, 4.124, 1.399, -32.580]
    conc_names = ["mono R", "raw R", "coarse R", "mono W", "raw W", "coarse W"]
    conc_normal = [0.437, 3.870, 13.693, -3.160, -10.576, -10.733]
    conc_noret = [2.380, 2.798, 8.982, -1.948, -6.300, -12.205]

    svg = Svg(1320, 500, "Clocktime case-study performance")
    panels = [(55, 65, 470, 335), (575, 65, 290, 335), (920, 65, 350, 335)]
    specs = [
        ("(a)", "Independent READ", read_names, read_normal, read_noret, -22, 16, [-20, -10, 0, 10]),
        ("(b)", "Independent UPDATE", update_names, update_normal, update_noret, -36, 10, [-30, -20, -10, 0, 10]),
        ("(c)", "Concurrent reader/writer", conc_names, conc_normal, conc_noret, -16, 16, [-10, 0, 10]),
    ]
    for (x, y, w, h), (label, title, names, normal, noret, ymin, ymax, ticks) in zip(panels, specs):
        panel_title(svg, x, 35, label, title)
        sy = linear_axis(svg, x, y, w, h, ymin, ymax, ticks, "VKSO vs. Raw (%)")
        group_w = w / len(names)
        bar_w = min(20, group_w * 0.28)
        for i, name in enumerate(names):
            center = x + group_w * (i + 0.5)
            for value, off, color in ((normal[i], -bar_w * 0.58, BLUE), (noret[i], bar_w * 0.58, ORANGE)):
                xx = center + off - bar_w / 2
                y0 = sy(0)
                yy = sy(value)
                svg.rect(xx, min(yy, y0), bar_w, abs(y0 - yy), color, color, 0, 1.5)
            svg.text(center, y + h + 15, name, 8.5 if len(names) > 6 else 9.3, rotate=-28, anchor="end", fill=GRAY)
    legend(svg, 485, 475, [("Normal", BLUE, "bar"), ("No retpoline", ORANGE, "bar")], 2, 145)
    svg.text(1090, 455, "R = public reader; W = writer mean", 9.5, fill=GRAY)
    svg.save(OUT / "clocktime_performance.svg")


def clocktime_size_figure():
    report = (ROOT / "test/test_gettime/vkso-tests/VKSO_READ_UPDATE性能报告_20260801.md").read_text(encoding="utf-8")
    expected = ("1,505", "1,305", "2,639", "2,055")
    if not all(token in report for token in expected):
        raise RuntimeError("clocktime size values drifted from the final report")
    panels = [
        ("Runtime SLOC", 1347, 1248, "SLOC"),
        ("Product SLOC", 1505, 1305, "SLOC"),
        ("Reader closure", 2639, 2055, "bytes"),
    ]
    svg = Svg(880, 430, "Clocktime case-study code size")
    for i, (title, raw, vkso, unit) in enumerate(panels):
        x, y, w, h = 55 + i * 285, 75, 230, 270
        panel_title(svg, x, 38, f"({chr(ord('a') + i)})", title)
        ymax = math.ceil(max(raw, vkso) * 1.18 / 250) * 250
        ticks = [0, ymax / 2, ymax]
        sy = linear_axis(svg, x, y, w, h, 0, ymax, ticks, unit)
        for j, (label, value, color) in enumerate((("Raw", raw, BLUE), ("VKSO", vkso, ORANGE))):
            xx = x + 42 + j * 92
            yy = sy(value)
            svg.rect(xx, yy, 54, y + h - yy, color, color, 0, 3)
            svg.text(xx + 27, yy - 8, f"{value:,}", 10.5, weight=700, fill=color)
            svg.text(xx + 27, y + h + 20, label, 10.5, weight=600)
        reduction = (1 - vkso / raw) * 100
        svg.text(x + w / 2, y + h + 45, f"−{reduction:.1f}%", 11, weight=700, fill=TEAL)
    svg.save(OUT / "clocktime_code_size.svg")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    architecture_figure()
    page_grafting_figure()
    binding_adaptation_figure()
    first_touch_figure()
    pgot_cost_figure()
    pgot_closure_figure()
    lz4_figure()
    bch_figure()
    xz_figure()
    clocktime_figure()
    clocktime_size_figure()
    print("generated 11 SVG figures in", OUT)


if __name__ == "__main__":
    main()
