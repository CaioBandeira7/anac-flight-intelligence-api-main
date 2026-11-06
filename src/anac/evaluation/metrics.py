"""Forecast metrics, with confidence intervals from a block bootstrap over target months."""

from __future__ import annotations

import math
import random

import polars as pl

BOOTSTRAP_DRAWS = 2000
SEED = 42


def _quantile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    position = share * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _interval(values: list[float]) -> list[float] | None:
    return [_quantile(values, 0.025), _quantile(values, 0.975)] if values else None


def ratio_with_interval(
    frame: pl.DataFrame, numerator: pl.Expr, denominator: pl.Expr, month: str = "target_month"
) -> dict[str, object]:
    """Point estimate and interval of sum(numerator) / sum(denominator), resampling months."""
    # Sorted, so the same seed resamples the same months on every run.
    months = (
        frame.group_by(month)
        .agg(numerator.sum().alias("n"), denominator.sum().alias("d"))
        .sort(month)
    )
    pairs = list(months.select("n", "d").iter_rows())
    total_d = sum(pair[1] for pair in pairs)
    if not total_d:
        return {"value": None, "ci95": None, "months": len(pairs)}
    value = sum(pair[0] for pair in pairs) / total_d
    rng = random.Random(SEED)
    draws = []
    for _ in range(BOOTSTRAP_DRAWS):
        sample = rng.choices(pairs, k=len(pairs))
        d = sum(pair[1] for pair in sample)
        if d:
            draws.append(sum(pair[0] for pair in sample) / d)
    return {"value": value, "ci95": _interval(draws), "months": len(pairs)}


def wape(frame: pl.DataFrame, actual: str, predicted: str) -> dict[str, object]:
    return ratio_with_interval(
        frame, (pl.col(predicted) - pl.col(actual)).abs(), pl.col(actual).abs()
    )


def bias(frame: pl.DataFrame, actual: str, predicted: str) -> dict[str, object]:
    """Positive means over-forecasting, relative to the actual total."""
    return ratio_with_interval(frame, pl.col(predicted) - pl.col(actual), pl.col(actual).abs())


def weighted_mae(
    frame: pl.DataFrame, actual: str, predicted: str, weight: str
) -> dict[str, object]:
    return ratio_with_interval(
        frame, (pl.col(predicted) - pl.col(actual)).abs() * pl.col(weight), pl.col(weight)
    )


def mean_absolute_scale(frame: pl.DataFrame, actual: str, naive: str) -> float | None:
    """Mean absolute error of the seasonal naive on training rows: the scale of MASE."""
    usable = frame.filter(pl.col(actual).is_not_null() & pl.col(naive).is_not_null())
    return (
        usable.select((pl.col(actual) - pl.col(naive)).abs().mean()).item()
        if usable.height
        else None
    )


def mase(
    frame: pl.DataFrame, actual: str, predicted: str, scale: float | None
) -> dict[str, object]:
    if not scale:
        return {"value": None, "ci95": None}
    # The denominator is summed per month, so it needs one scale per row, not one per month.
    per_row = pl.col(actual).is_not_null().cast(pl.Float64) * scale
    return ratio_with_interval(frame, (pl.col(predicted) - pl.col(actual)).abs(), per_row)


def rmsse(
    frame: pl.DataFrame, actual: str, predicted: str, scale_squared: float | None
) -> float | None:
    if not scale_squared or frame.is_empty():
        return None
    mse = frame.select(((pl.col(predicted) - pl.col(actual)) ** 2).mean()).item()
    return float(math.sqrt(mse / scale_squared))


def average_precision(labels: list[bool], scores: list[float]) -> float | None:
    """Area under the precision-recall curve, by average precision."""
    positives = sum(labels)
    if not positives:
        return None
    ordered = sorted(zip(scores, labels, strict=True), key=lambda pair: -pair[0])
    hits = 0
    total = 0.0
    for rank, (_, label) in enumerate(ordered, start=1):
        if label:
            hits += 1
            total += hits / rank
    return total / positives


def brier(labels: list[bool], probabilities: list[float]) -> float | None:
    if not labels:
        return None
    return sum((p - float(y)) ** 2 for y, p in zip(labels, probabilities, strict=True)) / len(
        labels
    )
