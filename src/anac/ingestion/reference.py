"""ANAC's official aggregate (carrier x route x month), used to reconcile our monthly totals."""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl

METRICS = ("takeoffs", "seats", "rpk", "ask")


def _number(column: str) -> str:
    return f"try_cast(replace(nullif({column}, ''), ',', '.') AS DOUBLE)"


def reference_totals(path: Path) -> pl.DataFrame:
    """Totals per carrier and month. The first line of the file is a timestamp, not a header."""
    source = (
        f"read_csv('{path.as_posix()}', skip=1, header=true, delim=';', quote='\"', "
        "all_varchar=true, strict_mode=false)"
    )
    with duckdb.connect() as connection:
        connection.execute("SET memory_limit='2GB'")
        records = connection.execute(
            f"""
            SELECT EMPRESA_SIGLA, CAST(ANO AS INTEGER), CAST(MES AS INTEGER),
                   sum({_number("DECOLAGENS")}), sum({_number("ASSENTOS")}),
                   sum({_number("RPK")}), sum({_number("ASK")}),
                   sum({_number("PASSAGEIROS_PAGOS")})
            FROM {source} GROUP BY 1, 2, 3
            """
        ).fetchall()
    return pl.DataFrame(
        records,
        schema={
            "carrier": pl.String,
            "year": pl.Int32,
            "month": pl.Int32,
            "takeoffs": pl.Float64,
            "seats": pl.Float64,
            "rpk": pl.Float64,
            "ask": pl.Float64,
            "paid_pax": pl.Float64,
        },
        orient="row",
    )


def monthly_totals(flights: pl.LazyFrame) -> pl.DataFrame:
    """The same totals from published flights, including repeated legs as the source does."""
    return (
        flights.select(
            pl.col("sg_empresa_icao").alias("carrier"),
            pl.col("dt_referencia").dt.year().cast(pl.Int32).alias("year"),
            pl.col("dt_referencia").dt.month().cast(pl.Int32).alias("month"),
            pl.col("nr_decolagem").cast(pl.Float64).alias("takeoffs"),
            pl.col("nr_assentos_ofertados").cast(pl.Float64).alias("seats"),
            pl.col("nr_rpk").alias("rpk"),
            pl.col("nr_ask").alias("ask"),
            pl.col("nr_passag_pagos").cast(pl.Float64).alias("paid_pax"),
        )
        .group_by("carrier", "year", "month")
        .agg(pl.col(*METRICS, "paid_pax").sum())
        .collect(engine="streaming")
    )


def compare(ours: pl.DataFrame, reference: pl.DataFrame) -> pl.DataFrame:
    """One row per month and metric, comparing market totals and the worst carrier."""
    keys = ["carrier", "year", "month"]
    joined = ours.join(reference, on=keys, how="full", coalesce=True, suffix="_ref").fill_null(0.0)
    frames = []
    for metric in METRICS:
        frames.append(
            joined.group_by("year", "month")
            .agg(
                pl.col(metric).sum().alias("ours"),
                pl.col(f"{metric}_ref").sum().alias("reference"),
                (pl.col(metric) - pl.col(f"{metric}_ref")).abs().sum().alias("absolute_by_carrier"),
            )
            .with_columns(pl.lit(metric).alias("metric"))
        )
    result = pl.concat(frames).with_columns(
        (pl.col("ours") / pl.col("reference") - 1).alias("relative_difference"),
        (pl.col("absolute_by_carrier") / pl.col("reference")).alias("relative_by_carrier"),
    )
    return result.sort("year", "month", "metric")
