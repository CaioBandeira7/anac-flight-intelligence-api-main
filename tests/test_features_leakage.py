"""These tests prove that information from after the cutoff cannot reach a feature."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pytest

from anac.evaluation.baselines import PREDICTIONS, evaluate_module
from anac.features.config import (
    FeatureConfig,
    LeakageError,
    SealedTestError,
    TimeConfig,
    month_index,
    parse_month,
)
from anac.features.contracts import MODULE_A, MODULE_B, MODULE_D, validate_features
from anac.features.daily import build_daily, daily_features_from_history, daily_targets
from anac.features.monthly import build_monthly, features_from_history, monthly_targets
from anac.features.panels import complete_airport_days, masked_dates
from anac.features.splits import (
    PURGED,
    TEST,
    TRAIN,
    VALIDATION,
    assert_no_sealed_targets,
    assign_split,
    withheld_from,
)

TIME = TimeConfig(first_target=parse_month("2022-01"))
CFG = FeatureConfig(processed=Path("x"), output=Path("x"), reports=Path("x"), time=TIME)
ORIGIN = parse_month("2023-06")
CUTOFF = ORIGIN - TIME.publication_lag_months


def route_panel(first: str = "2019-01", last: str = "2024-12") -> pl.DataFrame:
    rows = []
    units = [
        ("AZU", "SBGR", "SBRJ"),
        ("GLO", "SBGR", "SBRJ"),
        ("TAM", "SBBR", "SBSP"),
        ("GLO", "SBPA", "SBKP"),
    ]
    for m in range(parse_month(first), parse_month(last) + 1):
        for number, (carrier, origin, destination) in enumerate(units):
            seats = 10_000.0 + 500 * number + 20 * (m % 12)
            rows.append(
                {
                    "month_idx": m,
                    "carrier": carrier,
                    "origin": origin,
                    "destination": destination,
                    "pax": seats * (0.6 + 0.02 * (m % 7)),
                    "seats": seats,
                    "flights": 60.0 + number,
                    "km": 400.0 + number,
                    "is_international": False,
                }
            )
    return pl.DataFrame(rows, schema_overrides={"month_idx": pl.Int32})


def monthly(
    panel: pl.DataFrame, contract=MODULE_B, missing: set[int] | None = None
) -> pl.DataFrame:  # type: ignore[no-untyped-def]
    return features_from_history(
        panel.filter(pl.col("month_idx") <= CUTOFF),
        origin_month=ORIGIN,
        cutoff=CUTOFF,
        horizons=(1, 3, 6),
        contract=contract,
        missing=missing or set(),
        active_months=3,
        min_mean_seats=500,
    )


def airport_panel(first: date = date(2020, 1, 1), last: date = date(2024, 12, 31)) -> pl.DataFrame:
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    rows = [
        {
            "airport": airport,
            "date": day,
            "movements": 100 + 10 * index + day.weekday() * 3 + day.month,
        }
        for index, airport in enumerate(["SBGR", "SBSP", "SBBR"])
        for day in days
    ]
    return pl.DataFrame(rows, schema_overrides={"movements": pl.Int32, "date": pl.Date})


@pytest.mark.parametrize("contract", [MODULE_B, MODULE_D], ids=["b", "d"])
def test_changing_every_value_after_the_cutoff_changes_no_monthly_feature(contract) -> None:  # type: ignore[no-untyped-def]
    original = route_panel()
    future = pl.col("month_idx") > CUTOFF
    scrambled = original.with_columns(
        pl.when(future).then(pl.col("pax") * 97 + 13).otherwise(pl.col("pax")).alias("pax"),
        pl.when(future).then(pl.col("seats") * 3 + 1).otherwise(pl.col("seats")).alias("seats"),
        pl.when(future).then(pl.col("flights") + 500).otherwise(pl.col("flights")).alias("flights"),
    )
    assert monthly(original, contract).equals(monthly(scrambled, contract))


@pytest.mark.parametrize("contract", [MODULE_B, MODULE_D], ids=["b", "d"])
def test_deleting_every_row_after_the_cutoff_changes_no_monthly_feature(contract) -> None:  # type: ignore[no-untyped-def]
    original = route_panel()
    assert monthly(original, contract).equals(
        monthly(original.filter(pl.col("month_idx") <= CUTOFF), contract)
    )


def test_a_full_build_is_immune_to_future_changes_at_every_origin() -> None:
    """The real entry point cuts the panel per origin, so check it end to end."""
    original = route_panel()
    target = parse_month("2023-03")
    earliest_cut = target - 1 - TIME.publication_lag_months  # last cutoff among the horizons
    changed = original.with_columns(
        pl.when(pl.col("month_idx") > earliest_cut)
        .then(pl.col("pax") * 7)
        .otherwise(pl.col("pax"))
        .alias("pax")
    )
    build = lambda panel: build_monthly(  # noqa: E731
        panel, MODULE_B, CFG, horizons=(1,), min_mean_seats=500, missing=set(),
        first_target=target, last_target=target,
    )  # fmt: skip
    assert build(original).equals(build(changed))


def test_changing_every_value_after_the_cutoff_changes_no_daily_feature() -> None:
    original = airport_panel()
    cutoff = date(2023, 4, 30)
    scrambled = original.with_columns(
        pl.when(pl.col("date") > cutoff)
        .then(pl.col("movements") * 50)
        .otherwise(pl.col("movements"))
        .alias("movements")
    )

    def build(panel: pl.DataFrame) -> pl.DataFrame:
        return daily_features_from_history(
            panel.filter(pl.col("date") <= cutoff),
            origin_month=ORIGIN,
            cutoff=cutoff,
            horizons=(1, 3),
            distance_months={1: 3, 3: 5},
            top_airports=2,
        )

    assert build(original).equals(build(scrambled))


def test_baselines_inherit_the_guarantee() -> None:
    original = route_panel()
    changed = original.with_columns(
        pl.when(pl.col("month_idx") > CUTOFF).then(0.0).otherwise(pl.col("pax")).alias("pax")
    )
    assert PREDICTIONS["d"](monthly(original, MODULE_D)).equals(
        PREDICTIONS["d"](monthly(changed, MODULE_D))
    )


def test_history_past_the_cutoff_is_refused() -> None:
    with pytest.raises(LeakageError, match="after cutoff"):
        features_from_history(
            route_panel(),
            origin_month=ORIGIN,
            cutoff=CUTOFF,
            horizons=(1,),
            contract=MODULE_B,
            missing=set(),
            active_months=3,
            min_mean_seats=500,
        )
    with pytest.raises(LeakageError, match="after cutoff"):
        daily_features_from_history(
            airport_panel(),
            origin_month=ORIGIN,
            cutoff=date(2023, 4, 30),
            horizons=(1,),
            distance_months={1: 3},
            top_airports=2,
        )


def test_a_horizon_beyond_the_seasonal_lag_is_refused() -> None:
    with pytest.raises(LeakageError, match="lag of 12"):
        features_from_history(
            route_panel().filter(pl.col("month_idx") <= CUTOFF),
            origin_month=ORIGIN,
            cutoff=CUTOFF,
            horizons=(11,),
            contract=MODULE_B,
            missing=set(),
            active_months=3,
            min_mean_seats=500,
        )


def test_every_row_is_stamped_at_or_before_its_cutoff() -> None:
    features = monthly(route_panel())
    assert features.select((pl.col("_max_source_month") <= pl.col("cutoff_month")).all()).item()
    assert features.select((pl.col("target_month") - 12 <= pl.col("cutoff_month")).all()).item()
    forged = features.with_columns(pl.col("cutoff_month") - 1)
    with pytest.raises(LeakageError, match="after their cutoff"):
        validate_features(forged, MODULE_B)


def test_a_unit_that_only_starts_after_the_cutoff_is_not_eligible() -> None:
    panel = pl.concat(
        [
            route_panel(),
            route_panel(last="2023-12")
            .filter(pl.col("month_idx") > CUTOFF)
            .with_columns(pl.lit("NEW").alias("carrier")),
        ]
    )
    assert "NEW" not in monthly(panel).get_column("carrier").to_list()


def test_a_unit_that_stops_after_the_cutoff_stays_eligible() -> None:
    """Dropping it would mean choosing units by knowing the future."""
    stops = route_panel().filter((pl.col("carrier") != "TAM") | (pl.col("month_idx") <= CUTOFF))
    assert "TAM" in monthly(stops).get_column("carrier").to_list()


def test_undeclared_or_post_flight_columns_are_rejected() -> None:
    features = monthly(route_panel())
    with pytest.raises(ValueError, match="undeclared"):
        validate_features(features.with_columns(pl.lit(1.0).alias("pax_in_target_month")), MODULE_B)
    with pytest.raises(ValueError, match="missing"):
        validate_features(features.drop("hist_lf_3"), MODULE_B)
    with pytest.raises(ValueError, match="expected"):
        validate_features(features.with_columns(pl.col("hist_lf_3").cast(pl.Float32)), MODULE_B)


def test_outputs_match_their_contracts() -> None:
    validate_features(monthly(route_panel()), MODULE_B)
    validate_features(monthly(route_panel(), MODULE_D), MODULE_D)
    daily = build_daily(
        airport_panel(), _small_daily_cfg(), first_target=ORIGIN + 1, last_target=ORIGIN + 1
    )
    validate_features(daily, MODULE_A)
    assert daily.height > 0


def _small_daily_cfg() -> FeatureConfig:
    return FeatureConfig(
        processed=Path("x"),
        output=Path("x"),
        reports=Path("x"),
        time=TIME,
        a_horizons=(1, 3),
        a_top_airports=2,
    )


def test_a_missing_month_is_unknown_never_zero() -> None:
    gap = parse_month("2022-07")
    panel = route_panel().filter(pl.col("month_idx") != gap)
    features = monthly(panel, MODULE_D, missing={gap})
    # Target 2023-07 has its 12-month lag in the missing month.
    affected = features.filter(pl.col("target_month") == gap + 12)
    assert affected.height > 0
    assert affected.get_column("hist_pax_lag_12").null_count() == affected.height
    assert affected.get_column("hist_lf_lag_12").null_count() == affected.height
    assert features.get_column("hist_unknown_months_12").max() == 1
    # A month known to have data, where the unit did not fly, is a true zero.
    other = route_panel().filter(~((pl.col("month_idx") == gap) & (pl.col("carrier") == "TAM")))
    tam = monthly(other, MODULE_B).filter(
        (pl.col("carrier") == "TAM") & (pl.col("target_month") == gap + 12)
    )
    assert tam.get_column("hist_pax_lag_12").to_list() == [0.0]
    assert tam.get_column("hist_lf_lag_12").to_list() == [None]


def test_missing_month_adjusts_means_to_known_months() -> None:
    gap = CUTOFF - 1
    complete = route_panel()
    partial = complete.filter(pl.col("month_idx") != gap)
    features = monthly(partial, MODULE_D, missing={gap}).filter(
        (pl.col("origin") == "SBBR") & (pl.col("horizon") == 1)
    )
    rows = complete.filter(
        (pl.col("origin") == "SBBR") & pl.col("month_idx").is_in([CUTOFF, CUTOFF - 2])
    )
    assert features.get_column("hist_seats_mean_3")[0] == pytest.approx(
        rows.get_column("seats").sum() / 2
    )


def test_unknown_days_never_become_zero_or_targets() -> None:
    gap = {month_index(2022, 7)}
    days = [date(2022, 6, 1) + timedelta(days=i) for i in range(92)]
    counted = pl.DataFrame(
        {"airport": ["SBGR"] * 92, "date": days, "movements": [10] * 92},
        schema_overrides={"movements": pl.Int32, "date": pl.Date},
    ).filter(pl.col("date").dt.month() != 7)
    panel = complete_airport_days(counted, gap)
    inside = panel.filter(pl.col("date").dt.month() == 7)
    assert inside.get_column("movements").null_count() == inside.height
    # Flights crossing midnight may be lost, so the neighbouring days are also unknown.
    assert panel.filter(pl.col("date") == date(2022, 6, 30)).get_column("movements").to_list() == [
        None
    ]
    assert panel.filter(pl.col("date") == date(2022, 8, 1)).get_column("movements").to_list() == [
        None
    ]
    assert panel.filter(pl.col("date") == date(2022, 8, 2)).get_column("movements").to_list() == [
        10
    ]
    targets = daily_targets(panel, date(2030, 1, 1))
    assert targets.filter(pl.col("target_date").dt.month() == 7).is_empty()
    assert date(2022, 7, 15) in masked_dates(gap)


@pytest.mark.parametrize(
    ("target", "distance", "expected"),
    [
        ("2022-10", 3, TRAIN),
        ("2022-11", 3, PURGED),
        ("2022-08", 5, TRAIN),
        ("2022-09", 5, PURGED),
        ("2022-05", 8, TRAIN),
        ("2022-06", 8, PURGED),
        ("2023-01", 3, VALIDATION),
        ("2023-12", 8, VALIDATION),
        ("2024-01", 3, TEST),
    ],
)
def test_training_targets_are_purged_by_distance(target: str, distance: int, expected: str) -> None:
    frame = pl.DataFrame(
        {"target_month": [parse_month(target)], "distance": [distance]},
        schema={"target_month": pl.Int32, "distance": pl.Int32},
    )
    assert assign_split(frame, TIME).get_column("split")[0] == expected


def test_no_training_target_is_unknown_at_the_first_validation_origin() -> None:
    panel = route_panel()
    features = assign_split(
        build_monthly(
            panel, MODULE_B, CFG, horizons=(1, 3, 6), min_mean_seats=500, missing=set(),
            first_target=parse_month("2022-01"), last_target=parse_month("2023-12"),
        ),
        TIME,
    )  # fmt: skip
    train = features.filter(pl.col("split") == TRAIN)
    assert train.select(
        (pl.col("target_month") <= TIME.validation_start - pl.col("distance")).all()
    ).item()
    assert set(features.get_column("split").unique()) == {TRAIN, PURGED, VALIDATION}


def test_test_targets_are_sealed_by_default() -> None:
    panel = route_panel(last="2025-12")
    last = withheld_from(TIME, unseal_test=False) - 1
    targets = monthly_targets(panel, list(MODULE_B.unit), last)
    assert targets.get_column("target_month").max() == parse_month("2023-12")
    assert_no_sealed_targets(targets, TIME)
    with pytest.raises(SealedTestError):
        assert_no_sealed_targets(
            monthly_targets(panel, list(MODULE_B.unit), parse_month("2024-01")), TIME
        )
    with pytest.raises(SealedTestError, match="reason"):
        withheld_from(TIME, unseal_test=True)
    assert withheld_from(TIME, unseal_test=True, reason="final evaluation") == TIME.test_end + 1
    with pytest.raises(SealedTestError):
        evaluate_module(CFG, "b", split=TEST)
