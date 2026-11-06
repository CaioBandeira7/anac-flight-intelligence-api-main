"""Feature configuration and month arithmetic."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path


def month_index(year: int, month: int) -> int:
    return year * 12 + month - 1


def parse_month(text: str) -> int:
    year, month = text.split("-")
    return month_index(int(year), int(month))


def month_label(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


@dataclass(frozen=True)
class TimeConfig:
    publication_lag_months: int = 2
    first_target: int = parse_month("2013-01")
    validation_start: int = parse_month("2023-01")
    validation_end: int = parse_month("2023-12")
    test_start: int = parse_month("2024-01")
    test_end: int = parse_month("2025-12")

    def distance(self, horizon: int) -> int:
        """Months between the last known month and the target month."""
        return horizon + self.publication_lag_months


@dataclass(frozen=True)
class FeatureConfig:
    processed: Path
    output: Path
    reports: Path
    time: TimeConfig
    max_flight_load_factor: float = 1.5
    active_months: int = 3
    a_horizons: tuple[int, ...] = (1, 3)
    a_top_airports: int = 50
    b_horizons: tuple[int, ...] = (1, 3, 6)
    b_min_mean_seats: float = 500
    d_horizons: tuple[int, ...] = (1, 3, 6)
    d_min_mean_seats: float = 500
    d_high_pressure_quantile: float = 0.75

    def fingerprint(self) -> str:
        payload = asdict(self)
        for key in ("processed", "output", "reports"):
            payload.pop(key)
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def load_feature_config(path: Path, *, root: Path | None = None) -> FeatureConfig:
    base = root if root is not None else Path.cwd()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    time = raw["time"]
    return FeatureConfig(
        processed=base / raw["paths"]["processed"],
        output=base / raw["paths"]["output"],
        reports=base / raw["paths"]["reports"],
        time=TimeConfig(
            publication_lag_months=int(time["publication_lag_months"]),
            first_target=parse_month(time["first_target"]),
            validation_start=parse_month(time["validation_start"]),
            validation_end=parse_month(time["validation_end"]),
            test_start=parse_month(time["test_start"]),
            test_end=parse_month(time["test_end"]),
        ),
        max_flight_load_factor=float(raw["scope"]["max_flight_load_factor"]),
        active_months=int(raw["scope"]["active_months"]),
        a_horizons=tuple(raw["module_a"]["horizons"]),
        a_top_airports=int(raw["module_a"]["top_airports"]),
        b_horizons=tuple(raw["module_b"]["horizons"]),
        b_min_mean_seats=float(raw["module_b"]["min_mean_seats"]),
        d_horizons=tuple(raw["module_d"]["horizons"]),
        d_min_mean_seats=float(raw["module_d"]["min_mean_seats"]),
        d_high_pressure_quantile=float(raw["module_d"]["high_pressure_quantile"]),
    )


class LeakageError(RuntimeError):
    """Data from after the cutoff reached code that must only see the past."""


class SealedTestError(RuntimeError):
    """Test targets were requested without explicitly unsealing them."""
