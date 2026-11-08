from dataclasses import dataclass
from typing import Literal

from fastapi import FastAPI


@dataclass(frozen=True, slots=True)
class HealthResponse:
    status: Literal["ok"] = "ok"


def create_app() -> FastAPI:
    app = FastAPI(title="NEXUS AI API")

    @app.get("/health", response_model=HealthResponse, status_code=200)
    async def health() -> HealthResponse:
        """Report process liveness without probing future runtime dependencies."""
        return HealthResponse()

    return app
