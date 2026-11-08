"""Independent read-back of the dataset (DuckDB) and the data quality report."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from anac.config import RulesConfig
from anac.ingestion.chunking import ByteRange
from anac.ingestion.compaction import PeriodResult
from anac.ingestion.contract import CHUNK_FLAGS, DUPLICATE_FLAG, SELECTED_NAMES
from anac.ingestion.storage import write_json_atomic, write_parquet_atomic, write_text_atomic


class VerificationError(RuntimeError):
    """The published Parquet files do not match what the pipeline says it wrote."""


def verify_dataset(flights_dir: Path, expected_rows: int) -> dict[str, Any]:
    """Read everything back with a second engine, so a Polars bug cannot hide itself."""
    if expected_rows == 0:
        return {"rows": 0, "note": "nothing published"}
    glob = (flights_dir / "*" / "*" / "*.parquet").as_posix()
    source = f"read_parquet('{glob}', hive_partitioning=true, union_by_name=false)"
    with duckdb.connect(":memory:") as connection:
        row = connection.execute(
            f"""
            SELECT count(*), count(DISTINCT id_basica), min(dt_referencia), max(dt_referencia),
                   count_if(year <> extract(year FROM dt_referencia)
                            OR month <> extract(month FROM dt_referencia)),
                   count(DISTINCT (year, month))
            FROM {source}
            """
        ).fetchone()
        columns = [
            item[0] for item in connection.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()
        ]
    if row is None:  # pragma: no cover - an aggregate query always returns a row
        raise VerificationError("no result from the read-back query")
    rows, distinct_ids, min_date, max_date, wrong_partition, periods = row
    if rows != expected_rows:
        raise VerificationError(f"read back {rows} rows, expected {expected_rows}")
    if wrong_partition:
        raise VerificationError(f"{wrong_partition} rows are stored in the wrong partition")
    missing = sorted(set(SELECTED_NAMES) - set(columns))
    if missing:
        raise VerificationError(f"published files lack contract columns: {missing}")
    return {
        "engine": f"duckdb {duckdb.__version__}",
        "rows": rows,
        "distinct_id_basica": distinct_ids,
        "ids_repeated_across_months": rows - distinct_ids,
        "min_reference_date": str(min_date),
        "max_reference_date": str(max_date),
        "periods": periods,
        "rows_in_wrong_partition": wrong_partition,
    }


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def build_report(
    *,
    mode: str,
    source: dict[str, object],
    rules: RulesConfig,
    fingerprint: str,
    ranges: list[ByteRange],
    chunk_stats: list[dict[str, Any]],
    results: list[PeriodResult],
    period_rows: list[dict[str, Any]],
    totals: dict[str, int],
    verification: dict[str, Any],
    elapsed_seconds: float,
    bytes_processed_now: int,
    peak_rss_bytes: int,
    report_dir: Path,
) -> dict[str, Any]:
    """Aggregate chunk and month statistics and write JSON, Markdown and Parquet."""
    totals["rows_published"]
    reasons: Counter[str] = Counter()
    invalid: Counter[str] = Counter()
    chunk_flags: Counter[str] = Counter()
    nulls: Counter[str] = Counter()
    for stats in chunk_stats:
        reasons.update(stats["reject_reasons"])
        invalid.update(stats["invalid_values"])
        chunk_flags.update(stats["flags"])
        nulls.update(stats["nulls"])
    if totals["duplicate_ids_removed"]:
        reasons["duplicate_id_basica"] = totals["duplicate_ids_removed"]

    # Month-level flag counts are exact after id de-duplication, so they take priority.
    published_flags = {
        flag: sum(int(row[flag] or 0) for row in period_rows)
        for flag in (*CHUNK_FLAGS, DUPLICATE_FLAG)
    }
    parquet_bytes = sum(result.bytes_written for result in results)
    bytes_read = sum(item.size for item in ranges)
    source_bytes = int(str(source["size_bytes"]))
    # Reused chunks cost nothing, so counting them would inflate the speed of a resumed run.
    throughput = bytes_processed_now / elapsed_seconds if elapsed_seconds else 0.0

    by_year: dict[int, dict[str, Any]] = {}
    for row in period_rows:
        year = by_year.setdefault(
            row["year"],
            {
                "year": row["year"], "months": 0, "rows": 0, "takeoffs": 0, "seats": 0,
                "paid_passengers": 0, "null_excess": 0.0, DUPLICATE_FLAG: 0,
            },
        )  # fmt: skip
        year["months"] += 1
        year["rows"] += row["rows"]
        year["takeoffs"] += row["takeoffs"] or 0
        year["seats"] += row["seats"] or 0
        year["paid_passengers"] += row["paid_passengers"] or 0
        year["null_excess"] += (row["null_rate_excess_baggage"] or 0.0) * row["rows"]
        year[DUPLICATE_FLAG] += row[DUPLICATE_FLAG] or 0
    yearly = [
        {
            **{key: value for key, value in item.items() if key != "null_excess"},
            "null_rate_excess_baggage": _rate(item["null_excess"], item["rows"]),
        }
        for _, item in sorted(by_year.items())
    ]

    report: dict[str, Any] = {
        "mode": mode,
        "scope_warning": (
            None
            if mode == "full"
            else "Statistics describe sampled blocks of the file, not the whole dataset."
        ),
        "source": source,
        "rules": asdict(rules),
        "config_fingerprint": fingerprint,
        "coverage": {
            "chunks": len(ranges),
            "bytes_read": bytes_read,
            "source_bytes": source_bytes,
            "fraction_of_file": _rate(bytes_read, source_bytes),
        },
        "reconciliation": totals,
        "verification": verification,
        "reject_reasons": dict(sorted(reasons.items())),
        "invalid_values_by_column": dict(sorted(invalid.items())),
        "flags_on_published_rows": published_flags,
        "null_counts_before_id_dedup": dict(sorted(nulls.items())),
        "by_year": yearly,
        "performance": {
            "elapsed_seconds": round(elapsed_seconds, 2),
            "bytes_processed_this_invocation": bytes_processed_now,
            "chunk_seconds_all_invocations": round(
                sum(stats["elapsed_seconds"] for stats in chunk_stats), 2
            ),
            "peak_rss_gb": round(peak_rss_bytes / 1e9, 3),
            "throughput_mb_per_s": round(throughput / 1e6, 1),
            "parquet_bytes": parquet_bytes,
            "compression_ratio": round(bytes_read / parquet_bytes, 2) if parquet_bytes else None,
        },
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(report_dir / "quality_report.json", report)
    write_text_atomic(report_dir / "quality_report.md", _render_markdown(report))
    if period_rows:
        write_parquet_atomic(
            pl.DataFrame(period_rows, infer_schema_length=None).sort("year", "month"),
            report_dir / "quality_by_period.parquet",
            zstd_level=6,
        )
    return report


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def _render_markdown(report: dict[str, Any]) -> str:
    totals = report["reconciliation"]
    published = totals["rows_published"]
    performance = report["performance"]
    coverage = report["coverage"]
    verification = report["verification"]
    parts = [f"# Ingestion quality report ({report['mode']} run)"]
    if report["scope_warning"]:
        parts.append(f"> **Scope:** {report['scope_warning']}")
    parts.append(
        f"Source: `{report['source']['path']}`, {coverage['source_bytes']:,} bytes. "
        f"Read {coverage['bytes_read']:,} bytes in {coverage['chunks']} chunks "
        f"({coverage['fraction_of_file']:.2%} of the file)."
    )
    parts.append("## Reconciliation\n\n" + _table(
        ["Stage", "Rows"],
        [
            ["Lines read", f"{totals['lines_read']:,}"],
            ["Rejected in chunks", f"{totals['chunk_rejected_rows']:,}"],
            ["Valid after chunks", f"{totals['chunk_valid_rows']:,}"],
            ["Removed as repeated id_basica", f"{totals['duplicate_ids_removed']:,}"],
            ["**Published**", f"**{published:,}**"],
        ],
    ))  # fmt: skip
    parts.append(
        "## Independent read-back\n\n"
        f"{verification.get('engine', 'n/a')}: {verification.get('rows', 0):,} rows, "
        f"{verification.get('periods', 0)} months, reference dates from "
        f"{verification.get('min_reference_date')} to {verification.get('max_reference_date')}, "
        f"{verification.get('ids_repeated_across_months', 0):,} ids repeated across months."
    )
    reasons = report["reject_reasons"]
    parts.append("## Rejected rows\n\n" + (
        _table(["Reason", "Rows"], [[key, f"{value:,}"] for key, value in reasons.items()])
        if reasons else "None."
    ))  # fmt: skip
    invalid = report["invalid_values_by_column"]
    parts.append("## Unparseable values (set to null, row kept)\n\n" + (
        _table(["Column", "Values"], [[key, f"{value:,}"] for key, value in invalid.items()])
        if invalid else "None."
    ))  # fmt: skip
    flags = sorted(report["flags_on_published_rows"].items(), key=lambda item: -item[1])
    parts.append("## Flags on published rows\n\n" + _table(
        ["Flag", "Rows", "Share"],
        [[key, f"{value:,}", f"{_rate(value, published):.3%}"] for key, value in flags],
    ))  # fmt: skip
    parts.append("## By year\n\n" + _table(
        ["Year", "Months", "Rows", "Takeoffs", "Paid pax", "Excess baggage null", "Duplicates"],
        [
            [
                str(item["year"]), str(item["months"]), f"{item['rows']:,}",
                f"{item['takeoffs']:,}", f"{item['paid_passengers']:,}",
                f"{item['null_rate_excess_baggage']:.1%}", f"{item[DUPLICATE_FLAG]:,}",
            ]
            for item in report["by_year"]
        ],
    ))  # fmt: skip
    parts.append(
        "## Performance\n\n"
        f"This invocation: {performance['elapsed_seconds']} s, peak RSS "
        f"{performance['peak_rss_gb']} GB, {performance['throughput_mb_per_s']} MB/s on "
        f"{performance['bytes_processed_this_invocation']:,} newly processed bytes. "
        f"All invocations: {performance['chunk_seconds_all_invocations']} s in chunks, "
        f"compression ratio {performance['compression_ratio']}x."
    )
    return "\n\n".join(parts) + "\n"
