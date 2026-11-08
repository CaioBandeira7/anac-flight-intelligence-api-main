# Handoff to Codex: backend and ML follow-ups

`AGENTS.md` gives `src/**`, `tests/**`, `configs/**` and `scripts/**` to Codex, so this study changed none of them. The items below are proposals. None is implemented, and none should start without the owner's approval.

## 1. Serve the validation results through the API (optional)

Today the ML Studio reads a static file, `web/public/ml/showcase.json`, built by `research/ml-showcase/analysis.py`. If the API should own it, the contract would be:

| Endpoint | Response |
|---|---|
| `GET /v2/models/validation` | `{ data: Showcase, meta }`. `Showcase` is defined in `web/lib/data/showcase.ts`: `version`, `evaluated_on`, `tasks.{a,b,d_pax,d_seats}`, `eda` |

- **Source:** the same computation as `analysis.py`, moved into `src/anac/serving/export.py` as one more exported payload, so it stays read-only and precomputed.
- **Tests:**
  - Values equal `reports/models/*.json`.
  - `scatter` has at most 400 rows.
  - Every `monthly.month` is in 2023.
  - No test-period month appears.
- **Frontend change after it lands:** `loadShowcase` points at the endpoint instead of `/ml/showcase.json`. This is the shared contract flow in `AGENTS.md`.

## 2. Move the reproduction check into the test suite (optional)

`reproduce.py` proves that the saved validation predictions are bit-identical to a fresh refit. A slow test marked `real_data` could assert the same, skipped when the data is absent.

## 3. Final test on 2024–2025 (owner's decision)

Not run, for the reasons in Section 6.4 of `REPORT.md`: decision 3 (partial exposure) and the plan to retrain as `models/v2` first. When it is approved:

1. Unseal the targets through the documented procedure, with a recorded reason.
2. Score the **frozen** models once, without tuning.
3. Report against the same baselines, with the same block bootstrap.

## 4. Experiment worth validating before any test: level correction for Model D

Model D under-forecasts by about 12% in 2023. The market grew 15.3% over 2022, and trunk routes grew 19–44%. A correction using information known at the cutoff, such as the year-over-year change of the latest known months at market or origin level, could be evaluated on validation only. It must be fixed before the test is unsealed.
