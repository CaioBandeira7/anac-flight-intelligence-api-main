# Analytical layer

Monthly tables shared by Power BI and the API. They are built from the published flights, which are not changed.

```powershell
.venv\Scripts\anac-analytics build   # data/analytics/v1, about 2 minutes
```

The build validates before publishing and writes [validation.json](../reports/analytics/validation.json). Run again, it does nothing. If the dataset changed, it refuses to overwrite: use `--output data/analytics/v2`, and point the API at it with `ANAC_ANALYTICS_DIR`.

## Tables

Parquet in `data/analytics/v1/`, 29 MB in total. No CSV is needed, because Power BI reads Parquet directly.

| Table | Grain | Rows |
|---|---|---|
| `dim_month` | One per month, including months without data | 312 |
| `dim_airport` | One per ICAO code | 1,180 |
| `dim_carrier` | One per carrier ICAO code | 317 |
| `fact_route_carrier_month` | Month x carrier x origin x destination | 678,975 |
| `fact_route_month` | Month x origin x destination | 405,134 |
| `fact_carrier_month` | Month x carrier | 20,384 |
| `fact_airport_month` | Month x airport | 67,522 |

Every fact is rolled up from `fact_route_carrier_month`, so totals cannot diverge. Routes are directed: A to B and B to A are separate rows.

## Measures and units

`manifest.json` holds the description of every column, also served at `/v2/analytics/coverage`.

| Measure | Unit | Scope |
|---|---|---|
| `paid_passengers`, `free_passengers` | Count, per leg | Passenger |
| `seats`, `passenger_takeoffs` | Count | Passenger |
| `rpk` | Passenger-km | Passenger |
| `ask` | Seat-km | Passenger |
| `load_factor_paid` | Ratio from 0, may exceed 1 | Passenger |
| `all_takeoffs`, `source_rows`, `all_paid_passengers` | Count | All operated legs |
| `paid_cargo_kg`, `free_cargo_kg`, `mail_kg` | kg | All operated legs |
| `departures`, `arrivals`, `movements` | Count | All operated legs |
| `distance_km` | km, median | Not additive |
| `carriers`, `routes` | Count, distinct | Not additive |

**Passenger scope** is the same filter the models use: flights that took off, with seats, excluding non-revenue positioning, zero distance, the same origin and destination, and a paid load factor above 1.5. Across all years, that last rule removes 12,710 legs and 2.47 million passengers. It removes nothing in 2025.

**Never sum or average `load_factor_paid`.** Recompute it as the sum of `paid_passengers` over the sum of `seats`. An average of ratios would weigh a small route like a large one. `carriers`, `routes` and `distance_km` do not add up either.

## Coverage

- **Period:** 2000-01 to 2025-12, by reference month.
- **Absent months:** 2015-08, 2016-02, 2018-07 and 2020-08. They have no rows, and `dim_month.has_data` is false. A year containing one looks lower than it was, so do not read it as a fall in demand.
- **Known zero and unknown differ:** in a known month, a route without flights flew zero. In an absent month, nothing is known.
- **Recovering them:** see [supplements.md](supplements.md). The build picks up `flights_v2_1` once it is published.

## Limitations

- **Passengers per leg:** a passenger staying aboard a multi-leg flight counts once per leg, so totals run about 1-2% above ANAC's published figures.
- **Snapshot:** the source CSV predates later revisions. In 2025-12, Azul's takeoffs are 2.4% below ANAC's current aggregate.
- **Reference month:** flights are placed by reference date. Module A's daily panel uses the actual date, so the two can differ slightly around month ends.
- **Coordinates:** only 320 of 1,180 airports have them, because ANAC's list covers Brazilian public aerodromes. There is no invented location for the rest.
- **Names:** `dim_airport` and `dim_carrier` hold the latest known values. 20 carrier codes had more than one name over time, and `TAM` keeps its code under LATAM.
- **Left out on purpose:** excess and free baggage, and fuel, whose zeros often mean "not reported". There are no fares in this data.
- **Self-loops:** a flight with the same origin and destination counts as both a departure and an arrival.

## Power BI

Load each table with **Get Data > Blank Query** and this M, changing the path and name:

```
let
    Source = Parquet.Document(File.Contents("D:\anac-flight-intelligence-api-main\data\analytics\v1\fact_route_month.parquet"))
in
    Source
```

Create these relationships, all many-to-one and single direction. Load `dim_airport` once, and keep the second relationship inactive for use with `USERELATIONSHIP`, or load it twice as origin and destination.

| From | To |
|---|---|
| `fact_*[month]` | `dim_month[month]` |
| `fact_route_month[origin]` | `dim_airport[airport]` |
| `fact_route_month[destination]` | `dim_airport[airport]` (second role) |
| `fact_route_carrier_month[carrier]`, `fact_carrier_month[carrier]` | `dim_carrier[carrier]` |
| `fact_airport_month[airport]` | `dim_airport[airport]` |

```
Load Factor = DIVIDE(SUM(fact_route_month[paid_passengers]), SUM(fact_route_month[seats]))
```

Use one fact per visual, without adding them up: each is the same data at another grain. These steps have not been tested inside Power BI.

## API

GET only. Filters take ICAO or IATA codes and periods as `from` and `to` in `YYYY-MM`. Filters are checked against fixed patterns and applied as values, so they cannot become a query. Every response lists the period and `absent_months`.

| Endpoint | Filters | Returns |
|---|---|---|
| `/v2/analytics/routes` | `origin`, `destination`, `from`, `to`, `limit`, `offset` | Totals per directed route, by paid passengers |
| `/v2/analytics/routes/monthly` | `origin`, `destination`, `from`, `to` | Monthly totals for the selected direction |
| `/v2/analytics/airports` | `airport`, `from`, `to`, `limit`, `offset` | Totals per airport, by movements |
| `/v2/analytics/airports/monthly` | `airport` (required), `from`, `to` | Monthly totals of one airport |
| `/v2/analytics/carriers` | `carrier`, `from`, `to`, `limit`, `offset` | Totals per carrier, by paid passengers, with market share |
| `/v2/analytics/carriers/monthly` | `carrier` (required), `from`, `to` | Monthly totals and market share of one carrier |
| `/v2/analytics/airports/catalog` | | Every airport code with names, busiest first over the last 12 months, for search |
| `/v2/analytics/carriers/catalog` | | Every carrier code with its latest name, largest first over the last 12 months, for search |
| `/v2/analytics/coverage` | | Period, absent months, table sizes and units |

The catalogs are small (1,180 airports, 317 carriers) and are loaded once by the dashboard, which filters them locally. Carrier codes are never merged: "LATAM" finds `LAN` by its recorded name, not `TAM`.

Carrier codes are ICAO (3) or IATA (2). Market share is the carrier's paid passengers over every carrier's paid passengers in the same period, in the passenger scope, domestic and international legs alike. A carrier filter does not change that denominator.

In monthly series, absent months are listed and left out of `points`, while known months without flights appear as zeros.

## Validation

`validate.py` runs before publication, and any failure stops it:

- **Against the source:** monthly totals of 10 measures, computed separately in DuckDB, with the scope written in SQL. All 308 months agree.
- **Between tables:** routes and carriers match the base, and airport departures and arrivals each match all takeoffs.
- **Joins:** keys are unique, every fact key exists in its dimension, and joining keeps the row count.
- **Against the models:** passengers, seats and takeoffs agree with the feature panel.
