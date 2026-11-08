"""Daily features for module A, under the same rule: history stops at the cutoff date."""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from anac.features.calendar_br import daily_calendar
from anac.features.config import FeatureConfig, LeakageError
from anac.features.contracts import MODULE_A, validate_features


def month_first_day(index: int) -> date:
    year, zero_month = divmod(index, 12)
    return date(year, zero_month + 1, 1)


def month_last_day(index: int) -> date:
    return month_first_day(index + 1) - timedelta(days=1)


def daily_features_from_history(
    history: pl.DataFrame,
    *,
    origin_month: int,
    cutoff: date,
    horizons: tuple[int, ...],
    distance_months: dict[int, int],
    top_airports: int,
) -> pl.DataFrame:
    """Features of the top airports for every day of each target month."""
    schema = {spec.name: spec.dtype for spec in MODULE_A.features}
    if history.is_empty():
        return pl.DataFrame(schema=schema)
    latest = history.get_column("date").max()
    if isinstance(latest, date) and latest > cutoff:
        raise LeakageError(f"history reaches {latest}, after cutoff {cutoff}")

    window_24m = cutoff - timedelta(days=730)
    ranking = (
        history.filter(pl.col("date") > window_24m)
        .group_by("airport")
        .agg(pl.col("movements").sum().alias("_volume"))
        .sort("_volume", "airport", descending=[True, False])
        .head(top_airports)
        .with_row_index("id_rank_24m", offset=1)
        .with_columns(pl.col("id_rank_24m").cast(pl.Int32))
        .drop("_volume")
    )
    selected = history.join(ranking, on="airport", how="semi").sort("airport", "date")

    def in_days(days: int) -> pl.Expr:
        return pl.col("date") > cutoff - timedelta(days=days)

    previous_56 = pl.col("date").is_between(
        cutoff - timedelta(days=364 + 55), cutoff - timedelta(days=364)
    )
    levels = (
        selected.group_by("airport", maintain_order=True)
        .agg(
            pl.col("movements").filter(in_days(28)).mean().cast(pl.Float64).alias("hist_level_28"),
            pl.col("movements").filter(in_days(56)).mean().cast(pl.Float64).alias("hist_level_56"),
            pl.col("movements").filter(previous_56).mean().cast(pl.Float64).alias("_previous_56"),
        )
        .with_columns(
            pl.when(pl.col("_previous_56") > 0)
            .then(pl.col("hist_level_56") / pl.col("_previous_56"))
            .otherwise(None)
            .alias("hist_yoy_56"),
            pl.lit(latest, dtype=pl.Date).alias("_max_source_date"),
        )
        .drop("_previous_56")
    )
    same_weekday = (
        selected.filter(in_days(56))
        .with_columns((pl.col("date").dt.weekday() - 1).cast(pl.Int8).alias("cal_day_of_week"))
        .group_by("airport", "cal_day_of_week", maintain_order=True)
        .agg(pl.col("movements").mean().cast(pl.Float64).alias("hist_same_dow_mean_8w"))
    )

    parts = []
    for horizon in horizons:
        target_month = origin_month + horizon
        first, last = month_first_day(target_month), month_last_day(target_month)
        if last - timedelta(days=364) > cutoff:
            raise LeakageError("the 364-day lag would pass the cutoff")
        calendar = daily_calendar(first, last)
        grid = ranking.join(calendar, how="cross").with_columns(
            pl.lit(origin_month, dtype=pl.Int32).alias("origin_month"),
            pl.lit(horizon, dtype=pl.Int32).alias("horizon"),
            pl.lit(cutoff, dtype=pl.Date).alias("cutoff_date"),
            pl.lit(target_month, dtype=pl.Int32).alias("target_month"),
            pl.lit(distance_months[horizon], dtype=pl.Int32).alias("distance"),
            (pl.col("target_date") - pl.lit(cutoff))
            .dt.total_days()
            .cast(pl.Int32)
            .alias("distance_days"),
        )
        for lag in (364, 728):
            values = selected.select(
                pl.col("airport"),
                (pl.col("date") + timedelta(days=lag)).alias("target_date"),
                pl.col("movements").cast(pl.Float64).alias(f"hist_lag_{lag}"),
            )
            grid = grid.join(values, on=["airport", "target_date"], how="left")
        parts.append(grid)
    combined = (
        pl.concat(parts)
        .join(levels, on="airport", how="left")
        .join(same_weekday, on=["airport", "cal_day_of_week"], how="left")
    )
    return combined.select([pl.col(spec.name).cast(spec.dtype) for spec in MODULE_A.features]).sort(
        *MODULE_A.forecast_keys
    )


def build_daily(
    panel: pl.DataFrame,
    cfg: FeatureConfig,
    *,
    first_target: int,
    last_target: int,
) -> pl.DataFrame:
    lag = cfg.time.publication_lag_months
    origins = sorted(
        {target - h for target in range(first_target, last_target + 1) for h in cfg.a_horizons}
    )
    frames = []
    for origin in origins:
        cutoff_month = origin - lag
        cutoff = month_last_day(cutoff_month)
        history = panel.filter(pl.col("date").is_between(cutoff - timedelta(days=1100), cutoff))
        selected = tuple(h for h in cfg.a_horizons if first_target <= origin + h <= last_target)
        frames.append(
            daily_features_from_history(
                history,
                origin_month=origin,
                cutoff=cutoff,
                horizons=selected,
                distance_months={h: h + lag for h in selected},
                top_airports=cfg.a_top_airports,
            )
        )
    result = pl.concat(frames).sort(*MODULE_A.forecast_keys)
    validate_features(result, MODULE_A)
    return result


def daily_targets(panel: pl.DataFrame, first_withheld: date) -> pl.DataFrame:
    """Known days only. Unknown days are never targets; days from `first_withheld` are withheld."""
    return (
        panel.filter((pl.col("date") < first_withheld) & pl.col("movements").is_not_null())
        .rename({"date": "target_date"})
        .sort("airport", "target_date")
    )
