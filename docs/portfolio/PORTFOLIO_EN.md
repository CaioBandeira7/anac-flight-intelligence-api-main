# ANAC Flight Intelligence — portfolio overview

[Live dashboard](https://anac-flight-intelligence-api-main.vercel.app/dashboard) · [English presentation](presentation/anac-flight-intelligence-presentation-en.pdf) · [Source repository](https://github.com/CaioBandeira7/anac-flight-intelligence-api-main)

An end-to-end platform that turns 22,120,241 ANAC aviation records (2000–2025) into traceable market analysis, temporal model evaluation and a tool-grounded AI analyst.

## What I built

- Audited, resumable ingestion of approximately 20 GB into monthly Parquet, with independent read-back and explicit line accounting. Historical run: 308 observed months and no rejected records; suspicious values remain flagged rather than silently corrected.
- A seven-table analytical layer with directed routes, explicit passenger scopes and missing-month handling. FastAPI serves read-only data; Next.js provides market, airport, route and airline views.
- Four LightGBM regressors compared with ten baseline references on saved 2023 selection-model predictions. A retains its baseline because the improvement is inconclusive. B records 6.06 pp seat-weighted MAE against 6.54 pp; D records 22.24% passenger and 22.40% seat WAPE against 25.31% and 25.73%.
- A Groq tool-calling analyst with five fixed read-only tools, code-attached sources, heuristic numeric verification and per-process usage limits. Unsupported drafts receive one correction attempt and then a refusal.
- Docker/Render backend and Next.js/Vercel frontend. Consolidated validation: 368 Python passed, 11 skipped; 91 frontend passed; lint, types and build passed.

## Limits I can defend

The 2024–2025 holdout was partially exposed but not scored. Historical D training treated four globally missing months as zero; the loader is fixed, but v1 has not been retrained and its historical metrics do not measure the correction. D under-forecasts by approximately 12% and does not show a gain at every horizon. C is not trained. These results are validation, not future forecasts; no operational prediction endpoint exists.

Seat occupancy is paid passengers/seats, not RPK/ASK. The verifier checks numeric membership, not guaranteed entity/metric attribution. Rate-limit counters are in memory per process. There are no fares or prices in the data.

## Ownership and AI-assisted work

I directed the product scope, counting rules, methodological decisions and review. Claude Code and Codex implemented and reviewed work under written constraints, isolated branches and explicit human approvals. I do not claim a measured productivity improvement or commercial impact.

[Evidence and reproducibility](VALIDATION.md) · [Technical case study](CASE_STUDY.md) · [Model catalog](../ml/en/MODEL_CATALOG.md)
