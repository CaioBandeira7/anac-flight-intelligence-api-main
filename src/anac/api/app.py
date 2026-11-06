"""FastAPI over the eight exported payloads. GET only: there is nothing here that can write."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from anac.api.schemas import (
    AirportStat,
    AnalystCatalog,
    DatasetInfo,
    Envelope,
    HealthStatus,
    ModelCard,
    ModuleDescription,
    OverviewData,
    RouteStat,
)
from anac.serving.export import PayloadStore

DEFAULT_DIRECTORY = Path("data/serving/v1")
DEFAULT_ORIGINS = "http://localhost:3000"


def create_app(directory: Path | None = None) -> FastAPI:
    store = PayloadStore(directory or Path(os.environ.get("ANAC_SERVING_DIR", DEFAULT_DIRECTORY)))
    app = FastAPI(
        title="ANAC Flight Intelligence API",
        version="2.0.0",
        description=(
            "Read-only access to audited ANAC data and model evaluations. Payloads carry their "
            "provenance and caveats in `meta`. No endpoint serves ticket prices: the data has none."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("ANAC_CORS_ORIGINS", DEFAULT_ORIGINS).split(","),
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    def payload(endpoint: str) -> dict[str, Any]:
        try:
            return store.get(endpoint)
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=503, detail=f"Payload for {endpoint} has not been exported"
            ) from error

    @app.get("/health", tags=["system"])
    def health() -> Envelope[HealthStatus]:
        return Envelope[HealthStatus].model_validate(payload("/health"))

    @app.get("/v2/overview", tags=["data"])
    def overview() -> Envelope[OverviewData]:
        return Envelope[OverviewData].model_validate(payload("/v2/overview"))

    @app.get("/v2/airports", tags=["data"])
    def airports() -> Envelope[list[AirportStat]]:
        return Envelope[list[AirportStat]].model_validate(payload("/v2/airports"))

    @app.get("/v2/routes", tags=["data"])
    def routes() -> Envelope[list[RouteStat]]:
        return Envelope[list[RouteStat]].model_validate(payload("/v2/routes"))

    @app.get("/v2/models", tags=["models"])
    def models() -> Envelope[list[ModelCard]]:
        return Envelope[list[ModelCard]].model_validate(payload("/v2/models"))

    @app.get("/v2/datasets", tags=["data"])
    def datasets() -> Envelope[list[DatasetInfo]]:
        return Envelope[list[DatasetInfo]].model_validate(payload("/v2/datasets"))

    @app.get("/v2/modules", tags=["models"])
    def modules() -> Envelope[list[ModuleDescription]]:
        return Envelope[list[ModuleDescription]].model_validate(payload("/v2/modules"))

    @app.get("/v2/analyst/catalog", tags=["analyst"])
    def analyst_catalog() -> Envelope[AnalystCatalog]:
        return Envelope[AnalystCatalog].model_validate(payload("/v2/analyst/catalog"))

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(
        "anac.api.app:create_app",
        factory=True,
        host=os.environ.get("ANAC_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("ANAC_API_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
