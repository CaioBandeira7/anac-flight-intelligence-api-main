# Model catalog

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

### Module A

| Feature | Definition |
|---|---|
| `horizon` | Months from origin to target |
| `distance` | Months from cutoff to target |
| `distance_days` | Days from cutoff to target |
| `cal_day_of_week` | 0 is Monday |
| `cal_day_of_month` | Day of the month |
| `cal_month` | Calendar month |
| `cal_week_of_year` | ISO week |
| `cal_is_weekend` | Saturday or Sunday |
| `cal_is_holiday` | National holiday |
| `cal_is_carnival` | Carnival Monday or Tuesday |
| `cal_is_day_before_special` | Day before a holiday or Carnival |
| `cal_is_day_after_special` | Day after a holiday or Carnival |
| `cal_is_school_vacation` | January, July or December |
| `id_rank_24m` | Rank by movements, 24 months to cutoff |
| `hist_lag_364` | Movements 364 days before target (null if unknown) |
| `hist_lag_728` | Movements 728 days before target (null if unknown) |
| `hist_same_dow_mean_8w` | Mean on the target's weekday, 8 weeks to cutoff |
| `hist_level_28` | Mean daily movements, 28 days to cutoff |
| `hist_level_56` | Mean daily movements, 56 days to cutoff |
| `hist_yoy_56` | Last 56 days over the same days a year earlier |
| `airport` | Airport ICAO |

### Module B

| Feature | Definition |
|---|---|
| `horizon` | Months from origin to target |
| `distance` | Months from cutoff to target |
| `cal_month` | Calendar month |
| `cal_days_in_month` | Days in the month |
| `cal_weekend_days` | Saturdays and Sundays |
| `cal_holidays` | National holidays |
| `cal_has_carnival` | Month contains Carnival |
| `cal_is_school_vacation` | January, July or December |
| `id_km` | Median route distance up to cutoff |
| `id_is_international` | Crosses the border |
| `hist_route_lf_3` | Load factor of the route across carriers, 3 months to cutoff |
| `hist_carrier_lf_3` | Load factor of the carrier across routes, 3 months to cutoff |
| `hist_carrier_seat_share_3` | Carrier share of the route's seats, 3 months to cutoff |
| `hist_seats_mean_3` | Mean monthly seats, 3 known months to cutoff |
| `hist_seats_mean_6` | Mean monthly seats, 6 known months to cutoff |
| `hist_seats_mean_12` | Mean monthly seats, 12 known months to cutoff |
| `hist_pax_mean_3` | Mean monthly paid passengers, 3 known months to cutoff |
| `hist_pax_mean_6` | Mean monthly paid passengers, 6 known months to cutoff |
| `hist_pax_mean_12` | Mean monthly paid passengers, 12 known months to cutoff |
| `hist_flights_mean_3` | Mean monthly flights, 3 known months to cutoff |
| `hist_seats_per_flight_3` | Seats per flight, 3 months to cutoff |
| `hist_lf_3` | Seat-weighted paid load factor, 3 months to cutoff |
| `hist_lf_6` | Seat-weighted paid load factor, 6 months to cutoff |
| `hist_lf_12` | Seat-weighted paid load factor, 12 months to cutoff |
| `hist_lf_std_12` | Standard deviation of monthly load factor, 12 months to cutoff |
| `hist_yoy_pax` | Paid passengers, last 3 months over the same months a year earlier |
| `hist_yoy_seats` | Seats, last 3 months over the same months a year earlier |
| `hist_pax_lag_12` | Paid passengers in month T-12 (0 if not flown, null if unknown) |
| `hist_seats_lag_12` | Seats in target month minus 12 (0 if not operated, null if unknown) |
| `hist_lf_lag_12` | Load factor in target month minus 12 (null if not operated or unknown) |
| `hist_pax_lag_24` | Paid passengers in month T-24 (0 if not flown, null if unknown) |
| `hist_seats_lag_24` | Seats in target month minus 24 (0 if not operated, null if unknown) |
| `hist_lf_lag_24` | Load factor in target month minus 24 (null if not operated or unknown) |
| `hist_origin_lf_3` | Load factor of the origin airport, 3 months to cutoff |
| `hist_destination_lf_3` | Load factor of the destination airport, 3 months to cutoff |
| `hist_carriers_on_route_3` | Carriers on the route, 3 months to cutoff |
| `hist_months_observed_12` | Months with flights among the 12 to cutoff |
| `hist_unknown_months_12` | Months with no data at all among the 12 to cutoff |
| `hist_months_since_first` | Months between first flight and cutoff |
| `origin` | Origin ICAO |
| `destination` | Destination ICAO |
| `carrier` | Carrier ICAO |

