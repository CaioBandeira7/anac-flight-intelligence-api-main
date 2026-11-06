"""Aggregate flights into the panels every module reads."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import polars as pl

from anac.features.config import FeatureConfig, month_index

DATASET_PRIORITY = ("flights_v2_1", "flights")


def resolve_dataset(processed: Path) -> tuple[Path, str]:
    """Use the newest published version, and report which one, so builds are traceable."""
    for name in DATASET_PRIORITY:
        path = processed / name
        if path.is_dir() and any(path.glob("*/*/*.parquet")):
            return path, name
    raise FileNotFoundError(f"no published flights dataset in {processed}")


def scan_flights(path: Path) -> pl.LazyFrame:
    return pl.scan_parquet((path / "*" / "*" / "*.parquet").as_posix(), hive_partitioning=False)


def _month_expr(column: str = "dt_referencia") -> pl.Expr:
    return (
        pl.col(column).dt.year().cast(pl.Int32) * 12 + pl.col(column).dt.month().cast(pl.Int32) - 1
    )


def passenger_scope(flights: pl.LazyFrame, cfg: FeatureConfig) -> pl.LazyFrame:
    """Passenger legs that took place, without repeated or implausible records."""
    return flights.filter(
        ~pl.col("dq_duplicate_record")
        & ~pl.col("dq_no_takeoff")
        & (pl.col("nr_assentos_ofertados") > 0)
        & (pl.col("ds_grupo_di") != "IMPRODUTIVO")
        & ~pl.col("dq_zero_distance")
        & ~pl.col("dq_same_origin_destination")
        & pl.col("nr_passag_pagos").is_not_null()
        & (pl.col("load_factor_paid") <= cfg.max_flight_load_factor)
    )


def route_carrier_panel(flights: pl.LazyFrame, cfg: FeatureConfig) -> pl.DataFrame:
    """Module B's unit, from which module D's route totals are also derived."""
    return (
        passenger_scope(flights, cfg)
        .with_columns(_month_expr().alias("month_idx"))
        .group_by(
            "month_idx",
            pl.col("sg_empresa_icao").alias("carrier"),
            pl.col("sg_icao_origem").alias("origin"),
            pl.col("sg_icao_destino").alias("destination"),
        )
        .agg(
            pl.col("nr_passag_pagos").sum().cast(pl.Float64).alias("pax"),
            pl.col("nr_assentos_ofertados").sum().cast(pl.Float64).alias("seats"),
            pl.col("nr_decolagem").sum().cast(pl.Float64).alias("flights"),
            pl.col("km_distancia").median().alias("km"),
            pl.col("is_international").any().alias("is_international"),
        )
        .collect(engine="streaming")
        .sort("month_idx", "carrier", "origin", "destination")
    )


def known_months(flights: pl.LazyFrame) -> set[int]:
    """Months that have rows at all. Any other month inside the range is unknown, not zero."""
    frame = flights.select(_month_expr().alias("m")).unique().collect(engine="streaming")
    return set(frame.get_column("m").to_list())


def missing_months(known: set[int]) -> set[int]:
    return set(range(min(known), max(known) + 1)) - known


def masked_dates(missing: set[int]) -> set[date]:
    """Days inside a missing month, plus the adjacent days that lose flights crossing midnight."""
    days: set[date] = set()
    for index in missing:
        year, zero_month = divmod(index, 12)
        first = date(year, zero_month + 1, 1)
        following = date(year + (zero_month == 11), (zero_month + 1) % 12 + 1, 1)
        current = first - timedelta(days=1)
        while current <= following:
            days.add(current)
            current += timedelta(days=1)
    return days


def airport_day_panel(flights: pl.LazyFrame, missing: set[int]) -> pl.DataFrame:
    """Landings and takeoffs per airport and day, by actual date, with explicit unknown days."""
    usable = flights.filter(~pl.col("dq_duplicate_record") & ~pl.col("dq_no_takeoff"))
    departure = (
        pl.when(pl.col("dt_partida_real").is_null() | pl.col("dq_departure_reference_gap"))
        .then(pl.col("dt_referencia"))
        .otherwise(pl.col("dt_partida_real"))
    )
    arrival = (
        pl.when(
            pl.col("dt_chegada_real").is_null()
            | ((pl.col("dt_chegada_real") - departure).dt.total_days().abs() > 2)
        )
        .then(departure)
        .otherwise(pl.col("dt_chegada_real"))
    )
    takeoffs = usable.select(pl.col("sg_icao_origem").alias("airport"), departure.alias("date"))
    landings = usable.select(pl.col("sg_icao_destino").alias("airport"), arrival.alias("date"))
    counted = (
        pl.concat([takeoffs, landings])
        .group_by("airport", "date")
        .agg(pl.len().cast(pl.Int32).alias("movements"))
        .collect(engine="streaming")
    )
    return complete_airport_days(counted, missing)


def complete_airport_days(counted: pl.DataFrame, missing: set[int]) -> pl.DataFrame:
    """Add days without flights as 0 and days in unknown periods as null."""
    last = counted.get_column("date").max()
    spans = counted.group_by("airport").agg(pl.col("date").min().alias("first"))
    grid = (
        spans.with_columns(pl.date_ranges(pl.col("first"), pl.lit(last), "1d").alias("date"))
        .explode("date")
        .drop("first")
    )
    panel = grid.join(counted, on=["airport", "date"], how="left").with_columns(
        pl.col("movements").fill_null(0)
    )
    unknown = masked_dates(missing)
    if unknown:
        panel = panel.with_columns(
            pl.when(pl.col("date").is_in(list(unknown), nulls_equal=True))
            .then(None)
            .otherwise(pl.col("movements"))
            .alias("movements")
        )
    return panel.sort("airport", "date")


__all__ = [
    "airport_day_panel",
    "known_months",
    "masked_dates",
    "missing_months",
    "month_index",
    "passenger_scope",
    "resolve_dataset",
    "route_carrier_panel",
    "scan_flights",
]
