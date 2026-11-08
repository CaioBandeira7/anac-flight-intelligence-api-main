"""Validate official monthly ZIPs and publish a new dataset version. The source CSV is never read
for writing and the existing `flights/` directory is never changed.

Every gate must pass before anything is published:

1. schema        all contract columns exist (case, separator and encoding are normalised)
2. granularity   one row per id_basica, all in the declared month
3. definitions   the control month matches the base row by row
4. overlap       no id of a new month already exists in the base
5. reference     monthly takeoffs, seats, RPK and ASK match ANAC's aggregate
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import shutil
import tomllib
import zipfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from anac.config import RulesConfig
from anac.ingestion.compaction import Period, compact_period
from anac.ingestion.contract import SELECTED_NAMES, SOURCE_COLUMNS, SchemaDriftError
from anac.ingestion.parsing import parse_raw_chunk
from anac.ingestion.reference import METRICS, monthly_totals, reference_totals
from anac.ingestion.storage import (
    publish_directory,
    sha256_file,
    write_json_atomic,
    write_parquet_atomic,
)
from anac.validation.rules import validate_chunk

log = logging.getLogger("anac.supplements")

PORTAL = (
    "https://www.gov.br/anac/pt-br/assuntos/regulados/empresas-aereas/"
    "Instrucoes-para-a-elaboracao-e-apresentacao-das-demonstracoes-contabeis/"
    "envio-de-informacoes/basica/{year}/basica{month}.zip"
)
VERSION = "flights_v2_1"
EVALUATION_DATASET = "flights_eval_2026"
SOURCE_BASE = "anac_csv_snapshot"
SOURCE_ZIP = "anac_portal_basica_zip"
_CHUNK_ID_START = 900_000

COMPARED_TEXT = ("nr_voo", "sg_icao_origem", "sg_icao_destino", "sg_empresa_icao")
COMPARED_NUMBERS = ("nr_passag_pagos", "nr_assentos_ofertados", "km_distancia", "nr_ask", "nr_rpk")


class Role(StrEnum):
    GAP = "gap"
    CONTROL = "control"
    REVISION = "revision"
    EVALUATION = "evaluation"


class SupplementGateError(RuntimeError):
    """A gate failed: nothing is published."""


@dataclass(frozen=True)
class SupplementSpec:
    month: str
    role: Role

    @property
    def filename(self) -> str:
        return f"basica{self.month}.zip"

    @property
    def url(self) -> str:
        return PORTAL.format(year=self.month[:4], month=self.month)


@dataclass(frozen=True)
class SupplementConfig:
    directory: Path
    reference_csv: Path
    report: Path
    specs: tuple[SupplementSpec, ...]
    min_rows_in_month: float = 0.999
    min_control_id_match: float = 0.99
    min_control_value_match: float = 0.99
    max_reference_difference: float = 0.005

    def of_role(self, role: Role) -> list[SupplementSpec]:
        return [spec for spec in self.specs if spec.role is role]


def load_supplement_config(path: Path, *, root: Path | None = None) -> SupplementConfig:
    base = root if root is not None else Path.cwd()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    specs = tuple(
        SupplementSpec(month, Role(role))
        for role, months in raw["months"].items()
        for month in months
    )
    return SupplementConfig(
        directory=base / raw["paths"]["directory"],
        reference_csv=base / raw["paths"]["reference_csv"],
        report=base / raw["paths"]["report"],
        specs=specs,
        **raw["gates"],
    )


def supplement_status(cfg: SupplementConfig) -> dict[str, Any]:
    """What is present and what the user still needs to download."""
    entries = []
    for spec in cfg.specs:
        path = cfg.directory / spec.filename
        entries.append(
            {
                "month": spec.month,
                "role": spec.role.value,
                "file": spec.filename,
                "present": path.exists(),
                "bytes": path.stat().st_size if path.exists() else None,
                "url": spec.url,
            }
        )
    required = [item for item in entries if item["role"] in (Role.GAP, Role.CONTROL)]
    return {
        "directory": str(cfg.directory),
        "required_missing": [item["file"] for item in required if not item["present"]],
        "ready_to_publish": all(item["present"] for item in required),
        "files": entries,
    }


def read_official_zip(path: Path) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Read a monthly ZIP into the contract's column order, as strings."""
    with zipfile.ZipFile(path) as archive:
        members = [
            info for info in archive.infolist()
            if not info.is_dir() and info.filename.lower().endswith((".csv", ".txt"))
        ]  # fmt: skip
        if len(members) != 1:
            raise SchemaDriftError(f"{path.name}: expected one data file, found {len(members)}")
        raw = archive.read(members[0])
    try:
        text = raw.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
        encoding = "cp1252"
    del raw
    lines = text.split("\n", 2)
    # Some ANAC exports start with an "Atualizado em" line before the header.
    skip = 1 if lines[0].lower().startswith("atualizado em") else 0
    header_line = lines[skip]
    separator = ";" if header_line.count(";") > header_line.count(",") else ","
    frame = pl.read_csv(
        io.BytesIO(text.encode("utf-8")),
        separator=separator,
        skip_lines=skip,
        infer_schema=False,
        quote_char='"',
        truncate_ragged_lines=False,
        encoding="utf8",
    )
    del text
    frame = frame.rename({name: name.strip().strip('"').lower() for name in frame.columns})
    missing = sorted(set(SELECTED_NAMES) - set(frame.columns))
    if missing:
        raise SchemaDriftError(f"{path.name}: missing contract columns {missing}")
    extra = sorted(set(frame.columns) - set(SOURCE_COLUMNS))
    absent_optional = sorted(set(SOURCE_COLUMNS) - set(frame.columns))
    frame = frame.with_columns(
        pl.lit(None, dtype=pl.String).alias(name) for name in absent_optional
    )
    info = {
        "inner_file": members[0].filename,
        "encoding": encoding,
        "separator": separator,
        "rows": frame.height,
        "extra_columns": extra,
        "unused_columns_absent": absent_optional,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }
    return frame.select(SOURCE_COLUMNS), info


