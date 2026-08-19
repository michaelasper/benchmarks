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
QWEN_DISPLAY_NAMES = {
    "circuit_eval": "Circuit evaluator",
    "database_migration": "Database migration",
    "dynamic_config_service_api": "Dynamic config API",
    "xjq": "xjq",
    "file_backup": "File backup",
    "dag_execution": "DAG execution",
    "code_search": "Code search",
    "etl_pipeline": "ETL pipeline",
}
QWEN_PROBLEM_COLORS = {
    "circuit_eval": "#38bdf8",
    "database_migration": "#f59e0b",
    "dynamic_config_service_api": "#a78bfa",
    "xjq": "#2dd4bf",
    "file_backup": "#fb7185",
    "dag_execution": "#f97316",
    "code_search": "#60a5fa",
    "etl_pipeline": "#a3e635",
}
QWEN_OPUS_SUBSET = {
    "circuit_eval",
    "database_migration",
    "dynamic_config_service_api",
}
QWEN_SOL_FABLE_KIMI_SUBSET = {
    "xjq",
    "file_backup",
    "dag_execution",
    "circuit_eval",
    "code_search",
    "etl_pipeline",
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
    kind: str = "legacy"
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
QWEN_RUN = "qwen3.8-27b-pi-xhigh-2026-08-19"

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
    QWEN_RUN: RunSpec(
        data_dir=QWEN_RUN,
        prefix="qwen3.8-27b-pi-",
        scorecard_title="Qwen3.8-27B on SlopCodeBench",
        agent_label="pi 0.84.2",
        thinking="xhigh",
        kind="qwen",
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


def subset_records(
    groups: dict[str, list[dict[str, Any]]],
    names: set[str],
) -> list[dict[str, Any]]:
    return [
        record
        for problem, records in groups.items()
        if problem in names
        for record in records
    ]


def exact_summary(records: list[dict[str, Any]]) -> tuple[int, int, int]:
    return tuple(
        sum(record[field] == 1 for record in records)
        for field in (
            "strict_pass_rate",
            "isolated_pass_rate",
            "core_pass_rate",
        )
    )


def render_qwen_scorecard(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
    width = 1600
    height = 960
    title = spec.scorecard_title
    all_records = [record for records in groups.values() for record in records]
    strict, isolated, core = exact_summary(all_records)
    count = len(all_records)
    total_cost = sum(record["cost"] for record in all_records)
    full_problems = sum(
        all(record["strict_pass_rate"] == 1 for record in records)
        for records in groups.values()
    )
    partial_problems = sum(
        any(record["strict_pass_rate"] == 1 for record in records)
        for records in groups.values()
    )

    svg = svg_start(width, height, title)
    svg.extend(
        [
            svg_text(80, 78, title, size=42, weight=750),
            svg_text(
                80,
                118,
                "Eight cumulative coding trajectories · 39 checkpoints",
                size=19,
                fill=MUTED,
            ),
        ]
    )

    cards = [
        ("Strict", f"{strict}/{count}", f"{strict / count:.1%}", STRICT),
        (
            "Isolated",
            f"{isolated}/{count}",
            f"{isolated / count:.1%}",
            ISOLATED,
        ),
        ("Core", f"{core}/{count}", f"{core / count:.1%}", CORE),
        (
            "Full problems",
            f"{full_problems}/{len(groups)}",
            "end to end",
            "#f8fafc",
        ),
        (
            "Partial problems",
            f"{partial_problems}/{len(groups)}",
            f"{partial_problems / len(groups):.1%}",
            VERBOSITY,
        ),
        ("API cost", f"${total_cost:.2f}", "billed", "#f8fafc"),
    ]
    card_width = 226
    card_gap = 16
    for index, (label, value, note, color) in enumerate(cards):
        x = 80 + index * (card_width + card_gap)
        svg.extend(
            [
                (
                    f'<rect x="{x}" y="155" width="{card_width}" '
                    f'height="154" rx="18" fill="{PANEL}" '
                    'filter="url(#shadow)"/>'
                ),
                svg_text(x + 22, 190, label, size=15, fill=MUTED, weight=650),
                svg_text(x + 22, 248, value, size=34, fill=color, weight=750),
                svg_text(x + 22, 282, note, size=15, fill=MUTED),
            ]
        )

    svg.extend(
        [
            svg_text(80, 374, "Exact checkpoint solves", size=26, weight=750),
            svg_text(
                80,
                406,
                "Each threshold requires a perfect 100%; partial credit is excluded.",
                size=16,
                fill=MUTED,
            ),
            (
                '<rect x="80" y="435" width="1440" height="238" '
                f'rx="22" fill="{PANEL}"/>'
            ),
        ]
    )
    funnel = [
        ("Core contract", core, CORE),
        ("Current checkpoint", isolated, ISOLATED),
        ("Current + inherited tests", strict, STRICT),
    ]
    track_x = 390
    track_width = 1010
    for index, (label, solved, color) in enumerate(funnel):
        y = 474 + index * 62
        svg.extend(
            [
                svg_text(115, y + 25, label, size=17, weight=650),
                (
                    f'<rect x="{track_x}" y="{y}" width="{track_width}" '
                    f'height="35" rx="10" fill="{BACKGROUND}"/>'
                ),
                (
                    f'<rect x="{track_x}" y="{y}" '
                    f'width="{track_width * solved / count:.1f}" '
                    f'height="35" rx="10" fill="{color}"/>'
                ),
                svg_text(
                    1465,
                    y + 25,
                    f"{solved}/{count}  {solved / count:.1%}",
                    size=17,
                    fill=color,
                    weight=750,
                    anchor="end",
                ),
            ]
        )
    svg.extend(
        [
            svg_text(
                390,
                645,
                f"Core → isolated: −{(core - isolated) * 100 / count:.1f} pp",
                size=14,
                fill=MUTED,
            ),
            svg_text(
                760,
                645,
                f"Isolated → strict: −{(isolated - strict) * 100 / count:.1f} pp",
                size=14,
                fill=MUTED,
            ),
        ]
    )

    subset_specs = [
        ("Opus 5 subset", QWEN_OPUS_SUBSET, 80),
        (
            "Fable, Sol and Kimi subset",
            QWEN_SOL_FABLE_KIMI_SUBSET,
            810,
        ),
    ]
    for label, names, x in subset_specs:
        records = subset_records(groups, names)
        subset_strict, subset_isolated, subset_core = exact_summary(records)
        subset_cost = sum(record["cost"] for record in records)
        svg.extend(
            [
                (
                    f'<rect x="{x}" y="710" width="710" height="172" '
                    f'rx="20" fill="{PANEL}"/>'
                ),
                svg_text(x + 28, 749, label, size=20, weight=750),
                svg_text(
                    x + 682,
                    749,
                    f"{len(records)} checkpoints",
                    size=15,
                    fill=MUTED,
                    anchor="end",
                ),
            ]
        )
        values = [
            ("Strict", subset_strict, STRICT),
            ("Isolated", subset_isolated, ISOLATED),
            ("Core", subset_core, CORE),
        ]
        for index, (metric, solved, color) in enumerate(values):
            metric_x = x + 28 + index * 185
            svg.extend(
                [
                    svg_text(metric_x, 792, metric, size=14, fill=MUTED),
                    svg_text(
                        metric_x,
                        832,
                        f"{solved}/{len(records)}",
                        size=27,
                        fill=color,
                        weight=750,
                    ),
                ]
            )
        svg.extend(
            [
                svg_text(x + 590, 792, "Cost", size=14, fill=MUTED),
                svg_text(x + 590, 832, f"${subset_cost:.2f}", size=27, weight=750),
            ]
        )
    svg.append(
        svg_text(
            800,
            922,
            (
                "circuit_eval appears in both subsets; the union counts its "
                "8 checkpoints once."
            ),
            size=15,
            fill=MUTED,
            anchor="middle",
        )
    )
    write_svg(spec.image_path("scorecard"), svg)


def add_qwen_rate_panel(
    svg: list[str],
    records: list[dict[str, Any]],
    *,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    problem = records[0]["problem"]
    color = QWEN_PROBLEM_COLORS[problem]
    strict, isolated, core = exact_summary(records)
    svg.extend(
        [
            (
                f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                f'rx="18" fill="{PANEL}"/>'
            ),
            svg_text(
                x + 24,
                y + 35,
                QWEN_DISPLAY_NAMES[problem],
                size=18,
                fill=color,
                weight=750,
            ),
            svg_text(
                x + width - 24,
                y + 35,
                (
                    f"exact  {strict}/{len(records)} · "
                    f"{isolated}/{len(records)} · {core}/{len(records)}"
                ),
                size=13,
                fill=MUTED,
                anchor="end",
            ),
        ]
    )
    plot_x = x + 58
    plot_y = y + 58
    plot_width = width - 88
    plot_height = height - 100
    for percent in (0, 50, 100):
        grid_y = plot_y + plot_height * (1 - percent / 100)
        svg.extend(
            [
                (
                    f'<line x1="{plot_x}" y1="{grid_y:.1f}" '
                    f'x2="{plot_x + plot_width}" y2="{grid_y:.1f}" '
                    f'stroke="{GRID}" stroke-width="1"/>'
                ),
                svg_text(
                    plot_x - 9,
                    grid_y + 4,
                    f"{percent}%",
                    size=11,
                    fill=MUTED,
                    anchor="end",
                ),
            ]
        )
    fields = [
        ("strict_pass_rate", STRICT),
        ("isolated_pass_rate", ISOLATED),
        ("core_pass_rate", CORE),
    ]
    for field, field_color in fields:
        points_with_indexes: list[tuple[float, float, int]] = []
        for index, record in enumerate(records):
            point_x = plot_x + index * plot_width / max(1, len(records) - 1)
            point_y = plot_y + plot_height * (1 - float(record[field]))
            points_with_indexes.append((point_x, point_y, index))
        points = [
            (point_x, point_y)
            for point_x, point_y, _ in points_with_indexes
        ]
        svg.append(
            f'<path d="{path_from(points)}" fill="none" '
            f'stroke="{field_color}" stroke-width="3.5" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for point_x, point_y, index in points_with_indexes:
            solved = records[index][field] == 1
            radius = 5.5 if solved else 4.0
            svg.append(
                f'<circle cx="{point_x:.1f}" cy="{point_y:.1f}" '
                f'r="{radius}" fill="{field_color}" '
                f'stroke="{PANEL}" stroke-width="2"/>'
            )
    for index, record in enumerate(records):
        point_x = plot_x + index * plot_width / max(1, len(records) - 1)
        svg.append(
            svg_text(
                point_x,
                y + height - 13,
                f"C{record['idx']}",
                size=11,
                fill=MUTED,
                anchor="middle",
            )
        )


def render_qwen_trajectory(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
    width = 1600
    height = 1220
    title = "Strong starts rarely survived the full trajectory"
    svg = svg_start(width, height, title)
    svg.extend(
        [
            svg_text(80, 72, title, size=36, weight=750),
            svg_text(
                80,
                108,
                "Pass rate at every checkpoint; larger dots mark an exact 100% solve.",
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
            ("Core contract", CORE),
        ],
        x=820,
        y=78,
        step=225,
    )
    for index, problem in enumerate(QWEN_DISPLAY_NAMES):
        row = index // 2
        column = index % 2
        add_qwen_rate_panel(
            svg,
            groups[problem],
            x=60 + column * 760,
            y=145 + row * 250,
            width=720,
            height=220,
        )
    svg.append(
        svg_text(
            800,
            1180,
            "Five checkpoints passed strictly; no problem’s final checkpoint did.",
            size=16,
            fill=MUTED,
            anchor="middle",
        )
    )
    write_svg(spec.image_path("trajectory"), svg)


def render_qwen_efficiency(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
    width = 1600
    height = 990
    title = "Nearly half the spend went to one trajectory"
    svg = svg_start(width, height, title)
    all_records = [record for records in groups.values() for record in records]
    rows = sorted(
        groups.items(),
        key=lambda item: sum(record["cost"] for record in item[1]),
        reverse=True,
    )
    svg.extend(
        [
            svg_text(80, 72, title, size=36, weight=750),
            svg_text(
                80,
                108,
                (
                    "Billed API cost; time is summed within each sequential "
                    "problem trajectory."
                ),
                size=18,
                fill=MUTED,
            ),
        ]
    )
    plot_x = 350
    plot_width = 850
    max_cost = 16
    for tick in range(0, max_cost + 1, 4):
        tick_x = plot_x + plot_width * tick / max_cost
        svg.extend(
            [
                (
                    f'<line x1="{tick_x:.1f}" y1="150" '
                    f'x2="{tick_x:.1f}" y2="850" '
                    f'stroke="{GRID}" stroke-width="1"/>'
                ),
                svg_text(
                    tick_x,
                    880,
                    f"${tick}",
                    size=13,
                    fill=MUTED,
                    anchor="middle",
                ),
            ]
        )
    for index, (problem, records) in enumerate(rows):
        y = 175 + index * 84
        cost = sum(record["cost"] for record in records)
        minutes = sum(record["duration"] for record in records) / 60
        strict = sum(record["strict_pass_rate"] == 1 for record in records)
        bar_width = plot_width * cost / max_cost
        svg.extend(
            [
                svg_text(
                    80,
                    y + 27,
                    QWEN_DISPLAY_NAMES[problem],
                    size=17,
                    weight=650,
                ),
                (
                    f'<rect x="{plot_x}" y="{y}" width="{plot_width}" '
                    f'height="38" rx="10" fill="{PANEL}"/>'
                ),
                (
                    f'<rect x="{plot_x}" y="{y}" width="{bar_width:.1f}" '
                    f'height="38" rx="10" '
                    f'fill="{QWEN_PROBLEM_COLORS[problem]}"/>'
                ),
                svg_text(
                    1235,
                    y + 27,
                    (
                        f"${cost:.2f}  ·  {minutes / 60:.1f}h  ·  "
                        f"{strict}/{len(records)} strict"
                    ),
                    size=15,
                    fill=MUTED,
                ),
            ]
        )

    total_cost = sum(record["cost"] for record in all_records)
    summed_hours = sum(record["duration"] for record in all_records) / 3600
    total_steps = sum(record["steps"] for record in all_records)
    output_tokens = sum(record["output"] for record in all_records)
    svg.extend(
        [
            (
                '<rect x="80" y="910" width="1440" height="58" '
                f'rx="16" fill="{PANEL}"/>'
            ),
            svg_text(115, 947, f"API cost  ${total_cost:.2f}", size=17, weight=700),
            svg_text(
                430,
                947,
                f"Summed agent time  {summed_hours:.1f}h",
                size=17,
                weight=700,
            ),
            svg_text(850, 947, f"Agent steps  {total_steps:,}", size=17, weight=700),
            svg_text(
                1180,
                947,
                f"Output tokens  {output_tokens / 1_000_000:.2f}M",
                size=17,
                weight=700,
            ),
        ]
    )
    write_svg(spec.image_path("efficiency"), svg)


def render_qwen_code_health(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
    width = 1600
    height = 1070
    title = "More checkpoints brought much more code—and complexity"
    svg = svg_start(width, height, title)
    first_records = [records[0] for records in groups.values()]
    final_records = [records[-1] for records in groups.values()]
    first_loc = sum(record["loc"] for record in first_records)
    final_loc = sum(record["loc"] for record in final_records)
    first_high = sum(record["cc_high_count"] for record in first_records)
    final_high = sum(record["cc_high_count"] for record in final_records)
    max_cc = max(record["cc_max"] for records in groups.values() for record in records)
    svg.extend(
        [
            svg_text(80, 72, title, size=36, weight=750),
            svg_text(
                80,
                108,
                "First-to-final source volume and maximum cyclomatic complexity.",
                size=18,
                fill=MUTED,
            ),
        ]
    )
    summary = [
        ("Combined LOC", f"{first_loc:,} → {final_loc:,}"),
        ("Growth", f"+{(final_loc / first_loc - 1):.0%}"),
        ("High-CC functions", f"{first_high} → {final_high}"),
        ("Peak CC", str(max_cc)),
    ]
    for index, (label, value) in enumerate(summary):
        x = 80 + index * 365
        svg.extend(
            [
                (
                    f'<rect x="{x}" y="142" width="340" height="108" '
                    f'rx="18" fill="{PANEL}"/>'
                ),
                svg_text(x + 22, 176, label, size=14, fill=MUTED),
                svg_text(x + 22, 222, value, size=29, weight=750),
            ]
        )

    maximum_loc = max(record["loc"] for record in final_records)
    plot_x = 355
    plot_width = 850
    svg.extend(
        [
            svg_text(80, 293, "Problem", size=14, fill=MUTED, weight=650),
            svg_text(355, 293, "Lines of code", size=14, fill=MUTED, weight=650),
            svg_text(1290, 293, "Max CC", size=14, fill=MUTED, weight=650),
        ]
    )
    for index, problem in enumerate(QWEN_DISPLAY_NAMES):
        records = groups[problem]
        first = records[0]
        final = records[-1]
        y = 325 + index * 82
        first_width = plot_width * first["loc"] / maximum_loc
        final_width = plot_width * final["loc"] / maximum_loc
        growth = (
            f"{final['loc'] / first['loc']:.1f}×"
            if first["loc"]
            else "new"
        )
        label_inside = final_width > 700
        label_x = (
            plot_x + final_width - 16
            if label_inside
            else plot_x + final_width + 12
        )
        color = QWEN_PROBLEM_COLORS[problem]
        svg.extend(
            [
                svg_text(
                    80,
                    y + 29,
                    QWEN_DISPLAY_NAMES[problem],
                    size=16,
                    weight=650,
                ),
                (
                    f'<rect x="{plot_x}" y="{y + 4}" '
                    f'width="{first_width:.1f}" height="12" rx="6" '
                    f'fill="{MUTED}" opacity="0.62"/>'
                ),
                (
                    f'<rect x="{plot_x}" y="{y + 23}" '
                    f'width="{final_width:.1f}" height="23" rx="7" '
                    f'fill="{color}"/>'
                ),
                svg_text(
                    label_x,
                    y + 42,
                    (
                        f"{first['loc']:,} → {final['loc']:,}  "
                        f"({growth})"
                    ),
                    size=13,
                    fill=BACKGROUND if label_inside else color,
                    weight=700,
                    anchor="end" if label_inside else "start",
                ),
                svg_text(
                    1290,
                    y + 32,
                    f"{first['cc_max']} → {final['cc_max']}",
                    size=17,
                    fill=STRICT if final["cc_max"] > 30 else TEXT,
                    weight=700,
                ),
            ]
        )
    svg.extend(
        [
            svg_text(355, 1014, "first checkpoint", size=13, fill=MUTED),
            (
                f'<rect x="319" y="1003" width="24" height="10" '
                f'rx="5" fill="{MUTED}" opacity="0.62"/>'
            ),
            svg_text(605, 1014, "final checkpoint", size=13, fill=MUTED),
            (
                f'<rect x="569" y="1000" width="24" height="16" '
                f'rx="5" fill="{CORE}"/>'
            ),
            svg_text(
                1520,
                1014,
                "CC > 30 is highlighted",
                size=13,
                fill=MUTED,
                anchor="end",
            ),
        ]
    )
    write_svg(spec.image_path("code-health"), svg)


def add_comparison_panel(
    svg: list[str],
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    subtitle: str,
    rows: list[tuple[str, int, int, str]],
) -> None:
    svg.extend(
        [
            (
                f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                f'rx="22" fill="{PANEL}"/>'
            ),
            svg_text(x + 28, y + 43, title, size=21, weight=750),
            svg_text(x + 28, y + 72, subtitle, size=14, fill=MUTED),
        ]
    )
    plot_x = x + 305
    plot_width = width - 345
    top = y + 116
    row_bottom = y + height - 105
    axis_y = y + height - 50
    for percent in (0, 10, 20, 30, 40):
        tick_x = plot_x + plot_width * percent / 40
        svg.extend(
            [
                (
                    f'<line x1="{tick_x:.1f}" y1="{top - 16}" '
                    f'x2="{tick_x:.1f}" y2="{axis_y}" '
                    f'stroke="{GRID}" stroke-width="1"/>'
                ),
                svg_text(
                    tick_x,
                    axis_y + 25,
                    f"{percent}%",
                    size=12,
                    fill=MUTED,
                    anchor="middle",
                ),
            ]
        )
    row_gap = (row_bottom - top) / max(1, len(rows) - 1)
    for index, (label, solved, total, source) in enumerate(rows):
        row_y = top + index * row_gap
        rate = solved / total
        color = {
            "qwen": ISOLATED,
            "local": VERBOSITY,
            "external": "#64748b",
        }[source]
        svg.extend(
            [
                svg_text(
                    x + 28,
                    row_y + 18,
                    label,
                    size=14,
                    fill=TEXT if source == "qwen" else MUTED,
                    weight=700 if source == "qwen" else 500,
                ),
                (
                    f'<rect x="{plot_x}" y="{row_y}" width="{plot_width}" '
                    f'height="27" rx="8" fill="{BACKGROUND}"/>'
                ),
                (
                    f'<rect x="{plot_x}" y="{row_y}" '
                    f'width="{plot_width * rate / 0.4:.1f}" '
                    f'height="27" rx="8" fill="{color}"/>'
                ),
                svg_text(
                    x + width - 26,
                    row_y + 19,
                    f"{solved}/{total}  {rate:.1%}",
                    size=13,
                    fill=color,
                    weight=750,
                    anchor="end",
                ),
            ]
        )


def load_qwen_comparisons(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    data = json.loads((spec.data_path / "comparisons.json").read_text())
    subsets: list[dict[str, Any]] = []
    for subset in data["subsets"]:
        records = subset_records(groups, set(subset["problems"]))
        qwen_strict, _, _ = exact_summary(records)
        rows = []
        for row in subset["rows"]:
            solved = qwen_strict if row["source"] == "qwen" else row["solved"]
            total = len(records) if row["source"] == "qwen" else row["total"]
            rows.append((row["label"], solved, total, row["source"]))
        subsets.append(
            {
                "title": subset["title"],
                "subtitle": subset["subtitle"],
                "rows": rows,
            }
        )
    return subsets


def render_qwen_comparison(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
    width = 1600
    height = 1000
    title = "Related problem lists, different system scores"
    svg = svg_start(width, height, title)
    svg.extend(
        [
            svg_text(80, 72, title, size=36, weight=750),
            svg_text(
                80,
                108,
                (
                    "Strict checkpoints solved: every current and inherited "
                    "test passed."
                ),
                size=18,
                fill=MUTED,
            ),
        ]
    )
    left, right = load_qwen_comparisons(spec, groups)
    add_comparison_panel(
        svg,
        x=60,
        y=150,
        width=720,
        height=710,
        title=left["title"],
        subtitle=left["subtitle"],
        rows=left["rows"],
    )
    add_comparison_panel(
        svg,
        x=820,
        y=150,
        width=720,
        height=710,
        title=right["title"],
        subtitle=right["subtitle"],
        rows=right["rows"],
    )
    legend = [
        ("This Qwen run", ISOLATED),
        ("Reports in this repository", VERBOSITY),
        ("HumanLayer reports", "#64748b"),
    ]
    cursor = 230
    for label, color in legend:
        svg.extend(
            [
                f'<rect x="{cursor}" y="900" width="18" height="18" '
                f'rx="5" fill="{color}"/>',
                svg_text(cursor + 29, 915, label, size=14, fill=MUTED),
            ]
        )
        cursor += 390
    svg.append(
        svg_text(
            800,
            960,
            (
                "Single trajectories; models, agents, serving stacks and benchmark "
                "revisions differ. Directional comparison only."
            ),
            size=15,
            fill=MUTED,
            anchor="middle",
        )
    )
    write_svg(spec.image_path("comparison"), svg)


def render_qwen_charts(
    spec: RunSpec,
    groups: dict[str, list[dict[str, Any]]],
) -> None:
    render_qwen_scorecard(spec, groups)
    render_qwen_trajectory(spec, groups)
    render_qwen_efficiency(spec, groups)
    render_qwen_code_health(spec, groups)
    render_qwen_comparison(spec, groups)


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
    if spec.kind == "qwen":
        render_qwen_charts(spec, groups)
        return
    render_scorecard(spec, groups)
    render_correctness(spec, groups)
    render_quality(spec, groups)
    render_code_growth(spec, groups)
    if spec.termination_runs:
        render_termination(spec, groups)


if __name__ == "__main__":
    main()
