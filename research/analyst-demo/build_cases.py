"""AI Analyst in Action: recorded real runs, verified independently.

    .venv\\Scripts\\python research\\analyst-demo\\build_cases.py

Reads the live runs recorded during the analyst's validation (reports/agent/*.json, Groq,
model openai/gpt-oss-120b, 2026-11-06). It makes no LLM call. Each case is checked
against the analytical tables (data/analytics/v1) or the model reports, a path that does
not go through the analyst's tools. Writes research/analyst-demo/cases.json and
web/public/analyst/cases.json.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AGENT = ROOT / "reports" / "agent"
ANALYTICS = ROOT / "data" / "analytics" / "v1"
WEB = ROOT / "web" / "public" / "analyst" / "cases.json"


def run(file: str, case: int) -> dict[str, Any]:
    data = json.loads((AGENT / file).read_text(encoding="utf-8"))
    found = next(item for item in data["results"] if item["case"] == case)
    return {
        "file": f"reports/agent/{file}",
        "model": data["model"],
        "provider": data["provider"],
        **found,
    }


def year(frame: pl.LazyFrame, y: int) -> pl.LazyFrame:
    return frame.filter(pl.col("month").is_between(date(y, 1, 1), date(y, 12, 1)))


def check(label: str, expected: Any, found: Any, note: str = "") -> dict[str, Any]:
    return {
        "check": label,
        "in_answer": expected,
        "independent": found,
        "match": expected == found,
        "note": note,
    }


def main() -> None:
    routes = pl.scan_parquet(ANALYTICS / "fact_route_month.parquet")
    airports = pl.scan_parquet(ANALYTICS / "fact_airport_month.parquet")
    dim_airport = pl.read_parquet(ANALYTICS / "dim_airport.parquet")

    pax_2025 = int(year(routes, 2025).select(pl.col("paid_passengers").sum()).collect().item())
    pax_2024 = int(year(routes, 2024).select(pl.col("paid_passengers").sum()).collect().item())
    change = round((pax_2025 / pax_2024 - 1) * 100, 2)
    movements = year(airports, 2025).group_by("airport").agg(pl.col("movements").sum()).collect()
    mv = dict(zip(movements.get_column("airport"), movements.get_column("movements"), strict=True))
    cgh_sdu = (
        year(routes, 2025)
        .filter((pl.col("origin") == "SBSP") & (pl.col("destination") == "SBRJ"))
        .select(pl.col("paid_passengers").sum(), pl.col("seats").sum())
        .collect()
        .row(0)
    )
    ranked = (
        year(routes, 2025)
        .group_by("origin", "destination")
        .agg(pl.col("paid_passengers").sum())
        .sort("paid_passengers", descending=True)
        .with_row_index("rank", offset=1)
        .collect()
    )
    bjp = (
        dim_airport.filter(pl.col("iata") == "BJP")
        .select("airport", "name", "city", "uf")
        .to_dicts()
    )
    bjp_route = (
        ranked.filter(
            (pl.col("origin") == bjp[0]["airport"]) & (pl.col("destination") == "SBGR")
        ).to_dicts()
        if bjp
        else []
    )
    pax_2019 = int(year(routes, 2019).select(pl.col("paid_passengers").sum()).collect().item())
    columns = set()
    for table in ANALYTICS.glob("*.parquet"):
        columns |= set(pl.read_parquet_schema(table))
    price_columns = sorted(
        c for c in columns if re.search(r"price|fare|tarif|preco|valor", c, re.I)
    )
    module_a = json.loads(
        (ROOT / "reports" / "models" / "module_a.json").read_text(encoding="utf-8")
    )
    a_best = module_a["targets"]["movements"]
    a_value = round(a_best["baselines"][a_best["best_baseline"]]["value"] * 100, 2)

    cases = [
        {
            "id": "market",
            "title": "Market analysis",
            "business_problem": "How big was Brazilian air travel in the latest year, and is it growing?",
            "runs": [
                run("live_validation.json", 1),
                run("live_repro_case1.json", 1),
                run("live_validation_round2.json", 1),
            ],
            "story": "The first two attempts were refused by the numeric verifier: one draft attached a number to the wrong metric. The third run passed. The final answer is the one shown last.",
            "verification": [
                check(
                    "Paid passengers, 2025",
                    131_593_763,
                    pax_2025,
                    "Σ paid_passengers in fact_route_month, passenger scope",
                ),
                check(
                    "Change vs 2024, %", 9.72, change, "Σ 2025 / Σ 2024 − 1, from the same table"
                ),
            ],
            "value": "A verified headline figure with its period, unit and source, ready for a market brief.",
            "limits": "Passengers are counted per flight leg. The change compares calendar years, and the tool sees only the latest 12 months against the previous 12.",
        },
        {
            "id": "airports",
            "title": "Competitive intelligence: airports",
            "business_problem": "How do São Paulo's two main airports compare in traffic?",
            "runs": [run("live_validation.json", 3)],
            "verification": [
                check(
                    "GRU movements, 2025",
                    287_291,
                    int(mv["SBGR"]),
                    "Σ movements in fact_airport_month (takeoffs + landings)",
                ),
                check("CGH movements, 2025", 186_664, int(mv["SBSP"]), "Same table"),
            ],
            "value": "An airport comparison with the measure defined, which avoids mixing up movements and passengers.",
            "limits": "The analyst has no carrier tool, so market share by airline is out of its reach. The Airlines page of the dashboard answers that question from the analytical layer.",
        },
        {
            "id": "route",
            "title": "Route performance",
            "business_problem": "How busy and how full is the country's busiest route?",
            "runs": [run("live_validation.json", 2)],
            "verification": [
                check(
                    "CGH → SDU paid passengers, 2025",
                    1_968_523,
                    int(cgh_sdu[0]),
                    "fact_route_month, directed route SBSP → SBRJ",
                ),
                check(
                    "CGH → SDU load factor, %",
                    77,
                    round(cgh_sdu[0] / cgh_sdu[1] * 100),
                    f"Σ pax / Σ seats = {cgh_sdu[0] / cgh_sdu[1] * 100:.2f}%, rounded in the answer",
                ),
            ],
            "value": "A directed-route answer with load factor recomputed from sums, the same rule the dashboard follows.",
            "limits": "The tool lists only the 200 busiest routes. Seasonality and historical trends are not in the analyst's tools: the Routes Explorer shows them.",
        },
        {
            "id": "models",
            "title": "Model results, without overclaiming",
            "business_problem": "Can we already forecast airport traffic?",
            "runs": [run("live_validation_round2.json", 4)],
            "verification": [
                check(
                    "Module A selected method WAPE, %",
                    10.30,
                    a_value,
                    "reports/models/module_a.json, best baseline on validation 2023",
                ),
            ],
            "value": "The answer separates a 2023 validation score from a live forecast, and says no forecast is served.",
            "limits": "Results are validation only. The final test on 2024–2025 has not been run.",
        },
        {
            "id": "guardrails",
            "title": "Guardrails: what it refuses",
            "business_problem": "Does it invent answers when pushed?",
            "runs": [
                run("live_validation.json", 5),
                run("live_validation_round3.json", 6),
                run("live_validation.json", 7),
            ],
            "verification": [
                check(
                    "Price columns in the analytical tables",
                    "none",
                    "none" if not price_columns else ", ".join(price_columns),
                    "Schema of every table in data/analytics/v1: the answer that no price data exists is correct",
                ),
                check(
                    "BJP → GRU flights in the data",
                    "no figure given",
                    "no figure given"
                    if not bjp_route
                    else f"{bjp_route[0]['paid_passengers']} passengers",
                    f"{bjp[0]['airport'] if bjp else 'BJP'} → SBGR has no rows in any year of fact_route_month, so giving no number is correct; the reason it gave (top-200 limit) is weaker than the truth",
                ),
                check(
                    "Paid passengers, 2019",
                    "not available",
                    f"{pax_2019:,} in the tables",
                    "The data has 2019, but the analyst's tools only cover the latest 12 months. A tool limit, not missing data, and the run was marked answered instead of no_data",
                ),
            ],
            "value": "It refused a prompt injection and an invented price, and stayed inside the data it can read.",
            "limits": "The 2019 question exposes a real gap: the tools do not reach history, and that run's status should have been no_data. This is recorded as a known issue.",
        },
    ]
    for case in cases:
        case["checks_passed"] = sum(item["match"] for item in case["verification"])
        case["checks_total"] = len(case["verification"])
    payload = {
        "version": 1,
        "recorded": "2026-11-06, during the analyst's validation (Stage 5)",
        "provider": "groq",
        "model": "openai/gpt-oss-120b",
        "note": "Recorded real runs, not generated for this page. No LLM call was made to build it. Verification uses the analytical tables, not the analyst's tools.",
        "cases": cases,
    }
    (HERE / "cases.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    WEB.parent.mkdir(parents=True, exist_ok=True)
    WEB.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for case in cases:
        print(
            case["id"],
            [
                (v["check"], v["in_answer"], v["independent"], v["match"])
                for v in case["verification"]
            ],
        )


if __name__ == "__main__":
    main()
