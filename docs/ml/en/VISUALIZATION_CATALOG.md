# Visualization catalog

English companion to the exact original inventory: **26 web charts, 4 tables, 16 KPIs, 7 registry panels and 37 report figures**. PNG/SVG pairs count once. Every ID below maps to the original catalog. The three additional portfolio charts are separate illustrations, not additional ML Studio charts.

All predictive diagnostics use saved 2023 selection results. Blue denotes LightGBM, gray the baseline and dark ink the observed series in web charts; inspect static legends for their own colors. Lower error is better. The D training caveat, partially exposed/unscored holdout and lack of operational forecasts apply throughout. Static historical figures retain old labels where errata are explicitly documented.

## web-a-monthly: Actual vs predicted, by target month

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart; A.
- **Purpose:** Compare observed and predicted aggregate levels.
- **Axes, units and legend:** X: 2023 target month; Y: movements, passengers or seats, or B seat-weighted occupancy (%). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Only this web view follows the horizon selector. Aggregate cancellation can hide row errors. The best overall baseline is fixed, not necessarily best at each horizon.

## web-a-volume: Error by traffic volume

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart; A.
- **Purpose:** Inspect error heterogeneity by known historical size.
- **Axes, units and legend:** X: historical-feature deciles 1–10; Y: WAPE (%) or B seat-weighted MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_volume_decile; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Decile boundaries are estimated descriptively on validation, not fixed training thresholds. Horizons are pooled; do not infer future market ranks.

## web-a-entity: Largest units, by airport (ICAO)

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / PairBars; A.
- **Purpose:** Compare errors among the largest observed entities.
- **Axes, units and legend:** Categories: airports, carriers or directed routes; bar length: WAPE (%) or B MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_entity; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Retrospective observed-2023 ranking; horizons pooled. B aggregates a carrier's routes; small entities and market share are not represented.

## web-a-residuals: Residuals

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / Histogram; A.
- **Purpose:** Inspect signed error distribution.
- **Axes, units and legend:** X: (prediction−actual)/actual for volumes (%), or signed B occupancy error (pp); Y: unweighted row count. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** residuals; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Volume zero-actual rows are excluded. Tails clip at ±100% (B ±30 pp) and collect in outer bins; quantiles use unclipped errors. Not a future uncertainty band or the aggregate weighted bias.

## web-a-scatter: Actual vs predicted, row level

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / Scatter; A.
- **Purpose:** Compare individual actual and predicted observations.
- **Axes, units and legend:** X: actual; Y: LightGBM prediction; 45-degree equality line; log scale for volumes, linear occupancy for B. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** scatter; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Fixed-seed sample up to 400 horizon-1 rows, not the headline-score dataset. Nonpositive volume pairs are omitted on log axes. A cloud is descriptive, not a calibration guarantee.

## web-a-gain: What the trees split on

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / BarList; A.
- **Purpose:** Show fitting split-gain importance.
- **Axes, units and legend:** X: share of total fitting gain (%); Y: top-ten feature names. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** top_features_by_gain; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Selection-stage training importance, not held-out permutation importance, SHAP or causality. Top-ten shares need not sum to 100%; correlated features can substitute.

## web-a-horizon-table: Error by horizon

- **Location / task:** `ml-showcase.tsx` / DataTable; A.
- **Purpose:** Compare methods at each lead time.
- **Axes, units and legend:** Rows: 1/3 months for A, 1/3/6 otherwise; cells: WAPE (%) or B weighted MAE (pp), plus signed bias. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_horizon; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Point estimates alone do not establish significance. Overall adoption cannot be generalized to each horizon; paired intervals are in the experiment report.

## web-a-kpi-model: model KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; A.
- **Purpose:** Report pooled LightGBM error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-a-kpi-baseline: baseline KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; A.
- **Purpose:** Report pooled best-baseline error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-a-kpi-difference: difference KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; A.
- **Purpose:** Report paired model-minus-baseline error and decision.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-a-kpi-bias: bias KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; A.
- **Purpose:** Report signed systematic error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-a-examples: Retrospective hits and misses

- **Location / task:** `ml-showcase.tsx` / ExampleChart → LinesChart; A.
- **Purpose:** Inspect retrospective best/worst selected entities.
- **Axes, units and legend:** X: 2023 day/month at horizon 1; Y: observed and predicted volume. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** examples; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Chosen by pooled error among top-ten airports/top-twenty routes. Displayed scores pool horizons; lines show only horizon 1. Selected extremes are not representative.

## paper-a_actual_vs_predicted_monthly: a_actual_vs_predicted_monthly

