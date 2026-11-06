"""Synthetic CSV builder. These rows are test fixtures, never real results."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from anac.config import IngestionConfig
from anac.ingestion.contract import SOURCE_COLUMNS

BASE_ROW: dict[str, str] = {
    "id_basica": "1000.0",
    "id_empresa": "1000909",
    "sg_empresa_icao": "AZU",
    "nm_empresa": "AZUL LINHAS AÉREAS BRASILEIRAS S/A",
    "nm_pais": "BRASIL",
    "nr_voo": "6956",
    "cd_di": "0",
    "ds_di": "REGULAR PREVISTO EM HOTRAN",
    "ds_grupo_di": "REGULAR",
    "dt_referencia": "2013-08-01",
    "nr_ano_referencia": "2013",
    "nr_mes_referencia": "8",
    "ds_natureza_etapa": "DOMÉSTICA",
    "hr_partida_real": "08:27:00",
    "dt_partida_real": "2013-08-01",
    "sg_icao_origem": "SBCT",
    "nm_pais_origem": "BRASIL",
    "nm_continente_origem": "AMÉRICA DO SUL",
    "nr_etapa": "1",
    "hr_chegada_real": "09:54:00",
    "dt_chegada_real": "2013-08-01",
    "sg_icao_destino": "SBGR",
    "nm_pais_destino": "BRASIL",
    "nm_continente_destino": "AMÉRICA DO SUL",
    "lt_combustivel": "2347.0",
    "nr_assentos_ofertados": "118.0",
    "kg_payload": "15505.0",
    "km_distancia": "359.0",
    "nr_passag_pagos": "75.0",
    "nr_passag_gratis": "1.0",
    "kg_bagagem_livre": "391.0",
    "kg_bagagem_excesso": "42.0",
    "kg_carga_paga": "4.0",
    "kg_carga_gratis": "0.0",
    "kg_correio": "0.0",
    "nr_decolagem": "1",
    "nr_horas_voadas": "1,45",
    "kg_peso": "6137.0",
    "nr_velocidade_media": "247,828",
    "nr_ask": "42362.0",
    "nr_rpk": "26925.0",
    "nr_atk": "5566.0",
    "nr_rtk": "2176.0",
    "id_arquivo": "8967",
    "nm_arquivo": "AZUAGO13.txt",
    "nr_linha": "15843.0",
    "dt_sistema": "2019-08-25 22:57:15",
}


def csv_line(**overrides: str) -> str:
    """Render one source line, quoting decimal commas the way the real file does."""
    values = {**BASE_ROW, **overrides}
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="").writerow(
        [values.get(name, "") for name in SOURCE_COLUMNS]
    )
    return buffer.getvalue()


def header_line() -> str:
    return ",".join(SOURCE_COLUMNS)


def raw_bytes(*lines: str) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_csv(path: Path, lines: Iterable[str]) -> Path:
    path.write_bytes(("\n".join([header_line(), *lines]) + "\n").encode("utf-8"))
    return path


def many_rows(count: int) -> list[str]:
    """Rows with unique ids, spread over 2013-08, 2013-09 and 2020-01, out of order."""
    periods = [("2013-08", "2013", "8"), ("2020-01", "2020", "1"), ("2013-09", "2013", "9")]
    lines = []
    for index in range(count):
        month, year, number = periods[index % len(periods)]
        day = f"{month}-{(index % 28) + 1:02d}"
        lines.append(
            csv_line(
                id_basica=f"{index + 1}.0",
                nr_voo=str(1000 + index),
                dt_referencia=day,
                dt_partida_real=day,
                dt_chegada_real=day,
                nr_ano_referencia=year,
                nr_mes_referencia=number,
            )
        )
    return lines


@pytest.fixture
def make_config(tmp_path: Path) -> Callable[..., IngestionConfig]:
    def _make(source: Path, **overrides: object) -> IngestionConfig:
        defaults: dict[str, object] = {
            "source_csv": source,
            "full_output_root": tmp_path / "full",
            "sample_output_root": tmp_path / "sample",
            "full_report_dir": tmp_path / "full" / "reports",
            "chunk_size_mb": 1,
            "sample_blocks": 2,
            "sample_block_mb": 1,
            # The free-RAM guard reads the real machine. Tests must not depend on it,
            # so the one test that exercises the guard turns it on explicitly.
            "memory_min_available_gb": 0.0,
        }
        return IngestionConfig(**{**defaults, **overrides})  # type: ignore[arg-type]

    return _make
