"""The only data the agent can reach: fixed functions over exported payloads.

There is no query language here. Arguments are validated, used only for plain text matching over
in-memory lists, and capped, so nothing a model or a user writes can become a query.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from anac.serving.export import PayloadStore

MAX_ROWS = 10


class ToolError(Exception):
    """A tool call was rejected. The message is safe to show to the model."""


class _Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OverviewArguments(_Arguments):
    include_monthly: bool = False


class AirportArguments(_Arguments):
    query: str | None = Field(default=None, max_length=60, pattern=r"^[\w\s.'-]*$")
    limit: int = Field(default=5, ge=1, le=MAX_ROWS)


class RouteArguments(_Arguments):
    origin: str | None = Field(default=None, pattern=r"^[A-Za-z0-9]{3,4}$")
    destination: str | None = Field(default=None, pattern=r"^[A-Za-z0-9]{3,4}$")
    limit: int = Field(default=5, ge=1, le=MAX_ROWS)


class ModelArguments(_Arguments):
    module: Literal["a", "b", "c", "d"] | None = None


class CoverageArguments(_Arguments):
    pass


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


class AnalystTools:
    def __init__(self, store: PayloadStore) -> None:
        self._store = store
        self._registry: dict[str, tuple[type[_Arguments], Callable[[Any], dict[str, Any]]]] = {
            "get_market_overview": (OverviewArguments, self._overview),
            "search_airports": (AirportArguments, self._airports),
            "search_routes": (RouteArguments, self._routes),
            "get_model_results": (ModelArguments, self._models),
            "get_data_coverage": (CoverageArguments, self._coverage),
        }

    @property
    def names(self) -> list[str]:
        return list(self._registry)

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Run one allowed tool. Anything outside the registry or the schema is refused."""
        entry = self._registry.get(name)
        if entry is None:
            raise ToolError(f"Unknown tool: {name[:40]}")
        schema, function = entry
        try:
            parsed = schema.model_validate(arguments)
        except ValidationError as error:
            fields = sorted({".".join(map(str, item["loc"])) for item in error.errors()})
            raise ToolError(f"Invalid arguments for {name}: {fields}") from error
        return function(parsed)

    def period(self) -> dict[str, str]:
        """The latest 12 months covered, as {"from": "YYYY-MM", "to": "YYYY-MM"}."""
        return self._period()

    def _period(self) -> dict[str, str]:
        period: dict[str, str] = self._store.get("/v2/overview")["data"]["period"]
        return period

    def _dataset(self) -> str:
        return str(self._store.get("/health")["data"].get("version", "unknown"))

    def _provenance(
        self, endpoint: str, period: str, unit: str, note: str | None
    ) -> dict[str, Any]:
        return {
            "endpoint": endpoint,
            "dataset": self._dataset(),
            "period": period,
            "unit": unit,
            "generated_at": self._store.get(endpoint)["meta"]["generatedAt"],
            "note": note,
        }

    def _window(self) -> str:
        period = self._period()
        return f"{period['from']} to {period['to']}"

    def _overview(self, arguments: OverviewArguments) -> dict[str, Any]:
        payload = self._store.get("/v2/overview")
        data = payload["data"]
        result: dict[str, Any] = {
            "found": True,
            "kpis": [
                {
                    "id": kpi["id"],
                    "label": kpi["label"],
                    "value": kpi["value"],
                    "unit": kpi.get("unit"),
                    "change_vs_previous_12_months": kpi.get("delta"),
                }
                for kpi in data["kpis"]
            ],
        }
        if arguments.include_monthly:
            result["monthly"] = data["monthly"]
        result["provenance"] = self._provenance(
            "/v2/overview",
            self._window(),
            "flights and paid passengers as counts; load factor as a ratio from 0 to 1",
            payload["meta"].get("note"),
        )
        return result

    def _airports(self, arguments: AirportArguments) -> dict[str, Any]:
        payload = self._store.get("/v2/airports")
        rows = payload["data"]
        if arguments.query:
            needle = _fold(arguments.query)
            rows = [
                row
                for row in rows
                if any(
                    needle in _fold(str(row[key])) for key in ("icao", "iata", "name", "city", "uf")
                )
            ]
        provenance = self._provenance(
            "/v2/airports",
            self._window(),
            "movements: takeoffs plus landings, as a count",
            "Covers Brazilian public aerodromes with published coordinates, ranked by movements. "
            "Movements do not measure congestion or delays.",
        )
        if not rows:
            return {
                "found": False,
                "message": "No airport matches this search in the available data.",
                "provenance": provenance,
            }
        return {
            "found": True,
            "matches": len(rows),
            "airports": [
                {key: row[key] for key in ("icao", "iata", "name", "city", "uf", "movements")}
                for row in rows[: arguments.limit]
            ],
            "provenance": provenance,
        }

    def _routes(self, arguments: RouteArguments) -> dict[str, Any]:
        payload = self._store.get("/v2/routes")
        rows = payload["data"]
        if arguments.origin:
            rows = [row for row in rows if row["origin"].casefold() == arguments.origin.casefold()]
        if arguments.destination:
            rows = [
                row
                for row in rows
                if row["destination"].casefold() == arguments.destination.casefold()
            ]
        provenance = self._provenance(
            "/v2/routes",
            self._window(),
            "passengers: paid passengers per leg, as a count; loadFactor: ratio from 0 to 1",
            "Only the 200 busiest routes by paid passengers are available, in IATA codes. "
            "A route missing here may still exist.",
        )
        if not rows:
            return {
                "found": False,
                "message": "This route is not among the 200 busiest routes served here. That does not mean it does not exist: its figures are simply not available in this API.",
                "route_may_exist": True,
                "provenance": provenance,
            }
        return {
            "found": True,
            "matches": len(rows),
            "routes": rows[: arguments.limit],
            "provenance": provenance,
        }

    def _models(self, arguments: ModelArguments) -> dict[str, Any]:
        payload = self._store.get("/v2/models")
        cards = payload["data"]
        if arguments.module:
            cards = [card for card in cards if card.get("module") == arguments.module]
        provenance = self._provenance(
            "/v2/models",
            "validation on 2023-01 to 2023-12",
            "WAPE as a ratio (0.10 is 10%); seat-weighted MAE as a ratio (0.06 is 6 points)",
            "Validation results for 2023, not current forecasts. The final test on 2024-2025 has "
            "not been run. No live predictions are available.",
        )
        if not cards:
            return {"found": False, "message": "No such module.", "provenance": provenance}
        return {
            "found": True,
            "is_current_forecast": False,
            "models": [
                {
                    "module": card.get("module"),
                    "name": card["name"],
                    "method": card.get("method"),
                    "in_use": card.get("selected"),
                    "status": card["status"],
                    "metrics": [
                        {"name": metric["name"], "value": metric["value"]}
                        for metric in (card.get("metrics") or [])
                    ],
                    "comparison": card.get("note"),
                }
                for card in cards
            ],
            "provenance": provenance,
        }

    def _coverage(self, _: CoverageArguments) -> dict[str, Any]:
        catalog = self._store.get("/v2/analyst/catalog")["data"]
        datasets = self._store.get("/v2/datasets")["data"]
        return {
            "found": True,
            "datasets": datasets,
            "must_state": catalog["facts_that_must_accompany_answers"],
            "must_not_claim": catalog["must_not_claim"],
            "provenance": self._provenance("/v2/datasets", self._window(), "not applicable", None),
        }


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_market_overview",
            "description": "Market totals for the latest 12 months: flights, paid passengers, load factor, active routes and change against the previous 12 months. Optionally 24 monthly points.",
            "parameters": {
                "type": "object",
                "properties": {"include_monthly": {"type": "boolean"}},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_airports",
            "description": "Brazilian public airports ranked by movements (takeoffs plus landings) in the latest 12 months, largest first. Call without query for the busiest airports. Filter by code, name, city or state, also to find an airport's IATA code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Code, name, city or state. Omit for the ranking.",
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": MAX_ROWS},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_routes",
            "description": "The 200 busiest directed routes in the latest 12 months, ranked by paid passengers, largest first, with load factor. Call without filters for the busiest routes (a ranking). Filter by origin and/or destination IATA codes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "IATA code, such as GRU"},
                    "destination": {"type": "string", "description": "IATA code, such as GIG"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": MAX_ROWS},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_model_results",
            "description": "Validation results for 2023 of the methods per module: a airport movements, b seat occupancy, c baggage (not trained), d route demand and capacity. These are not forecasts.",
            "parameters": {
                "type": "object",
                "properties": {"module": {"type": "string", "enum": ["a", "b", "c", "d"]}},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_coverage",
            "description": "Available datasets, absent months, and what the data can and cannot support.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]
