"""FastAPI over the exported payloads, plus the analyst. Nothing here can write data."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from anac.agent.analyst import Analyst, AnalystAnswer
from anac.agent.llm import LlmClient, LlmConfig, LlmError, LlmErrorCode, load_env_file
from anac.agent.tools import AnalystTools
from anac.api.analytics import build_router
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
DEFAULT_ANALYTICS = Path("data/analytics/v1")
MAX_QUESTION_CHARS = 500
ERROR_RESPONSES = {
    LlmErrorCode.NOT_CONFIGURED: (503, "The analyst is not configured on the server."),
    LlmErrorCode.AUTH: (503, "The analyst could not authenticate with its model provider."),
    LlmErrorCode.RATE_LIMITED: (429, "The free usage limit was reached. Please try again shortly."),
    LlmErrorCode.UNAVAILABLE: (503, "The model provider is unavailable right now."),
    LlmErrorCode.TIMEOUT: (504, "The model took too long to answer."),
    LlmErrorCode.BAD_OUTPUT: (502, "The model returned an unusable answer. Please try again."),
}


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Only these roles: a client cannot add system or tool messages.
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    history: list[ChatTurn] = Field(default_factory=list, max_length=6)


class ChatSource(BaseModel):
    endpoint: str
    dataset: str
    period: str
    unit: str
    generated_at: str


class ChatResponse(BaseModel):
    status: Literal["answered", "no_data", "unverified"]
    answer: str
    sources: list[ChatSource]
    caveats: list[str]


class AnalystStatus(BaseModel):
    available: bool
    provider: str
    model: str
    reason: str | None


def create_app(
    directory: Path | None = None,
    llm: LlmClient | None = None,
    analytics_dir: Path | None = None,
) -> FastAPI:
    load_env_file(Path(".env"))
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
        allow_methods=["GET", "POST"],
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

    app.include_router(
        build_router(analytics_dir or Path(os.environ.get("ANAC_ANALYTICS_DIR", DEFAULT_ANALYTICS)))
    )

    analyst = Analyst(llm or LlmClient(LlmConfig.from_env()), AnalystTools(store))

    @app.get("/v2/analyst/status", tags=["analyst"])
    def analyst_status() -> AnalystStatus:
        return AnalystStatus.model_validate(analyst.status())

    @app.post("/v2/analyst/chat", tags=["analyst"])
    def analyst_chat(request: ChatRequest) -> ChatResponse:
        """Ask a question. Answers come only from fixed read-only tools over the exported data."""
        try:
            result: AnalystAnswer = analyst.ask(
                request.question.strip(), [turn.model_dump() for turn in request.history]
            )
        except LlmError as error:
            status, message = ERROR_RESPONSES[error.code]
            headers = {"Retry-After": str(error.retry_after)} if error.retry_after else None
            raise HTTPException(
                status_code=status,
                detail={"code": error.code.value, "message": message},
                headers=headers,
            ) from None
        except FileNotFoundError:
            raise HTTPException(
                status_code=503,
                detail={"code": "data_unavailable", "message": "The data has not been exported."},
            ) from None
        return ChatResponse(
            status=result.status,  # type: ignore[arg-type]
            answer=result.answer,
            sources=[ChatSource.model_validate(source) for source in result.sources],
            caveats=result.caveats,
        )

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
