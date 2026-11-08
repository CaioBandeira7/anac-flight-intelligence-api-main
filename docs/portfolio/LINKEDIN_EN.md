# LinkedIn post — English

Suggested image: [English cover](assets/cover/cover-github-1280x640-en.jpg). Optional carousel: [10-slide PDF](presentation/anac-flight-intelligence-presentation-en.pdf).

---

I built ANAC Flight Intelligence to turn Brazil's open aviation data into analysis that can be checked.

The project processes 22,120,241 records from 2000–2025 into audited Parquet and a seven-table analytical model, then serves a Next.js dashboard through FastAPI. It also includes a Groq tool-calling analyst with fixed read-only tools, source attribution and heuristic numeric checks.

The most useful part was learning where the evidence stops:

- Four LightGBM regressors are compared with simple baselines on 2023 validation. For airport movements, the gain is inconclusive, so the baseline stays.
- An audit found missing target months treated as zero in historical route-model training. The loader is corrected, but the frozen models have not been retrained; I do not claim the historical scores validate that fix.
- The 2024–2025 holdout was partially exposed through earlier inspection, but has not been scored. Module C is not trained. The application shows evaluation, not future forecasts.

Validation: 368 Python tests passed, 11 skipped; 91 frontend tests passed. The repository includes six English ML guides, chart documentation and a ten-slide presentation.

I directed scope and review, using Claude Code and Codex under written rules and explicit approvals. No simulated forecasts or measured commercial-impact claims are used.

Live: https://anac-flight-intelligence-api-main.vercel.app/dashboard
Code: https://github.com/CaioBandeira7/anac-flight-intelligence-api-main

#DataScience #MachineLearning #GenerativeAI #Python #OpenData #Aviation

---

Short version: An aviation data portfolio combining audited ingestion, temporal ML evaluation and a tool-grounded AI analyst—with the limitations documented alongside the results.

[Sources and validation](VALIDATION.md) · [Portuguese version](LINKEDIN_PT.md). This file is draft copy; nothing has been posted to LinkedIn.
