"""Why does Gol's baggage series lose persistence in 2019-2022? Data up to 2022 only. Read-only.

python scripts/investigate_gol_baggage.py [--data-root data] [--out reports/baggage]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

CARRIERS = "('AZU','GLO','TAM')"


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
    connection.execute("SET memory_limit='3GB'")
    connection.execute("SET preserve_insertion_order=false")
    connection.execute(
        f"""
        CREATE VIEW f AS
        SELECT * REPLACE (CAST(month AS INTEGER) AS month, CAST(year AS INTEGER) AS year),
               coalesce(kg_bagagem_livre, 0) + coalesce(kg_bagagem_excesso, 0) AS bag
        FROM read_parquet('{glob}', hive_partitioning=true)
        WHERE NOT dq_duplicate_record AND NOT dq_no_takeoff AND nr_assentos_ofertados > 0
          AND ds_grupo_di <> 'IMPRODUTIVO' AND year BETWEEN 2015 AND 2022
          AND sg_empresa_icao IN {CARRIERS} AND NOT is_international
        """
    )
    out: dict[str, Any] = {"scope": "domestic passenger flights of AZU, GLO and TAM, 2015-2022"}
    out["monthly"] = rows(
        connection,
        """
        SELECT sg_empresa_icao AS carrier, year, month, count(*) AS flights,
          round(sum(bag) / sum(nr_passag_pagos), 3) AS bag_per_pax,
          round(100.0 * count_if(bag = 0 AND nr_passag_pagos > 0) / count(*), 2) AS pct_flights_zero_bag,
          round(quantile_cont(bag / nullif(nr_passag_pagos, 0), 0.5), 2) AS median_flight_bag_per_pax,
          round(quantile_cont(bag / nullif(nr_passag_pagos, 0), 0.9)
                - quantile_cont(bag / nullif(nr_passag_pagos, 0), 0.1), 2) AS p90_p10_spread,
          round(100.0 * count_if(bag % 10 = 0) / count(*), 1) AS pct_bag_multiple_of_10
        FROM f GROUP BY 1, 2, 3 ORDER BY 1, 2, 3
        """,
    )
    # Share of variance between routes: if routes stop differing, the signal is gone.
    out["route_dispersion_by_year"] = rows(
        connection,
        """
        WITH r AS (
          SELECT sg_empresa_icao AS carrier, year, route_icao, sum(bag) / sum(nr_passag_pagos) AS v, sum(nr_passag_pagos) AS pax
          FROM f GROUP BY 1, 2, 3 HAVING sum(nr_passag_pagos) >= 20000
        )
        SELECT carrier, year, count(*) AS routes, round(avg(v), 2) AS mean, round(stddev(v), 2) AS between_route_std,
               round(quantile_cont(v, 0.1), 2) AS p10, round(quantile_cont(v, 0.9), 2) AS p90
        FROM r GROUP BY 1, 2 ORDER BY 1, 2
        """,
    )
    # Persistence within a stable block: adjacent months, not the same month a year earlier.
    out["month_to_month_route_persistence"] = rows(
        connection,
        """
        WITH rm AS (
          SELECT sg_empresa_icao AS carrier, route_icao, year * 12 + month AS m, year,
                 sum(bag) / sum(nr_passag_pagos) AS v
          FROM f GROUP BY 1, 2, 3, 4 HAVING sum(nr_passag_pagos) >= 2000
        ), p AS (
          SELECT a.carrier, a.year, a.v AS v1, b.v AS v0
          FROM rm a JOIN rm b ON a.carrier = b.carrier AND a.route_icao = b.route_icao AND a.m = b.m + 1
        ), r AS (
          SELECT carrier, year, rank() OVER (PARTITION BY carrier, year ORDER BY v1) AS r1,
                 rank() OVER (PARTITION BY carrier, year ORDER BY v0) AS r0 FROM p
        )
        SELECT carrier, year, count(*) AS pairs, round(corr(r1, r0), 3) AS spearman FROM r GROUP BY 1, 2 ORDER BY 1, 2
        """,
    )
    # Does a level shift between a pair of years explain low year-over-year rank correlation?
    out["gol_flights_by_source_file_month"] = rows(
        connection,
        """
        SELECT year, month, count(DISTINCT nm_arquivo) AS files, any_value(nm_arquivo) AS file_example,
               round(100.0 * count_if(nm_arquivo IS NULL) / count(*), 1) AS pct_no_file,
               count(DISTINCT id_arquivo) AS file_ids
        FROM f WHERE sg_empresa_icao = 'GLO' AND year BETWEEN 2018 AND 2022 GROUP BY 1, 2 ORDER BY 1, 2
        """,
    )
    out["gol_weight_composition"] = rows(
        connection,
        """
        SELECT year, round(avg(kg_peso / nullif(nr_passag_pagos + nr_passag_gratis, 0)), 2) AS weight_per_pax,
          round(sum(kg_carga_paga + kg_carga_gratis + kg_correio) / sum(nr_passag_pagos), 2) AS cargo_per_pax,
          round(sum(kg_bagagem_livre) / sum(nr_passag_pagos), 2) AS free_per_pax,
          round(sum(kg_bagagem_excesso) / sum(nr_passag_pagos), 3) AS excess_per_pax
        FROM f WHERE sg_empresa_icao = 'GLO' GROUP BY 1 ORDER BY 1
        """,
    )
    connection.close()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "gol_investigation.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
