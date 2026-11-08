# ML research & showcase — modules A, B and D

Reproduction, error analysis, figures and the technical report for the forecasting models. The report is [REPORT.md](REPORT.md), also rendered as [REPORT.pdf](REPORT.pdf).

**Scope.** Every number is a **validation result on 2023**: out-of-sample, from models whose configuration was fixed before validation. The sealed 2024–2025 test was **not run**; see Section 6.4 of the report. Nothing here is a live forecast.

## What this folder does

| Script | Reads | Writes |
|---|---|---|
| `reproduce.py [--refit]` | `data/features/v1`, `models/v1`, `reports/models` | `results/reproduction.json` |
| `analysis.py` | the same, plus `data/analytics/v1` | `results/analysis.json`, `figures/*.png` and `*.svg`, `web/public/ml/showcase.json` |
| `build_pdf.py` | `REPORT.md`, `figures/` | `REPORT.html`, `REPORT.pdf`, `web/public/ml/report.pdf` |

None of them writes to `data/`, `models/`, `reports/`, `src/` or the Parquet files. They import the project's own functions (`load_module_frame`, `compare`, `fit_selection_model`) so the metrics are computed exactly as in training. `--refit` retrains the selection models **in memory only**, to prove that the saved predictions are reproducible.

## Run

```powershell
# repository root; needs the locally built data/features/v1, models/v1 and data/analytics/v1
.venv\Scripts\python -m pip install -r research\ml-showcase\requirements.txt
.venv\Scripts\python research\ml-showcase\reproduce.py --refit   # ~40 s
.venv\Scripts\python research\ml-showcase\analysis.py            # ~20 s
.venv\Scripts\python research\ml-showcase\build_pdf.py           # needs Chrome or Edge
```

The PDF is printed by headless Chrome or Edge from the HTML, with no network access.

## Reproduction status (last run)

| Check | Result |
|---|---|
| Metrics recomputed vs `reports/models/*.json` | Identical for A, B, D-pax and D-seats |
| In-memory refit vs saved predictions | Bit-identical (maximum difference 0.0), same best iteration |
| `models/v1` SHA-256 vs manifests | All four match |
| `test_period_used` in every manifest | `false` |

## In the platform

The dashboard's **ML Studio** (`/dashboard/ml-studio`) reads `web/public/ml/showcase.json`, which holds aggregates only plus a 400-row sample per task. It links to `web/public/ml/report.pdf`. Rerun `analysis.py` and `build_pdf.py` to refresh both.

Work that belongs to the backend (Codex) is listed in [HANDOFF_CODEX.md](HANDOFF_CODEX.md).
