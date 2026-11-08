"""Smoke test on real data: a few small blocks of the CSV, written to a temporary folder."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from anac.config import IngestionConfig
from anac.ingestion.pipeline import run_ingestion

REAL_CSV = Path("data/raw/anac_brazil.csv")


@pytest.mark.real_data
@pytest.mark.skipif(not REAL_CSV.exists(), reason="the real CSV is not versioned")
def test_real_blocks_parse_and_reconcile(tmp_path: Path) -> None:
    cfg = IngestionConfig(
        source_csv=REAL_CSV,
        sample_blocks=3,
        sample_block_mb=4,
        sample_seed=1,
        memory_min_available_gb=0.0,  # independent of how busy this machine is
    )
    report = run_ingestion(cfg, "sample", output_root=tmp_path / "run")

    totals = report["reconciliation"]
    assert totals["lines_read"] > 0
    assert totals["lines_read"] == (
        totals["chunk_rejected_rows"] + totals["duplicate_ids_removed"] + totals["rows_published"]
    )
    flights = pl.scan_parquet(tmp_path / "run" / "processed" / "flights" / "**" / "*.parquet")
    summary = flights.select(
        pl.col("nr_horas_voadas").is_not_null().mean().alias("hours_present"),
        pl.col("is_international").mean().alias("international"),
        pl.col("dt_referencia").dt.year().min().alias("min_year"),
    ).collect()
    # Decimal commas must really parse. The original rule marked 100% as international.
    assert summary["hours_present"][0] > 0.9
    assert summary["international"][0] < 0.9
    assert summary["min_year"][0] >= 2000
