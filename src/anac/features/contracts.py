"""Explicit input and output contracts of each module.

A feature that is not declared here does not exist. `validate_features` rejects undeclared
columns, wrong types, target-month measurements and anything stamped after the cutoff.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import polars as pl

from anac.features.config import LeakageError


class Source(StrEnum):
    CALENDAR = "calendar"
    """Known long in advance."""
    IDENTITY = "identity"
    """Stable description of the unit, computed from history up to the cutoff."""
    HISTORY = "history"
    """Measured, always at or before the cutoff."""
    TIMING = "timing"
    """Describes the forecast itself (origin, cutoff, horizon)."""


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    dtype: type[pl.DataType]
    source: Source
    description: str


def _specs(source: Source, dtype: type[pl.DataType], items: dict[str, str]) -> list[FeatureSpec]:
    return [FeatureSpec(name, dtype, source, text) for name, text in items.items()]


TIMING_MONTHLY = _specs(
    Source.TIMING,
    pl.Int32,
    {
        "origin_month": "Month in which the forecast is made",
        "cutoff_month": "Last month whose measurements may be used",
        "target_month": "Month being predicted",
        "horizon": "Months from origin to target",
        "distance": "Months from cutoff to target",
    },
)
CALENDAR_MONTHLY = [
    *_specs(
        Source.CALENDAR,
        pl.Int8,
        {
            "cal_month": "Calendar month",
            "cal_days_in_month": "Days in the month",
            "cal_weekend_days": "Saturdays and Sundays",
            "cal_holidays": "National holidays",
        },
    ),
    *_specs(
        Source.CALENDAR,
        pl.Boolean,
        {
            "cal_has_carnival": "Month contains Carnival",
            "cal_is_school_vacation": "January, July or December",
        },
    ),
]
HISTORY_MONTHLY = _specs(
    Source.HISTORY,
    pl.Float64,
    {
        "hist_seats_mean_3": "Mean monthly seats, 3 known months to cutoff",
        "hist_seats_mean_6": "Mean monthly seats, 6 known months to cutoff",
        "hist_seats_mean_12": "Mean monthly seats, 12 known months to cutoff",
        "hist_pax_mean_3": "Mean monthly paid passengers, 3 known months to cutoff",
        "hist_pax_mean_6": "Mean monthly paid passengers, 6 known months to cutoff",
        "hist_pax_mean_12": "Mean monthly paid passengers, 12 known months to cutoff",
        "hist_flights_mean_3": "Mean monthly flights, 3 known months to cutoff",
        "hist_seats_per_flight_3": "Seats per flight, 3 months to cutoff",
        "hist_lf_3": "Seat-weighted paid load factor, 3 months to cutoff",
        "hist_lf_6": "Seat-weighted paid load factor, 6 months to cutoff",
        "hist_lf_12": "Seat-weighted paid load factor, 12 months to cutoff",
        "hist_lf_std_12": "Standard deviation of monthly load factor, 12 months to cutoff",
        "hist_yoy_pax": "Paid passengers, last 3 months over the same months a year earlier",
        "hist_yoy_seats": "Seats, last 3 months over the same months a year earlier",
        "hist_pax_lag_12": "Paid passengers in month T-12 (0 if not flown, null if unknown)",
        "hist_seats_lag_12": "Seats in target month minus 12 (0 if not operated, null if unknown)",
        "hist_lf_lag_12": "Load factor in target month minus 12 (null if not operated or unknown)",
        "hist_pax_lag_24": "Paid passengers in month T-24 (0 if not flown, null if unknown)",
        "hist_seats_lag_24": "Seats in target month minus 24 (0 if not operated, null if unknown)",
        "hist_lf_lag_24": "Load factor in target month minus 24 (null if not operated or unknown)",
        "hist_origin_lf_3": "Load factor of the origin airport, 3 months to cutoff",
        "hist_destination_lf_3": "Load factor of the destination airport, 3 months to cutoff",
        "hist_carriers_on_route_3": "Carriers on the route, 3 months to cutoff",
    },
)
HISTORY_COUNTS = _specs(
    Source.HISTORY,
    pl.Int32,
    {
        "hist_months_observed_12": "Months with flights among the 12 to cutoff",
        "hist_unknown_months_12": "Months with no data at all among the 12 to cutoff",
        "hist_months_since_first": "Months between first flight and cutoff",
    },
)
IDENTITY_ROUTE = [
    *_specs(
        Source.IDENTITY, pl.String, {"origin": "Origin ICAO", "destination": "Destination ICAO"}
    ),
    *_specs(Source.IDENTITY, pl.Float64, {"id_km": "Median route distance up to cutoff"}),
    *_specs(Source.IDENTITY, pl.Boolean, {"id_is_international": "Crosses the border"}),
]
CARRIER_ONLY = [
    *_specs(Source.IDENTITY, pl.String, {"carrier": "Carrier ICAO"}),
    *_specs(
        Source.HISTORY,
        pl.Float64,
        {
            "hist_route_lf_3": "Load factor of the route across carriers, 3 months to cutoff",
            "hist_carrier_lf_3": "Load factor of the carrier across routes, 3 months to cutoff",
            "hist_carrier_seat_share_3": "Carrier share of the route's seats, 3 months to cutoff",
        },
    ),
]
_STAMP_MONTHLY = FeatureSpec(
    "_max_source_month", pl.Int32, Source.TIMING, "Latest month actually read to build this row"
)

TIMING_DAILY = [
    *_specs(
        Source.TIMING,
        pl.Int32,
        {
            "origin_month": "Month in which the forecast is made",
            "horizon": "Months from origin to target",
        },
    ),
    FeatureSpec("cutoff_date", pl.Date, Source.TIMING, "Last date whose measurements may be used"),
    FeatureSpec("target_date", pl.Date, Source.TIMING, "Date being predicted"),
    FeatureSpec("target_month", pl.Int32, Source.TIMING, "Month being predicted"),
    FeatureSpec("distance", pl.Int32, Source.TIMING, "Months from cutoff to target"),
    FeatureSpec("distance_days", pl.Int32, Source.TIMING, "Days from cutoff to target"),
]
CALENDAR_DAILY = [
    *_specs(
        Source.CALENDAR,
        pl.Int8,
        {
            "cal_day_of_week": "0 is Monday",
            "cal_day_of_month": "Day of the month",
            "cal_month": "Calendar month",
            "cal_week_of_year": "ISO week",
        },
    ),
    *_specs(
        Source.CALENDAR,
        pl.Boolean,
        {
            "cal_is_weekend": "Saturday or Sunday",
            "cal_is_holiday": "National holiday",
            "cal_is_carnival": "Carnival Monday or Tuesday",
            "cal_is_day_before_special": "Day before a holiday or Carnival",
            "cal_is_day_after_special": "Day after a holiday or Carnival",
            "cal_is_school_vacation": "January, July or December",
        },
    ),
]
HISTORY_DAILY = _specs(
    Source.HISTORY,
    pl.Float64,
    {
        "hist_lag_364": "Movements 364 days before target (null if unknown)",
        "hist_lag_728": "Movements 728 days before target (null if unknown)",
        "hist_same_dow_mean_8w": "Mean on the target's weekday, 8 weeks to cutoff",
        "hist_level_28": "Mean daily movements, 28 days to cutoff",
        "hist_level_56": "Mean daily movements, 56 days to cutoff",
        "hist_yoy_56": "Last 56 days over the same days a year earlier",
    },
)
_STAMP_DAILY = FeatureSpec(
    "_max_source_date", pl.Date, Source.TIMING, "Latest date actually read to build this row"
)


@dataclass(frozen=True)
class ModuleContract:
    module: str
    title: str
    unit: tuple[str, ...]
    forecast_keys: tuple[str, ...]
    features: tuple[FeatureSpec, ...]
    targets: dict[str, str]
    metric: str
    stamp: str
    limit: str

    @property
    def feature_names(self) -> set[str]:
        return {spec.name for spec in self.features}

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready, so an API or an agent can describe the module without reading code."""
        return {
            "module": self.module,
            "title": self.title,
            "unit": list(self.unit),
            "targets": self.targets,
            "primary_metric": self.metric,
            "features": [
                {
                    "name": spec.name,
                    "type": spec.dtype.__name__,
                    "source": spec.source.value,
                    "description": spec.description,
                }
                for spec in self.features
            ],
        }


