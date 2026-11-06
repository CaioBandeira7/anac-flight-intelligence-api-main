# Recovering the missing months

The source CSV has no rows for 2015-08, 2016-02, 2018-07 and 2020-08. ANAC publishes these months, but its portal refuses scripted downloads, so the files must be downloaded by browser.

Save them, without renaming or unzipping, in `data/raw/supplements/`. `anac-ingest supplements status` shows what is present.

## Required

| File | Role | Link |
|---|---|---|
| `basica2015-08.zip` | Missing month | [Download](https://www.gov.br/anac/pt-br/assuntos/regulados/empresas-aereas/Instrucoes-para-a-elaboracao-e-apresentacao-das-demonstracoes-contabeis/envio-de-informacoes/basica/2015/basica2015-08.zip) |
| `basica2016-02.zip` | Missing month | [Download](https://www.gov.br/anac/pt-br/assuntos/regulados/empresas-aereas/Instrucoes-para-a-elaboracao-e-apresentacao-das-demonstracoes-contabeis/envio-de-informacoes/basica/2016/basica2016-02.zip) |
| `basica2018-07.zip` | Missing month | [Download](https://www.gov.br/anac/pt-br/assuntos/regulados/empresas-aereas/Instrucoes-para-a-elaboracao-e-apresentacao-das-demonstracoes-contabeis/envio-de-informacoes/basica/2018/basica2018-07.zip) |
| `basica2020-08.zip` | Missing month | [Download](https://www.gov.br/anac/pt-br/assuntos/regulados/empresas-aereas/Instrucoes-para-a-elaboracao-e-apresentacao-das-demonstracoes-contabeis/envio-de-informacoes/basica/2020/basica2020-08.zip) |
| `basica2018-06.zip` | Control: already in the base, to test that both sources agree | [Download](https://www.gov.br/anac/pt-br/assuntos/regulados/empresas-aereas/Instrucoes-para-a-elaboracao-e-apresentacao-das-demonstracoes-contabeis/envio-de-informacoes/basica/2018/basica2018-06.zip) |

## Optional

- **Later evaluation:** `basica2026-01.zip` to `basica2026-09.zip`, same pattern under `basica/2026/`. Published to `flights_eval_2026/`, a dataset no training code reads.
- **Revisions:** `basica2025-10.zip` to `basica2025-12.zip`, under `basica/2025/`. Only measured, never merged.

## Commands

```powershell
.venv\Scripts\anac-ingest supplements status
.venv\Scripts\anac-ingest supplements publish              # flights_v2_1/
.venv\Scripts\anac-ingest supplements publish-evaluation   # flights_eval_2026/
.venv\Scripts\anac-ingest supplements revisions
```

## What `publish` does

It stops at the first failed gate and publishes nothing. The source CSV and `flights/` are never changed.

1. **Schema:** every contract column exists. Separator, encoding, header case and a leading "Atualizado em" line are normalised.
2. **Granularity:** one row per `id_basica`, all in the declared month.
3. **Definitions:** in the control month, ids and values match the base row by row (at least 99%).
4. **Overlap:** no id of a new month is already in the base.
5. **Reference:** monthly takeoffs, seats, RPK and ASK within 0.5% of ANAC's aggregate.

Then it builds `flights_v2_1/` with a `_source` column per row, reads it back with DuckDB and publishes it with an atomic rename. It refuses to overwrite an existing version. The gates have only been tested on synthetic ZIPs: the official files could not be opened yet.

## After publishing

`anac-features` picks up `flights_v2_1` automatically. Existing outputs were built from `flights`, so point `paths.output` in `configs/features.toml` at `data/features/v2` and rebuild.

## What the official aggregate already confirms

`data/raw/supplements/reference/Dados_Estatisticos.csv` (361 MB, downloaded 2026-11-06, ignored by Git) covers all these months. Against our 308 months, in [reference_reconciliation.json](../reports/ingestion/reference_reconciliation.json):

- **Takeoffs and seats:** only 2025-12 differs by more than 0.1% (-0.7% and -0.6%), because the CSV is an older snapshot.
- **RPK and ASK:** 4 months differ by more than 0.1%, at most 0.39%.
- **Missing months:** 2015-08 has 90,871 takeoffs, 2016-02 has 81,973, 2018-07 has 87,730 and 2020-08 has 24,497.
- **Later months:** 2026-01 to 2026-09 are all present.
