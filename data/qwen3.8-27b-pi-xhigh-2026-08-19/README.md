# Qwen3.8-27B / pi / xhigh / 2026-08-19

Published data for [Benchmarking Qwen3.8-27B with pi on
SlopCodeBench](../../qwen3.8-27b-pi-on-slop-code-bench.md).

## Dataset

The dataset contains one complete cumulative trajectory for each of eight
problems: 39 unique checkpoints in total. The selected trajectories share the
same model, agent, prompt, reasoning level, pass policy, seed, environment, and
SlopCodeBench problem-catalog commit. `circuit_eval` belongs to both comparison
subsets but appears only once in the union.

The normalized aggregate is **5/39 strict**, **8/39 isolated**, and **17/39
core**, at **$30.854072** in billed API cost. `source_manifest.json` records the
problem-to-source allocation.

## Files

- `config.yaml` — shared normalized configuration.
- `source_manifest.json` — source IDs, selected problems, and catalogue commit.
- `comparisons.json` — cited comparison scores used by the comparison figure.
- `problem_catalog.json` — catalogue version and commit recorded by the runner.
- `result.json` — aggregate summary recomputed over the 39 selected rows using
  SlopCodeBench’s summary formulas.
- `checkpoint_results.jsonl` — normalized correctness, inference, token, cost,
  and code-quality record for every checkpoint.
- `checkpoints.csv` — chart-ready selection of the most useful checkpoint
  fields.
- `diagnostics.jsonl` — selected failing test IDs and concise evaluator evidence
  for the report’s per-problem analysis.
- `trajectory.jsonl` — compact summaries of the retained pi event streams,
  including stop reasons, tool calls, changed files, timing, and token use.

Retained trajectory summaries contain the event streams available at extraction
time; earlier overwritten attempt events are not included. This affects
trajectory forensics, not checkpoint scoring or billed totals.

## Configuration

- **Model:** `openrouter/qwen3.8-27b`
- **Agent:** pi 0.84.2
- **Reasoning:** xhigh
- **Prompt:** `just-solve`
- **Pass policy:** `all-cases`
- **Seed:** 42
- **Environment:** Python 3.12 in Docker
- **Process timeout:** 7,200 seconds
- **Problem catalogue:** `v1.0` at `4d38d300059667d57e43c31969bc455f5c338b52`

No rubric grader was used. Composite code-quality fields are available for 37
of 39 checkpoints; two first checkpoints contained no measurable Python source.
The `all-cases` aggregate retains all configured checkpoints in its denominator;
three incomplete evaluator rows remain unsolved rather than being dropped.

Regenerate the CSV and figures from the committed data files with:

```bash
python scripts/render_charts.py data/qwen3.8-27b-pi-xhigh-2026-08-19
```
