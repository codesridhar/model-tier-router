"""Run the bundled smoke dataset against the current routing policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from model_router import (
    ModelRegistry,
    ModelSpec,
    RiskLevel,
    RouteConstraints,
    Router,
    RouteRequest,
    TaskType,
    Tier,
)


def build_router() -> Router:
    registry = ModelRegistry(
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
    return Router(model_registry=registry)


def load_cases(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    dataset_path = Path(__file__).with_name("test_queries.jsonl")
    router = build_router()
    failures = 0

    print(f"{'CASE':34} {'EXPECTED':12} {'ACTUAL':12} {'SCORE':5} RESULT")
    print("-" * 79)
    for case in load_cases(dataset_path):
        allowed = case.get("allowed_tiers", [tier.value for tier in Tier])
        request = RouteRequest(
            query=case["query"],
            task_type=TaskType(case.get("task_type", "general")),
            risk=RiskLevel(case.get("risk", "standard")),
            constraints=RouteConstraints(
                allowed_tiers={Tier(value) for value in allowed},
                required_capabilities=set(case.get("required_capabilities", [])),
                required_context_window=case.get("required_context_window", 0),
            ),
            tier_override=Tier(case["tier_override"]) if case.get("tier_override") else None,
        )
        decision = router.route(request)
        expected_tier = case.get("expected_tier")
        actual_tier = decision.tier.value if decision.tier else None
        passed = decision.status.value == case["expected_status"] and actual_tier == expected_tier
        failures += not passed
        score = "—" if decision.rule_score is None else str(decision.rule_score)
        print(
            f"{case['case_id'][:34]:34} {expected_tier!s:12} "
            f"{actual_tier!s:12} {score:5} {'PASS' if passed else 'FAIL'}"
        )

    if failures:
        raise SystemExit(f"{failures} dataset case(s) failed")
    print(f"\nAll {len(load_cases(dataset_path))} dataset cases passed.")


if __name__ == "__main__":
    main()