MODULE_B = ModuleContract(
    module="b",
    title="Seat occupancy by route and carrier",
    unit=("carrier", "origin", "destination"),
    forecast_keys=("carrier", "origin", "destination", "origin_month", "target_month"),
    features=tuple(
        [
            *TIMING_MONTHLY,
            *CALENDAR_MONTHLY,
            *IDENTITY_ROUTE,
            *CARRIER_ONLY,
            *HISTORY_MONTHLY,
            *HISTORY_COUNTS,
            _STAMP_MONTHLY,
        ]
    ),
    targets={
        "load_factor": "Paid passengers over seats, in the target month",
        "operated": "Whether the unit flew in the target month",
    },
    metric="seat-weighted MAE of load factor",
    stamp="_max_source_month",
    limit="cutoff_month",
)
MODULE_D = ModuleContract(
    module="d",
    title="Demand and capacity by route",
    unit=("origin", "destination"),
    forecast_keys=("origin", "destination", "origin_month", "target_month"),
    features=tuple(
        [
            *TIMING_MONTHLY,
            *CALENDAR_MONTHLY,
            *IDENTITY_ROUTE,
            *HISTORY_MONTHLY,
            *HISTORY_COUNTS,
            _STAMP_MONTHLY,
        ]
    ),
    targets={
        "pax": "Paid passengers carried. Demand served, not unconstrained demand",
        "seats": "Seats operated",
        "pressure": "Paid passengers over seats",
    },
    metric="WAPE of passengers and of seats",
    stamp="_max_source_month",
    limit="cutoff_month",
)
MODULE_A = ModuleContract(
    module="a",
    title="Flight movements by airport and day",
    unit=("airport",),
    forecast_keys=("airport", "origin_month", "target_date"),
    features=tuple(
        [
            *TIMING_DAILY,
            *CALENDAR_DAILY,
            FeatureSpec("airport", pl.String, Source.IDENTITY, "Airport ICAO"),
            FeatureSpec(
                "id_rank_24m", pl.Int32, Source.IDENTITY, "Rank by movements, 24 months to cutoff"
            ),
            *HISTORY_DAILY,
            _STAMP_DAILY,
        ]
    ),
    targets={"movements": "Takeoffs plus landings. Not congestion, delays or queues"},
    metric="WAPE and MASE of daily movements",
    stamp="_max_source_date",
    limit="cutoff_date",
)
CONTRACTS = {"a": MODULE_A, "b": MODULE_B, "d": MODULE_D}

