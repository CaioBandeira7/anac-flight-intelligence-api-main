# Technical interview guide

## A two-minute explanation

“I directed an aviation data platform that processes 22,120,241 open records into audited Parquet, an analytical star schema, a FastAPI/Next.js application and a tool-grounded AI analyst. I used Claude Code and Codex under written rules and human review. The strongest evidence is the ability to trace a number and explain where it stops being reliable: keeping A's baseline, disclosing D's historical defect and separating validation from forecasting.”

## Questions to prepare

**What is generative AI here?** The Groq tool-calling analyst and its controlled response flow. LightGBM is supervised tabular forecasting, not GenAI. The fixed tools limit data access; there is no vector retrieval system or unrestricted SQL agent to claim.

**How do you prevent hallucinations?** Tool schemas, fixed read-only functions, code-attached provenance and a numeric-membership verifier. One corrective attempt is allowed before refusal. This does not prove semantic attribution: a real number can still be attached to the wrong entity or period.

**Why LightGBM?** Tabular lags, calendar effects, categories, interactions and a conservative training configuration. There is no evidence of superiority to every neural network or boosting alternative. Baselines are part of the experiment, not decoration.

**Why is A not adopted?** 10.10% versus 10.30% WAPE is a point-estimate difference; its paired CI includes zero. Keeping the simpler recent-weekday baseline is the evidence-based result.

**What is wrong with D?** Four globally missing months became zero labels in the historical loader. The correction excludes them, but the frozen v1 models have not been retrained. Their 22.24%/22.40% aggregate WAPE does not validate corrected training. Bias is approximately −12%; horizon-6 point estimates are worse without proving inferiority statistically.

**Is your test really blind?** No. 2024–2025 labels have not been scored, but annual totals were previously inspected. This partial exposure is disclosed. I would not tune on that holdout or advertise it as fully blind.

**Do you forecast the future in production?** No. The dashboard displays saved 2023 evaluation. Low-level booster prediction code is not an operational inference service. Final refit boosters contain eligible 2023 history and cannot rescore that year as unseen.

**What about C?** Not trained. Its provisional baggage target and investigation are documented; there is no metric to show.

**How are metrics defined?** WAPE sums absolute errors over observed volume. B's MAE uses actual-seat weights and is reported in percentage points. Seat occupancy is paid passengers/seats; passenger load factor is RPK/ASK. WAPE 10% is not 90% accuracy.

**How strong are the intervals?** Twelve target-month clusters, 2,000 bootstrap draws, one validation year. They do not preserve inter-month dependence as moving blocks would; baseline selection and multiple comparisons limit inference. They are not future prediction bands.

**Is the public demo safe at scale?** Keys stay on the backend and routine tests mock the provider. Limits are per client and per process/day, not a distributed hard spending guarantee. CORS is not authentication. No paid call was needed for portfolio generation.

**What did you personally do?** Define scope, methodological/counting rules, stage approvals, review evidence and authorize publication. Be candid that agents implemented much of the code. Do not claim measured productivity, commercial impact or unverified infrastructure guarantees.

**What was tested?** Consolidated validation: 368 Python passed, 11 skipped for absent local inputs; 91 frontend passed with local API. Lint, strict mypy, TypeScript and build passed. 601 checks reconcile ML results. See [portfolio validation](../../portfolio/VALIDATION.md).

## Demonstration discipline

Use the [English demo script](../../portfolio/DEMO_SCRIPT_3MIN.md). Prefer recorded Analyst cases when a live paid call is unavailable or unauthorized. Show loading/error states honestly; do not replace missing data with synthetic predictions. Finish with the limitation you would address next, not an unmeasured business result.
