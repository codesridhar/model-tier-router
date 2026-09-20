from __future__ import annotations

import unittest

from model_router import EvaluationCase, Router, RouteRequest, Tier, evaluate


class EvaluationTests(unittest.TestCase):
    def test_report_distinguishes_exact_under_and_over_routing(self) -> None:
        cases = [
            EvaluationCase(
                case_id="exact",
                request=RouteRequest(query="Hello"),
                expected_tier=Tier.FAST,
            ),
            EvaluationCase(
                case_id="under",
                request=RouteRequest(query="Write a greeting"),
                expected_tier=Tier.MEDIUM,
            ),
            EvaluationCase(
                case_id="over",
                request=RouteRequest(query="Analyze this"),
                expected_tier=Tier.FAST,
            ),
        ]

        report = evaluate(Router(), cases)

        self.assertEqual(report.total, 3)
        self.assertEqual(report.exact, 1)
        self.assertEqual(report.under_routed, 1)
        self.assertEqual(report.over_routed, 1)
        self.assertEqual(report.unsatisfied, 0)
        self.assertAlmostEqual(report.accuracy, 1 / 3)

    def test_empty_dataset_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one evaluation case"):
            evaluate(Router(), [])


if __name__ == "__main__":
    unittest.main()
