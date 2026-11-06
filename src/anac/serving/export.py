"""Write JSON payloads matching the frontend's v2 contract (`web/lib/data/contracts.ts`).

Each file is what the endpoint should return, so a future API only has to read and serve it.
Every number comes from published data. A model card never shows a metric unless a real report
exists, and baseline metrics are labelled with the split they were computed on.
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from anac.features.config import FeatureConfig, month_label
from anac.features.contracts import CONTRACTS
from anac.features.panels import resolve_dataset
from anac.ingestion.storage import write_json_atomic

SCOPE_NOTE = (
    "Paid passengers are summed per flight leg, so a passenger staying aboard a multi-leg flight "
    "counts once per leg, which runs about 1-2% above ANAC's published totals. Load factor is paid "
    "passengers over seats on passenger legs."
)
PERIOD_NOTE = "The last 12 months published in this dataset."
ENDPOINTS = {
    "/health": "health.json",
    "/v2/overview": "overview.json",
    "/v2/airports": "airports.json",
    "/v2/routes": "routes.json",
    "/v2/models": "models.json",
    "/v2/datasets": "datasets.json",
    "/v2/modules": "modules.json",
    "/v2/analyst/catalog": "analyst_catalog.json",
}
_PASSENGER_SCOPE = (
    "NOT dq_duplicate_record AND NOT dq_no_takeoff AND nr_assentos_ofertados > 0 "
    "AND ds_grupo_di <> 'IMPRODUTIVO' AND NOT dq_zero_distance AND NOT dq_same_origin_destination "
    "AND nr_passag_pagos IS NOT NULL"
)
KPI_LABELS = {
    "flights": "Flights",
    "passengers": "Paid passengers",
    "load_factor": "Paid load factor",
    "active_routes": "Active routes",
}


def envelope(data: Any, generated_at: str, note: str | None = None) -> dict[str, Any]:
    meta: dict[str, Any] = {"source": "API", "isDemo": False, "generatedAt": generated_at}
    if note:
        meta["note"] = note
    return {"data": data, "meta": meta}


def load_airports(path: Path) -> pl.DataFrame:
    """ANAC's public aerodrome list. It only covers Brazilian public aerodromes."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    frame = pl.read_csv(
        io.BytesIO(text.encode("utf-8")),
        separator=";",
        skip_lines=1,
        infer_schema=False,
        truncate_ragged_lines=True,
    )
    return (
        frame.select(
            pl.col("Código OACI").str.strip_chars().alias("icao"),
            pl.col("Nome").str.strip_chars().alias("name"),
            pl.col("Município Servido").str.strip_chars().alias("city"),
            pl.col("LATGEOPOINT")
            .str.replace(",", ".", literal=True)
            .cast(pl.Float64, strict=False)
            .alias("lat"),
            pl.col("LONGEOPOINT")
            .str.replace(",", ".", literal=True)
            .cast(pl.Float64, strict=False)
            .alias("lon"),
        )
        .filter(pl.col("lat").is_not_null() & pl.col("lon").is_not_null())
        .unique("icao", keep="first")
    )


def _rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    result = connection.execute(sql)
    names = [item[0] for item in result.description]
    return [dict(zip(names, record, strict=True)) for record in result.fetchall()]


def _month_filter(first: int, last: int) -> str:
    return f"year(dt_referencia) * 12 + month(dt_referencia) - 1 BETWEEN {first} AND {last}"


