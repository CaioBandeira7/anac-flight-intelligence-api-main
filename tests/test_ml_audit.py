"""Regression tests for methodological issues found by the 2023 artifact audit."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from anac.evaluation.baselines import evaluate_module
from anac.evaluation.metrics import average_precision
from anac.features.config import FeatureConfig, SealedTestError, TimeConfig, parse_month
from anac.features.splits import assert_no_sealed_targets, exclude_unknown_targets
from anac.models.train import load_module_frame


@pytest.mark.parametrize("labels", [[True, False], [False, True]])
def test_average_precision_groups_tied_scores(labels: list[bool]) -> None:
    assert average_precision(labels, [0.5, 0.5]) == pytest.approx(0.5)


def test_average_precision_weights_recall_increments_at_distinct_thresholds() -> None:
    assert average_precision([True, False, True], [0.9, 0.9, 0.1]) == pytest.approx(
        (0.5 + 2 / 3) / 2
    )


def test_unknown_target_months_are_excluded_without_removing_known_zero_months() -> None:
    frame = pl.DataFrame(
        {"target_month": [parse_month("2015-08"), parse_month("2015-09")], "pax": [0.0, 0.0]}
    )
    actual = exclude_unknown_targets(frame, ["2015-08"])
    assert actual["target_month"].to_list() == [parse_month("2015-09")]
    assert actual["pax"].to_list() == [0.0]


def test_sealed_daily_guard_uses_configured_boundary() -> None:
    time = TimeConfig(test_start=parse_month("2025-03"))
    assert_no_sealed_targets(pl.DataFrame({"target_date": [date(2025, 2, 28)]}), time)
    with pytest.raises(SealedTestError):
        assert_no_sealed_targets(pl.DataFrame({"target_date": [date(2025, 3, 1)]}), time)


def _input(tmp_path: Path, *, sealed: bool = False) -> FeatureConfig:
    cfg = FeatureConfig(
        processed=tmp_path,
        output=tmp_path / "features",
        reports=tmp_path / "reports",
        time=TimeConfig(),
    )
    folder = cfg.output / "module_d"
    folder.mkdir(parents=True)
    months = [parse_month("2015-08"), parse_month("2015-09"), parse_month("2015-10")]
    frame = pl.DataFrame(
        {
            "origin": ["SBSP"] * 3,
            "destination": ["SBRJ"] * 3,
            "origin_month": [m - 1 for m in months],
            "target_month": months,
            "horizon": [1] * 3,
            "distance": [3] * 3,
            "split": ["train"] * 3,
            "hist_pax_lag_12": [10.0] * 3,
            "hist_seats_lag_12": [20.0] * 3,
            "hist_yoy_pax": [1.0] * 3,
            "hist_yoy_seats": [1.0] * 3,
            "hist_pax_mean_12": [10.0] * 3,
            "hist_seats_mean_12": [20.0] * 3,
        }
    )
    frame.write_parquet(folder / "features.parquet")
    target = pl.DataFrame(
        {
            "origin": ["SBSP"],
            "destination": ["SBRJ"],
            "target_month": [parse_month("2024-01") if sealed else months[-1]],
            "pax": [20.0],
            "seats": [40.0],
        }
    )
    target.write_parquet(folder / "targets.parquet")
    (folder / "manifest.json").write_text(
        json.dumps(
            {
                "identity": {"dataset": "synthetic", "dataset_digest": "test"},
                "unknown_months": ["2015-08"],
            }
        )
    )
    return cfg


def test_model_loader_distinguishes_unknown_month_and_known_route_inactivity(
    tmp_path: Path,
) -> None:
    cfg = _input(tmp_path)
    frame = load_module_frame(cfg, "d").sort("target_month")
    assert frame["target_month"].to_list() == [parse_month("2015-09"), parse_month("2015-10")]
    assert frame["pax"].to_list() == [0.0, 20.0]
    assert frame["seats"].to_list() == [0.0, 40.0]


def test_baseline_evaluation_refuses_sealed_targets_even_if_not_scored(tmp_path: Path) -> None:
    cfg = _input(tmp_path, sealed=True)
    with pytest.raises(SealedTestError):
        evaluate_module(cfg, "d")
    assert not cfg.reports.exists()


def test_model_loader_refuses_mislabeled_future_features(tmp_path: Path) -> None:
    cfg = _input(tmp_path)
    file = cfg.output / "module_d/features.parquet"
    features = pl.read_parquet(file).with_columns(
        pl.lit(parse_month("2024-01")).alias("target_month")
    )
    features.write_parquet(file)
    with pytest.raises(SealedTestError):
        load_module_frame(cfg, "d")
