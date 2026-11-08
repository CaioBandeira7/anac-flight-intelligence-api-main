# AGENTS.md — ANAC Flight Intelligence

Rules for every coding agent in this repository (Claude Code, Codex). Next.js-specific rules are in `web/AGENTS.md`.
Report to the owner in Portuguese. State what was run and what was not verified.

## What this is

A reproducible data and ML platform on ANAC air transport microdata, 2000-01 to 2025-12:

```
raw CSV (data/raw/anac_brazil.csv, ~20 GB, never modified)
  → anac-ingest → data/processed (dataset "flights")
  → anac-features → anac-models (frozen in models/v1)
  → serving payloads (data/serving/v1) and anac-analytics (data/analytics/v1, star schema)
  → anac-api (read-only FastAPI) → web/ (Next.js dashboard) and the AI Aviation Analyst
  → bi/ (Power BI, planned) reads data/analytics/v1
```

`data/`, `models/` and every Parquet file are ignored by Git and rebuilt locally.

## Layout

| Path | Contents |
|---|---|
| `src/anac/ingestion`, `validation` | CSV to Parquet, rules, audits |
| `src/anac/features`, `models`, `evaluation` | Point-in-time features, LightGBM, baselines |
| `src/anac/analytics` | Analytical tables and `AnalyticsStore` (read-only queries) |
| `src/anac/serving` | Payload export (`export_all`) |
| `src/anac/api` | FastAPI: `app.py`, `analytics.py`, `schemas.py` |
| `src/anac/agent` | Analyst: tools, LLM client, numeric verifier |
| `configs/*.toml` | Ingestion, features, models, supplements |
| `tests/` | pytest, synthetic data (`real_data` marker skips without the CSV) |
| `docs/` | analytics, decisions, features, ingestion, models, supplements |
| `reports/` | Audits and evaluation reports |
| `web/` | Next.js app; contracts in `web/lib/data/contracts.ts` |
| `bi/` | Power BI project (planned, not created yet) |
| `00_*.py`–`07_*.py`, `dashboard.html`, `Dockerfile.bak` | Legacy v1. Do not delete or edit. |

## Stack

- Python 3.12 in `.venv` (`requires-python >=3.11,<3.14`): Polars, DuckDB, LightGBM, FastAPI, httpx. Ruff (line 100), mypy strict on `src`, pytest.
- Web: Next.js 16.4.5, React 19.3, TypeScript, Tailwind 4, framer-motion, Vitest + Testing Library. Read `web/AGENTS.md` before writing Next code.

## Commands (Windows, repo root)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python -m pip install -e . --no-deps

.venv\Scripts\python -m pytest
.venv\Scripts\ruff check src tests
.venv\Scripts\ruff format --check src tests
.venv\Scripts\mypy src

.venv\Scripts\anac-api        # http://127.0.0.1:8000/docs
```

Heavy or state-changing commands. Ask the owner before running them:
`anac-ingest sample | full --confirm-full | status | supplements <status|publish|revisions|publish-evaluation>`,
`anac-features build | baselines`, `anac-models train` (refuses to overwrite frozen models), `anac-analytics build`.
Serving export has no CLI: `anac.serving.export.export_all(cfg, airports_csv, output)`.

API settings: `ANAC_API_HOST`, `ANAC_API_PORT`, `ANAC_SERVING_DIR`, `ANAC_ANALYTICS_DIR`,
`ANAC_CORS_ORIGINS` (default `http://localhost:3000`).

Web (in `web/`): `npm ci`, `npm run dev | build | start | lint | typecheck | test`.
`web/.env.local`: `NEXT_PUBLIC_DATA_SOURCE=api|mock`, `NEXT_PUBLIC_API_URL`.
Live integration tests: `ANAC_API_URL=http://127.0.0.1:<port> npx vitest run tests/analytics.test.tsx tests/dashboard.test.tsx`.

Before reporting done: the backend checks above; in `web/`, typecheck, lint, test and build.

## API contract

- GET only, except `POST /v2/analyst/chat`. Nothing writes data.
- Responses are `{ data, meta: { source, isDemo, generatedAt, note } }`.
- Pydantic models mirror `web/lib/data/contracts.ts`. A change to one is a change to both, in the same feature, contract first.
- `/v2/analytics/*` filters: airports ICAO or IATA (3–4 chars), carriers ICAO or IATA (2–3), months `YYYY-MM`,
  `from > to` → 422, `limit` 1–500. Missing tables → 503, never invented data.
- Every analytics response states its period and `absent_months`.
- Endpoints are listed in `docs/analytics.md` and `docs/models.md`; `tests/test_api.py` asserts the exact set.

## Data rules

- Passenger measures use the passenger scope, counted per flight leg. Routes are directed: A→B ≠ B→A.
- Never sum or average `load_factor_paid`. Recompute it as Σ paid passengers / Σ seats.
- "Flights" (all takeoffs), "passenger flights" (passenger scope) and "aircraft movements" (takeoffs + landings)
  are different counts. Never present them as equivalent.
- Absent months: 2015-08, 2016-02, 2018-07, 2020-08. They are unknown, not zero: listed, left out of series
  and shown as gaps. A known month without flights is a true zero.
