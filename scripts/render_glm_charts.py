#!/usr/bin/env python3
"""Render the GLM-5.3 report data and figures with the standard library."""

from __future__ import annotations

import csv
import html
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "images"
DEFAULT_DATA = ROOT / "data" / "glm-5.3-pi-xhigh-2026-08-19"

BG = "#0d1117"
PANEL = "#151b23"
RULE = "#303844"
TEXT = "#f2efe7"
MUTED = "#a6afbb"
STRICT = "#ff8066"
ISOLATED = "#69c9be"
CORE = "#bfd36b"
BAR_BG = "#252c36"
FONT = "Geist, Avenir Next, ui-sans-serif, system-ui, sans-serif"

CHECKPOINT_FIELDS = [
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
    "cache_read_tokens",
    "output_tokens",
    "reasoning_tokens",
    "loc",
    "functions",
    "cc_max",
    "verbosity",
    "erosion",
    "cloned_pct",
]

PROBLEM_FIELDS = [
    "problem",
    "checkpoints",
    "strict_solved",
    "isolated_solved",
    "core_solved",
    "strict_rate",
    "isolated_rate",
    "core_rate",
    "final_passed_tests",
    "final_total_tests",
    "final_pass_rate",
    "cost",
    "duration_seconds",
    "steps",
    "output_tokens",
    "first_loc",
    "final_loc",
    "peak_cc",
]

PHASE_FIELDS = [
    "phase",
    "checkpoint_instances",
    "strict_solved",
    "isolated_solved",
    "core_solved",
    "strict_rate",
    "isolated_rate",
    "core_rate",
]

DIFFICULTY_FIELDS = [
    "difficulty",
    "problems",
    "checkpoints",
    "strict_solved",
    "isolated_solved",
    "core_solved",
    "strict_rate",
    "isolated_rate",
    "core_rate",
    "mean_steps",
    "mean_duration_seconds",
    "cost",
]


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    return sorted(rows, key=lambda row: (row["problem"], row["idx"]))


def group_rows(
    rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["problem"]].append(row)
    return dict(grouped)


def exact(rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    fields = ("strict_pass_rate", "isolated_pass_rate", "core_pass_rate")
    return tuple(sum(row[field] == 1 for row in rows) for field in fields)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"invalid dataset: {message}")


