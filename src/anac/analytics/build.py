"""Build the monthly star schema from published flights, without changing them.

Every fact table is rolled up from one base table (month x carrier x origin x destination), so
totals cannot diverge between them. Dimensions have one row per key, so joins cannot multiply rows.
Output is published atomically, and only after validation passes.
"""

from __future__ import annotations

import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import polars as pl

from anac.analytics.validate import validate_tables
from anac.features.build import dataset_digest, git_state
from anac.features.calendar_br import monthly_calendar
from anac.features.config import FeatureConfig, month_label
from anac.features.panels import (
    known_months,
    missing_months,
    passenger_scope,
    resolve_dataset,
    scan_flights,
)
from anac.ingestion.storage import (
    publish_directory,
    read_json,
    write_json_atomic,
    write_parquet_atomic,
)
from anac.serving.export import load_airports

ROUTE_KEY = ["month", "origin", "destination"]
BASE_KEY = ["month", "carrier", "origin", "destination"]
PASSENGER_MEASURES = [
    "passenger_takeoffs",
    "paid_passengers",
    "free_passengers",
    "seats",
    "rpk",
    "ask",
]
ALL_FLIGHT_MEASURES = [
    "source_rows",
    "all_takeoffs",
    "all_paid_passengers",
    "paid_cargo_kg",
    "free_cargo_kg",
    "mail_kg",
]
ADDITIVE = [*ALL_FLIGHT_MEASURES, *PASSENGER_MEASURES]
TABLES = (
    "dim_month",
    "dim_airport",
    "dim_carrier",
    "fact_route_carrier_month",
    "fact_route_month",
    "fact_carrier_month",
    "fact_airport_month",
)

COLUMN_DOCS = {
    "month": "First day of the reference month (date)",
    "source_rows": "Flight legs in the source, without repeated records (count)",
    "all_takeoffs": "Takeoffs of all operated flights, including cargo and positioning (count)",
    "all_paid_passengers": "Paid passengers on all legs, per leg (count). For reconciliation",
    "paid_cargo_kg": "Paid cargo on all legs (kg)",
    "free_cargo_kg": "Free cargo on all legs (kg)",
    "mail_kg": "Mail on all legs (kg)",
    "passenger_takeoffs": "Takeoffs in passenger scope (count)",
    "paid_passengers": "Paid passengers in passenger scope, per leg (count)",
    "free_passengers": "Free passengers in passenger scope, per leg (count)",
    "seats": "Seats offered in passenger scope (count)",
    "rpk": "Revenue passenger-kilometres in passenger scope (passenger-km)",
    "ask": "Available seat-kilometres in passenger scope (seat-km)",
    "load_factor_paid": "paid_passengers / seats (ratio from 0, may exceed 1). Recompute when aggregating",
    "distance_km": "Median leg distance (km). Not additive",
    "carriers": "Distinct carriers (count). Not additive",
    "routes": "Distinct directed routes (count). Not additive",
    "is_international": "Crosses the border (boolean)",
    "departures": "Takeoffs at this airport, all operated flights (count)",
    "arrivals": "Landings at this airport, all operated flights (count)",
    "movements": "departures + arrivals (count)",
    "departing_paid_passengers": "Paid passengers leaving, passenger scope, per leg (count)",
    "arriving_paid_passengers": "Paid passengers arriving, passenger scope, per leg (count)",
    "international_paid_passengers": "Paid passengers on international legs, passenger scope (count)",
    "international_takeoffs": "Takeoffs on international legs, passenger scope (count)",
}


class AnalyticsStale(RuntimeError):
    """Existing tables came from another dataset."""


def _with_month(frame: pl.LazyFrame) -> pl.LazyFrame:
    return frame.with_columns(pl.col("dt_referencia").dt.truncate("1mo").alias("month"))


def _keyed(frame: pl.LazyFrame) -> pl.LazyFrame:
    return _with_month(frame).with_columns(
        pl.col("sg_empresa_icao").alias("carrier"),
        pl.col("sg_icao_origem").alias("origin"),
        pl.col("sg_icao_destino").alias("destination"),
    )


def with_load_factor(frame: pl.DataFrame) -> pl.DataFrame:
    """Always from summed values. An average of ratios would weigh a small route like a large one."""
    return frame.with_columns(
        pl.when(pl.col("seats") > 0)
        .then(pl.col("paid_passengers") / pl.col("seats"))
        .alias("load_factor_paid")
    )