- Only 320 of 1,180 airports have coordinates. Never invent locations.
- The data has no fares or prices. Nothing may suggest otherwise.
- Process the 20 GB source lazily or in chunks; never load it whole into memory.

## ML rules and known limitations

- Chronological splits, point-in-time features, 2-month publication lag, purged boundaries.
- The 2024–2025 test is sealed and has not been run. Never tune or select on it.
- A model is adopted only if it beats its best baseline with a 95% interval excluding zero.
- Do not retrain, overwrite or replace `models/v1` without explicit authorization.
- Results are 2023 validation, not forecasts. No prediction endpoint exists.
  - Module A: the baseline is selected; LightGBM's 10.10% against 10.30% WAPE is not conclusive.
  - Module B: LightGBM 6.06 against 6.54 pts MAE.
  - Module D: LightGBM 22.24% (passengers) and 22.40% (seats) WAPE; bias ≈ −12%; no gain at 6 months.
  - Module C: not trained.
  - Training lacks the four absent months.
- Decisions are logged in `docs/decisions.md`. Add new ones there.

## Never invent

No fabricated data, metrics, forecasts, evidence of runs, commercial conclusions, or capabilities of the analyst.
If something was not run or verified, say so.

## Frontend design (approved, preserve)

- Keep the landing page, boarding pass, CloudShader sky, Liquid Glass cards, DAY/NIGHT themes, typography and layout.
  No redesign without the owner's approval.
- Reuse what exists: `Card`, `DataTable`, `TrendChart`, `BarList`, `PeriodPicker`, the comboboxes, `InfoTip`/`Term`,
  `Overlay` (popovers render outside the glass cards).
- Every view handles loading, error and empty states, and ignores stale responses (`useResource` with `AbortSignal`).
  Mock data is always labelled DEMO.

## Power BI (`bi/`)

Owner: Codex. Others read only.

- Scope: semantic model, DAX measures, exports and their validation.
- Source: the analytical tables in `data/analytics/v1`, read as they are. Never edit, overwrite or rebuild them
  from `bi/`; a change to a table goes through `src/anac/analytics` and its validation.
- Follow the relationships, measures and caveats in `docs/analytics.md`: one fact per visual, load factor as a ratio
  of sums, absent months shown as missing, never as zero. Those steps have not yet been tested inside Power BI.
- Keep three kinds of content apart and label each:
  1. Historical facts: values read from the tables.
  2. Derived indicators: measures computed from those facts, with their formula.
  3. Inferences: interpretations. Marked as such, never shown as data.
- No invented data, forecasts or commercial conclusions. Model results are 2023 validation only.
- Every measure or export is checked against the API or the tables before it is reported.
- Do not commit data, Parquet or large exports. Ask the owner which Power BI files belong in Git.

## Credentials and paid calls

- `GROQ_API_KEY` lives only in the root `.env`, used by the backend. Never in the frontend or in a `NEXT_PUBLIC_*` variable.
- No calls to Groq without authorization: `/v2/analyst/status` and `/v2/analyst/chat` contact it, and so does
  `scripts/validate_analyst_live.py`. `/v2/analyst/config` does not. Automated tests use mocks.
- Changes to the analyst's prompts, numeric verifier, status logic or tools need explicit authorization.

## Git

- No commit, push, branch switch, worktree, merge, rebase or destructive operation without the owner's explicit
  authorization. Never discard changes you did not make.
- Never commit `data/`, `models/`, Parquet, `.env*`, `web/.env.local`, `.next/`, archives or snapshots.
- Do not delete the legacy scripts or modify `data/raw/anac_brazil.csv`.

## Ownership and parallel work

| Area | Owner |
|---|---|
| `web/**` | Claude Code |
| `src/**`, `tests/**`, `configs/**`, `scripts/**` | Codex |
| `bi/**` | Codex |
| `src/anac/api/schemas.py`, `src/anac/api/analytics.py` ↔ `web/lib/data/contracts.ts` | Shared contract |
| `docs/**`, `AGENTS.md`, `README.md` | Whoever changes the behaviour described; the owner approves |

Others read only. Shared contract files change through the contract flow: the owner defines the contract, Codex lands
the endpoint, schema, tests and docs, the frontend builds against the mock provider meanwhile, then integrates once
the backend is merged.

Planned worktrees (created only with authorization):

| Folder | Branch | Use |
|---|---|---|
| `D:\anac-flight-intelligence-api-main` | `feat/ingestion-v2` | Integration; the owner merges |
| `D:\anac-fi-web` | `claude/<feature>` | Frontend |
| `D:\anac-fi-backend` | `codex/<feature>` | Backend, ML, tests |
| `D:\anac-fi-bi` | `codex/bi-<feature>` | Power BI |

In a worktree:

- Create its own `.venv`: the main `.venv` is an editable install of the main folder's `src`.
- Point `ANAC_SERVING_DIR` and `ANAC_ANALYTICS_DIR` at the main folder's `data/`.
- Do not copy `.env`.
- Use separate ports (web 3000 and API 8000 for the frontend, API 8001 for the backend).
