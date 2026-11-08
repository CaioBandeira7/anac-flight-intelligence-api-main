"""Read-only queries over the analytical tables. Filters are values, never query text."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl


class AnalyticsNotBuilt(RuntimeError):
    """The tables have not been built."""


def parse_period_month(text: str) -> date:
    year, month = text.split("-")
    return date(int(year), int(month), 1)


def _label(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


class AnalyticsStore:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def _table(self, name: str) -> pl.LazyFrame:
        path = self._directory / f"{name}.parquet"
        if not path.exists():
            raise AnalyticsNotBuilt(name)
        return pl.scan_parquet(path)

    def manifest(self) -> dict[str, Any]:
        path = self._directory / "manifest.json"
        if not path.exists():
            raise AnalyticsNotBuilt("manifest")
        loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return loaded

    def _period(self, first: str | None, last: str | None) -> tuple[date, date]:
        manifest = self.manifest()
        start = parse_period_month(first or manifest["first_month"])
        end = parse_period_month(last or manifest["last_month"])
        return (
            max(start, parse_period_month(manifest["first_month"])),
            min(end, parse_period_month(manifest["last_month"])),
        )

    def _months(self, start: date, end: date) -> pl.DataFrame:
        return (
            self._table("dim_month")
            .filter(pl.col("month").is_between(start, end))
            .select("month", "has_data")
            .sort("month")
            .collect()
        )

    def _context(self, start: date, end: date) -> dict[str, Any]:
        months = self._months(start, end)
        absent = months.filter(~pl.col("has_data")).get_column("month").to_list()
        return {
            "period": {"from": _label(start), "to": _label(end)},
            "months_with_data": months.filter(pl.col("has_data")).height,
            "absent_months": [_label(value) for value in absent],
        }

    def resolve_airport(self, code: str | None) -> list[str] | None:
        """ICAO or IATA to ICAO. None means no filter, and an empty list means an unknown code."""
        if not code:
            return None
        wanted = code.strip().upper()
        found = (
            self._table("dim_airport")
            .filter((pl.col("airport") == wanted) | (pl.col("iata") == wanted))
            .select("airport")
            .collect()
        )
        return found.get_column("airport").to_list()

    def _airport_names(self) -> pl.LazyFrame:
        return self._table("dim_airport").select("airport", "iata", "name", "city", "uf", "country")

    def _route_filter(
        self, origin: str | None, destination: str | None, start: date, end: date
    ) -> pl.LazyFrame:
        routes = self._table("fact_route_month").filter(pl.col("month").is_between(start, end))
        origins, destinations = self.resolve_airport(origin), self.resolve_airport(destination)
        if origins is not None:
            routes = routes.filter(pl.col("origin").is_in(origins))
        if destinations is not None:
            routes = routes.filter(pl.col("destination").is_in(destinations))
        return routes

    def routes(
        self,
        origin: str | None,
        destination: str | None,
        first: str | None,
        last: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        """One row per directed route in the period. A to B and B to A stay apart."""
        start, end = self._period(first, last)
        names = self._airport_names()
        grouped = (
            self._route_filter(origin, destination, start, end)
            .group_by("origin", "destination")
            .agg(
                pl.col(
                    "passenger_takeoffs", "paid_passengers", "seats", "rpk", "ask", "all_takeoffs"
                ).sum(),
                pl.col("month").n_unique().alias("months_operated"),
                pl.col("distance_km").median(),
                pl.col("is_international").any(),
            )
            .with_columns(
                pl.when(pl.col("seats") > 0)
                .then(pl.col("paid_passengers") / pl.col("seats"))
                .alias("load_factor_paid")
            )
            .sort(["paid_passengers", "origin", "destination"], descending=[True, False, False])
            .collect()
        )
        page = (
            grouped.slice(offset, limit)
            .lazy()
            .join(
                names.select(
                    pl.col("airport").alias("origin"), pl.col("iata").alias("origin_iata")
                ),
                on="origin",
                how="left",
                maintain_order="left",
            )
            .join(
                names.select(
                    pl.col("airport").alias("destination"), pl.col("iata").alias("destination_iata")
                ),
                on="destination",
                how="left",
                maintain_order="left",
            )
            .collect()
        )
        return {
            **self._context(start, end),
            "total": grouped.height,
            "limit": limit,
            "offset": offset,
            "routes": page.to_dicts(),
        }

    def route_series(
        self, origin: str | None, destination: str | None, first: str | None, last: str | None
    ) -> dict[str, Any]:
        """Monthly totals of the selected direction. A known month without flights is a zero."""
        start, end = self._period(first, last)
        monthly = (
            self._route_filter(origin, destination, start, end)
            .group_by("month")
            .agg(
                pl.col(
                    "passenger_takeoffs", "paid_passengers", "seats", "rpk", "ask", "all_takeoffs"
                ).sum()
            )
            .collect()
        )
        return {**self._context(start, end), "points": self._series_points(monthly, start, end)}

    def _series_points(self, monthly: pl.DataFrame, start: date, end: date) -> list[dict[str, Any]]:
        measures = [name for name in monthly.columns if name != "month"]
        known = self._months(start, end).filter(pl.col("has_data")).select("month")
        filled = (
            known.join(monthly, on="month", how="left")
            .with_columns(pl.col(measures).fill_null(0))
            .sort("month")
        )
        if "seats" in measures:
            filled = filled.with_columns(
                pl.when(pl.col("seats") > 0)
                .then(pl.col("paid_passengers") / pl.col("seats"))
                .alias("load_factor_paid")
            )
        return [{**row, "month": _label(row["month"])} for row in filled.to_dicts()]

    def airports(
        self, airport: str | None, first: str | None, last: str | None, limit: int, offset: int
    ) -> dict[str, Any]:
        start, end = self._period(first, last)
        facts = self._table("fact_airport_month").filter(pl.col("month").is_between(start, end))
        resolved = self.resolve_airport(airport)
        if resolved is not None:
            facts = facts.filter(pl.col("airport").is_in(resolved))
        grouped = (
            facts.group_by("airport")
            .agg(
                pl.col(
                    "departures",
                    "arrivals",
                    "movements",
                    "departing_paid_passengers",
                    "arriving_paid_passengers",
                ).sum(),
                pl.col("month").n_unique().alias("months_operated"),
            )
            .sort(["movements", "airport"], descending=[True, False])
            .collect()
        )
        page = (
            grouped.slice(offset, limit)
            .lazy()
            .join(self._airport_names(), on="airport", how="left", maintain_order="left")
            .collect()
        )
        return {
            **self._context(start, end),
            "total": grouped.height,
            "limit": limit,
            "offset": offset,
            "airports": page.to_dicts(),
        }

    def airport_series(self, airport: str, first: str | None, last: str | None) -> dict[str, Any]:
        start, end = self._period(first, last)
        resolved = self.resolve_airport(airport) or []
        monthly = (
            self._table("fact_airport_month")
            .filter(pl.col("month").is_between(start, end) & pl.col("airport").is_in(resolved))
            .group_by("month")
            .agg(
                pl.col(
                    "departures",
                    "arrivals",
                    "movements",
                    "departing_paid_passengers",
                    "arriving_paid_passengers",
                ).sum()
            )
            .collect()
        )
        return {
            **self._context(start, end),
            "airport_found": bool(resolved),
            "points": self._series_points(monthly, start, end) if resolved else [],
        }

    def resolve_carrier(self, code: str | None) -> list[str] | None:
        """ICAO or IATA to ICAO. None means no filter, and an empty list means an unknown code."""
        if not code:
            return None
        wanted = code.strip().upper()
        found = (
            self._table("dim_carrier")
            .filter((pl.col("carrier") == wanted) | (pl.col("iata") == wanted))
            .select("carrier")
            .collect()
        )
        return found.get_column("carrier").to_list()

    def carriers(
        self, carrier: str | None, first: str | None, last: str | None, limit: int, offset: int
    ) -> dict[str, Any]:
        """Totals per carrier in the period, ordered by paid passengers, with market share.

        The share is over every carrier's paid passengers in the same period and scope.
        """
        start, end = self._period(first, last)
        facts = self._table("fact_carrier_month").filter(pl.col("month").is_between(start, end))
        market = int(facts.select(pl.col("paid_passengers").sum()).collect().item() or 0)
        resolved = self.resolve_carrier(carrier)
        if resolved is not None:
            facts = facts.filter(pl.col("carrier").is_in(resolved))
        grouped = (
            facts.group_by("carrier")
            .agg(
                pl.col(
                    "all_takeoffs",
                    "passenger_takeoffs",
                    "paid_passengers",
                    "seats",
                    "rpk",
                    "ask",
                    "international_paid_passengers",
                ).sum(),
                pl.col("month").n_unique().alias("months_operated"),
            )
            .with_columns(
                pl.when(pl.col("seats") > 0)
                .then(pl.col("paid_passengers") / pl.col("seats"))
                .alias("load_factor_paid"),
                (pl.col("paid_passengers") / market if market else pl.lit(None, pl.Float64)).alias(
                    "market_share"
                ),
            )
            .sort(["paid_passengers", "carrier"], descending=[True, False])
            .collect()
        )
        names = self._table("dim_carrier").select("carrier", "iata", "name", "country")
        page = (
            grouped.slice(offset, limit)
            .lazy()
            .join(names, on="carrier", how="left", maintain_order="left")
            .collect()
        )
        return {
            **self._context(start, end),
            "market_paid_passengers": market,
            "total": grouped.height,
            "limit": limit,
            "offset": offset,
            "carriers": page.to_dicts(),
        }

    def carrier_series(self, carrier: str, first: str | None, last: str | None) -> dict[str, Any]:
        """Monthly totals of one carrier, with its share of each month's paid passengers."""
        start, end = self._period(first, last)
        resolved = self.resolve_carrier(carrier) or []
        facts = self._table("fact_carrier_month").filter(pl.col("month").is_between(start, end))
        market = facts.group_by("month").agg(
            pl.col("paid_passengers").sum().alias("market_paid_passengers")
        )
        monthly = (
            facts.filter(pl.col("carrier").is_in(resolved))
            .group_by("month")
            .agg(
                pl.col(
                    "all_takeoffs", "passenger_takeoffs", "paid_passengers", "seats", "rpk", "ask"
                ).sum()
            )
            .collect()
        )
        points = self._series_points(monthly, start, end) if resolved else []
        totals = {
            _label(row["month"]): row["market_paid_passengers"]
            for row in market.collect().to_dicts()
        }
        for point in points:
            whole = totals.get(point["month"], 0)
            point["market_paid_passengers"] = whole
            point["market_share"] = point["paid_passengers"] / whole if whole else None
        return {**self._context(start, end), "carrier_found": bool(resolved), "points": points}

    def _recent(self) -> tuple[date, date]:
        """The last 12 months of the dataset, used only to order suggestions by relevance."""
        last = parse_period_month(self.manifest()["last_month"])
        index = last.year * 12 + last.month - 1 - 11
        return date(index // 12, index % 12 + 1, 1), last

    def airport_catalog(self) -> dict[str, Any]:
        """Every airport in the dimension, busiest first over the last 12 months."""
        start, end = self._recent()
        recent = (
            self._table("fact_airport_month")
            .filter(pl.col("month").is_between(start, end))
            .group_by("airport")
            .agg(pl.col("movements").sum().alias("recent_movements"))
        )
        rows = (
            self._table("dim_airport")
            .select("airport", "iata", "name", "city", "uf", "country", "first_month", "last_month")
            .join(recent, on="airport", how="left")
            .with_columns(pl.col("recent_movements").fill_null(0))
            .sort(["recent_movements", "airport"], descending=[True, False])
            .collect()
        )
        return {
            "recent_period": {"from": _label(start), "to": _label(end)},
            "airports": [
                {
                    **row,
                    "first_month": _label(row["first_month"]),
                    "last_month": _label(row["last_month"]),
                }
                for row in rows.to_dicts()
            ],
        }

    def carrier_catalog(self) -> dict[str, Any]:
        """Every carrier code in the dimension, largest first over the last 12 months."""
        start, end = self._recent()
        recent = (
            self._table("fact_carrier_month")
            .filter(pl.col("month").is_between(start, end))
            .group_by("carrier")
            .agg(pl.col("paid_passengers").sum().alias("recent_paid_passengers"))
        )
        rows = (
            self._table("dim_carrier")
            .select(
                "carrier", "iata", "name", "country", "name_variants", "first_month", "last_month"
            )
            .join(recent, on="carrier", how="left")
            .with_columns(pl.col("recent_paid_passengers").fill_null(0))
            .sort(["recent_paid_passengers", "carrier"], descending=[True, False])
            .collect()
        )
        return {
            "recent_period": {"from": _label(start), "to": _label(end)},
            "carriers": [
                {
                    **row,
                    "first_month": _label(row["first_month"]),
                    "last_month": _label(row["last_month"]),
                }
                for row in rows.to_dicts()
            ],
        }

    def coverage(self) -> dict[str, Any]:
        manifest = self.manifest()
        return {
            "dataset": manifest["identity"]["dataset"],
            "first_month": manifest["first_month"],
            "last_month": manifest["last_month"],
            "absent_months": manifest["absent_months"],
            "tables": {
                name: {"rows": item["rows"], "bytes": item["bytes"]}
                for name, item in manifest["tables"].items()
            },
            "units": manifest["column_docs"],
        }
