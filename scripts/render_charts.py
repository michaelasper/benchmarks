from __future__ import annotations

import csv
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "deepseek-v4-flash-opencode-high-2026-07-31"
INPUT_PATH = DATA_DIR / "checkpoint_results.jsonl"
CSV_PATH = DATA_DIR / "checkpoints.csv"
IMAGE_DIR = ROOT / "images"

BACKGROUND = "#0b1020"
PANEL = "#121a2c"
GRID = "#2b3650"
TEXT = "#f5f7ff"
MUTED = "#9aa8c4"
STRICT = "#ff6b6b"
ISOLATED = "#4ecdc4"
CORE = "#a3e635"
VERBOSITY = "#f59e0b"
EROSION = "#f43f5e"
CLONED = "#8b5cf6"
PROBLEM_COLORS = {
    "circuit_eval": "#38bdf8",
    "database_migration": "#f59e0b",
    "dynamic_config_service_api": "#a78bfa",
}
DISPLAY_NAMES = {
    "circuit_eval": "Circuit evaluator",
    "database_migration": "Database migration",
    "dynamic_config_service_api": "Dynamic config API",
}

CSV_FIELDS = [
    "problem",
    "checkpoint",
    "strict_solved",
    "isolated_solved",
    "core_solved",
    "passed_tests",
    "total_tests",
    "total_pass_rate",
    "isolated_pass_rate",
    "core_pass_rate",
    "cost",
    "duration_seconds",
    "steps",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "loc",
    "functions",
    "cc_max",
    "verbosity",
    "erosion",
    "cloned_pct",
]


def load_records() -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in INPUT_PATH.read_text().splitlines() if line.strip()
    ]


def group_records(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[record["problem"]].append(record)
    for problem_records in groups.values():
        problem_records.sort(key=lambda item: item["idx"])
    return dict(groups)


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def svg_text(
    x: float,
    y: float,
    value: object,
    *,
    size: int = 18,
    fill: str = TEXT,
    weight: int = 400,
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" '
        f'font-family="Inter, ui-sans-serif, system-ui, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}">{escape(value)}</text>'
    )


def svg_start(width: int, height: int, title: str) -> list[str]:
    return [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{escape(title)}">'
        ),
        f"<title>{escape(title)}</title>",
        (
            '<defs><filter id="shadow" x="-20%" y="-20%" '
            'width="140%" height="140%"><feDropShadow dx="0" '
            'dy="8" stdDeviation="12" flood-opacity="0.24"/>'
            "</filter></defs>"
        ),
        f'<rect width="{width}" height="{height}" fill="{BACKGROUND}"/>',
    ]


def write_svg(path: Path, elements: list[str]) -> None:
    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n")


def write_csv(records: list[dict[str, Any]]) -> None:
    with CSV_PATH.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        for item in records:
            writer.writerow(
                {
                    "problem": item["problem"],
                    "checkpoint": item["idx"],
                    "strict_solved": item["strict_pass_rate"] == 1,
                    "isolated_solved": item["isolated_pass_rate"] == 1,
                    "core_solved": item["core_pass_rate"] == 1,
                    "passed_tests": item["passed_tests"],
                    "total_tests": item["total_tests"],
                    "total_pass_rate": item["strict_pass_rate"],
                    "isolated_pass_rate": item["isolated_pass_rate"],
                    "core_pass_rate": item["core_pass_rate"],
                    "cost": item["cost"],
                    "duration_seconds": item["duration"],
                    "steps": item["steps"],
                    "input_tokens": item["input"],
                    "output_tokens": item["output"],
                    "reasoning_tokens": item["reasoning"],
                    "loc": item["loc"],
                    "functions": item["functions"],
                    "cc_max": item["cc_max"],
                    "verbosity": item["verbosity"],
                    "erosion": item["erosion"],
                    "cloned_pct": item["cloned_pct"],
                }
            )


