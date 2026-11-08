"""Decide, before any training, whether total checked baggage per passenger is a defensible target.

Criteria are fixed here and use data up to 2022 only. A carrier-month is admitted only if it
passes all of them. The verdict is a go/no-go for building the module, not a claim of skill.

    python scripts/assess_module_c.py [--data-root data] [--out reports/baggage]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

FIRST_YEAR, LAST_YEAR = 2018, 2022
CANDIDATES = ("AZU", "GLO", "TAM", "ONE", "ACN", "PTB", "PAM")
ANCHORS = ("AZU", "GLO", "TAM")
MIN_FLIGHTS_WITH_BAG = 0.98
MAX_RELATIVE_SHIFT = 0.25
MIN_ROUTE_PERSISTENCE = 0.70
MIN_ADMITTED_MONTHS = 36
MIN_QUALIFIED_CARRIERS = 2
MIN_DOMESTIC_PAX_SHARE = 0.60


def detect_shifts(monthly: pl.DataFrame) -> list[dict[str, Any]]:
    """Flag months where a carrier moved against the majority of its reference peers.

    Seasonality and market-wide changes hit every carrier and cancel out in a ratio. A carrier's
    own step shows up against every peer, while a peer's step shows up only against that peer, so
    requiring a majority separates the two without any iteration. Each pair keeps a trailing
    reference of accepted months, so a long block cannot become normal. A month with no peer
    cannot be verified and is not admitted.
    """
    values = {
        (row["carrier"], row["month_idx"]): row["bag_per_pax"]
        for row in monthly.iter_rows(named=True)
    }
    rows: list[dict[str, Any]] = []
    for carrier in monthly.get_column("carrier").unique().sort().to_list():
        series = monthly.filter(pl.col("carrier") == carrier).sort("month_idx")
        peers = [peer for peer in ANCHORS if peer != carrier]
        accepted: dict[str, list[float]] = {peer: [] for peer in peers}
        for record in series.iter_rows(named=True):
            month, own = record["month_idx"], record["bag_per_pax"]
            available = 0
            moved = 0
            for peer in peers:
                other = values.get((peer, month))
                if not other:
                    continue
                available += 1
                ratio = own / other
                history = sorted(accepted[peer][-12:])
                reference = history[len(history) // 2] if len(accepted[peer]) >= 6 else None
                pair_moved = bool(reference) and abs(ratio / reference - 1) > MAX_RELATIVE_SHIFT
                moved += pair_moved
                if not pair_moved:
                    accepted[peer].append(ratio)
            majority = available // 2 + 1
            rows.append(
                {
                    **{
                        key: record[key]
                        for key in (
                            "carrier",
                            "y",
                            "m",
                            "month_idx",
                            "flights",
                            "pax",
                            "bag_per_pax",
                            "share_with_bag",
                        )
                    },
                    "peers_compared": available,
                    "peers_moved_against": moved,
                    "shifted": available == 0 or moved >= majority,
                    "low_coverage": record["share_with_bag"] < MIN_FLIGHTS_WITH_BAG,
                }
            )
    return rows


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
        SELECT sg_empresa_icao AS carrier, year(dt_referencia) AS y, month(dt_referencia) AS m,
               route_icao, nr_passag_pagos AS pax,
               coalesce(kg_bagagem_livre, 0) + coalesce(kg_bagagem_excesso, 0) AS bag
        FROM read_parquet('{glob}', hive_partitioning=false)
        WHERE NOT dq_duplicate_record AND NOT dq_no_takeoff AND nr_assentos_ofertados > 0
          AND ds_grupo_di <> 'IMPRODUTIVO' AND NOT is_international AND nr_passag_pagos > 0
          AND year(dt_referencia) BETWEEN {FIRST_YEAR - 1} AND {LAST_YEAR}
        """
    )
    monthly = pl.DataFrame(
        connection.execute(
            """
            SELECT carrier, y, m, y * 12 + m - 1 AS month_idx, count(*) AS flights, sum(pax) AS pax,
                   sum(bag) * 1.0 / sum(pax) AS bag_per_pax, count_if(bag > 0) * 1.0 / count(*) AS share_with_bag
            FROM f GROUP BY 1, 2, 3
            """
        ).fetchall(),
        schema=[
            "carrier",
            "y",
            "m",
            "month_idx",
            "flights",
            "pax",
            "bag_per_pax",
            "share_with_bag",
        ],
        orient="row",
        infer_schema_length=None,
    ).sort("carrier", "month_idx")

    rows = detect_shifts(monthly)
    states = pl.DataFrame(rows).with_columns(
        (~pl.col("shifted") & ~pl.col("low_coverage")).alias("admitted")
    )
    in_period = states.filter(pl.col("y") >= FIRST_YEAR)

    admitted_keys = in_period.filter(pl.col("admitted")).select("carrier", "month_idx")
    connection.execute("CREATE TEMP TABLE admitted_months (carrier VARCHAR, month_idx INTEGER)")
    connection.executemany("INSERT INTO admitted_months VALUES (?, ?)", admitted_keys.rows())
    persistence = connection.execute(
        """
        WITH rm AS (
          SELECT f.carrier, route_icao, y * 12 + m - 1 AS month_idx, y, m, sum(bag) / sum(pax) AS v
          FROM f JOIN admitted_months a ON f.carrier = a.carrier AND f.y * 12 + f.m - 1 = a.month_idx
          GROUP BY 1, 2, 3, 4, 5 HAVING sum(pax) >= 2000
        ), p AS (
          SELECT a.carrier, a.v AS v1, b.v AS v0
          FROM rm a JOIN rm b ON a.carrier = b.carrier AND a.route_icao = b.route_icao
                             AND a.month_idx = b.month_idx + 12
        ), r AS (
          SELECT carrier, rank() OVER (PARTITION BY carrier ORDER BY v1) AS r1,
                 rank() OVER (PARTITION BY carrier ORDER BY v0) AS r0 FROM p
        )
        SELECT carrier, count(*) AS pairs, corr(r1, r0) AS spearman FROM r GROUP BY 1
        """
    ).fetchall()
    persistence_by_carrier = {row[0]: {"pairs": row[1], "spearman": row[2]} for row in persistence}
    market = connection.execute(f"SELECT sum(pax) FROM f WHERE y >= {FIRST_YEAR}").fetchone()
    total_pax = float(market[0]) if market and market[0] else 0.0
    connection.close()

    carriers: dict[str, Any] = {}
    for carrier in CANDIDATES:
        data = in_period.filter(pl.col("carrier") == carrier)
        if data.is_empty():
            carriers[carrier] = {"qualified": False, "reason": "no flights in the period"}
            continue
        admitted = data.filter(pl.col("admitted"))
        excluded = data.filter(~pl.col("admitted")).sort("month_idx")
        spearman = persistence_by_carrier.get(carrier, {}).get("spearman")
        reasons = []
        if admitted.height < MIN_ADMITTED_MONTHS:
            reasons.append(f"only {admitted.height} admitted months")
        if spearman is None or spearman < MIN_ROUTE_PERSISTENCE:
            reasons.append(f"route persistence {spearman}")
        carriers[carrier] = {
            "qualified": not reasons,
            "reasons": reasons,
            "months_in_period": data.height,
            "months_admitted": admitted.height,
            "months_excluded": [
                f"{row['y']}-{row['m']:02d}"
                for row in excluded.select("y", "m").iter_rows(named=True)
            ],
            "route_persistence_spearman": spearman,
            "route_pairs": persistence_by_carrier.get(carrier, {}).get("pairs"),
            "admitted_pax": float(admitted.get_column("pax").sum()),
        }

    qualified = [name for name, item in carriers.items() if item.get("qualified")]
    admitted_pax = sum(carriers[name]["admitted_pax"] for name in qualified)
    share = admitted_pax / total_pax if total_pax else 0.0
    passed = len(qualified) >= MIN_QUALIFIED_CARRIERS and share >= MIN_DOMESTIC_PAX_SHARE
    result = {
        "question": "Is total checked baggage per paid passenger a defensible target?",
        "period": f"{FIRST_YEAR}-01 to {LAST_YEAR}-12 (2024-2025 and 2023 not read)",
        "criteria": {
            "min_share_of_flights_with_baggage": MIN_FLIGHTS_WITH_BAG,
            "max_shift_relative_to_trailing_market_position": MAX_RELATIVE_SHIFT,
            "min_year_over_year_route_persistence": MIN_ROUTE_PERSISTENCE,
            "min_admitted_months": MIN_ADMITTED_MONTHS,
            "min_qualified_carriers": MIN_QUALIFIED_CARRIERS,
            "min_share_of_domestic_paid_pax": MIN_DOMESTIC_PAX_SHARE,
        },
        "carriers": carriers,
        "qualified_carriers": qualified,
        "share_of_domestic_paid_pax_covered": round(share, 4),
        "verdict": "may_proceed_to_baseline" if passed else "suspend_module_c",
        "remaining_condition": (
            "A model must still beat the same-month-last-year baseline on validation. "
            "If it does not, the module is suspended rather than published."
        ),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "module_c_assessment.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("qualified_carriers", "share_of_domestic_paid_pax_covered", "verdict")
            },
            indent=2,
        )
    )
    for name, item in carriers.items():
        print(
            name,
            {
                key: item.get(key)
                for key in (
                    "qualified",
                    "reasons",
                    "months_admitted",
                    "route_persistence_spearman",
                    "months_excluded",
                )
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
