"""Structural parsing of one byte range into string columns.

Polars' lenient options (``truncate_ragged_lines``, ``ignore_errors``, lossy UTF-8)
hide bad rows. Here every line is checked first and bad lines are quarantined, so
``lines_total`` always reconciles with ``parsed + malformed``.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import polars as pl

from anac.ingestion.contract import SELECTED_NAMES, SOURCE_COLUMNS

REASON_ENCODING = "invalid_encoding"
REASON_FIELD_COUNT = "wrong_field_count"
REASON_BLANK = "blank_line"

REJECT_SCHEMA = pl.Schema(
    {
        "chunk_id": pl.Int32,
        "source_line": pl.Int32,
        "reason": pl.String,
        "raw_record": pl.String,
    }
)

_ALL_STRINGS = {name: pl.String for name in SOURCE_COLUMNS}
# read_csv only accepts positions when has_header=False.
_SELECTED_POSITIONS = sorted(SOURCE_COLUMNS.index(name) for name in SELECTED_NAMES)


class ChunkIntegrityError(RuntimeError):
    """Parsed rows do not reconcile with lines read: the chunk must not be published."""


@dataclass(frozen=True)
class RawChunk:
    frame: pl.DataFrame
    """Selected columns as strings, plus ``_source_line``."""
    malformed: pl.DataFrame
    """Quarantined lines, in ``REJECT_SCHEMA``."""
    lines_total: int


def _decode_lines(raw: bytes) -> tuple[list[str], list[tuple[int, str]]]:
    """Return decoded lines and ``(line_number, escaped_text)`` for undecodable ones."""
    try:
        return raw.decode("utf-8").split("\n"), []
    except UnicodeDecodeError:
        pass
    lines: list[str] = []
    bad: list[tuple[int, str]] = []
    for number, line in enumerate(raw.split(b"\n")):
        try:
            lines.append(line.decode("utf-8"))
        except UnicodeDecodeError:
            lines.append("")
            bad.append((number, line.decode("utf-8", errors="backslashreplace")))
    return lines, bad


def _malformed_frame(
    chunk_id: int, numbers: list[int], reasons: list[str], records: list[str]
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "chunk_id": [chunk_id] * len(numbers),
            "source_line": numbers,
            "reason": reasons,
            "raw_record": records,
        },
        schema=REJECT_SCHEMA,
    )


def parse_raw_chunk(raw: bytes, chunk_id: int) -> RawChunk:
    """Validate line structure, then parse the good lines with an all-string schema."""
    lines, encoding_failures = _decode_lines(raw)
    if lines and lines[-1] == "":
        lines.pop()  # the text after the final newline is not a line
    has_cr = b"\r" in raw
    expected_commas = len(SOURCE_COLUMNS) - 1
    bad_encoding = {number for number, _ in encoding_failures}

    checks = pl.DataFrame({"line": lines}, schema={"line": pl.String}).with_row_index("number")
    del lines
    if has_cr:
        checks = checks.with_columns(pl.col("line").str.strip_chars_end("\r"))
    checks = checks.with_columns(
        pl.col("line")
        .str.replace_all(r'"[^"]*"', "")
        .str.count_matches(",", literal=True)
        .alias("commas"),
        pl.col("line").str.count_matches('"', literal=True).alias("quotes"),
    )
    structurally_ok = (pl.col("commas") == expected_commas) & (pl.col("quotes") % 2 == 0)
    bad = checks.filter(~structurally_ok)

    numbers: list[int] = [number for number, _ in encoding_failures]
    reasons: list[str] = [REASON_ENCODING] * len(numbers)
    records: list[str] = [text for _, text in encoding_failures]
    for number, line in bad.select("number", "line").iter_rows():
        if number in bad_encoding:
            continue
        numbers.append(number)
        reasons.append(REASON_BLANK if line == "" else REASON_FIELD_COUNT)
        records.append(line)

    lines_total = checks.height
    good = checks.filter(structurally_ok).select("number", "line")
    good_numbers = good.get_column("number")
    del checks, bad

    if good.height == lines_total and not has_cr:
        payload = raw  # common case: no copy
    else:
        payload = ("\n".join(good.get_column("line").to_list()) + "\n").encode("utf-8")
    del good

    if good_numbers.len() == 0:
        frame = pl.DataFrame(schema={name: pl.String for name in SELECTED_NAMES})
    else:
        frame = pl.read_csv(
            io.BytesIO(payload),
            has_header=False,
            schema=_ALL_STRINGS,
            columns=_SELECTED_POSITIONS,
            quote_char='"',
            encoding="utf8",
            truncate_ragged_lines=False,
            ignore_errors=False,
            raise_if_empty=False,
        )
    if frame.height != good_numbers.len():
        raise ChunkIntegrityError(
            f"chunk {chunk_id}: {good_numbers.len()} structurally valid lines "
            f"but the CSV reader returned {frame.height} rows"
        )
    frame = frame.select(SELECTED_NAMES).with_columns(
        good_numbers.cast(pl.Int32).alias("_source_line")
    )
    return RawChunk(frame, _malformed_frame(chunk_id, numbers, reasons, records), lines_total)