@dataclass
class ValidatedMonth:
    spec: SupplementSpec
    valid: pl.DataFrame
    rejects: pl.DataFrame
    info: dict[str, Any]
    gates: dict[str, Any] = field(default_factory=dict)


def validate_month(
    spec: SupplementSpec, path: Path, cfg: SupplementConfig, chunk_id: int
) -> ValidatedMonth:
    """Schema and granularity gates, through the same parser and rules as the main pipeline."""
    frame, info = read_official_zip(path)
    # Reusing the canonical parser keeps one definition of a valid row.
    payload = io.BytesIO()
    frame.write_csv(payload, include_header=False)
    parsed = parse_raw_chunk(payload.getvalue(), chunk_id)
    validated = validate_chunk(
        parsed.frame, chunk_id, RulesConfig(max_reference_date=_month_end(spec))
    )
    rejects = pl.concat([parsed.malformed, validated.rejects])
    valid = validated.valid
    if parsed.lines_total != valid.height + rejects.height:
        raise SupplementGateError(f"{path.name}: line accounting failed")

    year, month = (int(part) for part in spec.month.split("-"))
    in_month = valid.filter(
        (pl.col("dt_referencia").dt.year() == year) & (pl.col("dt_referencia").dt.month() == month)
    ).height
    share = in_month / valid.height if valid.height else 0.0
    repeated = valid.height - valid.get_column("id_basica").n_unique()
    gates = {
        "schema": "passed",
        "rows_in_declared_month": round(share, 6),
        "repeated_ids": repeated,
        "rejected_rows": rejects.height,
        "invalid_values": validated.invalid_counts,
    }
    if valid.is_empty() or share < cfg.min_rows_in_month:
        raise SupplementGateError(f"{path.name}: only {share:.4%} of rows are in {spec.month}")
    if repeated:
        raise SupplementGateError(f"{path.name}: {repeated} repeated id_basica values")
    return ValidatedMonth(spec, valid, rejects, info, gates)


