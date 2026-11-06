"""Monthly features for modules B and D.

The rule is structural: `features_from_history` only receives rows at or before the cutoff and
refuses anything else. Targets are built elsewhere, so this code cannot see them.
"""

from __future__ import annotations

import polars as pl

from anac.features.calendar_br import monthly_calendar
from anac.features.config import FeatureConfig, LeakageError
from anac.features.contracts import ModuleContract, validate_features


def _sum_last(column: str, cutoff: int, months: int) -> pl.Expr:
    return pl.col(column).filter(pl.col("month_idx") > cutoff - months).sum()


def _safe_ratio(numerator: pl.Expr, denominator: pl.Expr) -> pl.Expr:
    return pl.when(denominator > 0).then(numerator / denominator).otherwise(None)


def _known_in_window(cutoff: int, months: int, missing: set[int]) -> int:
    return months - sum(1 for m in range(cutoff - months + 1, cutoff + 1) if m in missing)


def _unit_history(
    history: pl.DataFrame, keys: list[str], cutoff: int, missing: set[int]
) -> pl.DataFrame:
    known = {n: max(_known_in_window(cutoff, n, missing), 1) for n in (3, 6, 12)}
    # Fixed order: floating-point sums must not depend on how groups were partitioned.
    grouped = (
        history.sort([*keys, "month_idx"])
        .group_by([*keys, "month_idx"], maintain_order=True)
        .agg(
            pl.col("pax", "seats", "flights").sum(),
            pl.col("km").median(),
            pl.col("is_international").any(),
        )
    )
    monthly_lf = pl.col("pax") / pl.col("seats")
    in_12 = pl.col("month_idx") > cutoff - 12
    prior_3 = pl.col("month_idx").is_between(cutoff - 14, cutoff - 12)
    return grouped.group_by(keys, maintain_order=True).agg(
        (_sum_last("seats", cutoff, 3) / known[3]).alias("hist_seats_mean_3"),
        (_sum_last("seats", cutoff, 6) / known[6]).alias("hist_seats_mean_6"),
        (_sum_last("seats", cutoff, 12) / known[12]).alias("hist_seats_mean_12"),
        (_sum_last("pax", cutoff, 3) / known[3]).alias("hist_pax_mean_3"),
        (_sum_last("pax", cutoff, 6) / known[6]).alias("hist_pax_mean_6"),
        (_sum_last("pax", cutoff, 12) / known[12]).alias("hist_pax_mean_12"),
        (_sum_last("flights", cutoff, 3) / known[3]).alias("hist_flights_mean_3"),
        _safe_ratio(_sum_last("seats", cutoff, 3), _sum_last("flights", cutoff, 3)).alias(
            "hist_seats_per_flight_3"
        ),
        _safe_ratio(_sum_last("pax", cutoff, 3), _sum_last("seats", cutoff, 3)).alias("hist_lf_3"),
        _safe_ratio(_sum_last("pax", cutoff, 6), _sum_last("seats", cutoff, 6)).alias("hist_lf_6"),
        _safe_ratio(_sum_last("pax", cutoff, 12), _sum_last("seats", cutoff, 12)).alias(
            "hist_lf_12"
        ),
        monthly_lf.filter(in_12).std().alias("hist_lf_std_12"),
        _safe_ratio(_sum_last("pax", cutoff, 3), pl.col("pax").filter(prior_3).sum()).alias(
            "hist_yoy_pax"
        ),
        _safe_ratio(_sum_last("seats", cutoff, 3), pl.col("seats").filter(prior_3).sum()).alias(
            "hist_yoy_seats"
        ),
        pl.col("month_idx").filter(in_12).len().cast(pl.Int32).alias("hist_months_observed_12"),
        pl.col("month_idx").filter(pl.col("month_idx") > cutoff - 3).len().alias("_active_recent"),
        (cutoff - pl.col("month_idx").min()).cast(pl.Int32).alias("hist_months_since_first"),
        pl.col("km").median().alias("id_km"),
        pl.col("is_international").sort_by("month_idx").last().alias("id_is_international"),
    )