- **Location / task:** `research/ml-showcase/figures/a_actual_vs_predicted_monthly.png` (and `.svg`); A.
- **Purpose:** Compare observed and predicted aggregate levels.
- **Axes, units and legend:** X: 2023 target month; Y: movements, passengers or seats, or B seat-weighted occupancy (%). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Only this web view follows the horizon selector. Aggregate cancellation can hide row errors. The best overall baseline is fixed, not necessarily best at each horizon.

## paper-a_scatter: a_scatter

- **Location / task:** `research/ml-showcase/figures/a_scatter.png` (and `.svg`); A.
- **Purpose:** Compare individual actual and predicted observations.
- **Axes, units and legend:** X: actual; Y: LightGBM prediction; 45-degree equality line; log scale for volumes, linear occupancy for B. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** scatter; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Fixed-seed sample up to 400 horizon-1 rows, not the headline-score dataset. Nonpositive volume pairs are omitted on log axes. A cloud is descriptive, not a calibration guarantee.

## paper-a_residuals: a_residuals

- **Location / task:** `research/ml-showcase/figures/a_residuals.png` (and `.svg`); A.
- **Purpose:** Inspect signed error distribution.
- **Axes, units and legend:** X: (prediction−actual)/actual for volumes (%), or signed B occupancy error (pp); Y: unweighted row count. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** residuals; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Volume zero-actual rows are excluded. Tails clip at ±100% (B ±30 pp) and collect in outer bins; quantiles use unclipped errors. Not a future uncertainty band or the aggregate weighted bias.

## paper-a_by_horizon: a_by_horizon

- **Location / task:** `research/ml-showcase/figures/a_by_horizon.png` (and `.svg`); A.
- **Purpose:** Compare methods at each lead time.
- **Axes, units and legend:** Rows: 1/3 months for A, 1/3/6 otherwise; cells: WAPE (%) or B weighted MAE (pp), plus signed bias. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_horizon; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Point estimates alone do not establish significance. Overall adoption cannot be generalized to each horizon; paired intervals are in the experiment report.

## paper-a_by_volume: a_by_volume

- **Location / task:** `research/ml-showcase/figures/a_by_volume.png` (and `.svg`); A.
- **Purpose:** Inspect error heterogeneity by known historical size.
- **Axes, units and legend:** X: historical-feature deciles 1–10; Y: WAPE (%) or B seat-weighted MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_volume_decile; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Decile boundaries are estimated descriptively on validation, not fixed training thresholds. Horizons are pooled; do not infer future market ranks.

## paper-a_by_entity: a_by_entity

- **Location / task:** `research/ml-showcase/figures/a_by_entity.png` (and `.svg`); A.
- **Purpose:** Compare errors among the largest observed entities.
- **Axes, units and legend:** Categories: airports, carriers or directed routes; bar length: WAPE (%) or B MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_entity; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Retrospective observed-2023 ranking; horizons pooled. B aggregates a carrier's routes; small entities and market share are not represented.

## paper-a_feature_gain: a_feature_gain

- **Location / task:** `research/ml-showcase/figures/a_feature_gain.png` (and `.svg`); A.
- **Purpose:** Show fitting split-gain importance.
- **Axes, units and legend:** X: share of total fitting gain (%); Y: top-ten feature names. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** top_features_by_gain; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Selection-stage training importance, not held-out permutation importance, SHAP or causality. Top-ten shares need not sum to 100%; correlated features can substitute.

## paper-a_error_by_month: a_error_by_month

- **Location / task:** `research/ml-showcase/figures/a_error_by_month.png` (and `.svg`); A.
- **Purpose:** Inspect monthly variation in row-level error.
- **Axes, units and legend:** X: target month 2023; Y: WAPE (%) or B weighted MAE (pp), panels by horizon. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly.model_error/baseline_error; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Errors are computed before aggregation; they are not absolute differences of aggregate level lines. Twelve points do not establish recurring seasonality.

## paper-a_examples_daily: a_examples_daily

- **Location / task:** `research/ml-showcase/figures/a_examples_daily.png` (and `.svg`); A.
- **Purpose:** Inspect retrospective best/worst selected entities.
- **Axes, units and legend:** X: 2023 day/month at horizon 1; Y: observed and predicted volume. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** examples; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Chosen by pooled error among top-ten airports/top-twenty routes. Displayed scores pool horizons; lines show only horizon 1. Selected extremes are not representative.

## web-b-monthly: Actual vs predicted, by target month

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart; B.
- **Purpose:** Compare observed and predicted aggregate levels.
- **Axes, units and legend:** X: 2023 target month; Y: movements, passengers or seats, or B seat-weighted occupancy (%). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Only this web view follows the horizon selector. Aggregate cancellation can hide row errors. The best overall baseline is fixed, not necessarily best at each horizon.

