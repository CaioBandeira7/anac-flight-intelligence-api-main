# Prediction guide

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
