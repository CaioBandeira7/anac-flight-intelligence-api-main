"""Analytical tables and their endpoints, built through the real pipeline on synthetic flights."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import polars as pl
import pytest
from fastapi.testclient import TestClient

from anac.analytics.build import AnalyticsStale, build_analytics
from anac.analytics.validate import AnalyticsValidationError, validate_tables
from anac.api.app import create_app
from anac.config import IngestionConfig
from anac.features.config import FeatureConfig, TimeConfig
from anac.ingestion.pipeline import run_ingestion
from tests.conftest import csv_line, write_csv


def leg(number: int, month: str, origin: str, destination: str, **overrides: str) -> str:
    year, month_number = month.split("-")
    day = f"{month}-{number % 28 + 1:02d}"
    values = {
        "id_basica": f"{number}.0",
        "nr_voo": str(1000 + number),
        "dt_referencia": day,
        "dt_partida_real": day,
        "dt_chegada_real": day,
        "nr_ano_referencia": year,
        "nr_mes_referencia": str(int(month_number)),
        "sg_icao_origem": origin,
        "sg_icao_destino": destination,
        "sg_iata_origem": {"SBGR": "GRU", "SBSP": "CGH"}.get(origin, ""),
        "sg_iata_destino": {"SBGR": "GRU", "SBSP": "CGH"}.get(destination, ""),
        **overrides,
    }
    return csv_line(**values)


LEGS = [
    # Directions differ on purpose: 75 paid passengers each way, but different counts of legs.
    leg(1, "2023-01", "SBGR", "SBSP"),
    leg(2, "2023-01", "SBGR", "SBSP"),
    leg(3, "2023-01", "SBSP", "SBGR", nr_passag_pagos="50.0", nr_rpk="17950.0"),
    leg(4, "2023-01", "SBGR", "SBSP", sg_empresa_icao="GLO", nm_empresa="GOL"),
    # Small route with a low load factor: an average of ratios would differ from the true ratio.
    leg(
        5,
        "2023-03",
        "SBGR",
        "SBSP",
        nr_passag_pagos="10.0",
        nr_assentos_ofertados="100.0",
        nr_rpk="3590.0",
        nr_ask="35900.0",
    ),
    leg(
        6,
        "2023-03",
        "SBGR",
        "SBSP",
        nr_passag_pagos="118.0",
        nr_passag_gratis="0.0",
        nr_rpk="42362.0",
    ),
    # A freighter: all takeoffs count, passenger measures do not.
    leg(
        7,
        "2023-03",
        "SBGR",
        "SBKP",
        nr_assentos_ofertados="0.0",
        nr_passag_pagos="0.0",
        nr_passag_gratis="0.0",
        nr_ask="0.0",
        nr_rpk="0.0",
        kg_carga_paga="5000.0",
    ),
    # The same leg under another id is a repeated record and must not count.
    leg(8, "2023-03", "SBSP", "SBKP"),
    leg(9, "2023-03", "SBSP", "SBKP"),
]


@pytest.fixture
def built(tmp_path: Path) -> tuple[FeatureConfig, Path]:
    # Legs 8 and 9 differ only by id once the flight number and day match.
    rows = [*LEGS[:7], leg(8, "2023-03", "SBSP", "SBKP", nr_voo="77", dt_referencia="2023-03-05", dt_partida_real="2023-03-05", dt_chegada_real="2023-03-05"),
            leg(9, "2023-03", "SBSP", "SBKP", nr_voo="77", dt_referencia="2023-03-05", dt_partida_real="2023-03-05", dt_chegada_real="2023-03-05")]  # fmt: skip
    ingestion = IngestionConfig(
        source_csv=write_csv(tmp_path / "s.csv", rows),
        full_output_root=tmp_path / "data",
        full_report_dir=tmp_path / "r",
        chunk_size_mb=1,
        memory_min_available_gb=0.0,
    )
    run_ingestion(ingestion, "full", confirm_full=True)
    cfg = FeatureConfig(
        processed=tmp_path / "data" / "processed",
        output=tmp_path / "features",
        reports=tmp_path / "b",
        time=TimeConfig(),
    )
    output = tmp_path / "analytics"
    build_analytics(cfg, output, tmp_path / "validation.json")
    return cfg, output


def table(output: Path, name: str) -> pl.DataFrame:
    return pl.read_parquet(output / f"{name}.parquet")


@pytest.fixture
def client(built: tuple[FeatureConfig, Path], tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path / "no_payloads", analytics_dir=built[1]))


def test_directions_stay_separate(built: tuple[FeatureConfig, Path]) -> None:
    route = table(built[1], "fact_route_month").filter(pl.col("month") == pl.date(2023, 1, 1))
    forward = route.filter((pl.col("origin") == "SBGR") & (pl.col("destination") == "SBSP"))
    backward = route.filter((pl.col("origin") == "SBSP") & (pl.col("destination") == "SBGR"))
    assert forward.get_column("paid_passengers").to_list() == [225]
    assert forward.get_column("carriers").to_list() == [2]
    assert backward.get_column("paid_passengers").to_list() == [50]


def test_load_factor_comes_from_sums_not_an_average_of_ratios(
    built: tuple[FeatureConfig, Path],
) -> None:
    row = table(built[1], "fact_route_month").filter(
        (pl.col("month") == pl.date(2023, 3, 1))
        & (pl.col("origin") == "SBGR")
        & (pl.col("destination") == "SBSP")
    )
    assert row.get_column("load_factor_paid")[0] == pytest.approx((10 + 118) / (100 + 118))


def test_freighters_count_as_takeoffs_only(built: tuple[FeatureConfig, Path]) -> None:
    row = (
        table(built[1], "fact_route_month")
        .filter(pl.col("destination") == "SBKP")
        .filter(pl.col("origin") == "SBGR")
    )
    assert row.get_column("all_takeoffs").to_list() == [1]
    assert row.get_column("passenger_takeoffs").to_list() == [0]
    assert row.get_column("seats").to_list() == [0]
    assert row.get_column("load_factor_paid").to_list() == [None]
    assert row.get_column("paid_cargo_kg").to_list() == [5000.0]


def test_repeated_records_do_not_count(built: tuple[FeatureConfig, Path]) -> None:
    row = table(built[1], "fact_route_month").filter(
        (pl.col("origin") == "SBSP") & (pl.col("destination") == "SBKP")
    )
    assert row.get_column("source_rows").to_list() == [1]
    assert row.get_column("paid_passengers").to_list() == [75]


def test_airport_movements_count_both_ends_of_each_flight(
    built: tuple[FeatureConfig, Path],
) -> None:
    airport = table(built[1], "fact_airport_month")
    base = table(built[1], "fact_route_carrier_month")
    assert airport.get_column("movements").sum() == 2 * base.get_column("all_takeoffs").sum()
    row = airport.filter((pl.col("airport") == "SBGR") & (pl.col("month") == pl.date(2023, 1, 1)))
    assert row.get_column("departures").to_list() == [3]
    assert row.get_column("arrivals").to_list() == [1]


def test_absent_month_is_flagged_and_never_a_zero_row(built: tuple[FeatureConfig, Path]) -> None:
    months = table(built[1], "dim_month")
    assert months.filter(~pl.col("has_data")).get_column("month_label").to_list() == ["2023-02"]
    february = pl.date(2023, 2, 1)
    assert table(built[1], "fact_route_month").filter(pl.col("month") == february).is_empty()


def test_dimension_joins_keep_totals(built: tuple[FeatureConfig, Path]) -> None:
    fact = table(built[1], "fact_route_carrier_month")
    joined = fact.join(table(built[1], "dim_carrier"), on="carrier", how="left").join(
        table(built[1], "dim_airport"),
        left_on="origin",
        right_on="airport",
        how="left",
        suffix="_origin",
    )
    assert joined.height == fact.height
    assert joined.get_column("paid_passengers").sum() == fact.get_column("paid_passengers").sum()


def test_measures_in_parquet_match_an_independent_read(built: tuple[FeatureConfig, Path]) -> None:
    path = (built[1] / "fact_route_month.parquet").as_posix()
    with duckdb.connect() as connection:
        total = connection.execute(
            f"SELECT sum(paid_passengers) FROM read_parquet('{path}')"
        ).fetchone()
    assert total is not None
    assert total[0] == 75 * 2 + 50 + 75 + 10 + 118 + 75


def _tampered(built: tuple[FeatureConfig, Path]) -> dict[str, pl.DataFrame]:
    return {
        name: table(built[1], name)
        for name in (
            "dim_month",
            "dim_airport",
            "dim_carrier",
            "fact_route_carrier_month",
            "fact_route_month",
            "fact_carrier_month",
            "fact_airport_month",
        )
    }


def test_validation_passes_on_good_tables(built: tuple[FeatureConfig, Path]) -> None:
    result = validate_tables(_tampered(built), built[0].processed / "flights", 1.5)
    assert result["status"] == "passed"


@pytest.mark.parametrize(
    ("name", "change", "message"),
    [
        (
            "fact_route_month",
            lambda f: f.with_columns(pl.col("paid_passengers") + 1),
            "route vs base",
        ),
        (
            "fact_route_carrier_month",
            lambda f: f.with_columns(pl.col("seats") * 2),
            "base vs source",
        ),
        (
            "fact_carrier_month",
            lambda f: f.with_columns(pl.col("all_takeoffs") + 1),
            "carrier vs base",
        ),
        (
            "fact_airport_month",
            lambda f: f.with_columns(pl.col("movements") + 1),
            "airport vs base",
        ),
        ("dim_airport", lambda f: pl.concat([f, f.head(1)]), "repeated key"),
        ("fact_route_month", lambda f: pl.concat([f, f.head(1)]), "repeated key"),
        ("dim_carrier", lambda f: f.tail(0), "join on carrier"),
        ("dim_month", lambda f: f.with_columns(pl.lit(True).alias("has_data")), "has_data"),
    ],
)
def test_validation_catches_broken_tables(
    built: tuple[FeatureConfig, Path], name: str, change: Any, message: str
) -> None:
    tables = _tampered(built)
    tables[name] = change(tables[name])
    with pytest.raises(AnalyticsValidationError, match=message):
        validate_tables(tables, built[0].processed / "flights", 1.5)


def test_rebuild_is_a_no_op_and_other_data_is_refused(
    built: tuple[FeatureConfig, Path], tmp_path: Path
) -> None:
    cfg, output = built
    before = (output / "fact_route_month.parquet").stat().st_mtime_ns
    build_analytics(cfg, output, tmp_path / "v.json")
    assert (output / "fact_route_month.parquet").stat().st_mtime_ns == before
    manifest = output / "manifest.json"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace('"dataset_digest": "', '"dataset_digest": "x'),
        encoding="utf-8",
    )
    with pytest.raises(AnalyticsStale):
        build_analytics(cfg, output, tmp_path / "v.json")


def test_route_filters_keep_direction_and_accept_iata(client: TestClient) -> None:
    forward = client.get(
        "/v2/analytics/routes", params={"origin": "GRU", "destination": "CGH", "to": "2023-01"}
    ).json()["data"]
    assert [(r["origin"], r["destination"], r["paid_passengers"]) for r in forward["routes"]] == [
        ("SBGR", "SBSP", 225)
    ]
    assert forward["routes"][0]["origin_iata"] == "GRU"
    backward = client.get(
        "/v2/analytics/routes", params={"origin": "CGH", "destination": "GRU", "to": "2023-01"}
    ).json()["data"]
    assert [r["paid_passengers"] for r in backward["routes"]] == [50]
    assert forward["period"] == {"from": "2023-01", "to": "2023-01"}


def test_series_marks_absent_months_and_true_zeros(client: TestClient) -> None:
    data = client.get(
        "/v2/analytics/routes/monthly", params={"origin": "SBSP", "destination": "SBGR"}
    ).json()["data"]
    assert data["absent_months"] == ["2023-02"]
    assert data["months_with_data"] == 2
    points = {point["month"]: point for point in data["points"]}
    assert set(points) == {"2023-01", "2023-03"}
    # March is known and this direction did not fly: a real zero, with no load factor.
    assert points["2023-03"]["paid_passengers"] == 0
    assert points["2023-03"]["load_factor_paid"] is None


def test_airport_endpoints(client: TestClient) -> None:
    ranking = client.get("/v2/analytics/airports").json()["data"]
    assert ranking["airports"][0]["airport"] == "SBGR"
    assert ranking["total"] == 3
    series = client.get("/v2/analytics/airports/monthly", params={"airport": "GRU"}).json()["data"]
    assert series["airport_found"] is True
    assert series["points"][0]["departures"] == 3


def test_unknown_airport_returns_nothing_rather_than_everything(client: TestClient) -> None:
    routes = client.get("/v2/analytics/routes", params={"origin": "ZZZZ"}).json()["data"]
    assert routes["routes"] == []
    assert routes["total"] == 0
    series = client.get("/v2/analytics/airports/monthly", params={"airport": "ZZZZ"}).json()["data"]
    assert series["airport_found"] is False
    assert series["points"] == []
    assert (
        client.get("/v2/analytics/routes/monthly", params={"origin": "ZZZZ"}).json()["data"][
            "points"
        ][0]["paid_passengers"]
        == 0
    )


@pytest.mark.parametrize(
    "params",
    [
        {"origin": "GRU' OR '1'='1"},
        {"origin": "SELECT"},
        {"from": "2023-13"},
        {"from": "2023"},
        {"from": "2023-03", "to": "2023-01"},
        {"limit": 100000},
        {"offset": -1},
    ],
)
def test_bad_filters_are_rejected(client: TestClient, params: dict[str, object]) -> None:
    assert client.get("/v2/analytics/routes", params=params).status_code == 422


def test_pagination_and_coverage(client: TestClient) -> None:
    page = client.get("/v2/analytics/routes", params={"limit": 1, "offset": 1}).json()["data"]
    assert len(page["routes"]) == 1
    assert page["total"] == 4
    coverage = client.get("/v2/analytics/coverage").json()["data"]
    assert coverage["absent_months"] == ["2023-02"]
    assert "passenger-km" in coverage["units"]["rpk"]
    assert coverage["tables"]["fact_route_month"]["rows"] > 0


def test_missing_tables_are_reported_not_invented(tmp_path: Path) -> None:
    app = TestClient(create_app(tmp_path, analytics_dir=tmp_path / "none"))
    assert app.get("/v2/analytics/routes").status_code == 503
    assert app.get("/v2/analytics/coverage").status_code == 503


def test_carrier_ranking_and_share_come_from_the_carrier_fact(
    client: TestClient, built: tuple[FeatureConfig, Path]
) -> None:
    facts = table(built[1], "fact_carrier_month")
    expected = facts.group_by("carrier").agg(pl.col("paid_passengers", "seats").sum())
    market = int(facts.get_column("paid_passengers").sum())
    data = client.get("/v2/analytics/carriers").json()["data"]
    assert data["market_paid_passengers"] == market
    assert data["total"] == expected.height
    assert data["absent_months"] == ["2023-02"]
    rows = {row["carrier"]: row for row in data["carriers"]}
    for item in expected.to_dicts():
        row = rows[item["carrier"]]
        assert row["paid_passengers"] == item["paid_passengers"]
        # Recomputed from sums, never averaged.
        assert row["load_factor_paid"] == pytest.approx(item["paid_passengers"] / item["seats"])
        assert row["market_share"] == pytest.approx(item["paid_passengers"] / market)
    assert [row["carrier"] for row in data["carriers"]] == ["AZU", "GLO"]
    assert sum(row["market_share"] for row in data["carriers"]) == pytest.approx(1)


def test_carrier_filter_keeps_the_market_denominator(client: TestClient) -> None:
    whole = client.get("/v2/analytics/carriers").json()["data"]
    only = client.get("/v2/analytics/carriers", params={"carrier": "glo"}).json()["data"]
    assert [row["carrier"] for row in only["carriers"]] == ["GLO"]
    assert only["market_paid_passengers"] == whole["market_paid_passengers"]
    assert only["carriers"][0]["market_share"] == whole["carriers"][1]["market_share"]
    unknown = client.get("/v2/analytics/carriers", params={"carrier": "ZZZ"}).json()["data"]
    assert unknown["carriers"] == []
    assert unknown["total"] == 0


def test_carrier_series_marks_absent_months_and_true_zeros(client: TestClient) -> None:
    data = client.get("/v2/analytics/carriers/monthly", params={"carrier": "GLO"}).json()["data"]
    assert data["carrier_found"] is True
    assert data["absent_months"] == ["2023-02"]
    points = {point["month"]: point for point in data["points"]}
    assert set(points) == {"2023-01", "2023-03"}
    january = points["2023-01"]
    assert january["market_share"] == pytest.approx(
        january["paid_passengers"] / january["market_paid_passengers"]
    )
    # GOL did not fly in March, a known month: a true zero with a zero share.
    assert points["2023-03"]["paid_passengers"] == 0
    assert points["2023-03"]["market_share"] == 0
    missing = client.get("/v2/analytics/carriers/monthly", params={"carrier": "ZZZ"}).json()
    assert missing["data"]["carrier_found"] is False
    assert missing["data"]["points"] == []


@pytest.mark.parametrize(
    "params", [{"carrier": "G' OR 1=1"}, {"carrier": "GOLX"}, {"from": "2023-03", "to": "2023-01"}]
)
def test_bad_carrier_filters_are_rejected(client: TestClient, params: dict[str, object]) -> None:
    assert client.get("/v2/analytics/carriers", params=params).status_code == 422
    assert (
        client.get(
            "/v2/analytics/carriers/monthly", params={"carrier": "GLO", **params}
        ).status_code
        == 422
    )


def test_catalogs_list_every_code_busiest_first(
    client: TestClient, built: tuple[FeatureConfig, Path]
) -> None:
    airports = client.get("/v2/analytics/airports/catalog").json()["data"]
    assert airports["recent_period"]["to"] == "2023-03"
    codes = [row["airport"] for row in airports["airports"]]
    assert set(codes) == set(table(built[1], "dim_airport").get_column("airport"))
    assert codes[0] == "SBGR"
    assert airports["airports"][0]["iata"] == "GRU"
    movements = [row["recent_movements"] for row in airports["airports"]]
    assert movements == sorted(movements, reverse=True)
    carriers = client.get("/v2/analytics/carriers/catalog").json()["data"]
    assert [row["carrier"] for row in carriers["carriers"]] == ["AZU", "GLO"]
    assert carriers["carriers"][0]["first_month"] == "2023-01"


def test_rankings_keep_their_order_across_runs(client: TestClient) -> None:
    # Regression: a join after sorting shuffled the rows from one run to the next.
    for _ in range(5):
        routes = client.get("/v2/analytics/routes").json()["data"]["routes"]
        passengers = [row["paid_passengers"] for row in routes]
        assert passengers == sorted(passengers, reverse=True)
        airports = client.get("/v2/analytics/airports").json()["data"]["airports"]
        movements = [row["movements"] for row in airports]
        assert movements == sorted(movements, reverse=True)
