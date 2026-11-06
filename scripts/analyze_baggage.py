"""Observability and consistency of baggage reporting, by carrier and period. No model is trained.

Persistence checks stop at 2022 so that the proposed validation and test years stay out of them.

    python scripts/analyze_baggage.py [--data-root data] [--out reports/baggage]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

MAJOR = ("AZU", "GLO", "TAM", "ONE", "ACN", "PTB")


def rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    result = connection.execute(sql)
    names = [item[0] for item in result.description]
    return [dict(zip(names, record, strict=True)) for record in result.fetchall()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("reports/baggage"))
    args = parser.parse_args()
    glob = (args.data_root / "processed/flights/*/*/*.parquet").as_posix()
    connection = duckdb.connect(":memory:")
    connection.execute("SET memory_limit='5GB'")
    connection.execute("SET preserve_insertion_order=false")
    # Passenger flights that took place, without repeated records.
    connection.execute(
        f"""
        CREATE VIEW f AS
        SELECT * REPLACE (CAST(month AS INTEGER) AS month, CAST(year AS INTEGER) AS year),
               coalesce(nm_pais = 'BRASIL', false) AS brazilian
        FROM read_parquet('{glob}', hive_partitioning=true)
        WHERE NOT dq_duplicate_record AND NOT dq_no_takeoff AND nr_assentos_ofertados > 0
          AND ds_grupo_di <> 'IMPRODUTIVO'
        """
    )
    connection.execute(
        """
        CREATE TEMP TABLE cm AS
        SELECT sg_empresa_icao AS carrier, any_value(brazilian) AS brazilian, year, month,
               count(*) AS flights, sum(nr_passag_pagos) AS pax,
               count_if(kg_bagagem_excesso IS NULL) AS excess_null,
               count_if(kg_bagagem_excesso > 0) AS excess_positive,
               sum(kg_bagagem_excesso) AS excess_kg,
               count_if(kg_bagagem_livre > 0) AS free_positive,
               sum(kg_bagagem_livre) AS free_kg
        FROM f GROUP BY 1, 3, 4
        """
    )
    # Reporting state of one carrier in one month. This is what can actually be observed.
    connection.execute(
        """
        CREATE TEMP TABLE state AS
        SELECT *,
          excess_positive * 1.0 / flights AS positive_rate,
          CASE
            WHEN excess_null = flights THEN '1_null'
            WHEN free_positive = 0 AND excess_positive = 0 THEN '2_all_zero'
            WHEN excess_positive = 0 THEN '3_free_only'
            WHEN excess_positive * 1.0 / flights < 0.01 THEN '4_excess_under_1pct'
            ELSE '5_excess_reported'
          END AS state
        FROM cm
        """
    )
    out: dict[str, Any] = {}
    out["state_definition"] = {
        "1_null": "baggage is null on every flight of the month",
        "2_all_zero": "excess and free baggage are zero on every flight: not reported, or indistinguishable from it",
        "3_free_only": "free baggage is reported, but excess is zero on every flight",
        "4_excess_under_1pct": "excess is above zero on under 1% of flights",
        "5_excess_reported": "excess is above zero on at least 1% of flights",
    }
    out["pax_share_by_state_and_year"] = rows(
        connection,
        """
        SELECT year, brazilian, state, count(*) AS carrier_months, sum(pax) AS pax,
               round(100.0 * sum(pax) / sum(sum(pax)) OVER (PARTITION BY year), 2) AS pct_of_year_pax
        FROM state GROUP BY 1, 2, 3 ORDER BY 1, 2, 3
        """,
    )
    out["excess_observable_share_by_year"] = rows(
        connection,
        """
        SELECT year,
          round(100.0 * sum(pax) FILTER (WHERE state = '5_excess_reported') / sum(pax), 1) AS pct_pax_excess_reported,
          round(100.0 * sum(pax) FILTER (WHERE state IN ('3_free_only','4_excess_under_1pct','5_excess_reported')) / sum(pax), 1) AS pct_pax_free_reported,
          count(DISTINCT carrier) AS carriers,
          count(DISTINCT carrier) FILTER (WHERE state = '5_excess_reported') AS carriers_excess_reported
        FROM state GROUP BY 1 ORDER BY 1
        """,
    )
    # Regime switches: how often does a large carrier move on or off in one step?
    out["state_changes_by_carrier"] = rows(
        connection,
        """
        WITH big AS (SELECT carrier FROM state GROUP BY 1 HAVING sum(flights) >= 100000),
        s AS (
          SELECT carrier, year, month, state, positive_rate,
                 lag(state) OVER w AS previous_state, lag(positive_rate) OVER w AS previous_rate
          FROM state WHERE carrier IN (SELECT carrier FROM big)
          WINDOW w AS (PARTITION BY carrier ORDER BY year, month)
        )
        SELECT carrier, count(*) AS months,
          count_if(state = '5_excess_reported') AS months_reported,
          count_if((state = '5_excess_reported') <> (previous_state = '5_excess_reported')) AS on_off_switches,
          count_if(abs(positive_rate - previous_rate) >= 0.30) AS jumps_of_30_points,
          min(year * 100 + month) FILTER (WHERE state = '5_excess_reported') AS first_reported,
          max(year * 100 + month) FILTER (WHERE state = '5_excess_reported') AS last_reported
        FROM s GROUP BY 1 ORDER BY months_reported DESC
        """,
    )
    listing = ",".join(f"'{item}'" for item in MAJOR)
    out["monthly_series_major"] = rows(
        connection,
        f"""
        SELECT carrier, year, month, flights, pax, state,
          round(100.0 * positive_rate, 1) AS positive_pct,
          round(excess_kg / nullif(pax, 0), 3) AS excess_kg_per_pax,
          round(free_kg / nullif(pax, 0), 2) AS free_kg_per_pax
        FROM state WHERE carrier IN ({listing}) AND year >= 2012 ORDER BY 1, 2, 3
        """,
    )

    # Is the reported baggage part of the reported total weight? kg_peso appears to be 75 kg per
    # passenger plus baggage, cargo and mail. If that holds, baggage can be tested row by row.
    out["weight_identity_by_year"] = rows(
        connection,
        """
        WITH w AS (
          SELECT year, brazilian, kg_peso,
            (nr_passag_pagos + nr_passag_gratis) * 75 + coalesce(kg_carga_paga, 0)
              + coalesce(kg_carga_gratis, 0) + coalesce(kg_correio, 0) AS without_baggage,
            coalesce(kg_bagagem_livre, 0) + coalesce(kg_bagagem_excesso, 0) AS baggage,
            nr_passag_pagos + nr_passag_gratis AS all_pax
          FROM f WHERE kg_peso IS NOT NULL
        )
        SELECT year, brazilian, count(*) AS flights,
          round(100.0 * count_if(abs(kg_peso - without_baggage - baggage) <= 2) / count(*), 2) AS pct_identity_holds,
          round(100.0 * count_if(abs(kg_peso - without_baggage) <= 2) / count(*), 2) AS pct_weight_excludes_baggage,
          round(sum(kg_peso - without_baggage) / nullif(sum(all_pax), 0), 2) AS implied_baggage_kg_per_pax,
          round(sum(baggage) / nullif(sum(all_pax), 0), 2) AS reported_baggage_kg_per_pax
        FROM w GROUP BY 1, 2 ORDER BY 1, 2
        """,
    )

    out["positive_excess_values"] = rows(
        connection,
        f"""
        SELECT year, sg_empresa_icao AS carrier, count(*) AS positive_flights,
          quantile_cont(kg_bagagem_excesso, 0.5) AS median_kg, quantile_cont(kg_bagagem_excesso, 0.99) AS p99_kg,
          round(100.0 * count_if(kg_bagagem_excesso = 1) / count(*), 1) AS pct_exactly_1kg,
          round(100.0 * count_if(kg_bagagem_excesso % 5 = 0) / count(*), 1) AS pct_multiple_of_5
        FROM f WHERE kg_bagagem_excesso > 0 AND sg_empresa_icao IN ({listing}) AND year >= 2012
        GROUP BY 1, 2 ORDER BY 2, 1
        """,
    )

    # Persistence: does a route keep its level one year later? Stops at 2022 on purpose.
    connection.execute(
        """
        CREATE TEMP TABLE route_month AS
        SELECT sg_empresa_icao AS carrier, route_icao, year, month, sum(nr_passag_pagos) AS pax,
               sum(kg_bagagem_excesso) / sum(nr_passag_pagos) AS excess_per_pax,
               sum(kg_bagagem_livre) / sum(nr_passag_pagos) AS free_per_pax,
               (sum(kg_bagagem_excesso) + sum(kg_bagagem_livre)) / sum(nr_passag_pagos) AS total_per_pax,
               sum(kg_carga_paga) AS cargo_kg
        FROM f WHERE sg_empresa_icao IN ('AZU','GLO','TAM') AND year BETWEEN 2012 AND 2022 AND NOT is_international
        GROUP BY 1, 2, 3, 4 HAVING sum(nr_passag_pagos) >= 2000
        """
    )
    out["year_over_year_persistence_to_2022"] = rows(
        connection,
        """
        WITH p AS (
          SELECT a.carrier, a.year,
            a.excess_per_pax AS e1, b.excess_per_pax AS e0, a.free_per_pax AS f1, b.free_per_pax AS f0,
            a.total_per_pax AS t1, b.total_per_pax AS t0
          FROM route_month a JOIN route_month b
            ON a.carrier = b.carrier AND a.route_icao = b.route_icao AND a.month = b.month AND a.year = b.year + 1
        ), r AS (
          SELECT carrier, year,
            rank() OVER (PARTITION BY carrier, year ORDER BY e1) AS re1, rank() OVER (PARTITION BY carrier, year ORDER BY e0) AS re0,
            rank() OVER (PARTITION BY carrier, year ORDER BY f1) AS rf1, rank() OVER (PARTITION BY carrier, year ORDER BY f0) AS rf0,
            rank() OVER (PARTITION BY carrier, year ORDER BY t1) AS rt1, rank() OVER (PARTITION BY carrier, year ORDER BY t0) AS rt0
          FROM p
        )
        SELECT carrier, year, count(*) AS route_months,
          round(corr(re1, re0), 3) AS spearman_excess,
          round(corr(rf1, rf0), 3) AS spearman_free,
          round(corr(rt1, rt0), 3) AS spearman_total
        FROM r GROUP BY 1, 2 ORDER BY 1, 2
        """,
    )
    out["candidate_total_baggage_by_carrier_year"] = rows(
        connection,
        """
        SELECT sg_empresa_icao AS carrier, year, sum(nr_passag_pagos) AS pax,
          round(sum(kg_bagagem_livre) / sum(nr_passag_pagos), 2) AS free_kg_per_pax,
          round(sum(kg_bagagem_excesso) / sum(nr_passag_pagos), 3) AS excess_kg_per_pax,
          round(100.0 * count_if(kg_bagagem_livre = 0) / count(*), 2) AS pct_flights_free_zero
        FROM f WHERE sg_empresa_icao IN ('AZU','GLO','TAM','ONE','ACN','TIB') AND year >= 2012
        GROUP BY 1, 2 ORDER BY 1, 2
        """,
    )

    # Alternatives inside this dataset, on all operated flights including freighters.
    connection.execute(
        f"""
        CREATE VIEW ops AS
        SELECT * REPLACE (CAST(month AS INTEGER) AS month, CAST(year AS INTEGER) AS year),
               coalesce(nm_pais = 'BRASIL', false) AS brazilian
        FROM read_parquet('{glob}', hive_partitioning=true)
        WHERE NOT dq_duplicate_record AND NOT dq_no_takeoff
        """
    )
    out["candidate_cargo_by_year"] = rows(
        connection,
        """
        SELECT year, brazilian, count(*) AS flights,
          round(100.0 * count_if(kg_carga_paga IS NULL) / count(*), 3) AS cargo_null_pct,
          round(100.0 * count_if(kg_carga_paga > 0) / count(*), 1) AS flights_with_cargo_pct,
          round(sum(kg_carga_paga) / 1e6, 1) AS paid_cargo_thousand_tonnes,
          round(100.0 * sum(kg_carga_paga) FILTER (WHERE nr_assentos_ofertados = 0) / nullif(sum(kg_carga_paga), 0), 1) AS pct_on_freighters,
          count(DISTINCT sg_empresa_icao) FILTER (WHERE kg_carga_paga > 0) AS carriers_with_cargo,
          count(DISTINCT route_icao) FILTER (WHERE kg_carga_paga > 0) AS routes_with_cargo
        FROM ops WHERE year >= 2012 GROUP BY 1, 2 ORDER BY 1, 2
        """,
    )
    out["candidate_weight_load_factor_by_year"] = rows(
        connection,
        """
        SELECT year, brazilian,
          round(100.0 * count_if(nr_rtk IS NULL OR nr_atk IS NULL) / count(*), 3) AS null_pct,
          round(100.0 * count_if(nr_atk > 0) / count(*), 1) AS atk_positive_pct,
          round(100.0 * sum(nr_rtk) FILTER (WHERE nr_atk > 0) / sum(nr_atk) FILTER (WHERE nr_atk > 0), 1) AS rtk_over_atk_pct
        FROM ops WHERE year >= 2012 GROUP BY 1, 2 ORDER BY 1, 2
        """,
    )
    connection.close()

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "baggage_diagnostic.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
