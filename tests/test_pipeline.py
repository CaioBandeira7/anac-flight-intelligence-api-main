"""End-to-end behaviour on synthetic files: partitioning, accounting, safety, resumption."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from pathlib import Path

import duckdb
import polars as pl
import pytest

from anac.cli import main
from anac.config import IngestionConfig
from anac.ingestion.compaction import OverwriteRefused
from anac.ingestion.contract import SELECTED_NAMES
from anac.ingestion.pipeline import (
    FullRunNotConfirmed,
    MemoryBudgetExceeded,
    PlanMismatch,
    RunLayout,
    run_ingestion,
    run_status,
)
from tests.conftest import csv_line, many_rows, write_csv

MakeConfig = Callable[..., IngestionConfig]


def run_full(cfg: IngestionConfig, **kwargs: object) -> dict[str, object]:
    return run_ingestion(cfg, "full", confirm_full=True, **kwargs)  # type: ignore[arg-type]


def flights(root: Path) -> pl.DataFrame:
    return pl.scan_parquet(root / "processed" / "flights" / "**" / "*.parquet").collect()


def small_chunks(cfg: IngestionConfig) -> IngestionConfig:
    return dataclasses.replace(cfg, chunk_size_mb=0.01)  # about 10 KB per chunk


def tree_state(root: Path) -> dict[str, int]:
    """Modification times of the data files. The report is derived and may be rewritten."""
    return {
        str(path): path.stat().st_mtime_ns
        for folder in (root / "interim", root / "processed")
        for path in folder.rglob("*.parquet")
    }


def test_full_run_refuses_without_confirmation(tmp_path: Path, make_config: MakeConfig) -> None:
    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(3)))
    with pytest.raises(FullRunNotConfirmed):
        run_ingestion(cfg, "full")
    assert not cfg.full_output_root.exists()
    assert main(["--config", "configs/ingestion.toml", "status", "--output-root",
                 str(tmp_path / "none")]) == 0  # fmt: skip


def test_partitions_are_real_periods_and_rows_reconcile(
    tmp_path: Path, make_config: MakeConfig
) -> None:
    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(30)))
    report = run_full(cfg)
    months = sorted(
        path.relative_to(cfg.full_output_root / "processed" / "flights").parts[:2]
        for path in (cfg.full_output_root / "processed" / "flights").rglob("*.parquet")
    )
    assert months == [
        ("year=2013", "month=08"),
        ("year=2013", "month=09"),
        ("year=2020", "month=01"),
    ]
    assert report["reconciliation"] == {  # type: ignore[index]
        "lines_read": 30,
        "chunk_valid_rows": 30,
        "chunk_rejected_rows": 0,
        "duplicate_ids_removed": 0,
        "rows_published": 30,
    }


def test_bad_rows_are_accounted_and_quarantined(tmp_path: Path, make_config: MakeConfig) -> None:
    lines = [
        *many_rows(10),
        csv_line(id_basica="", nr_voo="semid"),
        csv_line(id_basica="900.0", dt_referencia="1990-01-01"),
        "linha,quebrada",
    ]
    cfg = make_config(write_csv(tmp_path / "a.csv", lines))
    report = run_full(cfg)
    assert report["reject_reasons"] == {  # type: ignore[index]
        "invalid_id_basica": 1,
        "reference_date_out_of_range": 1,
        "wrong_field_count": 1,
    }
    totals = report["reconciliation"]  # type: ignore[index]
    assert totals["lines_read"] == 13
    assert totals["rows_published"] == 10
    rejects = pl.read_parquet(cfg.full_output_root / "interim/ingestion/chunks/*/rejects.parquet")
    assert rejects.height == 3
    assert "linha,quebrada" in rejects["raw_record"].to_list()


def test_repeated_id_is_removed_and_reported(tmp_path: Path, make_config: MakeConfig) -> None:
    lines = [csv_line(id_basica="7.0", nr_voo="1"), csv_line(id_basica="7.0", nr_voo="2")]
    cfg = make_config(write_csv(tmp_path / "a.csv", lines))
    report = run_full(cfg)
    frame = flights(cfg.full_output_root)
    assert frame["nr_voo"].to_list() == ["1"]
    assert report["reconciliation"]["duplicate_ids_removed"] == 1  # type: ignore[index]
    assert report["reject_reasons"] == {"duplicate_id_basica": 1}  # type: ignore[index]
    rejected = pl.read_parquet(cfg.full_output_root / "processed/flights_rejects/*.parquet")
    assert rejected["reason"].to_list() == ["duplicate_id_basica"]


def test_same_leg_under_new_id_is_flagged_not_deleted(
    tmp_path: Path, make_config: MakeConfig
) -> None:
    lines = [
        csv_line(id_basica="1.0"),
        csv_line(id_basica="2.0"),
        csv_line(id_basica="3.0", nr_passag_pagos="80.0"),
        csv_line(id_basica="4.0", dt_partida_real="", hr_partida_real=""),
        csv_line(id_basica="5.0", dt_partida_real="", hr_partida_real=""),
    ]
    cfg = make_config(write_csv(tmp_path / "a.csv", lines))
    run_full(cfg)
    frame = flights(cfg.full_output_root).sort("id_basica")
    assert frame.height == 5
    # Only an exact twin with a known departure counts: id 2 repeats id 1.
    assert frame["dq_duplicate_record"].to_list() == [False, True, False, False, False]


def test_duckdb_reads_the_same_data_and_types(tmp_path: Path, make_config: MakeConfig) -> None:
    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(30)))
    run_full(cfg)
    frame = flights(cfg.full_output_root)
    pattern = (cfg.full_output_root / "processed/flights/*/*/*.parquet").as_posix()
    with duckdb.connect() as connection:
        count, total, year = connection.execute(
            f"SELECT count(*), sum(nr_passag_pagos), min(year) "
            f"FROM read_parquet('{pattern}', hive_partitioning=true)"
        ).fetchone()  # type: ignore[misc]
    assert count == frame.height == 30
    assert total == frame["nr_passag_pagos"].sum()
    assert year == 2013
    assert frame.schema["dt_referencia"] == pl.Date
    assert frame.schema["nr_horas_voadas"] == pl.Float64
    assert frame.schema["nr_assentos_ofertados"] == pl.Int32
    assert set(SELECTED_NAMES) <= set(frame.columns)


def test_second_run_is_a_no_op(tmp_path: Path, make_config: MakeConfig) -> None:
    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(30)))
    first = run_full(cfg)
    before = tree_state(cfg.full_output_root)
    second = run_full(cfg)
    assert tree_state(cfg.full_output_root) == before
    assert first["reconciliation"] == second["reconciliation"]
    assert first["by_year"] == second["by_year"]
    assert before
    assert second["performance"]["bytes_processed_this_invocation"] == 0  # type: ignore[index]


def test_crash_during_chunks_resumes_to_the_same_result(
    tmp_path: Path, make_config: MakeConfig
) -> None:
    source = write_csv(tmp_path / "a.csv", many_rows(200))
    clean_root = tmp_path / "clean"
    crash_root = tmp_path / "crash"
    cfg = small_chunks(make_config(source))
    clean = run_full(cfg, output_root=clean_root, report_dir=clean_root / "r")

    calls: list[int] = []

    def crash(chunk_id: int) -> None:
        calls.append(chunk_id)
        if len(calls) == 2:
            raise KeyboardInterrupt

    layout = RunLayout.for_run(crash_root, crash_root / "r")
    with pytest.raises(KeyboardInterrupt):
        run_full(cfg, output_root=crash_root, report_dir=crash_root / "r", after_chunk=crash)
    assert not (crash_root / "processed").exists()
    assert run_status(cfg, crash_root)["state"] == "in_progress"

    # An interrupted write leaves a temporary directory, which must never count as done.
    stale = layout.chunks / "chunk=000099.tmp-1"
    stale.mkdir(parents=True)
    (stale / "stats.json").write_text("{}", encoding="utf-8")

    processed: list[int] = []
    resumed = run_full(
        cfg, output_root=crash_root, report_dir=crash_root / "r", after_chunk=processed.append
    )
    assert not stale.exists()
    assert resumed["reconciliation"] == clean["reconciliation"]
    assert run_status(cfg, crash_root)["state"] == "finished"
    columns = [c for c in flights(clean_root).columns if c != "_chunk_id"]
    left = flights(clean_root).select(columns).sort("id_basica")
    right = flights(crash_root).select(columns).sort("id_basica")
    assert left.equals(right)


def test_crash_during_compaction_resumes(
    tmp_path: Path, make_config: MakeConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(30)))
    from anac.ingestion import pipeline

    original = pipeline.compact_period
    calls = {"count": 0}

    def fail_on_second(*args: object, **kwargs: object) -> object:
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("disk full (simulated)")
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(pipeline, "compact_period", fail_on_second)
    with pytest.raises(OSError, match="simulated"):
        run_full(cfg)
    assert not (cfg.full_output_root / "processed" / "_SUCCESS.json").exists()

    monkeypatch.setattr(pipeline, "compact_period", original)
    assert run_full(cfg)["reconciliation"]["rows_published"] == 30  # type: ignore[index]
    assert (cfg.full_output_root / "processed" / "_SUCCESS.json").exists()


def test_changed_source_is_refused(tmp_path: Path, make_config: MakeConfig) -> None:
    source = write_csv(tmp_path / "a.csv", many_rows(10))
    cfg = make_config(source)
    run_full(cfg)
    write_csv(source, many_rows(11))
    with pytest.raises(PlanMismatch, match="source CSV changed"):
        run_full(cfg)


def test_changed_rules_are_refused(tmp_path: Path, make_config: MakeConfig) -> None:
    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(10)))
    run_full(cfg)
    stricter = dataclasses.replace(cfg, rules=dataclasses.replace(cfg.rules, max_flight_hours=10.0))
    with pytest.raises(PlanMismatch, match="configuration changed"):
        run_full(stricter)


def test_existing_month_is_never_overwritten(tmp_path: Path, make_config: MakeConfig) -> None:
    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(30)))
    target = cfg.full_output_root / "processed/flights/year=2013/month=08/data.parquet"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"precious result from elsewhere")
    with pytest.raises(OverwriteRefused):
        run_full(cfg)
    assert target.read_bytes() == b"precious result from elsewhere"


def test_altered_output_is_detected(tmp_path: Path, make_config: MakeConfig) -> None:
    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(30)))
    run_full(cfg)
    target = cfg.full_output_root / "processed/flights/year=2013/month=08/data.parquet"
    target.write_bytes(target.read_bytes() + b"x")
    with pytest.raises(OverwriteRefused):
        run_full(cfg)


def test_source_csv_is_never_modified(tmp_path: Path, make_config: MakeConfig) -> None:
    source = write_csv(tmp_path / "a.csv", many_rows(30))
    before = (source.read_bytes(), source.stat().st_mtime_ns)
    run_full(make_config(source))
    assert (source.read_bytes(), source.stat().st_mtime_ns) == before


def test_limit_chunks_publishes_nothing_final(tmp_path: Path, make_config: MakeConfig) -> None:
    cfg = small_chunks(make_config(write_csv(tmp_path / "a.csv", many_rows(100))))
    result = run_full(cfg, limit_chunks=1)
    assert result["status"] == "partial"
    assert result["chunks_done"] == 1
    assert not (cfg.full_output_root / "processed" / "flights").exists()


def test_sample_mode_stays_out_of_full_directories(tmp_path: Path, make_config: MakeConfig) -> None:
    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(9_000)))
    report = run_ingestion(cfg, "sample")
    assert report["mode"] == "sample"
    assert report["scope_warning"]
    assert report["coverage"]["fraction_of_file"] < 1
    totals = report["reconciliation"]
    assert totals["lines_read"] == totals["rows_published"] > 0
    assert not cfg.full_output_root.exists()
    run_root = cfg.sample_output_root / "blocks2_mb1_seed42"
    assert (run_root / "processed" / "_SUCCESS.json").exists()
    assert (run_root / "reports" / "quality_report.md").exists()


def test_quality_report_files_are_written(tmp_path: Path, make_config: MakeConfig) -> None:
    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(30)))
    run_full(cfg)
    report_dir = cfg.full_report_dir
    assert (report_dir / "quality_report.json").exists()
    markdown = (report_dir / "quality_report.md").read_text(encoding="utf-8")
    assert "Reconciliation" in markdown
    periods = pl.read_parquet(report_dir / "quality_by_period.parquet")
    assert periods.height == 3


@pytest.mark.parametrize(
    "limits", [{"memory_abort_gb": 0.0}, {"memory_min_available_gb": 1e9}], ids=["rss", "system"]
)
def test_memory_limits_stop_the_run_and_it_resumes(
    tmp_path: Path, make_config: MakeConfig, limits: dict[str, float]
) -> None:
    source = write_csv(tmp_path / "a.csv", many_rows(100))
    cfg = small_chunks(make_config(source))
    with pytest.raises(MemoryBudgetExceeded):
        run_full(dataclasses.replace(cfg, **limits))
    assert not (cfg.full_output_root / "processed" / "_SUCCESS.json").exists()
    # Memory limits do not change the output, so raising them must not invalidate the work.
    assert run_full(cfg)["reconciliation"]["rows_published"] == 100  # type: ignore[index]


def test_memory_limit_is_enforced_during_compaction(
    tmp_path: Path, make_config: MakeConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    from anac.ingestion import pipeline

    cfg = make_config(write_csv(tmp_path / "a.csv", many_rows(30)))
    calls = {"count": 0}

    def fail_after_chunk(_cfg: object, _memory: object) -> None:
        calls["count"] += 1
        if calls["count"] == 3:  # one chunk check, then the second month
            raise MemoryBudgetExceeded("simulated")

    monkeypatch.setattr(pipeline, "check_memory", fail_after_chunk)
    with pytest.raises(MemoryBudgetExceeded):
        run_full(cfg)
    assert not (cfg.full_output_root / "processed" / "_SUCCESS.json").exists()
    monkeypatch.undo()
    assert run_full(cfg)["reconciliation"]["rows_published"] == 30  # type: ignore[index]
