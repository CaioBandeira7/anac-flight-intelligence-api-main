"""Split the CSV into line-aligned byte ranges without reading it into memory.

Byte ranges are the unit of work and of resumption: each is parsed on its own, so
peak memory depends on the chunk size and not on the 20 GB file size.
"""

from __future__ import annotations

import csv
import hashlib
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO

from anac.config import MB
from anac.ingestion.contract import validate_header

_RECORD_ID = re.compile(r"^\d+(\.\d+)?$")
_MAX_PROBE_LINES = 10_000
_FINGERPRINT_BYTES = 1 * MB
_SAMPLE_SLACK_BYTES = 1 * MB


@dataclass(frozen=True)
class ByteRange:
    """A half-open ``[start, end)`` range holding whole CSV lines."""

    chunk_id: int
    start: int
    end: int

    @property
    def size(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class SourceFingerprint:
    """Detects a source change on resume without hashing all 20 GB."""

    path: str
    size_bytes: int
    mtime_ns: int
    edge_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def fingerprint_source(path: Path) -> SourceFingerprint:
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        digest.update(handle.read(_FINGERPRINT_BYTES))
        handle.seek(max(0, stat.st_size - _FINGERPRINT_BYTES))
        digest.update(handle.read(_FINGERPRINT_BYTES))
    return SourceFingerprint(str(path), stat.st_size, stat.st_mtime_ns, digest.hexdigest())


def read_header(path: Path) -> tuple[list[str], int]:
    """Return validated column names and the byte offset where data starts."""
    with path.open("rb") as handle:
        line = handle.readline()
    text = line.decode("utf-8-sig").rstrip("\r\n")
    columns = next(csv.reader([text]))
    validate_header(columns)
    return columns, len(line)


def _is_record_start(line: bytes, n_fields: int) -> bool:
    """A line starts a record if it parses to the full width with a numeric id."""
    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError:
        return False
    fields = next(csv.reader([text.rstrip("\r\n")]), [])
    return len(fields) == n_fields and _RECORD_ID.match(fields[0]) is not None


def next_record_boundary(handle: BinaryIO, position: int, size: int, n_fields: int) -> int:
    """Return the offset of the first valid record strictly after ``position``.

    Probing a parsed record (not just a newline) keeps the boundary correct if a
    quoted field ever contains a newline. Lines skipped here stay in the previous
    range, where they are parsed and counted, so nothing is lost.
    """
    if position >= size:
        return size
    handle.seek(position)
    handle.readline()
    for _ in range(_MAX_PROBE_LINES):
        offset = handle.tell()
        line = handle.readline()
        if not line:
            return size
        if _is_record_start(line, n_fields):
            return offset
    raise ValueError(f"no valid record within {_MAX_PROBE_LINES} lines after byte {position}")


def plan_full(path: Path, chunk_bytes: int) -> list[ByteRange]:
    """Tile the data section with adjacent ranges: no gap, no overlap."""
    if chunk_bytes <= 0:
        raise ValueError(f"chunk size must be positive, got {chunk_bytes} bytes")
    columns, data_start = read_header(path)
    size = path.stat().st_size
    ranges: list[ByteRange] = []
    start = data_start
    with path.open("rb") as handle:
        while start < size:
            end = next_record_boundary(handle, start + chunk_bytes - 1, size, len(columns))
            ranges.append(ByteRange(len(ranges), start, end))
            start = end
    return ranges


def plan_sample(path: Path, blocks: int, block_bytes: int, seed: int) -> list[ByteRange]:
    """Draw one block per equal-width stratum of the file.

    The CSV is grouped by monthly source file and is not chronological, so reading
    its first rows would only cover a few carriers and months.
    """
    columns, data_start = read_header(path)
    size = path.stat().st_size
    data_size = size - data_start
    stratum = data_size // blocks
    # A block may overrun by one line when aligned: the slack keeps neighbours apart.
    slack = min(_SAMPLE_SLACK_BYTES, block_bytes // 4)
    jitter_room = stratum - block_bytes - slack
    if jitter_room <= 0:
        raise ValueError(
            f"file too small for {blocks} blocks of {block_bytes} bytes; lower the sample size"
        )
    rng = random.Random(seed)
    ranges: list[ByteRange] = []
    with path.open("rb") as handle:
        for index in range(blocks):
            candidate = data_start + index * stratum + rng.randrange(jitter_room)
            start = next_record_boundary(handle, candidate, size, len(columns))
            end = next_record_boundary(handle, start + block_bytes - 1, size, len(columns))
            if end > start:
                ranges.append(ByteRange(len(ranges), start, end))
    return ranges


def read_range(path: Path, byte_range: ByteRange) -> bytes:
    with path.open("rb") as handle:
        handle.seek(byte_range.start)
        return handle.read(byte_range.size)
