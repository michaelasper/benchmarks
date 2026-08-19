# Benchmarks

Small, reproducible coding-agent benchmark reports.

## Reports

- [Benchmarking Qwen3.8-27B with pi on SlopCodeBench](qwen3.8-27b-pi-on-slop-code-bench.md)
  — 8 cumulative problems and 39 unique checkpoints, run through OpenRouter
  under pi 0.84.2 at xhigh reasoning. Qwen solved 5/39 checkpoints strictly,
  8/39 in isolation, and 17/39 at the core-contract level. August 19, 2026.
- [Benchmarking DeepSeek V4 Flash on SlopCodeBench](deepseek-v4-flash-on-slop-code-bench.md)
  — 3 problems, 17 checkpoints, OpenCode 1.18.10, high reasoning,
  July 31, 2026.
- [Running DeepSeek V4 Flash 0731 locally on SlopCodeBench](deepseek-v4-flash-0731-pi-on-slop-code-bench.md)
  — the same 3 problems and 17 checkpoints, run locally under the pi agent at
  maximum reasoning. Two differently quantized runs scored 1/17 and 5/17 after
  the quant and output-token cap both changed. August 7–8, 2026.

Each report links to the summarized run data and the script used to regenerate
its charts.

## Layout

```
data/<run>/     aggregates from the run, plus a normalized CSV and,
                where available, a per-checkpoint agent-loop summary
images/         generated figures, one prefix per run
scripts/        chart generation and run summarization, standard library only
```

Regenerate any run's figures with:

```bash
python scripts/render_charts.py [data/<run>]
```

No third-party Python packages are required.
