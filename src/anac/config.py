"""Typed configuration for the ingestion pipeline."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

MB = 1024 * 1024


@dataclass(frozen=True)
class RulesConfig:
    """Thresholds of the row-level validation rules."""

    min_reference_date: date = date(2000, 1, 1)
    max_reference_date: date = date(2025, 12, 31)
    max_departure_reference_gap_days: int = 3
    max_flight_hours: float = 30.0
    hours_clock_tolerance: float = 0.25
    ask_rpk_relative_tolerance: float = 0.01


@dataclass(frozen=True)
class IngestionConfig:
    """Everything a run needs. ``semantic_fingerprint`` guards safe resumption."""

    source_csv: Path
    full_output_root: Path = Path("data")
    sample_output_root: Path = Path("data/sample")
    full_report_dir: Path = Path("reports/ingestion")
    chunk_size_mb: float = 128
    sample_blocks: int = 20
    sample_block_mb: int = 16
    sample_seed: int = 42
    interim_zstd_level: int = 1
    processed_zstd_level: int = 6
    memory_warn_gb: float = 8.0
    memory_abort_gb: float = 12.0
    memory_min_available_gb: float = 1.0
    rules: RulesConfig = field(default_factory=RulesConfig)

    def semantic_fingerprint(self, mode: str, contract_version: str) -> str:
        """Hash the settings that change output content.

        Paths and memory limits are excluded on purpose: changing them does not
        change the rows produced, so it must not invalidate finished work.
        """
        payload: dict[str, object] = {
            "mode": mode,
            "contract": contract_version,
            "rules": {k: str(v) for k, v in asdict(self.rules).items()},
            "interim_zstd_level": self.interim_zstd_level,
            "processed_zstd_level": self.processed_zstd_level,
        }
        if mode == "full":
            payload["chunk_size_mb"] = self.chunk_size_mb
        else:
            payload["sample"] = [self.sample_blocks, self.sample_block_mb, self.sample_seed]
        encoded = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()[:16]


def load_config(path: Path, *, root: Path | None = None) -> IngestionConfig:
    """Load a TOML config, resolving relative paths against ``root``."""
    base = root if root is not None else Path.cwd()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    paths = raw["paths"]
    rules_raw = dict(raw.get("rules", {}))
    for key in ("min_reference_date", "max_reference_date"):
        if key in rules_raw:
            rules_raw[key] = date.fromisoformat(str(rules_raw[key]))
    return IngestionConfig(
        source_csv=base / paths["source_csv"],
        full_output_root=base / paths["full_output_root"],
        sample_output_root=base / paths["sample_output_root"],
        full_report_dir=base / paths["full_report_dir"],
        chunk_size_mb=float(raw["chunking"]["chunk_size_mb"]),
        sample_blocks=int(raw["sample"]["blocks"]),
        sample_block_mb=int(raw["sample"]["block_mb"]),
        sample_seed=int(raw["sample"]["seed"]),
        interim_zstd_level=int(raw["parquet"]["interim_zstd_level"]),
        processed_zstd_level=int(raw["parquet"]["processed_zstd_level"]),
        memory_warn_gb=float(raw["memory"]["warn_gb"]),
        memory_abort_gb=float(raw["memory"]["abort_gb"]),
        memory_min_available_gb=float(raw["memory"]["min_available_gb"]),
        rules=RulesConfig(**rules_raw),
    )
