"""Metrics by hand and baselines end to end, on synthetic data."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from anac.evaluation import metrics as m
from anac.evaluation.baselines import baselines_a, baselines_b, baselines_d, evaluate_module
from anac.features.calendar_br import (
    carnival_days,
    daily_calendar,
    easter,
    monthly_calendar,
    national_holidays,
)
from anac.features.config import FeatureConfig, TimeConfig, parse_month
from anac.features.contracts import MODULE_B, MODULE_D
from anac.features.monthly import build_monthly, monthly_targets
from anac.features.splits import assign_split
from anac.ingestion.storage import write_json_atomic, write_parquet_atomic
from tests.test_features_leakage import route_panel


def test_wape_and_bias_by_hand() -> None:
    frame = pl.DataFrame(
        {"target_month": [1, 1, 2], "y": [10.0, 20.0, 30.0], "p": [12.0, 16.0, 30.0]}
    )
    assert m.wape(frame, "y", "p")["value"] == pytest.approx(6 / 60)
    assert m.bias(frame, "y", "p")["value"] == pytest.approx(-2 / 60)


def test_weighted_mae_uses_seats_as_weights() -> None:
    frame = pl.DataFrame(
        {"target_month": [1, 1], "y": [0.5, 0.8], "p": [0.6, 0.8], "w": [100.0, 300.0]}
    )
    assert m.weighted_mae(frame, "y", "p", "w")["value"] == pytest.approx(10 / 400)


def test_interval_is_reproducible_and_contains_the_estimate() -> None:
    frame = pl.DataFrame(
        {"target_month": list(range(12)), "y": [100.0] * 12, "p": [100.0 + i for i in range(12)]}
    )
    first, second = m.wape(frame, "y", "p"), m.wape(frame, "y", "p")
    assert first == second
    assert first["ci95"][0] <= first["value"] <= first["ci95"][1]  # type: ignore[index]


def test_average_precision_and_brier_by_hand() -> None:
    assert m.average_precision([True, False, True], [0.9, 0.8, 0.7]) == pytest.approx(
        (1 + 2 / 3) / 2
    )
    assert m.average_precision([False], [0.5]) is None
    assert m.brier([True, False], [1.0, 0.5]) == pytest.approx(0.125)


def test_mase_scale_comes_from_the_naive_error() -> None:
    frame = pl.DataFrame({"y": [10.0, 20.0, None], "n": [12.0, 16.0, 5.0]})
    assert m.mean_absolute_scale(frame, "y", "n") == pytest.approx(3.0)


def test_mase_by_hand_divides_mean_error_by_the_scale() -> None:
    # Regression: the scale was once counted per month instead of per row.
    frame = pl.DataFrame(
        {"target_month": [1, 1, 2, 2], "y": [10.0] * 4, "p": [12.0, 8.0, 13.0, 7.0]}
    )
    assert m.mase(frame, "y", "p", 2.0)["value"] == pytest.approx(2.5 / 2.0)


def test_baseline_a_falls_back_only_when_the_lag_is_unknown() -> None:
    frame = pl.DataFrame(
        {
            "hist_lag_364": [100.0, None],
            "hist_yoy_56": [1.1, 1.1],
            "hist_same_dow_mean_8w": [90.0, 95.0],
            "hist_level_56": [80.0, 85.0],
        }
    )
    result = baselines_a(frame)
    assert result.get_column("pred_seasonal_naive").to_list() == [100.0, 95.0]
    assert result.get_column("pred_seasonal_trend")[0] == pytest.approx(110.0)
    assert result.get_column("pred_seasonal_trend")[1] == 95.0


def test_trend_is_limited_so_one_bad_year_cannot_explode_a_forecast() -> None:
    frame = pl.DataFrame(
        {
            "hist_lag_364": [100.0],
            "hist_yoy_56": [9.0],
            "hist_same_dow_mean_8w": [1.0],
            "hist_level_56": [1.0],
        }
    )
    assert baselines_a(frame).get_column("pred_seasonal_trend")[0] == 200.0


def test_baseline_b_and_d_use_only_declared_history() -> None:
    frame = pl.DataFrame(
        {"hist_lf_lag_12": [0.8, None], "hist_lf_12": [0.7, 0.75], "hist_lf_3": [0.6, 0.65]}
    )
    assert baselines_b(frame).get_column("pred_same_month_last_year").to_list() == [0.8, 0.75]
    route = pl.DataFrame(
        {
            "hist_pax_lag_12": [100.0, 0.0],
            "hist_seats_lag_12": [200.0, 0.0],
            "hist_yoy_pax": [1.1, None],
            "hist_yoy_seats": [1.0, None],
            "hist_pax_mean_12": [90.0, 50.0],
            "hist_seats_mean_12": [180.0, 100.0],
        }
    )
    result = baselines_d(route)
    assert result.get_column("pred_pax_seasonal_trend").to_list() == pytest.approx([110.0, 50.0])
    assert result.get_column("pred_pressure_seasonal_trend").to_list() == pytest.approx([0.55, 0.5])


@pytest.mark.parametrize(("module", "contract"), [("b", MODULE_B), ("d", MODULE_D)])
def test_evaluation_scores_validation_and_records_provenance(
    tmp_path: Path, module: str, contract
) -> None:  # type: ignore[no-untyped-def]
    time = TimeConfig(first_target=parse_month("2022-01"))
    cfg = FeatureConfig(
        processed=tmp_path, output=tmp_path / "f", reports=tmp_path / "r", time=time
    )
    panel = route_panel()
    features = assign_split(
        build_monthly(
            panel, contract, cfg, horizons=(1, 3), min_mean_seats=500, missing=set(),
            first_target=time.first_target, last_target=time.validation_end,
        ),
        time,
    )  # fmt: skip
    targets = monthly_targets(panel, list(contract.unit), time.validation_end)
    directory = tmp_path / "f" / f"module_{module}"
    write_parquet_atomic(features, directory / "features.parquet", zstd_level=1)
    write_parquet_atomic(targets, directory / "targets.parquet", zstd_level=1)
    write_json_atomic(
        directory / "manifest.json",
        {"identity": {"dataset": "test", "dataset_digest": "abc"}, "unknown_months": []},
    )
    report = evaluate_module(cfg, module)
    assert report["evaluated_on"].startswith("validation")
    assert report["kind"] == "baseline"
    assert report["rows"]["validation"] > 0
    assert (tmp_path / "r" / f"module_{module}.json").exists()
    assert (directory / "baseline_predictions_validation.parquet").exists()
    predictions = pl.read_parquet(directory / "baseline_predictions_validation.parquet")
    assert predictions.select((pl.col("target_month") <= time.validation_end).all()).item()
    if module == "d":
        assert 0 < report["results"]["high_pressure_event"]["threshold_from_train"] < 1.5


def test_calendar_facts() -> None:
    assert easter(2024) == date(2024, 3, 31)
    assert easter(2023) == date(2023, 4, 9)
    assert carnival_days(2024) == (date(2024, 2, 12), date(2024, 2, 13))
    assert date(2024, 3, 29) in national_holidays(2024)
    assert date(2024, 11, 20) in national_holidays(2024)
    assert date(2023, 11, 20) not in national_holidays(2023)
    days = daily_calendar(date(2024, 2, 11), date(2024, 2, 14))
    assert days.get_column("cal_is_carnival").to_list() == [False, True, True, False]
    assert days.get_column("cal_is_day_before_special").to_list() == [True, True, False, False]
    month = monthly_calendar([parse_month("2024-02")])
    assert month.get_column("cal_days_in_month")[0] == 29
    assert month.get_column("cal_has_carnival")[0] is True
