"""Payloads must match the frontend contract and must never invent a metric."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from anac.config import IngestionConfig
from anac.features.config import FeatureConfig, TimeConfig
from anac.ingestion.pipeline import run_ingestion
from anac.serving.export import ENDPOINTS, PayloadStore, build_models, export_all, load_airports
from tests.conftest import csv_line, write_csv

AIRPORTS = (
    "Atualizado em: 2026-11-01\n"
    "Código OACI;CIAD;Nome;Município;UF;Município Servido;UF Servido;LATGEOPOINT;LONGEOPOINT\n"
    "SBCT;PR0001;Afonso Pena;SJP;Paraná;Curitiba;Paraná;-25.53;-49.17\n"
    "SBGR;SP0001;Guarulhos;Guarulhos;São Paulo;São Paulo;São Paulo;-23.43;-46.47\n"
)


def rows() -> list[str]:
    lines = []
    for index, (month, year, number) in enumerate(
        [("2024-06", "2024", "6"), ("2025-06", "2025", "6"), ("2025-07", "2025", "7")] * 3
    ):
        day = f"{month}-{index + 1:02d}"
        lines.append(
            csv_line(
                id_basica=f"{index + 1}.0",
                dt_referencia=day,
                dt_partida_real=day,
                dt_chegada_real=day,
                nr_ano_referencia=year,
                nr_mes_referencia=number,
                sg_iata_origem="CWB",
                sg_iata_destino="GRU",
                sg_uf_origem="PR",
                sg_uf_destino="SP",
            )
        )
    return lines


@pytest.fixture
def exported(tmp_path: Path) -> Path:
    ingestion = IngestionConfig(
        source_csv=write_csv(tmp_path / "s.csv", rows()),
        full_output_root=tmp_path / "data",
        full_report_dir=tmp_path / "r",
        chunk_size_mb=1,
        memory_min_available_gb=0.0,
    )
    run_ingestion(ingestion, "full", confirm_full=True)
    airports = tmp_path / "airports.csv"
    airports.write_text(AIRPORTS, encoding="utf-8")
    cfg = FeatureConfig(
        processed=tmp_path / "data" / "processed",
        output=tmp_path / "features",
        reports=tmp_path / "baselines",
        time=TimeConfig(),
    )
    output = tmp_path / "serving"
    export_all(cfg, airports, output)
    return output


def test_every_endpoint_has_a_labelled_payload(exported: Path) -> None:
    store = PayloadStore(exported)
    assert set(store.endpoints()) == set(ENDPOINTS)
    for endpoint in store.endpoints():
        payload = store.get(endpoint)
        assert payload["meta"]["source"] == "API"
        assert payload["meta"]["isDemo"] is False
        assert "generatedAt" in payload["meta"]
    with pytest.raises(KeyError):
        store.get("/v2/unknown")


def test_overview_matches_the_frontend_contract(exported: Path) -> None:
    data = PayloadStore(exported).get("/v2/overview")["data"]
    assert set(data) == {"period", "kpis", "monthly", "topRoutes", "topAirports"}
    assert data["period"] == {"from": "2024-08", "to": "2025-07"}
    kpis = {kpi["id"]: kpi for kpi in data["kpis"]}
    assert set(kpis) == {"flights", "passengers", "load_factor", "active_routes"}
    assert kpis["passengers"]["value"] == 75 * 6
    assert kpis["load_factor"]["unit"] == "ratio"
    assert kpis["load_factor"]["value"] == pytest.approx(75 / 118)
    assert kpis["flights"]["delta"] == pytest.approx(1.0)
    assert set(data["monthly"][0]) == {"month", "passengers", "flights"}
    assert set(data["topRoutes"][0]) == {"origin", "destination", "passengers", "loadFactor"}
    assert data["topRoutes"][0]["origin"] == "CWB"
    assert set(data["topAirports"][0]) == {
        "icao",
        "iata",
        "name",
        "city",
        "uf",
        "lat",
        "lon",
        "movements",
    }


def test_absent_months_are_disclosed(exported: Path) -> None:
    catalog = PayloadStore(exported).get("/v2/analyst/catalog")["data"]
    text = " ".join(catalog["facts_that_must_accompany_answers"])
    assert "2024-07" in text
    assert any("fares" in item for item in catalog["must_not_claim"])
    assert "2024-07" in PayloadStore(exported).get("/v2/overview")["meta"]["note"]


def test_no_metric_is_shown_without_a_report(exported: Path) -> None:
    for card in PayloadStore(exported).get("/v2/models")["data"]:
        assert card["status"] == "not_trained"
        assert card["metrics"] is None


def test_baseline_cards_name_the_split_and_only_real_values(tmp_path: Path) -> None:
    section = {"value": 0.12, "ci95": [0.1, 0.14]}
    report = {
        "evaluated_at": "2026-11-06T00:00:00+00:00",
        "evaluated_on": "validation (2023-01 to 2023-12)",
        "results": {"pred_seasonal_trend": {"all": {"wape": section, "mase": {"value": None}}}},
    }
    (tmp_path / "module_a.json").write_text(json.dumps(report), encoding="utf-8")
    cards = {card["id"]: card for card in build_models(tmp_path)}
    assert cards["baseline-a"]["status"] == "available"
    assert [metric["name"].split(",")[0] for metric in cards["baseline-a"]["metrics"]] == ["WAPE"]
    assert cards["baseline-a"]["metrics"][0]["evaluatedOn"].startswith("validation")
    assert cards["module-c"]["metrics"] is None


def test_airport_list_is_read_with_coordinates(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_text(AIRPORTS, encoding="utf-8")
    frame = load_airports(path)
    assert frame.height == 2
    assert frame.filter(pl.col("icao") == "SBGR").get_column("lat")[0] == -23.43


def _model_report(beats: bool) -> dict[str, object]:
    return {
        "evaluated_on": "validation (2023-01 to 2023-12)",
        "trained_at": "2026-11-06T00:00:00+00:00",
        "targets": {
            "movements": {
                "metric": "WAPE",
                "lightgbm": {"value": 0.10},
                "baselines": {"pred_recent_weekday": {"value": 0.11}},
                "best_baseline": "pred_recent_weekday",
                "difference_vs_best_baseline": {"value": -0.01, "ci95": [-0.02, 0.01]},
                "beats_best_baseline": beats,
            }
        },
    }


@pytest.mark.parametrize("beats", [True, False])
def test_only_a_model_that_beat_its_baseline_is_selected(tmp_path: Path, beats: bool) -> None:
    reports = tmp_path / "baselines"
    reports.mkdir()
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "module_a.json").write_text(
        json.dumps(_model_report(beats)), encoding="utf-8"
    )
    cards = {card["id"]: card for card in build_models(reports)}
    assert cards["lightgbm-a"]["selected"] is beats
    assert cards["baseline-a"]["selected"] is not beats
    assert cards["baseline-a"]["metrics"][0]["value"] == 0.11
    assert cards["baseline-a"]["method"] == "Baseline: same weekday, recent 8 weeks"
    assert cards["lightgbm-a"]["metrics"][0]["evaluatedOn"].startswith("validation")
