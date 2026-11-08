"""Build English ML entry points from tracked audit evidence. No data reads or training."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/ml/en"


def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def write(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(body.strip() + "\n", encoding="utf-8")


def main() -> None:
    audit = load("research/ml-showcase/results/audit.json")
    public = load("web/public/ml/showcase.json")
    catalog = load("docs/ml/visualization-inventory.json")
    note = "\n\nSource: [tracked audit evidence](../../../research/ml-showcase/results/audit.json). The [original detailed Portuguese audit](../MODEL_CATALOG.md) is preserved as secondary material.\n"
    model = """# Model catalog

Four LightGBM regressors across A/B/D; ten baseline references (3/3/2/2 by target). C is not trained. Four legacy neural/boosted pipelines remain archived and unverified under the current temporal protocol.

## Targets, grain and coverage

| Target | Grain | Horizons | Baselines | Feature counts, numeric/categorical |
|---|---|---|---|---|
| A: aircraft movements | Airport × day, top 50 known at each cutoff | 1, 3 months | Same weekday a year ago; trend-adjusted annual; recent weekday mean | 20 / 1 |
| B: paid seat occupancy | Carrier × directed route × month | 1, 3, 6 | Annual occupancy; trailing 12-month mean; trailing 3-month mean | 39 / 3 |
| D: paid passengers | Directed route × month | 1, 3, 6 | Annual level; trend-adjusted annual | 36 / 2 |
| D: offered seats | Directed route × month | 1, 3, 6 | Annual level; trend-adjusted annual | 36 / 2 |

Source: audited ANAC microdata, 2000–2025, 22,120,241 records. Supervised feature/target artifacts stop before the test period. Eligibility uses only cutoff history. B scores units operating in the target month; D includes known inactivity as zero. B/D filters remove duplicates, non-operated/improductive records, zero distance, self-loops, zero paid passengers/seats and flight occupancy above 1.5. Values between 1 and 1.5 remain; do not promise occupancy is bounded by 100%.

A counts operated record endpoints on actual dates with documented date fallbacks. A self-loop can generate two movements. It is not congestion, delay, runway capacity or an arbitrary sum of another layer's takeoff field.

B's legacy `load_factor` target is paid passengers/seats, not RPK/ASK. D describes operated supply and carried passengers, not unconstrained demand, prices or profit.

## Training and transformation

LightGBM GBDT uses L1 objective/metric. Volumes train on `target / historical_level` with historical-level weights, aligning the absolute-error numerator with WAPE. Levels: `hist_level_56` for A; `hist_pax_mean_12` and `hist_seats_mean_12` for D. B directly models occupancy with observed-seat weights for training/evaluation; future observed seats are not an input feature. Predictions are floored at zero; B is not capped at one. Categorical vocabularies are fit on fitting data; unseen categories become missing.

The declared two-month publication lag gives distance = horizon + 2. Selection fitting uses purged 2013–2021 history; early stopping uses 2022; validation uses 2023. Exact selection fitting boundary is `target_month <= 2022-01 - distance`; eligible pre-validation train boundary is `2023-01 - distance`. This is a fixed selection model evaluated across origins, not independent rolling-refit folds.

Final boosters were refit after selecting tree counts, using eligible 2023 data before the first test origin. They cannot independently reproduce the 2023 validation score. Use the saved selection predictions instead.

Parameters in `configs/models.toml`: learning_rate=0.03, num_leaves=31, min_data_in_leaf=200, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5, cat_smooth=20, min_data_per_group=200, max_cat_threshold=32, seed=42, deterministic=true, force_col_wise=true, num_threads=4; maximum 3,000 rounds, early stopping 50. No documented hyperparameter search or demonstrated superiority to every alternative model family.

| Target | Historical fitting rows | Stopping rows | Trees | Final refit rows |
|---|---:|---:|---:|---:|
| A | 306,068 | 27,350 | 98 | 379,068 |
| B | 366,818 | 23,448 | 46 | 442,733 |
| D-passengers | 291,026 | 18,087 | 395 | 350,518 |
| D-seats | 291,104 | 18,099 | 243 | 350,614 |

