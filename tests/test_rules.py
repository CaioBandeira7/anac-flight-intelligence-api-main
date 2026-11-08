from __future__ import annotations

from datetime import date, datetime, time

import polars as pl
import pytest

from anac.config import RulesConfig
from anac.ingestion.parsing import parse_raw_chunk
from anac.validation import rules as r
from tests.conftest import csv_line, raw_bytes

RULES = RulesConfig()


def validated(*lines: str) -> r.ValidatedChunk:
    return r.validate_chunk(parse_raw_chunk(raw_bytes(*lines), 1).frame, 1, RULES)


def one(**overrides: str) -> dict[str, object]:
    result = validated(csv_line(**overrides))
    assert result.rejects.is_empty(), result.rejects
    return result.valid.row(0, named=True)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,45", 1.45),
        ("247,828", 247.828),
        ("2347.0", 2347.0),
        ("0", 0.0),
        ("-3,5", -3.5),
        ("1.234,56", 1234.56),
        ("1.234.567,8", 1234567.8),
        ("1.234", 1.234),
        ("3,98888e-05", 3.98888e-05),
        ("7.1e+06", 7.1e6),
        ("Inf", None),
        ("-inf", None),
        ("NaN", None),
        ("abc", None),
        ("1,2,3", None),
        ("12,", None),
        ("1e999", None),
        (None, None),
    ],
)
def test_decimal_expression(text: str | None, expected: float | None) -> None:
    frame = pl.DataFrame({"x": [text]}, schema={"x": pl.String})
    assert frame.select(r.decimal_expr("x")).item() == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("75", 75), ("75.0", 75), ("75,0", 75), ("75.5", None), ("99999999999", None), ("x", None)],
)
def test_integer_expression_never_truncates(text: str, expected: int | None) -> None:
    frame = pl.DataFrame({"x": [text]})
    assert frame.select(r.integer_expr("x", pl.Int32())).item() == expected


@pytest.mark.parametrize("text", ["2024-13-01", "2024-02-30", "01/02/2024", "2024-1-1", "20240101"])
def test_invalid_dates_become_null(text: str) -> None:
    assert pl.DataFrame({"x": [text]}).select(r.date_expr("x")).item() is None


def test_happy_row_has_expected_types_and_values() -> None:
    row = one()
    assert row["id_basica"] == 1000
    assert row["dt_referencia"] == date(2013, 8, 1)
    assert row["hr_partida_real"] == time(8, 27)
    assert row["partida_real_ts"] == datetime(2013, 8, 1, 8, 27)
    assert row["nr_horas_voadas"] == 1.45
    assert row["nr_assentos_ofertados"] == 118
    assert row["route_icao"] == "SBCT-SBGR"
    assert row["load_factor_paid"] == pytest.approx(75 / 118)
    assert row["has_excess_baggage"] is True
    assert row["is_international"] is False
    flags = {key: value for key, value in row.items() if key.startswith("dq_")}
    assert not any(flags.values()), flags


def test_output_schema_is_identical_for_any_content() -> None:
    first = validated(csv_line())
    second = validated(csv_line(nr_passag_pagos="", kg_bagagem_excesso="", dt_partida_real=""))
    assert first.valid.schema == second.valid.schema


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"id_basica": ""}, r.REASON_INVALID_ID),
        ({"id_basica": "abc"}, r.REASON_INVALID_ID),
        ({"id_basica": "10.5"}, r.REASON_INVALID_ID),
        ({"dt_referencia": ""}, r.REASON_INVALID_DATE),
        ({"dt_referencia": "2024-99-01"}, r.REASON_INVALID_DATE),
        ({"dt_referencia": "1999-12-31"}, r.REASON_DATE_RANGE),
        ({"dt_referencia": "2026-01-01"}, r.REASON_DATE_RANGE),
        ({"sg_icao_origem": ""}, r.REASON_MISSING_AIRPORT),
        ({"sg_icao_destino": "   "}, r.REASON_MISSING_AIRPORT),
    ],
)
def test_hard_rejects_keep_reason_line_and_raw_content(
    overrides: dict[str, str], reason: str
) -> None:
    result = validated(csv_line(id_basica="5.0"), csv_line(**overrides))
    assert result.valid.height == 1
    assert result.rejects["reason"].to_list() == [reason]
    assert result.rejects["source_line"].to_list() == [1]
    assert result.rejects["chunk_id"].to_list() == [1]
    assert "AZUL LINHAS" in result.rejects["raw_record"][0]


