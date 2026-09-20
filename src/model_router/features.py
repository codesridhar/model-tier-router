"""Deterministic feature extraction used by the rules-first router."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import RiskLevel, RouteRequest, TaskType


@dataclass(frozen=True)
class RuleAssessment:
    score: int
    reason_codes: tuple[str, ...]
    inferred_capabilities: frozenset[str] = frozenset()


_SIMPLE_PATTERNS = re.compile(
    r"\b(classify|extract|identify|translate|spellcheck|fix (?:a |the )?typo|sentiment)\b",
    re.IGNORECASE,
)
_REASONING_PATTERNS = re.compile(
    r"\b(analy[sz]e|compare|evaluate|investigate|debug|diagnose|design|strategy|trade-?offs?)\b",
    re.IGNORECASE,
)
_DEEP_PATTERNS = re.compile(
    r"\b(deadlock|race condition|distributed system|architecture migration|formal proof|"
    r"security vulnerabilit(?:y|ies)|root cause|multi-agent|optimization problem)\b",
    re.IGNORECASE,
)
_MULTI_COMPONENT = re.compile(
    r"\b(?:multiple|several|three|four|five|six|seven|eight|nine|\d+)\s+"
    r"(?:services|files|systems|sources|documents|repositories|components)\b",
    re.IGNORECASE,
)
_MULTI_STEP = re.compile(
    r"\b(first|then|finally|step-by-step|plan and (?:implement|test)|implement and test)\b",
    re.IGNORECASE,
)
_VISION_INPUT = re.compile(
    r"\b(?:describe|analy[sz]e|inspect|read|extract\s+text\s+from)\s+"
    r"(?:(?:this|the|an?)\s+)?(?:(?:attached|uploaded)\s+)?"
    r"(?:image|photo|picture|screenshot|diagram)\b",
    re.IGNORECASE,
)
_AUDIO_INPUT = re.compile(
    r"\b(?:transcribe|listen\s+to|analy[sz]e|summari[sz]e)\s+"
    r"(?:(?:this|the|an?)\s+)?(?:(?:attached|uploaded)\s+)?"
    r"(?:audio|recording|podcast|speech|voice\s+note)\b",
    re.IGNORECASE,
)


def assess(request: RouteRequest) -> RuleAssessment:
    """Compute explainable, provider-independent complexity signals."""

    text = "\n".join((request.query, *request.context))
    score = 0
    reasons: list[str] = []
    inferred_capabilities: set[str] = set()

    if _VISION_INPUT.search(text):
        inferred_capabilities.add("vision")
        reasons.append("VISION_INPUT_DETECTED")
    if _AUDIO_INPUT.search(text):
        inferred_capabilities.add("audio")
        reasons.append("AUDIO_INPUT_DETECTED")

    if _SIMPLE_PATTERNS.search(request.query) and request.task_type in {
        TaskType.GENERAL,
        TaskType.CLASSIFICATION,
        TaskType.EXTRACTION,
    }:
        reasons.append("BOUNDED_SIMPLE_TASK")

    if request.task_type in {TaskType.ANALYSIS, TaskType.CODING, TaskType.MATH}:
        score += 1
        reasons.append("REASONING_TASK_TYPE")
    if _REASONING_PATTERNS.search(text):
        score += 2
        reasons.append("MULTI_STEP_REASONING")
    if _DEEP_PATTERNS.search(text):
        score += 3
        reasons.append("SPECIALIZED_COMPLEXITY")
    if _MULTI_COMPONENT.search(text):
        score += 2
        reasons.append("MULTI_COMPONENT_ANALYSIS")
    if _MULTI_STEP.search(text) or request.query.count("\n-") >= 2:
        score += 2
        reasons.append("MULTIPLE_REQUIREMENTS")
    if "```" in text:
        score += 1
        reasons.append("CODE_CONTEXT")

    text_length = len(text)
    if text_length >= 20_000:
        score += 3
        reasons.append("VERY_LARGE_INPUT")
    elif text_length >= 5_000:
        score += 1
        reasons.append("LARGE_INPUT")

    risk_scores = {
        RiskLevel.LOW: 0,
        RiskLevel.STANDARD: 0,
        RiskLevel.HIGH: 2,
        RiskLevel.CRITICAL: 4,
    }
    risk_score = risk_scores[request.risk]
    if risk_score:
        score += risk_score
        reasons.append("HIGH_COST_OF_FAILURE")

    if not reasons:
        reasons.append("GENERAL_REQUEST")
    return RuleAssessment(
        score=score,
        reason_codes=tuple(dict.fromkeys(reasons)),
        inferred_capabilities=frozenset(inferred_capabilities),
    )
