#!/usr/bin/env python3
"""Validate Ox Alpha report data and render its CSVs and SVG figures."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
IMAGES = ROOT / "images"
DEFAULT_DATA = DATA_ROOT / "ox-alpha-pi-xhigh-2026-08-20"

BG = "#11100e"
PANEL = "#191815"
RULE = "#34312b"
TEXT = "#f5f1e8"
MUTED = "#aaa397"
BAR_BG = "#292722"
STRICT = "#ef806d"
ISOLATED = "#73b6aa"
CORE = "#b5c774"
OX = "#e5a84b"
GLM = "#81a5bd"
QWEN = "#918d86"
FONT = "Geist, Avenir Next, ui-sans-serif, system-ui, sans-serif"

PROBLEM_ORDER = [
    "circuit_eval",
    "code_search",
    "database_migration",
    "xjq",
    "dynamic_config_service_api",
    "etl_pipeline",
    "file_backup",
    "dag_execution",
]
DISPLAY_NAMES = {
    "circuit_eval": "Circuit evaluator",
    "code_search": "Code search",
    "database_migration": "Database migration",
    "xjq": "xjq",
    "dynamic_config_service_api": "Dynamic config API",
    "etl_pipeline": "ETL pipeline",
    "file_backup": "File backup",
    "dag_execution": "DAG execution",
}

CHECKPOINT_FIELDS = [
    "problem",
    "checkpoint",
    "strict_solved",
    "isolated_solved",
    "core_solved",
    "passed_tests",
    "skipped_tests",
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
    "lines_added",
    "lines_removed",
    "loc",
    "functions",
    "cc_high_count",
    "cc_max",
    "verbosity",
    "erosion",
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
    "first_loc",
    "final_loc",
    "first_cc_max",
    "final_cc_max",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"invalid dataset: {message}")


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
        grouped[str(row["problem"])].append(row)
    return dict(grouped)


def exact(rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    fields = ("strict_pass_rate", "isolated_pass_rate", "core_pass_rate")
    return tuple(sum(row[field] == 1 for row in rows) for field in fields)


def validate_dataset(
    data_dir: Path,
    rows: list[dict[str, Any]],
    grouped: dict[str, list[dict[str, Any]]],
) -> None:
    keys = [(str(row["problem"]), int(row["idx"])) for row in rows]
    key_set = set(keys)
    result_by_key = dict(zip(keys, rows))
    require(len(rows) == 39, f"expected 39 checkpoints, found {len(rows)}")
    require(len(grouped) == 8, f"expected 8 problems, found {len(grouped)}")
    require(len(key_set) == len(keys), "duplicate checkpoint key")
    require(set(grouped) == set(PROBLEM_ORDER), "problem set mismatch")

    for problem, problem_rows in grouped.items():
        indexes = [int(row["idx"]) for row in problem_rows]
        require(
            indexes == list(range(1, len(problem_rows) + 1)),
            f"{problem} has non-contiguous checkpoint indexes",
        )
        for row in problem_rows:
            index = int(row["idx"])
            require(row["state"] == "ran", f"{problem} C{index} did not run")
            require(
                row["checkpoint"] == f"checkpoint_{index}",
                f"{problem} C{index} checkpoint name",
            )
            require(
                bool(row["is_first"]) == (index == 1),
                f"{problem} C{index} first marker",
            )
            require(
                bool(row["is_last"]) == (index == len(problem_rows)),
                f"{problem} C{index} final marker",
            )
            count_fields = (
                "core_total",
                "core_passed",
                "functionality_total",
                "functionality_passed",
                "error_total",
                "error_passed",
                "regression_total",
                "regression_passed",
            )
            require(
                all(row[field] >= 0 for field in count_fields),
                f"{problem} C{index} negative test count",
            )
            for category in ("core", "functionality", "error", "regression"):
                require(
                    row[f"{category}_passed"] <= row[f"{category}_total"],
                    f"{problem} C{index} {category} passed exceeds total",
                )
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
            require(total > 0, f"{problem} C{index} empty test suite")
            require(isolated_total > 0, f"{problem} C{index} empty current suite")
            require(row["core_total"] > 0, f"{problem} C{index} empty core")
            require(total == row["total_tests"], f"{problem} C{index} total")
            require(
                passed == row["passed_tests"], f"{problem} C{index} passed"
            )
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

    result = json.loads((data_dir / "result.json").read_text())
    strict, isolated, core = exact(rows)
    require(result["num_problems"] == len(grouped), "aggregate problems")
    require(result["num_checkpoints"] == len(rows), "aggregate checkpoints")
    require(result["expected_checkpoints"] == len(rows), "expected checkpoints")
    require(result["checkpoints_solved"] == strict, "aggregate strict")
    require(
        result["checkpoints_iso_solved"] == isolated,
        "aggregate isolated",
    )
    require(result["checkpoints_core_solved"] == core, "aggregate core")
    require(
        abs(result["costs"]["total"] - sum(row["cost"] for row in rows))
        < 1e-9,
        "aggregate cost",
    )

    with (data_dir / "checkpoint_metadata.csv").open(newline="") as handle:
        metadata = list(csv.DictReader(handle))
    metadata_keys = [
        (row["problem"], int(row["checkpoint"])) for row in metadata
    ]
    require(len(metadata_keys) == len(key_set), "checkpoint metadata count")
    require(len(set(metadata_keys)) == len(metadata_keys), "duplicate metadata")
    require(set(metadata_keys) == key_set, "checkpoint metadata keys")
    resets = {
        (row["problem"], int(row["checkpoint"]))
        for row in metadata
        if row["include_prior_tests"] == "false"
    }
    require(
        resets
        == {
            ("dynamic_config_service_api", 3),
            ("dynamic_config_service_api", 4),
        },
        "prior-test reset set",
    )

    with (data_dir / "problem_metadata.csv").open(newline="") as handle:
        problem_metadata = list(csv.DictReader(handle))
    problem_keys = [row["problem"] for row in problem_metadata]
    require(len(problem_keys) == len(grouped), "problem metadata count")
    require(len(set(problem_keys)) == len(problem_keys), "duplicate problem metadata")
    require(set(problem_keys) == set(grouped), "problem metadata keys")

    trajectories = [
        json.loads(line)
        for line in (data_dir / "trajectory.jsonl").read_text().splitlines()
        if line.strip()
    ]
    trajectory_keys = [
        (row["problem"], int(row["checkpoint"])) for row in trajectories
    ]
    require(len(trajectory_keys) == len(key_set), "trajectory count")
    require(
        len(set(trajectory_keys)) == len(trajectory_keys),
        "duplicate trajectory",
    )
    require(set(trajectory_keys) == key_set, "trajectory keys")
    no_change_keys = set()
    retry_count = 0
    for trajectory in trajectories:
        key = (trajectory["problem"], int(trajectory["checkpoint"]))
        source = result_by_key[key]
        require(trajectory["steps"] == source["steps"], f"{key} steps")
        require(
            abs(trajectory["elapsed"] - round(source["duration"], 3))
            < 1e-9,
            f"{key} elapsed",
        )
        require(
            trajectory["net_output_tokens"] == source["output"],
            f"{key} output tokens",
        )
        if not trajectory["files_changed"]:
            no_change_keys.add(key)
        retry_count += bool(trajectory["is_retry"])
    require(
        no_change_keys
        == {
            ("circuit_eval", 8),
            ("code_search", 4),
            ("database_migration", 5),
            ("file_backup", 4),
        },
        "no-change checkpoint set",
    )
    require(retry_count == 3, "retained retry count")

    diagnostics = [
        json.loads(line)
        for line in (data_dir / "diagnostics.jsonl").read_text().splitlines()
        if line.strip()
    ]
    diagnostic_keys = [
        (row["problem"], int(row["checkpoint"])) for row in diagnostics
    ]
    require(len(diagnostics) == 8, "diagnostic count")
    require(len(set(diagnostic_keys)) == len(diagnostic_keys), "diagnostics")
    require(set(diagnostic_keys) <= key_set, "diagnostic keys")
    require(
        all(row.get("observed") and row.get("examples") for row in diagnostics),
        "diagnostic content",
    )

    with (data_dir / "test_outcomes.csv").open(newline="") as handle:
        outcomes = list(csv.DictReader(handle))
    outcome_keys = [
        (row["problem"], int(row["checkpoint"])) for row in outcomes
    ]
    require(len(outcome_keys) == len(key_set), "test outcome count")
    require(len(set(outcome_keys)) == len(outcome_keys), "duplicate test outcome")
    require(set(outcome_keys) == key_set, "test outcome keys")
    skipped = 0
    for outcome in outcomes:
        key = (outcome["problem"], int(outcome["checkpoint"]))
        passed = int(outcome["passed"])
        failed = int(outcome["failed"])
        skip_count = int(outcome["skipped"])
        total = int(outcome["total"])
        require(passed + failed + skip_count == total, f"{key} outcomes")
        require(passed == result_by_key[key]["passed_tests"], f"{key} passed")
        require(total == result_by_key[key]["total_tests"], f"{key} total")
        skipped += skip_count
    require(skipped == 63, "aggregate skipped outcomes")

    catalog = json.loads((data_dir / "problem_catalog.json").read_text())
    manifest = json.loads((data_dir / "source_manifest.json").read_text())
    require(manifest["problem_catalog"] == catalog, "manifest catalogue")
    require(
        manifest["totals"]["problems"] == len(grouped),
        "manifest problems",
    )
    require(
        manifest["totals"]["checkpoints"] == len(rows),
        "manifest checkpoints",
    )

    require(manifest["launcher_record"] == "run.sh", "launcher record")
    require(manifest["lineage_file"] == "source_hashes.json", "lineage file")
    source_hashes = json.loads((data_dir / "source_hashes.json").read_text())
    require(source_hashes["algorithm"] == "sha256", "source hash algorithm")
    require(len(source_hashes["files"]) == 208, "source hash file count")
    for name in (
        "result.json",
        "checkpoint_results.jsonl",
        "environment.yaml",
        "problem_catalog.json",
    ):
        digest = hashlib.sha256((data_dir / name).read_bytes()).hexdigest()
        require(
            digest == source_hashes["files"][name]["sha256"],
            f"published source hash {name}",
        )


def write_derived_data(
    data_dir: Path,
    rows: list[dict[str, Any]],
    grouped: dict[str, list[dict[str, Any]]],
) -> None:
    with (data_dir / "test_outcomes.csv").open(newline="") as handle:
        outcomes = {
            (row["problem"], int(row["checkpoint"])): row
            for row in csv.DictReader(handle)
        }
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
                    "skipped_tests": outcomes[
                        (row["problem"], int(row["idx"]))
                    ]["skipped"],
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
                    "lines_added": row["lines_added"],
                    "lines_removed": row["lines_removed"],
                    "loc": row["loc"],
                    "functions": row["functions"],
                    "cc_high_count": row["cc_high_count"],
                    "cc_max": row["cc_max"],
                    "verbosity": row["verbosity"],
                    "erosion": row["erosion"],
                }
            )

    with (data_dir / "problems.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=PROBLEM_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        for problem in PROBLEM_ORDER:
            problem_rows = grouped[problem]
            strict, isolated, core = exact(problem_rows)
            final = problem_rows[-1]
            first = problem_rows[0]
            count = len(problem_rows)
            writer.writerow(
                {
                    "problem": problem,
                    "checkpoints": count,
                    "strict_solved": strict,
                    "isolated_solved": isolated,
                    "core_solved": core,
                    "strict_rate": strict / count,
                    "isolated_rate": isolated / count,
                    "core_rate": core / count,
                    "final_passed_tests": final["passed_tests"],
                    "final_total_tests": final["total_tests"],
                    "final_pass_rate": final["strict_pass_rate"],
                    "cost": sum(row["cost"] for row in problem_rows),
                    "duration_seconds": sum(
                        row["duration"] for row in problem_rows
                    ),
                    "steps": sum(row["steps"] for row in problem_rows),
                    "first_loc": first["loc"],
                    "final_loc": final["loc"],
                    "first_cc_max": first["cc_max"],
                    "final_cc_max": final["cc_max"],
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
        f'text-anchor="{anchor}" font-variant-numeric="tabular-nums" '
        f'text-rendering="optimizeLegibility"{extra}>{esc(value)}</text>'
    )


def start(
    width: int,
    height: int,
    title: str,
    description: str,
) -> list[str]:
    return [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" role="img" '
            'aria-labelledby="chart-title chart-description">'
        ),
        f'<title id="chart-title">{esc(title)}</title>',
        f'<desc id="chart-description">{esc(description)}</desc>',
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


def path_from(points: list[tuple[float, float]]) -> str:
    return " ".join(
        ("M" if index == 0 else "L") + f" {x:.1f} {y:.1f}"
        for index, (x, y) in enumerate(points)
    )


def render_scorecard(
    rows: list[dict[str, Any]],
    grouped: dict[str, list[dict[str, Any]]],
) -> None:
    title = "Ox Alpha on the 39-checkpoint SlopCodeBench union"
    svg = start(
        1600,
        640,
        title,
        (
            "Scorecard showing 7 of 39 strict, 10 isolated, and 21 core "
            "checkpoints solved; zero of eight problems were fully solved."
        ),
    )
    heading(
        svg,
        title,
        "Eight trajectories · pi 0.84.2 · xhigh configured · OpenRouter preview",
    )
    strict, isolated, core = exact(rows)
    count = len(rows)
    total_cost = sum(row["cost"] for row in rows)
    total_hours = sum(row["duration"] for row in rows) / 3600
    partial = sum(
        any(row["strict_pass_rate"] == 1 for row in problem_rows)
        for problem_rows in grouped.values()
    )

    svg.extend(
        [
            text(
                70,
                196,
                "STRICT CHECKPOINTS",
                size=14,
                fill=MUTED,
                weight=650,
                spacing=1.35,
            ),
            text(70, 325, strict, size=126, fill=OX, weight=760),
            text(205, 314, f"/ {count}", size=40, fill=MUTED, weight=570),
            text(72, 367, f"{strict / count:.1%} exact", size=23, weight=680),
            text(
                72,
                407,
                "No final checkpoint passed every configured test.",
                size=17,
                fill=MUTED,
            ),
            rule(470, 174, 470, 430),
        ]
    )

    metrics = [
        ("Core contract", core, CORE),
        ("Current checkpoint", isolated, ISOLATED),
        ("All configured tests", strict, STRICT),
    ]
    for index, (label, solved, color) in enumerate(metrics):
        y = 190 + index * 82
        svg.extend(
            [
                text(535, y + 24, label, size=17, weight=630),
                *bar(775, y, 570, 32, solved / count, color, radius=8),
                text(
                    1515,
                    y + 24,
                    f"{solved}/{count}  {solved / count:.1%}",
                    size=17,
                    fill=color,
                    weight=720,
                    anchor="end",
                ),
            ]
        )

    stats = [
        ("Problems with a strict pass", f"{partial}/8"),
        ("Fully solved problems", "0/8"),
        ("pi-recorded cost est.", f"${total_cost:.2f}"),
        ("Summed agent time", f"{total_hours:.1f}h"),
        ("Agent steps", f"{sum(row['steps'] for row in rows):,}"),
    ]
    svg.append(rule(70, 475, 1530, 475))
    for index, (label, value) in enumerate(stats):
        x = 70 + index * 292
        svg.extend(
            [
                text(x, 520, label, size=13, fill=MUTED),
                text(x, 558, value, size=25, weight=700),
            ]
        )
        if index:
            svg.append(rule(x - 25, 505, x - 25, 566))
    svg.extend(
        [
            rule(70, 596, 1530, 596),
            text(
                70,
                626,
                "Strict requires 100%; two dynamic-config evaluations did not automatically carry prior suites.",
                size=15,
                fill=MUTED,
            ),
        ]
    )
    save("ox-alpha-pi-scorecard.svg", svg)


def add_rate_panel(
    svg: list[str],
    problem_rows: list[dict[str, Any]],
    *,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    problem = str(problem_rows[0]["problem"])
    strict, isolated, core = exact(problem_rows)
    svg.extend(
        [
            (
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" '
                f'height="{height:.1f}" rx="12" fill="{PANEL}"/>'
            ),
            text(
                x + 23,
                y + 35,
                DISPLAY_NAMES[problem],
                size=18,
                weight=690,
            ),
            text(
                x + width - 23,
                y + 35,
                (
                    f"exact  {strict}/{len(problem_rows)} · "
                    f"{isolated}/{len(problem_rows)} · "
                    f"{core}/{len(problem_rows)}"
                ),
                size=13,
                fill=MUTED,
                anchor="end",
            ),
        ]
    )
    plot_x = x + 57
    plot_y = y + 58
    plot_width = width - 87
    plot_height = height - 100
    for percent in (0, 50, 100):
        grid_y = plot_y + plot_height * (1 - percent / 100)
        svg.extend(
            [
                rule(plot_x, grid_y, plot_x + plot_width, grid_y),
                text(
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
        ("strict_pass_rate", STRICT, None),
        ("isolated_pass_rate", ISOLATED, "10 6"),
        ("core_pass_rate", CORE, "2 5"),
    ]
    for field, color, dash in fields:
        points = []
        for index, row in enumerate(problem_rows):
            point_x = plot_x + index * plot_width / max(1, len(problem_rows) - 1)
            point_y = plot_y + plot_height * (1 - float(row[field]))
            points.append((point_x, point_y))
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        svg.append(
            f'<path d="{path_from(points)}" fill="none" '
            f'stroke="{color}" stroke-width="3.5"{dash_attribute} '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for index, (point_x, point_y) in enumerate(points):
            solved = problem_rows[index][field] == 1
            radius = 5.5 if solved else 3.8
            svg.append(
                f'<circle cx="{point_x:.1f}" cy="{point_y:.1f}" '
                f'r="{radius}" fill="{color}" stroke="{PANEL}" '
                'stroke-width="2"/>'
            )
    for index, row in enumerate(problem_rows):
        point_x = plot_x + index * plot_width / max(1, len(problem_rows) - 1)
        svg.append(
            text(
                point_x,
                y + height - 13,
                f"C{row['idx']}",
                size=11,
                fill=MUTED,
                anchor="middle",
            )
        )


def render_trajectory(grouped: dict[str, list[dict[str, Any]]]) -> None:
    title = "Exact starts, imperfect finishes"
    svg = start(
        1600,
        1210,
        title,
        (
            "Eight panels trace strict, isolated, and core pass rates by "
            "checkpoint. Four opening checkpoints passed strictly; no final "
            "checkpoint did."
        ),
    )
    heading(
        svg,
        title,
        "Pass rate at every checkpoint; larger dots mark an exact 100% solve.",
    )
    legend = [
        ("All tests", STRICT, None),
        ("Current checkpoint", ISOLATED, "10 6"),
        ("Core contract", CORE, "2 5"),
    ]
    cursor = 870
    for label, color, dash in legend:
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        svg.extend(
            [
                (
                    f'<line x1="{cursor}" y1="81" x2="{cursor + 31}" '
                    f'y2="81" stroke="{color}" stroke-width="4"'
                    f'{dash_attribute}/>'
                ),
                text(cursor + 42, 87, label, size=15, fill=MUTED),
            ]
        )
        cursor += 215

    for index, problem in enumerate(PROBLEM_ORDER):
        row = index // 2
        column = index % 2
        add_rate_panel(
            svg,
            grouped[problem],
            x=60 + column * 760,
            y=157 + row * 247,
            width=720,
            height=217,
        )
    svg.extend(
        [
            rule(60, 1162, 1540, 1162),
            text(
                60,
                1193,
                "Four of eight opening checkpoints passed strictly; none of the eight final checkpoints did.",
                size=16,
                fill=MUTED,
            ),
        ]
    )
    save("ox-alpha-pi-trajectory.svg", svg)


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
            text(x, y, f"{solved}/{total}", size=17, fill=color, weight=700),
            *bar(x, y + 11, 108, 8, solved / total, color, radius=4),
        ]
    )


def render_landscape(grouped: dict[str, list[dict[str, Any]]]) -> None:
    title = "Four trajectories never reached a strict pass"
    svg = start(
        1600,
        850,
        title,
        (
            "Per-problem table of exact strict, isolated, and core solves, "
            "final total test-pass rate, and pi-recorded cost estimate."
        ),
    )
    heading(
        svg,
        title,
        "Exact solves across each trajectory; final is the last snapshot’s total test-pass rate.",
    )
    headers = [
        (70, "PROBLEM", "start"),
        (425, "N", "end"),
        (495, "STRICT", "start"),
        (665, "ISOLATED", "start"),
        (835, "CORE", "start"),
        (1250, "FINAL", "end"),
        (1525, "COST", "end"),
    ]
    for x, label, anchor in headers:
        fill = {"STRICT": STRICT, "ISOLATED": ISOLATED, "CORE": CORE}.get(
            label, MUTED
        )
        svg.append(
            text(
                x,
                178,
                label,
                size=13,
                fill=fill,
                weight=660,
                anchor=anchor,
                spacing=1.0,
            )
        )
    svg.append(rule(70, 196, 1530, 196))

    for index, problem in enumerate(PROBLEM_ORDER):
        problem_rows = grouped[problem]
        strict, isolated, core = exact(problem_rows)
        final = problem_rows[-1]
        count = len(problem_rows)
        y = 239 + index * 70
        final_rate = float(final["strict_pass_rate"])
        cost = sum(row["cost"] for row in problem_rows)
        svg.extend(
            [
                text(70, y, DISPLAY_NAMES[problem], size=18, weight=650),
                text(425, y, count, size=17, fill=MUTED, anchor="end"),
            ]
        )
        mini_metric(svg, 495, y, strict, count, STRICT)
        mini_metric(svg, 665, y, isolated, count, ISOLATED)
        mini_metric(svg, 835, y, core, count, CORE)
        svg.extend(
            [
                *bar(1025, y - 18, 95, 24, final_rate, OX, radius=6),
                text(
                    1250,
                    y,
                    (
                        f"{final['passed_tests']}/{final['total_tests']}  "
                        f"{final_rate:.1%}"
                    ),
                    size=16,
                    fill=TEXT if final_rate >= 0.9 else MUTED,
                    weight=680,
                    anchor="end",
                ),
                text(
                    1525,
                    y,
                    f"${cost:.2f}",
                    size=17,
                    fill=MUTED,
                    weight=650,
                    anchor="end",
                ),
                rule(70, y + 28, 1530, y + 28),
            ]
        )
    svg.extend(
        [
            text(70, 823, "N = checkpoints in the cumulative trajectory.", size=15, fill=MUTED),
            text(
                1530,
                823,
                "Final rates below 100% are not strict solves.",
                size=15,
                fill=MUTED,
                anchor="end",
            ),
        ]
    )
    save("ox-alpha-pi-landscape.svg", svg)


def comparison_summary(data_dir: Path) -> list[dict[str, Any]]:
    comparison = json.loads((data_dir / "comparisons.json").read_text())
    problem_set = set(comparison["problem_set"])
    expected = int(comparison["expected_checkpoints"])
    target_keys: set[tuple[str, int]] | None = None
    output = []
    colors = {"ox-alpha": OX, "glm-5.3": GLM, "qwen3.8-27b": QWEN}
    expected_settings = {
        "agent": "pi 0.84.2",
        "thinking": "xhigh",
        "prompt": "just-solve",
        "pass_policy": "all-cases",
        "seed": 42,
    }
    expected_catalog = {
        "version": "v1.0",
        "commit": "4d38d300059667d57e43c31969bc455f5c338b52",
    }

    for system in comparison["systems"]:
        dataset = DATA_ROOT / system["dataset"]
        rows = [
            row
            for row in load_rows(dataset / "checkpoint_results.jsonl")
            if row["problem"] in problem_set
        ]
        keys = {(str(row["problem"]), int(row["idx"])) for row in rows}
        require(len(rows) == expected, f"{system['id']} comparison row count")
        if target_keys is None:
            target_keys = keys
        require(keys == target_keys, f"{system['id']} comparison keys")

        manifest = json.loads((dataset / "source_manifest.json").read_text())
        settings = manifest["shared_configuration"]
        for field, expected_value in expected_settings.items():
            require(
                settings[field] == expected_value,
                f"{system['id']} comparison setting {field}",
            )
        require(
            manifest["problem_catalog"] == expected_catalog,
            f"{system['id']} comparison catalogue manifest",
        )
        catalog = json.loads((dataset / "problem_catalog.json").read_text())
        require(
            catalog == expected_catalog,
            f"{system['id']} comparison catalogue file",
        )
        result = json.loads((dataset / "result.json").read_text())
        require(result["agent_type"] == "pi", f"{system['id']} agent type")
        require(result["agent_version"] == "0.84.2", f"{system['id']} agent")
        require(result["thinking"] == "xhigh", f"{system['id']} thinking")
        require(result["prompt"] == "just-solve", f"{system['id']} prompt")

        strict, isolated, core = exact(rows)
        output.append(
            {
                "id": system["id"],
                "label": system["label"],
                "color": colors[system["id"]],
                "rows": rows,
                "count": len(rows),
                "strict": strict,
                "isolated": isolated,
                "core": core,
                "cost": sum(row["cost"] for row in rows),
                "hours": sum(row["duration"] for row in rows) / 3600,
                "steps": sum(row["steps"] for row in rows),
            }
        )
    return output


def render_comparison(data_dir: Path) -> None:
    title = "Observed strict scores: GLM 11, Ox 7, Qwen 5"
    systems = comparison_summary(data_dir)
    systems.sort(key=lambda item: item["strict"], reverse=True)
    svg = start(
        1600,
        830,
        title,
        (
            "Same-39 comparison: GLM solved 11 strict, Ox 7, and Qwen 5. "
            "Pi-recorded cost estimates were 21.72, 10.10, and 30.85 dollars "
            "respectively."
        ),
    )
    heading(
        svg,
        title,
        (
            "Same listed agent and evaluation settings; pi cost estimate "
            "shown at right."
        ),
    )
    svg.extend(
        [
            text(
                70,
                178,
                "EXACT CHECKPOINT SOLVES",
                size=14,
                fill=MUTED,
                weight=660,
                spacing=1.2,
            ),
            text(
                1070,
                178,
                "RECORDED EFFORT",
                size=14,
                fill=MUTED,
                weight=660,
                spacing=1.2,
            ),
            rule(1015, 158, 1015, 680),
        ]
    )

    metrics = [
        ("Core", "core", CORE),
        ("Isolated", "isolated", ISOLATED),
        ("Strict", "strict", STRICT),
    ]
    count = int(systems[0]["count"])
    require(
        all(system["count"] == count for system in systems),
        "comparison denominators differ",
    )
    plot_x = 300
    plot_width = 615
    for index, system in enumerate(systems):
        y = 225 + index * 158
        svg.extend(
            [
                text(70, y + 28, system["label"], size=21, weight=720),
                (
                    f'<rect x="{70}" y="{y + 47}" width="{6}" '
                    f'height="{74}" rx="3" fill="{system["color"]}"/>'
                ),
            ]
        )
        for metric_index, (label, key, color) in enumerate(metrics):
            metric_y = y + 38 + metric_index * 36
            solved = int(system[key])
            svg.extend(
                [
                    text(190, metric_y + 22, label, size=14, fill=MUTED),
                    *bar(
                        plot_x,
                        metric_y,
                        plot_width,
                        26,
                        (solved / count) / 0.7,
                        color,
                        radius=6,
                    ),
                    text(
                        965,
                        metric_y + 20,
                        f"{solved}/{count}  {solved / count:.1%}",
                        size=15,
                        fill=color,
                        weight=700,
                        anchor="end",
                    ),
                ]
            )

        stats = [
            ("pi cost est.", f"${system['cost']:.2f}"),
            ("Agent time", f"{system['hours']:.1f}h"),
            ("Steps", f"{system['steps']:,}"),
        ]
        for stat_index, (label, value) in enumerate(stats):
            stat_x = 1070 + stat_index * 165
            svg.extend(
                [
                    text(stat_x, y + 22, label, size=13, fill=MUTED),
                    text(
                        stat_x,
                        y + 58,
                        value,
                        size=24,
                        fill=system["color"],
                        weight=710,
                    ),
                ]
            )
        svg.append(rule(70, y + 137, 1530, y + 137))

    svg.extend(
        [
            text(
                300,
                720,
                "Bars share a 0–70% scale.",
                size=15,
                fill=MUTED,
            ),
            rule(70, 755, 1530, 755),
            text(
                70,
                793,
                "Single trajectories; execution topology and provider pricing differ, and Qwen’s union used two invocations.",
                size=16,
                fill=MUTED,
            ),
        ]
    )
    save("ox-alpha-pi-comparison.svg", svg)


def render_code_health(grouped: dict[str, list[dict[str, Any]]]) -> None:
    title = "The maintained surface tripled; exactness did not survive"
    first_rows = [grouped[problem][0] for problem in PROBLEM_ORDER]
    final_rows = [grouped[problem][-1] for problem in PROBLEM_ORDER]
    first_loc = sum(row["loc"] for row in first_rows)
    final_loc = sum(row["loc"] for row in final_rows)
    first_high = sum(row["cc_high_count"] for row in first_rows)
    final_high = sum(row["cc_high_count"] for row in final_rows)
    first_verbosity = sum(row["verbosity"] for row in first_rows) / 8
    final_verbosity = sum(row["verbosity"] for row in final_rows) / 8
    first_erosion = sum(row["erosion"] for row in first_rows) / 8
    final_erosion = sum(row["erosion"] for row in final_rows) / 8

    svg = start(
        1600,
        1050,
        title,
        (
            "First-to-final code health: measurable Python grew from 4,967 "
            "to 16,142 lines, and functions above CC 10 rose from 37 to 121."
        ),
    )
    heading(
        svg,
        title,
        "First-to-final measurable Python volume and maximum cyclomatic complexity.",
    )
    summaries = [
        ("Combined LOC", f"{first_loc:,} → {final_loc:,}"),
        ("Source growth", f"{final_loc / first_loc:.2f}×"),
        ("High-CC funcs (>10)", f"{first_high} → {final_high}"),
        ("Mean verbosity", f"{first_verbosity:.1%} → {final_verbosity:.1%}"),
        ("Mean erosion", f"{first_erosion:.1%} → {final_erosion:.1%}"),
    ]
    for index, (label, value) in enumerate(summaries):
        x = 70 + index * 292
        svg.extend(
            [
                text(x, 184, label, size=13, fill=MUTED),
                text(x, 224, value, size=24, fill=OX, weight=710),
            ]
        )
        if index:
            svg.append(rule(x - 25, 170, x - 25, 232))
    svg.append(rule(70, 260, 1530, 260))

    maximum_loc = max(row["loc"] for row in final_rows)
    plot_x = 390
    plot_width = 760
    svg.extend(
        [
            text(70, 302, "PROBLEM", size=13, fill=MUTED, weight=660, spacing=1.0),
            text(390, 302, "LINES OF CODE", size=13, fill=MUTED, weight=660, spacing=1.0),
            text(1300, 302, "MAX CC", size=13, fill=MUTED, weight=660, spacing=1.0),
        ]
    )
    for index, problem in enumerate(PROBLEM_ORDER):
        first = grouped[problem][0]
        final = grouped[problem][-1]
        y = 332 + index * 79
        first_width = plot_width * first["loc"] / maximum_loc
        final_width = plot_width * final["loc"] / maximum_loc
        growth = f"{final['loc'] / first['loc']:.1f}×"
        label_inside = final_width > 610
        label_x = (
            plot_x + final_width - 14
            if label_inside
            else plot_x + final_width + 13
        )
        svg.extend(
            [
                text(70, y + 30, DISPLAY_NAMES[problem], size=17, weight=640),
                (
                    f'<rect x="{plot_x}" y="{y + 5}" '
                    f'width="{first_width:.1f}" height="11" rx="5" '
                    f'fill="{MUTED}" opacity="0.62"/>'
                ),
                (
                    f'<rect x="{plot_x}" y="{y + 24}" '
                    f'width="{final_width:.1f}" height="23" rx="6" '
                    f'fill="{OX}"/>'
                ),
                text(
                    label_x,
                    y + 42,
                    f"{first['loc']:,} → {final['loc']:,}  ({growth})",
                    size=13,
                    fill=BG if label_inside else OX,
                    weight=700,
                    anchor="end" if label_inside else "start",
                ),
                text(
                    1300,
                    y + 31,
                    f"{first['cc_max']} → {final['cc_max']}",
                    size=17,
                    fill=STRICT if final["cc_max"] > 30 else TEXT,
                    weight=700,
                ),
                rule(70, y + 58, 1530, y + 58),
            ]
        )
    svg.extend(
        [
            text(390, 1000, "first checkpoint", size=14, fill=MUTED),
            (
                f'<rect x="354" y="990" width="24" height="10" '
                f'rx="5" fill="{MUTED}" opacity="0.62"/>'
            ),
            text(618, 1000, "final checkpoint", size=14, fill=MUTED),
            (
                f'<rect x="582" y="987" width="24" height="16" '
                f'rx="5" fill="{OX}"/>'
            ),
            text(
                1530,
                1000,
                "CC above 30 is highlighted.",
                size=14,
                fill=MUTED,
                anchor="end",
            ),
        ]
    )
    save("ox-alpha-pi-code-health.svg", svg)


def main() -> None:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
    rows = load_rows(data_dir / "checkpoint_results.jsonl")
    grouped = group_rows(rows)
    validate_dataset(data_dir, rows, grouped)
    # Validate every comparison input before writing any derived artifact.
    comparison_summary(data_dir)
    write_derived_data(data_dir, rows, grouped)
    render_scorecard(rows, grouped)
    render_trajectory(grouped)
    render_landscape(grouped)
    render_comparison(data_dir)
    render_code_health(grouped)


if __name__ == "__main__":
    main()