## web-b-volume: Error by traffic volume

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart; B.
- **Purpose:** Inspect error heterogeneity by known historical size.
- **Axes, units and legend:** X: historical-feature deciles 1–10; Y: WAPE (%) or B seat-weighted MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_volume_decile; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Decile boundaries are estimated descriptively on validation, not fixed training thresholds. Horizons are pooled; do not infer future market ranks.

## web-b-entity: Largest units, by carrier

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / PairBars; B.
- **Purpose:** Compare errors among the largest observed entities.
- **Axes, units and legend:** Categories: airports, carriers or directed routes; bar length: WAPE (%) or B MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_entity; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Retrospective observed-2023 ranking; horizons pooled. B aggregates a carrier's routes; small entities and market share are not represented.

## web-b-residuals: Residuals

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / Histogram; B.
- **Purpose:** Inspect signed error distribution.
- **Axes, units and legend:** X: (prediction−actual)/actual for volumes (%), or signed B occupancy error (pp); Y: unweighted row count. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** residuals; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Volume zero-actual rows are excluded. Tails clip at ±100% (B ±30 pp) and collect in outer bins; quantiles use unclipped errors. Not a future uncertainty band or the aggregate weighted bias.

## web-b-scatter: Actual vs predicted, row level

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / Scatter; B.
- **Purpose:** Compare individual actual and predicted observations.
- **Axes, units and legend:** X: actual; Y: LightGBM prediction; 45-degree equality line; log scale for volumes, linear occupancy for B. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** scatter; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Fixed-seed sample up to 400 horizon-1 rows, not the headline-score dataset. Nonpositive volume pairs are omitted on log axes. A cloud is descriptive, not a calibration guarantee.

## web-b-gain: What the trees split on

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / BarList; B.
- **Purpose:** Show fitting split-gain importance.
- **Axes, units and legend:** X: share of total fitting gain (%); Y: top-ten feature names. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** top_features_by_gain; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Selection-stage training importance, not held-out permutation importance, SHAP or causality. Top-ten shares need not sum to 100%; correlated features can substitute.

## web-b-horizon-table: Error by horizon

- **Location / task:** `ml-showcase.tsx` / DataTable; B.
- **Purpose:** Compare methods at each lead time.
- **Axes, units and legend:** Rows: 1/3 months for A, 1/3/6 otherwise; cells: WAPE (%) or B weighted MAE (pp), plus signed bias. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_horizon; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Point estimates alone do not establish significance. Overall adoption cannot be generalized to each horizon; paired intervals are in the experiment report.

## web-b-kpi-model: model KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; B.
- **Purpose:** Report pooled LightGBM error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-b-kpi-baseline: baseline KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; B.
- **Purpose:** Report pooled best-baseline error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-b-kpi-difference: difference KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; B.
- **Purpose:** Report paired model-minus-baseline error and decision.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-b-kpi-bias: bias KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; B.
- **Purpose:** Report signed systematic error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## paper-b_actual_vs_predicted_monthly: b_actual_vs_predicted_monthly

- **Location / task:** `research/ml-showcase/figures/b_actual_vs_predicted_monthly.png` (and `.svg`); B.
- **Purpose:** Compare observed and predicted aggregate levels.
- **Axes, units and legend:** X: 2023 target month; Y: movements, passengers or seats, or B seat-weighted occupancy (%). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Only this web view follows the horizon selector. Aggregate cancellation can hide row errors. The best overall baseline is fixed, not necessarily best at each horizon.

## paper-b_scatter: b_scatter

- **Location / task:** `research/ml-showcase/figures/b_scatter.png` (and `.svg`); B.
- **Purpose:** Compare individual actual and predicted observations.
- **Axes, units and legend:** X: actual; Y: LightGBM prediction; 45-degree equality line; log scale for volumes, linear occupancy for B. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** scatter; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Fixed-seed sample up to 400 horizon-1 rows, not the headline-score dataset. Nonpositive volume pairs are omitted on log axes. A cloud is descriptive, not a calibration guarantee.

## paper-b_residuals: b_residuals

- **Location / task:** `research/ml-showcase/figures/b_residuals.png` (and `.svg`); B.
- **Purpose:** Inspect signed error distribution.
- **Axes, units and legend:** X: (prediction−actual)/actual for volumes (%), or signed B occupancy error (pp); Y: unweighted row count. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** residuals; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Volume zero-actual rows are excluded. Tails clip at ±100% (B ±30 pp) and collect in outer bins; quantiles use unclipped errors. Not a future uncertainty band or the aggregate weighted bias.

## paper-b_by_horizon: b_by_horizon

