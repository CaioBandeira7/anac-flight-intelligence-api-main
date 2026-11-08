"""Ranking questions ("busiest routes in 2025"), with a scripted model. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from anac.agent.analyst import Analyst
from anac.agent.tools import TOOL_DEFINITIONS, AnalystTools
from anac.serving.export import PayloadStore
from tests.test_agent import Script, text, tool_call
from tests.test_api import AIRPORT, DATA, META

ROUTES = [
    {"origin": "CGH", "destination": "SDU", "passengers": 1968523, "loadFactor": 0.769},
    {"origin": "SDU", "destination": "CGH", "passengers": 1966721, "loadFactor": 0.760},
    {"origin": "BSB", "destination": "CGH", "passengers": 1173202, "loadFactor": 0.802},
]
AIRPORTS = [
    AIRPORT | {"movements": 287291},
    AIRPORT | {"icao": "SBSP", "iata": "CGH", "name": "Congonhas", "movements": 214000},
]


@pytest.fixture
def store(tmp_path: Path) -> PayloadStore:
    data = {**DATA, "routes.json": ROUTES, "airports.json": AIRPORTS}
    for name, content in data.items():
        (tmp_path / name).write_text(json.dumps({"data": content, "meta": META}), encoding="utf-8")
    return PayloadStore(tmp_path)


def test_the_prompt_states_the_covered_period(store: PayloadStore) -> None:
    script = Script(text("There is no data for that."))
    Analyst(script.client(), AnalystTools(store)).ask("Which routes were the busiest in 2025?")
    system = script.requests[0]["messages"][0]["content"]
    assert "The data covers 2025-01 to 2025-12" in system
    assert "Rankings" in system


def test_tool_descriptions_say_how_to_rank() -> None:
    descriptions = {
        item["function"]["name"]: item["function"]["description"] for item in TOOL_DEFINITIONS
    }
    for name in ("search_routes", "search_airports"):
        assert "largest first" in descriptions[name]
        assert "busiest" in descriptions[name]


def test_unfiltered_routes_come_ranked(store: PayloadStore) -> None:
    result = AnalystTools(store).call("search_routes", {"limit": 3})
    passengers = [row["passengers"] for row in result["routes"]]
    assert passengers == sorted(passengers, reverse=True)


def test_busiest_routes_question_is_answered_with_the_ranking(store: PayloadStore) -> None:
    script = Script(
        tool_call("search_routes", {"limit": 3}),
        text(
            "CGH to SDU carried 1,968,523 paid passengers (2025-01 to 2025-12). "
            "SDU to CGH carried 1,966,721 paid passengers (2025-01 to 2025-12). "
            "BSB to CGH carried 1,173,202 paid passengers (2025-01 to 2025-12)."
        ),
    )
    answer = Analyst(script.client(), AnalystTools(store)).ask(
        "Which routes were the busiest in 2025?"
    )
    assert answer.status == "answered"
    assert [source["endpoint"] for source in answer.sources] == ["/v2/routes"]


def test_a_ranking_with_a_wrong_figure_is_still_refused(store: PayloadStore) -> None:
    wrong = text("CGH to SDU carried 2,500,000 paid passengers (2025-01 to 2025-12).")
    script = Script(tool_call("search_routes", {"limit": 3}), wrong, wrong)
    answer = Analyst(script.client(), AnalystTools(store)).ask("Busiest routes in 2025?")
    assert answer.status == "unverified"


def test_busiest_airports_question_is_answered(store: PayloadStore) -> None:
    script = Script(
        tool_call("search_airports", {"limit": 2}),
        text(
            "GRU had 287,291 movements (2025-01 to 2025-12). CGH had 214,000 movements (2025-01 to 2025-12)."
        ),
    )
    answer = Analyst(script.client(), AnalystTools(store)).ask("Busiest airports in 2025?")
    assert answer.status == "answered"
