# Benchmarks

Small, reproducible coding-agent benchmark reports.

## Reports

- [Benchmarking Ox Alpha with pi on SlopCodeBench](ox-alpha-pi-on-slop-code-bench.md)
  — 8 cumulative problems and 39 checkpoints, run through OpenRouter under pi
  0.84.2 with xhigh configured. The stealth preview solved 7/39 checkpoints
  strictly, 10/39 in isolation, and 21/39 at the core-contract level. August
  20, 2026.
- [Benchmarking GLM-5.3 with pi on the full SlopCodeBench catalogue](glm-5.3-pi-on-slop-code-bench.md)
  — the complete 36-problem, 196-checkpoint catalogue, run through OpenRouter
  under pi 0.84.2 at xhigh reasoning. GLM solved 24/196 checkpoints strictly,
  53/196 in isolation, and 130/196 at the core-contract level. August 19, 2026.
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
scripts/        chart generation and run summarization; metadata extraction
```

Regenerate the DeepSeek and Qwen figures with:

```bash
python scripts/render_charts.py [data/<run>]
```

Regenerate the full-catalogue GLM figures with:

```bash
python scripts/render_glm_charts.py data/glm-5.3-pi-xhigh-2026-08-19
```

Regenerate the Ox Alpha figures with:

```bash
python scripts/render_ox_alpha_charts.py \
  data/ox-alpha-pi-xhigh-2026-08-20
```

No third-party Python packages are required to regenerate the figures.
