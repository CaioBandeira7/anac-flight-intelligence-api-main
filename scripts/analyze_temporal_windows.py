"""Compare candidate temporal windows. Describes coverage only; no model is trained.

To protect the proposed final test (2024-2025), this script reads its identifiers and row
counts, never its targets. The audit already showed annual totals for those years, and that is
recorded in the feature engineering proposal.

    python scripts/analyze_temporal_windows.py [--data-root data] [--out reports/features]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

GAP_MONTHS = ((2015, 8), (2016, 2), (2018, 7), (2020, 8))
LAGS = (1, 2, 3, 6, 12, 24)


def rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    result = connection.execute(sql)
    names = [item[0] for item in result.description]
    return [dict(zip(names, record, strict=True)) for record in result.fetchall()]


def month_index(year: int, month: int) -> int:
    return year * 12 + month - 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("reports/features"))
    args = parser.parse_args()
    glob = (args.data_root / "processed/flights/*/*/*.parquet").as_posix()
    connection = duckdb.connect(":memory:")
    connection.execute("SET memory_limit='5GB'")
    connection.execute("SET preserve_insertion_order=false")
    connection.execute(
        f"""
        CREATE VIEW f AS
        SELECT * REPLACE (CAST(month AS INTEGER) AS month, CAST(year AS INTEGER) AS year)
        FROM read_parquet('{glob}', hive_partitioning=true)
        WHERE NOT dq_duplicate_record AND NOT dq_no_takeoff
        """
    )
    connection.execute(
        """
        CREATE TEMP TABLE route_carrier AS
        SELECT year, month, year * 12 + month - 1 AS m, sg_empresa_icao AS carrier, route_icao,
               sum(nr_assentos_ofertados) AS seats, count(*) AS flights
        FROM f WHERE nr_assentos_ofertados > 0 AND ds_grupo_di <> 'IMPRODUTIVO'
          AND NOT dq_zero_distance AND NOT dq_same_origin_destination
        GROUP BY ALL
        """
    )
    connection.execute(
        """
        CREATE TEMP TABLE route_only AS
        SELECT year, month, m, route_icao, sum(seats) AS seats, sum(flights) AS flights
        FROM route_carrier GROUP BY ALL
        """
    )
    connection.execute(
        """
        CREATE TEMP TABLE airport_day AS
        SELECT airport, day, year(day) AS year, month(day) AS month, sum(n) AS movements FROM (
          SELECT sg_icao_origem AS airport, dt_referencia AS day, count(*) AS n FROM f GROUP BY 1, 2
          UNION ALL
          SELECT sg_icao_destino, dt_referencia, count(*) FROM f GROUP BY 1, 2
        ) GROUP BY 1, 2
        """
    )
    windows = {
        "long_train_2003_2022": (2003, 2022),
        "recent_train_2013_2022": (2013, 2022),
        "validation_2023": (2023, 2023),
        "test_2024_2025": (2024, 2025),
    }
    out: dict[str, Any] = {"windows": {}}
    for name, (first, last) in windows.items():
        between = f"year BETWEEN {first} AND {last}"
        size = rows(
            connection,
            f"""
            SELECT count(*) AS route_carrier_months, count(DISTINCT carrier) AS carriers,
                   count(DISTINCT route_icao) AS routes, count(DISTINCT m) AS months, sum(flights) AS flights
            FROM route_carrier WHERE {between}
            """,
        )[0]
        size["route_months"] = rows(
            connection, f"SELECT count(*) AS n FROM route_only WHERE {between}"
        )[0]["n"]
        size["airport_days"] = rows(
            connection, f"SELECT count(*) AS n FROM airport_day WHERE {between}"
        )[0]["n"]
        size["airports"] = rows(
            connection, f"SELECT count(DISTINCT airport) AS n FROM airport_day WHERE {between}"
        )[0]["n"]
        size["expected_months"] = (last - first + 1) * 12
        size["gap_months_inside"] = sum(1 for year, _ in GAP_MONTHS if first <= year <= last)
        size["pandemic_flights_share_pct"] = rows(
            connection,
            f"""
            SELECT round(100.0 * sum(flights) FILTER (WHERE m BETWEEN {month_index(2020, 3)} AND {month_index(2021, 12)})
                   / sum(flights), 1) AS pct
            FROM route_carrier WHERE {between}
            """,
        )[0]["pct"]
        out["windows"][name] = size

    # How much of the later window does each training window recognise? Uses identifiers only.
    coverage = []
    for train_name, (first, last) in (
        ("long_train_2003_2022", (2003, 2022)),
        ("recent_train_2013_2022", (2013, 2022)),
    ):
        for target_name, (target_first, target_last) in (
            ("validation_2023", (2023, 2023)),
            ("test_2024_2025", (2024, 2025)),
        ):
            coverage.append(
                {
                    "train": train_name,
                    "target": target_name,
                    **rows(
                        connection,
                        f"""
                        WITH t AS (SELECT DISTINCT route_icao, carrier FROM route_carrier WHERE year BETWEEN {first} AND {last}),
                             tr AS (SELECT DISTINCT route_icao FROM t),
                             tc AS (SELECT DISTINCT carrier FROM t),
                             v AS (SELECT route_icao, carrier, flights FROM route_carrier
                                   WHERE year BETWEEN {target_first} AND {target_last})
                        SELECT
                          round(100.0 * sum(flights) FILTER (WHERE route_icao IN (SELECT route_icao FROM tr)) / sum(flights), 2)
                            AS pct_flights_known_route,
                          round(100.0 * sum(flights) FILTER (WHERE carrier IN (SELECT carrier FROM tc)) / sum(flights), 2)
                            AS pct_flights_known_carrier,
                          round(100.0 * sum(v.flights) FILTER (WHERE (route_icao, carrier) IN (SELECT route_icao, carrier FROM t)) / sum(v.flights), 2)
                            AS pct_flights_known_route_and_carrier
                        FROM v
                        """,
                    )[0],
                }
            )
    # The same recognition test on recent history alone: how old is usable knowledge?
    for first, last in ((2003, 2012), (2013, 2019), (2017, 2022), (2021, 2022)):
        coverage.append(
            {
                "train": f"history_{first}_{last}",
                "target": "validation_2023",
                **rows(
                    connection,
                    f"""
                    WITH t AS (SELECT DISTINCT route_icao, carrier FROM route_carrier WHERE year BETWEEN {first} AND {last}),
                         v AS (SELECT route_icao, carrier, flights FROM route_carrier WHERE year = 2023)
                    SELECT round(100.0 * sum(flights) FILTER (WHERE route_icao IN (SELECT route_icao FROM t)) / sum(flights), 2)
                             AS pct_flights_known_route,
                           round(100.0 * sum(flights) FILTER (WHERE carrier IN (SELECT carrier FROM t)) / sum(flights), 2)
                             AS pct_flights_known_carrier,
                           round(100.0 * sum(flights) FILTER (WHERE (route_icao, carrier) IN (SELECT route_icao, carrier FROM t)) / sum(flights), 2)
                             AS pct_flights_known_route_and_carrier
                    FROM v
                    """,
                )[0],
            }
        )
    out["recognition"] = coverage

    # How many months have a lag that falls on a missing month?
    affected = []
    for name, (first, last) in windows.items():
        for lag in LAGS:
            hits = sorted(
                {
                    (year, month)
                    for year in range(first, last + 1)
                    for month in range(1, 13)
                    if any(
                        month_index(year, month) - lag == month_index(*gap) for gap in GAP_MONTHS
                    )
                }
            )
            affected.append({"window": name, "lag_months": lag, "target_months_hit": len(hits)})
    out["target_months_with_lag_on_a_gap"] = affected

    # Sizes that drive the choice of unit. Training years only.
    out["airport_concentration_2013_2022"] = rows(
        connection,
        """
        WITH a AS (
          SELECT airport, sum(movements) AS movements, count(*) AS days FROM airport_day
          WHERE year BETWEEN 2013 AND 2022 GROUP BY 1
        ), o AS (
          SELECT *, row_number() OVER (ORDER BY movements DESC) AS position,
                 sum(movements) OVER (ORDER BY movements DESC) * 100.0 / sum(movements) OVER () AS cumulative
          FROM a
        )
        SELECT count(*) AS airports,
          round(max(cumulative) FILTER (WHERE position = 10), 1) AS pct_top_10,
          round(max(cumulative) FILTER (WHERE position = 20), 1) AS pct_top_20,
          round(max(cumulative) FILTER (WHERE position = 50), 1) AS pct_top_50,
          round(max(cumulative) FILTER (WHERE position = 100), 1) AS pct_top_100,
          count_if(days >= 3000) AS airports_active_3000_days
        FROM o
        """,
    )[0]
    out["route_carrier_depth_2013_2022"] = rows(
        connection,
        """
        WITH d AS (
          SELECT route_icao, carrier, count(*) AS months, sum(seats) AS seats FROM route_carrier
          WHERE year BETWEEN 2013 AND 2022 GROUP BY 1, 2
        )
        SELECT count(*) AS pairs,
          count_if(months >= 12) AS pairs_12_months, count_if(months >= 36) AS pairs_36_months,
          round(100.0 * sum(seats) FILTER (WHERE months >= 12) / sum(seats), 1) AS seats_pct_12_months,
          round(100.0 * sum(seats) FILTER (WHERE months >= 36) / sum(seats), 1) AS seats_pct_36_months
        FROM d
        """,
    )[0]
    out["route_carrier_months_by_size_2013_2022"] = rows(
        connection,
        """
        SELECT CASE WHEN seats < 500 THEN '1_under_500' WHEN seats < 2000 THEN '2_500_2000'
                    WHEN seats < 10000 THEN '3_2000_10000' ELSE '4_over_10000' END AS seats_in_month,
          count(*) AS route_carrier_months, round(100.0 * sum(seats) / sum(sum(seats)) OVER (), 1) AS pct_seats
        FROM route_carrier WHERE year BETWEEN 2013 AND 2022 GROUP BY 1 ORDER BY 1
        """,
    )
    out["hourly_sparsity_top_airport_2019"] = rows(
        connection,
        """
        WITH h AS (
          SELECT sg_icao_origem AS airport, dt_referencia AS day, hour(hr_partida_real) AS h, count(*) AS n
          FROM f WHERE year = 2019 AND hr_partida_real IS NOT NULL
            AND sg_icao_origem IN ('SBGR','SBSP','SBBR','SBKP','SBPA','SBRF','SBFZ','SBEG','SBUL','SBPJ')
          GROUP BY 1, 2, 3
        )
        SELECT airport, count(*) AS active_airport_hours, round(count(*) * 100.0 / (365 * 24), 1) AS pct_of_hours_active,
               round(avg(n), 1) AS mean_departures_when_active
        FROM h GROUP BY 1 ORDER BY 2 DESC
        """,
    )
    connection.close()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "temporal_windows.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
