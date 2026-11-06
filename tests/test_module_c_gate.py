"""The shift detector must blame the carrier that moved, not its peers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import polars as pl


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "assess_module_c", Path("scripts/assess_module_c.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["assess_module_c"] = module
    spec.loader.exec_module(module)
    return module


def series(blocks: dict[str, float] | None = None, seasonal: bool = True) -> pl.DataFrame:
    """Three carriers over 36 months. `blocks` multiplies one carrier in months 18 to 29."""
    rows = []
    for index in range(36):
        season = 1 + 0.15 * (index % 12 == 0) if seasonal else 1.0
        for carrier, level in (("AZU", 8.0), ("GLO", 9.0), ("TAM", 7.0)):
            factor = (blocks or {}).get(carrier, 1.0) if 18 <= index < 30 else 1.0
            rows.append(
                {
                    "carrier": carrier,
                    "y": 2018 + index // 12,
                    "m": index % 12 + 1,
                    "month_idx": 24216 + index,
                    "flights": 100,
                    "pax": 1000,
                    "bag_per_pax": level * season * factor,
                    "share_with_bag": 1.0,
                }
            )
    return pl.DataFrame(rows)


def flagged(rows: list[dict[str, object]], carrier: str) -> list[object]:
    return [row["month_idx"] for row in rows if row["carrier"] == carrier and row["shifted"]]


def test_stable_carriers_are_never_flagged_despite_seasonality() -> None:
    rows = _load().detect_shifts(series())
    assert not [row for row in rows if row["shifted"]]


def test_a_step_is_blamed_only_on_the_carrier_that_moved() -> None:
    rows = _load().detect_shifts(series({"GLO": 0.45}))
    assert flagged(rows, "GLO") == [24216 + index for index in range(18, 30)]
    assert flagged(rows, "AZU") == []
    assert flagged(rows, "TAM") == []


def test_a_market_wide_change_is_not_a_recording_change() -> None:
    rows = _load().detect_shifts(series({"GLO": 0.5, "AZU": 0.5, "TAM": 0.5}))
    assert not [row for row in rows if row["shifted"]]


def test_a_month_with_no_peer_cannot_be_admitted() -> None:
    single = pl.DataFrame(
        {
            "carrier": ["AZU"],
            "y": [2019],
            "m": [1],
            "month_idx": [24228],
            "flights": [1],
            "pax": [1],
            "bag_per_pax": [8.0],
            "share_with_bag": [1.0],
        }
    )
    assert _load().detect_shifts(single)[0]["shifted"] is True
