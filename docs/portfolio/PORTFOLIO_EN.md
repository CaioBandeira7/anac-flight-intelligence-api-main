# ANAC Flight Intelligence — portfolio summary (English)

Cover: `assets/cover/cover-github-1280x640-en.jpg` · Deck: `presentation/anac-flight-intelligence-summary-en.pdf`

**Live:** [anac-flight-intelligence-api-main.vercel.app](https://anac-flight-intelligence-api-main.vercel.app) · **Code:** [github.com/CaioBandeira7/anac-flight-intelligence-api-main](https://github.com/CaioBandeira7/anac-flight-intelligence-api-main)

## One line

A data and machine-learning platform on Brazil's open aviation data (ANAC, 2000–2025): audited ingestion, an analytics dashboard, forecasting models tested honestly against baselines, and an AI analyst that answers only from the data and checks every number.

## The problem

ANAC publishes every Brazilian flight leg since 2000, about 20 GB of open data. Correct answers are hard to get from it. Flights, passenger flights and aircraft movements are different counts. Routes are directed. Load factor cannot be averaged. Four months are missing from the source and must never read as zero.

## What I built

- **Data engineering:** 22,120,241 rows ingested into Parquet in 8 minutes with a 2.37 GB memory peak, none rejected, and re-read by an independent audit script that shares no code with the pipeline. Analytical star schema with 3 dimensions and 4 fact tables.
- **Dashboard (Next.js 16, React 19, TypeScript):** market, airports, routes and airlines for any period. 2025: 131.6M paid passengers (+9.7% year over year), 976.4K flights, 82.1% load factor.
- **Machine learning (LightGBM):** chronological splits, point-in-time features with a 2-month publication lag, and a strict adoption rule: a model must beat its best baseline with a 95% block-bootstrap interval excluding zero.

  | Task (2023 validation) | Model | Best baseline | Verdict |
  |---|---|---|---|
  | Daily movements, 50 busiest airports | WAPE 10.10% | 10.30% | Not conclusive, baseline kept |
  | Load factor by route and carrier | MAE 6.06 pts | 6.54 pts | Better |
  | Monthly passengers by route | WAPE 22.24% | 25.31% | Better; 18.7% vs 24.1% at 1 month |

- **AI analyst (Groq, `openai/gpt-oss-120b`):** five fixed read-only tools, sources attached by code, a numeric verifier that refuses drafts with unsupported figures, the API key server-side only, and rate limits of 10 questions per visitor per hour and 200 per day.
- **Deployment:** FastAPI in Docker on Render, dashboard on Vercel.

## Limits stated up front

- The route-demand model under-forecasts by about 12% and is worse than the baseline at 6 months ahead.
- The final 2024–2025 test is sealed and has not been run. Results are validation, not forecasts; no prediction endpoint exists.
- The numeric verifier is heuristic: it checks that each figure belongs to the entity and metric it is attached to, but cannot guarantee every association.

## How it was built

With Claude Code and Codex working under written rules (`AGENTS.md`): separate ownership per directory, a contract-first API, no invented data, and every stage approved by me.

**Stack:** Python 3.12 · Polars · DuckDB · Parquet · LightGBM · FastAPI · Docker · Render · Next.js 16 · React 19 · TypeScript · Tailwind 4 · Vercel · Groq