### Module D

| Feature | Definition |
|---|---|
| `horizon` | Months from origin to target |
| `distance` | Months from cutoff to target |
| `cal_month` | Calendar month |
| `cal_days_in_month` | Days in the month |
| `cal_weekend_days` | Saturdays and Sundays |
| `cal_holidays` | National holidays |
| `cal_has_carnival` | Month contains Carnival |
| `cal_is_school_vacation` | January, July or December |
| `id_km` | Median route distance up to cutoff |
| `id_is_international` | Crosses the border |
| `hist_seats_mean_3` | Mean monthly seats, 3 known months to cutoff |
| `hist_seats_mean_6` | Mean monthly seats, 6 known months to cutoff |
| `hist_seats_mean_12` | Mean monthly seats, 12 known months to cutoff |
| `hist_pax_mean_3` | Mean monthly paid passengers, 3 known months to cutoff |
| `hist_pax_mean_6` | Mean monthly paid passengers, 6 known months to cutoff |
| `hist_pax_mean_12` | Mean monthly paid passengers, 12 known months to cutoff |
| `hist_flights_mean_3` | Mean monthly flights, 3 known months to cutoff |
| `hist_seats_per_flight_3` | Seats per flight, 3 months to cutoff |
| `hist_lf_3` | Seat-weighted paid load factor, 3 months to cutoff |
| `hist_lf_6` | Seat-weighted paid load factor, 6 months to cutoff |
| `hist_lf_12` | Seat-weighted paid load factor, 12 months to cutoff |
| `hist_lf_std_12` | Standard deviation of monthly load factor, 12 months to cutoff |
| `hist_yoy_pax` | Paid passengers, last 3 months over the same months a year earlier |
| `hist_yoy_seats` | Seats, last 3 months over the same months a year earlier |
| `hist_pax_lag_12` | Paid passengers in month T-12 (0 if not flown, null if unknown) |
| `hist_seats_lag_12` | Seats in target month minus 12 (0 if not operated, null if unknown) |
| `hist_lf_lag_12` | Load factor in target month minus 12 (null if not operated or unknown) |
| `hist_pax_lag_24` | Paid passengers in month T-24 (0 if not flown, null if unknown) |
| `hist_seats_lag_24` | Seats in target month minus 24 (0 if not operated, null if unknown) |
| `hist_lf_lag_24` | Load factor in target month minus 24 (null if not operated or unknown) |
| `hist_origin_lf_3` | Load factor of the origin airport, 3 months to cutoff |
| `hist_destination_lf_3` | Load factor of the destination airport, 3 months to cutoff |
| `hist_carriers_on_route_3` | Carriers on the route, 3 months to cutoff |
| `hist_months_observed_12` | Months with flights among the 12 to cutoff |
| `hist_unknown_months_12` | Months with no data at all among the 12 to cutoff |
| `hist_months_since_first` | Months between first flight and cutoff |
| `origin` | Origin ICAO |
| `destination` | Destination ICAO |

## Artifacts and reproduction

`models/v1` contains frozen boosters/manifests; feature panels, targets and saved selection predictions live under `data/features/v1/module_*`. They are ignored by Git and required separately. `reports/models/module_{a,b,d}.json` and the tracked audit preserve metrics. `scripts/audit_ml.py --artifact-root PATH` reconciles pre-test artifacts without refit. The historical `reproduce.py --refit` record predates the D correction and must not be treated as corrected-model performance. See [results](EXPERIMENT_RESULTS.md) and [prediction guide](PREDICTION_GUIDE.md).

Source: [tracked audit evidence](../../../research/ml-showcase/results/audit.json). The [original detailed Portuguese audit](../MODEL_CATALOG.md) is preserved as secondary material.