def validate_dataset(
    data_dir: Path,
    rows: list[dict[str, Any]],
    grouped: dict[str, list[dict[str, Any]]],
) -> None:
    keys = [(str(row["problem"]), int(row["idx"])) for row in rows]
    require(len(set(keys)) == len(keys), "duplicate checkpoint key")
    require(len(rows) == 196, f"expected 196 checkpoints, found {len(rows)}")
    require(len(grouped) == 36, f"expected 36 problems, found {len(grouped)}")

    for problem, problem_rows in grouped.items():
        indexes = [int(row["idx"]) for row in problem_rows]
        require(
            indexes == list(range(1, len(problem_rows) + 1)),
            f"{problem} has non-contiguous checkpoint indexes",
        )
        require(
            sum(bool(row["is_first"]) for row in problem_rows) == 1
            and bool(problem_rows[0]["is_first"]),
            f"{problem} has invalid first-checkpoint flags",
        )
        require(
            sum(bool(row["is_last"]) for row in problem_rows) == 1
            and bool(problem_rows[-1]["is_last"]),
            f"{problem} has invalid final-checkpoint flags",
        )
        for row in problem_rows:
            index = int(row["idx"])
            require(
                row["checkpoint"] == f"checkpoint_{index}",
                f"{problem} checkpoint name/index mismatch",
            )
            require(row["state"] == "ran", f"{problem} C{index} did not run")
            total = (
                row["core_total"]
                + row["functionality_total"]
                + row["error_total"]
                + row["regression_total"]
            )
            passed = (
                row["core_passed"]
                + row["functionality_passed"]
                + row["error_passed"]
                + row["regression_passed"]
            )
            isolated_total = total - row["regression_total"]
            isolated_passed = passed - row["regression_passed"]
            require(total == row["total_tests"], f"{problem} C{index} test total")
            require(passed == row["passed_tests"], f"{problem} C{index} pass total")
            rates = (
                (row["strict_pass_rate"], passed / total, "strict"),
                (
                    row["isolated_pass_rate"],
                    isolated_passed / isolated_total,
                    "isolated",
                ),
                (
                    row["core_pass_rate"],
                    row["core_passed"] / row["core_total"],
                    "core",
                ),
            )
            for actual, expected, label in rates:
                require(
                    abs(actual - expected) < 1e-12,
                    f"{problem} C{index} {label} rate",
                )

    with (data_dir / "problem_metadata.csv").open(newline="") as handle:
        problem_metadata = list(csv.DictReader(handle))
    problem_keys = {row["problem"] for row in problem_metadata}
    require(
        len(problem_metadata) == len(problem_keys),
        "duplicate problem metadata key",
    )
    require(problem_keys == set(grouped), "problem metadata key mismatch")
    with (data_dir / "checkpoint_metadata.csv").open(newline="") as handle:
        checkpoint_metadata = list(csv.DictReader(handle))
    metadata_keys = {
        (row["problem"], int(row["checkpoint"]))
        for row in checkpoint_metadata
    }
    require(
        len(checkpoint_metadata) == len(metadata_keys),
        "duplicate checkpoint metadata key",
    )
    require(metadata_keys == set(keys), "checkpoint metadata key mismatch")

    result = json.loads((data_dir / "result.json").read_text())
    strict, isolated, core = exact(rows)
    require(result["num_checkpoints"] == len(rows), "aggregate checkpoint count")
    require(result["num_problems"] == len(grouped), "aggregate problem count")
    require(result["checkpoints_solved"] == strict, "aggregate strict count")
    require(
        result["checkpoints_iso_solved"] == isolated,
        "aggregate isolated count",
    )
    require(result["checkpoints_core_solved"] == core, "aggregate core count")
    require(
        abs(result["costs"]["total"] - sum(row["cost"] for row in rows))
        < 1e-9,
        "aggregate cost",
    )


def subset(
    grouped: dict[str, list[dict[str, Any]]], names: set[str]
) -> list[dict[str, Any]]:
    return [
        row
        for problem, rows in grouped.items()
        if problem in names
        for row in rows
    ]


