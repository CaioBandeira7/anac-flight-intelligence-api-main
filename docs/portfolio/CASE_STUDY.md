# Building an AI-Powered Aviation Intelligence Platform with AI-Assisted Development

**ANAC Flight Intelligence v2** · Caio Bandeira · case study

## Problem

Brazil's civil aviation agency (ANAC) publishes every flight leg since 2000: about 20 GB of CSV. The data is open, but hard to use:

- **Raw records, no answers.** A question such as "which route grew most" means aggregating millions of rows correctly.
- **Easy to get wrong.** Flights, passenger flights and aircraft movements are different counts. Routes have a direction. Load factor cannot be averaged. Four months are missing entirely and must not read as zero.
- **No forecasts with evidence.** Predicting traffic is only useful if the model is shown to beat simple rules on data it has not seen.

## Solution

A platform that turns the public records into verified analysis:

- **Dashboard.** Market overview, airports, routes and airlines, filtered by period and entity. Every figure states its period, scope and unit, and absent months are flagged.
- **ML Studio.** Three forecasting problems, each compared with baselines on 2023 data the models never saw. It reports where machine learning helps and where it does not.
- **AI Aviation Analyst.** Plain-language questions, answered through fixed read-only tools, with every number checked against the tool results before it is shown.

## My role

I owned the product and its decisions. AI agents wrote most of the code under my direction.

- Defined the goals, scope and staged plan, and the rules: no invented data, chronological evaluation, a sealed test.
- Approved every stage before the next began, and every commit. The agents could not commit, push or call a paid model without explicit authorization (`AGENTS.md`).
- Made the methodological decisions recorded in `docs/decisions.md`, such as dropping excess baggage as a target and not running the final test yet.
- Authorized and capped the live LLM validation runs, and validated the interface manually.

## AI-assisted workflow

### Who did what

| | Evidence in the repository |
|---|---|
| **Claude Code** | Co-author of 12 of the 17 commits: every v2 commit except `1a5ead4`, which only ignores data files. It covered the ingestion, features, models, API, analytical layer, analyst and dashboard. Now responsible for `web/**` (frontend, UX, maps). |
| **Codex** | Joined for backend, ML and the Power BI project. It works in its own Git worktree, `D:\anac-fi-bi`, on branch `codex/bi-semantic-model`. Its work there (`bi/`, `src/anac/bi/`, three test files) is in progress and **not yet committed**. |
| **Shared rules** | `AGENTS.md`, imported by `CLAUDE.md`, gives both agents the same rules: architecture, commands, data rules, model limitations, design preservation, credentials, and file ownership by directory. |

### How a stage ran

