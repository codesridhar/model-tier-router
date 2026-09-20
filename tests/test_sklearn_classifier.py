from __future__ import annotations

import unittest

from model_router import RouteRequest, TaskType, Tier
from model_router.classifiers import TfidfClassifier, TrainingExample

TRAINING_DATA = [
    TrainingExample(
        query="Extract the invoice number", tier=Tier.FAST, task_type=TaskType.EXTRACTION
    ),
    TrainingExample(
        query="Classify this review sentiment", tier=Tier.FAST, task_type=TaskType.CLASSIFICATION
    ),
    TrainingExample(query="Identify the date", tier=Tier.FAST, task_type=TaskType.EXTRACTION),
    TrainingExample(query="Write a customer email", tier=Tier.MEDIUM, task_type=TaskType.WRITING),
    TrainingExample(
        query="Summarize this report", tier=Tier.MEDIUM, task_type=TaskType.SUMMARIZATION
    ),
    TrainingExample(
        query="Compare these two product options", tier=Tier.MEDIUM, task_type=TaskType.ANALYSIS
    ),
    TrainingExample(
        query="Debug a failure across several files", tier=Tier.HIGH, task_type=TaskType.CODING
    ),
    TrainingExample(
        query="Investigate a distributed deadlock", tier=Tier.HIGH, task_type=TaskType.CODING
    ),
    TrainingExample(
        query="Review this system architecture", tier=Tier.HIGH, task_type=TaskType.ANALYSIS
    ),
    TrainingExample(
        query="Plan a critical multi-region database migration",
        tier=Tier.MAX,
        task_type=TaskType.ANALYSIS,
    ),
    TrainingExample(
        query="Prove this difficult optimization theorem", tier=Tier.MAX, task_type=TaskType.MATH
    ),
    TrainingExample(
        query="Design a critical recovery strategy across systems",
        tier=Tier.MAX,
        task_type=TaskType.ANALYSIS,
    ),
]


class TfidfClassifierTests(unittest.TestCase):
    def test_classifier_returns_typed_prediction_and_confidence(self) -> None:
        classifier = TfidfClassifier(TRAINING_DATA)

        result = classifier.classify(
            RouteRequest(query="Investigate a distributed deadlock", task_type=TaskType.CODING)
        )

        self.assertEqual(result.tier, Tier.HIGH)
        self.assertIsNotNone(result.confidence)
        self.assertGreater(result.confidence or 0, 0)
        self.assertLessEqual(result.confidence or 0, 1)
        self.assertEqual(result.reason_codes, ("TRAINED_TEXT_CLASSIFIER",))

    def test_classifier_requires_multiple_tiers(self) -> None:
        examples = [
            TrainingExample(query=f"Extract value {index}", tier=Tier.FAST) for index in range(4)
        ]

        with self.assertRaisesRegex(ValueError, "at least two tiers"):
            TfidfClassifier(examples)

    def test_classifier_requires_minimum_dataset_size(self) -> None:
        examples = [
            TrainingExample(query="Extract a value", tier=Tier.FAST),
            TrainingExample(query="Analyze a system", tier=Tier.HIGH),
        ]

        with self.assertRaisesRegex(ValueError, "at least four"):
            TfidfClassifier(examples)


if __name__ == "__main__":
    unittest.main()
