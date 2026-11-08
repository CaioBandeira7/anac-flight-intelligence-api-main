"""Check availability of the months missing from our CSV, using only small downloads. Read-only.

ANAC's aggregated open-data CSV is ordered by year, carrier and month, so one carrier's month can
be found by binary search with ranged reads. Control months are compared with our Parquet files to
test whether both sources agree before trusting the aggregate for the missing months.

    python scripts/probe_anac_portal.py [--out reports/ingestion]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import duckdb

OPEN_DATA = (
    "https://sistemas.anac.gov.br/dadosabertos/Voos%20e%20opera%C3%A7%C3%B5es%20a%C3%A9reas/"
)
AGGREGATE = (
    OPEN_DATA + "Dados%20Estat%C3%ADsticos%20do%20Transporte%20A%C3%A9reo/Dados_Estatisticos.csv"
)
MICRODATA = (
    "https://www.gov.br/anac/pt-br/assuntos/regulados/empresas-aereas/"
    "Instrucoes-para-a-elaboracao-e-apresentacao-das-demonstracoes-contabeis/"
    "envio-de-informacoes/basica/{year}/basica{year}-{month}.zip"
)
HEADERS = {"User-Agent": "anac-flight-intelligence-research"}
GAPS = [(2015, 8), (2016, 2), (2018, 7), (2020, 8)]
CONTROLS = [
    (2015, 7),
    (2015, 9),
    (2016, 1),
    (2016, 3),
    (2018, 6),
    (2018, 8),
    (2020, 7),
    (2020, 9),
    (2025, 12),
]
RECENT = [(2026, 1), (2026, 9)]
PROBE_BYTES = 16 * 1024


class Downloader:
    def __init__(self) -> None:
        self.total_bytes = 0

    def get(
        self, url: str, byte_range: str | None = None, method: str = "GET"
    ) -> tuple[int, dict[str, str], bytes]:
        headers = dict(HEADERS)
        if byte_range:
            headers["Range"] = byte_range
        request = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = response.read() if method == "GET" else b""
                self.total_bytes += len(body)
                return response.status, dict(response.headers), body
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers or {}), b""


def parse(text: str) -> list[list[str]]:
    rows = []
    for line in text.split("\n"):
        try:
            fields = next(csv.reader([line.rstrip("\r")], delimiter=";"))
        except StopIteration:
            continue
        if len(fields) == 38 and fields[3].isdigit() and fields[4].isdigit():
            rows.append(fields)
    return rows


def number(text: str) -> float:
    text = text.strip()
    if not text:
        return 0.0
    return float(text.replace(",", ".")) if "," in text else float(text)


def row_key(row: list[str]) -> tuple[int, str, int]:
    return (int(row[3]), row[0], int(row[4]))


def find_start(client: Downloader, size: int, target: tuple[int, str, int]) -> int:
    """Offset close to the first row of ``target``. The file is ordered by year, carrier, month."""
    low, high = 0, size
    while high - low > PROBE_BYTES:
        middle = (low + high) // 2
        _, _, body = client.get(AGGREGATE, f"bytes={middle}-{middle + PROBE_BYTES - 1}")
        rows = parse(body.decode("utf-8", "replace").split(chr(10), 1)[-1])
        if not rows:
            low = middle + PROBE_BYTES
            continue
        if row_key(rows[0]) < target:
            low = middle
        else:
            high = middle
    return low


def carrier_month(
    client: Downloader, size: int, carrier: str, year: int, month: int
) -> dict[str, Any]:
    start = find_start(client, size, (year, carrier, month))
    following = (year, carrier, month + 1)  # also lands at the next carrier when month is 12
    end = min(find_start(client, size, following) + 2 * PROBE_BYTES, size)
    _, _, body = client.get(AGGREGATE, f"bytes={start}-{end - 1}")
    rows = [
        r for r in parse(body.decode("utf-8", "replace")) if row_key(r) == (year, carrier, month)
    ]
    totals = {
        "rows": len(rows),
        "paid_pax": 0.0,
        "takeoffs": 0.0,
        "seats": 0.0,
        "rpk": 0.0,
        "ask": 0.0,
    }
    for row in rows:
        totals["paid_pax"] += number(row[19])
        totals["ask"] += number(row[24])
        totals["rpk"] += number(row[25])
        totals["takeoffs"] += number(row[30])
        totals["seats"] += number(row[34])
    return totals


def our_totals(glob: str) -> dict[tuple[str, int, int], dict[str, Any]]:
    with duckdb.connect() as connection:
        rows = connection.execute(
            f"""
            SELECT sg_empresa_icao, year, CAST(month AS INTEGER), sum(nr_passag_pagos), sum(nr_decolagem),
                   sum(nr_assentos_ofertados), sum(nr_rpk), sum(nr_ask)
            FROM read_parquet('{glob}', hive_partitioning=true)
            WHERE sg_empresa_icao IN ('AZU', 'GLO', 'TAM') AND year >= 2015
            GROUP BY 1, 2, 3
            """
        ).fetchall()
    return {
        (row[0], row[1], row[2]): dict(
            zip(["paid_pax", "takeoffs", "seats", "rpk", "ask"], row[3:], strict=True)
        )
        for row in rows
    }


def listing(client: Downloader, path: str) -> list[dict[str, str]]:
    status, _, body = client.get(OPEN_DATA + path)
    if status != 200:
        return [{"status": str(status)}]
    entries = []
    for name, detail in re.findall(
        r'href="([^"]+)"[^\n]*?</a>\s*([^\n<]*)', body.decode("utf-8", "replace")
    ):
        if name != "../":
            entries.append({"name": name, "detail": detail.strip()})
    return entries


def head_columns(client: Downloader, url: str) -> str:
    status, _, body = client.get(url, "bytes=0-3999")
    return f"status {status}: " + body.decode("latin-1", "replace")[:1400]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("reports/ingestion"))
    args = parser.parse_args()
    glob = (args.data_root / "processed/flights/*/*/*.parquet").as_posix()
    client = Downloader()
    result: dict[str, Any] = {"probed_on": "2026-11-06"}

    micro = []
    for year, month in GAPS:
        url = MICRODATA.format(year=year, month=f"{month:02d}")
        status, _, _ = client.get(url, method="HEAD")
        micro.append({"month": f"{year}-{month:02d}", "url": url, "script_status": status})
    result["microdata_scripted_access"] = micro

    status, headers, _ = client.get(AGGREGATE, method="HEAD")
    size = int(headers["Content-Length"])
    result["aggregate"] = {
        "url": AGGREGATE,
        "status": status,
        "bytes": size,
        "last_modified": headers.get("Last-Modified"),
    }

    ours = our_totals(glob)
    months = []
    for year, month in GAPS + CONTROLS + RECENT:
        role = (
            "gap" if (year, month) in GAPS else "control" if (year, month) in CONTROLS else "recent"
        )
        for carrier in ("AZU", "GLO", "TAM"):
            official = carrier_month(client, size, carrier, year, month)
            entry: dict[str, Any] = {
                "month": f"{year}-{month:02d}",
                "carrier": carrier,
                "role": role,
                "official": official,
            }
            mine = ours.get((carrier, year, month))
            if mine:
                entry["ours"] = mine
                entry["relative_difference"] = {
                    key: round(float(mine[key]) / official[key] - 1, 5) if official[key] else None
                    for key in ("paid_pax", "takeoffs", "seats", "rpk", "ask")
                }
            months.append(entry)
            print(
                entry["month"],
                carrier,
                role,
                round(official["paid_pax"]),
                official["rows"],
                flush=True,
            )
    result["months"] = months

    rsa_folder = "Registro%20de%20servi%C3%A7os%20a%C3%A9reos/2020/Agosto/"
    vra_folder = "Voo%20Regular%20Ativo%20%28VRA%29/2018/07%20-%20Julho/"
    result["rsa_top_listing"] = listing(client, "Registro%20de%20servi%C3%A7os%20a%C3%A9reos/")
    result["rsa_2020_08_listing"] = listing(client, rsa_folder)
    result["vra_2018_07_listing"] = listing(client, vra_folder)
    for key, base, entries in (
        ("rsa_sample_head", rsa_folder, result["rsa_2020_08_listing"]),
        ("vra_sample_head", vra_folder, result["vra_2018_07_listing"]),
    ):
        files = [
            item["name"] for item in entries if item.get("name") and not item["name"].endswith("/")
        ]
        if files:
            result[key] = head_columns(client, OPEN_DATA + base + files[0])
    result["total_bytes_downloaded_by_probe"] = client.total_bytes

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "anac_portal_probe.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
