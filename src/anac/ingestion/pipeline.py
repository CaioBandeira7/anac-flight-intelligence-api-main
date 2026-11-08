"""Orchestrates plan -> chunks -> compaction -> verification -> report.

Resumption works at two levels: a finished chunk is a directory published by an atomic
rename, and a finished month is a file plus a manifest. A crash at any point leaves
only ``*.tmp-*`` leftovers, which the next run removes.
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

import polars as pl
import psutil

from anac.config import MB, IngestionConfig
from anac.ingestion import chunking
from anac.ingestion.chunking import ByteRange
from anac.ingestion.compaction import (
    Period,
    PeriodResult,
    compact_period,
)
from anac.ingestion.contract import CHUNK_FLAGS, CONTRACT_VERSION
from anac.ingestion.parsing import ChunkIntegrityError, parse_raw_chunk
from anac.ingestion.storage import (
    publish_directory,
    read_json,
    remove_stale_temporaries,
    write_json_atomic,
    write_parquet_atomic,
)
from anac.validation.report import build_report, verify_dataset
from anac.validation.rules import count_flags, validate_chunk

log = logging.getLogger("anac.ingestion")


class PlanMismatch(RuntimeError):
    """Existing outputs belong to a different source file or configuration."""


class FullRunNotConfirmed(RuntimeError):
    """A full run needs explicit confirmation."""


class MemoryBudgetExceeded(RuntimeError):
    """Resident memory passed the configured abort limit."""


@dataclass(frozen=True)
class RunLayout:
    interim: Path
    chunks: Path
    processed: Path
    flights: Path
    manifests: Path
    rejects: Path
    report: Path
    plan_file: Path
    log_file: Path

    @classmethod
    def for_run(cls, output_root: Path, report_dir: Path) -> RunLayout:
        interim = output_root / "interim" / "ingestion"
        processed = output_root / "processed"
        return cls(
            interim=interim,
            chunks=interim / "chunks",
            processed=processed,
            flights=processed / "flights",
            manifests=interim / "period_manifests",
            rejects=processed / "flights_rejects",
            report=report_dir,
            plan_file=interim / "plan.json",
            log_file=interim / "ingestion.log",
        )


class MemoryMonitor:
    """Samples process RSS in a background thread so the report shows the true peak."""

    def __init__(self, interval_seconds: float = 0.1) -> None:
        self._interval = interval_seconds
        self._process = psutil.Process()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.peak_bytes = 0

    def _run(self) -> None:
        while not self._stop.is_set():
            self.peak_bytes = max(self.peak_bytes, self._process.memory_info().rss)
            self._stop.wait(self._interval)

    def current_bytes(self) -> int:
        return int(self._process.memory_info().rss)

    def __enter__(self) -> MemoryMonitor:
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._stop.set()
        self._thread.join()


def check_memory(cfg: IngestionConfig, memory: MemoryMonitor) -> None:
    """Stop between units of work if memory is short. Finished work is kept for resuming.

    The RSS limit bounds this process. The system check is separate: on a shared desktop
    the machine can start paging long before this process reaches its own limit.
    """
    current = memory.current_bytes()
    available = psutil.virtual_memory().available
    if current > cfg.memory_abort_gb * 1e9:
        raise MemoryBudgetExceeded(
            f"RSS {current / 1e9:.2f} GB is above the {cfg.memory_abort_gb} GB limit. "
            "Rerun to resume, or lower chunk_size_mb in a new run."
        )
    if available < cfg.memory_min_available_gb * 1e9:
        raise MemoryBudgetExceeded(
            f"only {available / 1e9:.2f} GB of system RAM is available, below the "
            f"{cfg.memory_min_available_gb} GB floor. Free memory and rerun to resume."
        )
    if current > cfg.memory_warn_gb * 1e9:
        log.warning("RSS %.2f GB is above the warning level", current / 1e9)


def _configure_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log.setLevel(logging.INFO)
    log.propagate = False
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
    for handler in (logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")):
        handler.setFormatter(formatter)
        log.addHandler(handler)


def _load_or_create_plan(
    cfg: IngestionConfig, mode: str, layout: RunLayout, fingerprint: str
) -> list[ByteRange]:
    source = chunking.fingerprint_source(cfg.source_csv).to_dict()
    if layout.plan_file.exists():
        plan = read_json(layout.plan_file)
        if plan["source"] != source:
            raise PlanMismatch(
                "the source CSV changed since this run was planned "
                f"({plan['source']} != {source}). Use a new output root."
            )
        if plan["config_fingerprint"] != fingerprint:
            raise PlanMismatch(
                "the configuration changed since this run was planned. Output built with "
                "different rules cannot be mixed: use a new output root."
            )
        ranges = [ByteRange(**item) for item in plan["ranges"]]
        log.info("resuming existing plan with %d chunks", len(ranges))
        return ranges

    if mode == "full":
        ranges = chunking.plan_full(cfg.source_csv, int(cfg.chunk_size_mb * MB))
    else:
        ranges = chunking.plan_sample(
            cfg.source_csv, cfg.sample_blocks, cfg.sample_block_mb * MB, cfg.sample_seed
        )
    write_json_atomic(
        layout.plan_file,
        {
            "mode": mode,
            "contract_version": CONTRACT_VERSION,
            "config_fingerprint": fingerprint,
            "source": source,
            "ranges": [vars(item) for item in ranges],
        },
    )
    log.info("planned %d chunks", len(ranges))
    return ranges


def _chunk_dir(layout: RunLayout, chunk_id: int) -> Path:
    return layout.chunks / f"chunk={chunk_id:06d}"


def _load_finished_chunk(directory: Path) -> dict[str, Any] | None:
    """Return the stats of a finished chunk, or None if it needs processing."""
    stats_path = directory / "stats.json"
    if not stats_path.exists():
        return None
    stats = read_json(stats_path)
    for entry in [*stats["pieces"], *stats["reject_files"]]:
        path = directory / entry["name"]
        if not path.exists() or path.stat().st_size != entry["bytes"]:
            raise ChunkIntegrityError(
                f"{directory} is published but {entry['name']} is missing or changed; "
                "remove that chunk directory to rebuild it."
            )
    return stats


def process_chunk(cfg: IngestionConfig, layout: RunLayout, byte_range: ByteRange) -> dict[str, Any]:
    """Parse, validate and publish one chunk, or do nothing if it is already published."""
    final_dir = _chunk_dir(layout, byte_range.chunk_id)
    finished = _load_finished_chunk(final_dir)
    if finished is not None:
        return finished

    started = time.perf_counter()
    raw = chunking.read_range(cfg.source_csv, byte_range)
    parsed = parse_raw_chunk(raw, byte_range.chunk_id)
    del raw
    validated = validate_chunk(parsed.frame, byte_range.chunk_id, cfg.rules)

    malformed = parsed.malformed.height
    rejected = validated.rejects.height
    valid_rows = validated.valid.height
    if parsed.lines_total != valid_rows + rejected + malformed:
        raise ChunkIntegrityError(
            f"chunk {byte_range.chunk_id}: {parsed.lines_total} lines != "
            f"{valid_rows} valid + {rejected} rejected + {malformed} malformed"
        )

    temporary = final_dir.with_name(f"{final_dir.name}.tmp-{os.getpid()}")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)

    pieces: list[dict[str, Any]] = []
    with_period = validated.valid.with_columns(
        pl.col("dt_referencia").dt.year().alias("__year"),
        pl.col("dt_referencia").dt.month().alias("__month"),
    )
    for key, part in with_period.partition_by(
        ["__year", "__month"], as_dict=True, include_key=False
    ).items():
        year, month = int(str(key[0])), int(str(key[1]))
        name = f"period={year:04d}-{month:02d}.parquet"
        size = write_parquet_atomic(part, temporary / name, zstd_level=cfg.interim_zstd_level)
        pieces.append(
            {"name": name, "year": year, "month": month, "rows": part.height, "bytes": size}
        )

    all_rejects = pl.concat([parsed.malformed, validated.rejects])
    reject_files: list[dict[str, Any]] = []
    if all_rejects.height:
        size = write_parquet_atomic(
            all_rejects, temporary / "rejects.parquet", zstd_level=cfg.interim_zstd_level
        )
        reject_files.append({"name": "rejects.parquet", "rows": all_rejects.height, "bytes": size})

    reason_counts = dict(all_rejects.group_by("reason").len().sort("reason").iter_rows())
    valid = validated.valid
    stats = {
        "status": "complete",
        "chunk_id": byte_range.chunk_id,
        "start": byte_range.start,
        "end": byte_range.end,
        "lines_total": parsed.lines_total,
        "valid_rows": valid_rows,
        "rejected_rows": all_rejects.height,
        "reject_reasons": reason_counts,
        "invalid_values": validated.invalid_counts,
        "flags": count_flags(valid) if valid_rows else dict.fromkeys(CHUNK_FLAGS, 0),
        "nulls": {
            name: int(count)
            for name, count in zip(valid.columns, valid.null_count().row(0), strict=True)
        },
        "pieces": pieces,
        "reject_files": reject_files,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    write_json_atomic(temporary / "stats.json", stats)
    publish_directory(temporary, final_dir)
    return stats


def _compact_all(
    cfg: IngestionConfig,
    layout: RunLayout,
    fingerprint: str,
    chunk_stats: list[dict[str, Any]],
    on_period: Callable[[Period], None] | None = None,
) -> tuple[list[PeriodResult], list[dict[str, Any]]]:
    by_period: dict[Period, list[dict[str, Any]]] = defaultdict(list)
    for stats in chunk_stats:
        directory = _chunk_dir(layout, stats["chunk_id"])
        for piece in stats["pieces"]:
            by_period[Period(piece["year"], piece["month"])].append(
                {**piece, "path": str(directory / piece["name"])}
            )
    results: list[PeriodResult] = []
    period_rows: list[dict[str, Any]] = []
    for period in sorted(by_period, key=lambda item: (item.year, item.month)):
        if on_period is not None:
            on_period(period)
        result, stats = compact_period(
            period,
            by_period[period],
            flights_dir=layout.flights,
            manifests_dir=layout.manifests,
            rejects_dir=layout.rejects,
            fingerprint=fingerprint,
            zstd_level=cfg.processed_zstd_level,
        )
        results.append(result)
        period_rows.append(stats)
    return results, period_rows


def _reconcile(chunk_stats: list[dict[str, Any]], results: list[PeriodResult]) -> dict[str, int]:
    """Prove that every line read is accounted for, and fail the run if not."""
    lines = sum(item["lines_total"] for item in chunk_stats)
    valid = sum(item["valid_rows"] for item in chunk_stats)
    rejected = sum(item["rejected_rows"] for item in chunk_stats)
    published = sum(result.rows for result in results)
    duplicates = sum(result.duplicate_ids_removed for result in results)
    totals = {
        "lines_read": lines,
        "chunk_valid_rows": valid,
        "chunk_rejected_rows": rejected,
        "duplicate_ids_removed": duplicates,
        "rows_published": published,
    }
    if lines != valid + rejected:
        raise ChunkIntegrityError(f"line accounting failed: {totals}")
    if valid != published + duplicates:
        raise ChunkIntegrityError(f"publication accounting failed: {totals}")
    return totals


def run_ingestion(
    cfg: IngestionConfig,
    mode: str,
    *,
    output_root: Path | None = None,
    report_dir: Path | None = None,
    confirm_full: bool = False,
    limit_chunks: int | None = None,
    after_chunk: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Run or resume ingestion and return the quality report.

    ``limit_chunks`` stops after that many chunks are done and skips compaction. It
    allows a real full-mode rehearsal on part of the file; rerunning without it
    resumes from the same plan.
    """
    if mode not in {"sample", "full"}:
        raise ValueError(f"unknown mode: {mode}")
    if mode == "full" and not confirm_full:
        raise FullRunNotConfirmed(
            "a full run processes the whole CSV: pass --confirm-full to authorize it"
        )
    if mode == "full":
        root = output_root or cfg.full_output_root
        report_path = report_dir or cfg.full_report_dir
    else:
        run_name = f"blocks{cfg.sample_blocks}_mb{cfg.sample_block_mb}_seed{cfg.sample_seed}"
        root = output_root or cfg.sample_output_root / run_name
        report_path = report_dir or root / "reports"

    layout = RunLayout.for_run(root, report_path)
    _configure_logging(layout.log_file)
    fingerprint = cfg.semantic_fingerprint(mode, CONTRACT_VERSION)

    # Headers are checked before any file is created under a wrong contract.
    chunking.read_header(cfg.source_csv)
    removed = remove_stale_temporaries(layout.interim) + remove_stale_temporaries(layout.processed)
    if removed:
        log.warning("removed %d temporary leftovers of an interrupted run", removed)

    started = time.perf_counter()
    ranges = _load_or_create_plan(cfg, mode, layout, fingerprint)

    with MemoryMonitor() as memory:
        chunk_stats: list[dict[str, Any]] = []
        bytes_done = 0
        bytes_processed_now = 0
        total_bytes = sum(item.size for item in ranges)
        selected = ranges if limit_chunks is None else ranges[:limit_chunks]
        for byte_range in selected:
            already_done = (_chunk_dir(layout, byte_range.chunk_id) / "stats.json").exists()
            stats = process_chunk(cfg, layout, byte_range)
            chunk_stats.append(stats)
            bytes_done += byte_range.size
            if not already_done:
                bytes_processed_now += byte_range.size
            current = memory.current_bytes()
            log.info(
                "chunk %d/%d rows=%d rejected=%d %.1fs rss=%.2fGB avail=%.2fGB bytes=%.1f%%",
                byte_range.chunk_id + 1,
                len(ranges),
                stats["valid_rows"],
                stats["rejected_rows"],
                stats["elapsed_seconds"],
                current / 1e9,
                psutil.virtual_memory().available / 1e9,
                100 * bytes_done / total_bytes,
            )
            check_memory(cfg, memory)
            if after_chunk is not None:
                after_chunk(byte_range.chunk_id)

        if limit_chunks is not None and limit_chunks < len(ranges):
            log.info("stopping after %d chunks as requested; nothing compacted", limit_chunks)
            return {
                "status": "partial",
                "chunks_done": len(selected),
                "chunks_total": len(ranges),
                "peak_rss_bytes": memory.peak_bytes,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            }

        log.info("compacting into monthly Parquet files")
        results, period_rows = _compact_all(
            cfg, layout, fingerprint, chunk_stats, on_period=lambda _: check_memory(cfg, memory)
        )
        totals = _reconcile(chunk_stats, results)
        verification = verify_dataset(layout.flights, totals["rows_published"])
        peak = memory.peak_bytes

    report = build_report(
        mode=mode,
        source=chunking.fingerprint_source(cfg.source_csv).to_dict(),
        rules=cfg.rules,
        fingerprint=fingerprint,
        ranges=ranges,
        chunk_stats=chunk_stats,
        results=results,
        period_rows=period_rows,
        totals=totals,
        verification=verification,
        elapsed_seconds=time.perf_counter() - started,
        bytes_processed_now=bytes_processed_now,
        peak_rss_bytes=peak,
        report_dir=layout.report,
    )
    write_json_atomic(
        layout.processed / "_SUCCESS.json",
        {
            "mode": mode,
            "config_fingerprint": fingerprint,
            "totals": totals,
            "periods": len(results),
        },
    )
    log.info("done: %d rows in %d months", totals["rows_published"], len(results))
    return report


def run_status(cfg: IngestionConfig, output_root: Path) -> dict[str, Any]:
    """Describe the progress of a run without changing anything."""
    layout = RunLayout.for_run(output_root, output_root / "reports")
    if not layout.plan_file.exists():
        return {"state": "not_started", "output_root": str(output_root)}
    plan = read_json(layout.plan_file)
    total = len(plan["ranges"])
    done = sum(
        1
        for item in plan["ranges"]
        if (_chunk_dir(layout, item["chunk_id"]) / "stats.json").exists()
    )
    finished = (layout.processed / "_SUCCESS.json").exists()
    return {
        "state": "finished" if finished else "in_progress",
        "mode": plan["mode"],
        "chunks_done": done,
        "chunks_total": total,
        "output_root": str(output_root),
    }
