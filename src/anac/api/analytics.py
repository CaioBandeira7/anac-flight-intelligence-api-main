"""GET endpoints over the analytical tables. Filters are validated before reaching any table."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from anac.analytics.store import AnalyticsNotBuilt, AnalyticsStore

_MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"
_CODE = r"^[A-Za-z0-9]{3,4}$"
NOTE = (
    "Passenger measures use the passenger scope, per flight leg. Routes are directed. Absent months "
    "have no data at all and are not zeros."
)

Airport = Annotated[str | None, Query(pattern=_CODE, description="ICAO or IATA code")]
FromMonth = Annotated[
    str | None, Query(alias="from", pattern=_MONTH, description="First month, YYYY-MM")
]
ToMonth = Annotated[
    str | None, Query(alias="to", pattern=_MONTH, description="Last month, YYYY-MM")
]
Limit = Annotated[int, Query(ge=1, le=500)]
Offset = Annotated[int, Query(ge=0)]


class Meta(BaseModel):
    source: str = "API"
    isDemo: bool = False
    generatedAt: str
    note: str | None = None


class Context(BaseModel):
    period: dict[str, str]
    months_with_data: int
    absent_months: list[str]


class RoutePoint(BaseModel):
    month: str
    all_takeoffs: int
    passenger_takeoffs: int
    paid_passengers: int
    seats: int
    rpk: float
    ask: float
    load_factor_paid: float | None


class AirportPoint(BaseModel):
    month: str
    departures: int
    arrivals: int
    movements: int
    departing_paid_passengers: int
    arriving_paid_passengers: int


class RouteRow(BaseModel):
    origin: str
    destination: str
    origin_iata: str | None
    destination_iata: str | None
    is_international: bool
    distance_km: float | None
    months_operated: int
    all_takeoffs: int
    passenger_takeoffs: int
    paid_passengers: int
    seats: int
    rpk: float
    ask: float
    load_factor_paid: float | None


class AirportRow(BaseModel):
    airport: str
    iata: str | None
    name: str | None
    city: str | None
    uf: str | None
    country: str | None
    months_operated: int
    departures: int
    arrivals: int
    movements: int
    departing_paid_passengers: int
    arriving_paid_passengers: int


class RoutesData(Context):
    total: int
    limit: int
    offset: int
    routes: list[RouteRow]


class RouteSeries(Context):
    points: list[RoutePoint]


class AirportsData(Context):
    total: int
    limit: int
    offset: int
    airports: list[AirportRow]


class AirportSeries(Context):
    airport_found: bool
    points: list[AirportPoint]


class Coverage(BaseModel):
    dataset: str
    first_month: str
    last_month: str
    absent_months: list[str]
    tables: dict[str, dict[str, int]]
    units: dict[str, str]


class RoutesResponse(BaseModel):
    data: RoutesData
    meta: Meta


class RouteSeriesResponse(BaseModel):
    data: RouteSeries
    meta: Meta


class AirportsResponse(BaseModel):
    data: AirportsData
    meta: Meta


class AirportSeriesResponse(BaseModel):
    data: AirportSeries
    meta: Meta


class CoverageResponse(BaseModel):
    data: Coverage
    meta: Meta


def _check_period(first: str | None, last: str | None) -> None:
    if first and last and first > last:
        raise HTTPException(status_code=422, detail="'from' must not be after 'to'")


def build_router(directory: Path) -> APIRouter:
    store = AnalyticsStore(directory)
    router = APIRouter(prefix="/v2/analytics", tags=["analytics"])

    def respond(producer: Any) -> dict[str, Any]:
        try:
            data = producer()
            generated = store.manifest()["built_at"]
        except AnalyticsNotBuilt as error:
            raise HTTPException(
                status_code=503, detail="The analytical tables have not been built"
            ) from error
        return {
            "data": data,
            "meta": {"generatedAt": generated or datetime.now(UTC).isoformat(), "note": NOTE},
        }

    @router.get("/routes")
    def routes(
        origin: Airport = None,
        destination: Airport = None,
        first: FromMonth = None,
        last: ToMonth = None,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> RoutesResponse:
        """Totals per directed route in the period, ordered by paid passengers."""
        _check_period(first, last)
        return RoutesResponse.model_validate(
            respond(lambda: store.routes(origin, destination, first, last, limit, offset))
        )

    @router.get("/routes/monthly")
    def route_series(
        origin: Airport = None,
        destination: Airport = None,
        first: FromMonth = None,
        last: ToMonth = None,
    ) -> RouteSeriesResponse:
        """Monthly totals for the selected direction. Absent months are listed, not filled."""
        _check_period(first, last)
        return RouteSeriesResponse.model_validate(
            respond(lambda: store.route_series(origin, destination, first, last))
        )

    @router.get("/airports")
    def airports(
        airport: Airport = None,
        first: FromMonth = None,
        last: ToMonth = None,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> AirportsResponse:
        """Totals per airport in the period, ordered by movements."""
        _check_period(first, last)
        return AirportsResponse.model_validate(
            respond(lambda: store.airports(airport, first, last, limit, offset))
        )

    @router.get("/airports/monthly")
    def airport_series(
        airport: Annotated[str, Query(pattern=_CODE, description="ICAO or IATA code")],
        first: FromMonth = None,
        last: ToMonth = None,
    ) -> AirportSeriesResponse:
        """Monthly totals of one airport. Absent months are listed, not filled."""
        _check_period(first, last)
        return AirportSeriesResponse.model_validate(
            respond(lambda: store.airport_series(airport, first, last))
        )

    @router.get("/coverage")
    def coverage() -> CoverageResponse:
        """Months covered, absent months, table sizes and the unit of every measure."""
        return CoverageResponse.model_validate(respond(store.coverage))

    return router