def _month_end(spec: SupplementSpec) -> Any:
    from datetime import date, timedelta

    year, month = (int(part) for part in spec.month.split("-"))
    first_next = date(year + (month == 12), month % 12 + 1, 1)
    return first_next - timedelta(days=1)


def scan_base(flights_dir: Path) -> pl.LazyFrame:
    return pl.scan_parquet(
        (flights_dir / "*" / "*" / "*.parquet").as_posix(), hive_partitioning=False
    )


def gate_overlap(month: ValidatedMonth, flights_dir: Path) -> None:
    """A new month must add rows, never repeat rows the base already holds."""
    ids = month.valid.select("id_basica").lazy()
    found = scan_base(flights_dir).select("id_basica").join(ids, on="id_basica", how="semi")
    count = int(found.select(pl.len()).collect(engine="streaming").item())
    month.gates["ids_already_in_base"] = count
    if count:
        raise SupplementGateError(f"{month.spec.filename}: {count} ids already exist in the base")


def gate_control(month: ValidatedMonth, flights_dir: Path, cfg: SupplementConfig) -> None:
    """The control month exists in both sources, so they can be compared row by row."""
    columns = ["id_basica", *COMPARED_TEXT, *COMPARED_NUMBERS]
    year, number = (int(part) for part in month.spec.month.split("-"))
    base = (
        scan_base(flights_dir)
        .filter(
            (pl.col("dt_referencia").dt.year() == year)
            & (pl.col("dt_referencia").dt.month() == number)
        )
        .select(columns)
        .collect(engine="streaming")
    )
    new = month.valid.select(columns)
    joined = new.join(base, on="id_basica", how="inner", suffix="_base")
    id_match = joined.height / max(new.height, base.height, 1)
    equal = pl.all_horizontal(
        pl.col(name).eq_missing(pl.col(f"{name}_base")) for name in COMPARED_TEXT
    ) & pl.all_horizontal(
        ((pl.col(name) - pl.col(f"{name}_base")).abs() <= 0.5).fill_null(
            pl.col(name).is_null() & pl.col(f"{name}_base").is_null()
        )
        for name in COMPARED_NUMBERS
    )
    value_match = joined.select(equal.mean()).item() if joined.height else 0.0
    month.gates.update(
        {
            "control_rows_zip": new.height,
            "control_rows_base": base.height,
            "control_id_match": round(id_match, 6),
            "control_value_match": round(float(value_match), 6),
        }
    )
    if id_match < cfg.min_control_id_match or float(value_match) < cfg.min_control_value_match:
        raise SupplementGateError(
            f"{month.spec.filename}: control month does not match the base "
            f"(ids {id_match:.2%}, values {float(value_match):.2%})"
        )


def gate_reference(
    months: list[ValidatedMonth], reference: pl.DataFrame, cfg: SupplementConfig
) -> None:
    for month in months:
        year, number = (int(part) for part in month.spec.month.split("-"))
        ours = monthly_totals(month.valid.lazy()).filter(
            (pl.col("year") == year) & (pl.col("month") == number)
        )
        official = reference.filter((pl.col("year") == year) & (pl.col("month") == number))
        differences: dict[str, float | None] = {}
        for metric in METRICS:
            expected = float(official.get_column(metric).sum())
            actual = float(ours.get_column(metric).sum())
            differences[metric] = round(actual / expected - 1, 6) if expected else None
        month.gates["reference_difference"] = differences
        failed = [
            name for name, value in differences.items()
            if value is None or abs(value) > cfg.max_reference_difference
        ]  # fmt: skip
        if failed:
            raise SupplementGateError(
                f"{month.spec.filename}: differs from ANAC's aggregate on {failed}: {differences}"
            )


