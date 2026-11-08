from __future__ import annotations

from anac.ingestion.parsing import (
    REASON_BLANK,
    REASON_ENCODING,
    REASON_FIELD_COUNT,
    parse_raw_chunk,
)
from tests.conftest import csv_line, raw_bytes


def test_clean_chunk_keeps_values_and_quoted_decimal_commas() -> None:
    parsed = parse_raw_chunk(raw_bytes(csv_line(), csv_line(id_basica="2.0")), chunk_id=3)
    assert parsed.lines_total == 2
    assert parsed.malformed.is_empty()
    assert parsed.frame.height == 2
    assert parsed.frame["nr_horas_voadas"].to_list() == ["1,45", "1,45"]
    assert parsed.frame["nm_empresa"][0] == "AZUL LINHAS AÉREAS BRASILEIRAS S/A"
    assert parsed.frame["_source_line"].to_list() == [0, 1]


def test_extra_and_missing_fields_are_quarantined_not_truncated() -> None:
    good = csv_line()
    parsed = parse_raw_chunk(raw_bytes(good, good + ",extra", ",".join(good.split(",")[:50])), 0)
    assert parsed.lines_total == 3
    assert parsed.frame["_source_line"].to_list() == [0]
    assert parsed.malformed["reason"].to_list() == [REASON_FIELD_COUNT, REASON_FIELD_COUNT]
    assert parsed.malformed["source_line"].to_list() == [1, 2]


def test_unbalanced_quote_is_quarantined() -> None:
    good = csv_line()
    parsed = parse_raw_chunk(raw_bytes(good, good.replace('"1,45"', '"1,45')), 0)
    assert parsed.frame.height == 1
    assert parsed.malformed["reason"].to_list() == [REASON_FIELD_COUNT]


def test_newline_inside_quotes_is_counted_rather_than_silently_merged() -> None:
    good = csv_line()
    broken = good.replace("AZUL LINHAS", '"AZUL\nLINHAS')
    parsed = parse_raw_chunk(raw_bytes(good, broken), 0)
    assert parsed.frame.height == 1
    assert parsed.lines_total == parsed.frame.height + parsed.malformed.height


def test_invalid_utf8_line_is_quarantined_with_escaped_bytes() -> None:
    good = csv_line().encode()
    raw = good + b"\n" + good.replace("AÉ".encode(), b"A\xc9") + b"\n" + good + b"\n"
    parsed = parse_raw_chunk(raw, 0)
    assert parsed.lines_total == 3
    assert parsed.frame["_source_line"].to_list() == [0, 2]
    assert parsed.malformed["reason"].to_list() == [REASON_ENCODING]
    assert "\\xc9" in parsed.malformed["raw_record"][0]


def test_blank_line_is_counted() -> None:
    parsed = parse_raw_chunk(raw_bytes(csv_line(), "", csv_line()), 0)
    assert parsed.frame["_source_line"].to_list() == [0, 2]
    assert parsed.malformed["reason"].to_list() == [REASON_BLANK]


def test_crlf_does_not_leak_into_last_column() -> None:
    line = csv_line(nr_linha="77.0")
    parsed = parse_raw_chunk(f"{line}\r\n{line}\r\n".encode(), 0)
    assert parsed.malformed.is_empty()
    assert parsed.frame["nr_linha"].to_list() == ["77.0", "77.0"]


def test_empty_chunk_and_all_bad_chunk() -> None:
    assert parse_raw_chunk(b"", 0).lines_total == 0
    parsed = parse_raw_chunk(b"a,b\nc,d\n", 0)
    assert parsed.frame.is_empty()
    assert parsed.malformed.height == 2
