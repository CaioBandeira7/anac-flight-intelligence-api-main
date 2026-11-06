"""Essential endpoint checks, on synthetic payloads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from anac.api.app import create_app
from anac.serving.export import ENDPOINTS

META = {"source": "API", "isDemo": False, "generatedAt": "2026-11-06T00:00:00+00:00", "note": "n"}
AIRPORT = {
    "icao": "SBGR", "iata": "GRU", "name": "Guarulhos", "city": "São Paulo", "uf": "SP",
    "lat": -23.4, "lon": -46.4, "movements": 10,
}  # fmt: skip
ROUTE = {"origin": "GRU", "destination": "GIG", "passengers": 5, "loadFactor": 0.8}
DATA: dict[str, object] = {
    "health.json": {"ok": True, "version": "flights"},
    "overview.json": {
        "period": {"from": "2025-01", "to": "2025-12"},
        "kpis": [{"id": "flights", "label": "Flights", "value": 3, "unit": "count", "delta": None, "trend": [1.0]}],
        "monthly": [{"month": "2025-01", "passengers": 5, "flights": 3}],
        "topRoutes": [ROUTE],
        "topAirports": [AIRPORT],
    },
    "airports.json": [AIRPORT],
    "routes.json": [ROUTE],
    "models.json": [
        {
            "id": "m", "name": "n", "task": "t", "pipeline": "p", "status": "available",
            "metrics": [{"name": "WAPE", "value": 0.1, "evaluatedOn": "validation"}], "lastTrainedAt": None,
        }
    ],
    "datasets.json": [{"name": "flights", "description": "d", "approxSize": "1", "status": "ready"}],
    "modules.json": [
        {
            "module": "a", "title": "t", "unit": ["airport"], "targets": {"movements": "m"},
            "primary_metric": "WAPE",
            "features": [{"name": "x", "type": "Float64", "source": "history", "description": "d"}],
        }
    ],
    "analyst_catalog.json": {
        "version": 1, "dataset": "flights", "tools": [{"name": "t"}],
        "facts_that_must_accompany_answers": ["f"], "must_not_claim": ["c"],
    },
}  # fmt: skip


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    for name, data in DATA.items():
        (tmp_path / name).write_text(json.dumps({"data": data, "meta": META}), encoding="utf-8")
    return TestClient(create_app(tmp_path))


@pytest.mark.parametrize("endpoint", sorted(ENDPOINTS))
def test_every_endpoint_serves_its_payload_with_provenance(
    client: TestClient, endpoint: str
) -> None:
    response = client.get(endpoint)
    assert response.status_code == 200
    assert response.json()["meta"]["isDemo"] is False


def test_period_keeps_the_frontend_field_names(client: TestClient) -> None:
    assert client.get("/v2/overview").json()["data"]["period"] == {
        "from": "2025-01",
        "to": "2025-12",
    }


def test_api_is_read_only_and_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    analytics = {path for path in paths if path.startswith("/v2/analytics/")}
    assert analytics == {
        "/v2/analytics/routes",
        "/v2/analytics/routes/monthly",
        "/v2/analytics/airports",
        "/v2/analytics/airports/monthly",
        "/v2/analytics/coverage",
    }
    assert set(paths) == {*ENDPOINTS, "/v2/analyst/status", "/v2/analyst/chat", *analytics}
    # The chat is the only POST, and it cannot write anything.
    assert all(
        set(methods) == {"get"} for path, methods in paths.items() if path != "/v2/analyst/chat"
    )
    assert set(paths["/v2/analyst/chat"]) == {"post"}
    assert client.post("/v2/overview").status_code == 405
    assert client.get("/docs").status_code == 200


def test_missing_payload_is_reported_not_invented(tmp_path: Path) -> None:
    response = TestClient(create_app(tmp_path)).get("/v2/overview")
    assert response.status_code == 503
    assert "exported" in response.json()["detail"]


def test_a_payload_breaking_the_contract_is_not_served(client: TestClient, tmp_path: Path) -> None:
    bad = {"data": [{"origin": "GRU"}], "meta": META}
    (tmp_path / "routes.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="validation error"):
        client.get("/v2/routes")


def test_real_payloads_match_the_contract_when_exported() -> None:
    directory = Path("data/serving/v1")
    if not (directory / "overview.json").exists():
        pytest.skip("payloads not exported")
    real = TestClient(create_app(directory))
    for endpoint in ENDPOINTS:
        assert real.get(endpoint).status_code == 200, endpoint