def build_overview(connection: duckdb.DuckDBPyConnection, airports: pl.DataFrame) -> dict[str, Any]:
    latest_row = connection.execute(
        "SELECT max(year(dt_referencia) * 12 + month(dt_referencia) - 1) FROM f"
    ).fetchone()
    if latest_row is None or latest_row[0] is None:
        raise ValueError("the dataset is empty")
    latest = int(latest_row[0])
    current = _month_filter(latest - 11, latest)
    previous = _month_filter(latest - 23, latest - 12)

    def period(where: str) -> dict[str, Any]:
        return _rows(
            connection,
            f"""
            SELECT sum(nr_decolagem) FILTER (WHERE NOT dq_duplicate_record) AS flights,
              sum(nr_passag_pagos) FILTER (WHERE {_PASSENGER_SCOPE}) AS passengers,
              sum(nr_passag_pagos) FILTER (WHERE {_PASSENGER_SCOPE}) * 1.0
                / sum(nr_assentos_ofertados) FILTER (WHERE {_PASSENGER_SCOPE}) AS load_factor,
              count(DISTINCT route_icao) FILTER (WHERE {_PASSENGER_SCOPE}) AS active_routes
            FROM f WHERE {where}
            """,
        )[0]

    now, before = period(current), period(previous)
    monthly = _rows(
        connection,
        f"""
        SELECT year(dt_referencia) * 12 + month(dt_referencia) - 1 AS m,
          sum(nr_passag_pagos) FILTER (WHERE {_PASSENGER_SCOPE}) AS passengers,
          sum(nr_decolagem) FILTER (WHERE NOT dq_duplicate_record) AS flights,
          sum(nr_passag_pagos) FILTER (WHERE {_PASSENGER_SCOPE}) * 1.0
            / sum(nr_assentos_ofertados) FILTER (WHERE {_PASSENGER_SCOPE}) AS load_factor,
          count(DISTINCT route_icao) FILTER (WHERE {_PASSENGER_SCOPE}) AS active_routes
        FROM f WHERE {_month_filter(latest - 23, latest)} GROUP BY 1 ORDER BY 1
        """,
    )
    last_12 = [row for row in monthly if row["m"] > latest - 12]
    kpis = []
    for key, label in KPI_LABELS.items():
        delta = None
        if before[key]:
            delta = float(now[key]) / float(before[key]) - 1
        kpis.append(
            {
                "id": key,
                "label": label,
                "value": float(now[key]) if key == "load_factor" else int(now[key]),
                "unit": "ratio" if key == "load_factor" else "count",
                "delta": delta,
                "trend": [float(row[key]) for row in last_12],
            }
        )
    return {
        "period": {"from": month_label(latest - 11), "to": month_label(latest)},
        "kpis": kpis,
        "monthly": [
            {
                "month": month_label(row["m"]),
                "passengers": int(row["passengers"] or 0),
                "flights": int(row["flights"] or 0),
            }
            for row in monthly
        ],
        "topRoutes": build_routes(connection, latest, limit=10),
        "topAirports": build_airports(connection, latest, airports)[:10],
    }


def build_routes(
    connection: duckdb.DuckDBPyConnection, latest: int, limit: int = 200
) -> list[dict[str, Any]]:
    rows = _rows(
        connection,
        f"""
        SELECT coalesce(any_value(sg_iata_origem), sg_icao_origem) AS origin,
               coalesce(any_value(sg_iata_destino), sg_icao_destino) AS destination,
               sum(nr_passag_pagos) AS passengers,
               sum(nr_passag_pagos) * 1.0 / sum(nr_assentos_ofertados) AS load_factor
        FROM f WHERE {_PASSENGER_SCOPE} AND {_month_filter(latest - 11, latest)}
        GROUP BY sg_icao_origem, sg_icao_destino ORDER BY passengers DESC LIMIT {limit}
        """,
    )
    return [
        {
            "origin": row["origin"],
            "destination": row["destination"],
            "passengers": int(row["passengers"]),
            "loadFactor": float(row["load_factor"]),
        }
        for row in rows
    ]


def build_airports(
    connection: duckdb.DuckDBPyConnection, latest: int, airports: pl.DataFrame
) -> list[dict[str, Any]]:
    """Airports with published coordinates. Foreign airports have none and are left out."""
    window = _month_filter(latest - 11, latest)
    movements = _rows(
        connection,
        f"""
        WITH m AS (
          SELECT sg_icao_origem AS icao, sg_iata_origem AS iata, sg_uf_origem AS uf,
                 nm_municipio_origem AS city, nm_aerodromo_origem AS name
          FROM f WHERE NOT dq_duplicate_record AND NOT dq_no_takeoff AND {window}
          UNION ALL
          SELECT sg_icao_destino, sg_iata_destino, sg_uf_destino, nm_municipio_destino, nm_aerodromo_destino
          FROM f WHERE NOT dq_duplicate_record AND NOT dq_no_takeoff AND {window}
        )
        SELECT icao, any_value(iata) AS iata, any_value(uf) AS uf, any_value(city) AS city,
               any_value(name) AS name, count(*) AS movements
        FROM m GROUP BY 1 ORDER BY movements DESC
        """,
    )
    coordinates = {row["icao"]: row for row in airports.iter_rows(named=True)}
    result = []
    for row in movements:
        known = coordinates.get(row["icao"])
        if known is None or not row["uf"]:
            continue
        result.append(
            {
                "icao": row["icao"],
                "iata": row["iata"] or row["icao"],
                "name": row["name"] or known["name"],
                "city": row["city"] or known["city"] or "",
                "uf": row["uf"],
                "lat": known["lat"],
                "lon": known["lon"],
                "movements": int(row["movements"]),
            }
        )
    return result


