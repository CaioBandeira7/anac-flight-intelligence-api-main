"""Supplement gates, on synthetic ZIPs. The official files themselves have not been seen yet."""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import polars as pl
import pytest

from anac.ingestion.contract import SOURCE_COLUMNS, SchemaDriftError
from anac.ingestion.reference import compare, monthly_totals, reference_totals
from anac.ingestion.supplements import (
    SOURCE_BASE,
    SOURCE_ZIP,
    VERSION,
    Role,
    SupplementConfig,
    SupplementGateError,
    SupplementSpec,
    gate_control,
    publish,
    publish_evaluation,
    read_official_zip,
    supplement_status,
    validate_month,
)
from tests.conftest import csv_line, write_csv

GAP = SupplementSpec("2018-07", Role.GAP)
CONTROL = SupplementSpec("2018-06", Role.CONTROL)


def month_rows(month: str, first_id: int, count: int) -> list[str]:
    year, number = month.split("-")
    return [
        csv_line(
            id_basica=f"{first_id + index}.0",
            nr_voo=str(1000 + index),
            dt_referencia=f"{month}-{index % 28 + 1:02d}",
            dt_partida_real=f"{month}-{index % 28 + 1:02d}",
            dt_chegada_real=f"{month}-{index % 28 + 1:02d}",
            nr_ano_referencia=year,
            nr_mes_referencia=str(int(number)),
        )
        for index in range(count)
    ]


def zip_file(
    path: Path,
    rows: list[str],
    *,
    separator: str = ",",
    encoding: str = "utf-8",
    preface: bool = False,
    upper: bool = False,
    drop: tuple[str, ...] = (),
) -> Path:
    """Write rows the way an export could: other separator, encoding, header case or preface."""
    parsed = [next(csv.reader([row])) for row in rows]
    buffer = io.StringIO()
    if preface:
        buffer.write("Atualizado em: 2026-11-06\n")
    writer = csv.writer(buffer, delimiter=separator, lineterminator="\n")
    keep = [index for index, name in enumerate(SOURCE_COLUMNS) if name not in drop]
    header = [SOURCE_COLUMNS[index] for index in keep]
    writer.writerow([name.upper() for name in header] if upper else header)
    for row in parsed:
        writer.writerow([row[index] for index in keep])
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(path.stem + ".csv", buffer.getvalue().encode(encoding))
    return path


def base_dataset(root: Path, rows: list[str]) -> Path:
    """Publish a small `flights/` through the real ingestion, so schemas match."""
    from anac.config import IngestionConfig
    from anac.ingestion.pipeline import run_ingestion

    source = write_csv(root / "base.csv", rows)
    cfg = IngestionConfig(
        source_csv=source,
        full_output_root=root / "data",
        full_report_dir=root / "reports",
        chunk_size_mb=1,
        memory_min_available_gb=0.0,
    )
    run_ingestion(cfg, "full", confirm_full=True)
    return root / "data" / "processed"


def reference_csv(path: Path, flights: pl.LazyFrame, extra: list[str] | None = None) -> Path:
    """An aggregate matching the given flights, in ANAC's layout."""
    totals = monthly_totals(flights)
    lines = [
        "Atualizado em: 2026-11-06",
        '"EMPRESA_SIGLA";"ANO";"MES";"PASSAGEIROS_PAGOS";"ASK";"RPK";"DECOLAGENS";"ASSENTOS"',
    ]
    for row in totals.iter_rows(named=True):
        lines.append(
            f'"{row["carrier"]}";"{row["year"]}";"{row["month"]}";"{row["paid_pax"]:.0f}";'
            f'"{row["ask"]:.0f}";"{row["rpk"]:.0f}";"{row["takeoffs"]:.0f}";"{row["seats"]:.0f}"'
        )
    lines.extend(extra or [])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def config(tmp_path: Path, reference: Path) -> SupplementConfig:
    return SupplementConfig(
        directory=tmp_path / "supplements",
        reference_csv=reference,
        report=tmp_path / "report.json",
        specs=(GAP, CONTROL),
    )