def write_derived_data(
    data_dir: Path,
    rows: list[dict[str, Any]],
    grouped: dict[str, list[dict[str, Any]]],
) -> None:
    with (data_dir / "checkpoints.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=CHECKPOINT_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "problem": row["problem"],
                    "checkpoint": row["idx"],
                    "strict_solved": row["strict_pass_rate"] == 1,
                    "isolated_solved": row["isolated_pass_rate"] == 1,
                    "core_solved": row["core_pass_rate"] == 1,
                    "passed_tests": row["passed_tests"],
                    "total_tests": row["total_tests"],
                    "total_pass_rate": row["strict_pass_rate"],
                    "isolated_pass_rate": row["isolated_pass_rate"],
                    "core_pass_rate": row["core_pass_rate"],
                    "cost": row["cost"],
                    "duration_seconds": row["duration"],
                    "steps": row["steps"],
                    "input_tokens": row["input"],
                    "cache_read_tokens": row["cache_read"],
                    "output_tokens": row["output"],
                    "reasoning_tokens": row.get("reasoning", 0),
                    "loc": row["loc"],
                    "functions": row["functions"],
                    "cc_max": row["cc_max"],
                    "verbosity": row.get("verbosity"),
                    "erosion": row.get("erosion"),
                    "cloned_pct": row.get("cloned_pct"),
                }
            )

    with (data_dir / "problems.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=PROBLEM_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        for problem, problem_rows in grouped.items():
            strict, isolated, core = exact(problem_rows)
            final = problem_rows[-1]
            writer.writerow(
                {
                    "problem": problem,
                    "checkpoints": len(problem_rows),
                    "strict_solved": strict,
                    "isolated_solved": isolated,
                    "core_solved": core,
                    "strict_rate": strict / len(problem_rows),
                    "isolated_rate": isolated / len(problem_rows),
                    "core_rate": core / len(problem_rows),
                    "final_passed_tests": final["passed_tests"],
                    "final_total_tests": final["total_tests"],
                    "final_pass_rate": final["strict_pass_rate"],
                    "cost": sum(row["cost"] for row in problem_rows),
                    "duration_seconds": sum(
                        row["duration"] for row in problem_rows
                    ),
                    "steps": sum(row["steps"] for row in problem_rows),
                    "output_tokens": sum(
                        row["output"] for row in problem_rows
                    ),
                    "first_loc": problem_rows[0]["loc"],
                    "final_loc": final["loc"],
                    "peak_cc": max(row["cc_max"] for row in problem_rows),
                }
            )

    phases = [
        ("first", lambda row: row["is_first"]),
        ("middle", lambda row: not row["is_first"] and not row["is_last"]),
        ("final", lambda row: row["is_last"]),
    ]
    with (data_dir / "phases.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=PHASE_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        for name, predicate in phases:
            phase_rows = [row for row in rows if predicate(row)]
            strict, isolated, core = exact(phase_rows)
            count = len(phase_rows)
            writer.writerow(
                {
                    "phase": name,
                    "checkpoint_instances": count,
                    "strict_solved": strict,
                    "isolated_solved": isolated,
                    "core_solved": core,
                    "strict_rate": strict / count,
                    "isolated_rate": isolated / count,
                    "core_rate": core / count,
                }
            )

    with (data_dir / "problem_metadata.csv").open(newline="") as handle:
        metadata = {
            item["problem"]: item for item in csv.DictReader(handle)
        }
    by_difficulty: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        difficulty = metadata[row["problem"]]["difficulty"]
        by_difficulty[difficulty].append(row)
    with (data_dir / "difficulty_summary.csv").open(
        "w", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=DIFFICULTY_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        for difficulty in ("easy", "medium", "hard"):
            difficulty_rows = by_difficulty[difficulty]
            strict, isolated, core = exact(difficulty_rows)
            count = len(difficulty_rows)
            writer.writerow(
                {
                    "difficulty": difficulty,
                    "problems": len(
                        {row["problem"] for row in difficulty_rows}
                    ),
                    "checkpoints": count,
                    "strict_solved": strict,
                    "isolated_solved": isolated,
                    "core_solved": core,
                    "strict_rate": strict / count,
                    "isolated_rate": isolated / count,
                    "core_rate": core / count,
                    "mean_steps": sum(
                        row["steps"] for row in difficulty_rows
                    )
                    / count,
                    "mean_duration_seconds": sum(
                        row["duration"] for row in difficulty_rows
                    )
                    / count,
                    "cost": sum(row["cost"] for row in difficulty_rows),
                }
            )


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def text(
    x: float,
    y: float,
    value: object,
    *,
    size: int = 18,
    fill: str = TEXT,
    weight: int = 400,
    anchor: str = "start",
    spacing: float | None = None,
) -> str:
    extra = ""
    if spacing is not None:
        extra = f' letter-spacing="{spacing:.2f}"'
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" '
        f'font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}" font-variant-numeric="tabular-nums"'
        f'{extra}>{esc(value)}</text>'
    )


def start(width: int, height: int, title: str) -> list[str]:
    return [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{esc(title)}">'
        ),
        f"<title>{esc(title)}</title>",
        f'<rect width="{width}" height="{height}" fill="{BG}"/>',
    ]


def save(name: str, svg: list[str]) -> None:
    IMAGES.mkdir(exist_ok=True)
    svg.append("</svg>")
    (IMAGES / name).write_text("\n".join(svg) + "\n")


def rule(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: str = RULE,
    width: float = 1,
) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" '
        f'y2="{y2:.1f}" stroke="{color}" stroke-width="{width:.1f}"/>'
    )


