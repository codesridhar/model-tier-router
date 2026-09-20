"""Public API for the model tier router."""

from .config import ModelRegistry, RoutingPolicy
from .evaluation import CaseResult, EvaluationCase, EvaluationReport, evaluate
from .models import (
    ClassifierResult,
    DecisionSource,
    DecisionStatus,
    ModelSpec,
    RiskLevel,
    RouteConstraints,
    RouteDecision,
    RouteRequest,
    TaskType,
    Tier,
)
from .router import Classifier, Router

__version__ = "0.1.0"

__all__ = [
    "CaseResult",
    "Classifier",
    "ClassifierResult",
    "DecisionSource",
    "DecisionStatus",
    "EvaluationCase",
    "EvaluationReport",
    "ModelRegistry",
    "ModelSpec",
    "RiskLevel",
    "RouteConstraints",
    "RouteDecision",
    "RouteRequest",
    "Router",
    "RoutingPolicy",
    "TaskType",
    "Tier",
    "__version__",
    "evaluate",
]
