"""Response models mirroring `web/lib/data/contracts.ts`, so payloads are checked on the way out."""

from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseMeta(BaseModel):
    source: Literal["DEMO", "API"]
    isDemo: bool
    generatedAt: str
    note: str | None = None


class Envelope(BaseModel, Generic[T]):
    data: T
    meta: ResponseMeta


class Kpi(BaseModel):
    id: Literal["flights", "passengers", "load_factor", "active_routes"]
    label: str
    value: float
    unit: Literal["count", "ratio"] | None = None
    delta: float | None = None
    trend: list[float]


class MonthlyPoint(BaseModel):
    month: str
    passengers: int
    flights: int


class AirportStat(BaseModel):
    icao: str
    iata: str
    name: str
    city: str
    uf: str
    lat: float
    lon: float
    movements: int


class RouteStat(BaseModel):
    origin: str
    destination: str
    passengers: int
    loadFactor: float


class ModelMetric(BaseModel):
    name: str
    value: float
    evaluatedOn: str


class ModelCard(BaseModel):
    id: str
    name: str
    task: str
    pipeline: str
    status: Literal["not_trained", "training", "available", "deprecated"]
    metrics: list[ModelMetric] | None
    lastTrainedAt: str | None


class DatasetInfo(BaseModel):
    name: str
    description: str
    approxSize: str
    status: Literal["ingesting", "ready", "planned"]


class OverviewData(BaseModel):
    period: dict[Literal["from", "to"], str]
    kpis: list[Kpi]
    monthly: list[MonthlyPoint]
    topRoutes: list[RouteStat]
    topAirports: list[AirportStat]


class HealthStatus(BaseModel):
    ok: bool
    version: str | None = None
    detail: str | None = None


class ModuleFeature(BaseModel):
    name: str
    type: str
    source: str
    description: str


class ModuleDescription(BaseModel):
    module: str
    title: str
    unit: list[str]
    targets: dict[str, str]
    primary_metric: str
    features: list[ModuleFeature]


class AnalystCatalog(BaseModel):
    version: int
    dataset: str
    tools: list[dict[str, Any]]
    facts_that_must_accompany_answers: list[str]
    must_not_claim: list[str]