def bar(
    x: float,
    y: float,
    width: float,
    height: float,
    rate: float,
    color: str,
    *,
    radius: int = 5,
) -> list[str]:
    fill_width = width * max(0, min(1, rate))
    return [
        (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" '
            f'height="{height:.1f}" rx="{radius}" fill="{BAR_BG}"/>'
        ),
        (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{fill_width:.1f}" '
            f'height="{height:.1f}" rx="{radius}" fill="{color}"/>'
        ),
    ]


def heading(
    svg: list[str], title: str, subtitle: str, *, width: int = 1600
) -> None:
    svg.extend(
        [
            text(70, 70, title, size=36, weight=720),
            text(70, 108, subtitle, size=18, fill=MUTED),
            rule(70, 132, width - 70, 132),
        ]
    )


def render_scorecard(
    rows: list[dict[str, Any]],
    grouped: dict[str, list[dict[str, Any]]],
) -> None:
    title = "GLM-5.3 on the full SlopCodeBench catalogue"
    svg = start(1600, 570, title)
    heading(
        svg,
        title,
        "36 cumulative trajectories · 196 checkpoints · pi 0.84.2 · xhigh",
    )
    strict, isolated, core = exact(rows)
    count = len(rows)
    total_cost = sum(row["cost"] for row in rows)
    total_hours = sum(row["duration"] for row in rows) / 3600
    full = sum(
        all(row["strict_pass_rate"] == 1 for row in problem_rows)
        for problem_rows in grouped.values()
    )
    partial = sum(
        any(row["strict_pass_rate"] == 1 for row in problem_rows)
        for problem_rows in grouped.values()
    )

    svg.extend(
        [
            text(70, 200, "STRICT CHECKPOINTS", size=14, fill=MUTED,
                 weight=650, spacing=1.4),
            text(70, 306, f"{strict}", size=112, fill=STRICT, weight=740),
            text(225, 300, f"/ {count}", size=38, fill=MUTED, weight=550),
            text(72, 348, f"{strict / count:.1%} exact", size=22, weight=650),
            text(72, 386, "Every test configured for the evaluation passed.",
                 size=16, fill=MUTED),
        ]
    )

    metrics = [
        ("Core contract", core, CORE),
        ("Current checkpoint", isolated, ISOLATED),
        ("All configured tests", strict, STRICT),
    ]
    for index, (label, solved, color) in enumerate(metrics):
        y = 190 + index * 78
        svg.extend(
            [
                text(560, y + 23, label, size=17, weight=620),
                *bar(790, y, 600, 31, solved / count, color, radius=8),
                text(
                    1510,
                    y + 23,
                    f"{solved}/{count}  {solved / count:.1%}",
                    size=17,
                    fill=color,
                    weight=700,
                    anchor="end",
                ),
            ]
        )

    stats = [
        ("Full problems", f"{full}/36"),
        ("Problems with a strict pass", f"{partial}/36"),
        ("Billed API cost", f"${total_cost:.2f}"),
        ("Summed agent time", f"{total_hours:.1f}h"),
    ]
    for index, (label, value) in enumerate(stats):
        x = 560 + index * 245
        svg.extend(
            [
                text(x, 430, label, size=13, fill=MUTED),
                text(x, 468, value, size=25, weight=690),
            ]
        )

    svg.extend(
        [
            rule(70, 510, 1530, 510),
            text(
                70,
                545,
                "Strict means all configured tests; 12 evaluations omitted prior tests.",
                size=15,
                fill=MUTED,
            ),
        ]
    )
    save("glm-5.3-pi-scorecard.svg", svg)


