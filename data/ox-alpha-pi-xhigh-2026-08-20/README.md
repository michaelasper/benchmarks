# Ox Alpha / pi / xhigh / 2026-08-20

Published data for [Benchmarking Ox Alpha with pi on
SlopCodeBench](../../ox-alpha-pi-on-slop-code-bench.md).

## Dataset

The dataset contains one complete cumulative trajectory for each of eight
problems: 39 unique checkpoints in total. This is the union of the problem
lists used in the linked HumanLayer Opus and Fable/Sol/Kimi reports;
`circuit_eval` belongs to both lists and appears once.

The aggregate is **7/39 strict**, **10/39 isolated**, and **21/39 core**, with
**$10.101016** in pi-recorded estimated cost. Every configured checkpoint ran
and was
evaluated. `source_manifest.json` records source provenance and the retained
effective configuration.

## Files

- `result.json` — aggregate summary emitted by SlopCodeBench.
- `checkpoint_results.jsonl` — correctness, inference, cost, token, and
  code-quality record for every checkpoint.
- `checkpoints.csv` and `problems.csv` — chart-ready derived fields.
- `diagnostics.jsonl` — selected evaluator and diff evidence used in the
  report’s trajectory analysis.
- `test_outcomes.csv` — passed, failed, and skipped evaluator outcomes for
  each checkpoint. The aggregate treats skipped outcomes as not passed.
- `trajectory.jsonl` — compact summaries of the retained pi event streams,
  including stop reasons, tool calls, and changed files.
- `problem_metadata.csv` and `checkpoint_metadata.csv` — problem attributes
  and prior-test policy.
- `comparisons.json` — the three internal datasets used in the like-for-like
  comparison figure.
- `problem_catalog.json` — catalogue version and commit recorded by the
  runner.
- `source_manifest.json` — source ID, container digests, configuration,
  caveats, and publication-time runner state.
- `source_hashes.json` — SHA-256 lineage for all 208 local raw artifacts used
  to copy or derive the published files.
- `config.yaml`, `agent_config.yaml`, `model_config.yaml`, `run_config.yaml`,
  `environment.yaml`, and `prompt.jinja` — normalized effective configuration.
- `run.sh` — the historical source-root launcher and exact CLI concurrency
  controls. It must be placed in a matching SlopCodeBench checkout; it is not a
  standalone launcher from this data directory.

The retained trajectory stream begins at a continuation prompt for three
checkpoints because the harness overwrote the original attempt’s events on
retry. This limits attempt-level forensics, not checkpoint scoring or the
recorded usage totals.

## Configuration

- **Model:** `openrouter/stealth/ox-alpha`
- **Disclosed model identity:** none; the provider exposed only the preview
  alias
- **Agent:** pi 0.84.2
- **Reasoning:** configured as xhigh; the pi runtime environment exposed the
  mapped value `high`
- **Prompt:** `just-solve`
- **Pass policy:** `all-cases`
- **Seed:** 42
- **Environment:** Python 3.12 in Docker
- **Process timeout:** 7,200 seconds per attempt
- **Execution:** eight problem workers with concurrent checkpoint evaluation
- **Problem catalogue:** `v1.0` at
  `4d38d300059667d57e43c31969bc455f5c338b52`

No rubric grader was used. Composite quality fields use `scb-check 0.1.3`.
Two dynamic-configuration checkpoints were configured with
`include_prior_tests: false`; their workspaces remained cumulative, but their
evaluations did not automatically carry forward prior suites. Sixty-three test
outcomes were skipped across five evaluations and remain in the aggregate
denominators as not passed.

The preview’s published fallback pricing configuration was zero. The non-zero
`usage.cost` values were emitted by pi from its runtime model pricing; raw
provider billing telemetry was not retained. They are cost estimates, not proof
of the final invoiced amount.

Regenerate the CSVs and all five figures with only the Python standard
library:

```bash
python scripts/render_ox_alpha_charts.py \
  data/ox-alpha-pi-xhigh-2026-08-20
```
