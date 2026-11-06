"""Independent audit of the published Parquet files.

Shares no parsing or validation code with the pipeline. Uses DuckDB for everything and
reconciles against a separate read of the raw CSV, so a pipeline bug cannot confirm itself.

    python scripts/audit_processed.py [--data-root data] [--out reports/ingestion]
"""

from __future__ import annotations

import argparse
import itertools
import json
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import duckdb

Row = dict[str, Any]


def rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[Row]:
    result = connection.execute(sql)
    names = [item[0] for item in result.description]
    return [dict(zip(names, record, strict=True)) for record in result.fetchall()]


def one(connection: duckdb.DuckDBPyConnection, sql: str) -> Row:
    return rows(connection, sql)[0]


def count_physical_lines(path: Path) -> int:
    """Newlines minus the header: the plainest possible count of the source."""
    total = 0
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            total += block.count(b"\n")
    return total - 1


def raw_by_year(connection: duckdb.DuckDBPyConnection, csv_path: Path) -> list[Row]:
    source = (
        f"read_csv('{csv_path.as_posix()}', header=true, all_varchar=true, quote='\"', "
        "delim=',', parallel=true)"
    )
    return rows(
        connection,
        f"""
        SELECT left(dt_referencia, 4) AS year,
               count(*) AS rows,
               sum(try_cast(nr_passag_pagos AS DOUBLE)) AS paid_passengers,
               sum(try_cast(nr_assentos_ofertados AS DOUBLE)) AS seats,
               sum(try_cast(nr_decolagem AS DOUBLE)) AS takeoffs,
               sum(try_cast(km_distancia AS DOUBLE)) AS km,
               sum(try_cast(replace(nr_horas_voadas, ',', '.') AS DOUBLE)) AS hours
        FROM {source}
        GROUP BY 1 ORDER BY 1
        """,
    )


def structural(connection: duckdb.DuckDBPyConnection, glob: str, flights: Path) -> Row:
    schema_variants = one(
        connection,
        f"""
        WITH per_file AS (
            SELECT file_name, md5(string_agg(name || ':' || coalesce(type, ''), ',' ORDER BY name))
                   AS signature
            FROM parquet_schema('{glob}') GROUP BY file_name
        )
        SELECT count(*) AS files, count(DISTINCT signature) AS schema_variants FROM per_file
        """,
    )
    metadata_rows = one(
        connection,
        f"SELECT sum(num_rows) AS rows FROM parquet_file_metadata('{glob}')",
    )
    return {
        **schema_variants,
        "rows_from_parquet_footers": metadata_rows["rows"],
        "temporary_leftovers": sum(1 for _ in flights.rglob("*.tmp-*")),
        "files_on_disk": sum(1 for _ in flights.rglob("*.parquet")),
        "bytes_on_disk": sum(path.stat().st_size for path in flights.rglob("*.parquet")),
    }


def temporal(connection: duckdb.DuckDBPyConnection) -> Row:
    months = rows(
        connection,
        """
        SELECT year, month, count(*) AS rows, sum(nr_decolagem) AS takeoffs,
               sum(nr_passag_pagos) AS paid_passengers,
               count(DISTINCT sg_empresa_icao) AS carriers,
               count(DISTINCT dt_referencia) AS distinct_days,
               min(dt_referencia) AS min_date, max(dt_referencia) AS max_date
        FROM f GROUP BY 1, 2 ORDER BY 1, 2
        """,
    )
    present = {(row["year"], row["month"]) for row in months}
    first, last = (months[0]["year"], months[0]["month"]), (months[-1]["year"], months[-1]["month"])
    gaps = []
    year, month = first
    while (year, month) <= last:
        if (year, month) not in present:
            gaps.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    swings = []
    for previous, current in itertools.pairwise(months):
        change = current["rows"] / previous["rows"] - 1
        if abs(change) > 0.4:
            swings.append(
                {
                    "month": f"{current['year']:04d}-{current['month']:02d}",
                    "previous_rows": previous["rows"],
                    "rows": current["rows"],
                    "change": round(change, 3),
                    "carriers": current["carriers"],
                }
            )
    partition = one(
        connection,
        """
        SELECT count_if(year <> year(dt_referencia) OR month <> month(dt_referencia)) AS wrong,
               count_if(year(dt_referencia) <> nr_ano_referencia
                        OR month(dt_referencia) <> nr_mes_referencia) AS column_disagrees,
               min(dt_referencia) AS min_date, max(dt_referencia) AS max_date,
               min(partida_real_ts) AS min_departure, max(partida_real_ts) AS max_departure,
               min(chegada_real_ts) AS min_arrival, max(chegada_real_ts) AS max_arrival
        FROM f
        """,
    )
    return {
        "months": months,
        "gaps": gaps,
        "large_month_swings": swings,
        "partition_checks": partition,
        "months_with_incomplete_days": [
            f"{row['year']:04d}-{row['month']:02d} ({row['distinct_days']} days)"
            for row in months
            if row["distinct_days"] < 28
        ],
    }


