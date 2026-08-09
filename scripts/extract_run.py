#!/usr/bin/env python3
"""Summarize a SlopCodeBench run's agent loops into one committable file.

Usage:
    python3 extract_run.py <run-dir> <out-dir>

Writes:
    trajectory.jsonl  one row per checkpoint: agent-loop facts

The agent-loop facts come from each checkpoint's ``agent/stdout.jsonl`` (the
pi agent's ``--mode json`` event stream), which is ~30 MB for a 17-checkpoint
run and is therefore summarized here rather than committed. Timing and diff
facts come from ``inference_result.json`` and ``diff.json``.

``checkpoints.csv`` is deliberately not written here: ``render_charts.py``
owns that file and emits the column set its figures need. Writing it from two
places would leave the schema dependent on which script ran last.

Standard library only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path



def _ck_index(name: str) -> int:
    return int(str(name).rsplit("_", 1)[-1])


def summarize_trajectory(stdout_path: Path) -> dict[str, object]:
    """Reduce one pi event stream to the agent-loop facts the report needs.

    Only ``message_end`` events are read: ``turn_end`` repeats the final
    message of a turn and would double-count it.
    """
    assistant: list[dict] = []
    compaction_errors: list[str] = []
    first_user_text = ""
    with stdout_path.open() as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "compaction_end":
                message = event.get("errorMessage")
                if message:
                    compaction_errors.append(message)
                continue
            if event.get("type") != "message_end":
                continue
            message = event.get("message", {})
            if message.get("role") == "assistant":
                assistant.append(message)
            elif message.get("role") == "user" and not first_user_text:
                first_user_text = "".join(
                    block.get("text", "")
                    for block in message.get("content", [])
                    if block.get("type") == "text"
                )

    # The harness overwrites stdout.jsonl when it retries a failed attempt, so
    # a stream that opens with the continuation prompt is a retry, and the
    # original attempt's events are gone.
    retried = first_user_text.strip().startswith("Continue from where you left off")

    tool_calls: dict[str, int] = {}
    thinking_chars = 0
    capped_no_tool_call = 0  # anywhere in the trajectory, not just the end
    for message in assistant:
        for block in message.get("content", []):
            if block.get("type") == "toolCall":
                name = block.get("name", "?")
                tool_calls[name] = tool_calls.get(name, 0) + 1
            elif block.get("type") == "thinking":
                thinking_chars += len(block.get("thinking", ""))
        if message.get("stopReason") == "length" and not any(
            b.get("type") == "toolCall" for b in message.get("content", [])
        ):
            capped_no_tool_call += 1

    stop_reasons: dict[str, int] = {}
    for message in assistant:
        reason = message.get("stopReason") or "none"
        stop_reasons[reason] = stop_reasons.get(reason, 0) + 1

    final = assistant[-1] if assistant else {}
    final_blocks = [b.get("type") for b in final.get("content", [])]
    final_capped = final.get("stopReason") == "length" and (
        "toolCall" not in final_blocks
    )

    # Why the loop stopped, in order of specificity. A failed compaction means
    # the conversation outgrew the context window, which is a different failure
    # from the model spending its whole output budget on reasoning.
    if compaction_errors:
        termination = "context_overflow"
    elif final_capped and "thinking" in final_blocks:
        termination = "output_cap"
    elif final_capped:
        termination = "length_no_content"
    elif retried:
        termination = "retry"
    else:
        termination = "clean"

    return {
        "assistant_messages": len(assistant),
        "is_retry": retried,
        "thinking_chars": thinking_chars,
        "stop_reasons": stop_reasons,
        "capped_no_tool_call": capped_no_tool_call,
        "final_stop_reason": final.get("stopReason"),
        "final_blocks": final_blocks,
        "termination": termination,
        "compaction_errors": compaction_errors,
        "tool_calls": tool_calls,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    run_dir = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    results = [
        json.loads(line)
        for line in (run_dir / "checkpoint_results.jsonl").read_text().splitlines()
        if line.strip()
    ]
    results.sort(key=lambda r: (r["problem"], _ck_index(r["checkpoint"])))

    traj_path = out_dir / "trajectory.jsonl"
    with traj_path.open("w") as handle:
        for row in results:
            ck_dir = run_dir / row["problem"] / row["checkpoint"]
            diff = json.loads((ck_dir / "diff.json").read_text())
            inference = json.loads((ck_dir / "inference_result.json").read_text())
            usage = inference["usage"]
            record: dict[str, object] = {
                "problem": row["problem"],
                "checkpoint": _ck_index(row["checkpoint"]),
                "started": inference["started"],
                "completed": inference["completed"],
                "elapsed": round(inference["elapsed"], 3),
                "steps": usage["steps"],
                "output_tokens": usage["current_tokens"]["output"],
                "net_output_tokens": usage["net_tokens"]["output"],
                "net_input_tokens": usage["net_tokens"]["input"],
                "files_changed": sorted(diff["file_diffs"]),
            }
            stdout_path = ck_dir / "agent" / "stdout.jsonl"
            if stdout_path.exists():
                record.update(summarize_trajectory(stdout_path))
            handle.write(json.dumps(record) + "\n")

    print(f"wrote {traj_path} ({len(results)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
