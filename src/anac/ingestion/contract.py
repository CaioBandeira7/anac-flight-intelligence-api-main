"""Data contract of the raw ANAC CSV.

``Availability`` records *when* a value becomes known relative to departure. The
ingestion layer keeps all of them; later feature code must use this to avoid
leaking post-flight values into a forecast.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

CONTRACT_VERSION: Final = "1"

SOURCE_COLUMNS: Final[tuple[str, ...]] = (
    "id_basica", "id_empresa", "sg_empresa_icao", "sg_empresa_iata", "nm_empresa", "nm_pais",
    "ds_tipo_empresa", "nr_voo", "nr_singular", "id_di", "cd_di", "ds_di", "ds_grupo_di",
    "dt_referencia", "nr_ano_referencia", "nr_semestre_referencia", "nm_semestre_referencia",
    "nr_trimestre_referencia", "nm_trimestre_referencia", "nr_mes_referencia",
    "nm_mes_referencia", "nr_semana_referencia", "nm_dia_semana_referencia",
    "nr_dia_referencia", "nr_ano_mes_referencia", "id_tipo_linha", "cd_tipo_linha",
    "ds_tipo_linha", "ds_natureza_tipo_linha", "ds_servico_tipo_linha", "ds_natureza_etapa",
    "hr_partida_real", "dt_partida_real", "nr_ano_partida_real", "nr_semestre_partida_real",
    "nm_semestre_partida_real", "nr_trimestre_partida_real", "nm_trimestre_partida_real",
    "nr_mes_partida_real", "nm_mes_partida_real", "nr_semana_partida_real",
    "nm_dia_semana_partida_real", "nr_dia_partida_real", "nr_ano_mes_partida_real",
    "id_aerodromo_origem", "sg_icao_origem", "sg_iata_origem", "nm_aerodromo_origem",
    "nm_municipio_origem", "sg_uf_origem", "nm_regiao_origem", "nm_pais_origem",
    "nm_continente_origem", "nr_etapa", "hr_chegada_real", "dt_chegada_real",
    "nr_ano_chegada_real", "nr_semestre_chegada_real", "nm_semestre_chegada_real",
    "nr_trimestre_chegada_real", "nm_trimestre_chegada_real", "nr_mes_chegada_real",
    "nm_mes_chegada_real", "nr_semana_chegada_real", "nm_dia_semana_chegada_real",
    "nr_dia_chegada_real", "nr_ano_mes_chegada_real", "id_equipamento", "sg_equipamento_icao",
    "ds_modelo", "ds_matricula", "id_aerodromo_destino", "sg_icao_destino", "sg_iata_destino",
    "nm_aerodromo_destino", "nm_municipio_destino", "sg_uf_destino", "nm_regiao_destino",
    "nm_pais_destino", "nm_continente_destino", "nr_escala_destino", "lt_combustivel",
    "nr_assentos_ofertados", "kg_payload", "km_distancia", "nr_passag_pagos",
    "nr_passag_gratis", "kg_bagagem_livre", "kg_bagagem_excesso", "kg_carga_paga",
    "kg_carga_gratis", "kg_correio", "nr_decolagem", "nr_horas_voadas", "kg_peso",
    "nr_velocidade_media", "nr_pax_gratis_km", "nr_carga_paga_km", "nr_carga_gratis_km",
    "nr_correio_km", "nr_bagagem_paga_km", "nr_bagagem_gratis_km", "nr_ask", "nr_rpk", "nr_atk",
    "nr_rtk", "id_arquivo", "nm_arquivo", "nr_linha", "dt_sistema", "nr_chave",
)  # fmt: skip


class Kind(StrEnum):
    STRING = "string"
    INT32 = "int32"
    INT64 = "int64"
    FLOAT = "float"
    DATE = "date"
    TIME = "time"


class Availability(StrEnum):
    IDENTIFIER = "identifier"
    """Lineage or a row key. Never a model feature."""
    SCHEDULE = "schedule"
    """Plausibly known before departure (carrier, route, flight number, reference date)."""
    OPERATED = "operated"
    """Recorded as operated. Not assumed known at forecast time."""
    OUTCOME = "outcome"
    """Measured after the flight: passengers, baggage, fuel. Valid only as lagged history."""


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    kind: Kind
    availability: Availability


def _spec(kind: Kind, availability: Availability, *names: str) -> list[ColumnSpec]:
    return [ColumnSpec(name, kind, availability) for name in names]


SELECTED_COLUMNS: Final[tuple[ColumnSpec, ...]] = tuple(
    _spec(Kind.INT64, Availability.IDENTIFIER, "id_basica")
    + _spec(
        Kind.STRING,
        Availability.SCHEDULE,
        "id_empresa",
        "sg_empresa_icao",
        "sg_empresa_iata",
        "nm_empresa",
        "nm_pais",
        "ds_tipo_empresa",
        "nr_voo",
        "cd_di",
        "ds_di",
        "ds_grupo_di",
        "cd_tipo_linha",
        "ds_tipo_linha",
        "ds_natureza_tipo_linha",
        "ds_servico_tipo_linha",
        "ds_natureza_etapa",
        "sg_icao_origem",
        "sg_iata_origem",
        "nm_aerodromo_origem",
        "nm_municipio_origem",
        "sg_uf_origem",
        "nm_regiao_origem",
        "nm_pais_origem",
        "nm_continente_origem",
        "sg_icao_destino",
        "sg_iata_destino",
        "nm_aerodromo_destino",
        "nm_municipio_destino",
        "sg_uf_destino",
        "nm_regiao_destino",
        "nm_pais_destino",
        "nm_continente_destino",
    )
    + _spec(Kind.DATE, Availability.SCHEDULE, "dt_referencia")
    + _spec(Kind.INT32, Availability.SCHEDULE, "nr_ano_referencia", "nr_mes_referencia", "nr_etapa")
    + _spec(Kind.DATE, Availability.OPERATED, "dt_partida_real", "dt_chegada_real")
    + _spec(Kind.TIME, Availability.OPERATED, "hr_partida_real", "hr_chegada_real")
    + _spec(
        Kind.STRING,
        Availability.OPERATED,
        "sg_equipamento_icao",
        "ds_modelo",
        "ds_matricula",
    )
    + _spec(
        Kind.INT32,
        Availability.OPERATED,
        "nr_decolagem",
        "nr_assentos_ofertados",
    )
    + _spec(Kind.FLOAT, Availability.OPERATED, "km_distancia", "kg_payload", "nr_ask", "nr_atk")
    + _spec(Kind.INT32, Availability.OUTCOME, "nr_passag_pagos", "nr_passag_gratis")
    + _spec(
        Kind.FLOAT,
        Availability.OUTCOME,
        "lt_combustivel",
        "kg_bagagem_livre",
        "kg_bagagem_excesso",
        "kg_carga_paga",
        "kg_carga_gratis",
        "kg_correio",
        "nr_horas_voadas",
        "kg_peso",
        "nr_rpk",
        "nr_rtk",
    )
    + _spec(Kind.INT64, Availability.IDENTIFIER, "id_arquivo", "nr_linha")
    + _spec(Kind.STRING, Availability.IDENTIFIER, "nm_arquivo")
)

SPEC_BY_NAME: Final = {spec.name: spec for spec in SELECTED_COLUMNS}
SELECTED_NAMES: Final = tuple(spec.name for spec in SELECTED_COLUMNS)

_unknown = set(SELECTED_NAMES) - set(SOURCE_COLUMNS)
if _unknown:  # pragma: no cover - guards edits to this module
    raise RuntimeError(f"contract selects columns absent from the source: {sorted(_unknown)}")

NONNEGATIVE_METRICS: Final[tuple[str, ...]] = (
    "nr_assentos_ofertados", "nr_passag_pagos", "nr_passag_gratis", "km_distancia", "kg_payload",
    "nr_ask", "nr_atk", "lt_combustivel", "kg_bagagem_livre", "kg_bagagem_excesso",
    "kg_carga_paga", "kg_carga_gratis", "kg_correio", "nr_horas_voadas", "kg_peso", "nr_rpk",
    "nr_rtk",
)  # fmt: skip

LINEAGE_COLUMNS: Final[tuple[str, ...]] = ("_chunk_id", "_source_line")

DERIVED_COLUMNS: Final[tuple[str, ...]] = (
    "partida_real_ts", "chegada_real_ts", "route_icao", "is_international",
    "load_factor_paid", "has_excess_baggage",
)  # fmt: skip

CHUNK_FLAGS: Final[tuple[str, ...]] = (
    "dq_parse_error", "dq_reference_period_mismatch", "dq_missing_departure",
    "dq_departure_reference_gap", "dq_arrival_before_departure", "dq_implausible_flight_hours",
    "dq_hours_clock_mismatch", "dq_no_takeoff", "dq_pax_exceed_seats", "dq_pax_without_seats",
    "dq_zero_distance", "dq_same_origin_destination", "dq_negative_metric", "dq_ask_mismatch",
    "dq_rpk_mismatch", "dq_icao_nonstandard", "dq_nature_geography_mismatch",
)  # fmt: skip

DUPLICATE_FLAG: Final = "dq_duplicate_record"

CHUNK_OUTPUT_COLUMNS: Final[tuple[str, ...]] = (
    SELECTED_NAMES + DERIVED_COLUMNS + CHUNK_FLAGS + LINEAGE_COLUMNS
)


class SchemaDriftError(ValueError):
    """The CSV header does not match the data contract."""


def validate_header(columns: list[str]) -> None:
    """Fail loudly, naming the difference, if the source layout changed."""
    if tuple(columns) == SOURCE_COLUMNS:
        return
    missing = sorted(set(SOURCE_COLUMNS) - set(columns))
    extra = sorted(set(columns) - set(SOURCE_COLUMNS))
    detail = f"missing={missing} unexpected={extra}" if missing or extra else "column order changed"
    raise SchemaDriftError(f"CSV header violates contract v{CONTRACT_VERSION}: {detail}")