def build_base(flights: pl.LazyFrame, cfg: FeatureConfig) -> pl.DataFrame:
    """The grain everything else rolls up from. Repeated records are left out."""
    operated = (
        _keyed(flights.filter(~pl.col("dq_duplicate_record")))
        .group_by(BASE_KEY)
        .agg(
            pl.len().cast(pl.Int64).alias("source_rows"),
            pl.col("nr_decolagem").sum().cast(pl.Int64).alias("all_takeoffs"),
            pl.col("nr_passag_pagos").sum().cast(pl.Int64).alias("all_paid_passengers"),
            pl.col("kg_carga_paga").sum().alias("paid_cargo_kg"),
            pl.col("kg_carga_gratis").sum().alias("free_cargo_kg"),
            pl.col("kg_correio").sum().alias("mail_kg"),
            pl.col("km_distancia").median().alias("distance_km"),
            pl.col("is_international").any().alias("is_international"),
        )
        .collect(engine="streaming")
    )
    passengers = (
        _keyed(passenger_scope(flights, cfg))
        .group_by(BASE_KEY)
        .agg(
            pl.col("nr_decolagem").sum().cast(pl.Int64).alias("passenger_takeoffs"),
            pl.col("nr_passag_pagos").sum().cast(pl.Int64).alias("paid_passengers"),
            pl.col("nr_passag_gratis").sum().cast(pl.Int64).alias("free_passengers"),
            pl.col("nr_assentos_ofertados").sum().cast(pl.Int64).alias("seats"),
            pl.col("nr_rpk").sum().alias("rpk"),
            pl.col("nr_ask").sum().alias("ask"),
        )
        .collect(engine="streaming")
    )
    joined = operated.join(passengers, on=BASE_KEY, how="left", validate="1:1").with_columns(
        pl.col("passenger_takeoffs", "paid_passengers", "free_passengers", "seats").fill_null(0),
        pl.col("rpk", "ask").fill_null(0.0),
    )
    return with_load_factor(joined).sort(BASE_KEY)


def _sums() -> list[pl.Expr]:
    return [pl.col(name).sum() for name in ADDITIVE]


def build_route_month(base: pl.DataFrame) -> pl.DataFrame:
    """Directed: A to B and B to A stay separate rows."""
    rolled = base.group_by(ROUTE_KEY).agg(
        *_sums(),
        pl.col("distance_km").median(),
        pl.col("is_international").any(),
        pl.col("carrier").n_unique().cast(pl.Int32).alias("carriers"),
    )
    return with_load_factor(rolled).sort(ROUTE_KEY)


def build_carrier_month(base: pl.DataFrame) -> pl.DataFrame:
    international = pl.col("is_international")
    rolled = base.group_by("month", "carrier").agg(
        *_sums(),
        pl.col("paid_passengers")
        .filter(international)
        .sum()
        .alias("international_paid_passengers"),
        pl.col("passenger_takeoffs").filter(international).sum().alias("international_takeoffs"),
        pl.struct("origin", "destination").n_unique().cast(pl.Int32).alias("routes"),
    )
    return with_load_factor(rolled).sort("month", "carrier")


def build_airport_month(base: pl.DataFrame) -> pl.DataFrame:
    leaving = base.group_by("month", pl.col("origin").alias("airport")).agg(
        pl.col("all_takeoffs").sum().alias("departures"),
        pl.col("paid_passengers").sum().alias("departing_paid_passengers"),
    )
    arriving = base.group_by("month", pl.col("destination").alias("airport")).agg(
        pl.col("all_takeoffs").sum().alias("arrivals"),
        pl.col("paid_passengers").sum().alias("arriving_paid_passengers"),
    )
    joined = leaving.join(
        arriving, on=["month", "airport"], how="full", coalesce=True, validate="1:1"
    )
    filled = joined.with_columns(
        pl.col(
            "departures", "departing_paid_passengers", "arrivals", "arriving_paid_passengers"
        ).fill_null(0)
    )
    return filled.with_columns((pl.col("departures") + pl.col("arrivals")).alias("movements")).sort(
        "month", "airport"
    )


