"""Public request and result contracts for model routing."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Tier(str, Enum):
    FAST = "fast"
    MEDIUM = "medium"
    HIGH = "high"
    MAX = "max"


TIER_ORDER: tuple[Tier, ...] = (Tier.FAST, Tier.MEDIUM, Tier.HIGH, Tier.MAX)


class TaskType(str, Enum):
    GENERAL = "general"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    WRITING = "writing"
    CODING = "coding"
    ANALYSIS = "analysis"
    MATH = "math"


class RiskLevel(str, Enum):
    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionStatus(str, Enum):
    ROUTED = "routed"
    UNSATISFIED_CONSTRAINTS = "unsatisfied_constraints"


class DecisionSource(str, Enum):
    RULE = "rule"
    CLASSIFIER = "classifier"
    OVERRIDE = "override"
    FALLBACK = "fallback"


class RouteConstraints(BaseModel):
    """Caller-supplied limits and required model capabilities."""

    model_config = ConfigDict(frozen=True)

    allowed_tiers: set[Tier] = Field(default_factory=lambda: set(TIER_ORDER))
    required_capabilities: set[str] = Field(default_factory=set)
    required_context_window: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def require_an_allowed_tier(self) -> RouteConstraints:
        if not self.allowed_tiers:
            raise ValueError("allowed_tiers must contain at least one tier")
        return self


class RouteRequest(BaseModel):
    """A provider-independent routing request."""

    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=1)
    context: tuple[str, ...] = ()
    task_type: TaskType = TaskType.GENERAL
    risk: RiskLevel = RiskLevel.STANDARD
    constraints: RouteConstraints = Field(default_factory=RouteConstraints)
    tier_override: Tier | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_blank_query(self) -> RouteRequest:
        if not self.query.strip():
            raise ValueError("query must contain non-whitespace text")
        return self


class ModelSpec(BaseModel):
    """A concrete model registered for one capability tier."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(min_length=1)
    tier: Tier
    context_window: int = Field(default=0, ge=0)
    capabilities: set[str] = Field(default_factory=lambda: {"text"})


class ClassifierResult(BaseModel):
    """Validated output returned by an optional routing classifier."""

    model_config = ConfigDict(frozen=True)

    tier: Tier
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason_codes: tuple[str, ...] = ()


class RouteDecision(BaseModel):
    """The stable result returned by :class:`Router`."""

    model_config = ConfigDict(frozen=True)

    status: DecisionStatus
    tier: Tier | None = None
    model_id: str | None = None
    decision_source: DecisionSource
    reason_codes: tuple[str, ...]
    confidence: float | None = Field(default=None, ge=0, le=1)
    rule_score: int | None = Field(default=None, ge=0)
    policy_version: str
    classifier_error: str | None = None
