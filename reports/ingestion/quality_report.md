# Ingestion quality report (full run)

Source: `D:\anac-flight-intelligence-api-main\data\raw\anac_brazil.csv`, 20,147,615,274 bytes. Read 20,147,613,388 bytes in 151 chunks (100.00% of the file).

## Reconciliation

| Stage | Rows |
|---|---|
| Lines read | 22,120,241 |
| Rejected in chunks | 0 |
| Valid after chunks | 22,120,241 |
| Removed as repeated id_basica | 0 |
| **Published** | **22,120,241** |

## Independent read-back

duckdb 2.0.0: 22,120,241 rows, 308 months, reference dates from 2000-01-01 to 2025-12-31, 0 ids repeated across months.

## Rejected rows

None.

## Unparseable values (set to null, row kept)

| Column | Values |
|---|---|
| hr_chegada_real | 18 |

## Flags on published rows

| Flag | Rows | Share |
|---|---|---|
| dq_pax_exceed_seats | 117,627 | 0.532% |
| dq_nature_geography_mismatch | 74,637 | 0.337% |
| dq_zero_distance | 66,119 | 0.299% |
| dq_same_origin_destination | 47,675 | 0.216% |
| dq_duplicate_record | 26,040 | 0.118% |
| dq_missing_departure | 21,473 | 0.097% |
| dq_no_takeoff | 19,293 | 0.087% |
| dq_hours_clock_mismatch | 19,258 | 0.087% |
| dq_rpk_mismatch | 16,240 | 0.073% |
| dq_pax_without_seats | 11,673 | 0.053% |
| dq_ask_mismatch | 10,241 | 0.046% |
| dq_departure_reference_gap | 4,152 | 0.019% |
| dq_icao_nonstandard | 942 | 0.004% |
| dq_negative_metric | 121 | 0.001% |
| dq_parse_error | 18 | 0.000% |
| dq_implausible_flight_hours | 14 | 0.000% |
| dq_reference_period_mismatch | 0 | 0.000% |
| dq_arrival_before_departure | 0 | 0.000% |

## By year

| Year | Months | Rows | Takeoffs | Paid pax | Excess baggage null | Duplicates |
|---|---|---|---|---|---|---|
| 2000 | 12 | 785,716 | 785,514 | 44,642,524 | 5.9% | 9,431 |
| 2001 | 12 | 820,949 | 820,474 | 46,651,917 | 5.1% | 14,347 |
| 2002 | 12 | 760,395 | 759,548 | 45,969,308 | 5.4% | 1,469 |
| 2003 | 12 | 620,556 | 620,236 | 42,965,162 | 7.2% | 26 |
| 2004 | 12 | 612,839 | 612,460 | 46,677,979 | 8.1% | 235 |
| 2005 | 12 | 652,744 | 651,675 | 55,570,574 | 8.2% | 8 |
| 2006 | 12 | 681,383 | 680,457 | 60,601,260 | 8.5% | 19 |
| 2007 | 12 | 745,311 | 744,758 | 66,085,141 | 8.6% | 67 |
| 2008 | 12 | 766,478 | 766,171 | 69,552,928 | 8.1% | 356 |
| 2009 | 12 | 838,704 | 838,702 | 76,493,841 | 7.4% | 35 |
| 2010 | 12 | 969,306 | 968,738 | 91,882,620 | 8.0% | 1 |
| 2011 | 12 | 1,100,433 | 1,099,644 | 107,236,296 | 8.5% | 1 |
| 2012 | 12 | 1,141,313 | 1,140,133 | 114,155,273 | 8.9% | 0 |
| 2013 | 12 | 1,099,606 | 1,097,143 | 115,150,742 | 9.4% | 0 |
| 2014 | 12 | 1,098,931 | 1,097,694 | 122,496,853 | 9.7% | 1 |
| 2015 | 11 | 999,184 | 999,082 | 112,116,777 | 9.0% | 9 |
| 2016 | 11 | 889,258 | 889,153 | 102,721,522 | 8.9% | 12 |
| 2017 | 12 | 947,583 | 946,925 | 114,336,493 | 8.8% | 14 |
| 2018 | 11 | 887,172 | 886,254 | 108,214,605 | 9.5% | 6 |
| 2019 | 12 | 956,592 | 955,383 | 120,717,644 | 9.3% | 3 |
| 2020 | 11 | 447,151 | 446,514 | 49,462,883 | 0.0% | 0 |
| 2021 | 12 | 605,877 | 605,034 | 67,791,916 | 0.0% | 0 |
| 2022 | 12 | 841,389 | 840,533 | 98,643,810 | 0.0% | 0 |
| 2023 | 12 | 929,081 | 928,152 | 113,771,136 | 0.0% | 0 |
| 2024 | 12 | 945,070 | 944,156 | 120,094,316 | 0.0% | 0 |
| 2025 | 12 | 977,220 | 976,415 | 131,782,267 | 0.0% | 0 |

## Performance

This invocation: 477.48 s, peak RSS 2.368 GB, 42.2 MB/s on 20,147,613,388 newly processed bytes. All invocations: 359.92 s in chunks, compression ratio 17.11x.