def ready(tmp_path: Path) -> tuple[SupplementConfig, Path]:
    control_rows = month_rows("2018-06", 1, 30)
    gap_rows = month_rows("2018-07", 1000, 20)
    processed = base_dataset(tmp_path, [*control_rows, *month_rows("2018-08", 500, 10)])
    directory = tmp_path / "supplements"
    directory.mkdir()
    zip_file(directory / CONTROL.filename, control_rows)
    zip_file(directory / GAP.filename, gap_rows)
    frame_source = tmp_path / "all.csv"
    write_csv(frame_source, [*control_rows, *gap_rows])
    full = pl.DataFrame(
        {"carrier": ["AZU"], "year": [2018], "month": [7]},
    )
    assert full.height == 1
    gap_lazy = validate_month(
        GAP, directory / GAP.filename, config(tmp_path, tmp_path / "x"), 1
    ).valid.lazy()
    reference = reference_csv(tmp_path / "reference.csv", gap_lazy)
    return config(tmp_path, reference), processed


def test_status_names_exact_files_and_urls(tmp_path: Path) -> None:
    status = supplement_status(config(tmp_path, tmp_path / "r"))
    assert status["ready_to_publish"] is False
    assert status["required_missing"] == ["basica2018-07.zip", "basica2018-06.zip"]
    assert status["files"][0]["url"].endswith("/basica/2018/basica2018-07.zip")


@pytest.mark.parametrize(
    "layout",
    [
        {},
        {"separator": ";"},
        {"separator": ";", "encoding": "cp1252"},
        {"preface": True},
        {"upper": True},
        {"drop": ("nr_chave", "dt_sistema")},
    ],
    ids=["plain", "semicolon", "cp1252", "preface", "uppercase", "unused_columns_absent"],
)
def test_known_layout_variations_are_normalised(tmp_path: Path, layout: dict[str, object]) -> None:
    path = zip_file(tmp_path / GAP.filename, month_rows("2018-07", 1, 5), **layout)  # type: ignore[arg-type]
    frame, info = read_official_zip(path)
    assert tuple(frame.columns) == SOURCE_COLUMNS
    assert frame.get_column("nm_empresa")[0] == "AZUL LINHAS AÉREAS BRASILEIRAS S/A"
    assert frame.get_column("nr_horas_voadas")[0] == "1,45"
    assert info["rows"] == 5
    month = validate_month(GAP, path, config(tmp_path, tmp_path / "r"), 1)
    assert month.valid.height == 5
    assert month.valid.get_column("nr_horas_voadas")[0] == 1.45


def test_a_missing_contract_column_stops_everything(tmp_path: Path) -> None:
    path = zip_file(tmp_path / GAP.filename, month_rows("2018-07", 1, 5), drop=("nr_passag_pagos",))
    with pytest.raises(SchemaDriftError, match="nr_passag_pagos"):
        read_official_zip(path)


def test_rows_from_another_month_fail_the_granularity_gate(tmp_path: Path) -> None:
    path = zip_file(tmp_path / GAP.filename, month_rows("2018-06", 1, 5))
    with pytest.raises(SupplementGateError, match="are in 2018-07"):
        validate_month(GAP, path, config(tmp_path, tmp_path / "r"), 1)


def test_repeated_ids_fail_the_granularity_gate(tmp_path: Path) -> None:
    rows = month_rows("2018-07", 1, 5)
    path = zip_file(tmp_path / GAP.filename, [*rows, rows[0]])
    with pytest.raises(SupplementGateError, match="repeated"):
        validate_month(GAP, path, config(tmp_path, tmp_path / "r"), 1)


def test_control_month_must_match_row_by_row(tmp_path: Path) -> None:
    rows = month_rows("2018-06", 1, 30)
    processed = base_dataset(tmp_path, rows)
    changed = [row.replace('"1,45"', '"1,45"').replace(",75.0,", ",70.0,") for row in rows]
    path = zip_file(tmp_path / CONTROL.filename, changed)
    cfg = config(tmp_path, tmp_path / "r")
    month = validate_month(CONTROL, path, cfg, 1)
    with pytest.raises(SupplementGateError, match="does not match"):
        gate_control(month, processed / "flights", cfg)