def duplicates(connection: duckdb.DuckDBPyConnection) -> Row:
    ids = one(
        connection,
        """
        SELECT count(*) AS rows, count(DISTINCT id_basica) AS distinct_ids,
               count(*) - count(DISTINCT id_basica) AS repeated_ids
        FROM f
        """,
    )
    by_year = rows(
        connection,
        """
        SELECT year, count_if(dq_duplicate_record) AS flagged, count(*) AS rows,
               round(100.0 * count_if(dq_duplicate_record) / count(*), 3) AS pct,
               sum(nr_passag_pagos) FILTER (WHERE dq_duplicate_record) AS paid_pax_in_flagged
        FROM f GROUP BY 1 ORDER BY 1
        """,
    )
    # Recomputed here from scratch, without trusting the pipeline's flag.
    recount = one(
        connection,
        """
        WITH k AS (
            SELECT count(*) AS n FROM f WHERE partida_real_ts IS NOT NULL
            GROUP BY year, month, id_empresa, nr_voo, dt_referencia, dt_partida_real,
                     hr_partida_real, sg_icao_origem, sg_icao_destino, nr_etapa,
                     nr_passag_pagos, nr_assentos_ofertados, kg_payload
        )
        SELECT sum(n - 1) AS extra_rows_by_recount FROM k
        """,
    )
    weak = one(
        connection,
        """
        WITH k AS (
            SELECT count(*) AS n, count(DISTINCT nr_passag_pagos) AS pax_values
            FROM f WHERE partida_real_ts IS NOT NULL AND NOT dq_no_takeoff
            GROUP BY year, month, id_empresa, nr_voo, dt_referencia, hr_partida_real,
                     sg_icao_origem, sg_icao_destino
        )
        SELECT sum(n - 1) FILTER (WHERE n > 1) AS same_flight_extra_rows,
               sum(n - 1) FILTER (WHERE n > 1 AND pax_values > 1) AS with_different_pax
        FROM k
        """,
    )
    return {
        "ids": ids,
        "flag_by_year": by_year,
        "flag_total": one(connection, "SELECT count_if(dq_duplicate_record) AS n FROM f")["n"],
        **recount,
        "same_flight_key_without_metrics": weak,
    }


def missing_values(connection: duckdb.DuckDBPyConnection) -> Row:
    columns = [row["column_name"] for row in rows(connection, "DESCRIBE SELECT * FROM f")]
    selects = ", ".join(f'count(*) - count("{name}") AS "{name}"' for name in columns)
    totals = one(connection, f"SELECT {selects} FROM f")
    total = one(connection, "SELECT count(*) AS n FROM f")["n"]
    by_year = rows(
        connection,
        """
        SELECT year,
          round(100.0 * count_if(kg_bagagem_excesso IS NULL) / count(*), 2) AS excess_baggage,
          round(100.0 * count_if(kg_bagagem_livre IS NULL) / count(*), 2) AS free_baggage,
          round(100.0 * count_if(lt_combustivel IS NULL) / count(*), 2) AS fuel,
          round(100.0 * count_if(partida_real_ts IS NULL) / count(*), 2) AS departure_ts,
          round(100.0 * count_if(chegada_real_ts IS NULL) / count(*), 2) AS arrival_ts,
          round(100.0 * count_if(km_distancia IS NULL) / count(*), 2) AS distance,
          round(100.0 * count_if(sg_iata_origem IS NULL) / count(*), 2) AS iata_origin,
          round(100.0 * count_if(ds_natureza_tipo_linha = 'NÃO IDENTIFICADA') / count(*), 2)
            AS line_nature_unidentified
        FROM f GROUP BY 1 ORDER BY 1
        """,
    )
    return {
        "null_pct_by_column": {
            name: round(100 * count / total, 4) for name, count in totals.items() if count
        },
        "columns_never_null": sorted(name for name, count in totals.items() if not count),
        "by_year": by_year,
    }