- **Location / task:** `research/ml-showcase/figures/b_by_horizon.png` (and `.svg`); B.
- **Purpose:** Compare methods at each lead time.
- **Axes, units and legend:** Rows: 1/3 months for A, 1/3/6 otherwise; cells: WAPE (%) or B weighted MAE (pp), plus signed bias. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_horizon; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Point estimates alone do not establish significance. Overall adoption cannot be generalized to each horizon; paired intervals are in the experiment report.

## paper-b_by_volume: b_by_volume

- **Location / task:** `research/ml-showcase/figures/b_by_volume.png` (and `.svg`); B.
- **Purpose:** Inspect error heterogeneity by known historical size.
- **Axes, units and legend:** X: historical-feature deciles 1–10; Y: WAPE (%) or B seat-weighted MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_volume_decile; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Decile boundaries are estimated descriptively on validation, not fixed training thresholds. Horizons are pooled; do not infer future market ranks.

## paper-b_by_entity: b_by_entity

- **Location / task:** `research/ml-showcase/figures/b_by_entity.png` (and `.svg`); B.
- **Purpose:** Compare errors among the largest observed entities.
- **Axes, units and legend:** Categories: airports, carriers or directed routes; bar length: WAPE (%) or B MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_entity; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Retrospective observed-2023 ranking; horizons pooled. B aggregates a carrier's routes; small entities and market share are not represented.

## paper-b_feature_gain: b_feature_gain

- **Location / task:** `research/ml-showcase/figures/b_feature_gain.png` (and `.svg`); B.
- **Purpose:** Show fitting split-gain importance.
- **Axes, units and legend:** X: share of total fitting gain (%); Y: top-ten feature names. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** top_features_by_gain; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Selection-stage training importance, not held-out permutation importance, SHAP or causality. Top-ten shares need not sum to 100%; correlated features can substitute.

## paper-b_error_by_month: b_error_by_month

- **Location / task:** `research/ml-showcase/figures/b_error_by_month.png` (and `.svg`); B.
- **Purpose:** Inspect monthly variation in row-level error.
- **Axes, units and legend:** X: target month 2023; Y: WAPE (%) or B weighted MAE (pp), panels by horizon. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly.model_error/baseline_error; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Errors are computed before aggregation; they are not absolute differences of aggregate level lines. Twelve points do not establish recurring seasonality.

## web-d_pax-monthly: Actual vs predicted, by target month

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart; D-pax.
- **Purpose:** Compare observed and predicted aggregate levels.
- **Axes, units and legend:** X: 2023 target month; Y: movements, passengers or seats, or B seat-weighted occupancy (%). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Only this web view follows the horizon selector. Aggregate cancellation can hide row errors. The best overall baseline is fixed, not necessarily best at each horizon.

## web-d_pax-volume: Error by traffic volume

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart; D-pax.
- **Purpose:** Inspect error heterogeneity by known historical size.
- **Axes, units and legend:** X: historical-feature deciles 1–10; Y: WAPE (%) or B seat-weighted MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_volume_decile; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Decile boundaries are estimated descriptively on validation, not fixed training thresholds. Horizons are pooled; do not infer future market ranks.

## web-d_pax-entity: Largest units, by directed route

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / PairBars; D-pax.
- **Purpose:** Compare errors among the largest observed entities.
- **Axes, units and legend:** Categories: airports, carriers or directed routes; bar length: WAPE (%) or B MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_entity; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Retrospective observed-2023 ranking; horizons pooled. B aggregates a carrier's routes; small entities and market share are not represented.

## web-d_pax-residuals: Residuals

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / Histogram; D-pax.
- **Purpose:** Inspect signed error distribution.
- **Axes, units and legend:** X: (prediction−actual)/actual for volumes (%), or signed B occupancy error (pp); Y: unweighted row count. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** residuals; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Volume zero-actual rows are excluded. Tails clip at ±100% (B ±30 pp) and collect in outer bins; quantiles use unclipped errors. Not a future uncertainty band or the aggregate weighted bias.

## web-d_pax-scatter: Actual vs predicted, row level

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / Scatter; D-pax.
- **Purpose:** Compare individual actual and predicted observations.
- **Axes, units and legend:** X: actual; Y: LightGBM prediction; 45-degree equality line; log scale for volumes, linear occupancy for B. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** scatter; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Fixed-seed sample up to 400 horizon-1 rows, not the headline-score dataset. Nonpositive volume pairs are omitted on log axes. A cloud is descriptive, not a calibration guarantee.

## web-d_pax-gain: What the trees split on

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / BarList; D-pax.
- **Purpose:** Show fitting split-gain importance.
- **Axes, units and legend:** X: share of total fitting gain (%); Y: top-ten feature names. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** top_features_by_gain; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Selection-stage training importance, not held-out permutation importance, SHAP or causality. Top-ten shares need not sum to 100%; correlated features can substitute.

## web-d_pax-horizon-table: Error by horizon

