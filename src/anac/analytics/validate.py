"""Prove the tables agree with the source and with each other. Any failure stops publication.

Source totals come from DuckDB with the scope written in SQL, so a mistake in the Polars code cannot
confirm itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import polars as pl

_TOLERANCE = 1e-6


class AnalyticsValidationError(RuntimeError):
    """The tables disagree with the source or with each other."""


def _source_totals(dataset: Path, cap: float) -> pl.DataFrame:
    glob = (dataset / "*" / "*" / "*.parquet").as_posix()
    scope = (
        "NOT dq_no_takeoff AND nr_assentos_ofertados > 0 AND ds_grupo_di <> 'IMPRODUTIVO' "
        "AND NOT dq_zero_distance AND NOT dq_same_origin_destination "
        f"AND nr_passag_pagos IS NOT NULL AND load_factor_paid <= {float(cap)}"
    )
    with duckdb.connect() as connection:
        connection.execute("SET memory_limit='2GB'")
        connection.execute("SET preserve_insertion_order=false")
        records = connection.execute(
            f"""
            SELECT date_trunc('month', dt_referencia)::DATE,
              count(*), coalesce(sum(nr_decolagem), 0), coalesce(sum(nr_passag_pagos), 0),
              coalesce(sum(kg_carga_paga), 0), coalesce(sum(kg_correio), 0),
              coalesce(sum(nr_decolagem) FILTER (WHERE {scope}), 0),
              coalesce(sum(nr_passag_pagos) FILTER (WHERE {scope}), 0),
              coalesce(sum(nr_assentos_ofertados) FILTER (WHERE {scope}), 0),
              coalesce(sum(nr_rpk) FILTER (WHERE {scope}), 0),
              coalesce(sum(nr_ask) FILTER (WHERE {scope}), 0)
            FROM read_parquet('{glob}', hive_partitioning=false)
            WHERE NOT dq_duplicate_record GROUP BY 1
            """
        ).fetchall()
    names = [
        "month", "source_rows", "all_takeoffs", "all_paid_passengers", "paid_cargo_kg", "mail_kg",
        "passenger_takeoffs", "paid_passengers", "seats", "rpk", "ask",
    ]  # fmt: skip
    return pl.DataFrame(records, schema=names, orient="row", infer_schema_length=None).with_columns(
        pl.exclude("month").cast(pl.Float64)
    )


def _monthly(table: pl.DataFrame, measures: list[str]) -> pl.DataFrame:
    return table.group_by("month").agg(pl.col(measures).sum().cast(pl.Float64))


def _compare(
    left: pl.DataFrame, right: pl.DataFrame, measures: list[str], label: str, problems: list[str]
) -> None:
    joined = left.join(right, on="month", how="full", coalesce=True, suffix="_right").fill_null(0.0)
    for name in measures:
        gap = joined.select(
            (
                (pl.col(name) - pl.col(f"{name}_right")).abs() / pl.col(name).abs().clip(1.0, None)
            ).max()
        ).item()
        if gap is not None and gap > _TOLERANCE:
            problems.append(f"{label}: {name} differs by a relative {gap:.2e}")


def _unique_keys(frame: pl.DataFrame, keys: list[str], label: str, problems: list[str]) -> None:
    if frame.select(pl.struct(keys).is_duplicated().any()).item():
        problems.append(f"{label}: repeated key {keys}")
    if frame.select(pl.any_horizontal(pl.col(keys).is_null()).any()).item():
        problems.append(f"{label}: null in key {keys}")


def validate_tables(
    tables: dict[str, pl.DataFrame], dataset: Path, cap: float, panel_path: Path | None = None
) -> dict[str, Any]:
    problems: list[str] = []
    base = tables["fact_route_carrier_month"]
    route = tables["fact_route_month"]
    carrier = tables["fact_carrier_month"]
    airport = tables["fact_airport_month"]
    dim_month = tables["dim_month"]
    dim_airport = tables["dim_airport"]
    dim_carrier = tables["dim_carrier"]

    _unique_keys(base, ["month", "carrier", "origin", "destination"], "route carrier", problems)
    _unique_keys(route, ["month", "origin", "destination"], "route", problems)
    _unique_keys(carrier, ["month", "carrier"], "carrier", problems)
    _unique_keys(airport, ["month", "airport"], "airport", problems)
    _unique_keys(dim_month, ["month"], "dim month", problems)
    _unique_keys(dim_airport, ["airport"], "dim airport", problems)
    _unique_keys(dim_carrier, ["carrier"], "dim carrier", problems)

    measures = ["source_rows", "all_takeoffs", "all_paid_passengers", "paid_cargo_kg", "mail_kg",
                "passenger_takeoffs", "paid_passengers", "seats", "rpk", "ask"]  # fmt: skip
    source = _source_totals(dataset, cap)
    base_monthly = _monthly(base, measures)
    _compare(source, base_monthly, measures, "base vs source", problems)
    _compare(base_monthly, _monthly(route, measures), measures, "route vs base", problems)
    _compare(base_monthly, _monthly(carrier, measures), measures, "carrier vs base", problems)

    # Each takeoff counts once as a departure and once as a landing.
    airport_monthly = _monthly(
        airport,
        [
            "departures",
            "arrivals",
            "movements",
            "departing_paid_passengers",
            "arriving_paid_passengers",
        ],
    )
    expected = base_monthly.select(
        "month",
        pl.col("all_takeoffs").alias("departures"),
        pl.col("all_takeoffs").alias("arrivals"),
        (pl.col("all_takeoffs") * 2).alias("movements"),
        pl.col("paid_passengers").alias("departing_paid_passengers"),
        pl.col("paid_passengers").alias("arriving_paid_passengers"),
    )
    _compare(
        expected,
        airport_monthly,
        [
            "departures",
            "arrivals",
            "movements",
            "departing_paid_passengers",
            "arriving_paid_passengers",
        ],
        "airport vs base",
        problems,
    )

    # Joining a fact to its dimensions must neither add nor lose rows.
    joins = (
        (base, dim_carrier, "carrier", "carrier"),
        (base, dim_airport, "origin", "airport"),
        (base, dim_airport, "destination", "airport"),
        (airport, dim_airport, "airport", "airport"),
        (route, dim_month, "month", "month"),
    )
    for fact, dim, left, right in joins:
        joined = fact.join(dim.select(right), left_on=left, right_on=right, how="inner")
        if joined.height != fact.height:
            problems.append(f"join on {left}: {fact.height} rows became {joined.height}")

    with_data = set(dim_month.filter(pl.col("has_data")).get_column("month").to_list())
    in_facts = set(base.get_column("month").unique().to_list())
    if with_data != in_facts:
        problems.append("dim_month.has_data disagrees with the months in the facts")

    panel_check: dict[str, Any] = {"checked": False}
    if panel_path is not None:
        panel = pl.read_parquet(panel_path).with_columns(
            pl.date(pl.col("month_idx") // 12, pl.col("month_idx") % 12 + 1, 1).alias("month")
        )
        ours = _monthly(
            base.rename({"paid_passengers": "pax", "passenger_takeoffs": "flights"}),
            ["pax", "seats", "flights"],
        )
        theirs = _monthly(panel, ["pax", "seats", "flights"])
        before = len(problems)
        _compare(ours, theirs, ["pax", "seats", "flights"], "base vs feature panel", problems)
        panel_check = {
            "checked": True,
            "agrees": len(problems) == before,
            "rows_in_panel": panel.height,
        }

    if problems:
        raise AnalyticsValidationError("; ".join(problems))
    totals = base.select(pl.col(measures).sum().cast(pl.Float64)).row(0, named=True)
    return {
        "status": "passed",
        "months_compared_with_source": source.height,
        "tolerance_relative": _TOLERANCE,
        "totals": totals,
        "feature_panel": panel_check,
    }
