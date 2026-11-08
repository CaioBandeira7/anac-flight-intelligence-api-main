"""Merge chunk outputs into one Parquet file per reference month.

Since the CSV is not chronological, a month's rows can sit in any chunk. Chunks write
per-month pieces first; this stage combines them. A single month is small enough
(well under the size of a chunk's raw text) to be held in memory safely.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import polars as pl

from anac.ingestion.contract import CHUNK_FLAGS, DUPLICATE_FLAG
from anac.ingestion.parsing import REJECT_SCHEMA
from anac.ingestion.storage import read_json, write_json_atomic, write_parquet_atomic

REASON_DUPLICATE_ID: Final = "duplicate_id_basica"

# Rows that agree on all of these describe the same operated leg, even under a
# different id_basica: the audit found such pairs with identical metrics.
DUPLICATE_KEY: Final[tuple[str, ...]] = (
    "id_empresa", "nr_voo", "dt_referencia", "dt_partida_real", "hr_partida_real",
    "sg_icao_origem", "sg_icao_destino", "nr_etapa", "nr_passag_pagos",
    "nr_assentos_ofertados", "kg_payload",
)  # fmt: skip


class OverwriteRefused(RuntimeError):
    """A finished output exists but was built from different inputs."""


@dataclass(frozen=True)
class Period:
    year: int
    month: int

    @property
    def label(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


@dataclass(frozen=True)
class PeriodResult:
    period: Period
    rows: int
    duplicate_ids_removed: int
    bytes_written: int
    skipped: bool


def _input_digest(inputs: list[dict[str, Any]], fingerprint: str) -> str:
    payload = json.dumps({"inputs": inputs, "config": fingerprint}, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def period_stats(frame: pl.DataFrame, period: Period) -> dict[str, Any]:
    """Row-level aggregates of one month, for the report and the BI layer."""
    flags = (*CHUNK_FLAGS, DUPLICATE_FLAG)
    seats = pl.col("nr_assentos_ofertados")
    row = frame.select(
        pl.len().alias("rows"),
        pl.col("nr_decolagem").sum().alias("takeoffs"),
        seats.sum().alias("seats"),
        pl.col("nr_passag_pagos").sum().alias("paid_passengers"),
        pl.col("nr_passag_pagos")
        .filter(seats > 0)
        .sum()
        .truediv(seats.filter(seats > 0).sum())
        .alias("paid_load_factor"),
        pl.col("kg_bagagem_excesso").is_null().mean().alias("null_rate_excess_baggage"),
        pl.col("lt_combustivel").is_null().mean().alias("null_rate_fuel"),
        pl.col("has_excess_baggage").mean().alias("excess_baggage_rate"),
        pl.col("sg_empresa_icao").n_unique().alias("carriers"),
        pl.col("sg_icao_origem").n_unique().alias("origin_airports"),
        pl.col("is_international").mean().alias("international_share"),
        pl.col("dt_referencia").min().alias("min_date"),
        pl.col("dt_referencia").max().alias("max_date"),
        *[pl.col(flag).sum().alias(flag) for flag in flags],
    ).row(0, named=True)
    # ISO strings, so stats are identical whether freshly computed or loaded from a manifest.
    row["min_date"] = row["min_date"].isoformat()
    row["max_date"] = row["max_date"].isoformat()
    return {"year": period.year, "month": period.month, **row}


def compact_period(
    period: Period,
    pieces: list[dict[str, Any]],
    *,
    flights_dir: Path,
    manifests_dir: Path,
    rejects_dir: Path,
    fingerprint: str,
    zstd_level: int,
) -> tuple[PeriodResult, dict[str, Any]]:
    """Build or reuse the Parquet of one month. Idempotent for identical inputs."""
    # Identified by chunk and file name, so moving the output root does not invalidate it.
    inputs = sorted(
        (
            {
                "piece": Path(piece["path"]).parent.name + "/" + Path(piece["path"]).name,
                "bytes": piece["bytes"],
                "rows": piece["rows"],
            }
            for piece in pieces
        ),
        key=lambda item: str(item["piece"]),
    )
    digest = _input_digest(inputs, fingerprint)
    target = flights_dir / f"year={period.year:04d}" / f"month={period.month:02d}" / "data.parquet"
    manifest_path = manifests_dir / f"period={period.label}.json"

    if target.exists() and manifest_path.exists():
        manifest = read_json(manifest_path)
        unchanged = manifest["input_digest"] == digest
        if unchanged and target.stat().st_size == manifest["bytes"]:
            result = PeriodResult(
                period, manifest["rows"], manifest["duplicate_ids_removed"], manifest["bytes"], True
            )
            return result, manifest["stats"]
        raise OverwriteRefused(
            f"{target} exists but was built from different inputs or was altered. "
            "Remove it explicitly, or use a different output root."
        )
    if target.exists():
        raise OverwriteRefused(f"{target} exists without a manifest; refusing to overwrite it.")

    frame = (
        pl.scan_parquet([piece["path"] for piece in pieces])
        .sort("dt_referencia", "id_basica", "_chunk_id", "_source_line")
        .collect()
    )
    rows_in = frame.height
    first_id = frame.get_column("id_basica").is_first_distinct()
    duplicates = frame.filter(~first_id)
    kept = frame.filter(first_id)

    if duplicates.height:
        rejected = duplicates.select(
            pl.col("_chunk_id").alias("chunk_id"),
            pl.col("_source_line").alias("source_line"),
            pl.lit(REASON_DUPLICATE_ID).alias("reason"),
            pl.struct(pl.all()).struct.json_encode().alias("raw_record"),
        ).cast(REJECT_SCHEMA)
        write_parquet_atomic(
            rejected, rejects_dir / f"period={period.label}.parquet", zstd_level=zstd_level
        )

    has_departure = pl.col("partida_real_ts").is_not_null()
    kept = kept.with_columns(
        (has_departure & ~pl.struct(DUPLICATE_KEY).is_first_distinct()).alias(DUPLICATE_FLAG)
    )
    stats = period_stats(kept, period)
    size = write_parquet_atomic(kept, target, zstd_level=zstd_level)
    write_json_atomic(
        manifest_path,
        {
            "period": period.label,
            "rows": kept.height,
            "rows_in": rows_in,
            "duplicate_ids_removed": duplicates.height,
            "bytes": size,
            "input_digest": digest,
            "stats": stats,
        },
    )
    return PeriodResult(period, kept.height, duplicates.height, size, False), stats
