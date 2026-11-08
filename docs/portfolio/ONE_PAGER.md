# ANAC Flight Intelligence

**Brazilian aviation data → verified analysis, honest forecasts, and an AI analyst that shows its sources.**

![Overview](screenshots/overview-day.png)

## The problem

ANAC publishes every Brazilian flight leg since 2000, about 20 GB of open data. Turning it into correct answers is hard:
- Flights, passenger flights and aircraft movements are different counts.
- Routes have a direction.
- Load factor cannot be averaged.
- Four months are missing and must not read as zero.

## The product

| | |
|---|---|
| **Dashboard** | Market, airports, routes and airlines for any period, with absent months flagged |
| **ML Studio** | Three forecasting problems, each compared with baselines on held-out 2023 data |
| **AI Analyst** | Plain-language questions, answered through fixed tools, with numbers checked before they are shown |

## Results

- **ML, validation 2023:**
  - Route demand 1 month ahead: WAPE **18.7% vs 24.1%** for the best baseline.
  - Seat occupancy: **6.06 vs 6.54 pts**.
  - Airport traffic: **no conclusive gain** over a weekday rule, so the rule is kept.
- **Reproducible:** every metric is recomputed from saved artifacts, and an in-memory refit matches bit for bit.
- **Analyst:** five recorded real cases, with every quantitative answer confirmed against the data, one gap documented, and two wrong drafts blocked by the verifier.
- **Quality:** 334 backend and 81 frontend tests, strict typing, production build.

## What makes it different

- **Says when machine learning does not help.** Model A keeps the simple rule.
- **Never invents.** No fares (the data has none), no zero-filled gaps, no forecasts served before testing.
- **Built with AI agents under human control.** Claude Code and Codex share written rules, own separate directories and work in separate Git worktrees. Every stage and commit was approved by me.

## Stack

Python 3.12 · Polars · DuckDB · Parquet · LightGBM · FastAPI · Next.js 16 · React 19 · TypeScript · Tailwind 4 · Groq (OpenAI-compatible tool calls)

## Links

- **Repository:** `github.com/CaioBandeira7/anac-flight-intelligence-api-main`
- **Live demo:** not published yet (see [DEPLOYMENT.md](../DEPLOYMENT.md))
- **ML technical report:** [REPORT.pdf](../../research/ml-showcase/REPORT.pdf)
- **Case study:** [CASE_STUDY.md](CASE_STUDY.md) · **Analyst demo:** [ANALYST_DEMO.md](ANALYST_DEMO.md)
