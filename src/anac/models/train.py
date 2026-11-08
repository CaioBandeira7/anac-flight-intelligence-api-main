"""Train, compare with baselines on 2023, then freeze a final model for the sealed test.

Volumes are modelled as a ratio to the unit's recent level, because trees cannot extrapolate.
With L1 loss weighted by that level, |y - p * level| = level * |y / level - p|, so training
minimises the primary metric (WAPE) directly. Load factor uses L1 weighted by seats.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import polars as pl

from anac.evaluation import metrics as m
from anac.evaluation.baselines import PREDICTIONS
from anac.features.build import git_state
from anac.features.config import FeatureConfig, SealedTestError, month_label, parse_month
from anac.features.contracts import CONTRACTS, Source
from anac.features.splits import (
    PURGED,
    TRAIN,
    VALIDATION,
    assert_no_sealed_targets,
    exclude_unknown_targets,
)
from anac.ingestion.storage import read_json, sha256_file, write_json_atomic, write_parquet_atomic

KEEP_TIMING = {"horizon", "distance", "distance_days"}


class FrozenModelExists(RuntimeError):
    """A frozen model must not change silently."""


@dataclass(frozen=True)
class TargetSpec:
    module: str
    target: str
    scale: str | None
    weight: str
    baselines: tuple[str, ...]


SPECS = (
    TargetSpec(
        "a", "movements", "hist_level_56", "hist_level_56",
        ("pred_seasonal_naive", "pred_seasonal_trend", "pred_recent_weekday"),
    ),
    TargetSpec(
        "b", "load_factor", None, "seats",
        ("pred_same_month_last_year", "pred_mean_12", "pred_mean_3"),
    ),
    TargetSpec(
        "d", "pax", "hist_pax_mean_12", "hist_pax_mean_12",
        ("pred_pax_seasonal_naive", "pred_pax_seasonal_trend"),
    ),
    TargetSpec(
        "d", "seats", "hist_seats_mean_12", "hist_seats_mean_12",
        ("pred_seats_seasonal_naive", "pred_seats_seasonal_trend"),
    ),
)  # fmt: skip


@dataclass(frozen=True)
class ModelConfig:
    output: Path
    reports: Path
    early_stopping_start: int
    early_stopping_rounds: int
    num_boost_round: int
    params: dict[str, Any]


def load_model_config(path: Path, *, root: Path | None = None) -> ModelConfig:
    base = root if root is not None else Path.cwd()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return ModelConfig(
        output=base / raw["paths"]["output"],
        reports=base / raw["paths"]["reports"],
        early_stopping_start=parse_month(raw["training"]["early_stopping_start"]),
        early_stopping_rounds=int(raw["training"]["early_stopping_rounds"]),
        num_boost_round=int(raw["training"]["num_boost_round"]),
        params=raw["lightgbm"],
    )


def model_columns(module: str) -> tuple[list[str], list[str]]:
    """Numeric and categorical inputs, from the contract. Absolute time is left out on purpose."""
    numeric: list[str] = []
    categorical: list[str] = []
    for spec in CONTRACTS[module].features:
        if spec.source is Source.TIMING and spec.name not in KEEP_TIMING:
            continue
        (categorical if spec.dtype == pl.String else numeric).append(spec.name)
    return numeric, categorical


def encode(
    frame: pl.DataFrame,
    numeric: list[str],
    categorical: list[str],
    vocabulary: dict[str, list[str]],
) -> np.ndarray[Any, Any]:
    """Values never seen in fitting become missing."""
    expressions = [pl.col(name).cast(pl.Float64) for name in numeric]
    for name in categorical:
        mapping = {value: float(index) for index, value in enumerate(vocabulary[name])}
        expressions.append(
            pl.col(name).replace_strict(mapping, default=None, return_dtype=pl.Float64).alias(name)
        )
    return frame.select(expressions).to_numpy()


def fit_vocabulary(frame: pl.DataFrame, categorical: list[str]) -> dict[str, list[str]]:
    return {
        name: sorted(frame.get_column(name).drop_nulls().unique().to_list()) for name in categorical
    }


def _label_frame(frame: pl.DataFrame, spec: TargetSpec) -> pl.DataFrame:
    usable = frame.filter(pl.col(spec.target).is_not_null() & (pl.col(spec.weight) > 0))
    if spec.scale:
        return usable.with_columns((pl.col(spec.target) / pl.col(spec.scale)).alias("_label"))
    return usable.with_columns(pl.col(spec.target).alias("_label"))


def _dataset(
    frame: pl.DataFrame,
    spec: TargetSpec,
    numeric: list[str],
    categorical: list[str],
    vocabulary: dict[str, list[str]],
) -> lgb.Dataset:
    return lgb.Dataset(
        encode(frame, numeric, categorical, vocabulary),
        label=frame.get_column("_label").to_numpy(),
        weight=frame.get_column(spec.weight).to_numpy(),
        feature_name=[*numeric, *categorical],
        categorical_feature=categorical,
        free_raw_data=False,
    )


def predict(
    booster: lgb.Booster,
    frame: pl.DataFrame,
    spec: TargetSpec,
    numeric: list[str],
    categorical: list[str],
    vocabulary: dict[str, list[str]],
) -> np.ndarray[Any, Any]:
    raw = booster.predict(encode(frame, numeric, categorical, vocabulary))
    values = np.asarray(raw, dtype=np.float64)
    if spec.scale:
        values = values * frame.get_column(spec.scale).fill_null(0.0).to_numpy()
    return np.clip(values, 0.0, None)


def fit_selection_model(
    data: pl.DataFrame, spec: TargetSpec, cfg: ModelConfig
) -> tuple[lgb.Booster, dict[str, list[str]], dict[str, int]]:
    """Fit on early training with early stopping on its last stretch. Validation is not touched."""
    numeric, categorical = model_columns(spec.module)
    train = _label_frame(data.filter(pl.col("split") == TRAIN), spec)
    start = cfg.early_stopping_start
    fit = train.filter(pl.col("target_month") <= start - pl.col("distance"))
    stopping = train.filter(pl.col("target_month") >= start)
    vocabulary = fit_vocabulary(fit, categorical)
    fit_set = _dataset(fit, spec, numeric, categorical, vocabulary)
    stop_set = _dataset(stopping, spec, numeric, categorical, vocabulary)
    booster = lgb.train(
        cfg.params,
        fit_set,
        num_boost_round=cfg.num_boost_round,
        valid_sets=[stop_set],
        callbacks=[lgb.early_stopping(cfg.early_stopping_rounds, verbose=False)],
    )
    return booster, vocabulary, {"fit": fit.height, "early_stopping": stopping.height}


def fit_final_model(
    data: pl.DataFrame, spec: TargetSpec, cfg: ModelConfig, rounds: int, test_start: int
) -> tuple[lgb.Booster, dict[str, list[str]], int]:
    """Refit on everything known at the first test origin, keeping the chosen number of rounds."""
    numeric, categorical = model_columns(spec.module)
    rows = _label_frame(
        data.filter(
            pl.col("split").is_in([TRAIN, PURGED, VALIDATION])
            & (pl.col("target_month") <= test_start - pl.col("distance"))
        ),
        spec,
    )
    vocabulary = fit_vocabulary(rows, categorical)
    booster = lgb.train(
        cfg.params,
        _dataset(rows, spec, numeric, categorical, vocabulary),
        num_boost_round=rounds,
    )
    return booster, vocabulary, rows.height


def load_module_frame(features_cfg: FeatureConfig, module: str) -> pl.DataFrame:
    """Features, labels and baseline predictions. The test period does not exist in these files."""
    contract = CONTRACTS[module]
    directory = features_cfg.output / f"module_{module}"
    features = pl.read_parquet(directory / "features.parquet")
    targets = pl.read_parquet(directory / "targets.parquet")
    assert_no_sealed_targets(targets, features_cfg.time)
    assert_no_sealed_targets(features, features_cfg.time)
    if features.filter(pl.col("split") == "test").height:
        raise SealedTestError("test rows are present in the features")
    manifest = read_json(directory / "manifest.json")
    features = exclude_unknown_targets(features, manifest.get("unknown_months", []))
    with_baselines = PREDICTIONS[module](features)
    if module == "a":
        return with_baselines.join(targets, on=["airport", "target_date"], how="inner")
    joined = with_baselines.join(targets, on=[*contract.unit, "target_month"], how="left")
    if module == "d":
        return joined.with_columns(pl.col("pax", "seats").fill_null(0.0)).with_columns(
            pl.when(pl.col("seats") > 0).then(pl.col("pax") / pl.col("seats")).alias("pressure")
        )
    return joined.filter(pl.col("seats").is_not_null())


def _error(frame: pl.DataFrame, spec: TargetSpec, predicted: str) -> dict[str, object]:
    if spec.module == "b":
        return m.weighted_mae(frame, spec.target, predicted, "seats")
    return m.wape(frame, spec.target, predicted)


def _paired_difference(
    frame: pl.DataFrame, spec: TargetSpec, model: str, baseline: str
) -> dict[str, object]:
    """Model error minus baseline error on the same rows. Negative means the model is better."""
    actual = pl.col(spec.target)
    gap = (pl.col(model) - actual).abs() - (pl.col(baseline) - actual).abs()
    if spec.module == "b":
        return m.ratio_with_interval(frame, gap * pl.col("seats"), pl.col("seats"))
    return m.ratio_with_interval(frame, gap, actual.abs())


def compare(validation: pl.DataFrame, spec: TargetSpec, prediction: str) -> dict[str, Any]:
    """Model against every baseline, overall and per horizon, on identical rows."""
    frame = validation.filter(
        pl.all_horizontal(pl.col(name).is_not_null() for name in spec.baselines)
    )
    baselines = {name: _error(frame, spec, name) for name in spec.baselines}
    best = min(baselines, key=lambda name: float(baselines[name]["value"]))  # type: ignore[arg-type]
    difference = _paired_difference(frame, spec, prediction, best)
    interval = difference["ci95"]
    result: dict[str, Any] = {
        "rows": frame.height,
        "metric": "seat-weighted MAE" if spec.module == "b" else "WAPE",
        "lightgbm": _error(frame, spec, prediction),
        "baselines": baselines,
        "best_baseline": best,
        "difference_vs_best_baseline": difference,
        "beats_best_baseline": bool(interval and interval[1] < 0),  # type: ignore[index]
        "bias": m.bias(frame, spec.target, prediction),
        "by_horizon": {},
    }
    for horizon in sorted(frame.get_column("horizon").unique().to_list()):
        part = frame.filter(pl.col("horizon") == horizon)
        horizon_baselines = {name: _error(part, spec, name)["value"] for name in spec.baselines}
        horizon_best = min(horizon_baselines, key=lambda name: float(horizon_baselines[name]))  # type: ignore[arg-type]
        gap = _paired_difference(part, spec, prediction, horizon_best)
        result["by_horizon"][str(horizon)] = {
            "lightgbm": _error(part, spec, prediction)["value"],
            "best_baseline": horizon_best,
            "best_baseline_value": horizon_baselines[horizon_best],
            "difference": gap["value"],
            "ci95": gap["ci95"],
        }
    return result


def _importance(booster: lgb.Booster) -> dict[str, float]:
    gains = booster.feature_importance(importance_type="gain")
    total = float(gains.sum()) or 1.0
    ranked = sorted(zip(booster.feature_name(), gains, strict=True), key=lambda pair: -pair[1])
    return {name: round(float(gain) / total, 4) for name, gain in ranked[:10]}


def _pressure_event(
    data: pl.DataFrame, validation: pl.DataFrame, threshold: float, start: int
) -> dict[str, Any]:
    """Calibrate on the early-stopping stretch, which the fitted trees did not train on."""
    calibration = data.filter(
        (pl.col("split") == TRAIN) & (pl.col("target_month") >= start) & (pl.col("seats") > 0)
        & pl.col("pred_pressure").is_not_null()
    )  # fmt: skip
    edges = [
        float(calibration.select(pl.col("pred_pressure").quantile(q / 10)).item())
        for q in range(1, 10)
    ]

    def bucket(value: float) -> int:
        return sum(value > edge for edge in edges)

    counts = [[0, 0] for _ in range(10)]
    for score, actual in calibration.select("pred_pressure", "pressure").iter_rows():
        counts[bucket(score)][0] += actual >= threshold
        counts[bucket(score)][1] += 1
    rates = [hit / total if total else 0.0 for hit, total in counts]
    scored = validation.filter((pl.col("seats") > 0) & pl.col("pred_pressure").is_not_null())
    labels = [value >= threshold for value in scored.get_column("pressure").to_list()]
    scores = scored.get_column("pred_pressure").to_list()
    return {
        "threshold_from_train": threshold,
        "rows": len(labels),
        "base_rate_validation": sum(labels) / len(labels) if labels else None,
        "pr_auc": m.average_precision(labels, scores),
        "brier": m.brier(labels, [rates[bucket(score)] for score in scores]),
    }


def train_module(module: str, features_cfg: FeatureConfig, cfg: ModelConfig) -> dict[str, Any]:
    manifest_path = cfg.output / f"module_{module}" / "manifest.json"
    if manifest_path.exists():
        raise FrozenModelExists(f"{manifest_path} exists. Frozen models are never overwritten.")
    data = load_module_frame(features_cfg, module)
    feature_manifest = read_json(features_cfg.output / f"module_{module}" / "manifest.json")
    directory = cfg.output / f"module_{module}"
    directory.mkdir(parents=True, exist_ok=True)
    targets: dict[str, Any] = {}
    frozen: dict[str, Any] = {}

    for spec in (item for item in SPECS if item.module == module):
        numeric, categorical = model_columns(module)
        booster, vocabulary, sizes = fit_selection_model(data, spec, cfg)
        rounds = int(booster.best_iteration)
        name = f"pred_lightgbm_{spec.target}"
        scorable = data.with_columns(pl.col(spec.weight).fill_null(0.0))
        data = data.with_columns(
            pl.Series(name, predict(booster, scorable, spec, numeric, categorical, vocabulary))
        )
        validation = data.filter(pl.col("split") == VALIDATION)
        targets[spec.target] = {
            **compare(validation, spec, name),
            "rows_fit": sizes["fit"],
            "rows_early_stopping": sizes["early_stopping"],
            "best_iteration": rounds,
            "top_features_by_gain": _importance(booster),
        }
        final, final_vocabulary, final_rows = fit_final_model(
            data, spec, cfg, rounds, features_cfg.time.test_start
        )
        model_path = directory / f"{spec.target}.txt"
        final.save_model(str(model_path))
        vocabulary_path = directory / f"{spec.target}.vocabulary.json"
        vocabulary_path.write_text(
            json.dumps(final_vocabulary, ensure_ascii=False), encoding="utf-8"
        )
        frozen[spec.target] = {
            "file": model_path.name,
            "sha256": sha256_file(model_path),
            "rows": final_rows,
            "rounds": rounds,
            "numeric": numeric,
            "categorical": categorical,
            "scale": spec.scale,
            "last_target_month_used": month_label(features_cfg.time.test_start - 3),
        }

    extras: dict[str, Any] = {}
    if module == "d":
        data = data.with_columns(
            pl.when(pl.col("pred_lightgbm_seats") > 0)
            .then(pl.col("pred_lightgbm_pax") / pl.col("pred_lightgbm_seats"))
            .alias("pred_pressure")
        )
        baseline_report = json.loads(
            (features_cfg.reports / "module_d.json").read_text(encoding="utf-8")
        )
        event = baseline_report["results"]["high_pressure_event"]
        extras["high_pressure_event"] = {
            "lightgbm": _pressure_event(
                data,
                data.filter(pl.col("split") == VALIDATION),
                event["threshold_from_train"],
                cfg.early_stopping_start,
            ),
            "baseline": event,
        }

    contract = CONTRACTS[module]
    keys = [*contract.forecast_keys, "horizon"]
    prediction_columns = [name for name in data.columns if name.startswith("pred_lightgbm")]
    write_parquet_atomic(
        data.filter(pl.col("split") == VALIDATION).select(
            [*keys, *[item.target for item in SPECS if item.module == module], *prediction_columns]
        ),
        features_cfg.output / f"module_{module}" / "lightgbm_predictions_validation.parquet",
        zstd_level=3,
    )
    trained_at = datetime.now(UTC).isoformat(timespec="seconds")
    params = hashlib.sha256(json.dumps(cfg.params, sort_keys=True).encode()).hexdigest()[:16]
    write_json_atomic(
        manifest_path,
        {
            "module": module,
            "status": "frozen",
            "trained_at": trained_at,
            "dataset": feature_manifest["identity"]["dataset"],
            "dataset_digest": feature_manifest["identity"]["dataset_digest"],
            "params_fingerprint": params,
            "params": cfg.params,
            "git": git_state(),
            "models": frozen,
            "test_period_used": False,
        },
    )
    report = {
        "module": module,
        "title": contract.title,
        "kind": "lightgbm",
        "evaluated_on": (
            f"validation ({month_label(features_cfg.time.validation_start)} "
            f"to {month_label(features_cfg.time.validation_end)})"
        ),
        "dataset": feature_manifest["identity"]["dataset"],
        "unknown_months": feature_manifest["unknown_months"],
        "trained_at": trained_at,
        "params_fingerprint": params,
        "targets": targets,
        **extras,
    }
    write_json_atomic(cfg.reports / f"module_{module}.json", report)
    return report
