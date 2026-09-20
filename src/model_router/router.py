"""Routing service implementation."""

from __future__ import annotations

from typing import Protocol

from .config import ModelRegistry, RoutingPolicy
from .features import RuleAssessment, assess
from .models import (
    TIER_ORDER,
    ClassifierResult,
    DecisionSource,
    DecisionStatus,
    RouteDecision,
    RouteRequest,
    Tier,
)


class Classifier(Protocol):
    """Optional adapter for a local or remote query classifier."""

    def classify(self, request: RouteRequest) -> ClassifierResult:
        """Return a schema-validated tier recommendation."""
        ...


def _higher_tier(left: Tier, right: Tier) -> Tier:
    return left if TIER_ORDER.index(left) >= TIER_ORDER.index(right) else right


class Router:
    """Select the least capable configured tier expected to satisfy a request."""

    def __init__(
        self,
        *,
        policy: RoutingPolicy | None = None,
        model_registry: ModelRegistry | None = None,
        classifier: Classifier | None = None,
    ) -> None:
        self.policy = policy or RoutingPolicy()
        self.model_registry = model_registry or ModelRegistry.default()
        self.classifier = classifier

    def route(self, request: RouteRequest) -> RouteDecision:
        assessment = assess(request)
        if request.tier_override is not None:
            return self._finalize(
                request=request,
                minimum_tier=request.tier_override,
                source=DecisionSource.OVERRIDE,
                reasons=("CALLER_OVERRIDE",),
                inferred_capabilities=assessment.inferred_capabilities,
                exact_tier=True,
            )

        rule_tier = self._tier_for_score(assessment)
        selected_tier = rule_tier
        source = DecisionSource.RULE
        reasons = assessment.reason_codes
        confidence: float | None = None
        classifier_error: str | None = None

        classifier = self.classifier
        should_classify = (
            classifier is not None
            and self.policy.classifier_enabled
            and self.policy.classifier_min_score
            <= assessment.score
            <= self.policy.classifier_max_score
        )
        if should_classify:
            assert classifier is not None
            try:
                classified = classifier.classify(request)
                selected_tier = (
                    classified.tier
                    if self.policy.classifier_can_downgrade
                    else _higher_tier(rule_tier, classified.tier)
                )
                source = DecisionSource.CLASSIFIER
                reasons = tuple(dict.fromkeys((*reasons, *classified.reason_codes)))
                confidence = classified.confidence
            except Exception as exc:  # adapters may fail in provider-specific ways
                selected_tier = _higher_tier(rule_tier, self.policy.fallback_tier)
                source = DecisionSource.FALLBACK
                reasons = tuple(dict.fromkeys((*reasons, "CLASSIFIER_FAILURE")))
                classifier_error = type(exc).__name__

        return self._finalize(
            request=request,
            minimum_tier=selected_tier,
            source=source,
            reasons=reasons,
            confidence=confidence,
            classifier_error=classifier_error,
            rule_score=assessment.score,
            inferred_capabilities=assessment.inferred_capabilities,
        )

    def route_batch(
        self, requests: list[RouteRequest] | tuple[RouteRequest, ...]
    ) -> list[RouteDecision]:
        return [self.route(request) for request in requests]

    def _tier_for_score(self, assessment: RuleAssessment) -> Tier:
        if assessment.score >= self.policy.max_threshold:
            return Tier.MAX
        if assessment.score >= self.policy.high_threshold:
            return Tier.HIGH
        if assessment.score >= self.policy.medium_threshold:
            return Tier.MEDIUM
        return Tier.FAST

    def _finalize(
        self,
        *,
        request: RouteRequest,
        minimum_tier: Tier,
        source: DecisionSource,
        reasons: tuple[str, ...],
        confidence: float | None = None,
        classifier_error: str | None = None,
        rule_score: int | None = None,
        inferred_capabilities: frozenset[str] = frozenset(),
        exact_tier: bool = False,
    ) -> RouteDecision:
        constraints = request.constraints
        selected_model = self.model_registry.select(
            minimum_tier=minimum_tier,
            allowed_tiers=constraints.allowed_tiers,
            required_capabilities=set(constraints.required_capabilities) | inferred_capabilities,
            required_context_window=constraints.required_context_window,
            exact_tier=exact_tier,
        )
        if selected_model is None:
            return RouteDecision(
                status=DecisionStatus.UNSATISFIED_CONSTRAINTS,
                decision_source=source,
                reason_codes=tuple(dict.fromkeys((*reasons, "NO_ELIGIBLE_MODEL"))),
                confidence=confidence,
                rule_score=rule_score,
                policy_version=self.policy.version,
                classifier_error=classifier_error,
            )
        return RouteDecision(
            status=DecisionStatus.ROUTED,
            tier=selected_model.tier,
            model_id=selected_model.model_id,
            decision_source=source,
            reason_codes=reasons,
            confidence=confidence,
            rule_score=rule_score,
            policy_version=self.policy.version,
            classifier_error=classifier_error,
        )
