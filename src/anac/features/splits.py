"""Chronological splits by target month, purged by forecast distance."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import polars as pl

from anac.features.config import SealedTestError, TimeConfig, parse_month

TRAIN = "train"
PURGED = "purged"
VALIDATION = "validation"
TEST = "test"


def split_expr(time: TimeConfig) -> pl.Expr:
    """A training target must already be known when the first validation forecast is made.

    With distance k, the first validation target has its cutoff at validation_start - k, so
    training targets must not pass that month. Rows between the two are dropped, not reused.
    """
    target = pl.col("target_month")
    distance = pl.col("distance")
    return (
        pl.when(target >= time.test_start)
        .then(pl.lit(TEST))
        .when(target > time.validation_end)
        .then(pl.lit(PURGED))
        .when(target >= time.validation_start)
        .then(pl.lit(VALIDATION))
        .when(target <= time.validation_start - distance)
        .then(pl.lit(TRAIN))
        .otherwise(pl.lit(PURGED))
    )


def assign_split(frame: pl.DataFrame, time: TimeConfig) -> pl.DataFrame:
    return frame.with_columns(split_expr(time).alias("split"))


def withheld_from(time: TimeConfig, *, unseal_test: bool, reason: str | None = None) -> int:
    """First target month that must not be written. Unsealing requires a stated reason."""
    if not unseal_test:
        return time.test_start
    if not reason:
        raise SealedTestError("unsealing the test period requires a recorded reason")
    return time.test_end + 1


def exclude_unknown_targets(frame: pl.DataFrame, unknown_months: Sequence[str]) -> pl.DataFrame:
    """A missing source month is unknown, even for an otherwise eligible inactive route."""
    months = [parse_month(month) for month in unknown_months]
    return frame.filter(~pl.col("target_month").is_in(months)) if months else frame


def assert_no_sealed_targets(targets: pl.DataFrame, time: TimeConfig) -> None:
    if targets.is_empty():
        return
    if "target_date" in targets.columns:
        year, month = divmod(time.test_start, 12)
        sealed = pl.col("target_date") >= date(year, month + 1, 1)
    else:
        sealed = pl.col("target_month") >= time.test_start
    if targets.select(sealed.any()).item():
        raise SealedTestError("targets of the test period are present in this frame")
