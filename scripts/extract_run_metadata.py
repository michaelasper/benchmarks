#!/usr/bin/env python3
"""Extract problem and checkpoint metadata from a SlopCodeBench run.

Usage:
    python extract_run_metadata.py <run-dir> <out-dir>

Requires PyYAML. The report documents an explicit ``uv run --with pyyaml``
invocation so this extraction dependency does not affect figure rendering.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROBLEM_FIELDS = [
    "problem",
    "difficulty",
    "category",
    "entry_file",
    "version",
    "tags",
    "description",
]
CHECKPOINT_FIELDS = [
    "problem",
    "checkpoint",
    "include_prior_tests",
    "checkpoint_state",
    "checkpoint_version",
    "timeout_seconds",
]


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def write_csv(
    path: Path, fields: list[str], rows: list[dict[str, object]]
) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def extract_problem(run_dir: Path, problem: str) -> dict[str, object]:
    source = run_dir / problem / "problem.yaml"
    data = yaml.safe_load(source.read_text())
    return {
        "problem": problem,
        "difficulty": str(data["difficulty"]).lower(),
        "category": data["category"],
        "entry_file": data["entry_file"],
        "version": data["version"],
        "tags": "|".join(data.get("tags", [])),
        "description": " ".join(str(data["description"]).split()),
    }


def extract_checkpoint(
    run_dir: Path, row: dict[str, Any]
) -> dict[str, object]:
    problem = str(row["problem"])
    checkpoint = str(row["checkpoint"])
    source = run_dir / problem / checkpoint / "checkpoint.yaml"
    data = yaml.safe_load(source.read_text())
    return {
        "problem": problem,
        "checkpoint": int(row["idx"]),
        "include_prior_tests": str(
            bool(data["include_prior_tests"])
        ).lower(),
        "checkpoint_state": data["state"],
        "checkpoint_version": data["version"],
        "timeout_seconds": data["timeout"],
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    run_dir = Path(argv[1])
    out_dir = Path(argv[2])
    rows = load_rows(run_dir / "checkpoint_results.jsonl")
    keys = {(str(row["problem"]), int(row["idx"])) for row in rows}
    if len(keys) != len(rows):
        raise SystemExit("checkpoint_results.jsonl contains duplicate keys")

    problems = sorted({problem for problem, _ in keys})
    problem_rows = [
        extract_problem(run_dir, problem) for problem in problems
    ]
    checkpoint_rows = [
        extract_checkpoint(run_dir, row)
        for row in sorted(
            rows, key=lambda item: (item["problem"], item["idx"])
        )
    ]

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "problem_metadata.csv", PROBLEM_FIELDS, problem_rows)
    write_csv(
        out_dir / "checkpoint_metadata.csv",
        CHECKPOINT_FIELDS,
        checkpoint_rows,
    )
    print(
        f"wrote metadata for {len(problems)} problems and "
        f"{len(checkpoint_rows)} checkpoints"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