def problem_summary(
    problem: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    strict, isolated, core = exact(rows)
    return {
        "problem": problem,
        "rows": rows,
        "count": len(rows),
        "strict": strict,
        "isolated": isolated,
        "core": core,
        "final": rows[-1]["strict_pass_rate"],
    }


def mini_metric(
    svg: list[str],
    x: float,
    y: float,
    solved: int,
    total: int,
    color: str,
) -> None:
    svg.extend(
        [
            text(x, y, f"{solved}/{total}", size=17, fill=color,
                 weight=680),
            *bar(x, y + 11, 92, 7, solved / total, color, radius=3),
        ]
    )


def render_landscape(grouped: dict[str, list[dict[str, Any]]]) -> None:
    title = "Exact checkpoint solves across all 36 problems"
    width = 1200
    height = 2500
    svg = start(width, height, title)
    heading(
        svg,
        title,
        "Sorted by strict rate, strict count, then core rate; final is total test pass.",
        width=width,
    )
    summaries = [
        problem_summary(problem, rows) for problem, rows in grouped.items()
    ]
    summaries.sort(
        key=lambda item: (
            item["strict"] / item["count"],
            item["strict"],
            item["core"] / item["count"],
            item["final"],
        ),
        reverse=True,
    )

    panel_x = 60
    svg.extend(
        [
            text(panel_x, 176, "PROBLEM", size=14, fill=MUTED,
                 weight=650, spacing=1.1),
            text(410, 176, "N", size=14, fill=MUTED,
                 weight=650, anchor="end", spacing=1.1),
            text(470, 176, "STRICT", size=14, fill=STRICT,
                 weight=650, spacing=0.8),
            text(620, 176, "ISOLATED", size=14, fill=ISOLATED,
                 weight=650, spacing=0.8),
            text(770, 176, "CORE", size=14, fill=CORE,
                 weight=650, spacing=0.8),
            text(1140, 176, "FINAL", size=14, fill=MUTED,
                 weight=650, anchor="end", spacing=0.8),
            rule(panel_x, 194, 1140, 194),
        ]
    )
    for row_index, item in enumerate(summaries):
        y = 232 + row_index * 61
        svg.extend(
            [
                text(panel_x, y, item["problem"], size=18, weight=620),
                text(410, y, item["count"], size=17, fill=MUTED,
                     anchor="end"),
            ]
        )
        mini_metric(
            svg, 470, y, item["strict"], item["count"], STRICT
        )
        mini_metric(
            svg, 620, y, item["isolated"], item["count"], ISOLATED
        )
        mini_metric(svg, 770, y, item["core"], item["count"], CORE)
        svg.extend(
            [
                text(
                    1140,
                    y,
                    f"{item['final']:.1%}",
                    size=18,
                    fill=TEXT if item["final"] >= 0.9 else MUTED,
                    weight=680,
                    anchor="end",
                ),
                rule(panel_x, y + 27, 1140, y + 27),
            ]
        )
    svg.extend(
        [
            text(60, 2460, "N = checkpoints in the cumulative trajectory.",
                 size=16, fill=MUTED),
            text(
                1140,
                2460,
                "Exact requires 100%; lower final rates are not strict passes.",
                size=16,
                fill=MUTED,
                anchor="end",
            ),
        ]
    )
    save("glm-5.3-pi-landscape.svg", svg)


def render_trajectory(rows: list[dict[str, Any]]) -> None:
    title = "Core completion stayed higher, but both measures declined"
    svg = start(1600, 930, title)
    heading(
        svg,
        title,
        "Exact solves by trajectory phase, followed by final total test-pass rates.",
    )
    phases = [
        ("First checkpoint", [row for row in rows if row["is_first"]]),
        (
            "Middle checkpoints",
            [
                row
                for row in rows
                if not row["is_first"] and not row["is_last"]
            ],
        ),
        ("Final checkpoint", [row for row in rows if row["is_last"]]),
    ]
    colors = [STRICT, ISOLATED, CORE]
    labels = ["Strict", "Isolated", "Core"]
    for index, (phase, phase_rows) in enumerate(phases):
        x = 70 + index * 500
        solved = exact(phase_rows)
        svg.extend(
            [
                text(x, 185, phase, size=21, weight=690),
                text(x, 214, f"{len(phase_rows)} checkpoint instances",
                     size=17, fill=MUTED),
            ]
        )
        for metric_index, (label, color) in enumerate(zip(labels, colors)):
            y = 255 + metric_index * 76
            rate = solved[metric_index] / len(phase_rows)
            svg.extend(
                [
                    text(x, y, label, size=16, fill=MUTED),
                    *bar(x, y + 13, 330, 24, rate, color, radius=7),
                    text(
                        x + 420,
                        y + 34,
                        f"{solved[metric_index]}/{len(phase_rows)}  {rate:.1%}",
                        size=17,
                        fill=color,
                        weight=700,
                        anchor="end",
                    ),
                ]
            )

    svg.extend(
        [
            rule(70, 515, 1530, 515),
            text(70, 562, "FINAL TOTAL TEST-PASS RATE", size=14, fill=MUTED,
                 weight=650, spacing=1.4),
            text(70, 595, "Near-perfect still fails the strict threshold.",
                 size=18, weight=620),
        ]
    )
    final_rows = [row for row in rows if row["is_last"]]
    near_final = [
        row for row in final_rows if row["strict_pass_rate"] >= 0.95
    ]
    closest = max(final_rows, key=lambda row: row["strict_pass_rate"])
    bins = [
        ("100%", lambda value: value == 1),
        ("95–<100%", lambda value: 0.95 <= value < 1),
        ("90–<95%", lambda value: 0.90 <= value < 0.95),
        ("75–<90%", lambda value: 0.75 <= value < 0.90),
        ("<75%", lambda value: value < 0.75),
    ]
    counts = [
        sum(predicate(row["strict_pass_rate"]) for row in final_rows)
        for _, predicate in bins
    ]
    max_count = max(counts)
    chart_x = 70
    chart_y = 680
    chart_width = 1000
    chart_height = 150
    for tick in (0, 5, 10, 15):
        tick_y = chart_y + chart_height * (1 - tick / max_count)
        svg.extend(
            [
                rule(chart_x, tick_y, chart_x + chart_width, tick_y),
                text(chart_x - 12, tick_y + 5, tick, size=15, fill=MUTED,
                     anchor="end"),
            ]
        )
    bar_width = 125
    gap = 70
    for index, ((label, _), count) in enumerate(zip(bins, counts)):
        x = chart_x + 45 + index * (bar_width + gap)
        height = chart_height * count / max_count
        color = STRICT if index == 0 else ISOLATED if index == 1 else MUTED
        svg.extend(
            [
                (
                    f'<rect x="{x}" y="{chart_y + chart_height - height:.1f}" '
                    f'width="{bar_width}" height="{height:.1f}" rx="8" '
                    f'fill="{color}"/>'
                ),
                text(x + bar_width / 2, chart_y + chart_height - height - 12,
                     count, size=20, fill=color, weight=720,
                     anchor="middle"),
                text(x + bar_width / 2, chart_y + chart_height + 30,
                     label, size=16, fill=MUTED, anchor="middle"),
            ]
        )

    svg.extend(
        [
            text(
                1180,
                650,
                f"{len(near_final)} of {len(final_rows)}",
                size=52,
                fill=ISOLATED,
                weight=740,
            ),
            text(1180, 687, "final snapshots passed at least 95%", size=16,
                 weight=620),
            text(1180, 716, "but none passed every test.", size=16,
                 fill=MUTED),
            text(1180, 785, "Closest", size=16, fill=MUTED, weight=650,
                 spacing=1.0),
            text(1180, 820, closest["problem"], size=18, weight=680),
            text(
                1180,
                851,
                f"{closest['passed_tests']} / {closest['total_tests']} tests",
                size=18,
                fill=STRICT,
                weight=700,
            ),
            text(
                1530,
                900,
                "Middle checkpoints are repeated instances, not independent problems.",
                size=15,
                fill=MUTED,
                anchor="end",
            ),
        ]
    )
    save("glm-5.3-pi-trajectory.svg", svg)


def comparison_rows(
    data_dir: Path,
    grouped: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    data = json.loads((data_dir / "comparisons.json").read_text())
    output = []
    for comparison in data["subsets"]:
        run_rows = subset(grouped, set(comparison["problems"]))
        strict, _, _ = exact(run_rows)
        without_circuit = [
            row for row in run_rows if row["problem"] != "circuit_eval"
        ]
        without_circuit_strict, _, _ = exact(without_circuit)
        rows = []
        for row in comparison["rows"]:
            if row["source"] == "glm":
                row = {
                    **row,
                    "solved": strict,
                    "total": len(run_rows),
                    "without_circuit_solved": without_circuit_strict,
                    "without_circuit_total": len(without_circuit),
                }
            rows.append(row)
        output.append({**comparison, "rows": rows})
    return output


def comparison_panel(
    svg: list[str],
    x: float,
    y: float,
    width: float,
    comparison: dict[str, Any],
) -> None:
    svg.extend(
        [
            text(x, y, comparison["title"], size=24, weight=700),
            text(x, y + 32, comparison["subtitle"], size=16, fill=MUTED),
        ]
    )
    plot_x = x + 285
    plot_width = width - 360
    top = y + 84
    row_gap = 68
    axis_bottom = top + row_gap * len(comparison["rows"]) + 8
    for tick in range(0, 51, 10):
        tick_x = plot_x + plot_width * tick / 50
        svg.extend(
            [
                rule(tick_x, top - 20, tick_x, axis_bottom),
                text(tick_x, axis_bottom + 24, f"{tick}%", size=14,
                     fill=MUTED, anchor="middle"),
            ]
        )
    source_colors = {
        "glm": STRICT,
        "qwen": ISOLATED,
        "local": "#d7a85c",
        "external": "#7f8a98",
    }
    for index, row in enumerate(comparison["rows"]):
        row_y = top + index * row_gap
        rate = row["solved"] / row["total"]
        color = source_colors[row["source"]]
        svg.extend(
            [
                text(x, row_y + 20, row["label"], size=16,
                     fill=TEXT if row["source"] == "glm" else MUTED,
                     weight=700 if row["source"] == "glm" else 520),
                *bar(plot_x, row_y, plot_width, 27, rate / 0.5, color,
                     radius=7),
                text(
                    x + width,
                    row_y + 20,
                    f"{row['solved']}/{row['total']}  {rate:.1%}",
                    size=15,
                    fill=color,
                    weight=700,
                    anchor="end",
                ),
            ]
        )
        if row["source"] == "glm":
            svg.append(
                text(
                    plot_x,
                    row_y + 48,
                    (
                        "without circuit_eval  "
                        f"{row['without_circuit_solved']}/"
                        f"{row['without_circuit_total']}"
                    ),
                    size=14,
                    fill=MUTED,
                    weight=620,
                )
            )


def render_comparison(
    data_dir: Path, grouped: dict[str, list[dict[str, Any]]]
) -> None:
    title = "circuit_eval lifts both GLM subset scores"
    svg = start(1600, 940, title)
    heading(
        svg,
        title,
        "Strict checkpoints solved; all bars share the same 0–50% scale.",
    )
    comparisons = comparison_rows(data_dir, grouped)
    comparison_panel(svg, 60, 185, 700, comparisons[0])
    comparison_panel(svg, 840, 185, 700, comparisons[1])
    svg.extend(
        [
            rule(800, 160, 800, 810),
            text(60, 850, "GLM-5.3 · this run", size=16, fill=STRICT,
                 weight=680),
            text(300, 850, "Qwen · same pi setup", size=16, fill=ISOLATED,
                 weight=680),
            text(575, 850, "Local reports", size=16, fill="#d7a85c",
                 weight=680),
            text(780, 850, "HumanLayer reports", size=16, fill="#7f8a98",
                 weight=680),
            text(
                800,
                900,
                "One trajectory per problem and model; agents, providers, dates and suite revisions differ.",
                size=16,
                fill=MUTED,
                anchor="middle",
            ),
        ]
    )
    save("glm-5.3-pi-comparison.svg", svg)


def main() -> None:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
    rows = load_rows(data_dir / "checkpoint_results.jsonl")
    grouped = group_rows(rows)
    validate_dataset(data_dir, rows, grouped)
    write_derived_data(data_dir, rows, grouped)
    render_scorecard(rows, grouped)
    render_landscape(grouped)
    render_trajectory(rows)
    render_comparison(data_dir, grouped)


if __name__ == "__main__":
    main()