def render_scorecard(groups: dict[str, list[dict[str, Any]]]) -> None:
    width = 1440
    height = 820
    title = "DeepSeek V4 Flash on SlopCodeBench"
    svg = svg_start(width, height, title)
    svg.extend(
        [
            svg_text(90, 92, title, size=42, weight=750),
            svg_text(
                90,
                132,
                "3 problems · 17 checkpoints · OpenCode 1.18.10 · high",
                size=20,
                fill=MUTED,
            ),
        ]
    )

    totals = [item for values in groups.values() for item in values]
    rows: list[tuple[str, list[dict[str, Any]]]] = [
        (DISPLAY_NAMES[name], groups[name]) for name in DISPLAY_NAMES
    ]
    rows.append(("Overall", totals))
    metrics = [
        ("Strict", "strict_pass_rate", STRICT),
        ("Isolated", "isolated_pass_rate", ISOLATED),
        ("Core", "core_pass_rate", CORE),
    ]

    left = 320
    top = 205
    bar_width = 900
    row_gap = 120
    for index, (label, values) in enumerate(rows):
        y = top + index * row_gap
        svg.append(svg_text(90, y + 33, label, size=20, weight=650))
        svg.append(
            f'<rect x="{left}" y="{y}" width="{bar_width}" height="46" '
            f'rx="10" fill="{PANEL}"/>'
        )
        x = left
        for metric_label, field, color in metrics:
            solved = sum(item[field] == 1 for item in values)
            rate = solved / len(values)
            segment = bar_width / 3
            fill_width = max(2, segment * rate)
            svg.append(
                f'<rect x="{x:.1f}" y="{y}" width="{fill_width:.1f}" '
                f'height="46" rx="10" fill="{color}"/>'
            )
            value = f"{solved}/{len(values)}  {rate * 100:.1f}%"
            svg.append(
                svg_text(
                    x + segment / 2,
                    y + 31,
                    value,
                    size=18,
                    weight=700,
                    anchor="middle",
                )
            )
            svg.append(
                svg_text(
                    x + segment / 2,
                    y + 75,
                    metric_label,
                    size=15,
                    fill=MUTED,
                    anchor="middle",
                )
            )
            x += segment

    svg.extend(
        [
            (
                '<rect x="90" y="700" width="1260" height="74" rx="18" '
                f'fill="{PANEL}" filter="url(#shadow)"/>'
            ),
            svg_text(125, 746, "Total cost", size=16, fill=MUTED),
            svg_text(245, 748, "$0.6785", size=28, weight=750),
            svg_text(520, 746, "Mean test pass", size=16, fill=MUTED),
            svg_text(690, 748, "87.5%", size=28, weight=750),
            svg_text(920, 746, "Problems solved", size=16, fill=MUTED),
            svg_text(1085, 748, "0 / 3", size=28, weight=750),
        ]
    )
    write_svg(IMAGE_DIR / "deepseek-v4-flash-scorecard.svg", svg)


def points_for(
    records: list[dict[str, Any]],
    field: str,
    x: float,
    y: float,
    width: float,
    height: float,
) -> list[tuple[float, float]]:
    count = len(records)
    return [
        (
            x + (index * width / max(1, count - 1)),
            y + height - float(record[field]) * height,
        )
        for index, record in enumerate(records)
    ]


def path_from(points: list[tuple[float, float]]) -> str:
    return " ".join(
        ("M" if index == 0 else "L") + f" {x:.1f} {y:.1f}"
        for index, (x, y) in enumerate(points)
    )


def add_legend(
    svg: list[str],
    items: list[tuple[str, str]],
    *,
    x: float,
    y: float,
) -> None:
    cursor = x
    for label, color in items:
        svg.append(
            f'<line x1="{cursor}" y1="{y}" x2="{cursor + 34}" '
            f'y2="{y}" stroke="{color}" stroke-width="5" '
            'stroke-linecap="round"/>'
        )
        svg.append(svg_text(cursor + 45, y + 6, label, size=16, fill=MUTED))
        cursor += 205