## Historical defect and safeguards

Missing source months are 2015-08, 2016-02, 2018-07 and 2020-08. The old D loader joined absent targets and filled them with zero: 11,689 passenger and 11,692 seat fitting rows were affected. Current code excludes unknown months before filling known route inactivity. **No frozen model has been retrained, and the performance impact is unknown.** Guards reject test-period dates/months even when split labels are wrong.

The 2024–2025 holdout was partially exposed through previous annual-total inspection but has not been scored. Data revisions and incomplete as-of vintages limit leakage claims. Model C failed the provisional target gate and has no trained artifacts or metric; post-result methodology changes in its investigation are disclosed in decisions.

## Exact feature inventory

Feature names and descriptions below are read directly from the tracked audit. Calendar dates, absolute cutoff stamps and other excluded metadata are not booster features.
"""
    for module in ["a", "b", "d"]:
        model += f"\n### Module {module.upper()}\n\n| Feature | Definition |\n|---|---|\n"
        for feature in audit["modules"][module]["features"]:
            model += f"| `{feature['name']}` | {feature['description']} |\n"
    model += "\n## Artifacts and reproduction\n\n`models/v1` contains frozen boosters/manifests; feature panels, targets and saved selection predictions live under `data/features/v1/module_*`. They are ignored by Git and required separately. `reports/models/module_{a,b,d}.json` and the tracked audit preserve metrics. `scripts/audit_ml.py --artifact-root PATH` reconciles pre-test artifacts without refit. The historical `reproduce.py --refit` record predates the D correction and must not be treated as corrected-model performance. See [results](EXPERIMENT_RESULTS.md) and [prediction guide](PREDICTION_GUIDE.md)."
    write("MODEL_CATALOG.md", model + note)
    results = """# Experiment results

Scope: saved selection-stage predictions against 2023 labels, not 2024–2025 test results or current forecasts. Sources are `reports/models/module_{a,b,d}.json`, the tracked audit and public ML payload.

WAPE = sum(abs(predicted-actual)) / sum(abs(actual)). Weighted occupancy MAE = sum(seats × absolute occupancy error) / sum(seats). Difference = model minus best baseline on the same rows. Negative favors the model. Intervals are paired difference intervals, not subtraction of individual interval endpoints.

| Target | Rows | LightGBM (% or pp) | Baseline | Difference (metric points) | Difference 95% CI | Historical selection |
|---|---:|---:|---:|---:|---|---|
"""
    for key in ["a", "b", "d_pax", "d_seats"]:
        task = public["tasks"][key]
        diff = task["difference_vs_best_baseline"]
        base = task["baselines"][task["best_baseline"]]
        results += f"| {key} | {audit['tasks'][key]['rows']:,} | {task['lightgbm']['value'] * 100:.6f} | {base['value'] * 100:.6f} | {diff['value'] * 100:+.6f} | [{diff['ci95'][0] * 100:+.6f}, {diff['ci95'][1] * 100:+.6f}] | {'LightGBM' if task['beats_best_baseline'] else 'baseline'} |\n"
    results += "\n## Horizon-specific point estimates\n\n| Target | Horizon | LightGBM | Best baseline at this horizon |\n|---|---:|---:|---:|\n"
    for key in ["a", "b", "d_pax", "d_seats"]:
        for h in public["tasks"][key]["by_horizon"]:
            results += f"| {key} | {h['horizon']} | {h['model'] * 100:.4f} | {min(h['baselines'].values()) * 100:.4f} |\n"
    results += """
A is inconclusive overall and at both horizons. B's pooled improvement does not establish a gain at horizons 1/3, whose paired intervals include zero; horizon 6 favors the model. D improves at horizons 1/3; at 6, point estimates are worse and paired intervals include zero. That is not proof of inferiority at horizon 6.

