"""Follow-up questions raised by the independent audit. Read-only.

python scripts/audit_drilldown.py [--data-root data] [--out reports/ingestion]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

GAP_MONTHS = ("2015-08", "2016-02", "2018-07", "2020-08")
# Source files are named like AZUAGO15.txt, so a missing month could hide under another date.
GAP_FILE_SUFFIXES = ("AGO15", "FEV16", "JUL18", "AGO20")


def rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    result = connection.execute(sql)
    names = [item[0] for item in result.description]
    return [dict(zip(names, record, strict=True)) for record in result.fetchall()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("reports/ingestion"))
    args = parser.parse_args()
    glob = (args.data_root / "processed/flights/*/*/*.parquet").as_posix()
    csv_path = (args.data_root / "raw/anac_brazil.csv").as_posix()

    connection = duckdb.connect(":memory:")
    connection.execute("SET memory_limit='5GB'")
    connection.execute(f"SET temp_directory='{(args.data_root / 'interim/audit_tmp').as_posix()}'")
    connection.execute("SET preserve_insertion_order=false")
    connection.execute(
        "CREATE VIEW f AS SELECT * REPLACE (CAST(month AS INTEGER) AS month, "
        f"CAST(year AS INTEGER) AS year) FROM read_parquet('{glob}', hive_partitioning=true)"
    )
    out: dict[str, Any] = {}

    suffix_filter = " OR ".join(f"upper(nm_arquivo) LIKE '%{item}%'" for item in GAP_FILE_SUFFIXES)
    gap_filter = ", ".join(f"'{item}'" for item in GAP_MONTHS)
    out["gap_months"] = {
        "rows_from_source_files_of_gap_months": rows(
            connection,
            f"SELECT nm_arquivo, year, month, count(*) AS rows FROM f WHERE {suffix_filter} "
            "GROUP BY ALL ORDER BY rows DESC LIMIT 20",
        ),
        "departures_dated_in_gap_months": rows(
            connection,
            f"""
            SELECT strftime(dt_partida_real, '%Y-%m') AS departure_month,
                   strftime(dt_referencia, '%Y-%m') AS reference_month, count(*) AS rows
            FROM f WHERE strftime(dt_partida_real, '%Y-%m') IN ({gap_filter})
            GROUP BY ALL ORDER BY rows DESC LIMIT 20
            """,
        ),
        "neighbour_month_rows": rows(
            connection,
            """
            SELECT year, month, count(*) AS rows, sum(nr_passag_pagos) AS paid_pax,
                   count(DISTINCT dt_referencia) AS days
            FROM f WHERE (year, month) IN ((2015,7),(2015,9),(2016,1),(2016,3),(2018,6),(2018,8),
                                           (2020,7),(2020,9),(2014,8),(2017,7),(2019,8))
            GROUP BY ALL ORDER BY 1, 2
            """,
        ),
    }

    out["carrier_month_gaps"] = rows(
        connection,
        """
        WITH cm AS (
            SELECT sg_empresa_icao AS carrier, year * 12 + month - 1 AS m, count(*) AS n
            FROM f GROUP BY 1, 2
        ), big AS (
            SELECT carrier, min(m) AS first_m, max(m) AS last_m, count(*) AS months, sum(n) AS rows
            FROM cm GROUP BY 1 HAVING sum(n) >= 100000
        )
        SELECT carrier, rows, months,
               (first_m // 12)::VARCHAR || '-' || lpad((first_m % 12 + 1)::VARCHAR, 2, '0') AS first_month,
               (last_m // 12)::VARCHAR || '-' || lpad((last_m % 12 + 1)::VARCHAR, 2, '0') AS last_month,
               last_m - first_m + 1 - months AS months_missing_inside_range
        FROM big ORDER BY rows DESC
        """,
    )

    out["null_versus_zero_by_carrier_nationality"] = rows(
        connection,
        """
        SELECT year, nm_pais = 'BRASIL' AS brazilian_carrier, count(*) AS rows,
          round(100.0 * count_if(kg_bagagem_excesso IS NULL) / count(*), 2) AS excess_null,
          round(100.0 * count_if(kg_bagagem_excesso = 0) / count(*), 2) AS excess_zero,
          round(100.0 * count_if(kg_bagagem_excesso > 0) / count(*), 2) AS excess_positive,
          round(100.0 * count_if(kg_bagagem_livre IS NULL) / count(*), 2) AS free_null,
          round(100.0 * count_if(kg_bagagem_livre = 0) / count(*), 2) AS free_zero,
          round(100.0 * count_if(lt_combustivel IS NULL) / count(*), 2) AS fuel_null,
          round(100.0 * count_if(lt_combustivel = 0) / count(*), 2) AS fuel_zero
        FROM f WHERE nr_assentos_ofertados > 0 AND year BETWEEN 2012 AND 2025
        GROUP BY ALL ORDER BY 1, 2
        """,
    )

    out["excess_positive_rate_major_carriers"] = rows(
        connection,
        """
        WITH major AS (
            SELECT sg_empresa_icao AS carrier FROM f WHERE year >= 2008
            GROUP BY 1 ORDER BY count(*) DESC LIMIT 7
        )
        SELECT year, sg_empresa_icao AS carrier, count(*) AS rows,
          round(100.0 * avg(has_excess_baggage::INT), 1) AS positive_pct,
          round(sum(kg_bagagem_excesso) / nullif(sum(nr_passag_pagos), 0), 3) AS excess_kg_per_pax,
          round(sum(kg_bagagem_livre) / nullif(sum(nr_passag_pagos), 0), 2) AS free_kg_per_pax
        FROM f WHERE sg_empresa_icao IN (SELECT carrier FROM major)
          AND nr_assentos_ofertados > 0 AND year >= 2008
        GROUP BY ALL ORDER BY 2, 1
        """,
    )
    out["who_reports_excess_2024"] = rows(
        connection,
        """
        SELECT sg_empresa_icao AS carrier, any_value(nm_pais) AS country, count(*) AS rows,
          round(100.0 * avg(has_excess_baggage::INT), 1) AS positive_pct,
          round(sum(kg_bagagem_livre) / nullif(sum(nr_passag_pagos), 0), 2) AS free_kg_per_pax
        FROM f WHERE year = 2024 AND nr_assentos_ofertados > 0
        GROUP BY 1 ORDER BY rows DESC LIMIT 15
        """,
    )

    metrics = [
        "lt_combustivel", "kg_payload", "km_distancia", "nr_passag_pagos", "nr_passag_gratis",
        "kg_bagagem_livre", "kg_bagagem_excesso", "kg_carga_paga", "kg_carga_gratis", "kg_correio",
        "nr_horas_voadas", "kg_peso", "nr_ask", "nr_atk", "nr_rpk", "nr_rtk",
        "nr_assentos_ofertados",
    ]  # fmt: skip
    negative = ", ".join(f"count_if({name} < 0) AS {name}" for name in metrics)
    out["negative_values_by_column"] = rows(connection, f"SELECT {negative} FROM f")[0]

    out["outliers"] = rows(
        connection,
        """
        SELECT count_if(dt_partida_real > DATE '2026-01-01') AS departures_after_2025,
          count_if(abs(date_diff('day', dt_referencia, dt_partida_real)) > 365) AS gap_over_1_year,
          count_if(load_factor_paid > 1) AS load_factor_over_1,
          count_if(load_factor_paid > 1.5) AS load_factor_over_1_5,
          count_if(nr_passag_pagos > 853) AS paid_pax_over_a380_max_cert,
          count_if(nr_assentos_ofertados > 853) AS seats_over_a380_max_cert,
          count_if(kg_bagagem_excesso > 10000) AS excess_over_10_tonnes
        FROM f
        """,
    )[0]

    out["model_ready_scope"] = rows(
        connection,
        """
        SELECT
          count(*) AS all_rows,
          count_if(NOT dq_duplicate_record AND NOT dq_no_takeoff) AS operated_unique,
          count_if(NOT dq_duplicate_record AND NOT dq_no_takeoff AND nr_assentos_ofertados > 0
                   AND ds_grupo_di <> 'IMPRODUTIVO') AS passenger_scope,
          count_if(NOT dq_duplicate_record AND NOT dq_no_takeoff AND nr_assentos_ofertados > 0
                   AND ds_grupo_di <> 'IMPRODUTIVO' AND NOT dq_pax_exceed_seats
                   AND NOT dq_zero_distance AND NOT dq_same_origin_destination
                   AND nr_passag_pagos IS NOT NULL) AS load_factor_scope,
          count_if(NOT dq_duplicate_record AND NOT dq_no_takeoff AND nr_assentos_ofertados > 0
                   AND NOT dq_missing_departure AND NOT dq_departure_reference_gap
                   AND ds_grupo_di <> 'IMPRODUTIVO') AS hourly_scope
        FROM f
        """,
    )[0]

    # Second independent read of the raw CSV for the questions Parquet cannot answer alone.
    source = (
        f"read_csv('{csv_path}', header=true, all_varchar=true, quote='\"', delim=',', "
        "parallel=true)"
    )
    out["raw_checks"] = rows(
        connection,
        f"""
        SELECT left(dt_referencia, 7) AS month, count(*) AS rows FROM {source}
        WHERE left(dt_referencia, 7) IN ({gap_filter})
        GROUP BY 1 ORDER BY 1
        """,
    )
    out["raw_arrival_times_not_valid_clock"] = rows(
        connection,
        f"""
        SELECT hr_chegada_real, nm_arquivo, count(*) AS rows FROM {source}
        WHERE hr_chegada_real IS NOT NULL
          AND NOT regexp_full_match(hr_chegada_real, '([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]')
        GROUP BY ALL ORDER BY rows DESC LIMIT 20
        """,
    )
    out["raw_invalid_arrival_times"] = rows(
        connection,
        """
        SELECT year, month, sg_empresa_icao AS carrier, nm_arquivo, count(*) AS rows
        FROM f WHERE dq_parse_error GROUP BY ALL ORDER BY rows DESC LIMIT 10
        """,
    )
    connection.close()

    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / "audit_drilldown.json"
    target.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
