# GLM-5.3 / pi / xhigh / 2026-08-19

Published data for [Benchmarking GLM-5.3 with pi on the full
SlopCodeBench catalogue](../../glm-5.3-pi-on-slop-code-bench.md).

## Dataset

This is one run over the complete configured SlopCodeBench v1.0 catalogue:
**36 problems and 196 checkpoints**. All expected checkpoints completed and
were evaluated. The aggregate result is **24/196 strict**, **53/196 isolated**,
and **130/196 core**, at **$167.515333** in billed API cost.

The workspace carries forward between checkpoints, but the catalogue does not
always carry prior tests forward. Twelve evaluations across six problems set
`include_prior_tests: false`; those rows are identified in
`checkpoint_metadata.csv`. A strict pass always means every test configured for
that evaluation passed.

## Files

- `config.yaml` — normalised resolved run configuration.
- `agent_config.yaml`, `environment.yaml`, `model_config.yaml`, `prompt.jinja`,
  and `run_config.yaml` — retained effective configuration inputs.
- `source_manifest.json` — run identity, catalogue commit, provider slug,
  container digests, source limitations, and completeness checks.
- `problem_catalog.json` — catalogue version and commit recorded by the runner.
- `result.json` — aggregate summary emitted by SlopCodeBench.
- `checkpoint_results.jsonl` — correctness, inference, token, cost, and static
  analysis fields for all 196 checkpoints.
- `checkpoints.csv` — chart-ready checkpoint fields.
- `problems.csv` — one aggregate row per problem.
- `phases.csv` — exact results for first, middle, and final checkpoint phases.
- `problem_metadata.csv` — difficulty, category, entry point, description, and
  tags recorded in each run artefact.
- `difficulty_summary.csv` — correctness and effort grouped by catalogue
  difficulty.
- `checkpoint_metadata.csv` — checkpoint version, timeout, and prior-test
  policy for every row.
- `diagnostics.jsonl` — selected evaluator evidence cited in the report.
- `comparisons.json` — cited strict scores used in the comparison figure.
- `trajectory.jsonl` — compact summaries of all retained pi event streams,
  including termination, tool calls, changed files, timing, and token use.

The trajectory extractor sees the retained event stream. Fourteen rows begin
with a continuation prompt after a failed attempt, so the overwritten
first-attempt events and their failure causes are unavailable. The process
timeout applied to each attempt. Scoring and billed totals still include the
completed inference records.

## Derived-file conventions

- Rates are fractions from 0 to 1. `*_solved` is true only when the corresponding
  rate is exactly 1.
- `cost` is billed US dollars; durations are seconds; token and step fields are
  integer counts.
- Test totals and passes are counts for the evaluation row. Prior tests are
  included only when `checkpoint_metadata.csv` says so.
- `loc`, function, and complexity fields describe the checkpoint snapshot, not
  the size of the diff.
- In `problems.csv`, costs, durations, steps, and output tokens are summed;
  `final_*` comes from the last checkpoint and `peak_cc` is the trajectory
  maximum.
- `phases.csv` groups repeated checkpoint instances. Its middle row is not a set
  of independent problems.
- An empty CSV cell or JSON `null` means the analyser did not produce that
  measure; it does not mean zero.

## Configuration and provenance

- **Model:** `openrouter/z-ai/glm-5.3`
- **Agent:** pi 0.84.2
- **Reasoning:** xhigh
- **Prompt:** `just-solve`
- **Pass policy:** `all-cases`
- **Seed:** 42
- **Environment:** Python 3.12 in Docker
- **Per-attempt process timeout:** 7,200 seconds
- **Problem catalogue:** `v1.0` at
  `4d38d300059667d57e43c31969bc455f5c338b52`

No rubric grader was used. Static quality fields were produced by
`scb-check==0.1.3`.

The runner did not record its git revision. At publication, the source
workspace was dirty and the run, model, and agent configurations were untracked;
the exact runtime patch is unavailable. `source_manifest.json` records this
limit alongside the observed source head, provider slug, image digests, and
retained configurations. These files improve auditability, but do not guarantee
an exact benchmark rerun.

Regenerate the four chart CSVs and four figures from the published checkpoint
records and `problem_metadata.csv` with the Python standard library:

```bash
python scripts/render_glm_charts.py data/glm-5.3-pi-xhigh-2026-08-19
```

To re-extract the two metadata CSV inputs from the original run directory, use
PyYAML explicitly:

```bash
uv run --with pyyaml python scripts/extract_run_metadata.py \
  ../slop-code-bench/outputs/glm-5.3/pi-0.84.2_just-solve_max_all_20260819T1653 \
  data/glm-5.3-pi-xhigh-2026-08-19
```
