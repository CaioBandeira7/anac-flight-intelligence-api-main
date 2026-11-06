# Ingestion v2

Turns the 20 GB ANAC CSV into monthly Parquet files, with every input line accounted for. This is the first stage of ANAC Flight Intelligence 2.0. It replaces `01_ingestao.py`, which stays in the repository as a reference.

The full file was processed on 2026-11-06. Results, the independent audit and the reliability assessment are in [reports/ingestion/INGESTION_REPORT.md](../reports/ingestion/INGESTION_REPORT.md). Sample figures below are labelled as such.

## Quick start

Requires Python 3.12. Pinned dependencies (numpy 1.26, torch 2.4) in the original `requirements.txt` have no wheels for 3.14.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python -m pip install -e . --no-deps

.venv\Scripts\python -m pytest                     # tests
.venv\Scripts\anac-ingest sample                   # 20 blocks of 16 MB into data/sample/
.venv\Scripts\anac-ingest full --confirm-full      # whole file; rerun the same command to resume
.venv\Scripts\anac-ingest status                   # progress of the full run
```

## How it works

```text
CSV -> plan byte ranges -> for each chunk: check lines, type, validate -> publish chunk
                                                                             |
    report <- read back with DuckDB <- reconcile counts <- monthly Parquet <-+
```

| Output | Location |
|---|---|
| Clean flights | `data/processed/flights/year=YYYY/month=MM/data.parquet` |
| Rows removed as repeated ids | `data/processed/flights_rejects/` |
| Rows rejected while parsing or validating | `data/interim/ingestion/chunks/chunk=*/rejects.parquet` |
| Quality report (full run) | `reports/ingestion/quality_report.{md,json}`, `quality_by_period.parquet` |

Code lives in `src/anac/`: `ingestion/contract.py` (schema and column availability), `chunking.py`, `parsing.py`, `compaction.py`, `pipeline.py`, plus `validation/rules.py` and `validation/report.py`.

## Decisions

**Byte ranges instead of a streaming engine.** Each 128 MB range is processed alone and published atomically. That makes both memory and resumption simple to reason about: finished work is a directory that exists, or it is not finished. Chunk boundaries are placed on a line that parses to the full 111 fields, not on any newline.

**Two passes, because the file is not chronological.** Rows are grouped by source file, so one month can be spread across the CSV. Chunks write per-month pieces, then compaction merges them. For the same reason, sampling uses one random block per stratum of the file rather than its first rows.

**Partition by `dt_referencia`.** It was present in every sampled row and matched `nr_ano_referencia` and `nr_mes_referencia`. `dt_partida_real` is sometimes missing.

**Reject rarely, flag generously.** A row is rejected only if it cannot be identified or placed. Anything else suspicious keeps its row and gets a `dq_*` flag. Each model can then choose a policy, and changing that policy never requires re-ingesting.

| Rejected | Flagged and kept |
|---|---|
| Wrong field count, invalid UTF-8, blank line | Passengers above seats, passengers without seats |
| Missing or invalid `id_basica` | No takeoff, zero distance, same origin and destination |
| Missing, invalid or out-of-range reference date | ASK or RPK disagreeing with seats x km or passengers x km |
| Missing airport code | Implausible hours, arrival before departure, departure far from reference date |
| Repeated `id_basica` within a month | Same leg under a different id, regulatory nature disagreeing with geography, unparseable value |

**No value is clipped or imputed.** `load_factor_paid` can exceed 1, because that is evidence of a data problem. Missing baggage stays null in `has_excess_baggage` rather than becoming "no excess".

**International means crossing the border.** `is_international` compares origin and destination countries. The original rule compared the destination continent with `"América do Sul"`, while the data is uppercase, so it marked 100% of rows as international. Even with the case fixed, it would have called São Paulo to Buenos Aires domestic.

**Numbers.** `"1,45"`, `"2347.0"`, `"1.234,56"` and `"3,98e-05"` all parse. `Inf`, `NaN` and text become null and are counted per column. `"75.5"` in an integer column is invalid, not 75. A lone `"1.234"` is read as 1.234, because the source writes plain decimals with a dot.

**Dropped columns.** The calendar breakdowns (derivable), `nr_escala_destino` (empty in the sample), `nr_chave` and `dt_sistema` (not analytical), and `nr_velocidade_media` (contains `Inf`, and is derivable from distance and hours).

## Safety guarantees

Each one has a test in `tests/test_pipeline.py`.

- `full` refuses to start without `--confirm-full`.
- The run fails unless `lines read = valid + rejected` and `valid = published + repeated ids`.
- A second engine (DuckDB) reads the output back and must find the same row count and correct partitions.
- A crash during chunks or compaction resumes to the same data. Leftover `*.tmp-*` files never count as finished.
- A changed source file or changed rules stop the run instead of mixing outputs.
- An existing month built from other inputs, or altered since, is never overwritten.
- The source CSV is opened read-only.

## Measured on real samples

| Run | Read | Rows | Time | Peak RSS | Speed |
|---|---|---|---|---|---|
| 20 blocks x 16 MB | 336 MB (1.7%) | 365,766 | 9.4 s | 0.91 GB | 36 MB/s |
| 4 blocks x 128 MB | 537 MB (2.7%) | 594,310 | 11.1 s | 1.78 GB | 49 MB/s |
| 16 blocks x 128 MB | 2.15 GB (10.7%) | 2,346,304 | 46.0 s | 2.00 GB | 47 MB/s |

Full run: 22,120,241 rows in 151 chunks and 308 months, 8.0 minutes, 42 MB/s, peak RSS 2.37 GB, 1.18 GB of Parquet. RSS levelled off near 2 GB. The run stops safely, keeping finished work, if RSS passes 12 GB or free system RAM falls below 1 GB. Both are checked after each chunk and before each month is compacted.

An independent re-read with Python's `csv` module matched all 365,766 rows of the first sample on 10 checked columns, with no differences. The ASK and RPK checks also support the number parsing: only about 0.03% of rows in that sample disagree with seats x km or passengers x km.

The full run rejected no rows either, so rejection paths have only been exercised with synthetic data.

## What later stages must know

**Availability.** `contract.py` labels each column `schedule`, `operated` or `outcome`. Passengers, baggage, fuel, and actual times are known only after the flight, so they can only enter a forecast as lagged history. `nr_assentos_ofertados` is labelled `operated`, because this data records the aircraft that flew rather than the published schedule.

**Duplicates.** 26,040 legs repeat under a different `id_basica` with identical metrics, 97% of them in 2000 to 2002 (at most 1.75% of a year). Volume models should filter on `dq_duplicate_record`.

**Non-flights.** `DUPLICATED LEG` rows (`cd_di = D`) have `nr_decolagem = 0` and no seats. Cargo and positioning rows are also present. Each model needs an explicit scope filter, such as `ds_grupo_di` and seats above zero.

**Missing months.** The CSV has no rows for 2015-08, 2016-02, 2018-07 and 2020-08. Lags must be computed by date, never by position.

**Zero often means not reported.** Foreign carriers report baggage and fuel as null until 2019 and as zero from 2020, so `has_excess_baggage = false` and `lt_combustivel = 0` are unreliable for them. Among Brazilian carriers, the excess rate swings in ways that reflect reporting rather than behaviour. Model C must not use this column as it stands.

## Open questions

1. **Clock of the timestamps.** One clock is used for departure and arrival. The quietest domestic hour stays between 01:00 and 04:00 in all 26 years, which fits Brazilian time rather than UTC. The official data dictionary has not been found to confirm this.
2. **Missing months.** ANAC's official sources list all four. They have not been downloaded or integrated yet. See [etapa2_proposta.md](etapa2_proposta.md).
