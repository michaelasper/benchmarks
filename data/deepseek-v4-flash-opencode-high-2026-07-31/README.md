# DeepSeek V4 Flash / OpenCode / high / 2026-07-31

Source artifacts for the report:
[Benchmarking DeepSeek V4 Flash on SlopCodeBench](../../deepseek-v4-flash-on-slop-code-bench.md).

## Files

- `config.yaml` — resolved runner configuration, with local absolute paths
  normalized to repository-relative paths.
- `result.json` — aggregate run result produced by SlopCodeBench.
- `checkpoint_results.jsonl` — one evaluator record per checkpoint.
- `checkpoints.csv` — selected columns normalized for analysis and charts.

The run covered `circuit_eval`, `database_migration`, and
`dynamic_config_service_api`. It used seed 42, Python 3.12, OpenCode 1.18.10,
the `just-solve` prompt, and high reasoning effort.
