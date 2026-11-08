"""Baselines every future model must beat. They read features only, so they share the leakage tests.

Only the validation split is evaluated. The test period cannot be read from this code path:
test targets are not written by default, and `evaluate_module` refuses to score them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import polars as pl

from anac.evaluation import metrics as m
from anac.features.build import git_state
from anac.features.config import FeatureConfig, SealedTestError, month_label
from anac.features.contracts import CONTRACTS
from anac.features.splits import (
    TEST,
    TRAIN,
    VALIDATION,
    assert_no_sealed_targets,
    exclude_unknown_targets,
)
from anac.ingestion.storage import read_json, write_json_atomic, write_parquet_atomic

TREND_LIMITS = (0.5, 2.0)


def _clipped(column: str) -> pl.Expr:
    return pl.col(column).clip(*TREND_LIMITS).fill_null(1.0)


def baselines_a(features: pl.DataFrame) -> pl.DataFrame:
    recent = pl.coalesce("hist_same_dow_mean_8w", "hist_level_56")
    return features.with_columns(
        pl.coalesce("hist_lag_364", recent).alias("pred_seasonal_naive"),
        pl.coalesce(pl.col("hist_lag_364") * _clipped("hist_yoy_56"), recent).alias(
            "pred_seasonal_trend"
        ),
        recent.alias("pred_recent_weekday"),
    )


def baselines_b(features: pl.DataFrame) -> pl.DataFrame:
    return features.with_columns(
        pl.coalesce("hist_lf_lag_12", "hist_lf_12").alias("pred_same_month_last_year"),
        pl.col("hist_lf_12").alias("pred_mean_12"),
        pl.col("hist_lf_3").alias("pred_mean_3"),
    )


def baselines_d(features: pl.DataFrame) -> pl.DataFrame:
    def trended(lag: str, yoy: str, level: str) -> pl.Expr:
        return pl.coalesce(
            pl.when(pl.col(lag) > 0).then(pl.col(lag) * _clipped(yoy)),
            pl.col(level),
        )

    frame = features.with_columns(
        pl.coalesce("hist_pax_lag_12", "hist_pax_mean_12").alias("pred_pax_seasonal_naive"),
        pl.coalesce("hist_seats_lag_12", "hist_seats_mean_12").alias("pred_seats_seasonal_naive"),
        trended("hist_pax_lag_12", "hist_yoy_pax", "hist_pax_mean_12").alias(
            "pred_pax_seasonal_trend"
        ),
        trended("hist_seats_lag_12", "hist_yoy_seats", "hist_seats_mean_12").alias(
            "pred_seats_seasonal_trend"
        ),
    )
    return frame.with_columns(
        pl.when(pl.col("pred_seats_seasonal_trend") > 0)
        .then(pl.col("pred_pax_seasonal_trend") / pl.col("pred_seats_seasonal_trend"))
        .alias("pred_pressure_seasonal_trend")
    )


PREDICTIONS = {"a": baselines_a, "b": baselines_b, "d": baselines_d}


def _segments(frame: pl.DataFrame, column: str) -> dict[str, pl.DataFrame]:
    return {
        f"{column}={value}": frame.filter(pl.col(column) == value)
        for value in sorted(frame.get_column(column).unique().to_list())
    }


def _evaluate_a(train: pl.DataFrame, validation: pl.DataFrame) -> dict[str, Any]:
    scale = m.mean_absolute_scale(train, "movements", "hist_lag_364")
    groups = {
        "all": validation,
        **_segments(validation, "horizon"),
        "top_10_airports": validation.filter(pl.col("id_rank_24m") <= 10),
        "airports_11_to_50": validation.filter(pl.col("id_rank_24m") > 10),
    }
    results: dict[str, Any] = {"mase_scale_from_train": scale}
    for name in ("pred_seasonal_naive", "pred_seasonal_trend", "pred_recent_weekday"):
        results[name] = {
            group: {
                "rows": data.height,
                "wape": m.wape(data, "movements", name),
                "mase": m.mase(data, "movements", name, scale),
                "bias": m.bias(data, "movements", name),
            }
            for group, data in groups.items()
        }
    return results


def _evaluate_b(
    train: pl.DataFrame, validation: pl.DataFrame, all_validation: pl.DataFrame
) -> dict[str, Any]:
    groups = {
        "all": validation,
        **_segments(validation, "horizon"),
        "large_units": validation.filter(pl.col("hist_seats_mean_12") >= 10_000),
        "small_units": validation.filter(pl.col("hist_seats_mean_12") < 10_000),
    }
    results: dict[str, Any] = {
        "operating_rate_of_eligible_units": all_validation.select(pl.col("operated").mean()).item(),
        "training_rows_with_target": train.height,
    }
    for name in ("pred_same_month_last_year", "pred_mean_12", "pred_mean_3"):
        usable = {key: data.filter(pl.col(name).is_not_null()) for key, data in groups.items()}
        results[name] = {
            group: {
                "rows": data.height,
                "seat_weighted_mae": m.weighted_mae(data, "load_factor", name, "seats"),
                "seat_weighted_bias": m.ratio_with_interval(
                    data, (pl.col(name) - pl.col("load_factor")) * pl.col("seats"), pl.col("seats")
                ),
            }
            for group, data in usable.items()
        }
    return results


def _pressure_event(
    train: pl.DataFrame, validation: pl.DataFrame, quantile: float
) -> dict[str, Any]:
    """Threshold and calibration both come from training rows only."""
    fitted = train.filter((pl.col("seats") > 0) & pl.col("pressure").is_not_null())
    threshold = float(fitted.select(pl.col("pressure").quantile(quantile)).item())
    usable = fitted.filter(pl.col("pred_pressure_seasonal_trend").is_not_null())
    bins = [
        float(usable.select(pl.col("pred_pressure_seasonal_trend").quantile(q / 10)).item())
        for q in range(1, 10)
    ]

    def bucket(value: float) -> int:
        return sum(value > edge for edge in bins)

    counts = [[0, 0] for _ in range(10)]
    for score, pressure in usable.select("pred_pressure_seasonal_trend", "pressure").iter_rows():
        index = bucket(score)
        counts[index][0] += pressure >= threshold
        counts[index][1] += 1
    rates = [hit / total if total else 0.0 for hit, total in counts]
    scored = validation.filter(
        (pl.col("seats") > 0) & pl.col("pred_pressure_seasonal_trend").is_not_null()
    )
    labels = [value >= threshold for value in scored.get_column("pressure").to_list()]
    scores = scored.get_column("pred_pressure_seasonal_trend").to_list()
    probabilities = [rates[bucket(score)] for score in scores]
    return {
        "threshold_from_train": threshold,
        "base_rate_validation": sum(labels) / len(labels) if labels else None,
        "pr_auc": m.average_precision(labels, scores),
        "brier": m.brier(labels, probabilities),
        "rows": len(labels),
    }


def _evaluate_d(train: pl.DataFrame, validation: pl.DataFrame, quantile: float) -> dict[str, Any]:
    results: dict[str, Any] = {}
    groups = {"all": validation, **_segments(validation, "horizon")}
    for target, naive in (("pax", "hist_pax_lag_12"), ("seats", "hist_seats_lag_12")):
        usable_train = train.filter(pl.col(naive).is_not_null())
        squared = usable_train.select(((pl.col(target) - pl.col(naive)) ** 2).mean()).item()
        for name in (f"pred_{target}_seasonal_naive", f"pred_{target}_seasonal_trend"):
            results[name] = {
                group: {
                    "rows": data.height,
                    "wape": m.wape(data, target, name),
                    "bias": m.bias(data, target, name),
                    "rmsse": m.rmsse(data, target, name, squared),
                }
                for group, data in groups.items()
            }
    results["high_pressure_event"] = _pressure_event(train, validation, quantile)
    return results


def _rounded(value: Any) -> Any:
    """Parallel float sums differ around the 15th digit, so reports keep 8 decimals."""
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, dict):
        return {key: _rounded(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_rounded(item) for item in value]
    return value


def evaluate_module(cfg: FeatureConfig, module: str, *, split: str = VALIDATION) -> dict[str, Any]:
    """Score baselines on the validation split and write a report any API can serve."""
    if split == TEST:
        raise SealedTestError("baselines are scored on validation only during model selection")
    contract = CONTRACTS[module]
    directory = cfg.output / f"module_{module}"
    manifest = read_json(directory / "manifest.json")
    features = pl.read_parquet(directory / "features.parquet")
    targets = pl.read_parquet(directory / "targets.parquet")
    assert_no_sealed_targets(targets, cfg.time)
    assert_no_sealed_targets(features, cfg.time)
    features = exclude_unknown_targets(features, manifest.get("unknown_months", []))
    predicted = PREDICTIONS[module](features).filter(pl.col("split").is_in([TRAIN, split]))

    if module == "a":
        joined = predicted.join(targets, on=["airport", "target_date"], how="inner")
        train = joined.filter(pl.col("split") == TRAIN)
        validation = joined.filter(pl.col("split") == split)
        results = _evaluate_a(train, validation)
        keys, values = ["airport", "origin_month", "target_date", "horizon"], ["movements"]
    else:
        keys = [*contract.unit, "origin_month", "target_month", "horizon"]
        joined = predicted.join(targets, on=[*contract.unit, "target_month"], how="left")
        if module == "b":
            joined = joined.with_columns(pl.col("seats").is_not_null().alias("operated"))
            operating = joined.filter(pl.col("operated"))
            results = _evaluate_b(
                operating.filter(pl.col("split") == TRAIN),
                operating.filter(pl.col("split") == split),
                joined.filter(pl.col("split") == split),
            )
            values = ["load_factor", "seats"]
        else:
            # An eligible route without flights in a known month carried zero passengers.
            joined = joined.with_columns(pl.col("pax", "seats").fill_null(0.0)).with_columns(
                pl.when(pl.col("seats") > 0).then(pl.col("pax") / pl.col("seats")).alias("pressure")
            )
            results = _evaluate_d(
                joined.filter(pl.col("split") == TRAIN),
                joined.filter(pl.col("split") == split),
                cfg.d_high_pressure_quantile,
            )
            values = ["pax", "seats", "pressure"]
        train = joined.filter(pl.col("split") == TRAIN)
        validation = joined.filter(pl.col("split") == split)

    prediction_columns = [name for name in joined.columns if name.startswith("pred_")]
    write_parquet_atomic(
        validation.select([*keys, *values, *prediction_columns]),
        directory / "baseline_predictions_validation.parquet",
        zstd_level=3,
    )
    report = {
        "module": module,
        "title": contract.title,
        "kind": "baseline",
        "evaluated_on": (
            f"{split} ({month_label(cfg.time.validation_start)} "
            f"to {month_label(cfg.time.validation_end)})"
        ),
        "dataset": manifest["identity"]["dataset"],
        "dataset_digest": manifest["identity"]["dataset_digest"],
        "config_fingerprint": cfg.fingerprint(),
        "git": git_state(),
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "unknown_months": manifest["unknown_months"],
        "rows": {"train": train.height, split: validation.height},
        "targets": contract.targets,
        "primary_metric": contract.metric,
        "results": results,
    }
    rounded: dict[str, Any] = _rounded(report)
    write_json_atomic(cfg.reports / f"module_{module}.json", rounded)
    return rounded