@pytest.mark.parametrize(
    ("overrides", "flag"),
    [
        ({"nr_mes_referencia": "9"}, "dq_reference_period_mismatch"),
        ({"dt_partida_real": ""}, "dq_missing_departure"),
        (
            {"dt_partida_real": "2015-08-01", "dt_chegada_real": "2015-08-01"},
            "dq_departure_reference_gap",
        ),
        ({"dt_chegada_real": "2013-07-31"}, "dq_arrival_before_departure"),
        ({"nr_horas_voadas": "6578,88"}, "dq_implausible_flight_hours"),
        ({"nr_horas_voadas": "5,0"}, "dq_hours_clock_mismatch"),
        ({"nr_decolagem": "0"}, "dq_no_takeoff"),
        ({"nr_passag_pagos": "118.0", "nr_passag_gratis": "1.0"}, "dq_pax_exceed_seats"),
        ({"nr_assentos_ofertados": "0.0"}, "dq_pax_without_seats"),
        ({"km_distancia": "0.0"}, "dq_zero_distance"),
        ({"sg_icao_destino": "SBCT"}, "dq_same_origin_destination"),
        ({"nr_passag_gratis": "-1.0"}, "dq_negative_metric"),
        ({"nr_ask": "1.0"}, "dq_ask_mismatch"),
        ({"nr_rpk": "1.0"}, "dq_rpk_mismatch"),
        ({"sg_icao_destino": "SN6L"}, "dq_icao_nonstandard"),
        ({"nr_passag_pagos": "abc"}, "dq_parse_error"),
    ],
)
def test_each_soft_rule_flags_and_keeps_the_row(overrides: dict[str, str], flag: str) -> None:
    assert one(**overrides)[flag] is True


def test_rounding_in_ask_is_not_flagged() -> None:
    assert one(nr_ask="42363.0")["dq_ask_mismatch"] is False


def test_invalid_values_are_counted_per_column_and_nulled() -> None:
    result = validated(csv_line(nr_passag_pagos="abc", nr_horas_voadas="x"), csv_line())
    assert result.invalid_counts == {"nr_passag_pagos": 1, "nr_horas_voadas": 1}
    assert result.valid["nr_passag_pagos"].to_list() == [None, 75]


def test_inf_is_not_a_valid_measure() -> None:
    result = validated(csv_line(nr_rpk="Inf"))
    assert result.invalid_counts == {"nr_rpk": 1}
    assert result.valid["nr_rpk"][0] is None


def test_missing_value_is_not_counted_as_invalid() -> None:
    result = validated(csv_line(kg_bagagem_excesso=""))
    assert result.invalid_counts == {}
    assert result.valid["dq_parse_error"][0] is False


@pytest.mark.parametrize(
    ("origin", "destination", "nature", "international", "mismatch"),
    [
        ("BRASIL", "BRASIL", "DOMÉSTICA", False, False),
        # Same continent, but it crosses the border. The original rule got this wrong.
        ("BRASIL", "ARGENTINA", "INTERNACIONAL", True, False),
        ("ESTADOS UNIDOS DA AMÉRICA", "BRASIL", "INTERNACIONAL", True, False),
        # Domestic geography under an international regulatory nature: real, flagged.
        ("BRASIL", "BRASIL", "INTERNACIONAL", False, True),
        ("BRASIL", "CHILE", "DOMÉSTICA", True, True),
    ],
)
def test_international_uses_countries(
    origin: str, destination: str, nature: str, international: bool, mismatch: bool
) -> None:
    row = one(nm_pais_origem=origin, nm_pais_destino=destination, ds_natureza_etapa=nature)
    assert row["is_international"] is international
    assert row["dq_nature_geography_mismatch"] is mismatch


def test_unknown_country_gives_unknown_international() -> None:
    assert one(nm_pais_destino="")["is_international"] is None


def test_load_factor_is_not_clipped_and_is_null_without_seats() -> None:
    assert one(nr_passag_pagos="150.0")["load_factor_paid"] == pytest.approx(150 / 118)
    assert one(nr_assentos_ofertados="0.0", nr_passag_pagos="0.0")["load_factor_paid"] is None


@pytest.mark.parametrize(("text", "expected"), [("42.0", True), ("0.0", False), ("", None)])
def test_missing_baggage_is_not_treated_as_no_excess(text: str, expected: bool | None) -> None:
    assert one(kg_bagagem_excesso=text)["has_excess_baggage"] is expected


def test_string_fields_are_trimmed_and_empty_becomes_null() -> None:
    row = one(ds_matricula="AXU ", sg_empresa_iata="   ")
    assert row["ds_matricula"] == "AXU"
    assert row["sg_empresa_iata"] is None
