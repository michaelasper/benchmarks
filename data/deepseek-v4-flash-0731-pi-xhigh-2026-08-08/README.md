# DeepSeek V4 Flash 0731 / pi / max reasoning / 2026-08-08

Source artifacts for the report:
[Running DeepSeek V4 Flash 0731 locally on SlopCodeBench](../../deepseek-v4-flash-0731-pi-on-slop-code-bench.md).

## Files

- `config.yaml` — resolved runner configuration, with local absolute paths
  normalized to repository-relative paths.
- `result.json` — aggregate run result produced by SlopCodeBench.
- `checkpoint_results.jsonl` — one evaluator record per checkpoint.
- `checkpoints.csv` — selected columns normalized for analysis and charts.
- `trajectory.jsonl` — one record per checkpoint summarizing the agent loop:
  stop reasons, termination cause, reasoning volume, tool calls, files changed.
  Summarized from the agent event stream, which is ~30 MB per run and is not
  committed.

The run covered `circuit_eval`, `database_migration`, and
`dynamic_config_service_api`. It used seed 42, Python 3.12, the `pi` agent
0.84.0, the `just-solve` prompt, and maximum reasoning effort, against a
locally served quantized model with a 131,072-token context window.

## Serving configuration

Max output tokens 49,152; compaction reserve 49,152. This run also used a
larger quantization than the 2026-08-07 run; see the report for why that makes
the comparison confounded.