def _stage_month(month: ValidatedMonth, stage: Path, interim: Path, level: int) -> dict[str, Any]:
    """Compaction adds the duplicate flag and the same sort as every other month."""
    year, number = (int(part) for part in month.spec.month.split("-"))
    pieces_dir = interim / month.spec.month
    piece = pieces_dir / f"period={month.spec.month}.parquet"
    size = write_parquet_atomic(month.valid, piece, zstd_level=1)
    result, _ = compact_period(
        Period(year, number),
        [{"path": str(piece), "bytes": size, "rows": month.valid.height}],
        flights_dir=stage,
        manifests_dir=interim / "manifests",
        rejects_dir=interim / "rejects",
        fingerprint=month.info["sha256"],
        zstd_level=level,
    )
    return {"month": month.spec.month, "rows": result.rows, "bytes": result.bytes_written}


def _with_source(path: Path, source: str, target: Path, level: int) -> int:
    frame = pl.read_parquet(path).with_columns(pl.lit(source).alias("_source"))
    write_parquet_atomic(frame, target, zstd_level=level)
    return frame.height


def _verify_published(stage: Path, expected_rows: int, sources: dict[str, int]) -> dict[str, Any]:
    glob = (stage / "*" / "*" / "*.parquet").as_posix()
    with duckdb.connect() as connection:
        row = connection.execute(
            f"""
            SELECT count(*), count(DISTINCT id_basica), min(dt_referencia), max(dt_referencia),
                   count_if(_source = '{SOURCE_ZIP}')
            FROM read_parquet('{glob}', hive_partitioning=false)
            """
        ).fetchone()
    if row is None or row[0] != expected_rows:
        raise SupplementGateError(f"read back {row and row[0]} rows, expected {expected_rows}")
    if row[4] != sources.get(SOURCE_ZIP, 0):
        raise SupplementGateError("rows by source do not reconcile")
    return {
        "rows": row[0],
        "distinct_id_basica": row[1],
        "min_reference_date": str(row[2]),
        "max_reference_date": str(row[3]),
        "rows_from_zip": row[4],
    }


def publish(cfg: SupplementConfig, processed_dir: Path, interim_dir: Path) -> dict[str, Any]:
    """Validate everything available, then publish `flights_v2_1/` atomically if the gates pass."""
    status = supplement_status(cfg)
    if not status["ready_to_publish"]:
        raise SupplementGateError(f"files still missing: {status['required_missing']}")
    base_dir = processed_dir / "flights"
    target = processed_dir / VERSION
    if target.exists():
        raise SupplementGateError(f"{target} already exists; refusing to overwrite it")

    reference = reference_totals(cfg.reference_csv)
    chunk_id = _CHUNK_ID_START
    gaps: list[ValidatedMonth] = []
    report: dict[str, Any] = {"status": "validating", "months": []}

    for spec in cfg.of_role(Role.CONTROL):
        month = validate_month(spec, cfg.directory / spec.filename, cfg, chunk_id)
        chunk_id += 1
        gate_control(month, base_dir, cfg)
        report["months"].append(
            {"month": spec.month, "role": spec.role.value, **month.info, **month.gates}
        )
    for spec in cfg.of_role(Role.GAP):
        month = validate_month(spec, cfg.directory / spec.filename, cfg, chunk_id)
        chunk_id += 1
        gate_overlap(month, base_dir)
        gaps.append(month)
    gate_reference(gaps, reference, cfg)
    for month in gaps:
        report["months"].append(
            {"month": month.spec.month, "role": month.spec.role.value, **month.info, **month.gates}
        )

    stage = processed_dir / f"{VERSION}.tmp-build"
    interim = interim_dir / "supplements"
    for leftover in (stage, interim):
        if leftover.exists():
            shutil.rmtree(leftover)
    level = 6
    sources: dict[str, int] = {SOURCE_BASE: 0, SOURCE_ZIP: 0}
    for path in sorted(base_dir.glob("*/*/data.parquet")):
        relative = path.relative_to(base_dir)
        sources[SOURCE_BASE] += _with_source(path, SOURCE_BASE, stage / relative, level)
    staged = interim / "staged"
    for month in gaps:
        entry = _stage_month(month, staged, interim, level)
        year, number = month.spec.month.split("-")
        relative = Path(f"year={year}") / f"month={number}" / "data.parquet"
        sources[SOURCE_ZIP] += _with_source(staged / relative, SOURCE_ZIP, stage / relative, level)
        log.info("staged %s: %d rows", entry["month"], entry["rows"])

    verification = _verify_published(stage, sum(sources.values()), sources)
    digest = hashlib.sha256(
        json.dumps(sorted(item["sha256"] for item in report["months"])).encode()
    ).hexdigest()
    manifest = {
        "version": VERSION,
        "built_from": "flights",
        "supplement_digest": digest,
        "rows_by_source": sources,
        "verification": verification,
    }
    write_json_atomic(stage / "_manifest.json", manifest)
    publish_directory(stage, target)
    report.update({"status": "published", **manifest})
    write_json_atomic(cfg.report, report)
    return report


