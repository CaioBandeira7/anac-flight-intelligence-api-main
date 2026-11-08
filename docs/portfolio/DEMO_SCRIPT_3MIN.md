# Three-minute demo — English

Pre-open the dashboard, ML Studio, recorded Analyst cases and English deck. Request `/health` to wake the API if necessary. New Groq calls are optional and require the presenter's consent; use the recorded cases by default.

| Time | Screen | Narration |
|---|---|---|
| 0:00–0:20 | Landing and README | “ANAC Flight Intelligence turns 22,120,241 aviation records into traceable analysis. The challenge is getting counting rules and evidence right.” |
| 0:20–0:50 | Dashboard | “Every measure has a period and scope. Flights, passenger flights and airport movements differ. Missing months remain gaps.” Switch DAY/NIGHT. |
| 0:50–1:10 | Routes | “Routes are directed. Seat occupancy is total paid passengers divided by seats; it is distinct from passenger load factor, RPK divided by ASK.” |
| 1:10–2:05 | ML Studio, A/B/D | “These are 2023 validation results, not forecasts. A's gain is inconclusive, so its baseline stays. B's weighted MAE is 6.06 percentage points against 6.54. D's historical passenger WAPE is 22.24%, but the audit found zero-filled missing targets in training. The loader is fixed; the models have not been retrained. The holdout is partially exposed but unscored; C is not trained.” |
| 2:05–2:40 | Recorded Analyst cases | “Five fixed read-only tools ground the answer. Sources are attached by code. Numeric verification checks membership, not guaranteed semantic attribution. Usage limits protect a public demo, but are per-process memory counters.” |
| 2:40–3:00 | README and deck | “368 Python tests passed, 11 skipped; 91 frontend tests passed. I directed the project with AI-assisted implementation and review. The code and evidence are available, including the cases where the models do not help.” |

## Recorded figures and fallback

2025 paid passengers: **131,593,763**. Directed CGH→SDU: **1,968,523**, seat occupancy approximately **76.94%**. These are historical analytical figures, not current demand or unique travellers. Source: [recorded Analyst verification](ANALYST_DEMO.md).

If the API is unavailable, show the screenshots and recorded cases with their capture date. If a live Analyst response fails or reaches a quota, use its recorded example; do not imply a new answer was produced. [Portuguese script](pt-BR/DEMO_SCRIPT_3MIN.md).
