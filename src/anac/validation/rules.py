"""Type conversion and row validation.

Two severities, on purpose:

* **Reject**: the row cannot be placed or identified (no id, date or airport). It
  goes to quarantine with a reason.
* **Flag** (``dq_*``): the row is suspicious but real. It stays in the dataset with a
  boolean flag, so each downstream model chooses its own policy and the choice can
  be reversed without re-ingesting. Nothing is clipped or imputed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

import polars as pl

from anac.config import RulesConfig
from anac.ingestion.contract import (
    CHUNK_FLAGS,
    CHUNK_OUTPUT_COLUMNS,
    NONNEGATIVE_METRICS,
    SELECTED_COLUMNS,
    Kind,
)
from anac.ingestion.parsing import REJECT_SCHEMA

REASON_INVALID_ID: Final = "invalid_id_basica"
REASON_INVALID_DATE: Final = "invalid_reference_date"
REASON_DATE_RANGE: Final = "reference_date_out_of_range"
REASON_MISSING_AIRPORT: Final = "missing_airport"

_PLAIN_NUMBER: Final = r"^[+-]?\d+(\.\d+)?([eE][+-]?\d+)?$"
_COMMA_DECIMAL: Final = r"^[+-]?\d+,\d+([eE][+-]?\d+)?$"
_PT_BR_THOUSANDS: Final = r"^[+-]?\d{1,3}(\.\d{3})+,\d+$"
_ISO_DATE: Final = r"^\d{4}-\d{2}-\d{2}$"
_ICAO: Final = r"^[A-Z]{4}$"
_BRAZIL: Final = "BRASIL"
_DOMESTIC_NATURE: Final = "DOMÉSTICA"
_INTERNATIONAL_NATURE: Final = "INTERNACIONAL"

_TMP: Final = "__typed__"
_INVALID: Final = "__invalid__"
_REASON: Final = "__reject_reason__"


def decimal_expr(name: str) -> pl.Expr:
    """Parse a decimal written with a dot, a comma or pt-BR thousands separators.

    ``"1,45"`` -> 1.45, ``"2347.0"`` -> 2347.0, ``"1.234,56"`` -> 1234.56,
    ``"3,98e-05"`` -> 0.0000398. A lone ``"1.234"`` is read as 1.234 because the
    source writes plain decimals with a dot. ``Inf``, ``NaN`` and any other text
    become null, and the caller counts them as invalid.
    """
    text = pl.col(name)
    normalized = (
        pl.when(text.str.contains(_PT_BR_THOUSANDS))
        .then(text.str.replace_all(".", "", literal=True).str.replace(",", ".", literal=True))
        .when(text.str.contains(_COMMA_DECIMAL))
        .then(text.str.replace(",", ".", literal=True))
        .when(text.str.contains(_PLAIN_NUMBER))
        .then(text)
        .otherwise(None)
    )
    value = normalized.cast(pl.Float64, strict=False)
    return pl.when(value.is_finite()).then(value).otherwise(None)


def integer_expr(name: str, dtype: pl.DataType) -> pl.Expr:
    """Parse an integer stored as ``"75"`` or ``"75.0"``. ``"75.5"`` is invalid, not 75."""
    value = decimal_expr(name)
    return pl.when(value == value.floor()).then(value).otherwise(None).cast(dtype, strict=False)


def date_expr(name: str) -> pl.Expr:
    text = pl.col(name)
    return (
        pl.when(text.str.contains(_ISO_DATE))
        .then(text)
        .otherwise(None)
        .str.to_date("%Y-%m-%d", strict=False)
    )


def time_expr(name: str) -> pl.Expr:
    return pl.col(name).str.to_time("%H:%M:%S", strict=False)


def _typed_expr(name: str, kind: Kind) -> pl.Expr:
    match kind:
        case Kind.INT32:
            return integer_expr(name, pl.Int32())
        case Kind.INT64:
            return integer_expr(name, pl.Int64())
        case Kind.FLOAT:
            return decimal_expr(name)
        case Kind.DATE:
            return date_expr(name)
        case Kind.TIME:
            return time_expr(name)
        case Kind.STRING:
            return pl.col(name)


def normalize_strings(raw: pl.DataFrame) -> pl.DataFrame:
    """Trim whitespace and turn empty strings into null."""
    text_columns = [name for name, dtype in raw.schema.items() if dtype == pl.String]
    return raw.with_columns(
        pl.col(name).str.strip_chars().replace("", None).alias(name) for name in text_columns
    )


def _reject_reason_expr(rules: RulesConfig) -> pl.Expr:
    date_ = pl.col("dt_referencia")
    return (
        pl.when(pl.col("id_basica").is_null())
        .then(pl.lit(REASON_INVALID_ID))
        .when(date_.is_null())
        .then(pl.lit(REASON_INVALID_DATE))
        .when((date_ < rules.min_reference_date) | (date_ > rules.max_reference_date))
        .then(pl.lit(REASON_DATE_RANGE))
        .when(pl.col("sg_icao_origem").is_null() | pl.col("sg_icao_destino").is_null())
        .then(pl.lit(REASON_MISSING_AIRPORT))
        .otherwise(None)
    )


def _derived_exprs() -> list[pl.Expr]:
    seats = pl.col("nr_assentos_ofertados")
    excess = pl.col("kg_bagagem_excesso")
    origin_country = pl.col("nm_pais_origem")
    destination_country = pl.col("nm_pais_destino")
    return [
        pl.col("dt_partida_real").dt.combine(pl.col("hr_partida_real")).alias("partida_real_ts"),
        pl.col("dt_chegada_real").dt.combine(pl.col("hr_chegada_real")).alias("chegada_real_ts"),
        pl.concat_str(["sg_icao_origem", "sg_icao_destino"], separator="-").alias("route_icao"),
        # Geographic definition: a leg is international if it crosses the border.
        # Using the continent would mark GRU-EZE as domestic.
        pl.when(origin_country.is_null() | destination_country.is_null())
        .then(None)
        .otherwise((origin_country != _BRAZIL) | (destination_country != _BRAZIL))
        .alias("is_international"),
        # Deliberately unclipped: values above 1 are evidence, flagged separately.
        pl.when(seats > 0)
        .then(pl.col("nr_passag_pagos") / seats)
        .otherwise(None)
        .alias("load_factor_paid"),
        # Missing baggage stays null. It is not the same as "no excess baggage".
        pl.when(excess.is_null()).then(None).otherwise(excess > 0).alias("has_excess_baggage"),
    ]


def _flag_exprs(rules: RulesConfig) -> list[pl.Expr]:
    seats = pl.col("nr_assentos_ofertados")
    paid = pl.col("nr_passag_pagos")
    free = pl.col("nr_passag_gratis")
    km = pl.col("km_distancia")
    hours = pl.col("nr_horas_voadas")
    clock_hours = (
        pl.col("chegada_real_ts") - pl.col("partida_real_ts")
    ).dt.total_seconds() / 3600.0
    gap_days = (pl.col("dt_partida_real") - pl.col("dt_referencia")).dt.total_days().abs()
    tolerance = rules.ask_rpk_relative_tolerance

    def mismatch(observed: str, expected: pl.Expr) -> pl.Expr:
        difference = (pl.col(observed) - expected).abs()
        return (difference > 1.0) & (difference > tolerance * expected.abs())

    nature = pl.col("ds_natureza_etapa")
    international = pl.col("is_international")
    flags = {
        "dq_reference_period_mismatch": (
            pl.col("nr_ano_referencia") != pl.col("dt_referencia").dt.year()
        )
        | (pl.col("nr_mes_referencia") != pl.col("dt_referencia").dt.month()),
        "dq_missing_departure": pl.col("partida_real_ts").is_null(),
        "dq_departure_reference_gap": gap_days > rules.max_departure_reference_gap_days,
        "dq_arrival_before_departure": pl.col("chegada_real_ts") < pl.col("partida_real_ts"),
        "dq_implausible_flight_hours": hours > rules.max_flight_hours,
        "dq_hours_clock_mismatch": (clock_hours - hours).abs() > rules.hours_clock_tolerance,
        "dq_no_takeoff": pl.col("nr_decolagem") == 0,
        "dq_pax_exceed_seats": (seats > 0) & (paid + free > seats),
        "dq_pax_without_seats": (seats == 0) & (paid > 0),
        "dq_zero_distance": km == 0,
        "dq_same_origin_destination": pl.col("sg_icao_origem") == pl.col("sg_icao_destino"),
        "dq_negative_metric": pl.any_horizontal(pl.col(c) < 0 for c in NONNEGATIVE_METRICS),
        "dq_ask_mismatch": mismatch("nr_ask", seats * km),
        "dq_rpk_mismatch": mismatch("nr_rpk", paid * km),
        "dq_icao_nonstandard": ~(
            pl.col("sg_icao_origem").str.contains(_ICAO)
            & pl.col("sg_icao_destino").str.contains(_ICAO)
        ),
        "dq_nature_geography_mismatch": ((nature == _DOMESTIC_NATURE) & international)
        | ((nature == _INTERNATIONAL_NATURE) & ~international),
    }
    # A comparison against a missing value is "not flagged". Missingness has its own
    # null-rate metrics in the quality report.
    return [expr.fill_null(False).alias(name) for name, expr in flags.items()]


@dataclass(frozen=True)
class ValidatedChunk:
    valid: pl.DataFrame
    rejects: pl.DataFrame
    invalid_counts: dict[str, int] = field(default_factory=dict)
    """Per-column values that were present but could not be parsed (now null)."""


def validate_chunk(raw: pl.DataFrame, chunk_id: int, rules: RulesConfig) -> ValidatedChunk:
    """Convert types, split off rejects and add flags and derived columns."""
    normalized = normalize_strings(raw)
    typed_specs = [spec for spec in SELECTED_COLUMNS if spec.kind is not Kind.STRING]
    typed_names = [spec.name for spec in typed_specs]

    frame = normalized.with_columns(
        _typed_expr(spec.name, spec.kind).alias(_TMP + spec.name) for spec in typed_specs
    ).with_columns(
        (pl.col(name).is_not_null() & pl.col(_TMP + name).is_null()).alias(_INVALID + name)
        for name in typed_names
    )
    invalid_row = frame.select(
        [pl.col(_INVALID + name).sum().alias(name) for name in typed_names]
    ).row(0, named=True)
    invalid_counts = {name: int(count) for name, count in invalid_row.items() if count}

    frame = frame.with_columns(
        pl.any_horizontal(pl.col(_INVALID + name) for name in typed_names)
        .fill_null(False)
        .alias("dq_parse_error")
    )
    typed = frame.drop(typed_names).rename({_TMP + name: name for name in typed_names})
    typed = typed.with_columns(_reject_reason_expr(rules).alias(_REASON))

    reasons = typed.get_column(_REASON)
    rejected_mask = reasons.is_not_null()
    source_columns = [name for name in normalized.columns if name != "_source_line"]
    rejects = (
        normalized.with_columns(reasons)
        .filter(rejected_mask)
        .select(
            pl.lit(chunk_id, dtype=pl.Int32).alias("chunk_id"),
            pl.col("_source_line").alias("source_line"),
            pl.col(_REASON).alias("reason"),
            pl.struct(source_columns).struct.json_encode().alias("raw_record"),
        )
        .cast(REJECT_SCHEMA)
    )

    valid = (
        typed.filter(~rejected_mask)
        .with_columns(_derived_exprs())
        .with_columns(_flag_exprs(rules))
        .with_columns(pl.lit(chunk_id, dtype=pl.Int32).alias("_chunk_id"))
        .select(CHUNK_OUTPUT_COLUMNS)
    )
    return ValidatedChunk(valid, rejects, invalid_counts)


def count_flags(frame: pl.DataFrame, flags: tuple[str, ...] = CHUNK_FLAGS) -> dict[str, int]:
    row = frame.select(pl.col(name).sum() for name in flags).row(0, named=True)
    return {name: int(count or 0) for name, count in row.items()}
