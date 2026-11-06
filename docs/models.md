# Models and API

LightGBM models for modules A, B and D, compared with baselines on 2023. The final test on 2024-2025 has not been run.

```powershell
.venv\Scripts\anac-models train   # refuses to overwrite frozen models
.venv\Scripts\anac-api            # http://127.0.0.1:8000/docs
```

## Method

- One conservative configuration in `configs/models.toml`, fixed before seeing validation results. No hyperparameter search.
- Fit on targets from 2013, with early stopping on 2022 targets, so 2023 is scored once and plays no part in training.
- Volumes are predicted as a ratio to the unit's recent level, with L1 loss weighted by that level, which optimises WAPE directly. Load factor uses L1 weighted by seats.
- After scoring, each model is refit on everything known at the first test origin with the same number of rounds, then frozen in `models/v1` with hashes in a manifest. Reports are in `reports/models/`.

## Results on validation (2023)

Differences are paired on the same rows. A model "beats" its best baseline only if the 95% interval, from a block bootstrap over 12 months, excludes zero.

| Module | Metric | LightGBM | Best baseline | Difference (95% interval) | Beats it? |
|---|---|---|---|---|---|
| A | WAPE | 10.10% | 10.30% | -0.21 (-0.84 to 0.35) | No |
| B | Seat-weighted MAE | 6.06 pts | 6.54 pts | -0.48 (-0.94 to -0.04) | Yes |
| D, passengers | WAPE | 22.24% | 25.31% | -3.07 (-4.97 to -1.09) | Yes |
| D, seats | WAPE | 22.40% | 25.73% | -3.33 (-5.32 to -1.19) | Yes |

The dataset still lacks four training months. These results have not been confirmed on the test period.

## API

Read-only, GET only. Each response is validated against models mirroring `web/lib/data/contracts.ts`, and a payload that breaks the contract is not served. OpenAPI is at `/openapi.json` and `/docs`.

`/health`, `/v2/overview`, `/v2/airports`, `/v2/routes`, `/v2/models`, `/v2/datasets`, `/v2/modules`, `/v2/analyst/catalog`

Settings: `ANAC_SERVING_DIR`, `ANAC_CORS_ORIGINS`, `ANAC_API_HOST`, `ANAC_API_PORT`.

## Known issues (P1)

1. **Module A:** the model does not beat the recent-weekday baseline. A simple rule is the honest choice unless the test shows otherwise.
2. **Module D, 6 months ahead:** no better than same month last year (+1.6 and +1.5 points, intervals include zero).
3. **Module D bias:** about -12% on passengers and seats in 2023. Training ends during the recovery, so levels run low.
4. **High-pressure event:** PR-AUC rose from 0.589 to 0.601, but Brier worsened from 0.186 to 0.198.
5. **Not evaluated:** the 2003 window, pandemic treatment and a 3-month publication lag.
6. **Pending data:** the four missing months and the 2026 evaluation still need the official ZIPs. Models must be retrained on `flights_v2_1` and frozen as `models/v2`.
7. **Dashboard:** `/v2/models` shows LightGBM alongside baselines, and the frontend may need to label them.

## AI Aviation Analyst

One agent over five fixed, read-only tools (`src/anac/agent/tools.py`): market overview, airports, routes, model results and data coverage. There is no SQL or free-form query, and arguments are validated and capped.

- **Provider:** any OpenAI-compatible API with tool calls, Groq by default. Set `GROQ_API_KEY` in `.env` (see `.env.example`), and optionally `ANAC_LLM_PROVIDER`, `ANAC_LLM_BASE_URL`, `ANAC_LLM_MODEL`, `ANAC_LLM_API_KEY`. The key stays on the backend.
- **Endpoints:** `GET /v2/analyst/status` and `POST /v2/analyst/chat`.
- **Grounding:** sources are attached by the backend from the tools actually called. Every number in an answer must match a tool result, allowing for rounding, unit conversion and integers up to 12. An unmatched number triggers one correction, then a refusal.
- **Limit of that check:** it verifies that a number exists in the tool results, not that it is attached to the right entity, so a model could still misattribute a real figure.