1. **Plan.** The agent inspected the code and data and proposed an approach. Example: `docs/etapa2_proposta.md`. Nothing was implemented before the plan was approved.
2. **Implement** in small, testable pieces, reusing existing contracts (`web/lib/data/contracts.ts` mirrors the API's pydantic models).
3. **Test and audit.** Each stage ended with its tests, lint, typecheck and build, and often an independent audit: ingestion audits in `reports/ingestion/`, a full in-memory refit of the models, headless-browser checks of every page.
4. **Human review.** I reviewed the report, asked for changes or approved, and authorized the commit. Commits were never pushed without approval.

### Isolation and conflicts

- **Ownership.** `web/**` belongs to Claude Code. `src/**`, `tests/**`, `configs/**`, `scripts/**` and `bi/**` belong to Codex. Files on the API contract change only through a contract-first flow.
- **Worktrees.** Each agent works in its own folder and branch, so neither touches the other's files mid-task. The first one, for Power BI, was created only after approval.
- **When the boundary held.** In the ML showcase, the frontend agent needed backend code it does not own. It wrote its analysis under `research/` and left a written handoff for Codex (`research/ml-showcase/HANDOFF_CODEX.md`) instead of editing `src/`.

### What the verification caught

These are examples of agents and checks finding real problems, all recorded in the repository:

- A Polars join that silently reordered rows after sorting. Found while verifying rankings, fixed with `maintain_order`, and covered by a regression test (`test_rankings_keep_their_order_across_runs`).
- A baseline card showing the wrong baseline in the dashboard, caught in review and fixed in the export.
- The analyst's verifier rejecting a draft that attached "12" to the wrong metric (`reports/agent/live_repro_case1.json`).
- A method change made after seeing a result. It is disclosed in decision 9, which notes that the verdict deserves less weight.
- Page headers painted under the animated sky, and card content drawn over the sticky header. Both found by screenshot audits and fixed with stacking changes.

I did not measure time saved, so this study makes no productivity claim. The qualitative benefit:
- Each stage got broad, consistent implementation and testing quickly.
- The human time went to decisions, review and validation rather than boilerplate.

## Technical architecture

```
ANAC CSV (~20 GB, never modified)
  → anac-ingest      Polars, chunked and resumable, audited     → Parquet dataset "flights"
  → anac-features    point-in-time features, purged splits       → data/features/v1
  → anac-models      LightGBM + baselines, frozen with hashes    → models/v1
  → anac-analytics   star schema, validated against DuckDB SQL   → data/analytics/v1 (Parquet)
  → anac-api         FastAPI, GET only (+ analyst chat)          → /v2/*, /v2/analytics/*
  → web/             Next.js 16, React 19, TypeScript, Tailwind  → dashboard, ML Studio, analyst
```

- **Data.** Polars for ingestion and features, DuckDB for independent validation, Parquet throughout. The analytical layer is checked before publishing: monthly totals of 10 measures agree with a separate DuckDB computation for all 308 months.
- **API.** FastAPI, read-only, with filters validated against fixed patterns, so they cannot become a query. Every response carries its period and absent months.
- **Analyst.** An OpenAI-compatible tool-calling client (Groq by default). The key stays on the server.
- **Models.** LightGBM with one configuration fixed before validation, compared with simple baselines through a block bootstrap.

## Key features

- Period picker with presets and the period kept in the URL. Accessible autocomplete over 1,180 airports and 317 carrier codes.
- Directed routes, a swap button, and server-side pagination.
- Absent months shown as gaps, never zeros, with a warning.
- Definitions of each measure on hover and keyboard focus.
- A floating analyst that keeps the conversation across pages and never contacts the provider just by opening.
- DAY and NIGHT themes, desktop and mobile.

## ML research findings

All results are 2023 validation, not test results and not forecasts (`research/ml-showcase/REPORT.md`):

| Model | Result | Verdict |
|---|---|---|
| A — daily airport movements | LightGBM WAPE 10.10% vs 10.30% for a weekday rule | No conclusive gain. The rule is kept. |
| B — load factor by route and carrier | 6.06 vs 6.54 pts seat-weighted MAE | Small, conclusive gain |
| D — route passengers and seats | WAPE 22.24% / 22.40% vs 25.31% / 25.73% | Better at 1–3 months. **About −12% bias**, and no better at 6 months |

The study reproduces every metric from the saved artifacts, and a fresh in-memory refit gave bit-identical predictions. The 2024–2025 test was deliberately **not run**: that period was partly seen during the audit, and the models are due to be retrained first.

## Engineering challenges

- **20 GB on a laptop.** Chunked, resumable ingestion with memory checks, and lazy queries everywhere.
- **Leakage.** Feature functions raise an error if data after the cutoff reaches them, and tests scramble the future to prove the features do not change.
- **Unknown versus zero.** Four absent months propagate as nulls through lags, means, charts and comparisons.
- **Honest LLM answers.** A numeric verifier, sources attached by the backend, and refusal when verification fails.
- **Two agents, one repository.** Shared rules, ownership by directory, worktrees, and a contract-first flow.

## Results

- **Tests:**
  - 334 backend tests (pytest), with ruff and mypy in strict mode;
  - 81 frontend tests (Vitest), with typecheck, lint and production build;
  - 52 integration tests against the live API (no model calls).
- **Reproduction:** all model metrics are reproduced exactly from the saved artifacts, and the frozen model hashes match their manifests.
- **Analyst demo:** five recorded real cases. Every quantitative answer agrees with an independent check of the data, and one known gap is documented (`docs/portfolio/ANALYST_DEMO.md`).

## Limitations

- **Missing data:** four months are absent until the official files are recovered.
- **Test not run:** the 2024–2025 test has not been run.
- **Model D:** under-forecasts in a growth year.
- **Analyst reach:** it has no carrier tool and no history beyond the latest 12 months, and its numeric check is heuristic.
- **Map coverage:** only 320 of 1,180 airports have coordinates.
- **Not deployed:** the deployment is prepared but not published, and the Docker images have not been built yet.

## Future improvements

- Recover the absent months, retrain as `models/v2`, then run the sealed test once.
- Add a carrier tool and a history tool to the analyst, through the protected change process.
- An interactive route map, using only airports with published coordinates.
- Finish the Power BI semantic model (Codex, in progress).