- **Location / task:** `ml-showcase.tsx` / DataTable; D-pax.
- **Purpose:** Compare methods at each lead time.
- **Axes, units and legend:** Rows: 1/3 months for A, 1/3/6 otherwise; cells: WAPE (%) or B weighted MAE (pp), plus signed bias. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_horizon; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Point estimates alone do not establish significance. Overall adoption cannot be generalized to each horizon; paired intervals are in the experiment report.

## web-d_pax-kpi-model: model KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; D-pax.
- **Purpose:** Report pooled LightGBM error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-d_pax-kpi-baseline: baseline KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; D-pax.
- **Purpose:** Report pooled best-baseline error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-d_pax-kpi-difference: difference KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; D-pax.
- **Purpose:** Report paired model-minus-baseline error and decision.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-d_pax-kpi-bias: bias KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; D-pax.
- **Purpose:** Report signed systematic error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-d_pax-examples: Retrospective hits and misses

- **Location / task:** `ml-showcase.tsx` / ExampleChart → LinesChart; D-pax.
- **Purpose:** Inspect retrospective best/worst selected entities.
- **Axes, units and legend:** X: 2023 day/month at horizon 1; Y: observed and predicted volume. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** examples; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Chosen by pooled error among top-ten airports/top-twenty routes. Displayed scores pool horizons; lines show only horizon 1. Selected extremes are not representative.

## paper-d_pax_actual_vs_predicted_monthly: d_pax_actual_vs_predicted_monthly

- **Location / task:** `research/ml-showcase/figures/d_pax_actual_vs_predicted_monthly.png` (and `.svg`); D-pax.
- **Purpose:** Compare observed and predicted aggregate levels.
- **Axes, units and legend:** X: 2023 target month; Y: movements, passengers or seats, or B seat-weighted occupancy (%). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Only this web view follows the horizon selector. Aggregate cancellation can hide row errors. The best overall baseline is fixed, not necessarily best at each horizon.

## paper-d_pax_scatter: d_pax_scatter

- **Location / task:** `research/ml-showcase/figures/d_pax_scatter.png` (and `.svg`); D-pax.
- **Purpose:** Compare individual actual and predicted observations.
- **Axes, units and legend:** X: actual; Y: LightGBM prediction; 45-degree equality line; log scale for volumes, linear occupancy for B. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** scatter; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Fixed-seed sample up to 400 horizon-1 rows, not the headline-score dataset. Nonpositive volume pairs are omitted on log axes. A cloud is descriptive, not a calibration guarantee.

## paper-d_pax_residuals: d_pax_residuals

- **Location / task:** `research/ml-showcase/figures/d_pax_residuals.png` (and `.svg`); D-pax.
- **Purpose:** Inspect signed error distribution.
- **Axes, units and legend:** X: (prediction−actual)/actual for volumes (%), or signed B occupancy error (pp); Y: unweighted row count. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** residuals; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Volume zero-actual rows are excluded. Tails clip at ±100% (B ±30 pp) and collect in outer bins; quantiles use unclipped errors. Not a future uncertainty band or the aggregate weighted bias.

## paper-d_pax_by_horizon: d_pax_by_horizon

- **Location / task:** `research/ml-showcase/figures/d_pax_by_horizon.png` (and `.svg`); D-pax.
- **Purpose:** Compare methods at each lead time.
- **Axes, units and legend:** Rows: 1/3 months for A, 1/3/6 otherwise; cells: WAPE (%) or B weighted MAE (pp), plus signed bias. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_horizon; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Point estimates alone do not establish significance. Overall adoption cannot be generalized to each horizon; paired intervals are in the experiment report.

## paper-d_pax_by_volume: d_pax_by_volume

- **Location / task:** `research/ml-showcase/figures/d_pax_by_volume.png` (and `.svg`); D-pax.
- **Purpose:** Inspect error heterogeneity by known historical size.
- **Axes, units and legend:** X: historical-feature deciles 1–10; Y: WAPE (%) or B seat-weighted MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_volume_decile; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Decile boundaries are estimated descriptively on validation, not fixed training thresholds. Horizons are pooled; do not infer future market ranks.

## paper-d_pax_by_entity: d_pax_by_entity

- **Location / task:** `research/ml-showcase/figures/d_pax_by_entity.png` (and `.svg`); D-pax.
- **Purpose:** Compare errors among the largest observed entities.
- **Axes, units and legend:** Categories: airports, carriers or directed routes; bar length: WAPE (%) or B MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_entity; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Retrospective observed-2023 ranking; horizons pooled. B aggregates a carrier's routes; small entities and market share are not represented.

## paper-d_pax_feature_gain: d_pax_feature_gain