def flags(connection: duckdb.DuckDBPyConnection) -> Row:
    columns = [
        row["column_name"]
        for row in rows(connection, "DESCRIBE SELECT * FROM f")
        if row["column_name"].startswith("dq_")
    ]
    anyflag = " OR ".join(columns)
    selects = ", ".join(f"count_if({name}) AS {name}" for name in columns)
    totals = one(connection, f"SELECT {selects}, count_if({anyflag}) AS any_flag FROM f")
    by_year = rows(
        connection,
        f"""
        SELECT year, count(*) AS rows, count_if({anyflag}) AS any_flag,
               round(100.0 * count_if({anyflag}) / count(*), 3) AS any_flag_pct, {selects}
        FROM f GROUP BY 1 ORDER BY 1
        """,
    )
    recount = one(
        connection,
        """
        SELECT count_if(nr_assentos_ofertados > 0
                 AND nr_passag_pagos + nr_passag_gratis > nr_assentos_ofertados) AS pax_exceed_seats,
               count_if(nr_assentos_ofertados = 0 AND nr_passag_pagos > 0) AS pax_without_seats,
               count_if(nr_decolagem = 0) AS no_takeoff,
               count_if(km_distancia = 0) AS zero_distance,
               count_if(sg_icao_origem = sg_icao_destino) AS same_od,
               count_if(chegada_real_ts < partida_real_ts) AS arrival_before_departure,
               count_if(nr_horas_voadas > 30) AS hours_over_30
        FROM f
        """,
    )
    return {"totals": totals, "by_year": by_year, "independent_recount": recount}


