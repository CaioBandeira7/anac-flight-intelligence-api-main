from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from anac.config import MB
from anac.ingestion import chunking
from anac.ingestion.contract import SOURCE_COLUMNS, SchemaDriftError
from tests.conftest import csv_line, header_line, many_rows, write_csv


def test_header_matches_contract(tmp_path: Path) -> None:
    columns, offset = chunking.read_header(write_csv(tmp_path / "a.csv", many_rows(1)))
    assert tuple(columns) == SOURCE_COLUMNS
    assert offset == len(header_line()) + 1


def test_bom_in_header_is_accepted(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "a.csv", many_rows(1))
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    assert tuple(chunking.read_header(path)[0]) == SOURCE_COLUMNS


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda c: c[:-1], "missing"),
        (lambda c: [*c, "coluna_nova"], "unexpected"),
        (lambda c: [c[1], c[0], *c[2:]], "order"),
    ],
)
def test_schema_drift_is_named(tmp_path: Path, change, message: str) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "drift.csv"
    path.write_text(",".join(change(list(SOURCE_COLUMNS))) + "\n", encoding="utf-8")
    with pytest.raises(SchemaDriftError, match=message):
        chunking.read_header(path)


@pytest.mark.parametrize("chunk_bytes", [700, 5_000, 64_000, 10 * MB])
def test_full_plan_tiles_data_section_exactly(tmp_path: Path, chunk_bytes: int) -> None:
    path = write_csv(tmp_path / "a.csv", many_rows(500))
    ranges = chunking.plan_full(path, chunk_bytes)
    _, data_start = chunking.read_header(path)
    assert ranges[0].start == data_start
    assert ranges[-1].end == path.stat().st_size
    for left, right in itertools.pairwise(ranges):
        assert left.end == right.start


@pytest.mark.parametrize("chunk_bytes", [0, -1])
def test_non_positive_chunk_size_is_refused(tmp_path: Path, chunk_bytes: int) -> None:
    # Regression: a zero size never advanced the boundary and looped forever.
    path = write_csv(tmp_path / "a.csv", many_rows(3))
    with pytest.raises(ValueError, match="positive"):
        chunking.plan_full(path, chunk_bytes)


def test_chunks_contain_whole_lines_only(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "a.csv", many_rows(300))
    total = 0
    for byte_range in chunking.plan_full(path, 5_000):
        raw = chunking.read_range(path, byte_range)
        assert raw.endswith(b"\n")
        assert raw.split(b",", 1)[0].replace(b".0", b"").isdigit()
        total += raw.count(b"\n")
    assert total == 300


def test_boundary_skips_a_line_that_is_not_a_record_start(tmp_path: Path) -> None:
    good = csv_line()
    path = write_csv(tmp_path / "a.csv", [good, "not,a,record", good])
    _, data_start = chunking.read_header(path)
    with path.open("rb") as handle:
        boundary = chunking.next_record_boundary(
            handle, data_start, path.stat().st_size, len(SOURCE_COLUMNS)
        )
    assert boundary == data_start + len(good.encode()) + 1 + len("not,a,record\n")


def test_sample_plan_is_deterministic_and_non_overlapping(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "a.csv", many_rows(3000))
    first = chunking.plan_sample(path, 5, 40_000, seed=7)
    assert first == chunking.plan_sample(path, 5, 40_000, seed=7)
    assert first != chunking.plan_sample(path, 5, 40_000, seed=8)
    for left, right in itertools.pairwise(first):
        assert left.end <= right.start


def test_sample_plan_rejects_file_too_small(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "a.csv", many_rows(3))
    with pytest.raises(ValueError, match="too small"):
        chunking.plan_sample(path, 5, 1 * MB, seed=1)


def test_fingerprint_detects_content_change_of_same_size(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "a.csv", many_rows(5))
    before = chunking.fingerprint_source(path)
    content = bytearray(path.read_bytes())
    content[-2] = ord("9") if content[-2] != ord("9") else ord("8")
    path.write_bytes(bytes(content))
    assert chunking.fingerprint_source(path).edge_sha256 != before.edge_sha256
