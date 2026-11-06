"""Essential guarantees of training, on a small synthetic panel."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from anac.evaluation.baselines import evaluate_module
from anac.features.config import FeatureConfig, SealedTestError, TimeConfig, parse_month
from anac.features.contracts import MODULE_D
from anac.features.monthly import build_monthly, monthly_targets
from anac.features.splits import assign_split
from anac.ingestion.storage import write_json_atomic, write_parquet_atomic
from anac.models.train import (
    FrozenModelExists,
    ModelConfig,
    encode,
    fit_vocabulary,
    load_module_frame,
    model_columns,
    train_module,
)
from tests.test_features_leakage import route_panel

PARAMS = {
    "objective": "l1", "metric": "l1", "learning_rate": 0.1, "num_leaves": 7, "min_data_in_leaf": 5,
    "seed": 42, "deterministic": True, "force_col_wise": True, "num_threads": 1, "verbosity": -1,
}  # fmt: skip


@pytest.fixture
def prepared(tmp_path: Path) -> tuple[FeatureConfig, ModelConfig]:
    time = TimeConfig(first_target=parse_month("2021-06"))
    features_cfg = FeatureConfig(
        processed=tmp_path, output=tmp_path / "f", reports=tmp_path / "br", time=time
    )
    panel = route_panel()
    features = assign_split(
        build_monthly(
            panel, MODULE_D, features_cfg, horizons=(1, 3), min_mean_seats=500, missing=set(),
            first_target=time.first_target, last_target=time.validation_end,
        ),
        time,
    )  # fmt: skip
    directory = tmp_path / "f" / "module_d"
    write_parquet_atomic(features, directory / "features.parquet", zstd_level=1)
    write_parquet_atomic(
        monthly_targets(panel, list(MODULE_D.unit), time.validation_end),
        directory / "targets.parquet",
        zstd_level=1,
    )
    write_json_atomic(
        directory / "manifest.json",
        {"identity": {"dataset": "t", "dataset_digest": "x"}, "unknown_months": []},
    )
    evaluate_module(features_cfg, "d")
    cfg = ModelConfig(
        output=tmp_path / "m",
        reports=tmp_path / "mr",
        early_stopping_start=parse_month("2022-01"),
        early_stopping_rounds=5,
        num_boost_round=20,
        params=PARAMS,
    )
    return features_cfg, cfg


def test_inputs_exclude_absolute_time_and_every_target() -> None:
    for module in ("a", "b", "d"):
        numeric, categorical = model_columns(module)
        names = {*numeric, *categorical}
        assert not names & {
            "origin_month",
            "cutoff_month",
            "target_month",
            "target_date",
            "cutoff_date",
        }
        assert not names & {"movements", "load_factor", "pax", "seats", "pressure"}
        assert not any(name.startswith("_") for name in names)
        assert "horizon" in names


def test_unseen_categories_become_missing() -> None:
    fit = pl.DataFrame({"x": [1.0], "carrier": ["AZU"]})
    encoded = encode(
        pl.DataFrame({"x": [2.0], "carrier": ["NEW"]}),
        ["x"],
        ["carrier"],
        fit_vocabulary(fit, ["carrier"]),
    )
    assert np.isnan(encoded[0, 1])


def test_training_compares_with_baselines_and_freezes(
    prepared: tuple[FeatureConfig, ModelConfig],
) -> None:
    features_cfg, cfg = prepared
    report = train_module("d", features_cfg, cfg)
    assert report["evaluated_on"].startswith("validation")
    for name in ("pax", "seats"):
        item = report["targets"][name]
        assert item["lightgbm"]["value"] is not None
        assert item["best_baseline"] in item["baselines"]
        assert item["best_iteration"] >= 1
    manifest = json.loads((cfg.output / "module_d" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "frozen"
    assert manifest["test_period_used"] is False
    assert (cfg.output / "module_d" / "pax.txt").exists()
    with pytest.raises(FrozenModelExists):
        train_module("d", features_cfg, cfg)


def test_training_refuses_test_targets(prepared: tuple[FeatureConfig, ModelConfig]) -> None:
    features_cfg, _ = prepared
    path = features_cfg.output / "module_d" / "targets.parquet"
    targets = pl.read_parquet(path)
    leaked = targets.head(1).with_columns(
        pl.lit(features_cfg.time.test_start, dtype=pl.Int32).alias("target_month")
    )
    write_parquet_atomic(pl.concat([targets, leaked]), path, zstd_level=1)
    with pytest.raises(SealedTestError):
        load_module_frame(features_cfg, "d")