## Bias and secondary diagnostics

Relative aggregate volume bias: A approximately −2.01%, D-passengers −12.21%, D-seats −11.78%. Do not attribute D's bias causally to only the missing-target defect.

B's signed seat-weighted error is **−0.0521517 pp**, with 95% CI approximately **[−1.05063, +0.923085] pp**. Its legacy unweighted relative bias is a different estimand and remains preserved. B's international descriptive MAE is 7.1229 pp versus baseline 6.4980; domestic is 5.8343 versus 6.5512. No segment-specific paired CI establishes universal adoption.

Secondary high-pressure AP is 0.6008393127 for LightGBM versus the tie-corrected baseline 0.5890506146. The historical field named `pr_auc` denotes average precision, not trapezoidal PR AUC. Reported Brier is 0.1977126325 versus 0.18634969 (lower is better): it is not independently reproduced because calibration artifacts are incomplete. Better AP does not imply better calibration.

## Uncertainty and adoption limits

The bootstrap samples 12 target-month clusters independently with replacement, 2,000 draws, seed 42. It preserves within-month dependence, not inter-month autocorrelation as a moving-block bootstrap would. The best baseline was selected and compared on the same year; no multiplicity correction or nested selection bootstrap is reported.

These are historical adoption decisions on one validation year. Revised data lack complete as-of vintages. The 2024–2025 holdout was partially exposed but not scored. D's historical defect affects 11,689/11,692 fitting rows; the loader correction has not been evaluated through new training. C is not trained. No metric is an operational future-forecast guarantee.

601 checks passed during reconciliation, with original input hashes preserved. Full paired horizon intervals remain in [audit.json](../../../research/ml-showcase/results/audit.json) and the [original detailed results](../EXPERIMENT_RESULTS.md).
"""
    write("EXPERIMENT_RESULTS.md", results)
    write(
        "PREDICTION_GUIDE.md",
        """# Prediction guide

## What is implemented

1. **Historical temporal validation:** saved predictions from selection models for 2023, evaluated against historical labels. Multiple origins and horizons share one selection-stage model; this is not rolling retraining with independent folds.
2. **Frozen final models:** refit boosters exist, including eligible 2023 history. Their existence does not create a production inference service or permit unbiased rescoring of 2023.
3. **Low-level prediction code:** `src/anac/models/train.py` contains prediction helpers, which require the exact engineered features, scaling and categorical vocabulary. They do not accept an arbitrary airport/month form safely.
4. **No operational future prediction endpoint:** `/v2/models` and `/v2/modules` expose result cards/metadata; ML Studio loads a static payload. The API has no forecast generation route.

## Interpreting a horizon

For origin month O, cutoff is O−2 under the assumed publication lag. Target is O+h. A nominal one-month horizon therefore uses source references at least three months before the target. Purged boundaries prevent using labels unavailable at the origin.

Monthly plots follow the horizon selector. KPIs, residuals, volume/entity summaries pool horizons; target values can repeat across forecast tasks and are not extra demand. Scatter/examples show horizon 1; selected example scores may use pooled errors.

## Real examples

The A experiment has 36,500 comparable validation rows and WAPE 10.10%, versus baseline 10.30%, without a conclusive gain. D-passengers has horizon-1 WAPE 18.7414% versus 24.0745%, while horizon 6 is 26.7149% versus 25.0888% with a difference CI including zero. These are retrospective errors, not new predictions requested by a user.

## Requirements for honest future inference

A future implementation would need versioned source snapshots, as-of feature availability, categorical/scaling parity, an explicit origin/target contract, eligibility and missing-month rules, prediction persistence/provenance and genuinely out-of-sample evaluation. None of those are implied by a static chart. New real training must be separately authorized and versioned; do not overwrite v1.

