# Experiment results

Scope: saved selection-stage predictions against 2023 labels, not 2024–2025 test results or current forecasts. Sources are `reports/models/module_{a,b,d}.json`, the tracked audit and public ML payload.

WAPE = sum(abs(predicted-actual)) / sum(abs(actual)). Weighted occupancy MAE = sum(seats × absolute occupancy error) / sum(seats). Difference = model minus best baseline on the same rows. Negative favors the model. Intervals are paired difference intervals, not subtraction of individual interval endpoints.

| Target | Rows | LightGBM (% or pp) | Baseline | Difference (metric points) | Difference 95% CI | Historical selection |
|---|---:|---:|---:|---:|---|---|
| a | 36,500 | 10.095354 | 10.302566 | -0.207212 | [-0.844025, +0.346761] | baseline |
| b | 42,369 | 6.058023 | 6.541995 | -0.483973 | [-0.938230, -0.043803] | LightGBM |
| d_pax | 33,762 | 22.241909 | 25.308501 | -3.066592 | [-4.972356, -1.094918] | LightGBM |
| d_seats | 33,762 | 22.397056 | 25.729931 | -3.332875 | [-5.317340, -1.185566] | LightGBM |

## Horizon-specific point estimates

| Target | Horizon | LightGBM | Best baseline at this horizon |
|---|---:|---:|---:|
| a | 1 | 9.8742 | 10.0919 |
| a | 3 | 10.3165 | 10.5132 |
| b | 1 | 5.9891 | 6.3298 |
| b | 3 | 6.0918 | 6.5553 |
| b | 6 | 6.0944 | 6.7459 |
| d_pax | 1 | 18.7414 | 24.0745 |
| d_pax | 3 | 21.3114 | 25.3481 |
| d_pax | 6 | 26.7149 | 25.0888 |
| d_seats | 1 | 18.7105 | 25.7176 |
| d_seats | 3 | 21.4866 | 25.7636 |
| d_seats | 6 | 27.0399 | 25.5269 |

A is inconclusive overall and at both horizons. B's pooled improvement does not establish a gain at horizons 1/3, whose paired intervals include zero; horizon 6 favors the model. D improves at horizons 1/3; at 6, point estimates are worse and paired intervals include zero. That is not proof of inferiority at horizon 6.

## Bias and secondary diagnostics

Relative aggregate volume bias: A approximately −2.01%, D-passengers −12.21%, D-seats −11.78%. Do not attribute D's bias causally to only the missing-target defect.

B's signed seat-weighted error is **−0.0521517 pp**, with 95% CI approximately **[−1.05063, +0.923085] pp**. Its legacy unweighted relative bias is a different estimand and remains preserved. B's international descriptive MAE is 7.1229 pp versus baseline 6.4980; domestic is 5.8343 versus 6.5512. No segment-specific paired CI establishes universal adoption.

Secondary high-pressure AP is 0.6008393127 for LightGBM versus the tie-corrected baseline 0.5890506146. The historical field named `pr_auc` denotes average precision, not trapezoidal PR AUC. Reported Brier is 0.1977126325 versus 0.18634969 (lower is better): it is not independently reproduced because calibration artifacts are incomplete. Better AP does not imply better calibration.

## Uncertainty and adoption limits

The bootstrap samples 12 target-month clusters independently with replacement, 2,000 draws, seed 42. It preserves within-month dependence, not inter-month autocorrelation as a moving-block bootstrap would. The best baseline was selected and compared on the same year; no multiplicity correction or nested selection bootstrap is reported.

These are historical adoption decisions on one validation year. Revised data lack complete as-of vintages. The 2024–2025 holdout was partially exposed but not scored. D's historical defect affects 11,689/11,692 fitting rows; the loader correction has not been evaluated through new training. C is not trained. No metric is an operational future-forecast guarantee.

601 checks passed during reconciliation, with original input hashes preserved. Full paired horizon intervals remain in [audit.json](../../../research/ml-showcase/results/audit.json) and the [original detailed results](../EXPERIMENT_RESULTS.md).