def compare_revisions(cfg: SupplementConfig, processed_dir: Path) -> list[dict[str, Any]]:
    """Measure how much recent months changed since the CSV snapshot. Replaces nothing."""
    results = []
    base_dir = processed_dir / "flights"
    chunk_id = _CHUNK_ID_START + 100
    for spec in cfg.of_role(Role.REVISION):
        path = cfg.directory / spec.filename
        if not path.exists():
            continue
        month = validate_month(spec, path, cfg, chunk_id)
        chunk_id += 1
        year, number = (int(part) for part in spec.month.split("-"))
        base = (
            scan_base(base_dir)
            .filter(
                (pl.col("dt_referencia").dt.year() == year)
                & (pl.col("dt_referencia").dt.month() == number)
            )
            .select("id_basica")
            .collect(engine="streaming")
        )
        results.append(
            {
                "month": spec.month,
                "rows_portal": month.valid.height,
                "rows_snapshot": base.height,
                "ids_only_in_portal": month.valid.join(base, on="id_basica", how="anti").height,
                "ids_only_in_snapshot": base.join(month.valid, on="id_basica", how="anti").height,
            }
        )
    return results


def publish_evaluation(
    cfg: SupplementConfig, processed_dir: Path, interim_dir: Path
) -> dict[str, Any]:
    """Keep later months in their own dataset, physically apart from anything used for training."""
    target = processed_dir / EVALUATION_DATASET
    specs = [s for s in cfg.of_role(Role.EVALUATION) if (cfg.directory / s.filename).exists()]
    if not specs:
        raise SupplementGateError("no evaluation files present")
    if target.exists():
        raise SupplementGateError(f"{target} already exists; refusing to overwrite it")
    reference = reference_totals(cfg.reference_csv)
    base_dir = (
        processed_dir / VERSION if (processed_dir / VERSION).exists() else processed_dir / "flights"
    )
    months = []
    for offset, spec in enumerate(specs):
        month = validate_month(
            spec, cfg.directory / spec.filename, cfg, _CHUNK_ID_START + 200 + offset
        )
        gate_overlap(month, base_dir)
        months.append(month)
    gate_reference(months, reference, cfg)
    stage = processed_dir / f"{EVALUATION_DATASET}.tmp-build"
    interim = interim_dir / "supplements_eval"
    for leftover in (stage, interim):
        if leftover.exists():
            shutil.rmtree(leftover)
    sources = {SOURCE_ZIP: 0}
    for month in months:
        _stage_month(month, interim / "staged", interim, 6)
        year, number = month.spec.month.split("-")
        relative = Path(f"year={year}") / f"month={number}" / "data.parquet"
        sources[SOURCE_ZIP] += _with_source(
            interim / "staged" / relative, SOURCE_ZIP, stage / relative, 6
        )
    verification = _verify_published(stage, sources[SOURCE_ZIP], sources)
    write_json_atomic(
        stage / "_manifest.json",
        {
            "version": EVALUATION_DATASET,
            "months": [m.spec.month for m in months],
            "verification": verification,
        },
    )
    publish_directory(stage, target)
    return {
        "status": "published",
        "months": [m.spec.month for m in months],
        "verification": verification,
    }
