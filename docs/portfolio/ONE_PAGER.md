# ANAC Flight Intelligence — one-page overview

**Problem:** make Brazil's open aviation data useful without hiding counting rules, gaps or model limitations.

**System:** 22,120,241 ANAC records → audited monthly Parquet → analytical star schema and temporal features → FastAPI → Next.js dashboard and fixed-tool Groq analyst.

**Evidence:** four LightGBM regressors, ten baseline references, 26 web charts and 37 report figures. A: WAPE 10.10% vs 10.30%, inconclusive. B: weighted MAE 6.06 pp vs 6.54 pp. D: historical WAPE 22.24% passengers and 22.40% seats, with bias and horizon limits. 368 Python passed, 11 skipped; 91 frontend passed.

**Limits:** D has not been retrained after correcting missing targets; the holdout is partially exposed but unscored; C is not trained. Historical evaluation is not future forecasting. Numeric verification is heuristic, and quotas are per-process memory state.

**Role:** product direction and technical review by Caio Bandeira, with Claude Code and Codex implementing under written constraints and human publication approval.

[Live](https://anac-flight-intelligence-api-main.vercel.app/dashboard) · [10-slide deck](presentation/anac-flight-intelligence-presentation-en.pdf) · [Case study](CASE_STUDY.md) · [Validation](VALIDATION.md)