def consistency(connection: duckdb.DuckDBPyConnection) -> Row:
    result: Row = {}
    result["ranges"] = rows(
        connection,
        """
        SELECT 'seats' AS metric, min(nr_assentos_ofertados) AS min,
               quantile_cont(nr_assentos_ofertados, 0.5) AS p50,
               quantile_cont(nr_assentos_ofertados, 0.999) AS p999,
               max(nr_assentos_ofertados) AS max FROM f
        UNION ALL SELECT 'paid_pax', min(nr_passag_pagos), quantile_cont(nr_passag_pagos, 0.5),
               quantile_cont(nr_passag_pagos, 0.999), max(nr_passag_pagos) FROM f
        UNION ALL SELECT 'km', min(km_distancia), quantile_cont(km_distancia, 0.5),
               quantile_cont(km_distancia, 0.999), max(km_distancia) FROM f
        UNION ALL SELECT 'hours', min(nr_horas_voadas), quantile_cont(nr_horas_voadas, 0.5),
               quantile_cont(nr_horas_voadas, 0.999), max(nr_horas_voadas) FROM f
        UNION ALL SELECT 'excess_kg', min(kg_bagagem_excesso),
               quantile_cont(kg_bagagem_excesso, 0.5), quantile_cont(kg_bagagem_excesso, 0.999),
               max(kg_bagagem_excesso) FROM f
        UNION ALL SELECT 'fuel_l', min(lt_combustivel), quantile_cont(lt_combustivel, 0.5),
               quantile_cont(lt_combustivel, 0.999), max(lt_combustivel) FROM f
        UNION ALL SELECT 'load_factor', min(load_factor_paid), quantile_cont(load_factor_paid, 0.5),
               quantile_cont(load_factor_paid, 0.999), max(load_factor_paid) FROM f
        """,
    )
    result["service_by_year"] = rows(
        connection,
        """
        SELECT year, count(*) AS rows,
          count_if(NOT dq_duplicate_record) AS rows_without_duplicates,
          sum(nr_decolagem) FILTER (WHERE NOT dq_duplicate_record) AS takeoffs,
          sum(nr_passag_pagos) FILTER (WHERE NOT dq_duplicate_record) AS paid_pax,
          sum(nr_passag_pagos) FILTER (WHERE NOT dq_duplicate_record AND NOT is_international)
            AS paid_pax_domestic,
          sum(nr_passag_pagos) FILTER (WHERE NOT dq_duplicate_record AND is_international)
            AS paid_pax_international,
          sum(nr_rpk) FILTER (WHERE NOT dq_duplicate_record) AS rpk,
          sum(nr_ask) FILTER (WHERE NOT dq_duplicate_record) AS ask,
          round(sum(nr_rpk) FILTER (WHERE NOT dq_duplicate_record AND nr_ask > 0)
                / sum(nr_ask) FILTER (WHERE NOT dq_duplicate_record AND nr_ask > 0), 4)
            AS rpk_over_ask,
          round(100.0 * count_if(is_international) / count(*), 2) AS international_pct,
          round(100.0 * count_if(nr_assentos_ofertados = 0) / count(*), 2) AS zero_seats_pct,
          count(DISTINCT sg_empresa_icao) AS carriers,
          count(DISTINCT sg_icao_origem) AS airports,
          count(DISTINCT route_icao) AS routes
        FROM f GROUP BY 1 ORDER BY 1
        """,
    )
    result["di_by_year"] = rows(
        connection,
        """
        SELECT year, ds_grupo_di, cd_di, ds_di, count(*) AS rows FROM f
        GROUP BY ALL ORDER BY 1, rows DESC
        """,
    )
    result["route_distance"] = one(
        connection,
        """
        WITH medians AS (
            SELECT route_icao, median(km_distancia) AS km FROM f
            WHERE km_distancia > 0 GROUP BY 1
        )
        SELECT count(*) AS rows_checked,
               count_if(abs(f.km_distancia - m.km) > 0.05 * m.km) AS over_5pct_from_route_median,
               count_if(abs(f.km_distancia - m.km) > 0.5 * m.km) AS over_50pct_from_route_median
        FROM f JOIN medians m USING (route_icao) WHERE f.km_distancia > 0
        """,
    )
    result["identifiers"] = {
        "carrier_icao_with_several_names": one(
            connection,
            """
            SELECT count(*) AS n FROM (SELECT sg_empresa_icao FROM f
            GROUP BY 1 HAVING count(DISTINCT nm_empresa) > 1)
            """,
        )["n"],
        "airport_icao_with_several_countries": rows(
            connection,
            """
            SELECT sg_icao_origem AS icao, string_agg(DISTINCT nm_pais_origem, ' | ') AS countries,
                   count(*) AS rows FROM f GROUP BY 1
            HAVING count(DISTINCT nm_pais_origem) > 1 ORDER BY rows DESC LIMIT 15
            """,
        ),
        "nonstandard_icao": rows(
            connection,
            """
            SELECT code, count(*) AS rows FROM (
              SELECT sg_icao_origem AS code FROM f WHERE NOT regexp_full_match(sg_icao_origem, '[A-Z]{4}')
              UNION ALL
              SELECT sg_icao_destino FROM f WHERE NOT regexp_full_match(sg_icao_destino, '[A-Z]{4}')
            ) GROUP BY 1 ORDER BY rows DESC LIMIT 15
            """,
        ),
    }
    result["international_vs_regulatory_nature"] = rows(
        connection,
        """
        SELECT ds_natureza_etapa, is_international, count(*) AS rows FROM f
        GROUP BY ALL ORDER BY rows DESC
        """,
    )
    return result


def baggage(connection: duckdb.DuckDBPyConnection) -> Row:
    by_year = rows(
        connection,
        """
        SELECT year,
          round(100.0 * count_if(kg_bagagem_excesso IS NULL) / count(*), 2) AS null_pct,
          round(100.0 * avg(has_excess_baggage::INT), 2) AS positive_pct,
          round(sum(kg_bagagem_excesso) / sum(nr_passag_pagos) FILTER (WHERE kg_bagagem_excesso
                IS NOT NULL), 4) AS excess_kg_per_paid_pax
        FROM f WHERE nr_assentos_ofertados > 0 GROUP BY 1 ORDER BY 1
        """,
    )
    carrier_year = rows(
        connection,
        """
        WITH cy AS (
          SELECT year, sg_empresa_icao, count(*) AS n,
                 avg(has_excess_baggage::INT) AS positive
          FROM f WHERE nr_assentos_ofertados > 0 GROUP BY 1, 2 HAVING count(*) >= 1000
        )
        SELECT year, count(*) AS carriers,
               count_if(positive IS NULL) AS never_report,
               count_if(positive = 0) AS always_zero,
               round(min(positive), 3) AS min_rate, round(median(positive), 3) AS median_rate,
               round(max(positive), 3) AS max_rate
        FROM cy GROUP BY 1 ORDER BY 1
        """,
    )
    return {"by_year": by_year, "carrier_year_spread": carrier_year}


