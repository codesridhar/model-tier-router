from __future__ import annotations

import unittest

from pydantic import ValidationError

from model_router import (
    ClassifierResult,
    DecisionSource,
    DecisionStatus,
    ModelRegistry,
    ModelSpec,
    RiskLevel,
    RouteConstraints,
    Router,
    RouteRequest,
    RoutingPolicy,
    TaskType,
    Tier,
)


class HighClassifier:
    def classify(self, request: RouteRequest) -> ClassifierResult:
        return ClassifierResult(
            tier=Tier.HIGH,
            confidence=0.86,
            reason_codes=("CLASSIFIER_COMPLEXITY",),
        )


class FailingClassifier:
    def classify(self, request: RouteRequest) -> ClassifierResult:
        raise TimeoutError("classifier timed out")


class RouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = Router()

    def test_bounded_extraction_routes_fast(self) -> None:
        decision = self.router.route(
            RouteRequest(query="Extract the invoice date", task_type=TaskType.EXTRACTION)
        )

        self.assertEqual(decision.status, DecisionStatus.ROUTED)
        self.assertEqual(decision.tier, Tier.FAST)
        self.assertIn("BOUNDED_SIMPLE_TASK", decision.reason_codes)

    def test_complex_multi_component_task_routes_high(self) -> None:
        decision = self.router.route(
            RouteRequest(
                query="Investigate this deadlock across three services and identify the root cause",
                task_type=TaskType.CODING,
            )
        )

        self.assertEqual(decision.tier, Tier.HIGH)
        self.assertIn("SPECIALIZED_COMPLEXITY", decision.reason_codes)
        self.assertIn("MULTI_COMPONENT_ANALYSIS", decision.reason_codes)

    def test_critical_complex_task_routes_max(self) -> None:
        decision = self.router.route(
            RouteRequest(
                query="Design an architecture migration across multiple distributed systems",
                task_type=TaskType.ANALYSIS,
                risk=RiskLevel.CRITICAL,
            )
        )

        self.assertEqual(decision.tier, Tier.MAX)

    def test_allowed_tiers_raise_selection_to_next_eligible_tier(self) -> None:
        decision = self.router.route(
            RouteRequest(
                query="Write a greeting",
                constraints=RouteConstraints(allowed_tiers={Tier.MEDIUM, Tier.HIGH}),
            )
        )

        self.assertEqual(decision.tier, Tier.MEDIUM)

    def test_number_without_component_noun_does_not_raise_tier(self) -> None:
        decision = self.router.route(RouteRequest(query="Write three words"))

        self.assertEqual(decision.tier, Tier.FAST)
        self.assertNotIn("MULTI_COMPONENT_ANALYSIS", decision.reason_codes)

    def test_override_is_exact_and_has_precedence(self) -> None:
        decision = self.router.route(
            RouteRequest(query="Investigate a deadlock", tier_override=Tier.FAST)
        )

        self.assertEqual(decision.tier, Tier.FAST)
        self.assertEqual(decision.decision_source, DecisionSource.OVERRIDE)
        self.assertEqual(decision.reason_codes, ("CALLER_OVERRIDE",))

    def test_override_fails_when_tier_is_disallowed(self) -> None:
        decision = self.router.route(
            RouteRequest(
                query="Summarize this",
                tier_override=Tier.FAST,
                constraints=RouteConstraints(allowed_tiers={Tier.MEDIUM}),
            )
        )

        self.assertEqual(decision.status, DecisionStatus.UNSATISFIED_CONSTRAINTS)
        self.assertIsNone(decision.tier)

    def test_registry_enforces_capability_and_context_requirements(self) -> None:
        registry = ModelRegistry(
            [
                ModelSpec(model_id="quick", tier=Tier.FAST, context_window=8_000),
                ModelSpec(
                    model_id="vision-pro",
                    tier=Tier.HIGH,
                    context_window=100_000,
                    capabilities={"text", "vision"},
                ),
            ]
        )
        decision = Router(model_registry=registry).route(
            RouteRequest(
                query="Describe the image",
                constraints=RouteConstraints(
                    required_capabilities={"vision"}, required_context_window=20_000
                ),
            )
        )

        self.assertEqual(decision.tier, Tier.HIGH)
        self.assertEqual(decision.model_id, "vision-pro")

    def test_query_can_infer_vision_capability(self) -> None:
        registry = ModelRegistry(
            [
                ModelSpec(model_id="text-fast", tier=Tier.FAST, context_window=8_000),
                ModelSpec(
                    model_id="vision-high",
                    tier=Tier.HIGH,
                    context_window=100_000,
                    capabilities={"text", "vision"},
                ),
            ]
        )

        decision = Router(model_registry=registry).route(
            RouteRequest(query="Describe the attached image")
        )

        self.assertEqual(decision.tier, Tier.HIGH)
        self.assertEqual(decision.model_id, "vision-high")
        self.assertIn("VISION_INPUT_DETECTED", decision.reason_codes)

    def test_query_can_infer_audio_capability(self) -> None:
        registry = ModelRegistry(
            [
                ModelSpec(model_id="text-fast", tier=Tier.FAST),
                ModelSpec(
                    model_id="audio-max",
                    tier=Tier.MAX,
                    capabilities={"text", "audio"},
                ),
            ]
        )

        decision = Router(model_registry=registry).route(
            RouteRequest(query="Transcribe this recording")
        )

        self.assertEqual(decision.tier, Tier.MAX)
        self.assertIn("AUDIO_INPUT_DETECTED", decision.reason_codes)

    def test_technical_use_of_image_does_not_infer_vision(self) -> None:
        decision = self.router.route(RouteRequest(query="Build a Docker image"))

        self.assertEqual(decision.tier, Tier.FAST)
        self.assertNotIn("VISION_INPUT_DETECTED", decision.reason_codes)

    def test_missing_capability_returns_explicit_failure(self) -> None:
        decision = self.router.route(
            RouteRequest(
                query="Transcribe this audio",
                constraints=RouteConstraints(required_capabilities={"audio"}),
            )
        )

        self.assertEqual(decision.status, DecisionStatus.UNSATISFIED_CONSTRAINTS)
        self.assertIn("NO_ELIGIBLE_MODEL", decision.reason_codes)

    def test_unknown_context_capacity_does_not_satisfy_requirement(self) -> None:
        decision = self.router.route(
            RouteRequest(
                query="Summarize the supplied corpus",
                constraints=RouteConstraints(required_context_window=32_000),
            )
        )

        self.assertEqual(decision.status, DecisionStatus.UNSATISFIED_CONSTRAINTS)

    def test_classifier_can_raise_but_not_lower_rule_tier(self) -> None:
        router = Router(
            classifier=HighClassifier(),
            policy=RoutingPolicy(classifier_min_score=0, classifier_max_score=20),
        )
        decision = router.route(RouteRequest(query="Analyze this choice"))

        self.assertEqual(decision.tier, Tier.HIGH)
        self.assertEqual(decision.decision_source, DecisionSource.CLASSIFIER)
        self.assertEqual(decision.confidence, 0.86)

    def test_classifier_failure_uses_documented_fallback(self) -> None:
        router = Router(
            classifier=FailingClassifier(),
            policy=RoutingPolicy(classifier_min_score=0, classifier_max_score=20),
        )
        decision = router.route(RouteRequest(query="Hello"))

        self.assertEqual(decision.tier, Tier.MEDIUM)
        self.assertEqual(decision.decision_source, DecisionSource.FALLBACK)
        self.assertEqual(decision.classifier_error, "TimeoutError")
        self.assertIn("CLASSIFIER_FAILURE", decision.reason_codes)

    def test_blank_query_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            RouteRequest(query="   ")

    def test_batch_preserves_order(self) -> None:
        decisions = self.router.route_batch(
            [
                RouteRequest(query="Extract a date", task_type=TaskType.EXTRACTION),
                RouteRequest(
                    query="Design a distributed system architecture across several services",
                    risk=RiskLevel.CRITICAL,
                ),
            ]
        )

        self.assertEqual([item.tier for item in decisions], [Tier.FAST, Tier.MAX])

    def test_empty_registry_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one model"):
            ModelRegistry([])

    def test_duplicate_model_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "model_id values must be unique"):
            ModelRegistry(
                [
                    ModelSpec(model_id="duplicate", tier=Tier.FAST),
                    ModelSpec(model_id="duplicate", tier=Tier.HIGH),
                ]
            )

    def test_invalid_policy_thresholds_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "medium < high < max"):
            RoutingPolicy(medium_threshold=5, high_threshold=5, max_threshold=9)

        with self.assertRaisesRegex(ValidationError, "classifier_min_score"):
            RoutingPolicy(classifier_min_score=8, classifier_max_score=7)

    def test_feature_signals_cover_code_steps_size_and_risk(self) -> None:
        decision = self.router.route(
            RouteRequest(
                query="First inspect the code, then test it:\n```python\npass\n```" + "x" * 5_000,
                risk=RiskLevel.HIGH,
            )
        )

        self.assertEqual(decision.tier, Tier.HIGH)
        self.assertIn("MULTIPLE_REQUIREMENTS", decision.reason_codes)
        self.assertIn("CODE_CONTEXT", decision.reason_codes)
        self.assertIn("LARGE_INPUT", decision.reason_codes)
        self.assertIn("HIGH_COST_OF_FAILURE", decision.reason_codes)


if __name__ == "__main__":
    unittest.main()