- **Location / task:** `research/ml-showcase/figures/d_pax_feature_gain.png` (and `.svg`); D-pax.
- **Purpose:** Show fitting split-gain importance.
- **Axes, units and legend:** X: share of total fitting gain (%); Y: top-ten feature names. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** top_features_by_gain; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Selection-stage training importance, not held-out permutation importance, SHAP or causality. Top-ten shares need not sum to 100%; correlated features can substitute.

## paper-d_pax_error_by_month: d_pax_error_by_month

- **Location / task:** `research/ml-showcase/figures/d_pax_error_by_month.png` (and `.svg`); D-pax.
- **Purpose:** Inspect monthly variation in row-level error.
- **Axes, units and legend:** X: target month 2023; Y: WAPE (%) or B weighted MAE (pp), panels by horizon. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly.model_error/baseline_error; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Errors are computed before aggregation; they are not absolute differences of aggregate level lines. Twelve points do not establish recurring seasonality.

## paper-d_pax_examples: d_pax_examples

- **Location / task:** `research/ml-showcase/figures/d_pax_examples.png` (and `.svg`); D-pax.
- **Purpose:** Inspect retrospective best/worst selected entities.
- **Axes, units and legend:** X: 2023 day/month at horizon 1; Y: observed and predicted volume. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** examples; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Chosen by pooled error among top-ten airports/top-twenty routes. Displayed scores pool horizons; lines show only horizon 1. Selected extremes are not representative.

## web-d_seats-monthly: Actual vs predicted, by target month

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart; D-seats.
- **Purpose:** Compare observed and predicted aggregate levels.
- **Axes, units and legend:** X: 2023 target month; Y: movements, passengers or seats, or B seat-weighted occupancy (%). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Only this web view follows the horizon selector. Aggregate cancellation can hide row errors. The best overall baseline is fixed, not necessarily best at each horizon.

## web-d_seats-volume: Error by traffic volume

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart; D-seats.
- **Purpose:** Inspect error heterogeneity by known historical size.
- **Axes, units and legend:** X: historical-feature deciles 1–10; Y: WAPE (%) or B seat-weighted MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_volume_decile; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Decile boundaries are estimated descriptively on validation, not fixed training thresholds. Horizons are pooled; do not infer future market ranks.

## web-d_seats-entity: Largest units, by directed route

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / PairBars; D-seats.
- **Purpose:** Compare errors among the largest observed entities.
- **Axes, units and legend:** Categories: airports, carriers or directed routes; bar length: WAPE (%) or B MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_entity; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Retrospective observed-2023 ranking; horizons pooled. B aggregates a carrier's routes; small entities and market share are not represented.

## web-d_seats-residuals: Residuals

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / Histogram; D-seats.
- **Purpose:** Inspect signed error distribution.
- **Axes, units and legend:** X: (prediction−actual)/actual for volumes (%), or signed B occupancy error (pp); Y: unweighted row count. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** residuals; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Volume zero-actual rows are excluded. Tails clip at ±100% (B ±30 pp) and collect in outer bins; quantiles use unclipped errors. Not a future uncertainty band or the aggregate weighted bias.

## web-d_seats-scatter: Actual vs predicted, row level

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / Scatter; D-seats.
- **Purpose:** Compare individual actual and predicted observations.
- **Axes, units and legend:** X: actual; Y: LightGBM prediction; 45-degree equality line; log scale for volumes, linear occupancy for B. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** scatter; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Fixed-seed sample up to 400 horizon-1 rows, not the headline-score dataset. Nonpositive volume pairs are omitted on log axes. A cloud is descriptive, not a calibration guarantee.

## web-d_seats-gain: What the trees split on

- **Location / task:** `web/components/dashboard/ml-showcase.tsx` TaskView / BarList; D-seats.
- **Purpose:** Show fitting split-gain importance.
- **Axes, units and legend:** X: share of total fitting gain (%); Y: top-ten feature names. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** top_features_by_gain; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Selection-stage training importance, not held-out permutation importance, SHAP or causality. Top-ten shares need not sum to 100%; correlated features can substitute.

## web-d_seats-horizon-table: Error by horizon

- **Location / task:** `ml-showcase.tsx` / DataTable; D-seats.
- **Purpose:** Compare methods at each lead time.
- **Axes, units and legend:** Rows: 1/3 months for A, 1/3/6 otherwise; cells: WAPE (%) or B weighted MAE (pp), plus signed bias. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_horizon; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Point estimates alone do not establish significance. Overall adoption cannot be generalized to each horizon; paired intervals are in the experiment report.

## web-d_seats-kpi-model: model KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; D-seats.
- **Purpose:** Report pooled LightGBM error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-d_seats-kpi-baseline: baseline KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; D-seats.
- **Purpose:** Report pooled best-baseline error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-d_seats-kpi-difference: difference KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; D-seats.
- **Purpose:** Report paired model-minus-baseline error and decision.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## web-d_seats-kpi-bias: bias KPI

