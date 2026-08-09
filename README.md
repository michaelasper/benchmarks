# Benchmarks

Small, reproducible coding-agent benchmark reports.

## Reports

- [Benchmarking DeepSeek V4 Flash on SlopCodeBench](deepseek-v4-flash-on-slop-code-bench.md)
  — 3 problems, 17 checkpoints, OpenCode 1.18.10, high reasoning,
  July 31, 2026.
- [Running DeepSeek V4 Flash 0731 locally on SlopCodeBench](deepseek-v4-flash-0731-pi-on-slop-code-bench.md)
  — the same 3 problems and 17 checkpoints, run locally under the pi agent at
  maximum reasoning. Two runs a day apart scored 1/17 and 5/17 on identical
  weights; most of the gap is the output-token cap. August 7–8, 2026.

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