def _month_date(index: int) -> date:
    return date(index // 12, index % 12 + 1, 1)


def build_dim_month(known: set[int]) -> pl.DataFrame:
    """Every month in the covered range, including those with no data, which are marked as such."""
    indexes = list(range(min(known), max(known) + 1))
    calendar = monthly_calendar(indexes).rename(
        {
            "cal_days_in_month": "days_in_month",
            "cal_weekend_days": "weekend_days",
            "cal_holidays": "national_holidays",
            "cal_has_carnival": "has_carnival",
            "cal_is_school_vacation": "is_school_vacation",
            "cal_month": "month_number",
        }
    )
    return calendar.with_columns(
        pl.col("target_month").map_elements(_month_date, return_dtype=pl.Date).alias("month"),
        pl.col("target_month").map_elements(month_label, return_dtype=pl.String).alias("month_label"),
        (pl.col("target_month") // 12).cast(pl.Int32).alias("year"),
        ((pl.col("month_number").cast(pl.Int32) - 1) // 3 + 1).cast(pl.Int8).alias("quarter"),
        pl.col("target_month").is_in(sorted(known)).alias("has_data"),
    ).select(
        "month", "month_label", "year", "quarter", "month_number", "days_in_month", "weekend_days",
        "national_holidays", "has_carnival", "is_school_vacation", "has_data",
    )  # fmt: skip


def _latest(column: str) -> pl.Expr:
    """The most recent known value: names and codes change over 26 years."""
    return pl.col(column).sort_by("month").drop_nulls().last()


def build_dim_airport(flights: pl.LazyFrame, airports_csv: Path | None) -> pl.DataFrame:
    def side(prefix: str) -> pl.LazyFrame:
        return _with_month(flights).select(
            "month",
            pl.col(f"sg_icao_{prefix}").alias("airport"),
            pl.col(f"sg_iata_{prefix}").alias("iata"),
            pl.col(f"nm_aerodromo_{prefix}").alias("name"),
            pl.col(f"nm_municipio_{prefix}").alias("city"),
            pl.col(f"sg_uf_{prefix}").alias("uf"),
            pl.col(f"nm_regiao_{prefix}").alias("region"),
            pl.col(f"nm_pais_{prefix}").alias("country"),
            pl.col(f"nm_continente_{prefix}").alias("continent"),
        )

    unique = pl.concat([side("origem"), side("destino")]).unique().collect(engine="streaming")
    dim = unique.group_by("airport").agg(
        *[
            _latest(name)
            for name in ("iata", "name", "city", "uf", "region", "country", "continent")
        ],
        pl.col("month").min().alias("first_month"),
        pl.col("month").max().alias("last_month"),
    )
    if airports_csv is not None and airports_csv.exists():
        coordinates = load_airports(airports_csv).select(
            pl.col("icao").alias("airport"), "lat", "lon"
        )
        dim = dim.join(coordinates, on="airport", how="left", validate="1:1")
    else:
        dim = dim.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("lat"), pl.lit(None, dtype=pl.Float64).alias("lon")
        )
    return dim.sort("airport")


def build_dim_carrier(flights: pl.LazyFrame) -> pl.DataFrame:
    unique = (
        _with_month(flights)
        .select(
            "month",
            pl.col("sg_empresa_icao").alias("carrier"),
            pl.col("sg_empresa_iata").alias("iata"),
            pl.col("nm_empresa").alias("name"),
            pl.col("nm_pais").alias("country"),
        )
        .unique()
        .collect(engine="streaming")
    )
    return (
        unique.group_by("carrier")
        .agg(
            _latest("iata"),
            _latest("name"),
            _latest("country"),
            pl.col("name").n_unique().cast(pl.Int32).alias("name_variants"),
            pl.col("month").min().alias("first_month"),
            pl.col("month").max().alias("last_month"),
        )
        .sort("carrier")
    )


def build_analytics(
    cfg: FeatureConfig, output: Path, report: Path, airports_csv: Path | None = None
) -> dict[str, Any]:
    """Build, validate against the source, then publish. Nothing partial is ever visible."""
    dataset, version = resolve_dataset(cfg.processed)
    digest = dataset_digest(dataset)
    identity = {"dataset": version, "dataset_digest": digest, "scope": cfg.max_flight_load_factor}
    if (output / "manifest.json").exists():
        existing = read_json(output / "manifest.json")
        if existing["identity"] == identity:
            return existing
        raise AnalyticsStale(f"{output} was built from other data. Use a new version folder.")

    flights = scan_flights(dataset)
    known = known_months(flights)
    base = build_base(flights, cfg)
    tables = {
        "dim_month": build_dim_month(known),
        "dim_airport": build_dim_airport(flights, airports_csv),
        "dim_carrier": build_dim_carrier(flights),
        "fact_route_carrier_month": base,
        "fact_route_month": build_route_month(base),
        "fact_carrier_month": build_carrier_month(base),
        "fact_airport_month": build_airport_month(base),
    }
    panel = cfg.output / "panels" / "route_carrier.parquet"
    validation = validate_tables(
        tables, dataset, cfg.max_flight_load_factor, panel if panel.exists() else None
    )

    stage = output.with_name(f"{output.name}.tmp-build")
    if stage.exists():
        shutil.rmtree(stage)
    sizes = {}
    for name, frame in tables.items():
        sizes[name] = {
            "rows": frame.height,
            "bytes": write_parquet_atomic(frame, stage / f"{name}.parquet", zstd_level=6),
            "columns": {column: str(dtype) for column, dtype in frame.schema.items()},
        }
    absent = sorted(month_label(index) for index in missing_months(known))
    manifest = {
        "identity": identity,
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git": git_state(),
        "first_month": month_label(min(known)),
        "last_month": month_label(max(known)),
        "absent_months": absent,
        "tables": sizes,
        "column_docs": COLUMN_DOCS,
    }
    write_json_atomic(stage / "manifest.json", manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    publish_directory(stage, output)
    write_json_atomic(
        report, {**validation, "tables": {name: size["rows"] for name, size in sizes.items()}}
    )
    return manifest