The D loader is fixed but D has not been retrained; corrected-model performance is unknown. The 2024–2025 holdout is partially exposed but unscored; C is not trained. Use [experiment results](EXPERIMENT_RESULTS.md) for exact limits, not future predictive intervals or commercial claims.
""",
    )
    write(
        "ML_ARCHITECTURE.md",
        """# Data, ML and application architecture

```mermaid
flowchart TD
    RAW[Read-only ANAC CSV] --> ING[Chunking, validation, atomic monthly Parquet]
    ING --> DATA[Processed flights]
    DATA --> FE[Point-in-time panels and features]
    FE --> SEL[Purged fitting and early stopping]
    SEL --> PRED[Saved 2023 selection predictions]
    PRED --> EVAL[Baselines, metrics and month-cluster intervals]
    EVAL --> PAYLOAD[Static showcase JSON and report]
    SEL --> FINAL[Post-selection final refit, frozen v1]
    FINAL -. not valid for rescoring 2023 .-> WARNING[No operational prediction service]
    DATA --> ANALYTICS[Three dimensions and four facts]
    ANALYTICS --> API[Read-only FastAPI data routes]
    DATA --> SERVING[Versioned serving payloads]
    SERVING --> API
    SERVING --> TOOLS[Five fixed Analyst tools]
    TOOLS <--> GROQ[Groq tool-calling client]
    GROQ --> VERIFY[Heuristic numeric verifier]
    VERIFY --> CHAT[POST /v2/analyst/chat with rate limits]
    API --> UI[Next.js dashboard]
    CHAT --> UI
    PAYLOAD --> UI
```

## Modules and boundaries

- `src/anac/ingestion` and `validation`: bounded parsing, flags, rejects, line accounting, independent DuckDB verification and resumable publication. The 20 GB source is not loaded whole into memory.
- `src/anac/features`: scope rules, panels, temporal stamps, categorical/numeric contracts and purged splits. The two-month publication lag is a documented assumption, not a complete historical availability reconstruction.
- `src/anac/models` and `evaluation`: fitting/early stopping, frozen manifests, saved selection predictions, baselines and metrics. Guards reject sealed target dates/months, including mislabeled features. Missing target months are excluded before known-inactivity zero fill.
- `src/anac/analytics`: analytical tables and read-only DuckDB queries. Tables have distinct grains; ratios are recomputed from sums.
- `src/anac/serving`: result cards and fixed tool payloads. API `/v2/models`, `/v2/modules`, `/v2/datasets` describe data/results, not inference.
- `src/anac/api` and `agent`: validated contracts, environment-configured CORS, fixed tools, Groq-compatible client and heuristic numeric verification. Chat quotas are per-process in-memory state.
- `web/components/dashboard/ml-showcase.tsx` and `ml-charts.tsx`: render `/ml/showcase.json`; no model inference occurs in the browser. The report is `/ml/report.pdf`.

## Reproducibility

The repository versions source, contracts, configuration, reports and aggregate presentation data. `data/`, models, Parquet, `.env`, dependencies and builds are ignored. Numerical reproduction requires separate input artifacts; a code-only clone cannot reconstruct omitted data or boosters by itself. The audit hashes 29 inputs and reconciles saved 2023 predictions without refitting. Its output is confined to `research/ml-showcase/results`.

Historical reproduction records predate the D fix. Full `analysis.py` regeneration includes previously exposed historical analytical series; do not describe it as a newly blind holdout evaluation. Final v1 boosters cannot score 2023 as unseen data. The 2024–2025 holdout was partially exposed but unscored. C is not trained.