def add_rate_panel(
    svg: list[str],
    records: list[dict[str, Any]],
    *,
    panel_x: float,
    panel_y: float,
    panel_width: float,
    panel_height: float,
    fields: list[tuple[str, str]],
) -> None:
    plot_x = panel_x + 58
    plot_y = panel_y + 72
    plot_width = panel_width - 88
    plot_height = panel_height - 132
    svg.append(
        f'<rect x="{panel_x}" y="{panel_y}" width="{panel_width}" '
        f'height="{panel_height}" rx="20" fill="{PANEL}"/>'
    )
    svg.append(
        svg_text(
            panel_x + 28,
            panel_y + 40,
            DISPLAY_NAMES[records[0]["problem"]],
            size=20,
            weight=700,
        )
    )

    for percent in (0, 25, 50, 75, 100):
        grid_y = plot_y + plot_height * (1 - percent / 100)
        svg.append(
            f'<line x1="{plot_x}" y1="{grid_y:.1f}" '
            f'x2="{plot_x + plot_width}" y2="{grid_y:.1f}" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
        svg.append(
            svg_text(
                plot_x - 10,
                grid_y + 5,
                f"{percent}%",
                size=12,
                fill=MUTED,
                anchor="end",
            )
        )

    for index, record in enumerate(records):
        px = plot_x + index * plot_width / max(1, len(records) - 1)
        svg.append(
            svg_text(
                px,
                plot_y + plot_height + 28,
                f"C{record['idx']}",
                size=13,
                fill=MUTED,
                anchor="middle",
            )
        )

    for field, color in fields:
        points = points_for(
            records,
            field,
            plot_x,
            plot_y,
            plot_width,
            plot_height,
        )
        svg.append(
            f'<path d="{path_from(points)}" fill="none" '
            f'stroke="{color}" stroke-width="4" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for px, py in points:
            svg.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" '
                f'fill="{color}" stroke="{PANEL}" stroke-width="2"/>'
            )


def render_correctness(groups: dict[str, list[dict[str, Any]]]) -> None:
    width = 1540
    height = 650
    title = "Correctness by checkpoint"
    svg = svg_start(width, height, title)
    svg.extend(
        [
            svg_text(70, 72, title, size=36, weight=750),
            svg_text(
                70,
                108,
                "100% is the strict-pass threshold",
                size=18,
                fill=MUTED,
            ),
        ]
    )
    add_legend(
        svg,
        [
            ("All tests", STRICT),
            ("Current checkpoint", ISOLATED),
            ("Core behavior", CORE),
        ],
        x=720,
        y=82,
    )

    for index, problem in enumerate(DISPLAY_NAMES):
        add_rate_panel(
            svg,
            groups[problem],
            panel_x=50 + index * 500,
            panel_y=145,
            panel_width=470,
            panel_height=450,
            fields=[
                ("strict_pass_rate", STRICT),
                ("isolated_pass_rate", ISOLATED),
                ("core_pass_rate", CORE),
            ],
        )
    write_svg(IMAGE_DIR / "deepseek-v4-flash-correctness.svg", svg)


def render_quality(groups: dict[str, list[dict[str, Any]]]) -> None:
    width = 1540
    height = 690
    title = "Quality signals by checkpoint"
    svg = svg_start(width, height, title)
    svg.extend(
        [
            svg_text(70, 72, title, size=36, weight=750),
            svg_text(
                70,
                108,
                "Share of lines or complexity mass flagged",
                size=18,
                fill=MUTED,
            ),
        ]
    )
    add_legend(
        svg,
        [
            ("Verbosity", VERBOSITY),
            ("Structural erosion", EROSION),
            ("Cloned lines", CLONED),
        ],
        x=745,
        y=82,
    )

    for index, problem in enumerate(DISPLAY_NAMES):
        records = groups[problem]
        add_rate_panel(
            svg,
            records,
            panel_x=50 + index * 500,
            panel_y=145,
            panel_width=470,
            panel_height=480,
            fields=[
                ("verbosity", VERBOSITY),
                ("erosion", EROSION),
                ("cloned_pct", CLONED),
            ],
        )
        first = records[0]["loc"]
        final = records[-1]["loc"]
        svg.append(
            svg_text(
                285 + index * 500,
                655,
                f"LOC  {first:,} → {final:,}",
                size=15,
                fill=MUTED,
                anchor="middle",
            )
        )
    write_svg(IMAGE_DIR / "deepseek-v4-flash-quality.svg", svg)


def render_code_growth(groups: dict[str, list[dict[str, Any]]]) -> None:
    width = 1400
    height = 720
    title = "Source volume carried forward"
    svg = svg_start(width, height, title)
    svg.extend(
        [
            svg_text(80, 76, title, size=36, weight=750),
            svg_text(
                80,
                112,
                "Lines of code in each checkpoint snapshot",
                size=18,
                fill=MUTED,
            ),
        ]
    )

    plot_x = 125
    plot_y = 165
    plot_width = 1160
    plot_height = 440
    maximum = 4500
    for value in (0, 1000, 2000, 3000, 4000):
        grid_y = plot_y + plot_height * (1 - value / maximum)
        svg.append(
            f'<line x1="{plot_x}" y1="{grid_y:.1f}" '
            f'x2="{plot_x + plot_width}" y2="{grid_y:.1f}" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
        svg.append(
            svg_text(
                plot_x - 20,
                grid_y + 5,
                f"{value:,}",
                size=14,
                fill=MUTED,
                anchor="end",
            )
        )

    max_checkpoints = max(len(values) for values in groups.values())
    for checkpoint in range(1, max_checkpoints + 1):
        px = plot_x + (checkpoint - 1) * plot_width / (max_checkpoints - 1)
        svg.append(
            svg_text(
                px,
                plot_y + plot_height + 35,
                f"C{checkpoint}",
                size=15,
                fill=MUTED,
                anchor="middle",
            )
        )

    for problem, records in groups.items():
        color = PROBLEM_COLORS[problem]
        points = [
            (
                plot_x + (record["idx"] - 1) * plot_width / (max_checkpoints - 1),
                plot_y + plot_height * (1 - float(record["loc"]) / maximum),
            )
            for record in records
        ]
        svg.append(
            f'<path d="{path_from(points)}" fill="none" '
            f'stroke="{color}" stroke-width="5" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for index, (px, py) in enumerate(points):
            svg.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" '
                f'fill="{color}" stroke="{BACKGROUND}" stroke-width="3"/>'
            )
            if index == len(points) - 1:
                svg.append(
                    svg_text(
                        px + 12,
                        py - 12,
                        f"{records[index]['loc']:,}",
                        size=14,
                        fill=color,
                        weight=700,
                    )
                )

    add_legend(
        svg,
        [
            ("Circuit evaluator", PROBLEM_COLORS["circuit_eval"]),
            ("Database migration", PROBLEM_COLORS["database_migration"]),
            (
                "Dynamic config API",
                PROBLEM_COLORS["dynamic_config_service_api"],
            ),
        ],
        x=310,
        y=680,
    )
    write_svg(IMAGE_DIR / "deepseek-v4-flash-code-growth.svg", svg)


def main() -> None:
    IMAGE_DIR.mkdir(exist_ok=True)
    records = load_records()
    groups = group_records(records)
    write_csv(records)
    render_scorecard(groups)
    render_correctness(groups)
    render_quality(groups)
    render_code_growth(groups)


if __name__ == "__main__":
    main()