def clock(connection: duckdb.DuckDBPyConnection) -> Row:
    """Departure hour profile per year, on large Brazilian airports and domestic legs."""
    hist = rows(
        connection,
        """
        WITH d AS (
          SELECT year, hour(hr_partida_real) AS h FROM f
          WHERE sg_icao_origem IN ('SBGR','SBSP','SBBR','SBGL','SBRJ','SBKP','SBCF','SBPA','SBSV','SBRF')
            AND NOT is_international AND nr_assentos_ofertados > 0 AND hr_partida_real IS NOT NULL
        ), c AS (SELECT year, h, count(*) AS n FROM d GROUP BY 1, 2)
        SELECT year,
          arg_min(h, n) AS quietest_hour,
          round(100.0 * sum(n) FILTER (WHERE h BETWEEN 1 AND 4) / sum(n), 2) AS pct_01_04,
          round(100.0 * sum(n) FILTER (WHERE h BETWEEN 6 AND 9) / sum(n), 2) AS pct_06_09
        FROM c GROUP BY 1 ORDER BY 1
        """,
    )
    agreement = rows(
        connection,
        """
        SELECT year, count(*) AS rows,
          round(100.0 * count_if(dq_hours_clock_mismatch) / count(*), 3) AS mismatch_pct
        FROM f WHERE is_international AND chegada_real_ts IS NOT NULL GROUP BY 1 ORDER BY 1
        """,
    )
    return {"domestic_hour_profile": hist, "international_hours_vs_clock": agreement}


def code_share(connection: duckdb.DuckDBPyConnection) -> Row:
    """Does a code-share row have an operating twin at the same minute on the same route?"""
    by_year = rows(
        connection,
        """
        WITH keyed AS (
          SELECT year, cd_di, sg_empresa_icao, route_icao, partida_real_ts, nr_assentos_ofertados
          FROM f WHERE partida_real_ts IS NOT NULL AND NOT dq_duplicate_record
                   AND nr_assentos_ofertados > 0
        ), slots AS (
          SELECT route_icao, partida_real_ts,
                 count(DISTINCT sg_empresa_icao) AS carriers
          FROM keyed GROUP BY 1, 2
        )
        SELECT k.year,
          count_if(k.cd_di = 'C') AS code_share_rows,
          count_if(k.cd_di = 'C' AND s.carriers > 1) AS code_share_with_other_carrier,
          count_if(k.cd_di = '0') AS regular_rows,
          count_if(k.cd_di = '0' AND s.carriers > 1) AS regular_with_other_carrier
        FROM keyed k JOIN slots s USING (route_icao, partida_real_ts)
        GROUP BY 1 ORDER BY 1
        """,
    )
    carriers = rows(
        connection,
        """
        SELECT sg_empresa_icao, count(*) AS rows,
               round(avg(nr_decolagem), 3) AS avg_takeoffs,
               round(100.0 * count_if(is_international) / count(*), 1) AS international_pct,
               min(year) AS first_year, max(year) AS last_year
        FROM f WHERE cd_di = 'C' GROUP BY 1 ORDER BY rows DESC LIMIT 10
        """,
    )
    return {"by_year": by_year, "top_carriers": carriers}


def rejects(connection: duckdb.DuckDBPyConnection, data_root: Path) -> Row:
    pattern_chunks = (data_root / "interim/ingestion/chunks/*/rejects.parquet").as_posix()
    pattern_ids = (data_root / "processed/flights_rejects/*.parquet").as_posix()
    result: Row = {"by_reason": [], "samples": []}
    sources = []
    if list((data_root / "interim/ingestion/chunks").glob("*/rejects.parquet")):
        sources.append(pattern_chunks)
    if list((data_root / "processed/flights_rejects").glob("*.parquet")):
        sources.append(pattern_ids)
    if not sources:
        return result
    listing = ", ".join(f"'{item}'" for item in sources)
    source = f"read_parquet([{listing}])"
    result["by_reason"] = rows(
        connection, f"SELECT reason, count(*) AS rows FROM {source} GROUP BY 1 ORDER BY 2 DESC"
    )
    result["by_year_of_record"] = rows(
        connection,
        f"""
        SELECT reason, left(json_extract_string(raw_record, '$.dt_referencia'), 4) AS year,
               count(*) AS rows
        FROM {source} GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 40
        """,
    )
    result["samples"] = rows(
        connection,
        f"""
        SELECT reason, left(raw_record, 400) AS raw_record FROM (
            SELECT *, row_number() OVER (PARTITION BY reason ORDER BY chunk_id, source_line) AS r
            FROM {source}
        ) WHERE r <= 3 ORDER BY reason, r
        """,
    )
    return result