def test_publish_builds_a_new_version_and_touches_nothing_else(tmp_path: Path) -> None:
    cfg, processed = ready(tmp_path)
    base_files = {p: p.stat().st_mtime_ns for p in (processed / "flights").rglob("*.parquet")}
    report = publish(cfg, processed, tmp_path / "interim")
    assert report["status"] == "published"
    assert report["rows_by_source"] == {SOURCE_BASE: 40, SOURCE_ZIP: 20}
    assert base_files == {
        p: p.stat().st_mtime_ns for p in (processed / "flights").rglob("*.parquet")
    }
    published = pl.scan_parquet(
        (processed / VERSION / "*" / "*" / "*.parquet").as_posix(), hive_partitioning=False
    ).collect()
    assert published.height == 60
    months = (
        published.select(pl.col("dt_referencia").dt.strftime("%Y-%m").unique())
        .to_series()
        .to_list()
    )
    assert sorted(months) == ["2018-06", "2018-07", "2018-08"]
    assert "dq_duplicate_record" in published.columns
    assert set(published.get_column("_source").unique()) == {SOURCE_BASE, SOURCE_ZIP}
    with pytest.raises(SupplementGateError, match="already exists"):
        publish(cfg, processed, tmp_path / "interim")


def test_publish_refuses_while_files_are_missing(tmp_path: Path) -> None:
    cfg, processed = ready(tmp_path)
    (cfg.directory / CONTROL.filename).unlink()
    with pytest.raises(SupplementGateError, match="missing"):
        publish(cfg, processed, tmp_path / "interim")
    assert not (processed / VERSION).exists()


def test_ids_already_in_the_base_block_publication(tmp_path: Path) -> None:
    cfg, processed = ready(tmp_path)
    zip_file(cfg.directory / GAP.filename, month_rows("2018-07", 1, 20))  # ids of the control month
    with pytest.raises(SupplementGateError, match="already exist"):
        publish(cfg, processed, tmp_path / "interim")
    assert not (processed / VERSION).exists()


def test_disagreement_with_the_official_aggregate_blocks_publication(tmp_path: Path) -> None:
    cfg, processed = ready(tmp_path)
    zip_file(cfg.directory / GAP.filename, month_rows("2018-07", 1000, 18))  # 10% fewer rows
    with pytest.raises(SupplementGateError, match="differs"):
        publish(cfg, processed, tmp_path / "interim")
    assert not (processed / VERSION).exists()


def test_evaluation_months_stay_in_a_separate_dataset(tmp_path: Path) -> None:
    rows = month_rows("2025-12", 1, 10)
    processed = base_dataset(tmp_path, rows)
    spec = SupplementSpec("2026-01", Role.EVALUATION)
    directory = tmp_path / "supplements"
    directory.mkdir()
    zip_file(directory / spec.filename, month_rows("2026-01", 500, 10))
    probe = SupplementConfig(directory, tmp_path / "x", tmp_path / "r.json", (spec,))
    lazy = validate_month(spec, directory / spec.filename, probe, 1).valid.lazy()
    cfg = SupplementConfig(
        directory, reference_csv(tmp_path / "ref.csv", lazy), tmp_path / "r.json", (spec,)
    )
    result = publish_evaluation(cfg, processed, tmp_path / "interim")
    assert result["months"] == ["2026-01"]
    assert (processed / "flights_eval_2026").exists()
    assert not (processed / VERSION).exists()
    base = pl.scan_parquet(
        (processed / "flights" / "*" / "*" / "*.parquet").as_posix(), hive_partitioning=False
    )
    assert base.select(pl.col("dt_referencia").max()).collect().item().year == 2025


def test_reference_reader_and_comparison(tmp_path: Path) -> None:
    path = tmp_path / "ref.csv"
    path.write_text(
        "Atualizado em: 2026-11-06\n"
        '"EMPRESA_SIGLA";"ANO";"MES";"PASSAGEIROS_PAGOS";"ASK";"RPK";"DECOLAGENS";"ASSENTOS"\n'
        '"AZU";"2018";"7";"100";"1000";"800";"10";"120"\n'
        '"AZU";"2018";"7";"50";"500";"400";"5";"60"\n'
        '"GLO";"2018";"7";"";"";"";"";""\n',
        encoding="utf-8",
    )
    reference = reference_totals(path)
    azul = reference.filter(pl.col("carrier") == "AZU")
    assert azul.get_column("takeoffs").to_list() == [15.0]
    ours = pl.DataFrame(
        {"carrier": ["AZU"], "year": [2018], "month": [7], "takeoffs": [15.0], "seats": [180.0],
         "rpk": [1200.0], "ask": [1500.0], "paid_pax": [150.0]},
        schema_overrides={"year": pl.Int32, "month": pl.Int32},
    )  # fmt: skip
    result = compare(ours, reference)
    assert result.filter(pl.col("metric") == "seats").get_column(
        "relative_difference"
    ).to_list() == [0.0]
