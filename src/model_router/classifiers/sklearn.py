"""Trainable text classifier backed by scikit-learn.

Install with ``pip install 'model-tier-router[nlp]'``. The classifier works out of the box with a
small, generic dataset bundled in the package. Consuming applications can extend or replace that
dataset because tier boundaries ultimately depend on their models and quality criteria.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from importlib.resources import files
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models import ClassifierResult, RiskLevel, RouteRequest, TaskType, Tier

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
except ImportError as exc:  # pragma: no cover - exercised in an environment without the extra
    raise ImportError(
        "TfidfClassifier requires the NLP extra: pip install 'model-tier-router[nlp]'"
    ) from exc


class TrainingExample(BaseModel):
    """One human-reviewed query and its lowest successful model tier."""

    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=1)
    tier: Tier
    task_type: TaskType = TaskType.GENERAL
    risk: RiskLevel = RiskLevel.STANDARD


@lru_cache(maxsize=1)
def default_training_examples() -> tuple[TrainingExample, ...]:
    """Load the versioned generic examples distributed with the package.

    The returned models are immutable, and the resource is parsed only once per process.
    """

    resource = files("model_router").joinpath("data/default_training_data.jsonl")
    lines = resource.read_text(encoding="utf-8").splitlines()
    return tuple(
        TrainingExample.model_validate_json(line)
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    )


class TfidfClassifier:
    """A deterministic, local baseline classifier with bundled generic examples.

    The implementation uses word and phrase features with balanced logistic regression. It makes
    no network calls and is safe to share between threads after training. Retraining should create
    a new instance and replace it atomically in the host application.
    """

    def __init__(
        self,
        examples: Iterable[TrainingExample] | None = None,
        *,
        include_default_examples: bool = True,
    ) -> None:
        """Train a classifier from bundled data and optional application examples.

        With no arguments, the bundled generic dataset is used. Supplied examples extend that
        dataset by default. Set ``include_default_examples=False`` to train exclusively on the
        supplied examples.
        """

        additional_examples = tuple(examples or ())
        bundled_examples = default_training_examples() if include_default_examples else ()
        training_examples = (*bundled_examples, *additional_examples)
        if len(training_examples) < 4:
            raise ValueError("at least four training examples are required")
        labels = {example.tier.value for example in training_examples}
        if len(labels) < 2:
            raise ValueError("training examples must contain at least two tiers")

        self._pipeline: Pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        lowercase=True,
                        ngram_range=(1, 2),
                        sublinear_tf=True,
                        max_features=20_000,
                    ),
                ),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1_000,
                        random_state=0,
                    ),
                ),
            ]
        )
        texts = [
            self._text(example.query, example.task_type, example.risk)
            for example in training_examples
        ]
        tiers = [example.tier.value for example in training_examples]
        self._pipeline.fit(texts, tiers)
        self.training_example_count = len(training_examples)
        self.includes_default_examples = include_default_examples

    def classify(self, request: RouteRequest) -> ClassifierResult:
        """Predict a tier and calibrated-like probability for one request.

        Logistic-regression probabilities are useful for relative confidence and routing policy,
        but consumers should measure calibration against a held-out dataset before assigning a
        strict operational meaning to them.
        """

        text = self._text(request.query, request.task_type, request.risk)
        probabilities: Any = self._pipeline.predict_proba([text])[0]
        classifier: Any = self._pipeline.named_steps["classifier"]
        best_index = int(probabilities.argmax())
        return ClassifierResult(
            tier=Tier(classifier.classes_[best_index]),
            confidence=float(probabilities[best_index]),
            reason_codes=("TRAINED_TEXT_CLASSIFIER",),
        )

    @staticmethod
    def _text(query: str, task_type: TaskType, risk: RiskLevel) -> str:
        return f"task_{task_type.value} risk_{risk.value} {query.strip()}"