def reconcile_with_raw(
    raw: Sequence[Row], processed_by_year: Sequence[Row], rejected_by_year: Sequence[Row]
) -> list[Row]:
    by_year = {str(row["year"]): row for row in processed_by_year}
    rejected: dict[str, int] = {}
    for row in rejected_by_year:
        key = str(row["year"])
        rejected[key] = rejected.get(key, 0) + int(row["rows"])
    table = []
    for row in raw:
        year = str(row["year"])
        published = by_year.get(year, {})
        table.append(
            {
                "year": year,
                "raw_rows": row["rows"],
                "published_rows": published.get("rows", 0),
                "rejected_rows": rejected.get(year, 0),
                "unexplained_rows": row["rows"] - published.get("rows", 0) - rejected.get(year, 0),
                "raw_paid_pax": row["paid_passengers"],
                "published_paid_pax": published.get("paid_pax", 0),
                "raw_takeoffs": row["takeoffs"],
                "published_takeoffs": published.get("takeoffs", 0),
                "raw_seats": row["seats"],
                "published_seats": published.get("seats", 0),
                "raw_km": row["km"],
                "published_km": published.get("km", 0),
                "raw_hours": row["hours"],
                "published_hours": published.get("hours", 0),
            }
        )
    return table


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("reports/ingestion"))
    parser.add_argument("--memory-limit", default="5GB")
    args = parser.parse_args()

    flights = args.data_root / "processed" / "flights"
    glob = (flights / "*" / "*" / "*.parquet").as_posix()
    csv_path = args.data_root / "raw" / "anac_brazil.csv"
    temp_dir = args.data_root / "interim" / "audit_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(":memory:")
    connection.execute(f"SET memory_limit='{args.memory_limit}'")
    connection.execute(f"SET temp_directory='{temp_dir.as_posix()}'")
    connection.execute("SET preserve_insertion_order=false")
    connection.execute(
        # DuckDB infers the zero-padded partition value month=08 as text.
        "CREATE VIEW f AS SELECT * REPLACE (CAST(month AS INTEGER) AS month, "
        f"CAST(year AS INTEGER) AS year) FROM read_parquet('{glob}', hive_partitioning=true)"
    )

    audit: Row = {"engine": f"duckdb {duckdb.__version__}"}
    timings: dict[str, float] = {}

    def timed(name: str, function: Any, *call_args: Any) -> Any:
        started = time.perf_counter()
        print(f"[audit] {name} ...", flush=True)
        value = function(*call_args)
        timings[name] = round(time.perf_counter() - started, 1)
        print(f"[audit] {name} done in {timings[name]} s", flush=True)
        return value

    audit["physical_lines_in_csv"] = timed("physical_lines", count_physical_lines, csv_path)
    audit["structural"] = timed("structural", structural, connection, glob, flights)
    audit["temporal"] = timed("temporal", temporal, connection)
    audit["duplicates"] = timed("duplicates", duplicates, connection)
    audit["missing_values"] = timed("missing_values", missing_values, connection)
    audit["flags"] = timed("flags", flags, connection)
    audit["consistency"] = timed("consistency", consistency, connection)
    audit["baggage"] = timed("baggage", baggage, connection)
    audit["clock"] = timed("clock", clock, connection)
    audit["code_share"] = timed("code_share", code_share, connection)
    audit["rejects"] = timed("rejects", rejects, connection, args.data_root)

    raw = timed("raw_csv_by_year", raw_by_year, connection, csv_path)
    processed = rows(
        connection,
        """
        SELECT year, count(*) AS rows, sum(nr_passag_pagos) AS paid_pax,
               sum(nr_decolagem) AS takeoffs, sum(nr_assentos_ofertados) AS seats,
               sum(km_distancia) AS km, sum(nr_horas_voadas) AS hours
        FROM f GROUP BY 1 ORDER BY 1
        """,
    )
    audit["reconciliation_with_raw"] = reconcile_with_raw(
        raw, processed, audit["rejects"].get("by_year_of_record", [])
    )
    audit["timings_seconds"] = timings
    connection.close()

    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / "independent_audit.json"
    target.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(f"[audit] wrote {target}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