- **Location / task:** `ml-showcase.tsx` / StatTile; D-seats.
- **Purpose:** Report signed systematic error.
- **Axes, units and legend:** No axes; WAPE (%) or B weighted MAE (pp); difference in metric points; volume bias relative (%) or B weighted signed error (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** lightgbm/baselines/difference_vs_best_baseline/bias and seat_weighted_bias; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Repeated targets pool horizons. B's weighted bias differs from its preserved legacy ratio. Metric CI is not future prediction uncertainty; WAPE is not accuracy.

## paper-d_seats_actual_vs_predicted_monthly: d_seats_actual_vs_predicted_monthly

- **Location / task:** `research/ml-showcase/figures/d_seats_actual_vs_predicted_monthly.png` (and `.svg`); D-seats.
- **Purpose:** Compare observed and predicted aggregate levels.
- **Axes, units and legend:** X: 2023 target month; Y: movements, passengers or seats, or B seat-weighted occupancy (%). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Only this web view follows the horizon selector. Aggregate cancellation can hide row errors. The best overall baseline is fixed, not necessarily best at each horizon.

## paper-d_seats_scatter: d_seats_scatter

- **Location / task:** `research/ml-showcase/figures/d_seats_scatter.png` (and `.svg`); D-seats.
- **Purpose:** Compare individual actual and predicted observations.
- **Axes, units and legend:** X: actual; Y: LightGBM prediction; 45-degree equality line; log scale for volumes, linear occupancy for B. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** scatter; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Fixed-seed sample up to 400 horizon-1 rows, not the headline-score dataset. Nonpositive volume pairs are omitted on log axes. A cloud is descriptive, not a calibration guarantee.

## paper-d_seats_residuals: d_seats_residuals

- **Location / task:** `research/ml-showcase/figures/d_seats_residuals.png` (and `.svg`); D-seats.
- **Purpose:** Inspect signed error distribution.
- **Axes, units and legend:** X: (prediction−actual)/actual for volumes (%), or signed B occupancy error (pp); Y: unweighted row count. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** residuals; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Volume zero-actual rows are excluded. Tails clip at ±100% (B ±30 pp) and collect in outer bins; quantiles use unclipped errors. Not a future uncertainty band or the aggregate weighted bias.

## paper-d_seats_by_horizon: d_seats_by_horizon

- **Location / task:** `research/ml-showcase/figures/d_seats_by_horizon.png` (and `.svg`); D-seats.
- **Purpose:** Compare methods at each lead time.
- **Axes, units and legend:** Rows: 1/3 months for A, 1/3/6 otherwise; cells: WAPE (%) or B weighted MAE (pp), plus signed bias. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_horizon; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Point estimates alone do not establish significance. Overall adoption cannot be generalized to each horizon; paired intervals are in the experiment report.

## paper-d_seats_by_volume: d_seats_by_volume

- **Location / task:** `research/ml-showcase/figures/d_seats_by_volume.png` (and `.svg`); D-seats.
- **Purpose:** Inspect error heterogeneity by known historical size.
- **Axes, units and legend:** X: historical-feature deciles 1–10; Y: WAPE (%) or B seat-weighted MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_volume_decile; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Decile boundaries are estimated descriptively on validation, not fixed training thresholds. Horizons are pooled; do not infer future market ranks.

## paper-d_seats_by_entity: d_seats_by_entity

- **Location / task:** `research/ml-showcase/figures/d_seats_by_entity.png` (and `.svg`); D-seats.
- **Purpose:** Compare errors among the largest observed entities.
- **Axes, units and legend:** Categories: airports, carriers or directed routes; bar length: WAPE (%) or B MAE (pp). Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** by_entity; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Retrospective observed-2023 ranking; horizons pooled. B aggregates a carrier's routes; small entities and market share are not represented.

## paper-d_seats_feature_gain: d_seats_feature_gain

- **Location / task:** `research/ml-showcase/figures/d_seats_feature_gain.png` (and `.svg`); D-seats.
- **Purpose:** Show fitting split-gain importance.
- **Axes, units and legend:** X: share of total fitting gain (%); Y: top-ten feature names. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** top_features_by_gain; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Selection-stage training importance, not held-out permutation importance, SHAP or causality. Top-ten shares need not sum to 100%; correlated features can substitute.

## paper-d_seats_error_by_month: d_seats_error_by_month

- **Location / task:** `research/ml-showcase/figures/d_seats_error_by_month.png` (and `.svg`); D-seats.
- **Purpose:** Inspect monthly variation in row-level error.
- **Axes, units and legend:** X: target month 2023; Y: WAPE (%) or B weighted MAE (pp), panels by horizon. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** monthly.model_error/baseline_error; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Errors are computed before aggregation; they are not absolute differences of aggregate level lines. Twelve points do not establish recurring seasonality.

## paper-overview_model_vs_baseline: overview_model_vs_baseline

- **Location / task:** `figures/overview_model_vs_baseline.{png,svg}`; A/B/D-pax/D-seats.
- **Purpose:** Compare each target against its own reference.
- **Axes, units and legend:** Separate task panels, error units and paired decision annotations. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** reports/models and fig_overview; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** B occupancy MAE and volume WAPE are different estimands; do not rank tasks by magnitude. Historical aggregate decisions remain subject to D's defect.

## paper-eda_monthly_market: eda_monthly_market

- **Location / task:** `figures/eda_monthly_market.{png,svg}`; Data context.
- **Purpose:** Describe historical operated market levels and study windows.
- **Axes, units and legend:** X: months 2000–2025; Y: monthly paid passengers and seats; study-period shading and gaps. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** Existing eda() figure, analytical route-month totals; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Historical observation, not prediction. Includes previously exposed test-period totals; not evidence of a blind test. This portfolio step does not regenerate that figure.

## paper-eda_concentration: eda_concentration

- **Location / task:** `figures/eda_concentration.{png,svg}`; Data context.
- **Purpose:** Describe concentration in the 2022 universe.
- **Axes, units and legend:** X: top N, logarithmic; Y: cumulative 2022 share for airports by movements and routes by passengers. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** Existing eda() figure and analytical 2022 totals; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** The curves describe different populations. A selects top 50 at each cutoff, not one fixed 2022 list. This does not prove universal coverage.

## registry-a-baseline: Model registry: A / baseline

- **Location / task:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`; A.
- **Purpose:** Display a method's historical selection status, or C's not-trained status.
- **Axes, units and legend:** No axes; method, metric, period and selection badge. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** /v2/models, /v2/modules; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Status cards are not live forecasts. C has no score; selected D does not mean corrected training was evaluated.

## registry-a-lightgbm: Model registry: A / lightgbm

- **Location / task:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`; A.
- **Purpose:** Display a method's historical selection status, or C's not-trained status.
- **Axes, units and legend:** No axes; method, metric, period and selection badge. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** /v2/models, /v2/modules; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Status cards are not live forecasts. C has no score; selected D does not mean corrected training was evaluated.

## registry-b-baseline: Model registry: B / baseline

- **Location / task:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`; B.
- **Purpose:** Display a method's historical selection status, or C's not-trained status.
- **Axes, units and legend:** No axes; method, metric, period and selection badge. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** /v2/models, /v2/modules; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Status cards are not live forecasts. C has no score; selected D does not mean corrected training was evaluated.

## registry-b-lightgbm: Model registry: B / lightgbm

- **Location / task:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`; B.
- **Purpose:** Display a method's historical selection status, or C's not-trained status.
- **Axes, units and legend:** No axes; method, metric, period and selection badge. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** /v2/models, /v2/modules; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Status cards are not live forecasts. C has no score; selected D does not mean corrected training was evaluated.

## registry-d-baseline: Model registry: D / baseline

- **Location / task:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`; D.
- **Purpose:** Display a method's historical selection status, or C's not-trained status.
- **Axes, units and legend:** No axes; method, metric, period and selection badge. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** /v2/models, /v2/modules; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Status cards are not live forecasts. C has no score; selected D does not mean corrected training was evaluated.

## registry-d-lightgbm: Model registry: D / lightgbm

- **Location / task:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`; D.
- **Purpose:** Display a method's historical selection status, or C's not-trained status.
- **Axes, units and legend:** No axes; method, metric, period and selection badge. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** /v2/models, /v2/modules; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Status cards are not live forecasts. C has no score; selected D does not mean corrected training was evaluated.

## registry-c: Model registry: C not trained

- **Location / task:** `web/components/dashboard/data-views.tsx::MlStudioView`; C.
- **Purpose:** Display a method's historical selection status, or C's not-trained status.
- **Axes, units and legend:** No axes; method, metric, period and selection badge. Web colors: model blue, baseline gray, actual dark; paper legend is authoritative.
- **Source:** /v2/models, /v2/modules; web fields come from `web/public/ml/showcase.json`, generated from saved selection results; paper figures are in `research/ml-showcase/figures/`.
- **Statistical reading:** Observed retrospective evidence; compare methods only within the same target, scope and unit.
- **Supported conclusion:** Supports the stated descriptive comparison on the evaluated population, not causality or future operational performance.
- **Limits:** Status cards are not live forecasts. C has no score; selected D does not mean corrected training was evaluated.
