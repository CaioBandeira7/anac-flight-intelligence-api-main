# Building an aviation intelligence platform with AI-assisted development

**Caio Bandeira · ANAC Flight Intelligence**

## Problem and design

ANAC aviation microdata spans approximately 20 GB and 22,120,241 records. Correct analysis requires explicit definitions: passenger counts are per leg, routes are directed, airport movements count endpoints and four months are absent. The project separates ingestion, analytical aggregation, ML evaluation and the LLM interface so each claim can be traced to its source.

## My role

I set scope and counting rules, approved stages, reviewed evidence and authorized publication. Claude Code and Codex wrote and reviewed code under shared rules. I do not claim sole manual authorship, measured time savings or business outcomes. Commit history, `AGENTS.md` and [decisions](../decisions.md) record the work.

Claude's v3 includes the deployed API/dashboard, corrected rankings, Groq integration and rate limiting. Codex's audit examined four LightGBM regressors and ten baseline references, documented the charts and corrected methodological code. The work was integrated by Git in a separate branch, tested and merged without changing the frozen model artifacts. The separate Power BI workstream is outside this portfolio release; no claim is made about its current state.

## Architecture and engineering decisions

Ingestion uses bounded chunks, atomic publication, resumable manifests and line accounting. DuckDB provides independent read-back. The analytical layer has three dimensions and four facts; filtered queries preserve grains and denominator scope. FastAPI contracts are mirrored in TypeScript. Next.js provides loading, error and empty states with explicit API/DEMO data labels.

The Analyst accesses five fixed read-only tools through Groq, not arbitrary SQL or unrestricted history. A numeric verifier can trigger one correction and then refusal. It checks whether figures occur in results, not guaranteed entity/metric association. Server-side keys, per-client windows and a daily quota limit exposure; in-memory quotas are not distributed protection.

## What the audit caught

- Ranking order could change after a join; the v3 correction and regression tests preserve order.
- Historical D training treated globally missing months as zero target values. The loader now excludes those months, while keeping known route inactivity as legitimate zero. Frozen v1 remains unchanged.
- Average precision mishandled tied scores. The correction groups equal-score thresholds.
- Occupancy bias used an unweighted relative ratio with misleading interpretation. The UI now reports signed seat-weighted error in percentage points and preserves the legacy field.
- The original refit reproduction claim could not be carried forward after the loader correction. Current verification reconciles saved validation predictions without refitting.

## Evidence and limits

Consolidated checks: **368 Python passed, 11 skipped; 91 frontend passed**, plus lint, formatting, strict mypy, types and production build. The ML reconciliation passed 601 checks and preserved hashes of 29 input artifacts.

A's improvement is inconclusive; its baseline stays. D is biased and does not improve every horizon; it has not been retrained after the correction. The 2024–2025 holdout was partially exposed but not scored. C is not trained. A single validation year with 12 month clusters is limited evidence of generalization. There is no operational prediction endpoint or fare data.

## What I would defend in an interview

The contribution is a traceable end-to-end system and evidence-based decisions, including keeping a simpler method when needed. The GenAI component is tool calling and verification; LightGBM is supervised forecasting, not generative AI. New training, a distributed quota store or broader tool coverage would require a separate justified task, not a last-minute feature added for presentation.

[Architecture](../ml/en/ML_ARCHITECTURE.md) · [Interview guide](../ml/en/INTERVIEW_GUIDE.md) · [Validation](VALIDATION.md) · [Original case-study snapshot](pt-BR/CASE_STUDY_original.md)
