from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from model_router.demo_app import create_app


class DemoAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_page_is_served(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Routing Workbench", response.text)

    def test_route_endpoint_explains_high_tier(self) -> None:
        response = self.client.post(
            "/api/route",
            json={
                "query": "Investigate this deadlock across three services",
                "task_type": "coding",
                "risk": "standard",
                "allowed_tiers": ["fast", "medium", "high", "max"],
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["decision"]["tier"], "high")
        self.assertEqual(body["decision"]["rule_score"], 8)
        self.assertIn("SPECIALIZED_COMPLEXITY", body["decision"]["reason_codes"])

    def test_constraints_can_produce_no_eligible_model(self) -> None:
        response = self.client.post(
            "/api/route",
            json={
                "query": "Transcribe this recording",
                "allowed_tiers": ["fast", "medium", "high"],
                "required_capabilities": ["audio"],
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["decision"]["status"], "unsatisfied_constraints")
        self.assertIsNone(body["decision"]["tier"])

    def test_query_text_infers_vision_without_explicit_capability(self) -> None:
        response = self.client.post(
            "/api/route",
            json={"query": "Describe the attached image"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["decision"]["tier"], "high")
        self.assertIn("VISION_INPUT_DETECTED", body["decision"]["reason_codes"])

    def test_empty_allowed_tiers_is_rejected(self) -> None:
        response = self.client.post(
            "/api/route",
            json={"query": "Hello", "allowed_tiers": []},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
