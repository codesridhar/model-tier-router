"""Local web application for exercising the model router."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from .config import ModelRegistry
from .models import (
    ModelSpec,
    RiskLevel,
    RouteConstraints,
    RouteDecision,
    RouteRequest,
    TaskType,
    Tier,
)
from .router import Router


class DemoRouteRequest(BaseModel):
    """Browser-facing request contract for the routing workbench."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=100_000)
    context: str = Field(default="", max_length=250_000)
    task_type: TaskType = TaskType.GENERAL
    risk: RiskLevel = RiskLevel.STANDARD
    allowed_tiers: list[Tier] = Field(default_factory=lambda: list(Tier), min_length=1)
    required_capabilities: set[str] = Field(default_factory=set)
    required_context_window: int = Field(default=0, ge=0, le=1_000_000)
    tier_override: Tier | None = None


class Thresholds(BaseModel):
    medium: int
    high: int
    max: int


class RouteInspection(BaseModel):
    """Decision plus the policy values needed to explain it visually."""

    decision: RouteDecision
    thresholds: Thresholds


def demo_registry() -> ModelRegistry:
    """Return representative model metadata for local experimentation."""

    return ModelRegistry(
        [
            ModelSpec(model_id="demo-fast", tier=Tier.FAST, context_window=16_000),
            ModelSpec(model_id="demo-medium", tier=Tier.MEDIUM, context_window=64_000),
            ModelSpec(
                model_id="demo-high",
                tier=Tier.HIGH,
                context_window=128_000,
                capabilities={"text", "vision"},
            ),
            ModelSpec(
                model_id="demo-max",
                tier=Tier.MAX,
                context_window=256_000,
                capabilities={"text", "vision", "audio"},
            ),
        ]
    )


def create_app(router: Router | None = None) -> FastAPI:
    """Create the test app with an injectable router for tests and embedding."""

    active_router = router or Router(model_registry=demo_registry())
    html_path = Path(__file__).parent / "static" / "index.html"

    app = FastAPI(
        title="Model Routing Workbench",
        version="0.1.0",
        description="Interactive test surface for model-tier-router.",
    )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> HTMLResponse:
        """Render the local routing workbench."""

        return HTMLResponse(html_path.read_text(encoding="utf-8"))

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Report whether the demo application is ready."""

        return {"status": "ok"}

    @app.post("/api/route", response_model=RouteInspection, tags=["routing"])
    def route_query(payload: DemoRouteRequest) -> RouteInspection:
        """Evaluate one user query and return its routing decision and thresholds."""

        request = RouteRequest(
            query=payload.query,
            context=(payload.context,) if payload.context.strip() else (),
            task_type=payload.task_type,
            risk=payload.risk,
            constraints=RouteConstraints(
                allowed_tiers=set(payload.allowed_tiers),
                required_capabilities=payload.required_capabilities,
                required_context_window=payload.required_context_window,
            ),
            tier_override=payload.tier_override,
        )
        decision = active_router.route(request)
        policy = active_router.policy
        return RouteInspection(
            decision=decision,
            thresholds=Thresholds(
                medium=policy.medium_threshold,
                high=policy.high_threshold,
                max=policy.max_threshold,
            ),
        )

    return app


app = create_app()


def main() -> None:
    """Start the local development server."""

    import uvicorn

    uvicorn.run("model_router.demo_app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