def _lag_values(
    history: pl.DataFrame, keys: list[str], month: int, lag: int, missing: set[int]
) -> pl.DataFrame:
    """Values of one past month, labelled for the given lag. Empty if that month is unknown."""
    grouped = (
        history.filter(pl.col("month_idx") == month)
        .group_by(keys, maintain_order=True)
        .agg(pl.col("pax", "seats").sum())
        .with_columns(_safe_ratio(pl.col("pax"), pl.col("seats")).alias("lf"))
    )
    return grouped.rename(
        {"pax": f"hist_pax_lag_{lag}", "seats": f"hist_seats_lag_{lag}", "lf": f"hist_lf_lag_{lag}"}
    ).with_columns(pl.lit(month in missing).alias(f"_lag_{lag}_unknown"))


def _attach_lag(
    frame: pl.DataFrame,
    values: pl.DataFrame,
    keys: list[str],
    lag: int,
    month: int,
    missing: set[int],
    first_known: int,
) -> pl.DataFrame:
    joined = frame.join(values.drop(f"_lag_{lag}_unknown"), on=keys, how="left")
    pax, seats = f"hist_pax_lag_{lag}", f"hist_seats_lag_{lag}"
    if month in missing or month < first_known:
        return joined.with_columns(
            pl.lit(None, dtype=pl.Float64).alias(pax), pl.lit(None, dtype=pl.Float64).alias(seats)
        )
    # The month is known, so a unit without rows did not fly: zero, never imputed.
    return joined.with_columns(pl.col(pax).fill_null(0.0), pl.col(seats).fill_null(0.0))


def _network_features(
    history: pl.DataFrame, cutoff: int, with_carrier: bool
) -> dict[str, pl.DataFrame]:
    recent = history.filter(pl.col("month_idx") > cutoff - 3).sort(
        "month_idx", "carrier", "origin", "destination"
    )
    lf = _safe_ratio(pl.col("pax").sum(), pl.col("seats").sum())
    frames = {
        "origin": recent.group_by("origin", maintain_order=True).agg(lf.alias("hist_origin_lf_3")),
        "destination": recent.group_by("destination", maintain_order=True).agg(
            lf.alias("hist_destination_lf_3")
        ),
        "route": recent.group_by("origin", "destination", maintain_order=True).agg(
            lf.alias("hist_route_lf_3"),
            pl.col("carrier").n_unique().cast(pl.Float64).alias("hist_carriers_on_route_3"),
            pl.col("seats").sum().alias("_route_seats_3"),
        ),
    }
    if with_carrier:
        frames["carrier"] = recent.group_by("carrier", maintain_order=True).agg(
            lf.alias("hist_carrier_lf_3")
        )
        frames["carrier_route"] = recent.group_by(
            "carrier", "origin", "destination", maintain_order=True
        ).agg(pl.col("seats").sum().alias("_unit_seats_3"))
    return frames