def _metric(name: str, section: dict[str, Any], evaluated_on: str) -> dict[str, Any] | None:
    value = section.get("value")
    return (
        {"name": name, "value": value, "evaluatedOn": evaluated_on} if value is not None else None
    )


def build_models(reports: Path) -> list[dict[str, Any]]:
    """Cards say plainly that only baselines exist. Nothing here is a trained model."""
    primary = {
        "a": ("pred_seasonal_trend", (("WAPE", "wape"), ("MASE", "mase"))),
        "b": ("pred_same_month_last_year", (("Seat-weighted MAE", "seat_weighted_mae"),)),
        "d": ("pred_pax_seasonal_trend", (("WAPE (passengers)", "wape"),)),
    }
    cards = []
    for module, (baseline, metrics) in primary.items():
        contract = CONTRACTS[module]
        path = reports / f"module_{module}.json"
        values: list[dict[str, Any]] | None = None
        evaluated_at: str | None = None
        if path.exists():
            report = json.loads(path.read_text(encoding="utf-8"))
            evaluated_at = report["evaluated_at"]
            section = report["results"][baseline]["all"]
            items = [
                _metric(
                    f"{label}, baseline {baseline.removeprefix('pred_')}",
                    section[key],
                    report["evaluated_on"],
                )
                for label, key in metrics
            ]
            values = [item for item in items if item]
        cards.append(
            {
                "id": f"baseline-{module}",
                "name": f"Baseline: {contract.title}",
                "task": ", ".join(contract.targets),
                "pipeline": "anac-features baselines",
                "status": "available" if values else "not_trained",
                "metrics": values,
                "lastTrainedAt": evaluated_at,
            }
        )
    cards.extend(_lightgbm_cards(reports.parent / "models"))
    cards.append(
        {
            "id": "module-c",
            "name": "Checked baggage per passenger",
            "task": "Provisional target. Published only if it beats its baseline on validation.",
            "pipeline": "scripts/assess_module_c.py",
            "status": "not_trained",
            "metrics": None,
            "lastTrainedAt": None,
        }
    )
    return cards


def _lightgbm_cards(directory: Path) -> list[dict[str, Any]]:
    """Trained models appear only when a real report exists, labelled with the split."""
    cards = []
    for module in CONTRACTS:
        path = directory / f"module_{module}.json"
        if not path.exists():
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        metrics = []
        for target, item in report["targets"].items():
            metrics.append(
                {
                    "name": f"{item['metric']} ({target})",
                    "value": item["lightgbm"]["value"],
                    "evaluatedOn": report["evaluated_on"],
                }
            )
        cards.append(
            {
                "id": f"lightgbm-{module}",
                "name": f"LightGBM: {CONTRACTS[module].title}",
                "task": ", ".join(report["targets"]),
                "pipeline": "anac-models train",
                "status": "available",
                "metrics": metrics,
                "lastTrainedAt": report["trained_at"],
            }
        )
    return cards


def build_datasets(processed: Path, version: str, rows: int) -> list[dict[str, Any]]:
    published = processed / version
    size = sum(path.stat().st_size for path in published.rglob("*.parquet"))
    datasets = [
        {
            "name": version,
            "description": "ANAC flight legs, audited against the raw file and ANAC's official aggregate.",
            "approxSize": f"{rows / 1e6:.1f} million rows, {size / 1e9:.2f} GB",
            "status": "ready",
        }
    ]
    if version != "flights_v2_1":
        datasets.append(
            {
                "name": "flights_v2_1",
                "description": "Adds 2015-08, 2016-02, 2018-07 and 2020-08 from ANAC's monthly files.",
                "approxSize": "Same dataset plus four months",
                "status": "planned",
            }
        )
    return datasets


