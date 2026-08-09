from __future__ import annotations

import csv
import html
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
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

TERMINATION_COLORS = {
    "clean": CORE,
    "output_cap": STRICT,
    "context_overflow": EROSION,
    "retry": VERBOSITY,
    "length_no_content": CLONED,
}
TERMINATION_ORDER = [
    "clean",
    "output_cap",
    "retry",
    "context_overflow",
    "length_no_content",
]

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


@dataclass(frozen=True)
class RunSpec:
    """Everything that varies between published runs."""

    data_dir: str
    prefix: str
    scorecard_title: str
    agent_label: str
    thinking: str
    termination_runs: tuple[tuple[str, str], ...] = ()

    @property
    def data_path(self) -> Path:
        return DATA_ROOT / self.data_dir

    @property
    def input_path(self) -> Path:
        return self.data_path / "checkpoint_results.jsonl"

    @property
    def csv_path(self) -> Path:
        return self.data_path / "checkpoints.csv"

    def image_path(self, name: str) -> Path:
        return IMAGE_DIR / f"{self.prefix}{name}.svg"


OPENCODE_RUN = "deepseek-v4-flash-opencode-high-2026-07-31"
PI_0807_RUN = "deepseek-v4-flash-0731-pi-xhigh-2026-08-07"
PI_0808_RUN = "deepseek-v4-flash-0731-pi-xhigh-2026-08-08"

RUNS: dict[str, RunSpec] = {
    OPENCODE_RUN: RunSpec(
        data_dir=OPENCODE_RUN,
        prefix="deepseek-v4-flash-",
        scorecard_title="DeepSeek V4 Flash on SlopCodeBench",
        agent_label="OpenCode 1.18.10",
        thinking="high",
    ),
    PI_0808_RUN: RunSpec(
        data_dir=PI_0808_RUN,
        prefix="deepseek-v4-flash-0731-",
        scorecard_title="DeepSeek V4 Flash 0731 on SlopCodeBench",
        agent_label="pi 0.84.0",
        thinking="xhigh",
        termination_runs=(
            ("2026-08-07", PI_0807_RUN),
            ("2026-08-08", PI_0808_RUN),
        ),
    ),
}
DEFAULT_RUN = OPENCODE_RUN


def load_records(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text().splitlines() if line.strip()
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


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as file:
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
                    "reasoning_tokens": item.get("reasoning", 0),
                    "loc": item["loc"],
                    "functions": item["functions"],
                    "cc_max": item["cc_max"],
                    # Quality metrics are absent, not zero, when a checkpoint
                    # snapshot holds no source file for the analyzer to read.
                    # That happens when the agent loop was truncated before it
                    # wrote anything, so an empty cell here is a real signal
                    # and must not be flattened into 0.
                    "verbosity": item.get("verbosity"),
                    "erosion": item.get("erosion"),
                    "cloned_pct": item.get("cloned_pct"),
                }
            )


def render_scorecard(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
    width = 1440
    height = 820
    title = spec.scorecard_title
    svg = svg_start(width, height, title)
    totals = [item for values in groups.values() for item in values]
    subtitle = (
        f"{len(groups)} problems · {len(totals)} checkpoints · "
        f"{spec.agent_label} · {spec.thinking}"
    )
    svg.extend(
        [
            svg_text(90, 92, title, size=42, weight=750),
            svg_text(90, 132, subtitle, size=20, fill=MUTED),
        ]
    )

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

    total_cost = sum(float(item["cost"]) for item in totals)
    mean_pass = sum(float(item["strict_pass_rate"]) for item in totals)
    mean_pass /= len(totals)
    problems_solved = sum(
        all(item["strict_pass_rate"] == 1 for item in values)
        for values in groups.values()
    )
    svg.extend(
        [
            (
                '<rect x="90" y="700" width="1260" height="74" rx="18" '
                f'fill="{PANEL}" filter="url(#shadow)"/>'
            ),
            svg_text(125, 746, "Total cost", size=16, fill=MUTED),
            svg_text(245, 748, f"${total_cost:.4f}", size=28, weight=750),
            svg_text(520, 746, "Mean test pass", size=16, fill=MUTED),
            svg_text(690, 748, f"{mean_pass * 100:.1f}%", size=28, weight=750),
            svg_text(920, 746, "Problems solved", size=16, fill=MUTED),
            svg_text(
                1085,
                748,
                f"{problems_solved} / {len(groups)}",
                size=28,
                weight=750,
            ),
        ]
    )
    write_svg(spec.image_path("scorecard"), svg)


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
    step: float = 205,
) -> None:
    cursor = x
    for label, color in items:
        svg.append(
            f'<line x1="{cursor}" y1="{y}" x2="{cursor + 34}" '
            f'y2="{y}" stroke="{color}" stroke-width="5" '
            'stroke-linecap="round"/>'
        )
        svg.append(svg_text(cursor + 45, y + 6, label, size=16, fill=MUTED))
        cursor += step


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