def features_from_history(
    history: pl.DataFrame,
    *,
    origin_month: int,
    cutoff: int,
    horizons: tuple[int, ...],
    contract: ModuleContract,
    missing: set[int],
    active_months: int,
    min_mean_seats: float,
) -> pl.DataFrame:
    """Features of every eligible unit for one forecast origin."""
    latest: int | None = history.select(pl.col("month_idx").max()).item()
    if latest is None:
        return pl.DataFrame(schema={spec.name: spec.dtype for spec in contract.features})
    if latest > cutoff:
        raise LeakageError(f"history reaches month {latest}, after cutoff {cutoff}")

    with_carrier = "carrier" in contract.unit
    keys = list(contract.unit)
    first_known: int = history.select(pl.col("month_idx").min()).item()
    stats = _unit_history(history, keys, cutoff, missing)
    # Eligibility is decided from the past alone. Filtering on the target month would leak.
    stats = stats.filter(
        (pl.col("hist_seats_mean_12") >= min_mean_seats)
        & (pl.col("hist_months_observed_12") > 0)
        & (pl.col("_active_recent") >= 1)
    )
    if active_months != 3:
        recent = history.filter(pl.col("month_idx") > cutoff - active_months).select(keys).unique()
        stats = stats.join(recent, on=keys, how="semi")
    # Network features read every unit, so the stamp is the latest month in the whole history.
    stats = stats.drop("_active_recent").with_columns(
        pl.lit(latest, dtype=pl.Int32).alias("_max_source_month")
    )
    stats = stats.with_columns(
        pl.lit(
            sum(1 for m in range(cutoff - 11, cutoff + 1) if m in missing), dtype=pl.Int32
        ).alias("hist_unknown_months_12")
    )

    network = _network_features(history, cutoff, with_carrier)
    enriched = stats.join(network["origin"], on="origin", how="left").join(
        network["destination"], on="destination", how="left"
    )
    route = network["route"]
    if with_carrier:
        enriched = (
            enriched.join(route, on=["origin", "destination"], how="left")
            .join(network["carrier"], on="carrier", how="left")
            .join(network["carrier_route"], on=["carrier", "origin", "destination"], how="left")
            .with_columns(
                _safe_ratio(pl.col("_unit_seats_3"), pl.col("_route_seats_3")).alias(
                    "hist_carrier_seat_share_3"
                )
            )
            .drop("_unit_seats_3", "_route_seats_3")
        )
    else:
        enriched = enriched.join(
            route.drop("hist_route_lf_3", "_route_seats_3"),
            on=["origin", "destination"],
            how="left",
        )

    parts = []
    for horizon in horizons:
        target = origin_month + horizon
        distance = target - cutoff
        if distance > 12:
            raise LeakageError(f"lag of 12 months would pass the cutoff at distance {distance}")
        frame = enriched.with_columns(
            pl.lit(origin_month, dtype=pl.Int32).alias("origin_month"),
            pl.lit(cutoff, dtype=pl.Int32).alias("cutoff_month"),
            pl.lit(target, dtype=pl.Int32).alias("target_month"),
            pl.lit(horizon, dtype=pl.Int32).alias("horizon"),
            pl.lit(distance, dtype=pl.Int32).alias("distance"),
        )
        for lag in (12, 24):
            month = target - lag
            values = _lag_values(history, keys, month, lag, missing)
            frame = _attach_lag(frame, values, keys, lag, month, missing, first_known)
        parts.append(frame)
    combined = pl.concat(parts)
    combined = combined.join(
        monthly_calendar(sorted({origin_month + h for h in horizons})),
        on="target_month",
        how="left",
    )
    return combined.select([pl.col(spec.name).cast(spec.dtype) for spec in contract.features]).sort(
        *contract.forecast_keys
    )


def build_monthly(
    panel: pl.DataFrame,
    contract: ModuleContract,
    cfg: FeatureConfig,
    *,
    horizons: tuple[int, ...],
    min_mean_seats: float,
    missing: set[int],
    first_target: int,
    last_target: int,
) -> pl.DataFrame:
    """Features for every target month in range, cutting the panel fresh for each origin."""
    lag = cfg.time.publication_lag_months
    origins = sorted(
        {
            target - horizon
            for target in range(first_target, last_target + 1)
            for horizon in horizons
        }
    )
    frames = []
    for origin in origins:
        cutoff = origin - lag
        # 40 months cover the 24-month lag at the longest distance. Older rows are not used.
        history = panel.filter(pl.col("month_idx").is_between(cutoff - 40, cutoff))
        selected = tuple(h for h in horizons if first_target <= origin + h <= last_target)
        frames.append(
            features_from_history(
                history,
                origin_month=origin,
                cutoff=cutoff,
                horizons=selected,
                contract=contract,
                missing=missing,
                active_months=cfg.active_months,
                min_mean_seats=min_mean_seats,
            )
        )
    result = pl.concat(frames).sort(*contract.forecast_keys)
    validate_features(result, contract)
    return result


def monthly_targets(panel: pl.DataFrame, keys: list[str], last_month: int) -> pl.DataFrame:
    """Observed values, kept apart from features. Anything from `last_month` on is withheld."""
    return (
        panel.filter(pl.col("month_idx") <= last_month)
        .sort([*keys, "month_idx"])
        .group_by([*keys, "month_idx"], maintain_order=True)
        .agg(pl.col("pax", "seats").sum())
        .with_columns(_safe_ratio(pl.col("pax"), pl.col("seats")).alias("load_factor"))
        .rename({"month_idx": "target_month"})
        .with_columns(pl.col("target_month").cast(pl.Int32))
        .sort(*keys, "target_month")
    )
