"""Build panels, features and targets, recording exactly what produced them."""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from anac.features.config import FeatureConfig, month_label
from anac.features.contracts import CONTRACTS
from anac.features.daily import build_daily, daily_targets, month_first_day
from anac.features.monthly import build_monthly, monthly_targets
from anac.features.panels import (
    airport_day_panel,
    known_months,
    missing_months,
    resolve_dataset,
    route_carrier_panel,
    scan_flights,
)
from anac.features.splits import assign_split, withheld_from
from anac.ingestion.storage import read_json, write_json_atomic, write_parquet_atomic

log = logging.getLogger("anac.features")


class StaleBuild(RuntimeError):
    """Existing output came from other data or settings."""


def dataset_digest(path: Path) -> str:
    """Names and sizes of the data files: fast, and changes whenever the dataset changes."""
    entries = sorted(
        (file.relative_to(path).as_posix(), file.stat().st_size)
        for file in path.glob("*/*/*.parquet")
    )
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()[:16]


def git_state() -> dict[str, Any]:
    def run(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments], capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "commit": run("rev-parse", "--short", "HEAD"),
        "tracked_changes": bool(run("status", "--short", "--untracked-files=no")),
    }


def load_panels(cfg: FeatureConfig) -> dict[str, Any]:
    dataset, version = resolve_dataset(cfg.processed)
    digest = dataset_digest(dataset)
    panels_dir = cfg.output / "panels"
    identity = {"dataset": version, "dataset_digest": digest, "config": cfg.fingerprint()}
    manifest_path = panels_dir / "manifest.json"
    if manifest_path.exists() and read_json(manifest_path).get("identity") == identity:
        stored = read_json(manifest_path)
        return {
            "version": version,
            "digest": digest,
            "route_carrier": pl.read_parquet(panels_dir / "route_carrier.parquet"),
            "airport_day": pl.read_parquet(panels_dir / "airport_day.parquet"),
            "missing": set(stored["missing_month_indexes"]),
        }
    flights = scan_flights(dataset)
    missing = missing_months(known_months(flights))
    log.info(
        "building panels from %s; unknown months: %s", version, sorted(map(month_label, missing))
    )
    route_carrier = route_carrier_panel(flights, cfg)
    airport_day = airport_day_panel(flights, missing)
    write_parquet_atomic(route_carrier, panels_dir / "route_carrier.parquet", zstd_level=3)
    write_parquet_atomic(airport_day, panels_dir / "airport_day.parquet", zstd_level=3)
    write_json_atomic(
        manifest_path,
        {
            "identity": identity,
            "missing_month_indexes": sorted(missing),
            "missing_months": sorted(month_label(m) for m in missing),
            "rows": {"route_carrier": route_carrier.height, "airport_day": airport_day.height},
        },
    )
    return {
        "version": version,
        "digest": digest,
        "route_carrier": route_carrier,
        "airport_day": airport_day,
        "missing": missing,
    }


def build_module(
    cfg: FeatureConfig,
    module: str,
    *,
    unseal_test: bool = False,
    unseal_reason: str | None = None,
) -> dict[str, Any]:
    """Features and targets of one module. Test targets stay unwritten unless unsealed."""
    contract = CONTRACTS[module]
    time = cfg.time
    withheld = withheld_from(time, unseal_test=unseal_test, reason=unseal_reason)
    last_target = withheld - 1
    panels = load_panels(cfg)
    identity = {
        "module": module,
        "dataset": panels["version"],
        "dataset_digest": panels["digest"],
        "config": cfg.fingerprint(),
        "first_target": month_label(time.first_target),
        "last_target": month_label(last_target),
    }
    directory = cfg.output / f"module_{module}"
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        existing = read_json(manifest_path)
        if existing["identity"] == identity:
            log.info("module %s is up to date", module)
            return existing
        raise StaleBuild(
            f"{directory} was built from other data or settings. Remove it explicitly, or "
            "point paths.output at a new version."
        )

    if module == "a":
        features = build_daily(
            panels["airport_day"], cfg, first_target=time.first_target, last_target=last_target
        )
        targets = daily_targets(panels["airport_day"], month_first_day(withheld))
    else:
        features = build_monthly(
            panels["route_carrier"],
            contract,
            cfg,
            horizons=cfg.b_horizons if module == "b" else cfg.d_horizons,
            min_mean_seats=cfg.b_min_mean_seats if module == "b" else cfg.d_min_mean_seats,
            missing=panels["missing"],
            first_target=time.first_target,
            last_target=last_target,
        )
        targets = monthly_targets(panels["route_carrier"], list(contract.unit), last_target)

    features = assign_split(features, time)
    rows_by_split = dict(features.group_by("split").len().sort("split").iter_rows())
    write_parquet_atomic(features, directory / "features.parquet", zstd_level=3)
    write_parquet_atomic(targets, directory / "targets.parquet", zstd_level=3)
    manifest = {
        "identity": identity,
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git": git_state(),
        "contract": contract.to_dict(),
        "rows": {"features": features.height, "targets": targets.height, "by_split": rows_by_split},
        "unknown_months": sorted(month_label(m) for m in panels["missing"]),
        "publication_lag_months": time.publication_lag_months,
        "test_targets_written": unseal_test,
        "unseal_reason": unseal_reason,
    }
    write_json_atomic(manifest_path, manifest)
    log.info("module %s: %d feature rows, %s", module, features.height, rows_by_split)
    return manifest
