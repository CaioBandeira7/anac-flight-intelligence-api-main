"""Cross-artifact checks for the versioned audit, public payload and complete chart catalog."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("key", "module", "target"),
    [
        ("a", "a", "movements"),
        ("b", "b", "load_factor"),
        ("d_pax", "d", "pax"),
        ("d_seats", "d", "seats"),
    ],
)
def test_public_metrics_match_frozen_reports_and_audited_predictions(key, module, target):
    audit = read("research/ml-showcase/results/audit.json")
    report = read(f"reports/models/module_{module}.json")["targets"][target]
    public = read("web/public/ml/showcase.json")["tasks"][key]
    assert audit["status"] == "passed"
    assert audit["failures"] == []
    assert audit["test_period_read"] is False
    assert audit["production_models_refit"] is False
    assert public["lightgbm"] == report["lightgbm"]
    assert public["difference_vs_best_baseline"] == report["difference_vs_best_baseline"]
    assert public["bias"] == report["bias"]
    assert public["lightgbm"]["value"] == pytest.approx(
        audit["tasks"][key]["metrics"]["lightgbm"]["value"]
    )
    assert public["beats_best_baseline"] == report["beats_best_baseline"]
    assert all(row["month"].startswith("2023-") for row in public["monthly"])


def test_catalog_covers_every_report_figure_once_and_web_statistical_views():
    catalog = read("docs/ml/visualization-inventory.json")
    entries = catalog["items"]
    assert len({entry["id"] for entry in entries}) == len(entries)
    figures = {path.stem for path in (ROOT / "research/ml-showcase/figures").glob("*.png")}
    described = {
        entry["id"].removeprefix("paper-") for entry in entries if entry["id"].startswith("paper-")
    }
    assert described == figures
    assert len(figures) == catalog["report_figures"] == 37
    assert catalog["web_charts"] == 26
    assert catalog["web_tables"] == 4 and catalog["web_kpis"] == 16
    assert catalog["registry_panels"] == 7
    for entry in entries:
        assert all(
            entry.get(field)
            for field in [
                "name",
                "location",
                "task",
                "purpose",
                "axes",
                "data",
                "interpretation",
                "conclusion",
                "limits",
            ]
        )


def test_corrected_bias_and_audit_dont_silently_rewrite_legacy_b_result():
    public = read("web/public/ml/showcase.json")["tasks"]["b"]
    audit = read("research/ml-showcase/results/audit.json")["tasks"]["b"]
    assert public["bias"]["value"] > 0
    assert public["seat_weighted_bias"]["value"] < 0
    assert public["seat_weighted_bias"]["value"] == pytest.approx(
        audit["seat_weighted_signed_error"]
    )
    assert len(public["seat_weighted_bias"]["ci95"]) == 2
    assert audit["metrics"]["lightgbm"]["value"] == pytest.approx(0.06058022524963083)


def test_corrected_pdf_is_the_one_published_and_retains_audit_errata():
    report = (ROOT / "research/ml-showcase/REPORT.pdf").read_bytes()
    assert report.startswith(b"%PDF-")
    assert report == (ROOT / "web/public/ml/report.pdf").read_bytes()
    markdown = (ROOT / "research/ml-showcase/REPORT.md").read_text(encoding="utf-8")
    assert "11,689 pax and 11,692 seats" in markdown
    assert "not predictive intervals" in markdown
    assert "Historical relative, unweighted bias" in markdown