See [deployment configuration](../../DEPLOYMENT.md), [analytics contracts](../../analytics.md) and [model catalog](MODEL_CATALOG.md). Portfolio generation uses tracked evidence and screenshots only, without rebuilding analytics or training models.
""",
    )
    write(
        "INTERVIEW_GUIDE.md",
        """# Technical interview guide

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
""",
    )
    # Shared descriptions cover each view individually; exact IDs preserve the original inventory.
    desc = {
        "monthly": (
            "Compare observed and predicted aggregate levels",
            "X: 2023 target month; Y: movements, passengers or seats, or B seat-weighted occupancy (%)",
            "monthly",
            "Only this web view follows the horizon selector. Aggregate cancellation can hide row errors. The best overall baseline is fixed, not necessarily best at each horizon.",
        ),
        "volume": (
            "Inspect error heterogeneity by known historical size",
            "X: historical-feature deciles 1–10; Y: WAPE (%) or B seat-weighted MAE (pp)",
            "by_volume_decile",
            "Decile boundaries are estimated descriptively on validation, not fixed training thresholds. Horizons are pooled; do not infer future market ranks.",
        ),
        "entity": (
            "Compare errors among the largest observed entities",
            "Categories: airports, carriers or directed routes; bar length: WAPE (%) or B MAE (pp)",
            "by_entity",
            "Retrospective observed-2023 ranking; horizons pooled. B aggregates a carrier's routes; small entities and market share are not represented.",
        ),
        "residuals": (
            "Inspect signed error distribution",
            "X: (prediction−actual)/actual for volumes (%), or signed B occupancy error (pp); Y: unweighted row count",
            "residuals",
            "Volume zero-actual rows are excluded. Tails clip at ±100% (B ±30 pp) and collect in outer bins; quantiles use unclipped errors. Not a future uncertainty band or the aggregate weighted bias.",
        ),
        "scatter": (
            "Compare individual actual and predicted observations",
            "X: actual; Y: LightGBM prediction; 45-degree equality line; log scale for volumes, linear occupancy for B",
            "scatter",
            "Fixed-seed sample up to 400 horizon-1 rows, not the headline-score dataset. Nonpositive volume pairs are omitted on log axes. A cloud is descriptive, not a calibration guarantee.",
        ),
        "gain": (
            "Show fitting split-gain importance",
            "X: share of total fitting gain (%); Y: top-ten feature names",
            "top_features_by_gain",
            "Selection-stage training importance, not held-out permutation importance, SHAP or causality. Top-ten shares need not sum to 100%; correlated features can substitute.",
        ),
        "horizon-table": (
            "Compare methods at each lead time",
            "Rows: 1/3 months for A, 1/3/6 otherwise; cells: WAPE (%) or B weighted MAE (pp), plus signed bias",
            "by_horizon",
            "Point estimates alone do not establish significance. Overall adoption cannot be generalized to each horizon; paired intervals are in the experiment report.",
        ),
        "examples": (
            "Inspect retrospective best/worst selected entities",
            "X: 2023 day/month at horizon 1; Y: observed and predicted volume",
            "examples",
            "Chosen by pooled error among top-ten airports/top-twenty routes. Displayed scores pool horizons; lines show only horizon 1. Selected extremes are not representative.",
        ),
        "error-month": (
            "Inspect monthly variation in row-level error",
            "X: target month 2023; Y: WAPE (%) or B weighted MAE (pp), panels by horizon",
            "monthly.model_error/baseline_error",
            "Errors are computed before aggregation; they are not absolute differences of aggregate level lines. Twelve points do not establish recurring seasonality.",
        ),
    }
    output = [
        "# Visualization catalog",
        "",
        "English companion to the exact original inventory: **26 web charts, 4 tables, 16 KPIs, 7 registry panels and 37 report figures**. PNG/SVG pairs count once. Every ID below maps to the original catalog. The three additional portfolio charts are separate illustrations, not additional ML Studio charts.",
        "",
        "All predictive diagnostics use saved 2023 selection results. Blue denotes LightGBM, gray the baseline and dark ink the observed series in web charts; inspect static legends for their own colors. Lower error is better. The D training caveat, partially exposed/unscored holdout and lack of operational forecasts apply throughout. Static historical figures retain old labels where errata are explicitly documented.",
    ]
    entries = []
    for entry in catalog["items"]:
        eid = entry["id"]
        loc = entry["location"]
        # Locations from the original inventory contain no translated analytical claims.
        loc = loc.replace("(+ `.svg`)", "(and `.svg`)")
        if eid.startswith("registry"):
            purpose, axes, source, limits = (
                "Display a method's historical selection status, or C's not-trained status",
                "No axes; method, metric, period and selection badge",
                "/v2/models, /v2/modules",
                "Status cards are not live forecasts. C has no score; selected D does not mean corrected training was evaluated.",
            )
        elif "kpi-" in eid:
            kind = eid.rsplit("-", 1)[1]
            purpose = {
                "model": "Report pooled LightGBM error",
                "baseline": "Report pooled best-baseline error",
                "difference": "Report paired model-minus-baseline error and decision",
                "bias": "Report signed systematic error",
            }[kind]
            axes, source, limits = (
                "No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp)",
                "lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias",
                "Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.",
            )
        elif eid == "paper-overview_model_vs_baseline":
            purpose, axes, source, limits = (
                "Compare each target against its own reference",
                "Separate task panels, error units and paired decision annotations",
                "reports/models and fig_overview",
                "B occupancy MAE and volume WAPE are different estimands; do not rank tasks by magnitude. Historical aggregate decisions remain subject to D's defect.",
            )
        elif eid == "paper-eda_monthly_market":
            purpose, axes, source, limits = (
                "Describe historical operated market levels and study windows",
                "X: months 2000–2025; Y: monthly paid passengers and seats; study-period shading and gaps",
                "Existing eda() figure, analytical route-month totals",
                "Historical observation, not prediction. Includes previously exposed test-period totals; not evidence of a blind test. This portfolio step does not regenerate that figure.",
            )
        elif eid == "paper-eda_concentration":
            purpose, axes, source, limits = (
                "Describe concentration in the 2022 universe",
                "X: top N, logarithmic; Y: cumulative 2022 share for airports by movements and routes by passengers",
                "Existing eda() figure and analytical 2022 totals",
                "The curves describe different populations. A selects top 50 at each cutoff, not one fixed 2022 list. This does not prove universal coverage.",
            )
        else:
            suffix = eid.split("-")[-1] if eid.startswith("web") else eid
            mapping = [
                ("actual_vs_predicted_monthly", "monthly"),
                ("error_by_month", "error-month"),
                ("by_horizon", "horizon-table"),
                ("by_volume", "volume"),
                ("by_entity", "entity"),
                ("feature_gain", "gain"),
                ("examples", "examples"),
                ("scatter", "scatter"),
                ("residuals", "residuals"),
            ]
            if eid.startswith("paper"):
                suffix = next(v for k, v in mapping if k in eid)
            elif "horizon-table" in eid:
                suffix = "horizon-table"
            purpose, axes, source, limits = desc[suffix]
        row = {
            "id": eid,
            "name": entry["name"],
            "location": loc,
            "task": entry["task"] if entry["task"] != "Contexto dos dados" else "Data context",
            "purpose": purpose,
            "axes": axes,
            "data": source,
            "interpretation": "Observed retrospective evidence; compare methods only within the same target, scope and unit.",
            "conclusion": "Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.",
            "limits": limits,
        }
        entries.append(row)
        output += [
            "",
            f"## {eid}: {row['name']}",
            "",
            f"- **Location / task:** {loc}; {row['task']}.",
            f"- **Purpose:** {purpose}.",
            f"- **Axes, units and legend:** {axes}. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.",
            f"- **Source:** {source}; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.",
            f"- **Statistical reading:** {row['interpretation']}",
            f"- **Supported conclusion:** {row['conclusion']}",
            f"- **Limits:** {limits}",
        ]
    write("VISUALIZATION_CATALOG.md", "\n".join(output))
    (OUT / "visualization-inventory.json").write_text(
        json.dumps(
            {**{k: v for k, v in catalog.items() if k != "items"}, "items": entries}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        "Six English ML guides generated; exact IDs preserved for", len(entries), "visual entries"
    )


if __name__ == "__main__":
    main()