def render_correctness(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
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
    write_svg(spec.image_path("correctness"), svg)


def render_quality(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
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
    write_svg(spec.image_path("quality"), svg)


def growth_maximum(groups: dict[str, list[dict[str, Any]]]) -> int:
    peak = max(
        int(record["loc"]) for values in groups.values() for record in values
    )
    return ((peak // 500) + 1) * 500


def render_code_growth(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
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
    maximum = growth_maximum(groups)
    for value in range(0, maximum, 1000):
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
    write_svg(spec.image_path("code-growth"), svg)


def load_trajectory(data_dir: str) -> dict[tuple[str, int], dict[str, Any]]:
    path = DATA_ROOT / data_dir / "trajectory.jsonl"
    entries: dict[tuple[str, int], dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        entries[(item["problem"], int(item["checkpoint"]))] = item
    return entries


def checkpoint_slots(
    groups: dict[str, list[dict[str, Any]]],
) -> list[tuple[str, int]]:
    slots: list[tuple[str, int]] = []
    for problem in DISPLAY_NAMES:
        for record in groups.get(problem, []):
            slots.append((problem, int(record["idx"])))
    return slots


def termination_counts(
    entries: dict[tuple[str, int], dict[str, Any]],
    slots: list[tuple[str, int]],
) -> str:
    counts: dict[str, int] = defaultdict(int)
    for slot in slots:
        entry = entries.get(slot)
        if entry is not None:
            counts[str(entry["termination"])] += 1
    parts = [
        f"{name.replace('_', ' ')} {counts[name]}"
        for name in TERMINATION_ORDER
        if counts.get(name)
    ]
    return "  ·  ".join(parts)


def render_termination(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
    width = 1540
    height = 620
    title = "Why the agent loop stopped"
    svg = svg_start(width, height, title)
    svg.extend(
        [
            svg_text(70, 72, title, size=36, weight=750),
            svg_text(
                70,
                108,
                "Termination reason per checkpoint, both pi runs",
                size=18,
                fill=MUTED,
            ),
        ]
    )

    slots = checkpoint_slots(groups)
    cell_width = 66.0
    cell_gap = 10.0
    cell_height = 74.0
    plot_x = 70.0
    matrix_width = len(slots) * cell_width + (len(slots) - 1) * cell_gap
    row_top = 250.0
    row_gap = 150.0

    svg.append(
        f'<rect x="50" y="170" width="{matrix_width + 40:.1f}" '
        f'height="{row_top + row_gap + cell_height + 46 - 170:.1f}" '
        f'rx="20" fill="{PANEL}"/>'
    )

    def slot_x(index: int) -> float:
        return plot_x + index * (cell_width + cell_gap)

    for problem in DISPLAY_NAMES:
        indexes = [
            index
            for index, (name, _) in enumerate(slots)
            if name == problem
        ]
        if not indexes:
            continue
        start = slot_x(indexes[0])
        end = slot_x(indexes[-1]) + cell_width
        svg.append(
            f'<line x1="{start:.1f}" y1="212" x2="{end:.1f}" y2="212" '
            f'stroke="{PROBLEM_COLORS[problem]}" stroke-width="3" '
            'stroke-linecap="round"/>'
        )
        svg.append(
            svg_text(
                (start + end) / 2,
                202,
                DISPLAY_NAMES[problem],
                size=15,
                fill=PROBLEM_COLORS[problem],
                weight=650,
                anchor="middle",
            )
        )

    for row, (label, data_dir) in enumerate(spec.termination_runs):
        entries = load_trajectory(data_dir)
        y = row_top + row * row_gap
        svg.append(svg_text(plot_x, y - 16, label, size=19, weight=700))
        svg.append(
            svg_text(
                plot_x + matrix_width,
                y - 16,
                termination_counts(entries, slots),
                size=15,
                fill=MUTED,
                anchor="end",
            )
        )
        for index, slot in enumerate(slots):
            entry = entries.get(slot)
            termination = str(entry["termination"]) if entry else "missing"
            color = TERMINATION_COLORS.get(termination, GRID)
            x = slot_x(index)
            svg.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" '
                f'width="{cell_width:.1f}" height="{cell_height:.1f}" '
                f'rx="12" fill="{color}"/>'
            )
            svg.append(
                svg_text(
                    x + cell_width / 2,
                    y + 34,
                    f"C{slot[1]}",
                    size=16,
                    fill=BACKGROUND,
                    weight=750,
                    anchor="middle",
                )
            )
            changed = len(entry["files_changed"]) if entry else 0
            plural = "" if changed == 1 else "s"
            note = (
                "no edits" if changed == 0 else f"{changed} file{plural}"
            )
            svg.append(
                svg_text(
                    x + cell_width / 2,
                    y + 56,
                    note,
                    size=11,
                    fill=BACKGROUND,
                    weight=600,
                    anchor="middle",
                )
            )

    add_legend(
        svg,
        [
            ("Clean stop", CORE),
            ("Output cap", STRICT),
            ("Retry", VERBOSITY),
            ("Context overflow", EROSION),
            ("Length, no content", CLONED),
        ],
        x=70,
        y=568,
        step=280,
    )
    write_svg(spec.image_path("termination"), svg)


def resolve_spec(argument: str | None) -> RunSpec:
    if argument is None:
        return RUNS[DEFAULT_RUN]
    name = Path(argument.rstrip("/")).name
    if name not in RUNS:
        known = ", ".join(sorted(RUNS))
        raise SystemExit(f"unknown run {name!r}; known runs: {known}")
    return RUNS[name]


def main() -> None:
    spec = resolve_spec(sys.argv[1] if len(sys.argv) > 1 else None)
    IMAGE_DIR.mkdir(exist_ok=True)
    records = load_records(spec.input_path)
    groups = group_records(records)
    write_csv(spec.csv_path, records)
    render_scorecard(spec, groups)
    render_correctness(spec, groups)
    render_quality(spec, groups)
    render_code_growth(spec, groups)
    if spec.termination_runs:
        render_termination(spec, groups)


if __name__ == "__main__":
    main()
