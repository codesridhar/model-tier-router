"""Dependency-free evaluation utilities for routing policies."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .models import TIER_ORDER, DecisionStatus, RouteRequest, Tier
from .router import Router


class EvaluationCase(BaseModel):
    """A reviewed request and the lowest tier that completes it successfully."""

    model_config = ConfigDict(frozen=True)

    request: RouteRequest
    expected_tier: Tier
    case_id: str | None = None


class CaseResult(BaseModel):
    """Evaluation result for one case."""

    model_config = ConfigDict(frozen=True)

    case_id: str | None
    expected_tier: Tier
    actual_tier: Tier | None
    status: DecisionStatus


class EvaluationReport(BaseModel):
    """Aggregate quality and cost-direction metrics for a router."""

    model_config = ConfigDict(frozen=True)

    total: int = Field(gt=0)
    exact: int
    under_routed: int
    over_routed: int
    unsatisfied: int
    accuracy: float = Field(ge=0, le=1)
    under_routing_rate: float = Field(ge=0, le=1)
    over_routing_rate: float = Field(ge=0, le=1)
    results: tuple[CaseResult, ...]


def evaluate(router: Router, cases: Iterable[EvaluationCase]) -> EvaluationReport:
    """Evaluate a router against human-reviewed minimum successful tiers."""

    evaluation_cases = tuple(cases)
    if not evaluation_cases:
        raise ValueError("at least one evaluation case is required")

    exact = 0
    under_routed = 0
    over_routed = 0
    unsatisfied = 0
    results: list[CaseResult] = []

    for case in evaluation_cases:
        decision = router.route(case.request)
        actual_tier = decision.tier
        if actual_tier is None:
            unsatisfied += 1
        else:
            actual_index = TIER_ORDER.index(actual_tier)
            expected_index = TIER_ORDER.index(case.expected_tier)
            if actual_index == expected_index:
                exact += 1
            elif actual_index < expected_index:
                under_routed += 1
            else:
                over_routed += 1
        results.append(
            CaseResult(
                case_id=case.case_id,
                expected_tier=case.expected_tier,
                actual_tier=actual_tier,
                status=decision.status,
            )
        )

    total = len(evaluation_cases)
    return EvaluationReport(
        total=total,
        exact=exact,
        under_routed=under_routed,
        over_routed=over_routed,
        unsatisfied=unsatisfied,
        accuracy=exact / total,
        under_routing_rate=under_routed / total,
        over_routing_rate=over_routed / total,
        results=tuple(results),
    )
