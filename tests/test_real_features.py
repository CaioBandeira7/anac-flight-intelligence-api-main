"""The same leakage proof on real panels, when they exist locally."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from anac.features.config import load_feature_config, month_label, parse_month
from anac.features.contracts import MODULE_B, MODULE_D, validate_features
from anac.features.monthly import features_from_history

PANELS = Path("data/features/v1/panels")
CONFIG = Path("configs/features.toml")


@pytest.mark.real_data
@pytest.mark.skipif(not (PANELS / "route_carrier.parquet").exists(), reason="panels not built")
@pytest.mark.parametrize("contract", [MODULE_B, MODULE_D], ids=["b", "d"])
@pytest.mark.parametrize("origin", ["2019-03", "2022-11", "2023-06"])
def test_real_future_cannot_change_features(contract, origin: str) -> None:  # type: ignore[no-untyped-def]
    panel = pl.read_parquet(PANELS / "route_carrier.parquet")
    index = parse_month(origin)
    cutoff = index - 2

    def build(frame: pl.DataFrame) -> pl.DataFrame:
        return features_from_history(
            frame.filter(pl.col("month_idx").is_between(cutoff - 40, cutoff)),
            origin_month=index,
            cutoff=cutoff,
            horizons=(1, 3, 6),
            contract=contract,
            missing=set(),
            active_months=3,
            min_mean_seats=500,
        )

    scrambled = panel.with_columns(
        pl.when(pl.col("month_idx") > cutoff)
        .then(pl.col("pax") * 11 + 3)
        .otherwise(pl.col("pax"))
        .alias("pax")
    )
    original = build(panel)
    validate_features(original, contract)
    assert original.height > 100
    assert original.equals(build(scrambled))


@pytest.mark.real_data
@pytest.mark.skipif(
    not CONFIG.exists() or not (Path("data/features/v1/module_b").exists()), reason="not built"
)
@pytest.mark.parametrize("module", ["a", "b", "d"])
def test_built_outputs_hold_no_test_targets(module: str) -> None:
    cfg = load_feature_config(CONFIG)
    directory = cfg.output / f"module_{module}"
    targets = pl.scan_parquet(directory / "targets.parquet")
    features = pl.scan_parquet(directory / "features.parquet")
    if module == "a":
        last = targets.select(pl.col("target_date").max()).collect().item()
        assert (last.year, last.month) <= (2023, 12)
    else:
        last = targets.select(pl.col("target_month").max()).collect().item()
        assert month_label(last) <= "2023-12"
    assert "test" not in features.select(pl.col("split").unique()).collect().to_series().to_list()