FORBIDDEN_TERMS = (
    "fuel", "combustivel", "bagagem", "baggage", "horas", "partida_real", "chegada_real",
)  # fmt: skip


def validate_features(frame: pl.DataFrame, contract: ModuleContract) -> None:
    """Fail on any column or type outside the contract, or any row stamped after its cutoff."""
    columns = set(frame.columns)
    expected = contract.feature_names
    if columns != expected:
        raise ValueError(
            f"module {contract.module}: undeclared={sorted(columns - expected)} "
            f"missing={sorted(expected - columns)}"
        )
    for spec in contract.features:
        if frame.schema[spec.name] != spec.dtype:
            raise ValueError(
                f"module {contract.module}: {spec.name} is {frame.schema[spec.name]}, "
                f"expected {spec.dtype.__name__}"
            )
    for name in columns:
        if any(term in name.lower() for term in FORBIDDEN_TERMS):
            raise LeakageError(f"column {name} holds a post-flight measurement")
    if frame.is_empty():
        return
    late = frame.filter(pl.col(contract.stamp) > pl.col(contract.limit)).height
    if late:
        raise LeakageError(f"module {contract.module}: {late} rows read data after their cutoff")
    keys = [*contract.forecast_keys]
    if frame.select(pl.struct(keys).is_duplicated().any()).item():
        raise ValueError(f"module {contract.module}: repeated forecast keys")