def build_analyst_catalog(version: str, unknown_months: list[str]) -> dict[str, Any]:
    """What a future agent may read and must state. Not an agent implementation."""
    return {
        "version": 1,
        "dataset": version,
        "tools": [
            {"name": name.strip("/").replace("/", "_"), "endpoint": name, "payload": file}
            for name, file in ENDPOINTS.items()
            if name not in ("/health", "/v2/analyst/catalog")
        ],
        "facts_that_must_accompany_answers": [
            *(
                [f"These months are absent from the dataset: {', '.join(unknown_months)}."]
                if unknown_months
                else []
            ),
            SCOPE_NOTE,
            "Movements count takeoffs and landings. They do not measure congestion, queues or delays.",
            "Passengers carried are demand served, not unconstrained demand.",
        ],
        "must_not_claim": [
            "Ticket prices or fare predictions: this dataset has no fares.",
            "Excess baggage behaviour: reporting differs by carrier and period.",
            "Causal effects: these data show associations.",
            "Forecast quality beyond the split a metric was computed on.",
        ],
    }


def export_all(cfg: FeatureConfig, airports_csv: Path, output: Path) -> dict[str, Any]:
    dataset, version = resolve_dataset(cfg.processed)
    glob = (dataset / "*" / "*" / "*.parquet").as_posix()
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    airports = load_airports(airports_csv)
    with duckdb.connect() as connection:
        connection.execute("SET memory_limit='3GB'")
        connection.execute("SET preserve_insertion_order=false")
        connection.execute(
            f"CREATE VIEW f AS SELECT * FROM read_parquet('{glob}', hive_partitioning=false)"
        )
        overview = build_overview(connection, airports)
        latest_row = connection.execute(
            "SELECT max(year(dt_referencia) * 12 + month(dt_referencia) - 1), count(*) FROM f"
        ).fetchone()
        if latest_row is None:
            raise ValueError("the dataset is empty")
        latest, rows = int(latest_row[0]), int(latest_row[1])
        present = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT year(dt_referencia) * 12 + month(dt_referencia) - 1 FROM f"
            ).fetchall()
        }
        routes = build_routes(connection, latest)
        airport_rows = build_airports(connection, latest, airports)
    unknown = sorted(month_label(m) for m in set(range(min(present), max(present) + 1)) - present)

    note = f"{PERIOD_NOTE} {SCOPE_NOTE}"
    if unknown:
        note += f" Absent months: {', '.join(unknown)}."
    payloads: dict[str, Any] = {
        "health.json": envelope(
            {"ok": True, "version": version, "detail": "Static export"}, generated_at
        ),
        "overview.json": envelope(overview, generated_at, note),
        "airports.json": envelope(
            airport_rows, generated_at, "Brazilian public aerodromes with published coordinates."
        ),
        "routes.json": envelope(routes, generated_at, note),
        "models.json": envelope(
            build_models(cfg.reports),
            generated_at,
            (
                "Metrics come from validation. The final test on 2024-2025 has not been run."
                if (cfg.reports.parent / "models").exists()
                else "Baselines only. No forecasting model has been trained."
            ),
        ),
        "datasets.json": envelope(build_datasets(cfg.processed, version, rows), generated_at),
        "modules.json": envelope(
            [contract.to_dict() for contract in CONTRACTS.values()], generated_at
        ),
        "analyst_catalog.json": envelope(build_analyst_catalog(version, unknown), generated_at),
    }
    for name, payload in payloads.items():
        write_json_atomic(output / name, payload)
    write_json_atomic(
        output / "index.json",
        {"generated_at": generated_at, "dataset": version, "endpoints": ENDPOINTS},
    )
    return {"output": str(output), "files": sorted(payloads), "dataset": version}


class PayloadStore:
    """The whole read layer a future API needs: resolve an endpoint to its stored payload."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def endpoints(self) -> list[str]:
        return sorted(ENDPOINTS)

    def get(self, endpoint: str) -> dict[str, Any]:
        if endpoint not in ENDPOINTS:
            raise KeyError(endpoint)
        loaded: dict[str, Any] = json.loads(
            (self._directory / ENDPOINTS[endpoint]).read_text(encoding="utf-8")
        )
        return loaded
