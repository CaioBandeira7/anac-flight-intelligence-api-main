# Features and baselines

Point-in-time features for modules A, B and D, with baselines every future model must beat. No model has been trained. Contracts live in `src/anac/features/contracts.py` and settings in `configs/features.toml`.

```powershell
.venv\Scripts\anac-features build       # panels, features and targets
.venv\Scripts\anac-features baselines   # scored on validation only
```

Outputs go to `data/features/v1/module_{a,b,d}/`, each with a `manifest.json` recording the dataset version and digest, config fingerprint and git commit. Baseline reports go to `reports/baselines/`.

## Definitions

At the start of origin month `O`, the last known month is `C = O - 2`. The target is `T = O + h`.

| | A | B | D |
|---|---|---|---|
| Unit | Airport x day | Route x carrier x month | Route x month |
| Target | Takeoffs + landings | Paid passengers / seats | Paid passengers and seats; pressure is their ratio |
| `h` (months) | 1, 3 | 1, 3, 6 | 1, 3, 6 |
| Scope | Top 50 airports by movements in the 24 months to `C` | Passenger legs, at least 500 seats a month on average, active in the 3 months to `C` | Same as B, summed across carriers |
| Primary metric | WAPE, MASE | Seat-weighted MAE | WAPE, RMSSE |

Flights with a paid load factor above 1.5 are treated as recording errors for B and D. Load factors between 1 and 1.5 are kept.

## How leakage is prevented

- **By construction.** Feature functions receive history already cut at the cutoff, and raise `LeakageError` if a later row arrives. Targets are built in separate functions and stored in separate files.
- **Eligibility** uses only data up to the cutoff, so a unit that later stops flying stays in, and one that starts later stays out.
- **Contracts.** `validate_features` rejects undeclared columns, wrong types, repeated keys and rows stamped after their cutoff.
- **Unknown months** are never zero. A lag falling on one is null, means divide by known months only, and days adjacent to an unknown month are also unknown.
- **Purge.** Training targets must be known at the first validation origin: for `h` = 1, 3, 6, the last training target is 2022-10, 2022-08, 2022-05.
- **Sealed test.** Targets from 2024 on are not written. Unsealing requires a recorded reason, and baselines refuse the test split.

`tests/test_features_leakage.py` and `tests/test_real_features.py` prove this by scrambling or deleting everything after the cutoff, on synthetic and real panels, and requiring identical features.

## Baselines on validation (2023)

Dataset `flights`, which still lacks four months. A future model must beat the best row of its module.

| Module | Baseline | Result | 95% interval |
|---|---|---|---|
| A | Recent same weekday | WAPE 10.3%, MASE 0.52 | 9.2–11.4% |
| A | Same weekday a year ago, with trend | WAPE 15.7%, MASE 0.79 | 14.6–16.8% |
| A | Same weekday a year ago | WAPE 16.0%, MASE 0.81 | 14.5–17.7% |
| B | Mean of the 12 months to cutoff | Seat-weighted MAE 6.54 pts | 6.17–6.95 |
| B | Same month last year | Seat-weighted MAE 6.90 pts | 6.51–7.26 |
| D (passengers) | Same month last year | WAPE 25.3% | 24.1–26.6% |
| D (seats) | Same month last year | WAPE 25.7% | 24.4–27.2% |
| D (high pressure) | Calibrated trend forecast | PR-AUC 0.59, base rate 0.33, Brier 0.19 | |

Intervals come from a block bootstrap over 12 target months. In B, 89.8% of eligible units flew in the target month, and errors are conditional on that.

2023 follows the pandemic recovery, so trend adjustments from 2022 run high. The sign of the bias differs by baseline, which is why several are kept.

## Serving

`anac.serving.export.export_all` writes one JSON per endpoint to `data/serving/v1/`, matching `web/lib/data/contracts.ts`, with `{data, meta}` envelopes. `PayloadStore` resolves an endpoint to its payload, which is all a read-only API needs. `analyst_catalog.json` lists what the AI Aviation Analyst may read, what must accompany its answers and what it must not claim.

Module cards show baselines only, labelled with the split they were computed on.
